"""ADR-1056 段2 / K4: チャット秘書の名前探しがテナントをまたがない（本物の PostgreSQL・RLS）と、
入口の migration が 2 回流しても失敗しないことの試験。

PostgreSQL 専用。RLS_TEST_DATABASE_URL が無ければ skip（ローカル pytest は SQLite）。
土台は tests/rls_bootstrap.py・tests/test_rls_passkey_enroll_skips.py と同じ書き方。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.auth.dependencies import set_tenant_context
from app.services.secretary_resolve import resolve_names
from tests.rls_bootstrap import bootstrap_tenant_schema

_RLS_DB_URL: Optional[str] = os.getenv("RLS_TEST_DATABASE_URL")
_ADMIN_URL: str = os.getenv(
    "RLS_ADMIN_DATABASE_URL",
    "postgresql+asyncpg://jarvis:testpass@localhost:5432/jarvis_test_db",
)
_MIGRATION = (
    Path(__file__).resolve().parents[2] / "migrations" / "20261101_120000_enable_secretary_chat_tenant4.sql"
)
_TENANT_A = 9561
_TENANT_B = 9562

pytestmark = pytest.mark.skipif(
    not _RLS_DB_URL,
    reason="RLS_TEST_DATABASE_URL 未設定のため skip（PostgreSQL 専用）",
)


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def admin_engine():
    eng = create_async_engine(_ADMIN_URL, echo=False)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def app_engine():
    assert _RLS_DB_URL
    eng = create_async_engine(_RLS_DB_URL, echo=False)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture(scope="module", loop_scope="module", autouse=True)
async def seeded(admin_engine):
    for tid in (_TENANT_A, _TENANT_B):
        await bootstrap_tenant_schema(admin_engine, tid)
    async with admin_engine.begin() as conn:
        for tid, schema in ((_TENANT_A, f"tenant_{_TENANT_A:03d}"), (_TENANT_B, f"tenant_{_TENANT_B:03d}")):
            await conn.execute(text(f"SET LOCAL search_path = {schema}, public"))
            await conn.execute(text("SELECT set_config('app.is_operator', 'true', true)"))
            lead_id = (
                await conn.execute(
                    text("INSERT INTO leads (tenant_id, customer_name) VALUES (:t, '秘書テスト') RETURNING id"),
                    {"t": tid},
                )
            ).scalar_one()
            await conn.execute(
                text(
                    "INSERT INTO companies (tenant_id, company_code, lead_id, name, normalized_name) "
                    "VALUES (:t, :c, :l, '秘書テスト商事', '秘書テスト商事')"
                ),
                {"t": tid, "c": f"SEC{tid}", "l": lead_id},
            )
            await conn.execute(
                text(
                    "INSERT INTO contacts (tenant_id, company_id, contact_code, lead_id, surname, display_name) "
                    "SELECT :t, id, :c, :l, '佐藤', '佐藤 秘書' FROM companies WHERE tenant_id = :t"
                ),
                {"t": tid, "c": f"SECC{tid}", "l": lead_id},
            )
    yield


async def _resolve_as(app_engine, tenant_id: int):
    async with app_engine.connect() as conn:
        from sqlalchemy.ext.asyncio import AsyncSession

        session = AsyncSession(bind=conn)
        await set_tenant_context(session, tenant_id)
        try:
            return await resolve_names(session, tenant_id, "秘書テスト", "佐藤")
        finally:
            await session.rollback()
            await session.close()


@pytest.mark.asyncio(loop_scope="module")
async def test_resolve_returns_only_own_tenant(app_engine, admin_engine):
    a = await _resolve_as(app_engine, _TENANT_A)
    b = await _resolve_as(app_engine, _TENANT_B)
    assert len(a["companies"]) == 1 and len(a["contacts"]) == 1
    assert len(b["companies"]) == 1 and len(b["contacts"]) == 1
    async with admin_engine.connect() as conn:
        ids = {}
        for tid in (_TENANT_A, _TENANT_B):
            await conn.execute(text(f"SET search_path = tenant_{tid:03d}, public"))
            ids[tid] = (await conn.execute(text("SELECT id FROM companies"))).scalar_one()
    assert a["companies"][0]["id"] == ids[_TENANT_A]
    assert b["companies"][0]["id"] == ids[_TENANT_B]


@pytest.mark.asyncio(loop_scope="module")
async def test_migration_twice_does_not_fail(admin_engine):
    prereq = (_MIGRATION.parent / "20260627_120000_add_tenant_features_table.sql").read_text(encoding="utf-8")
    sql = _MIGRATION.read_text(encoding="utf-8")
    for script in (prereq, sql, sql):  # 入口の表を用意してから、本体を 2 回流す
        async with admin_engine.connect() as conn:
            raw = await conn.get_raw_connection()
            await raw.driver_connection.execute(script)
            await conn.commit()
    async with admin_engine.connect() as conn:
        n = (
            await conn.execute(
                text(
                    "SELECT COUNT(*) FROM public.tenant_features "
                    "WHERE tenant_id = 4 AND feature_key = 'secretary_chat' AND enabled"
                )
            )
        ).scalar_one()
    assert n == 1
