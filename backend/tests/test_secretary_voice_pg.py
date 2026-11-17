"""ADR-1080 便1: 秘書の声の移行 2 本と save_voice を本物の PostgreSQL で試す（design.md §9 の V10・V11・V12）。

PG（CI の使い捨て DB。pg fixture）。users の書込の守り（RLS）の移行を流した DB で、アプリの役割 salesanchor_app の
非同期の取引から、口と同じ save_voice を呼ぶ。テストデータはすべて架空。
"""

from __future__ import annotations

import asyncio
import os
import re

import pytest
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.services.llm_budget import USAGE_PURPOSES, USAGE_SDKS
from app.services.secretary_voice import VoiceNotSaved, read_voice, save_voice
from tests.test_secretary_rules_tables_pg import needs_ci_pg
from tests.test_tcg_work_matching_integration import MIGRATIONS
from tests.test_tcg_work_matching_integration import pg as pg  # noqa: F401  fixture
from tests.test_users_rls import _GRANT_DDL
from tests.test_users_rls import _MIGRATIONS as USERS_RLS_MIGRATIONS

USERS_MIGRATION = "20261117_100000_add_users_secretary_voice.sql"
LEDGER_MIGRATION = "20261117_100100_add_llm_usage_tts_characters.sql"


def _run_migration(cur, name):
    cur.execute((MIGRATIONS / name).read_text())


def _prepare(conn):
    """管理者の接続で users の書込の守りと権限を整え、会社 999・998 と利用者 999 を用意する。"""
    cur = conn.cursor()
    for name in USERS_RLS_MIGRATIONS:
        _run_migration(cur, name)
    cur.execute(_GRANT_DDL)
    cur.execute(
        "INSERT INTO public.tenants (id, tenant_code, tenant_name, company_name) "
        "VALUES (998, 'tenant_998', 'Test Tenant B', 'Test Tenant B') ON CONFLICT (id) DO NOTHING"
    )
    cur.execute(
        "INSERT INTO public.users (id, tenant_id, username, email, full_name, role) "
        "VALUES (999, 999, 'testuser999', 'test999@example.com', 'Test User A', 'admin') ON CONFLICT (id) DO NOTHING"
    )
    return cur


def _apply_both(cur):
    _run_migration(cur, USERS_MIGRATION)
    _run_migration(cur, LEDGER_MIGRATION)


def _shape(cur):
    cur.execute(
        "SELECT table_name, column_name, data_type FROM information_schema.columns "
        "WHERE table_schema = 'public' AND ((table_name = 'users' AND column_name = 'secretary_voice') "
        "OR (table_name = 'llm_usage_events' AND column_name = 'billed_characters')) ORDER BY 1, 2"
    )
    columns = cur.fetchall()
    cur.execute(
        "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint "
        "WHERE conrelid = 'public.llm_usage_events'::regclass "
        "AND conname IN ('llm_usage_events_purpose_check', 'llm_usage_events_sdk_check') ORDER BY 1"
    )
    return columns, cur.fetchall()


def _constraint_values(cur, conname):
    cur.execute(
        "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
        "WHERE conrelid = 'public.llm_usage_events'::regclass AND conname = %s",
        (conname,),
    )
    return set(re.findall(r"'([^']+)'", cur.fetchone()[0]))


def _engine(conn):
    url = make_url(os.environ["RLS_TEST_DATABASE_URL"]).set(
        database=conn.info.dbname, drivername="postgresql+asyncpg"
    )
    return create_async_engine(url, poolclass=NullPool)


@needs_ci_pg
def test_v10_migrations_are_idempotent(pg):  # noqa: F811
    conn, _, _ = pg
    cur = _prepare(conn)
    _apply_both(cur)
    first = _shape(cur)
    assert len(first[0]) == 2
    assert len(first[1]) == 2
    _apply_both(cur)
    assert _shape(cur) == first


@needs_ci_pg
def test_v12_ledger_value_sets_equal_python(pg):  # noqa: F811
    conn, _, _ = pg
    cur = _prepare(conn)
    _apply_both(cur)
    assert _constraint_values(cur, "llm_usage_events_purpose_check") == set(USAGE_PURPOSES)
    assert _constraint_values(cur, "llm_usage_events_sdk_check") == set(USAGE_SDKS)


@needs_ci_pg
def test_v11_save_voice_works_under_rls(pg):  # noqa: F811
    conn, _, _ = pg
    cur = _prepare(conn)
    _apply_both(cur)

    async def _save(tenant_id, voice):
        engine = _engine(conn)
        try:
            async with AsyncSession(engine, expire_on_commit=False) as db:
                await save_voice(db, user_id=999, tenant_id=tenant_id, voice=voice)
        finally:
            await engine.dispose()

    async def _read():
        engine = _engine(conn)
        try:
            async with AsyncSession(engine, expire_on_commit=False) as db:
                return await read_voice(db, 999)
        finally:
            await engine.dispose()

    assert asyncio.run(_read()) == "Charon"  # 未選択は既定

    asyncio.run(_save(999, "Aoede"))
    cur.execute("SELECT secretary_voice FROM public.users WHERE id = 999")
    assert cur.fetchone()[0] == "Aoede"
    assert asyncio.run(_read()) == "Aoede"

    # 別の会社の文脈では 0 行に当たり、失敗になって値は変わらない（守りが効いている）
    with pytest.raises(VoiceNotSaved):
        asyncio.run(_save(998, "Erinome"))
    cur.execute("SELECT secretary_voice FROM public.users WHERE id = 999")
    assert cur.fetchone()[0] == "Aoede"
