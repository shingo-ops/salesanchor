"""public.tenant_llm_budgets・public.tenant_settings に RLS（型C）（ADR-1067 段階④ 便④-5）。

使い捨て DB を試験ごとに作り（共有の検証用 DB に表を足さない）、本物の migration を本番と同じ順で当てて、
アプリ接続役（NOBYPASSRLS）で確かめる。読む＝全行、書く＝自社の会社文脈か運営文脈だけ。
会社番号は 966（自社）/ 967（他社）/ 965（会社を作る処理の試験だけ）。
"""
from __future__ import annotations

import os
import types
import uuid
from contextlib import asynccontextmanager
from decimal import Decimal
from unittest.mock import AsyncMock, patch
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

_TENANT_A = 966
_TENANT_B = 967
_TENANT_NEW = 965
# 表を作る・列を足す移行（本番と同じ順）
_BASE_MIGRATIONS = [
    "056_add_suppliers_type_and_promote_public.sql",
    "062_create_inventory_movements_and_budget.sql",
    "066_add_tenant_llm_budgets_notification_dedupe.sql",
    "20260604_220000_create_translation_glossary.sql",
    "070_add_spreadsheet_phase.sql",
    "080_phase_b_migration.sql",
    "20260604_050000_add_tenant_policy_columns.sql",
]
_MIGRATION = "20261107_160000_add_tenant_budget_settings_rls.sql"
_GRANT_DDL = """
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO salesanchor_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO salesanchor_app;
"""
_TABLES = ["tenant_llm_budgets", "tenant_settings"]

# 表ごとの「他社の行を INSERT」「UPDATE」の文
_INSERT_OTHER = {
    "tenant_llm_budgets": "INSERT INTO public.tenant_llm_budgets (tenant_id) VALUES (967)",
    "tenant_settings": "INSERT INTO public.tenant_settings (tenant_id, spreadsheet_phase) VALUES (967, 'B')",
}
_UPDATE_OTHER = {
    "tenant_llm_budgets": "UPDATE public.tenant_llm_budgets SET monthly_budget_usd = 99 WHERE tenant_id = :t",
    "tenant_settings": "UPDATE public.tenant_settings SET spreadsheet_phase = 'A' WHERE tenant_id = :t",
}


def _with_db(url: str, name: str) -> str:
    return urlunsplit(urlsplit(url)._replace(path="/" + name))


@asynccontextmanager
async def _fresh():
    """使い捨て DB を作り (admin_engine, app_engine) を返す。終了時に DROP。"""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    control = create_async_engine(ADMIN_PG_URL, isolation_level="AUTOCOMMIT")
    name = "tbs_rls_" + uuid.uuid4().hex[:12]
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
                    "VALUES (965, 'tenant_965', 'T965', 'T965', TRUE), "
                    "(966, 'tenant_966', 'T966', 'T966', TRUE), "
                    "(967, 'tenant_967', 'T967', 'T967', TRUE)"
                )
            )
        # 表を本物の migration で作る（表の定義を試験に書き写さない）
        for mig in _BASE_MIGRATIONS:
            await _apply_migration(admin_engine, mig)
        async with admin_engine.begin() as conn:
            raw = await conn.get_raw_connection()
            await raw.driver_connection.execute(_GRANT_DDL)
            await conn.execute(
                text(
                    "INSERT INTO public.tenant_llm_budgets (tenant_id, monthly_budget_usd) "
                    "VALUES (966, 10), (967, 20)"
                )
            )
            await conn.execute(
                text(
                    "INSERT INTO public.tenant_settings (tenant_id, spreadsheet_phase) "
                    "VALUES (966, 'B'), (967, 'B')"
                )
            )
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
        await conn.execute(text("SELECT set_config('app.tenant_id', '', true)"))
        await conn.execute(text("SELECT set_config('app.is_operator', 'true', true)"))
    return conn, trans


def _sqlstate(exc) -> str | None:
    orig = exc.orig
    return getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)


async def _ids(conn, table: str) -> list[int]:
    from sqlalchemy import text

    rows = (
        await conn.execute(text(f"SELECT tenant_id FROM public.{table} ORDER BY tenant_id"))
    ).all()
    return [r[0] for r in rows]


async def _fresh_conn_setting(app_engine, name: str):
    """プールから新しく取った接続で current_setting を読む（接続に設定が残っていないかの確認）。"""
    from sqlalchemy import text

    conn = await app_engine.connect()
    try:
        val = (await conn.execute(text(f"SELECT current_setting('{name}', true)"))).scalar()
        await conn.rollback()
        return val
    finally:
        await conn.close()


def _make_session(app_engine):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    return async_sessionmaker(app_engine, expire_on_commit=False)()


