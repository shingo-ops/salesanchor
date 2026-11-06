"""public.inventory_movements に RLS（型A）（ADR-1067 段階④ 便④-1）。

使い捨て DB を試験ごとに作り（共有の検証用 DB に表を足さない）、本物の migration を適用して、
アプリ接続役（NOBYPASSRLS）で確かめる。読む＝自社の会社文脈か運営文脈、書く＝自社の会社文脈だけ。
会社番号は 976（自社）/ 977（他社）。
"""
from __future__ import annotations

import os
import sys
import uuid
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import pytest

from tests.rls_bootstrap import _apply_migration, bootstrap_public_products

ADMIN_PG_URL = os.getenv("RLS_ADMIN_DATABASE_URL") or os.getenv("TEST_PG_URL")
APP_PG_URL = os.getenv("RLS_TEST_DATABASE_URL")

pytestmark = [
    pytest.mark.skipif(
        not ADMIN_PG_URL or not APP_PG_URL,
        reason=(
            "実 PostgreSQL 環境が必要 "
            "(RLS_ADMIN_DATABASE_URL / RLS_TEST_DATABASE_URL 未設定)。"
        ),
    ),
    pytest.mark.asyncio,
]

# 書き出し台本を import するための path 追加（test_export_inventory_for_sheet.py と同じ形）
_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

_TENANT_A = 976
_TENANT_B = 977
_MIGRATION = "20261107_100000_add_inventory_movements_rls.sql"
_GRANT_DDL = """
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO salesanchor_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO salesanchor_app;
"""
_INSERT_MOVEMENT = (
    "INSERT INTO public.inventory_movements "
    "(tenant_id, product_id, before_qty, delta_qty, after_qty, source_type, operator_id, notes) "
    "VALUES (:t, :p, 100, -1, 99, 'manual_adjust', 1, :n)"
)


def _with_db(url: str, name: str) -> str:
    return urlunsplit(urlsplit(url)._replace(path="/" + name))


@asynccontextmanager
async def _fresh():
    """使い捨て DB を作り (admin_engine, app_engine, product_id) を返す。終了時に DROP。"""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    control = create_async_engine(ADMIN_PG_URL, isolation_level="AUTOCOMMIT")
    name = "imv_rls_" + uuid.uuid4().hex[:12]
    async with control.connect() as conn:
        await conn.execute(text(f'CREATE DATABASE "{name}"'))
    admin_engine = create_async_engine(_with_db(ADMIN_PG_URL, name), echo=False)
    # 接続 1 本で使い回す（SET の戻り忘れ・張り直し漏れを実際に検出するため）
    app_engine = create_async_engine(
        _with_db(APP_PG_URL, name), echo=False, pool_size=1, max_overflow=0
    )
    try:
        # inventory_movements と products・suppliers を本物の migration で作る
        await bootstrap_public_products(admin_engine)
        async with admin_engine.begin() as conn:
            pid = (
                await conn.execute(
                    text(
                        "INSERT INTO public.products (name, stock_quantity) "
                        "VALUES ('imv rls', 100) RETURNING id"
                    )
                )
            ).scalar_one()
            raw = await conn.get_raw_connection()
            await raw.driver_connection.execute(_GRANT_DDL)
            for tid in (_TENANT_A, _TENANT_B):
                await conn.execute(text(_INSERT_MOVEMENT), {"t": tid, "p": pid, "n": f"seed{tid}"})
        await _apply_migration(admin_engine, _MIGRATION)
        yield admin_engine, app_engine, pid
    finally:
        await app_engine.dispose()
        await admin_engine.dispose()
        async with control.connect() as conn:
            await conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        await control.dispose()


async def _admin_exec(admin_engine, sql: str, params: dict | None = None):
    from sqlalchemy import text

    async with admin_engine.begin() as conn:
        result = await conn.execute(text(sql), params or {})
        return result.all() if result.returns_rows else []


async def _ctx_conn(app_engine, tenant_id: int | None, operator: bool = False):
    """アプリ接続役で文脈を張った接続と trans を返す（tenant_id=None は会社文脈なし）。"""
    from sqlalchemy import text

    conn = await app_engine.connect()
    trans = await conn.begin()
    if tenant_id is not None:
        await conn.execute(text("SELECT set_config('app.tenant_id', :t, true)"), {"t": str(tenant_id)})
    if operator:
        await conn.execute(text("SELECT set_config('app.is_operator', 'true', true)"))
    return conn, trans


def _sqlstate(exc) -> str | None:
    orig = exc.orig
    return getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)


async def _count_by_tenant(conn) -> dict[int, int]:
    from sqlalchemy import text

    rows = (
        await conn.execute(
            text("SELECT tenant_id, count(*) FROM public.inventory_movements GROUP BY tenant_id")
        )
    ).all()
    return {r[0]: r[1] for r in rows}


# ① 自社の文脈: INSERT でき、自社の行だけが見える（土台 1 行＋今の 1 行）
async def test_own_context_inserts_and_sees_only_own_rows():
    async with _fresh() as (_admin, app_engine, pid):
        conn, trans = await _ctx_conn(app_engine, _TENANT_A)
        try:
            from sqlalchemy import text

            await conn.execute(text(_INSERT_MOVEMENT), {"t": _TENANT_A, "p": pid, "n": "mine"})
            assert await _count_by_tenant(conn) == {_TENANT_A: 2}
        finally:
            await trans.rollback()
            await conn.close()


