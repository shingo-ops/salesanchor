"""Discord OAuth callback — audit_logs RLS 実 PostgreSQL 証明テスト。

RLS（row-level security）が有効な PostgreSQL 実 DB で
「set_tenant_context 後に audit_logs INSERT が通ること」を実証する。

SQLite ユニットテストでは RLS が no-op のため検出不可。
このテストが set_tenant_context 追加修正の本質的な実証になる。

実行条件:
  RLS_ADMIN_DATABASE_URL (or TEST_PG_URL) / RLS_TEST_DATABASE_URL が設定済みの場合のみ。

実行:
    pytest backend/tests/test_discord_oauth_rls.py -v
"""
from __future__ import annotations

import os

import pytest
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from tests.rls_bootstrap import bootstrap_tenant_schema

ADMIN_PG_URL = os.getenv("RLS_ADMIN_DATABASE_URL") or os.getenv("TEST_PG_URL")
APP_PG_URL = os.getenv("RLS_TEST_DATABASE_URL")

_TENANT_ID = 99  # テスト専用テナント（既存テナントと衝突しない大きな値）
_SCHEMA = f"tenant_{_TENANT_ID:03d}"
_USER_ID = 9901


@pytest.mark.skipif(
    not ADMIN_PG_URL or not APP_PG_URL,
    reason="実 PostgreSQL 環境が必要 (RLS_ADMIN_DATABASE_URL / TEST_PG_URL / RLS_TEST_DATABASE_URL 未設定)。",
)
@pytest.mark.asyncio
async def test_audit_logs_insert_passes_with_set_tenant_context():
    """set_tenant_context 相当の SET を実行後、audit_logs INSERT が RLS に通る。

    修正内容: discord_oauth.py:183 に set_tenant_context(db, tenant_id) を追加。
    本テストはその修正の PostgreSQL 実 DB での証明。
    """
    admin_engine = create_async_engine(ADMIN_PG_URL, echo=False)
    app_engine = create_async_engine(APP_PG_URL, echo=False)
    app_session_factory = sessionmaker(app_engine, class_=AsyncSession, expire_on_commit=False)

    try:
        # テナントスキーマ構築（RLS ポリシー含む）
        await bootstrap_tenant_schema(admin_engine, _TENANT_ID)

        # set_tenant_context 相当のセッション変数設定後に INSERT
        async with app_session_factory() as session:
            async with session.begin():
                # set_tenant_context の実処理と同等（auth/dependencies.py:275-277）
                await session.execute(text(f"SET search_path = {_SCHEMA}, public"))
                await session.execute(
                    text("SELECT set_config('app.tenant_id', :tid, true)"),
                    {"tid": str(_TENANT_ID)},
                )
                await session.execute(text("SELECT set_config('app.is_operator', '', true)"))

                # audit_logs INSERT（discord_oauth_callback の record_audit_log 相当）
                await session.execute(
                    text(f"""
                        INSERT INTO {_SCHEMA}.audit_logs
                            (tenant_id, user_id, action, table_name, record_id, old_data, new_data)
                        VALUES
                            (:tenant_id, :user_id, :action, :table_name, :record_id,
                             :old_data, :new_data)
                    """),
                    {
                        "tenant_id": _TENANT_ID,
                        "user_id": _USER_ID,
                        "action": "update",
                        "table_name": "tenant_discord_config",
                        "record_id": _TENANT_ID,
                        "old_data": None,
                        "new_data": '{"guild_id": "123456789012345678", "source": "discord_oauth_callback"}',
                    },
                )
                # ここに到達すれば RLS が通った証明
    finally:
        # テスト用スキーマをクリーンアップ
        async with admin_engine.begin() as conn:
            await conn.execute(text(f"DROP SCHEMA IF EXISTS {_SCHEMA} CASCADE"))
            await conn.execute(
                text("DELETE FROM public.tenants WHERE id = :tid"),
                {"tid": _TENANT_ID},
            )
        await admin_engine.dispose()
        await app_engine.dispose()


@pytest.mark.skipif(
    not ADMIN_PG_URL or not APP_PG_URL,
    reason="実 PostgreSQL 環境が必要 (RLS_ADMIN_DATABASE_URL / TEST_PG_URL / RLS_TEST_DATABASE_URL 未設定)。",
)
@pytest.mark.asyncio
async def test_audit_logs_insert_blocked_without_set_tenant_context():
    """set_tenant_context なしでは audit_logs INSERT が RLS に弾かれる（修正前の挙動の実証）。

    app.tenant_id 未設定 → current_setting('app.tenant_id', true) = NULL
    → RLS ポリシー tenant_isolation_audit_logs: 6 = NULL → FALSE → INSERT blocked。
    これが discord_oauth_callback で 500 を返していた根本原因。
    """
    admin_engine = create_async_engine(ADMIN_PG_URL, echo=False)
    app_engine = create_async_engine(APP_PG_URL, echo=False)
    app_session_factory = sessionmaker(app_engine, class_=AsyncSession, expire_on_commit=False)

    # テナントスキーマ構築（1つ目のテストが先に走れば不要だが冪等なので安全）
    await bootstrap_tenant_schema(admin_engine, _TENANT_ID)

    try:
        async with app_session_factory() as session:
            # app.tenant_id を設定しない（修正前の状態を再現）
            # search_path も設定しないことで explicit schema 修飾でも RLS が効くことを確認
            with pytest.raises(ProgrammingError, match="violates row-level security policy|permission denied"):
                async with session.begin():
                    await session.execute(
                        text(f"""
                            INSERT INTO {_SCHEMA}.audit_logs
                                (tenant_id, user_id, action, table_name, record_id, old_data, new_data)
                            VALUES
                                (:tenant_id, :user_id, :action, :table_name, :record_id,
                                 :old_data, :new_data)
                        """),
                        {
                            "tenant_id": _TENANT_ID,
                            "user_id": _USER_ID,
                            "action": "update",
                            "table_name": "tenant_discord_config",
                            "record_id": _TENANT_ID,
                            "old_data": None,
                            "new_data": '{"source": "pre_fix_simulation"}',
                        },
                    )
    finally:
        async with admin_engine.begin() as conn:
            await conn.execute(text(f"DROP SCHEMA IF EXISTS {_SCHEMA} CASCADE"))
            await conn.execute(
                text("DELETE FROM public.tenants WHERE id = :tid"),
                {"tid": _TENANT_ID},
            )
        await admin_engine.dispose()
        await app_engine.dispose()
