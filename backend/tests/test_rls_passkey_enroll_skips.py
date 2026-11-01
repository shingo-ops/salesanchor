"""ログイン直後のパスキー登録の案内のスキップ記録の表（ADR-1013 便6）の本物の PostgreSQL 試験。

migration ファイルをそのまま流して、2 回目も失敗しない（冪等）こと、アプリ用の役割
（salesanchor_app）で INSERT と count の SELECT が通ることを確かめる。

PostgreSQL 専用。RLS_TEST_DATABASE_URL が無ければ skip（ローカル pytest は SQLite）。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from tests.rls_bootstrap import public_bootstrap_lock

_RLS_DB_URL: Optional[str] = os.getenv("RLS_TEST_DATABASE_URL")
_ADMIN_URL: str = os.getenv(
    "RLS_ADMIN_DATABASE_URL",
    "postgresql+asyncpg://jarvis:testpass@localhost:5432/jarvis_test_db",
)

_MIGRATION = Path(__file__).resolve().parents[2] / "migrations" / "20261031_200000_add_passkey_enroll_prompt_skips.sql"
_USER_ID = 991201

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


async def _run_migration(admin_engine) -> None:
    sql = _MIGRATION.read_text(encoding="utf-8")
    async with public_bootstrap_lock(admin_engine):
        async with admin_engine.connect() as conn:
            raw = await conn.get_raw_connection()
            await raw.driver_connection.execute(sql)  # 複数文をそのまま流す
            await conn.commit()


@pytest_asyncio.fixture(scope="module", loop_scope="module", autouse=True)
async def setup_table(admin_engine):
    await _run_migration(admin_engine)
    async with admin_engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO public.users (id, tenant_id, username, email, is_active) "
                "VALUES (:id, 999, 'enroll_skip_user', 'enroll-skip@example.com', TRUE) "
                "ON CONFLICT (id) DO NOTHING"
            ),
            {"id": _USER_ID},
        )
    yield
    async with public_bootstrap_lock(admin_engine):  # 共有 public の表の作り直しを他の試験と直列にする
        async with admin_engine.begin() as conn:
            await conn.execute(text("DROP TABLE IF EXISTS public.passkey_enroll_prompt_skips"))
            await conn.execute(text("DELETE FROM public.users WHERE id = :id"), {"id": _USER_ID})


@pytest.mark.asyncio(loop_scope="module")
async def test_migration_is_idempotent(admin_engine):
    await _run_migration(admin_engine)  # 2 回目も失敗しない


@pytest.mark.asyncio(loop_scope="module")
async def test_app_role_can_insert_and_count(app_engine):
    async with app_engine.begin() as conn:
        await conn.execute(
            text("INSERT INTO public.passkey_enroll_prompt_skips (user_id) VALUES (:uid)"),
            {"uid": _USER_ID},
        )
        row = (
            await conn.execute(
                text(
                    "SELECT count(*) AS n FROM public.passkey_enroll_prompt_skips "
                    "WHERE user_id = :uid AND skipped_at > now() - interval '180 days'"
                ),
                {"uid": _USER_ID},
            )
        ).one()
    assert row.n >= 1


@pytest.mark.asyncio(loop_scope="module")
async def test_migration_regrants_after_revoke(admin_engine, app_engine):
    """GRANT を取り消してから migration を流し直すと、権限が戻ること（CI の既定権限に頼らない）。"""
    async with admin_engine.begin() as conn:
        await conn.execute(text("REVOKE ALL ON TABLE public.passkey_enroll_prompt_skips FROM salesanchor_app"))
        await conn.execute(
            text("REVOKE ALL ON SEQUENCE public.passkey_enroll_prompt_skips_id_seq FROM salesanchor_app")
        )
        revoked = (
            await conn.execute(
                text("SELECT has_table_privilege('salesanchor_app', 'public.passkey_enroll_prompt_skips', 'INSERT')")
            )
        ).scalar_one()
    assert revoked is False

    await _run_migration(admin_engine)

    async with admin_engine.begin() as conn:
        can_insert = (
            await conn.execute(
                text("SELECT has_table_privilege('salesanchor_app', 'public.passkey_enroll_prompt_skips', 'INSERT')")
            )
        ).scalar_one()
        can_select = (
            await conn.execute(
                text("SELECT has_table_privilege('salesanchor_app', 'public.passkey_enroll_prompt_skips', 'SELECT')")
            )
        ).scalar_one()
        can_use_seq = (
            await conn.execute(
                text(
                    "SELECT has_sequence_privilege("
                    "'salesanchor_app', 'public.passkey_enroll_prompt_skips_id_seq', 'USAGE')"
                )
            )
        ).scalar_one()
    assert can_insert is True
    assert can_select is True
    assert can_use_seq is True

    async with app_engine.begin() as conn:
        await conn.execute(
            text("INSERT INTO public.passkey_enroll_prompt_skips (user_id) VALUES (:uid)"),
            {"uid": _USER_ID},
        )
        row = (
            await conn.execute(
                text("SELECT count(*) AS n FROM public.passkey_enroll_prompt_skips WHERE user_id = :uid"),
                {"uid": _USER_ID},
            )
        ).one()
    assert row.n >= 1
