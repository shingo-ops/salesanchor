"""Discord OAuth2 Bot Invite エンドポイント (discord_oauth.py) のテスト

POST /api/v1/discord/oauth/start  — Invite URL 発行（認証必須）
GET  /api/v1/discord/oauth/callback — Discord コールバック（公開）

oauth_state (Redis) と DB upsert はモックし、エンドポイントのルーティング・
パラメータ検証・リダイレクト URL の正しさを検証する。

実行:
    pytest backend/tests/test_discord_oauth.py -v
"""

from __future__ import annotations

import os
from contextlib import ExitStack
from unittest.mock import AsyncMock, patch
from urllib.parse import parse_qs, urlparse

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.auth.dependencies import (
    get_current_tenant,
    get_current_user,
)
from app.database import get_db
from app.models import User


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

_ALL_PERMS = {"channels.view", "channels.manage"}


async def _mock_load_user_permissions(db, tenant_id, user_id):
    return _ALL_PERMS


def _mock_user() -> User:
    user = User()
    user.id = 42
    user.tenant_id = 7
    user.username = "testuser"
    user.email = "test@example.com"
    user.role = "admin"
    user.is_active = True
    return user


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    @event.listens_for(eng.sync_engine, "connect")
    def _setup(dbapi_conn, _):
        dbapi_conn.create_function("NOW", 0, lambda: "2026-06-02 00:00:00+00:00")
        dbapi_conn.execute("PRAGMA foreign_keys = ON")

    @event.listens_for(eng.sync_engine, "before_cursor_execute", retval=True)
    def _rewrite(conn, cursor, statement, parameters, context, executemany):
        if "public.tenant_discord_config" in statement:
            statement = statement.replace(
                "public.tenant_discord_config", "tenant_discord_config"
            )
        return statement, parameters

    async with eng.begin() as conn:
        await conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS tenant_discord_config (
                tenant_id INTEGER PRIMARY KEY,
                guild_id  VARCHAR(32) NOT NULL,
                connected_by_staff_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        )

    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db_session(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def app_client(db_session):
    """discord_oauth ルーターを含む最小 FastAPI アプリでテスト用 AsyncClient を返す。"""
    from app.routers import discord_oauth
    from fastapi import Depends, FastAPI

    app = FastAPI()
    app.include_router(discord_oauth.router, prefix="/api/v1")

    mock_user = _mock_user()

    async def override_get_db():
        yield db_session

    async def override_get_current_user():
        return mock_user

    async def override_get_current_tenant():
        return mock_user.tenant_id

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_current_tenant] = override_get_current_tenant

    transport = ASGITransport(app=app)
    with ExitStack() as stack:
        stack.enter_context(
            patch(
                "app.auth.dependencies.load_user_permissions",
                _mock_load_user_permissions,
            )
        )
        stack.enter_context(
            patch(
                "app.routers.discord_oauth.record_audit_log",
                AsyncMock(return_value=None),
            )
        )
        stack.enter_context(
            patch(
                "app.routers.discord_oauth.reset_tenant_context",
                AsyncMock(return_value=None),
            )
        )
        stack.enter_context(
            patch(
                "app.auth.dependencies.set_tenant_context",
                AsyncMock(return_value=None),
            )
        )
        async with AsyncClient(
            transport=transport, base_url="http://test", follow_redirects=False
        ) as ac:
            yield ac


@pytest_asyncio.fixture
async def unauth_client(db_session):
    """認証 dependency を override しない（未認証テスト用）。"""
    from app.routers import discord_oauth
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(discord_oauth.router, prefix="/api/v1")

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test", follow_redirects=False
    ) as ac:
        yield ac


# ---------------------------------------------------------------------------
# POST /api/v1/discord/oauth/start
# ---------------------------------------------------------------------------


