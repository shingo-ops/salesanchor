"""秘書の「予定のカルテ」で Meet を付けてよいかを読む件の試験（ADR-1078）。

入れ子の取引の中で読み、失敗しても外の取引（commit と会社の文脈の張り直し）が壊れないことを確かめる。
実 PostgreSQL（RLS_ADMIN_DATABASE_URL か TEST_PG_URL と RLS_TEST_DATABASE_URL）があるときだけ動く。
"""
from __future__ import annotations

import os

import pytest
from cryptography.fernet import Fernet

from tests.rls_bootstrap import (
    _apply_migration_on_conn,
    bootstrap_tenant_schema,
    public_bootstrap_lock,
)

os.environ.setdefault("METADATA_FERNET_KEY", Fernet.generate_key().decode())

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

_TENANT = 989
_OWNER = 98901  # Google をつないだ本人
_OTHER = 98902  # つないでいない人

_MIGRATIONS = (
    "076_add_google_calendar_config.sql",
    "077_calendar_sync_mode_and_webhook_subscriptions.sql",
    "20260606_010000_add_google_drive_config.sql",
    "20261016_010000_add_google_config_rls.sql",
)


async def _cleanup(admin_engine) -> None:
    from sqlalchemy import text

    async with admin_engine.begin() as conn:
        await conn.execute(
            text("DELETE FROM public.tenant_google_calendar_config WHERE tenant_id = :t"),
            {"t": _TENANT},
        )
        await conn.execute(
            text("DELETE FROM public.users WHERE id IN (:a, :b)"),
            {"a": _OWNER, "b": _OTHER},
        )


async def _setup():
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool

    admin_engine = create_async_engine(ADMIN_PG_URL, echo=False)
    app_engine = create_async_engine(APP_PG_URL, echo=False, poolclass=NullPool)
    await bootstrap_tenant_schema(admin_engine, _TENANT)
    async with public_bootstrap_lock(admin_engine):
        async with admin_engine.begin() as conn:
            for filename in _MIGRATIONS:
                await _apply_migration_on_conn(conn, filename, schema_name=None)
    async with admin_engine.begin() as conn:
        for uid in (_OWNER, _OTHER):
            await conn.execute(
                text(
                    "INSERT INTO public.users ("
                    " id, tenant_id, username, email, full_name,"
                    " role, is_active, is_super_admin, locale, theme)"
                    " VALUES (:id, :t, :uname, :email, 'Karte Meet', 'admin',"
                    "         TRUE, FALSE, 'ja', 'light')"
                    " ON CONFLICT (id) DO NOTHING"
                ),
                {
                    "id": uid,
                    "t": _TENANT,
                    "uname": f"karte-meet-{uid}",
                    "email": f"karte-meet-{uid}@example.com",
                },
            )
        await conn.execute(
            text("DELETE FROM public.tenant_google_calendar_config WHERE tenant_id = :t"),
            {"t": _TENANT},
        )
        await conn.execute(
            text(
                "INSERT INTO public.tenant_google_calendar_config"
                " (tenant_id, sync_mode, connected_by_user_id,"
                "  access_token_encrypted, refresh_token_encrypted, calendar_id)"
                " VALUES (:t, 'bidirectional', :u, 'x', 'y', 'primary')"
            ),
            {"t": _TENANT, "u": _OWNER},
        )
    factory = async_sessionmaker(app_engine, class_=AsyncSession, expire_on_commit=False)
    return admin_engine, app_engine, factory


async def _teardown(admin_engine, app_engine) -> None:
    try:
        await _cleanup(admin_engine)
    finally:
        await admin_engine.dispose()
        await app_engine.dispose()


async def test_read_meet_available_owner_true_other_false():
    from app.auth.dependencies import set_tenant_context
    from app.routers import assistant

    admin_engine, app_engine, factory = await _setup()
    try:
        async with factory() as db:
            await set_tenant_context(db, _TENANT)
            assert await assistant._read_meet_available(db, _TENANT, _OWNER) is True
            assert await assistant._read_meet_available(db, _TENANT, _OTHER) is False
    finally:
        await _teardown(admin_engine, app_engine)


async def test_read_meet_available_failed_sql_keeps_transaction_usable(monkeypatch):
    from sqlalchemy import text

    from app.auth.dependencies import reset_tenant_context, set_tenant_context
    from app.routers import assistant

    async def _failing(db, tenant_id, user_id):
        await db.execute(text("SELECT * FROM no_such_table_adr1078"))
        return True

    admin_engine, app_engine, factory = await _setup()
    try:
        async with factory() as db:
            await set_tenant_context(db, _TENANT)
            monkeypatch.setattr(assistant, "can_add_meet", _failing)
            assert await assistant._read_meet_available(db, _TENANT, _OWNER) is False
            # 失敗した文が外の取引を中断のまま残さない
            await db.commit()
            await reset_tenant_context(db, _TENANT)
            monkeypatch.undo()
            assert await assistant.can_add_meet(db, _TENANT, _OWNER) is True
    finally:
        await _teardown(admin_engine, app_engine)