async def _no_context_session(app_engine):
    """get_db の後と同じ「文脈なし」の session（SET を空にして commit）。"""
    from sqlalchemy import text

    session = _make_session(app_engine)
    await session.execute(text("SET app.tenant_id = ''"))
    await session.execute(text("SET app.is_operator = ''"))
    await session.commit()
    return session


# ① 読取は全行: 文脈なし・他社の文脈・空文字の文脈（22P02 にならない）でも 2 行とも見える
@pytest.mark.parametrize("table", _TABLES)
async def test_select_sees_all_rows_in_any_context(table):
    from sqlalchemy import text

    async with _fresh() as (_admin, app_engine):
        expected = [_TENANT_A, _TENANT_B]
        conn, trans = await _ctx_conn(app_engine, None)
        try:
            assert await _ids(conn, table) == expected
        finally:
            await trans.rollback()
            await conn.close()
        conn, trans = await _ctx_conn(app_engine, _TENANT_B)
        try:
            assert await _ids(conn, table) == expected
        finally:
            await trans.rollback()
            await conn.close()
        conn = await app_engine.connect()
        try:
            await conn.execute(text("SET app.tenant_id = ''"))
            assert await _ids(conn, table) == expected
            await conn.execute(text("RESET app.tenant_id"))
            await conn.rollback()
        finally:
            await conn.close()


# ② 他社の tenant_id で INSERT すると 42501（既に行があるので主キーより先に RLS で止まる）
@pytest.mark.parametrize("table", _TABLES)
async def test_insert_other_tenant_rejected(table):
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError

    async with _fresh() as (_admin, app_engine):
        conn, trans = await _ctx_conn(app_engine, _TENANT_A)
        try:
            with pytest.raises(DBAPIError) as exc_info:
                await conn.execute(text(_INSERT_OTHER[table]))
            assert _sqlstate(exc_info.value) == "42501"
        finally:
            await trans.rollback()
            await conn.close()


# ③ 他社の行への UPDATE・DELETE は 0 行（他社の行は元のまま 1 行）
@pytest.mark.parametrize("table", _TABLES)
async def test_update_delete_other_tenant_rows_affect_nothing(table):
    from sqlalchemy import text

    async with _fresh() as (admin_engine, app_engine):
        conn, trans = await _ctx_conn(app_engine, _TENANT_A)
        try:
            r = await conn.execute(text(_UPDATE_OTHER[table]), {"t": _TENANT_B})
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
        if table == "tenant_llm_budgets":
            vals = await _admin_exec(
                admin_engine,
                "SELECT monthly_budget_usd FROM public.tenant_llm_budgets WHERE tenant_id = :t",
                {"t": _TENANT_B},
            )
            assert vals == [(Decimal("20"),)] or [float(v[0]) for v in vals] == [20.0]
        else:
            vals = await _admin_exec(
                admin_engine,
                "SELECT spreadsheet_phase FROM public.tenant_settings WHERE tenant_id = :t",
                {"t": _TENANT_B},
            )
            assert vals == [("B",)]


# ④ 運営の文脈: 他社の行の UPDATE が 1 行
@pytest.mark.parametrize("table", _TABLES)
async def test_operator_context_can_update_other_tenant_row(table):
    from sqlalchemy import text

    async with _fresh() as (_admin, app_engine):
        conn, trans = await _ctx_conn(app_engine, None, operator=True)
        try:
            r = await conn.execute(text(_UPDATE_OTHER[table]), {"t": _TENANT_B})
            assert r.rowcount == 1
        finally:
            await trans.rollback()
            await conn.close()


# ⑤ 同じ移行をもう一度当てても通り、ポリシーは各表 4 本のまま
@pytest.mark.parametrize("table", _TABLES)
async def test_migration_idempotent_four_policies(table):
    async with _fresh() as (admin_engine, _app):
        await _apply_migration(admin_engine, _MIGRATION)
        flags = await _admin_exec(
            admin_engine,
            "SELECT relrowsecurity, relforcerowsecurity FROM pg_class "
            f"WHERE oid = to_regclass('public.{table}')",
        )
        assert tuple(flags[0]) == (True, True)
        n = (
            await _admin_exec(
                admin_engine,
                "SELECT count(*) FROM pg_policies WHERE schemaname = 'public' AND tablename = :tn",
                {"tn": table},
            )
        )[0][0]
        assert n == 4


# ⑥ 自社の行の tenant_id を他社へ付け替える UPDATE は 42501
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