class TestDiscordOAuthStart:
    """POST /api/v1/discord/oauth/start のテスト。"""

    @pytest.mark.asyncio
    async def test_start_returns_invite_url_and_state(self, app_client):
        """認証済みユーザーが呼ぶと invite_url と state が返る。"""
        mock_issued = {
            "state": "test-random-state-abc123",
            "ttl_seconds": 600,
            "expires_at": "2026-06-02T00:10:00+00:00",
        }
        with patch(
            "app.routers.discord_oauth.oauth_state.issue_state",
            AsyncMock(return_value=mock_issued),
        ):
            res = await app_client.post("/api/v1/discord/oauth/start")

        assert res.status_code == 200
        body = res.json()
        assert "invite_url" in body
        assert "state" in body
        assert "expires_at" in body
        assert body["state"] == "test-random-state-abc123"
        assert "discord.com/oauth2/authorize" in body["invite_url"]
        assert "state=test-random-state-abc123" in body["invite_url"]

    @pytest.mark.asyncio
    async def test_start_unauthenticated_returns_error(self, unauth_client):
        """未認証だと 401 または 403 が返る。"""
        res = await unauth_client.post("/api/v1/discord/oauth/start")
        assert res.status_code in (401, 403, 422)

    @pytest.mark.asyncio
    async def test_invite_url_contains_required_permissions(self, app_client):
        """発行された invite_url に permissions=805432406 が含まれる。

        Developer Portal で確認した permissions integer（2026-06-16）と一致することを保証する。
        ADR-091 Bot 権限定義の正本と同期している。
        """
        mock_issued = {
            "state": "perm-check-state-xyz",
            "ttl_seconds": 600,
            "expires_at": "2026-06-16T00:10:00+00:00",
        }
        with patch(
            "app.routers.discord_oauth.oauth_state.issue_state",
            AsyncMock(return_value=mock_issued),
        ):
            res = await app_client.post("/api/v1/discord/oauth/start")

        assert res.status_code == 200
        invite_url = res.json()["invite_url"]
        parsed = urlparse(invite_url)
        qs = parse_qs(parsed.query)

        assert qs.get("permissions") == ["805432406"], (
            f"permissions が 805432406 ではありません: {qs.get('permissions')}"
        )

    @pytest.mark.asyncio
    async def test_invite_url_contains_required_oauth_params(self, app_client):
        """発行された invite_url に必須の OAuth2 パラメータが全て含まれる。

        - scope に bot と applications.commands が含まれること
        - response_type=code が含まれること
        - redirect_uri が /discord/oauth/callback を含むこと
        - state が含まれること
        """
        mock_issued = {
            "state": "oauth-param-check-state",
            "ttl_seconds": 600,
            "expires_at": "2026-06-16T00:10:00+00:00",
        }
        with patch(
            "app.routers.discord_oauth.oauth_state.issue_state",
            AsyncMock(return_value=mock_issued),
        ):
            res = await app_client.post("/api/v1/discord/oauth/start")

        assert res.status_code == 200
        invite_url = res.json()["invite_url"]
        parsed = urlparse(invite_url)
        qs = parse_qs(parsed.query)

        # scope: bot と applications.commands が含まれること
        scope_values = qs.get("scope", [""])
        scope_str = " ".join(scope_values)
        assert "bot" in scope_str, f"scope に bot が含まれていません: {scope_str}"
        assert "applications.commands" in scope_str, (
            f"scope に applications.commands が含まれていません: {scope_str}"
        )

        # response_type=code（callback-less flow を避けるために必須）
        assert qs.get("response_type") == ["code"], (
            f"response_type が code ではありません: {qs.get('response_type')}"
        )

        # redirect_uri にコールバックパスが含まれること
        redirect_uri_values = qs.get("redirect_uri", [""])
        assert any("discord/oauth/callback" in v for v in redirect_uri_values), (
            f"redirect_uri に discord/oauth/callback が含まれていません: {redirect_uri_values}"
        )

        # state が含まれること
        assert qs.get("state") == ["oauth-param-check-state"], (
            f"state が一致しません: {qs.get('state')}"
        )


# ---------------------------------------------------------------------------
# GET /api/v1/discord/oauth/callback
# ---------------------------------------------------------------------------

_FRONTEND_BASE = "https://app.salesanchor.jp"


