"""public.suppliers の会社別 RLS（ADR-1018 段階②b）。

使い捨て DB を試験ごとに作り（共有の検証用 DB に表を足さない）、
suppliers 関連 migration と RLS migration を適用し、アプリ接続役（NOBYPASSRLS）で確かめる。
会社番号は 982 / 983。
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import uuid
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from urllib.parse import urlsplit, urlunsplit

import pytest
from fastapi import HTTPException, UploadFile

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

_TENANT_A = 982
_TENANT_B = 983
_MIGRATIONS = (
    "056_add_suppliers_type_and_promote_public.sql",
    "20260603_010000_add_suppliers_line_and_address.sql",
    "20260918_030000_supplier_ssot_phase2.sql",
    "20260920_020000_supplier_line_name_unique.sql",
    "20260924_010000_add_supplier_extraction_rules.sql",
    "20260924_030000_add_extraction_example_text.sql",
    "20261006_170200_add_supplier_new_system_rules.sql",
    "20261016_020000_add_suppliers_rls.sql",
)
# 取込経路が参照する public の表は本物の migration を適用して得る（定義のコピーを持たない）。
# extraction_ship_format は 20260928_110000 が追加する。
_SUPPORT_MIGRATIONS = (
    "20260921_110000_pipeline_tables_public.sql",
    "20260926_080000_create_extraction_prompt_config.sql",
    "20260928_110000_create_extraction_shadow_tables.sql",
    "20261013_180000_drop_extraction_shadow_tables.sql",
)
_SUPPORT_DDL = """
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO salesanchor_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO salesanchor_app;
"""


def _with_db(url: str, name: str) -> str:
    return urlunsplit(urlsplit(url)._replace(path="/" + name))


@asynccontextmanager
async def _fresh():
    """使い捨て DB を作り (admin_engine, app_engine) を返す。終了時に DROP。"""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    control = create_async_engine(ADMIN_PG_URL, isolation_level="AUTOCOMMIT")
    name = "s2b_rls_" + uuid.uuid4().hex[:12]
    async with control.connect() as conn:
        await conn.execute(text(f'CREATE DATABASE "{name}"'))
    admin_engine = create_async_engine(_with_db(ADMIN_PG_URL, name), echo=False)
    # 接続 1 本で使い回す（SET の戻り忘れを実際に検出するため）
    app_engine = create_async_engine(
        _with_db(APP_PG_URL, name), echo=False, pool_size=1, max_overflow=0
    )
    try:
        # 取込表が FK で参照する public.products 等を、本物の migration で先に用意する
        await bootstrap_public_products(admin_engine)
        for filename in _MIGRATIONS[:-1]:
            await _apply_migration(admin_engine, filename)
        for filename in _SUPPORT_MIGRATIONS:
            await _apply_migration(admin_engine, filename)
        async with admin_engine.begin() as conn:
            raw = await conn.get_raw_connection()
            await raw.driver_connection.execute(_SUPPORT_DDL)
        await _apply_migration(admin_engine, _MIGRATIONS[-1])
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


async def _seed_supplier(admin_engine, name: str, tenant_id: int | None, code: str | None = None,
                         line_name: str | None = None) -> int:
    rows = await _admin_exec(
        admin_engine,
        "INSERT INTO public.suppliers (name, tenant_id, supplier_code, line_name) "
        "VALUES (:n, :t, :c, :l) RETURNING id",
        {"n": name, "t": tenant_id, "c": code, "l": line_name},
    )
    return rows[0][0]


async def _ctx_conn(app_engine, tenant_id: int | None, operator: bool = False):
    """アプリ接続役で文脈（tenant / operator）を張った接続と trans を返す。"""
    from sqlalchemy import text

    conn = await app_engine.connect()
    trans = await conn.begin()
    if tenant_id is not None:
        await conn.execute(text("SELECT set_config('app.tenant_id', :t, true)"), {"t": str(tenant_id)})
    if operator:
        await conn.execute(text("SELECT set_config('app.is_operator', 'true', true)"))
    return conn, trans


async def _operator_value(db) -> str | None:
    from sqlalchemy import text

    return (await db.execute(text("SELECT current_setting('app.is_operator', true)"))).scalar_one()


def _session(app_engine):
    from sqlalchemy.ext.asyncio import AsyncSession

    return AsyncSession(app_engine, expire_on_commit=False)


# ① 構造
async def test_catalog_rls_forced_and_four_policies():
    from sqlalchemy import text

    async with _fresh() as (admin_engine, _app):
        async with admin_engine.connect() as conn:
            flags = (
                await conn.execute(
                    text(
                        "SELECT relrowsecurity, relforcerowsecurity FROM pg_class "
                        "WHERE oid = to_regclass('public.suppliers')"
                    )
                )
            ).one()
            assert tuple(flags) == (True, True)
            names = (
                await conn.execute(
                    text(
                        "SELECT policyname FROM pg_policies "
                        "WHERE schemaname = 'public' AND tablename = 'suppliers' ORDER BY policyname"
                    )
                )
            ).scalars().all()
            assert names == ["suppliers_delete", "suppliers_insert", "suppliers_select", "suppliers_update"]


# ② 見える範囲
async def test_select_common_rows_visible_and_other_tenant_rows_hidden():
    async with _fresh() as (admin_engine, app_engine):
        await _seed_supplier(admin_engine, "common", None)
        await _seed_supplier(admin_engine, "a-own", _TENANT_A)
        await _seed_supplier(admin_engine, "b-own", _TENANT_B)

        async def names(tenant_id):
            from sqlalchemy import text

            conn, trans = await _ctx_conn(app_engine, tenant_id)
            try:
                return sorted((await conn.execute(text("SELECT name FROM public.suppliers"))).scalars().all())
            finally:
                await trans.rollback()
                await conn.close()

        assert await names(None) == ["common"]
        assert await names(_TENANT_A) == ["a-own", "common"]
        assert await names(_TENANT_B) == ["b-own", "common"]


# ③ 書けない範囲
async def test_tenant_context_cannot_write_common_rows():
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError

    async with _fresh() as (admin_engine, app_engine):
        common_id = await _seed_supplier(admin_engine, "common", None)
        b_id = await _seed_supplier(admin_engine, "b-own", _TENANT_B)

        # 会社文脈で共通行の UPDATE → 0 行
        conn, trans = await _ctx_conn(app_engine, _TENANT_A)
        try:
            upd = await conn.execute(
                text("UPDATE public.suppliers SET notes = 'z' WHERE id = :i"), {"i": common_id}
            )
            assert upd.rowcount == 0
            # 他社行の UPDATE → 0 行
            upd = await conn.execute(
                text("UPDATE public.suppliers SET notes = 'z' WHERE id = :i"), {"i": b_id}
            )
            assert upd.rowcount == 0
        finally:
            await trans.rollback()
            await conn.close()

        # 会社文脈で共通行の INSERT → 42501
        conn, trans = await _ctx_conn(app_engine, _TENANT_A)
        try:
            with pytest.raises(DBAPIError) as exc_info:
                await conn.execute(
                    text("INSERT INTO public.suppliers (name, tenant_id) VALUES ('x', NULL)")
                )
            orig = exc_info.value.orig
            assert (getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)) == "42501"
        finally:
            await trans.rollback()
            await conn.close()

        # 自社行の INSERT は通る。運営文脈なら共通行の UPDATE が 1 行
        conn, trans = await _ctx_conn(app_engine, _TENANT_A)
        try:
            await conn.execute(text("INSERT INTO public.suppliers (name, tenant_id) VALUES ('a', 982)"))
        finally:
            await trans.rollback()
            await conn.close()
        conn, trans = await _ctx_conn(app_engine, None, operator=True)
        try:
            upd = await conn.execute(
                text("UPDATE public.suppliers SET notes = 'z' WHERE id = :i"), {"i": common_id}
            )
            assert upd.rowcount == 1
        finally:
            await trans.rollback()
            await conn.close()


# ④ #1 LINE 取込の自動登録（文脈なしのセッションで呼ぶ）
async def test_import_line_export_autoregisters_common_supplier():
    from app.services import tcg_line_import_svc as svc

    export_text = "2026.10.01 木曜日\n12:00 新規仕入先X こんにちは\n"
    async with _fresh() as (admin_engine, app_engine):
        with patch.object(svc, "_write_source_messages", AsyncMock(return_value=[])), patch.object(
            svc, "_enqueue_extraction"
        ):
            async with _session(app_engine) as db:
                result = await svc.import_line_export(
                    db, "t.txt", export_text, uploaded_by=None, window_hours=0
                )
                assert result["status"] == "imported"
                assert await _operator_value(db) in (None, "")
        rows = await _admin_exec(
            admin_engine,
            "SELECT tenant_id, supplier_code FROM public.suppliers WHERE line_name = '新規仕入先X'",
        )
        assert len(rows) == 1
        assert rows[0][0] is None
        assert rows[0][1] and rows[0][1].startswith("SP-")


# ⑤ #2 取込レビューの仕入先決定
async def _seed_job(admin_engine, names: list[str]) -> uuid.UUID:
    job_id = uuid.uuid4()
    await _admin_exec(
        admin_engine,
        "INSERT INTO public.import_jobs (id, filename, raw_sha256, review_status, unresolved_names) "
        "VALUES (:i, 'test.zip', :s, 'pending_review', CAST(:n AS jsonb))",
        {"i": str(job_id), "s": job_id.hex, "n": json.dumps(names, ensure_ascii=False)},
    )
    return job_id


async def test_resolve_supplier_create_writes_common_row():
    from app.routers.tcg_line_import import ResolveRequest, resolve_supplier

    async with _fresh() as (admin_engine, app_engine):
        job_id = await _seed_job(admin_engine, ["新規A"])
        async with _session(app_engine) as db:
            r = await resolve_supplier(
                str(job_id), ResolveRequest(display_name="新規A", action="create"), db
            )
            assert r.remaining_unresolved == []
            assert await _operator_value(db) in (None, "")
        rows = await _admin_exec(
            admin_engine, "SELECT tenant_id, supplier_code FROM public.suppliers WHERE line_name = '新規A'"
        )
        assert len(rows) == 1 and rows[0][0] is None and rows[0][1].startswith("SP-")


# assign は RLS と無関係に、既存コードが整数列へ文字列 id（str(sup[0])）を渡すため
# asyncpg の DataError で落ちる（段階②b 以前からの不具合。本便では直さない）。
# 直ったら XPASS になり、共通行への書込が通ることを確認できる。
@pytest.mark.xfail(reason="既存不具合: assign が str(id) を整数列に渡す（②b 対象外）", strict=False)
async def test_resolve_supplier_assign_writes_common_row():
    from app.routers.tcg_line_import import ResolveRequest, resolve_supplier

    async with _fresh() as (admin_engine, app_engine):
        await _seed_supplier(admin_engine, "既存", None, code="SP-90001", line_name="旧名")
        job_id = await _seed_job(admin_engine, ["新名B"])
        async with _session(app_engine) as db:
            r = await resolve_supplier(
                str(job_id),
                ResolveRequest(display_name="新名B", action="assign", supplier_code="SP-90001"),
                db,
            )
            assert r.remaining_unresolved == []
            assert await _operator_value(db) in (None, "")
        rows = await _admin_exec(
            admin_engine, "SELECT line_name FROM public.suppliers WHERE supplier_code = 'SP-90001'"
        )
        assert rows[0][0] == "新名B"


# ⑥ #3 運営の仕入先マスタ画面
async def test_super_admin_supplier_writes_reflect_on_common_rows():
    from app.routers import super_admin_suppliers as r
    from app.schemas.central_masters import (
        CentralSupplierCreate,
        CentralSupplierUpdate,
        SupplierExtractionRulesUpdate,
    )

    user = SimpleNamespace(id=1)
    async with _fresh() as (admin_engine, app_engine):
        async with _session(app_engine) as db:
            created = await r.create_supplier(CentralSupplierCreate(name="運営作成"), db=db, current_user=user)
            sid = created.id
            assert await _operator_value(db) in (None, "")
        rows = await _admin_exec(
            admin_engine, "SELECT tenant_id, supplier_code FROM public.suppliers WHERE id = :i", {"i": sid}
        )
        assert rows[0][0] is None and rows[0][1] == f"SP-{sid:05d}"

        async with _session(app_engine) as db:
            await r.update_supplier(sid, CentralSupplierUpdate(notes="更新後"), db=db)
        assert (await _admin_exec(admin_engine, "SELECT notes FROM public.suppliers WHERE id = :i", {"i": sid}))[0][0] == "更新後"

        async with _session(app_engine) as db:
            await r.update_supplier_extraction_rules(
                sid, SupplierExtractionRulesUpdate(extraction_notes="ルール"), db=db
            )
        assert (
            await _admin_exec(admin_engine, "SELECT extraction_notes FROM public.suppliers WHERE id = :i", {"i": sid})
        )[0][0] == "ルール"

        async with _session(app_engine) as db:
            await r.delete_supplier(sid, db=db)
        assert (await _admin_exec(admin_engine, "SELECT is_active FROM public.suppliers WHERE id = :i", {"i": sid}))[0][0] is False

        # CSV 取込 commit（新規 1 件 + 既存コード更新 1 件）
        existing = await _seed_supplier(admin_engine, "CSV既存", None, code="SP-90010")
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=list(r._CSV_EXPORT_COLS))
        w.writeheader()
        blank = {c: "" for c in r._CSV_EXPORT_COLS}
        w.writerow({**blank, "name": "CSV新規", "supplier_type": "corporate"})
        w.writerow({**blank, "supplier_code": "SP-90010", "notes": "CSV更新"})
        raw = buf.getvalue().encode("utf-8")
        async with _session(app_engine) as db:
            res = await r.import_suppliers_commit(
                file=UploadFile(filename="s.csv", file=io.BytesIO(raw)),
                digest=hashlib.sha256(raw).hexdigest(),
                db=db,
            )
            assert (res["inserted"], res["updated"]) == (1, 1)
            assert await _operator_value(db) in (None, "")
        assert (await _admin_exec(admin_engine, "SELECT notes FROM public.suppliers WHERE id = :i", {"i": existing}))[0][0] == "CSV更新"
        rows = await _admin_exec(admin_engine, "SELECT tenant_id FROM public.suppliers WHERE name = 'CSV新規'")
        assert len(rows) == 1 and rows[0][0] is None


# ⑦ #4 名寄せ CLI
async def test_link_pending_updates_common_supplier_line_name():
    from app.services import line_source_names as lsn

    name = "名寄せ対象"
    sha = "a" * 64
    job_id = uuid.uuid4()
    async with _fresh() as (admin_engine, app_engine):
        sid = await _seed_supplier(admin_engine, "名寄せ先", None, code="SP-90002", line_name="別名")
        messages = [{"display_name": name, "timestamp": "2026-10-01 12:00:00", "body": "x"}]
        await _admin_exec(
            admin_engine,
            "INSERT INTO public.import_jobs (id, filename, raw_sha256, review_status, pending_messages) "
            "VALUES (:i, 'test.zip', :s, 'pending_review', CAST(:m AS jsonb))",
            {"i": str(job_id), "s": sha, "m": json.dumps(messages, ensure_ascii=False)},
        )
        data = {
            "import_job_id": str(job_id),
            "android_sha256": sha,
            "name_hash": lsn.digest(name),
            "supplier_code": "SP-90002",
        }
        # 履歴証明（長文 80 字以上の突合）は本試験の対象外なので差し替える
        with patch.object(lsn, "history_proof", lambda *a, **k: "proof"):
            async with _session(app_engine) as db:
                out = await lsn.link_pending(db, data)
                assert out["status"] == "linked"
                assert await _operator_value(db) in (None, "")
        rows = await _admin_exec(admin_engine, "SELECT line_name FROM public.suppliers WHERE id = :i", {"i": sid})
        assert rows[0][0] == name


# ⑧ #6 発注の仕入先複製（自社の行として作る）
async def test_purchase_order_supplier_copy_is_own_tenant_row():
    from sqlalchemy import text

    from app.auth.dependencies import set_tenant_context
    from app.routers import purchase_orders as po

    async with _fresh() as (admin_engine, app_engine):
        common_id = await _seed_supplier(admin_engine, "共通先", None)
        async with _session(app_engine) as db:
            await set_tenant_context(db, _TENANT_A)
            # 通常は照合 SELECT が元の共通行自身に一致して INSERT に届かない。
            # INSERT 文そのものの RLS 適合を見るため、照合 SELECT だけ空振りさせる。
            orig_execute = db.execute

            async def execute(stmt, *a, **k):
                if str(stmt).startswith("SELECT id FROM suppliers WHERE"):
                    return await orig_execute(text("SELECT id FROM suppliers WHERE false"))
                return await orig_execute(stmt, *a, **k)

            db.execute = execute
            new_id = await po._resolve_tenant_supplier_id(db, common_id, _TENANT_A)
            db.execute = orig_execute
            await db.commit()
        rows = await _admin_exec(
            admin_engine, "SELECT tenant_id, supplier_code FROM public.suppliers WHERE id = :i", {"i": new_id}
        )
        assert rows[0][0] == _TENANT_A and rows[0][1] is None


# ⑨ 例外で終わっても operator が残らない
async def test_operator_flag_cleared_even_when_path_raises():
    from app.routers import super_admin_suppliers as r
    from app.routers.tcg_line_import import ResolveRequest, resolve_supplier

    async with _fresh() as (admin_engine, app_engine):
        job_id = uuid.uuid4()
        await _admin_exec(
            admin_engine,
            "INSERT INTO public.import_jobs (id, filename, raw_sha256, review_status, unresolved_names) "
            "VALUES (:i, 'test.zip', :s, 'pending_review', CAST('[\"未知\"]' AS jsonb))",
            {"i": str(job_id), "s": job_id.hex},
        )
        async with _session(app_engine) as db:
            with pytest.raises(HTTPException):
                await resolve_supplier(
                    str(job_id),
                    ResolveRequest(display_name="未知", action="assign", supplier_code="SP-NONE"),
                    db,
                )
            assert await _operator_value(db) in (None, "")
            with pytest.raises(HTTPException):
                await r.delete_supplier(999999, db=db)
            assert await _operator_value(db) in (None, "")
