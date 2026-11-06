"""public.discord_server_snapshots・public.discord_server_apply_runs に RLS（型A）（ADR-1067 段階④ 便④-2）。

使い捨て DB を試験ごとに作り（共有の検証用 DB に表を足さない）、本物の migration を適用して、
アプリ接続役（NOBYPASSRLS）で確かめる。読む＝自社の会社文脈か運営文脈、書く＝自社の会社文脈だけ。
会社番号は 972（自社）/ 973（他社）。
"""
from __future__ import annotations

import json
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit

import pytest

from tests.rls_bootstrap import _apply_migration, _ensure_public_users

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

_TENANT_A = 972
_TENANT_B = 973
_BASE_MIGRATION = "20261106_120000_create_discord_server_snapshot_tables.sql"
_MIGRATION = "20261107_110000_add_discord_server_records_rls.sql"
_GRANT_DDL = """
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO salesanchor_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO salesanchor_app;
"""
_TABLES = ["discord_server_snapshots", "discord_server_apply_runs"]

_INSERT_SNAPSHOT = (
    "INSERT INTO public.discord_server_snapshots (tenant_id, purpose, body, taken_by) "
    "VALUES (:t, 'own', CAST(:body AS JSONB), :uid) RETURNING id"
)
_INSERT_APPLY = (
    "INSERT INTO public.discord_server_apply_runs "
    "(tenant_id, purpose, plan_digest, started_at, finished_at, applied_by, result) "
    "VALUES (:t, 'own', :digest, :started, :finished, :uid, CAST(:result AS JSONB)) RETURNING id"
)
_BODY = '{"version":1,"roles":[],"channels":[]}'

# 表ごとの「今の 1 行を入れる文」と「他社の行を書き換える UPDATE 文（列だけ変える）」
_INSERT_BY_TABLE = {
    "discord_server_snapshots": (
        "INSERT INTO public.discord_server_snapshots (tenant_id, purpose, body, taken_by) "
        "VALUES (:t, 'own', CAST(:body AS JSONB), 1)",
        {"body": _BODY},
    ),
    "discord_server_apply_runs": (
        "INSERT INTO public.discord_server_apply_runs "
        "(tenant_id, purpose, plan_digest, applied_by, result) "
        "VALUES (:t, 'own', 'd', 1, CAST(:result AS JSONB))",
        {"result": '{"rows":[]}'},
    ),
}
_UPDATE_BY_TABLE = {
    "discord_server_snapshots": "UPDATE public.discord_server_snapshots SET taken_by = 2 WHERE tenant_id = :t",
    "discord_server_apply_runs": "UPDATE public.discord_server_apply_runs SET plan_digest = 'hacked' WHERE tenant_id = :t",
}


def _with_db(url: str, name: str) -> str:
    return urlunsplit(urlsplit(url)._replace(path="/" + name))


@asynccontextmanager
async def _fresh():
    """使い捨て DB を作り (admin_engine, app_engine) を返す。終了時に DROP。"""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    control = create_async_engine(ADMIN_PG_URL, isolation_level="AUTOCOMMIT")
    name = "dsr_rls_" + uuid.uuid4().hex[:12]
    async with control.connect() as conn:
        await conn.execute(text(f'CREATE DATABASE "{name}"'))
    admin_engine = create_async_engine(_with_db(ADMIN_PG_URL, name), echo=False)
    # 接続 1 本で使い回す（SET の戻り忘れ・張り直し漏れを実際に検出するため）
    app_engine = create_async_engine(
        _with_db(APP_PG_URL, name), echo=False, pool_size=1, max_overflow=0
    )
    try:
        async with admin_engine.begin() as conn:
            await _ensure_public_users(conn)
            await conn.execute(
                text(
                    "INSERT INTO public.tenants (id, tenant_code, tenant_name, company_name, is_active) "
                    "VALUES (972, 'tenant_972', 'T972', 'T972', TRUE), "
                    "(973, 'tenant_973', 'T973', 'T973', TRUE)"
                )
            )
        # 2 表を本物の migration で作る（表の定義を試験に書き写さない）
        await _apply_migration(admin_engine, _BASE_MIGRATION)
        async with admin_engine.begin() as conn:
            raw = await conn.get_raw_connection()
            await raw.driver_connection.execute(_GRANT_DDL)
            for sql, extra in _INSERT_BY_TABLE.values():
                for tid in (_TENANT_A, _TENANT_B):
                    await conn.execute(text(sql), {"t": tid, **extra})
        await _apply_migration(admin_engine, _MIGRATION)
        yield admin_engine, app_engine
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


