"""会社のオーナーの許可（ADR-1063 便3）を実 PostgreSQL で確かめる。会社番号は 970 / 971。

使い捨て DB を作り、本物の create_tenant_schema（rls_bootstrap）と migration を流し、
アプリ接続役 salesanchor_app（NOBYPASSRLS）で確かめる。
(1) オーナー探し _owner_user_ids は会社の文脈が無いと 0 人（RLS）、文脈があればその会社のオーナーだけ。
(2) devices の部品は別の会社・頼んでいない依頼・自分の依頼を許可しない。一覧は同じ会社の頼んだ依頼だけ。
(3) require_tenant_owner はオーナーだけ通す（admin・社員・別の会社のオーナーは 403）。
"""

from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit, urlunsplit

import pytest
from fastapi import HTTPException

ADMIN_PG_URL = os.getenv("RLS_ADMIN_DATABASE_URL") or os.getenv("TEST_PG_URL")
APP_PG_URL = os.getenv("RLS_TEST_DATABASE_URL")

pytestmark = [
    pytest.mark.skipif(
        not ADMIN_PG_URL or not APP_PG_URL,
        reason="実 PostgreSQL 環境が必要 (RLS_ADMIN_DATABASE_URL / RLS_TEST_DATABASE_URL 未設定)。",
    ),
    pytest.mark.asyncio,
]

_TA = 970
_TB = 971
_OWNER_A = 9700
_STAFF_A = 9701
_ADMIN_A = 9702
_OWNER_B = 9710
_STAFF_B = 9711
# test_users_rls.py と同じ順（self_hosted → auth_events → 機械の表）
_MIGRATIONS = (
    "20261013_160000_add_self_hosted_auth_tables.sql",
    "001_create_auth_events.sql",
    "20261101_130000_add_new_device_approval.sql",
    "20261106_140000_add_login_request_admin_requested_at.sql",
)
_EXTRA_DDL = """
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS last_login TIMESTAMPTZ NULL;
"""
_GRANT_DDL = """
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO salesanchor_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO salesanchor_app;
GRANT USAGE ON SCHEMA tenant_970 TO salesanchor_app;
GRANT USAGE ON SCHEMA tenant_971 TO salesanchor_app;
GRANT SELECT ON tenant_970.roles, tenant_970.user_roles TO salesanchor_app;
GRANT SELECT ON tenant_971.roles, tenant_971.user_roles TO salesanchor_app;
"""


def _with_db(url: str, name: str) -> str:
    return urlunsplit(urlsplit(url)._replace(path="/" + name))


@asynccontextmanager
async def _fresh():
    """使い捨て DB を作り、2 社・5 人・役割を入れて (admin_engine, app_engine) を返す。終了時に DROP。"""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    from tests.rls_bootstrap import _apply_migration, bootstrap_tenant_schema

    control = create_async_engine(ADMIN_PG_URL, isolation_level="AUTOCOMMIT")
    name = "owner_lr_" + uuid.uuid4().hex[:12]
    async with control.connect() as conn:
        await conn.execute(text(f'CREATE DATABASE "{name}"'))
    admin_engine = create_async_engine(_with_db(ADMIN_PG_URL, name), echo=False)
    app_engine = create_async_engine(_with_db(APP_PG_URL, name), echo=False, pool_size=1, max_overflow=0)
    try:
        await bootstrap_tenant_schema(admin_engine, _TA)
        await bootstrap_tenant_schema(admin_engine, _TB)
        async with admin_engine.begin() as conn:
            raw = await conn.get_raw_connection()
            await raw.driver_connection.execute(_EXTRA_DDL)
        for mig in _MIGRATIONS:
            await _apply_migration(admin_engine, mig)
        async with admin_engine.begin() as conn:
            for uid, tid in ((_OWNER_A, _TA), (_STAFF_A, _TA), (_ADMIN_A, _TA), (_OWNER_B, _TB), (_STAFF_B, _TB)):
                await conn.execute(
                    text(
                        "INSERT INTO public.users (id, tenant_id, username, email, full_name, is_active) "
                        "VALUES (:u, :t, :n, :e, :n, TRUE)"
                    ),
                    {"u": uid, "t": tid, "n": f"u{uid}", "e": f"u{uid}@example.com"},
                )
            for uid, schema, key in (
                (_OWNER_A, "tenant_970", "owner"),
                (_ADMIN_A, "tenant_970", "admin"),
                (_OWNER_B, "tenant_971", "owner"),
            ):
                await conn.execute(
                    text(
                        f"INSERT INTO {schema}.user_roles (user_id, role_id) "
                        f"SELECT :u, id FROM {schema}.roles WHERE system_key = :k"
                    ),
                    {"u": uid, "k": key},
                )
            raw = await conn.get_raw_connection()
            await raw.driver_connection.execute(_GRANT_DDL)
        yield admin_engine, app_engine
    finally:
        await app_engine.dispose()
        await admin_engine.dispose()
        async with control.connect() as conn:
            await conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        await control.dispose()