# ⑦ 予算の保存（運営）: 文脈なしの session から upsert_budget を直に呼んで保存でき、運営の印が接続に残らない
async def test_upsert_budget_operator_entry():
    from app.routers.super_admin_llm_budget import LLMBudgetUpdate, upsert_budget

    async with _fresh() as (admin_engine, app_engine):
        session = await _no_context_session(app_engine)
        try:
            res = await upsert_budget(
                _TENANT_B,
                LLMBudgetUpdate(
                    monthly_budget_usd=Decimal("25.00"), hard_stop=True, notify_admin=True
                ),
                db=session,
            )
            assert Decimal(str(res.monthly_budget_usd)) == Decimal("25.00")
        finally:
            await session.close()
        rows = await _admin_exec(
            admin_engine,
            "SELECT monthly_budget_usd FROM public.tenant_llm_budgets WHERE tenant_id = :t",
            {"t": _TENANT_B},
        )
        assert Decimal(str(rows[0][0])) == Decimal("25.00")
        # 同じ接続が戻る（pool_size=1）。運営の印が残っていない
        assert await _fresh_conn_setting(app_engine, "app.is_operator") == ""


# ⑧ 段階の切替（運営）: record_audit_log は差し替えない。使い捨て DB には tenant_967.audit_logs が無いので
# 本物の呼び出しが失敗し、savepoint の道を通る（記録の失敗で切替が消えないことの確かめ）
async def test_switch_phase_operator_entry():
    from app.routers.super_admin_phase_switch import PhaseSwitchRequest, switch_phase_endpoint

    async with _fresh() as (admin_engine, app_engine):
        session = await _no_context_session(app_engine)
        try:
            res = await switch_phase_endpoint(
                _TENANT_B,
                PhaseSwitchRequest(phase="A"),
                db=session,
                current_user=types.SimpleNamespace(id=1),
            )
            assert res.phase == "A"
        finally:
            await session.close()
        rows = await _admin_exec(
            admin_engine,
            "SELECT spreadsheet_phase FROM public.tenant_settings WHERE tenant_id = :t",
            {"t": _TENANT_B},
        )
        assert rows == [("A",)]
        assert await _fresh_conn_setting(app_engine, "app.is_operator") == ""


# ⑨ 翻訳の見張りの通知: 文脈なしの session から通知でき、最終通知時刻が書かれ、会社の文脈が接続に残らない
async def test_translation_monitor_notify_writes_debounce():
    from sqlalchemy import text

    from app.services.translation_monitor import (
        TranslationHealthSnapshot,
        notify_translation_anomaly,
    )

    async with _fresh() as (admin_engine, app_engine):
        before = await _admin_exec(
            admin_engine,
            "SELECT last_translation_monitor_notified_at FROM public.tenant_llm_budgets WHERE tenant_id = :t",
            {"t": _TENANT_A},
        )
        assert before == [(None,)]
        session = await _no_context_session(app_engine)
        try:
            with patch(
                "app.services.translation_monitor._post_webhook",
                new=AsyncMock(return_value=True),
            ):
                sent = await notify_translation_anomaly(
                    session,
                    _TENANT_A,
                    TranslationHealthSnapshot(100, 30, 40, 0.30, 0.40),
                    tenant_code="t966",
                )
            assert sent is True
            # 取引が壊れていない
            assert (await session.execute(text("SELECT 1"))).scalar() == 1
        finally:
            await session.close()
        after = await _admin_exec(
            admin_engine,
            "SELECT last_translation_monitor_notified_at FROM public.tenant_llm_budgets WHERE tenant_id = :t",
            {"t": _TENANT_A},
        )
        assert after[0][0] is not None
        assert await _fresh_conn_setting(app_engine, "app.tenant_id") == ""


# ⑩ 会社を作る処理: 新しい会社の app.tenant_id を張ってから tenant_settings に INSERT できる
# （backend/app/services/tenant.py の会社を作る処理と同じ文）
async def test_tenant_creation_settings_insert():
    from sqlalchemy import text

    async with _fresh() as (admin_engine, app_engine):
        conn = await app_engine.connect()
        try:
            async with conn.begin():
                await conn.execute(
                    text("SELECT set_config('app.tenant_id', :t, true)"), {"t": str(_TENANT_NEW)}
                )
                await conn.execute(
                    text(
                        "INSERT INTO public.tenant_settings (tenant_id, spreadsheet_phase, "
                        "inventory_agg_filter, agg_price_threshold_jpy, agg_qty_threshold, "
                        "quote_validity_days, default_currency, document_language, duty_incoterms, "
                        "issue_mode) VALUES (965, 'B', 'none', 0, 0, 1, 'JPY', 'en', 'DAP', 'pdf') "
                        "ON CONFLICT (tenant_id) DO NOTHING"
                    )
                )
        finally:
            await conn.close()
        rows = await _admin_exec(
            admin_engine,
            "SELECT count(*) FROM public.tenant_settings WHERE tenant_id = :t",
            {"t": _TENANT_NEW},
        )
        assert rows == [(1,)]
