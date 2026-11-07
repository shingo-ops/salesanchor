"""スタッフ招待の表 public.staff_join_invites の会社別 RLS（ADR-1068・設計 §3-1・§3-2・§3-3）。

実 PostgreSQL（salesanchor_app＝NOBYPASSRLS で接続）で、会社の分離を示す。
SQLite では set_tenant_context が何もしない（backend/app/auth/dependencies.py）ため、
会社の分離の根拠は SQLite の試験 tests/test_staff_join_api.py ではなくこの試験に置く。
"""
from __future__ import annotations

import hashlib
import os
from datetime import datetime, timedelta, timezone

import pytest

from tests.rls_bootstrap import (
    _apply_migration,
    bootstrap_tenant_schema,
    public_bootstrap_lock,
)

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

_TENANT_A = 984
_TENANT_B = 985
_CREATOR = 999  # rls_bootstrap が public.users に入れる試験用の利用者
_RAW_A = "a" * 43
_RAW_B = "b" * 43
_KEY_A = f"{_TENANT_A}.{_RAW_A}"
_KEY_B = f"{_TENANT_B}.{_RAW_B}"
_MIGRATIONS = ("20261107_120000_create_staff_join_invites.sql",)


def _h(key: str) -> bytes:
    return hashlib.sha256(key.encode()).digest()


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
        await conn.execute(
            text("DELETE FROM public.staff_join_invites WHERE tenant_id IN (:a, :b)"),
            {"a": _TENANT_A, "b": _TENANT_B},
        )


async def _teardown(admin_engine, app_engine):
    try:
        await _cleanup(admin_engine)
    finally:
        await admin_engine.dispose()
        await app_engine.dispose()


async def _seed_admin(admin_engine):
    """admin 接続で A・B の招待を 1 本ずつ入れる（鍵の sha256 は会社の番号つきの全体）。"""
    from sqlalchemy import text

    expires = datetime.now(timezone.utc) + timedelta(hours=72)
    async with admin_engine.begin() as conn:
        for tid, key in ((_TENANT_A, _KEY_A), (_TENANT_B, _KEY_B)):
            await conn.execute(
                text(
                    "INSERT INTO public.staff_join_invites "
                    "(tenant_id, role_id, created_by, token_hash, expires_at, status) "
                    "VALUES (:t, 1, :u, :h, :e, 'open')"
                ),
                {"t": tid, "u": _CREATOR, "h": _h(key), "e": expires},
            )


async def _select_as(app_engine, tenant_id: int | None, sql: str, params: dict | None = None):
    from sqlalchemy import text

    async with app_engine.connect() as conn:
        trans = await conn.begin()
        try:
            if tenant_id is not None:
                await conn.execute(
                    text("SELECT set_config('app.tenant_id', :t, true)"), {"t": str(tenant_id)},
                )
            return (await conn.execute(text(sql), params or {})).all()
        finally:
            await trans.rollback()


