"""自社ログインの監査記録が、会社の指定が空の接続でも書けることの試験（便5 追補）。

本番と同じ作り方（rls_bootstrap.bootstrap_tenant_schema）でテナント 991 を作り、
`_record_auth_audit` が会社を指定してから書き、書いたら空に戻すことを確かめる。

PostgreSQL 専用。RLS_TEST_DATABASE_URL が無ければ skip（ローカル pytest は SQLite）。
"""

from __future__ import annotations

import os
from typing import Optional

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.auth.dependencies import clear_tenant_context
from app.routers.auth import _record_auth_audit
from app.services.audit import record_audit_log
from tests.rls_bootstrap import bootstrap_tenant_schema, tenant_schema_lock

_RLS_DB_URL: Optional[str] = os.getenv("RLS_TEST_DATABASE_URL")
_ADMIN_URL: str = os.getenv(
    "RLS_ADMIN_DATABASE_URL",
    "postgresql+asyncpg://jarvis:testpass@localhost:5432/jarvis_test_db",
)

_TENANT_ID = 991
_SCHEMA = "tenant_991"

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


async def _remove_test_tenant_rows(conn) -> None:
    """この試験のテナント（id 991）が入れた行だけを消す。他のテナントの行には触れない。"""
    await conn.execute(text(f"DROP SCHEMA IF EXISTS {_SCHEMA} CASCADE"))
    exists = await conn.scalar(text("SELECT to_regclass('public.tenant_settings')"))
    if exists is not None:
        await conn.execute(text("DELETE FROM public.tenant_settings WHERE tenant_id = :t"), {"t": _TENANT_ID})
    exists = await conn.scalar(text("SELECT to_regclass('public.tenants')"))
    if exists is not None:
        await conn.execute(text("DELETE FROM public.tenants WHERE id = :t"), {"t": _TENANT_ID})


@pytest_asyncio.fixture(scope="module", loop_scope="module", autouse=True)
async def setup_schema(admin_engine):
    # 本物の定義（backend/app/services/tenant.py）でテナント 991 を作る。本番の表の作り方を試験に書き写さない
    async with tenant_schema_lock(admin_engine, _TENANT_ID):
        async with admin_engine.begin() as conn:
            await _remove_test_tenant_rows(conn)
        await bootstrap_tenant_schema(admin_engine, _TENANT_ID)
        async with admin_engine.begin() as conn:
            # 本物の作り方の権限付与は失敗すると全部付かないため、ここで付け直す（tenant.py:1691-1709）
            await conn.execute(text(f"GRANT USAGE ON SCHEMA {_SCHEMA} TO salesanchor_app"))
            await conn.execute(text(f"GRANT SELECT, INSERT ON {_SCHEMA}.audit_logs TO salesanchor_app"))
            await conn.execute(text(
                f"GRANT USAGE, SELECT ON SEQUENCE {_SCHEMA}.audit_logs_id_seq TO salesanchor_app"
            ))
        yield
        async with admin_engine.begin() as conn:
            await _remove_test_tenant_rows(conn)


async def _count(admin_engine, event: str) -> int:
    async with admin_engine.connect() as conn:
        result = await conn.execute(
            text(f"SELECT count(*) FROM {_SCHEMA}.audit_logs WHERE new_data->>'event' = :e"),
            {"e": event},
        )
        return result.scalar_one()


@pytest.mark.asyncio(loop_scope="module")
async def test_a_empty_tenant_context_fails_like_production(app_engine):
    """a: 会社の指定が空のまま書くと、本番と同じ失敗になる（再現）。"""
    async with AsyncSession(app_engine) as db:
        await clear_tenant_context(db)
        with pytest.raises(Exception) as exc:
            await record_audit_log(
                db,
                tenant_id=_TENANT_ID,
                user_id=1,
                action="create",
                table_name="webauthn_credentials",
                record_id=1,
                new_data={"event": "test_a"},
            )
        assert "invalid input syntax for type integer" in str(exc.value)
        await db.rollback()


@pytest.mark.asyncio(loop_scope="module")
async def test_b_helper_writes_and_resets_context(app_engine, admin_engine):
    """b: 直したあと。空の接続からでも書け、書いたあと app.tenant_id は空に戻る。"""
    async with AsyncSession(app_engine) as db:
        await clear_tenant_context(db)
        await _record_auth_audit(
            db,
            tenant_id=_TENANT_ID,
            user_id=1,
            action="create",
            table_name="webauthn_credentials",
            record_id=1,
            new_data={"event": "test_b"},
        )
        current = (
            await db.execute(text("SELECT current_setting('app.tenant_id', true)"))
        ).scalar_one()
        assert current in ("", None)
        await db.commit()
    assert await _count(admin_engine, "test_b") == 1


@pytest.mark.asyncio(loop_scope="module")
async def test_c_never_set_connection_also_works(app_engine, admin_engine):
    """c: app.tenant_id を一度も設定していない新しい接続でも書ける（:822 の形）。"""
    async with AsyncSession(app_engine) as db:
        await _record_auth_audit(
            db,
            tenant_id=_TENANT_ID,
            user_id=1,
            action="update",
            table_name="webauthn_credentials",
            record_id=1,
            new_data={"event": "test_c"},
        )
        await db.commit()
    assert await _count(admin_engine, "test_c") == 1