async def _add_request(admin_engine, user_id: int, *, asked: bool) -> str:
    from sqlalchemy import text

    rid = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    async with admin_engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO public.auth_login_requests "
                "(id, user_id, status, match_number, candidates, pending_token_hash, expires_at, admin_requested_at) "
                "VALUES (:id, :u, 'pending', '12', '123456', :h, :exp, :asked)"
            ),
            {
                "id": rid,
                "u": user_id,
                "h": uuid.uuid4().bytes,
                "exp": now + timedelta(minutes=30),
                "asked": now if asked else None,
            },
        )
    return rid


def _session(app_engine):
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    return async_sessionmaker(app_engine, class_=AsyncSession, expire_on_commit=False)()


async def test_owner_lookup_needs_tenant_context():
    from app.auth.dependencies import clear_tenant_context, set_tenant_context
    from app.services.user_notices import _owner_user_ids

    async with _fresh() as (_admin, app_engine):
        async with _session(app_engine) as db:
            await clear_tenant_context(db)
            assert await _owner_user_ids(db, _TA) == []
            await set_tenant_context(db, _TA)
            assert await _owner_user_ids(db, _TA) == [_OWNER_A]
            await clear_tenant_context(db)


async def test_devices_parts_keep_to_one_company():
    from sqlalchemy import text

    from app.auth import devices

    async with _fresh() as (admin_engine, app_engine):
        other = await _add_request(admin_engine, _STAFF_B, asked=True)
        unasked = await _add_request(admin_engine, _STAFF_A, asked=False)
        own = await _add_request(admin_engine, _OWNER_A, asked=True)
        good = await _add_request(admin_engine, _STAFF_A, asked=True)
        async with _session(app_engine) as db:
            kw = {"approver_user_id": _OWNER_A, "note": "電話で確認", "tenant_id": _TA, "require_admin_requested": True}
            listed = await devices.list_admin_requested(db, tenant_id=_TA, exclude_user_id=_OWNER_A)
            assert [str(r.id) for r in listed] == [good]
            assert (await devices.approve_request_as_admin(db, request_id=other, **kw)).outcome == "not_found"
            assert (await devices.approve_request_as_admin(db, request_id=unasked, **kw)).outcome == "not_found"
            assert (await devices.approve_request_as_admin(db, request_id=own, **kw)).outcome == "own_request"
            ok = await devices.approve_request_as_admin(db, request_id=good, **kw)
            assert (ok.outcome, ok.target_user_id, ok.target_tenant_id) == ("approved", _STAFF_A, _TA)
            await db.commit()
            again = await devices.approve_request_as_admin(db, request_id=good, **kw)
            assert again.outcome == "not_found"
            assert await devices.mark_admin_requested(db, unasked) is True
            assert await devices.mark_admin_requested(db, unasked) is False
            await db.commit()
        async with admin_engine.connect() as conn:
            row = (
                await conn.execute(
                    text(
                        "SELECT status, decided_via, decided_by_user_id, decided_note FROM public.auth_login_requests WHERE id = :id"
                    ),
                    {"id": good},
                )
            ).first()
            assert tuple(row) == ("approved", "admin", _OWNER_A, "電話で確認")
            other_row = (
                await conn.execute(text("SELECT status FROM public.auth_login_requests WHERE id = :id"), {"id": other})
            ).first()
            assert other_row.status == "pending"


async def test_require_tenant_owner_only_lets_owner_in():
    from app.auth.dependencies import clear_tenant_context, require_tenant_owner, set_tenant_context
    from app.models import User

    async with _fresh() as (_admin, app_engine):
        async with _session(app_engine) as db:
            await set_tenant_context(db, _TA)
            owner = User(id=_OWNER_A, tenant_id=_TA, email="o@example.com")
            assert await require_tenant_owner(tenant_id=_TA, user=owner, db=db) is owner
            for uid in (_ADMIN_A, _STAFF_A, _OWNER_B):
                with pytest.raises(HTTPException) as exc:
                    await require_tenant_owner(tenant_id=_TA, user=User(id=uid, tenant_id=_TA, email="x@example.com"), db=db)
                assert exc.value.status_code == 403 and exc.value.detail == "owner_only"
            await clear_tenant_context(db)