# ② 他社の文脈では自社の行が 0 行
async def test_other_tenant_context_sees_no_rows():
    from sqlalchemy import text

    async with _fresh() as (_admin, app_engine, _pid):
        conn, trans = await _ctx_conn(app_engine, _TENANT_B)
        try:
            n = (
                await conn.execute(
                    text("SELECT count(*) FROM public.inventory_movements WHERE tenant_id = :t"),
                    {"t": _TENANT_A},
                )
            ).scalar_one()
            assert n == 0
        finally:
            await trans.rollback()
            await conn.close()


# ③ 他社の tenant_id で INSERT すると 42501
async def test_insert_other_tenant_rejected():
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError

    async with _fresh() as (_admin, app_engine, pid):
        conn, trans = await _ctx_conn(app_engine, _TENANT_A)
        try:
            with pytest.raises(DBAPIError) as exc_info:
                await conn.execute(text(_INSERT_MOVEMENT), {"t": _TENANT_B, "p": pid, "n": "x"})
            assert _sqlstate(exc_info.value) == "42501"
        finally:
            await trans.rollback()
            await conn.close()


# ④ 他社の行への UPDATE・DELETE は 0 行（他社の行は元のまま）
async def test_update_delete_other_tenant_rows_affect_nothing():
    from sqlalchemy import text

    async with _fresh() as (admin_engine, app_engine, _pid):
        conn, trans = await _ctx_conn(app_engine, _TENANT_A)
        try:
            r = await conn.execute(
                text("UPDATE public.inventory_movements SET notes = 'hacked' WHERE tenant_id = :t"),
                {"t": _TENANT_B},
            )
            assert r.rowcount == 0
            r = await conn.execute(
                text("DELETE FROM public.inventory_movements WHERE tenant_id = :t"), {"t": _TENANT_B}
            )
            assert r.rowcount == 0
        finally:
            await trans.rollback()
            await conn.close()
        rows = await _admin_exec(
            admin_engine,
            "SELECT notes FROM public.inventory_movements WHERE tenant_id = :t",
            {"t": _TENANT_B},
        )
        assert rows == [(f"seed{_TENANT_B}",)]


# ⑤ 運営の文脈: どちらの会社の行も読める
async def test_operator_context_reads_all_tenants():
    async with _fresh() as (_admin, app_engine, _pid):
        conn, trans = await _ctx_conn(app_engine, None, operator=True)
        try:
            assert await _count_by_tenant(conn) == {_TENANT_A: 1, _TENANT_B: 1}
        finally:
            await trans.rollback()
            await conn.close()


# ⑥ 文脈なしは 0 行（新しい接続・同じ接続で SET app.tenant_id = '' の後。どちらもエラーにならない）
async def test_no_context_sees_zero_rows():
    from sqlalchemy import text

    async with _fresh() as (_admin, app_engine, _pid):
        conn, trans = await _ctx_conn(app_engine, None)
        try:
            n = (await conn.execute(text("SELECT count(*) FROM public.inventory_movements"))).scalar_one()
            assert n == 0
        finally:
            await trans.rollback()
            await conn.close()

        conn = await app_engine.connect()
        try:
            await conn.execute(text("SET app.tenant_id = ''"))
            n = (await conn.execute(text("SELECT count(*) FROM public.inventory_movements"))).scalar_one()
            assert n == 0
            await conn.execute(text("RESET app.tenant_id"))
            await conn.rollback()
        finally:
            await conn.close()


# ⑦ 同じ移行をもう一度当てても通り、ポリシーは 4 本のまま
async def test_migration_idempotent_four_policies():
    async with _fresh() as (admin_engine, _app, _pid):
        await _apply_migration(admin_engine, _MIGRATION)
        flags = await _admin_exec(
            admin_engine,
            "SELECT relrowsecurity, relforcerowsecurity FROM pg_class "
            "WHERE oid = to_regclass('public.inventory_movements')",
        )
        assert tuple(flags[0]) == (True, True)
        n = (
            await _admin_exec(
                admin_engine,
                "SELECT count(*) FROM pg_policies "
                "WHERE schemaname = 'public' AND tablename = 'inventory_movements'",
            )
        )[0][0]
        assert n == 4


# ⑧ 自社の行の tenant_id を他社へ付け替える UPDATE は 42501
async def test_update_tenant_id_to_other_rejected():
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError

    async with _fresh() as (_admin, app_engine, _pid):
        conn, trans = await _ctx_conn(app_engine, _TENANT_A)
        try:
            with pytest.raises(DBAPIError) as exc_info:
                await conn.execute(
                    text("UPDATE public.inventory_movements SET tenant_id = :b WHERE tenant_id = :a"),
                    {"a": _TENANT_A, "b": _TENANT_B},
                )
            assert _sqlstate(exc_info.value) == "42501"
        finally:
            await trans.rollback()
            await conn.close()


# ⑨ 書き出しの入口: 自社の行だけが返り、文脈が取引の外に残らない
async def test_export_fetch_movements_scoped_and_context_not_leaked():
    from sqlalchemy import text

    from export_inventory_for_sheet import fetch_movements

    async with _fresh() as (_admin, app_engine, _pid):
        rows = await fetch_movements(
            app_engine, tenant_id=_TENANT_A, since=date(2000, 1, 1), until=None
        )
        assert len(rows) == 1
        assert rows[0]["notes"] == f"seed{_TENANT_A}"
        # 同じ app_engine（接続 1 本）で文脈なしの SELECT が 0 行
        async with app_engine.connect() as conn:
            n = (await conn.execute(text("SELECT count(*) FROM public.inventory_movements"))).scalar_one()
            assert n == 0
