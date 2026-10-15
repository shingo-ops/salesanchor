"""Google 接続設定 2 表の会社別 RLS（ADR-1018 段階②a）。

対象: public.tenant_google_calendar_config / public.tenant_google_drive_config
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from cryptography.fernet import Fernet

from tests.rls_bootstrap import (
    _apply_migration,
    bootstrap_tenant_schema,
    public_bootstrap_lock,
)

os.environ.setdefault("METADATA_FERNET_KEY", Fernet.generate_key().decode())
os.environ.setdefault("GOOGLE_CALENDAR_CLIENT_ID", "test-client-id.apps.googleusercontent.com")
os.environ.setdefault("GOOGLE_CALENDAR_CLIENT_SECRET", "test-secret")
os.environ.setdefault("GOOGLE_CALENDAR_REDIRECT_URI", "https://api.example.com/callback")

ADMIN_PG_URL = (
    os.getenv("RLS_ADMIN_DATABASE_URL")
    or os.getenv("TEST_PG_URL")
)
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

_TENANT_A = 980
_TENANT_B = 981
_TABLES = ("tenant_google_calendar_config", "tenant_google_drive_config")
_MIGRATIONS = (
    "076_add_google_calendar_config.sql",
    "20260606_010000_add_google_drive_config.sql",
    "20261016_010000_add_google_config_rls.sql",
)


async def _setup():
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.pool import NullPool

    admin_engine = create_async_engine(ADMIN_PG_URL, echo=False)
    app_engine = create_async_engine(APP_PG_URL, echo=False, poolclass=NullPool)
    await bootstrap_tenant_schema(admin_engine, _TENANT_A)
    await bootstrap_tenant_schema(admin_engine, _TENANT_B)
    async with public_bootstrap_lock(admin_engine):
        for filename in _MIGRATIONS:
            await _apply_migration(admin_engine, filename)
    await _cleanup(admin_engine)
    return admin_engine, app_engine


async def _cleanup(admin_engine):
    from sqlalchemy import text

    async with admin_engine.begin() as conn:
        for table in _TABLES:
            await conn.execute(
                text(f"DELETE FROM public.{table} WHERE tenant_id IN (:a, :b)"),
                {"a": _TENANT_A, "b": _TENANT_B},
            )


async def _teardown(admin_engine, app_engine):
    try:
        await _cleanup(admin_engine)
    finally:
        await admin_engine.dispose()
        await app_engine.dispose()


async def _seed_admin(admin_engine, calendar_id_a: str = "primary"):
    """admin 接続で A・B の行を両表に入れる。"""
    from sqlalchemy import text

    async with admin_engine.begin() as conn:
        for tid in (_TENANT_A, _TENANT_B):
            cal = calendar_id_a if tid == _TENANT_A else "primary"
            await conn.execute(
                text(
                    "INSERT INTO public.tenant_google_calendar_config "
                    "(tenant_id, access_token_encrypted, refresh_token_encrypted, calendar_id) "
                    "VALUES (:t, 'x', 'y', :c)"
                ),
                {"t": tid, "c": cal},
            )
            await conn.execute(
                text(
                    "INSERT INTO public.tenant_google_drive_config "
                    "(tenant_id, access_token_encrypted, refresh_token_encrypted) "
                    "VALUES (:t, 'x', 'y')"
                ),
                {"t": tid},
            )


async def _count_as(app_engine, table: str, tenant_id: int | None):
    from sqlalchemy import text

    async with app_engine.connect() as conn:
        trans = await conn.begin()
        try:
            if tenant_id is not None:
                await conn.execute(
                    text("SELECT set_config('app.tenant_id', :t, true)"),
                    {"t": str(tenant_id)},
                )
            rows = (
                await conn.execute(text(f"SELECT tenant_id FROM public.{table}"))
            ).all()
            return [r[0] for r in rows]
        finally:
            await trans.rollback()


# ① catalog
async def test_catalog_rls_enabled_and_forced_with_one_policy():
    from sqlalchemy import text

    admin_engine, app_engine = await _setup()
    try:
        async with admin_engine.connect() as conn:
            for table in _TABLES:
                flags = (
                    await conn.execute(
                        text(
                            "SELECT relrowsecurity, relforcerowsecurity FROM pg_class "
                            "WHERE oid = to_regclass(:n)"
                        ),
                        {"n": f"public.{table}"},
                    )
                ).one()
                assert tuple(flags) == (True, True)
                n = (
                    await conn.execute(
                        text(
                            "SELECT count(*) FROM pg_policies "
                            "WHERE schemaname = 'public' AND tablename = :t"
                        ),
                        {"t": table},
                    )
                ).scalar_one()
                assert n == 1
    finally:
        await _teardown(admin_engine, app_engine)


# ② 見える範囲
async def test_select_only_own_tenant_rows_and_none_without_context():
    admin_engine, app_engine = await _setup()
    try:
        await _seed_admin(admin_engine)
        for table in _TABLES:
            assert await _count_as(app_engine, table, _TENANT_A) == [_TENANT_A]
            assert await _count_as(app_engine, table, _TENANT_B) == [_TENANT_B]
            assert await _count_as(app_engine, table, None) == []
    finally:
        await _teardown(admin_engine, app_engine)


# ③ 書けない範囲
async def test_cross_tenant_insert_denied_and_update_affects_zero_rows():
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError

    admin_engine, app_engine = await _setup()
    try:
        await _seed_admin(admin_engine)
        for table in _TABLES:
            # A 文脈で tenant_id=B を INSERT → 42501
            async with app_engine.connect() as conn:
                trans = await conn.begin()
                try:
                    await conn.execute(
                        text("SELECT set_config('app.tenant_id', :t, true)"),
                        {"t": str(_TENANT_A)},
                    )
                    with pytest.raises(DBAPIError) as exc_info:
                        await conn.execute(
                            text(
                                f"INSERT INTO public.{table} "
                                "(tenant_id, access_token_encrypted, refresh_token_encrypted) "
                                "VALUES (:b, 'x', 'y')"
                            ),
                            {"b": _TENANT_B},
                        )
                    orig = exc_info.value.orig
                    sqlstate = getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)
                    assert sqlstate == "42501"
                finally:
                    await trans.rollback()

            # A 文脈で B 行を UPDATE → 0 行
            async with app_engine.connect() as conn:
                trans = await conn.begin()
                try:
                    await conn.execute(
                        text("SELECT set_config('app.tenant_id', :t, true)"),
                        {"t": str(_TENANT_A)},
                    )
                    upd = await conn.execute(
                        text(
                            f"UPDATE public.{table} SET access_token_encrypted = 'z' "
                            "WHERE tenant_id = :b"
                        ),
                        {"b": _TENANT_B},
                    )
                    assert upd.rowcount == 0
                finally:
                    await trans.rollback()
    finally:
        await _teardown(admin_engine, app_engine)


# ④ OAuth 戻り先（文脈なしの session で保存できる）
async def test_oauth_callbacks_save_row_without_prior_context():
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.routers import google_calendar as cal_router
    from app.routers import integrations as drive_router

    admin_engine, app_engine = await _setup()
    expiry = datetime.now(timezone.utc) + timedelta(hours=1)

    async def fake_cal_exchange(code, state):
        return {
            "tenant_id": _TENANT_A,
            "user_id": None,
            "access_token": "cal-access",
            "refresh_token": "cal-refresh",
            "expiry": expiry,
        }

    async def fake_drive_exchange(code, state):
        return {
            "tenant_id": _TENANT_A,
            "user_id": None,
            "access_token": "drv-access",
            "refresh_token": "drv-refresh",
            "expiry": expiry,
            "account_email": "rls-test@example.com",
        }

    try:
        with patch.object(cal_router.cal_svc, "exchange_code", fake_cal_exchange):
            async with AsyncSession(app_engine, expire_on_commit=False) as db:
                resp = await cal_router.connect_callback(code="c", state="s", db=db)
        assert "connected=true" in resp.headers["location"]

        with patch.object(drive_router.drive_svc, "exchange_code", fake_drive_exchange):
            async with AsyncSession(app_engine, expire_on_commit=False) as db:
                resp = await drive_router.connect_callback(code="c", state="s", db=db)
        assert "connected=true" in resp.headers["location"]

        async with admin_engine.connect() as conn:
            for table in _TABLES:
                n = (
                    await conn.execute(
                        text(f"SELECT count(*) FROM public.{table} WHERE tenant_id = :a"),
                        {"a": _TENANT_A},
                    )
                ).scalar_one()
                assert n == 1
    finally:
        await _teardown(admin_engine, app_engine)


# ⑤ commit 後の読取（calendar_id が 'primary' に化けない）
async def test_get_calendar_id_after_token_refresh_keeps_context():
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.auth.dependencies import set_tenant_context
    from app.services import encryption
    from app.services import google_calendar as cal_svc

    admin_engine, app_engine = await _setup()
    custom_calendar_id = "rls-custom-calendar@group.calendar.google.com"
    try:
        await _seed_admin(admin_engine, calendar_id_a=custom_calendar_id)

        fake_creds = MagicMock()
        fake_creds.token = "refreshed-access"
        fake_creds.expiry = datetime.now(timezone.utc) + timedelta(hours=1)
        fake_creds.refresh = MagicMock(return_value=None)

        async with AsyncSession(app_engine, expire_on_commit=False) as db:
            await set_tenant_context(db, _TENANT_A)
            with patch.object(cal_svc, "_is_token_expired", return_value=True), patch.object(
                cal_svc, "_build_credentials", return_value=fake_creds
            ):
                new_access = await cal_svc._refresh_if_needed(
                    db,
                    _TENANT_A,
                    encryption.encrypt("old-access"),
                    encryption.encrypt("old-refresh"),
                    datetime.now(timezone.utc) - timedelta(hours=1),
                )
            assert new_access == "refreshed-access"
            assert await cal_svc.get_calendar_id(db, _TENANT_A) == custom_calendar_id
            await db.rollback()
    finally:
        await _teardown(admin_engine, app_engine)