class TestDiscordOAuthCallback:
    """GET /api/v1/discord/oauth/callback のテスト。"""

    @pytest.mark.asyncio
    async def test_callback_valid_state_and_guild_id_redirects_connected(
        self, app_client
    ):
        """有効な state と guild_id があると guild_id が保存されて
        app.salesanchor.jp/channels?discord_status=connected にリダイレクトされる。
        """
        mock_payload = {
            "tenant_id": 7,
            "staff_id": 42,
            "created_at": "2026-06-02T00:00:00+00:00",
            "nonce": "abc",
        }
        with patch(
            "app.routers.discord_oauth.oauth_state.consume_state",
            AsyncMock(return_value=mock_payload),
        ):
            res = await app_client.get(
                "/api/v1/discord/oauth/callback",
                params={"state": "valid-state", "guild_id": "123456789012345678"},
            )

        assert res.status_code in (302, 307)
        location = res.headers["location"]
        assert location == f"{_FRONTEND_BASE}/channels?discord_status=connected"
        # _FRONTEND_BASE_URL が空文字でないことの回帰テスト
        assert location.startswith("https://app.salesanchor.jp")

    @pytest.mark.asyncio
    async def test_callback_missing_state_redirects_error(self, app_client):
        """state なしで呼ぶと discord_status=error&reason=missing_state にリダイレクトされる。"""
        res = await app_client.get("/api/v1/discord/oauth/callback")

        assert res.status_code in (302, 307)
        location = res.headers["location"]
        assert "discord_status=error" in location
        assert "reason=missing_state" in location

    @pytest.mark.asyncio
    async def test_callback_invalid_state_redirects_error(self, app_client):
        """無効な state（改ざん・期限切れ）では
        discord_status=error&reason=invalid_state にリダイレクトされる。
        """
        with patch(
            "app.routers.discord_oauth.oauth_state.consume_state",
            AsyncMock(return_value=None),
        ):
            res = await app_client.get(
                "/api/v1/discord/oauth/callback",
                params={"state": "tampered-state", "guild_id": "123456789012345678"},
            )

        assert res.status_code in (302, 307)
        location = res.headers["location"]
        assert "discord_status=error" in location
        assert "reason=invalid_state" in location

    @pytest.mark.asyncio
    async def test_callback_calls_set_tenant_context_before_db_writes(self, app_client):
        """callback は DB 書き込み前に set_tenant_context を正しい tenant_id で呼ぶ。

        audit_logs の RLS ポリシー（tenant_isolation_audit_logs）は
        app.tenant_id が設定済みでないと INSERT をブロックする（:183 修正の回帰テスト）。
        SQLite 環境では RLS が no-op のため、呼ばれたかを mock で確認する。
        PostgreSQL RLS 実証は test_discord_oauth_rls.py で実施。
        """
        mock_payload = {
            "tenant_id": 7,
            "staff_id": 42,
            "created_at": "2026-06-02T00:00:00+00:00",
            "nonce": "abc",
        }
        with patch(
            "app.routers.discord_oauth.oauth_state.consume_state",
            AsyncMock(return_value=mock_payload),
        ), patch(
            "app.auth.dependencies.set_tenant_context",
            AsyncMock(return_value=None),
        ) as mock_set_ctx:
            res = await app_client.get(
                "/api/v1/discord/oauth/callback",
                params={"state": "valid-state", "guild_id": "123456789012345678"},
            )

        assert res.status_code in (302, 307)
        # set_tenant_context が呼ばれ、tenant_id=7 が渡されたことを確認
        mock_set_ctx.assert_awaited_once()
        call_args = mock_set_ctx.call_args
        assert call_args.args[1] == 7 or call_args.kwargs.get("tenant_id") == 7, (
            f"set_tenant_context が tenant_id=7 で呼ばれていない: {call_args}"
        )

    @pytest.mark.asyncio
    async def test_callback_missing_guild_id_redirects_error(self, app_client):
        """guild_id なしで呼ぶと discord_status=error&reason=missing_guild_id にリダイレクトされる。"""
        res = await app_client.get(
            "/api/v1/discord/oauth/callback",
            params={"state": "some-state"},
        )

        assert res.status_code in (302, 307)
        location = res.headers["location"]
        assert "discord_status=error" in location
        assert "reason=missing_guild_id" in location