async def _count_by_tenant(conn, table: str) -> dict[int, int]:
    from sqlalchemy import text

    rows = (
        await conn.execute(text(f"SELECT tenant_id, count(*) FROM public.{table} GROUP BY tenant_id"))
    ).all()
    return {r[0]: r[1] for r in rows}


# ① 自社の文脈: INSERT でき、自社の行だけが見える（土台 1 行＋今の 1 行）
@pytest.mark.parametrize("table", _TABLES)
async def test_own_context_inserts_and_sees_only_own_rows(table):
    from sqlalchemy import text

    async with _fresh() as (_admin, app_engine):
        conn, trans = await _ctx_conn(app_engine, _TENANT_A)
        try:
            sql, extra = _INSERT_BY_TABLE[table]
            await conn.execute(text(sql), {"t": _TENANT_A, **extra})
            assert await _count_by_tenant(conn, table) == {_TENANT_A: 2}
        finally:
            await trans.rollback()
            await conn.close()


# ② 他社の文脈では自社の行が 0 行
@pytest.mark.parametrize("table", _TABLES)
async def test_other_tenant_context_sees_no_rows(table):
    from sqlalchemy import text

    async with _fresh() as (_admin, app_engine):
        conn, trans = await _ctx_conn(app_engine, _TENANT_B)
        try:
            n = (
                await conn.execute(
                    text(f"SELECT count(*) FROM public.{table} WHERE tenant_id = :t"),
                    {"t": _TENANT_A},
                )
            ).scalar_one()
            assert n == 0
        finally:
            await trans.rollback()
            await conn.close()


# ③ 他社の tenant_id で INSERT すると 42501
@pytest.mark.parametrize("table", _TABLES)
async def test_insert_other_tenant_rejected(table):
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError

    async with _fresh() as (_admin, app_engine):
        conn, trans = await _ctx_conn(app_engine, _TENANT_A)
        try:
            sql, extra = _INSERT_BY_TABLE[table]
            with pytest.raises(DBAPIError) as exc_info:
                await conn.execute(text(sql), {"t": _TENANT_B, **extra})
            assert _sqlstate(exc_info.value) == "42501"
        finally:
            await trans.rollback()
            await conn.close()


# ④ 他社の行への UPDATE・DELETE は 0 行（他社の行は元のまま 1 行）
@pytest.mark.parametrize("table", _TABLES)
async def test_update_delete_other_tenant_rows_affect_nothing(table):
    from sqlalchemy import text

    async with _fresh() as (admin_engine, app_engine):
        conn, trans = await _ctx_conn(app_engine, _TENANT_A)
        try:
            r = await conn.execute(text(_UPDATE_BY_TABLE[table]), {"t": _TENANT_B})
            assert r.rowcount == 0
            r = await conn.execute(
                text(f"DELETE FROM public.{table} WHERE tenant_id = :t"), {"t": _TENANT_B}
            )
            assert r.rowcount == 0
        finally:
            await trans.rollback()
            await conn.close()
        rows = await _admin_exec(
            admin_engine,
            f"SELECT count(*) FROM public.{table} WHERE tenant_id = :t",
            {"t": _TENANT_B},
        )
        assert rows == [(1,)]
        # 元のまま（書き換えられていない）
        col = "taken_by" if table == "discord_server_snapshots" else "plan_digest"
        expected = 1 if table == "discord_server_snapshots" else "d"
        vals = await _admin_exec(
            admin_engine, f"SELECT {col} FROM public.{table} WHERE tenant_id = :t", {"t": _TENANT_B}
        )
        assert vals == [(expected,)]


