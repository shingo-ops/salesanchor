"""自社ログインの監査記録が、会社の指定が空の接続でも書けることの試験（便5 追補）。

本番の tenant_NNN.audit_logs の行の制限（NULLIF なし）と同じ式を持つ表を作り、
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


@pytest_asyncio.fixture(scope="module", loop_scope="module", autouse=True)
async def setup_schema(admin_engine):
    async with admin_engine.begin() as conn:
        await conn.execute(text(f"DROP SCHEMA IF EXISTS {_SCHEMA} CASCADE"))
        await conn.execute(text(f"CREATE SCHEMA {_SCHEMA}"))
        await conn.execute(text(f"""
            CREATE TABLE {_SCHEMA}.audit_logs (
                id         BIGSERIAL PRIMARY KEY,
                tenant_id  INTEGER NOT NULL,
                user_id    INTEGER NOT NULL,
                action     VARCHAR NOT NULL,
                table_name VARCHAR NOT NULL,
                record_id  INTEGER,
                old_data   JSONB,
                new_data   JSONB,
                created_at TIMESTAMPTZ DEFAULT now()
            )
        """))
        await conn.execute(text(f"ALTER TABLE {_SCHEMA}.audit_logs ENABLE ROW LEVEL SECURITY"))
        # 本番と同じ式（NULLIF を付けない）
        await conn.execute(text(f"""
            CREATE POLICY tenant_isolation ON {_SCHEMA}.audit_logs
                USING (tenant_id = (current_setting('app.tenant_id', true))::integer)
        """))
        await conn.execute(text(f"GRANT USAGE ON SCHEMA {_SCHEMA} TO salesanchor_app"))
        await conn.execute(text(f"GRANT SELECT, INSERT ON {_SCHEMA}.audit_logs TO salesanchor_app"))
        await conn.execute(text(
            f"GRANT USAGE, SELECT ON SEQUENCE {_SCHEMA}.audit_logs_id_seq TO salesanchor_app"
        ))
    yield
    async with admin_engine.begin() as conn:
        await conn.execute(text(f"DROP SCHEMA IF EXISTS {_SCHEMA} CASCADE"))


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