# ① catalog
async def test_catalog_rls_enabled_and_forced_with_one_policy():
    from sqlalchemy import text

    admin_engine, app_engine = await _setup()
    try:
        async with admin_engine.connect() as conn:
            flags = (
                await conn.execute(
                    text(
                        "SELECT relrowsecurity, relforcerowsecurity FROM pg_class "
                        "WHERE oid = to_regclass('public.staff_join_invites')"
                    )
                )
            ).one()
            assert tuple(flags) == (True, True)
            n = (
                await conn.execute(
                    text(
                        "SELECT count(*) FROM pg_policies "
                        "WHERE schemaname = 'public' AND tablename = 'staff_join_invites'"
                    )
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
        sql = "SELECT tenant_id FROM public.staff_join_invites"
        assert [r[0] for r in await _select_as(app_engine, _TENANT_A, sql)] == [_TENANT_A]
        assert [r[0] for r in await _select_as(app_engine, _TENANT_B, sql)] == [_TENANT_B]
        assert await _select_as(app_engine, None, sql) == []
    finally:
        await _teardown(admin_engine, app_engine)


# ③ 鍵の会社の番号を書き換えても、別の会社の行は引けない（設計 §3-2）
async def test_other_tenants_key_hash_is_not_found_under_my_context():
    admin_engine, app_engine = await _setup()
    try:
        await _seed_admin(admin_engine)
        sql = "SELECT id FROM public.staff_join_invites WHERE token_hash = :h"
        # B の文脈で A の鍵の sha256 を引いても 0 行（RLS）
        assert await _select_as(app_engine, _TENANT_B, sql, {"h": _h(_KEY_A)}) == []
        # 会社の番号だけ A→B に書き換えた鍵は sha256 が合わず 0 行
        rewritten = f"{_TENANT_B}.{_RAW_A}"
        assert await _select_as(app_engine, _TENANT_B, sql, {"h": _h(rewritten)}) == []
        # 正しい文脈と正しい鍵なら 1 行
        assert len(await _select_as(app_engine, _TENANT_A, sql, {"h": _h(_KEY_A)})) == 1
    finally:
        await _teardown(admin_engine, app_engine)


# ④ 書けない範囲
async def test_cross_tenant_insert_denied_and_update_affects_zero_rows():
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError

    admin_engine, app_engine = await _setup()
    try:
        await _seed_admin(admin_engine)
        # A 文脈で tenant_id=B を INSERT → 42501
        async with app_engine.connect() as conn:
            trans = await conn.begin()
            try:
                await conn.execute(
                    text("SELECT set_config('app.tenant_id', :t, true)"), {"t": str(_TENANT_A)},
                )
                with pytest.raises(DBAPIError) as exc_info:
                    await conn.execute(
                        text(
                            "INSERT INTO public.staff_join_invites "
                            "(tenant_id, role_id, created_by, token_hash, expires_at) "
                            "VALUES (:b, 1, :u, :h, now())"
                        ),
                        {"b": _TENANT_B, "u": _CREATOR, "h": _h("x" * 50)},
                    )
                orig = exc_info.value.orig
                sqlstate = getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)
                assert sqlstate == "42501"
            finally:
                await trans.rollback()

        # A 文脈で B の行を UPDATE → 0 行
        async with app_engine.connect() as conn:
            trans = await conn.begin()
            try:
                await conn.execute(
                    text("SELECT set_config('app.tenant_id', :t, true)"), {"t": str(_TENANT_A)},
                )
                upd = await conn.execute(
                    text("UPDATE public.staff_join_invites SET status = 'revoked' WHERE tenant_id = :b"),
                    {"b": _TENANT_B},
                )
                assert upd.rowcount == 0
            finally:
                await trans.rollback()
    finally:
        await _teardown(admin_engine, app_engine)


# ⑤ 実際の入口（鍵から有効な招待を引く関数）を、RLS のもとで通す
async def test_open_invite_by_key_respects_tenant_context_under_rls():
    from fastapi import HTTPException
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.routers import staff_join as router

    admin_engine, app_engine = await _setup()
    try:
        await _seed_admin(admin_engine)
        async with AsyncSession(app_engine, expire_on_commit=False) as session:
            invite = await router._open_invite_by_key(session, _KEY_A, "127.0.0.1", for_update=False)
            assert int(invite.tenant_id) == _TENANT_A
            await session.rollback()
        # 会社の番号だけ書き換えた鍵は同じ 404（他社の行は見えない）
        async with AsyncSession(app_engine, expire_on_commit=False) as session:
            with pytest.raises(HTTPException) as exc_info:
                await router._open_invite_by_key(session, f"{_TENANT_B}.{_RAW_A}", "127.0.0.1", for_update=False)
            assert exc_info.value.status_code == 404
    finally:
        await _teardown(admin_engine, app_engine)