# ⑤ 運営の文脈: どちらの会社の行も読める
@pytest.mark.parametrize("table", _TABLES)
async def test_operator_context_reads_all_tenants(table):
    async with _fresh() as (_admin, app_engine):
        conn, trans = await _ctx_conn(app_engine, None, operator=True)
        try:
            assert await _count_by_tenant(conn, table) == {_TENANT_A: 1, _TENANT_B: 1}
        finally:
            await trans.rollback()
            await conn.close()


# ⑥ 文脈なしは 0 行（新しい接続・同じ接続で SET app.tenant_id = '' の後。どちらもエラーにならない）
@pytest.mark.parametrize("table", _TABLES)
async def test_no_context_sees_zero_rows(table):
    from sqlalchemy import text

    async with _fresh() as (_admin, app_engine):
        conn, trans = await _ctx_conn(app_engine, None)
        try:
            n = (await conn.execute(text(f"SELECT count(*) FROM public.{table}"))).scalar_one()
            assert n == 0
        finally:
            await trans.rollback()
            await conn.close()

        conn = await app_engine.connect()
        try:
            await conn.execute(text("SET app.tenant_id = ''"))
            n = (await conn.execute(text(f"SELECT count(*) FROM public.{table}"))).scalar_one()
            assert n == 0
            await conn.execute(text("RESET app.tenant_id"))
            await conn.rollback()
        finally:
            await conn.close()


# ⑦ 同じ移行をもう一度当てても通り、ポリシーは 2 表とも 4 本のまま
async def test_migration_idempotent_four_policies():
    async with _fresh() as (admin_engine, _app):
        await _apply_migration(admin_engine, _MIGRATION)
        for table in _TABLES:
            flags = await _admin_exec(
                admin_engine,
                "SELECT relrowsecurity, relforcerowsecurity FROM pg_class "
                f"WHERE oid = to_regclass('public.{table}')",
            )
            assert tuple(flags[0]) == (True, True)
            n = (
                await _admin_exec(
                    admin_engine,
                    "SELECT count(*) FROM pg_policies "
                    "WHERE schemaname = 'public' AND tablename = :tn",
                    {"tn": table},
                )
            )[0][0]
            assert n == 4


# ⑧ 自社の行の tenant_id を他社へ付け替える UPDATE は 42501
@pytest.mark.parametrize("table", _TABLES)
async def test_update_tenant_id_to_other_rejected(table):
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError

    async with _fresh() as (_admin, app_engine):
        conn, trans = await _ctx_conn(app_engine, _TENANT_A)
        try:
            with pytest.raises(DBAPIError) as exc_info:
                await conn.execute(
                    text(f"UPDATE public.{table} SET tenant_id = :b WHERE tenant_id = :a"),
                    {"a": _TENANT_A, "b": _TENANT_B},
                )
            assert _sqlstate(exc_info.value) == "42501"
        finally:
            await trans.rollback()
            await conn.close()


# ⑨ 書込の入口と同じ文脈の張り方（SET app.tenant_id / SET app.is_operator）で、RETURNING 付き INSERT が通る
async def test_write_entry_context_insert_returning_ok():
    from sqlalchemy import text

    async with _fresh() as (_admin, app_engine):
        conn = await app_engine.connect()
        try:
            await conn.execute(text(f"SET app.tenant_id = '{_TENANT_A}'"))
            await conn.execute(text("SET app.is_operator = ''"))
            snap_id = (
                await conn.execute(
                    text(_INSERT_SNAPSHOT), {"t": _TENANT_A, "body": _BODY, "uid": 1}
                )
            ).scalars().all()
            assert len(snap_id) == 1
            now = datetime.now(timezone.utc)
            run_id = (
                await conn.execute(
                    text(_INSERT_APPLY),
                    {
                        "t": _TENANT_A,
                        "digest": "d",
                        "started": now,
                        "finished": now,
                        "uid": 1,
                        "result": json.dumps({"rows": []}),
                    },
                )
            ).scalars().all()
            assert len(run_id) == 1
        finally:
            await conn.rollback()
            await conn.execute(text("RESET app.tenant_id"))
            await conn.execute(text("RESET app.is_operator"))
            await conn.rollback()
            await conn.close()
