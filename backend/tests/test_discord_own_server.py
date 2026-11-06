"""自社用 Discord サーバーの登録（discord-server-management 便1b）の試験。

招待の開始（purpose の受け取り・権限）・戻り（用途別の保存と戻り先）・
自社用の取得と解除・受け取り係（自社用サーバーは顧客用として扱わない）を
SQLite で確かめる。受け取り係の 2 本は SQL を差し替えず本物の文を流す。
"""
from __future__ import annotations

import os
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from app.auth.dependencies import get_current_tenant, get_current_user
from app.database import get_db
from app.discord_gateway.client import JarvisDiscordClient
from app.models import User

_FRONTEND = "https://app.salesanchor.jp"
_TENANT = 7
_OTHER_TENANT = 8
_GUILD_CUSTOMER = "111111111111111111"
_GUILD_OWN = "222222222222222222"
_GUILD_OTHER = "333333333333333333"

_PERMS_FULL = {"channels.manage", "tenant.profile.view", "tenant.profile.edit"}
_PERMS_NO_EDIT = {"channels.manage", "tenant.profile.view"}


def _mock_user() -> User:
    user = User()
    user.id = 42
    user.tenant_id = _TENANT
    user.username = "testuser"
    user.email = "test@example.com"
    user.role = "admin"
    user.is_active = True
    return user


@pytest_asyncio.fixture
async def engine(test_engine, setup_test_db):
    """conftest の共通の表（test_engine・setup_test_db）を使う。前と後で登録の表を空にする。"""
    async with test_engine.begin() as conn:
        await conn.execute(text("DELETE FROM tenant_discord_config"))
    yield test_engine
    async with test_engine.begin() as conn:
        await conn.execute(text("DELETE FROM tenant_discord_config"))


@pytest.fixture
def factory(engine):
    return sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture
def perms():
    """この試験で使う権限の集合（試験ごとに差し替える）。"""
    return set(_PERMS_FULL)


@pytest_asyncio.fixture
async def client(factory, perms):
    from app.routers import discord_guild_config, discord_oauth

    app = FastAPI()
    app.include_router(discord_oauth.router, prefix="/api/v1")
    app.include_router(discord_guild_config.router, prefix="/api/v1")

    mock_user = _mock_user()

    async def override_db():
        async with factory() as s:
            yield s

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_current_tenant] = lambda: _TENANT

    async def _perms(db, tenant_id, user_id):
        return perms

    with ExitStack() as stack:
        stack.enter_context(patch("app.auth.dependencies.load_user_permissions", _perms))
        stack.enter_context(patch("app.routers.discord_oauth.load_user_permissions", _perms))
        for mod in ("discord_oauth", "discord_guild_config"):
            stack.enter_context(
                patch(f"app.routers.{mod}.record_audit_log", AsyncMock(return_value=None))
            )
            stack.enter_context(
                patch(f"app.routers.{mod}.reset_tenant_context", AsyncMock(return_value=None))
            )
        stack.enter_context(
            patch("app.auth.dependencies.set_tenant_context", AsyncMock(return_value=None))
        )
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test", follow_redirects=False
        ) as ac:
            yield ac


async def _insert(factory, tenant_id: int, purpose: str, guild_id: str) -> None:
    async with factory() as s:
        await s.execute(
            text(
                "INSERT INTO tenant_discord_config (tenant_id, purpose, guild_id)"
                " VALUES (:t, :p, :g)"
            ),
            {"t": tenant_id, "p": purpose, "g": guild_id},
        )
        await s.commit()


async def _rows(factory) -> list[tuple]:
    async with factory() as s:
        result = await s.execute(
            text("SELECT tenant_id, purpose, guild_id FROM tenant_discord_config ORDER BY 1, 2")
        )
        return [tuple(r) for r in result.fetchall()]


_ISSUED = {"state": "st-1", "ttl_seconds": 600, "expires_at": "2026-11-06T00:10:00+00:00"}


def _issue_mock() -> AsyncMock:
    return AsyncMock(return_value=_ISSUED)


def _consume(payload: dict | None) -> AsyncMock:
    return AsyncMock(return_value=payload)


def _payload(**extra) -> dict:
    return {"tenant_id": _TENANT, "staff_id": 42, "created_at": "x", "nonce": "n", **extra}


async def _callback(client, guild_id: str = _GUILD_OWN):
    return await client.get(
        "/api/v1/discord/oauth/callback",
        params={"state": "s", "guild_id": guild_id, "code": "c"},
    )


def _exchange(guild_id: str):
    """code の交換を差し替える（この試験は用途ごとの行と戻り先を見る。交換そのものは test_discord_oauth.py）。"""
    return patch(
        "app.routers.discord_oauth._exchange_code_for_guild_id",
        AsyncMock(return_value=guild_id),
    )


# ---------------------------------------------------------------------------
# 1〜4: 招待の開始
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_01_start_empty_body_is_customer(client, monkeypatch):
    monkeypatch.setenv("DISCORD_CLIENT_SECRET", "test-secret-not-real")
    issue = _issue_mock()
    with patch("app.routers.discord_oauth.oauth_state.issue_state", issue):
        res = await client.post("/api/v1/discord/oauth/start", json={})
    assert res.status_code == 200
    assert issue.call_args.kwargs["extra"] == {"purpose": "customer"}


@pytest.mark.asyncio
async def test_02_start_own_with_edit_permission(client, monkeypatch):
    monkeypatch.setenv("DISCORD_CLIENT_SECRET", "test-secret-not-real")
    issue = _issue_mock()
    with patch("app.routers.discord_oauth.oauth_state.issue_state", issue):
        res = await client.post("/api/v1/discord/oauth/start", json={"purpose": "own"})
    assert res.status_code == 200
    assert issue.call_args.kwargs["extra"] == {"purpose": "own"}


@pytest.mark.asyncio
async def test_03_start_own_without_edit_permission_is_403(client, perms):
    perms.clear()
    perms.update(_PERMS_NO_EDIT)
    issue = _issue_mock()
    with patch("app.routers.discord_oauth.oauth_state.issue_state", issue):
        res = await client.post("/api/v1/discord/oauth/start", json={"purpose": "own"})
    assert res.status_code == 403
    issue.assert_not_called()


@pytest.mark.asyncio
async def test_04_start_unknown_purpose_is_422(client):
    issue = _issue_mock()
    with patch("app.routers.discord_oauth.oauth_state.issue_state", issue):
        res = await client.post("/api/v1/discord/oauth/start", json={"purpose": "x"})
    assert res.status_code == 422
    issue.assert_not_called()


# ---------------------------------------------------------------------------
# 5〜8, 11: 戻り
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_05_callback_own_creates_own_row_and_returns_to_own_tab(client, factory):
    with patch(
        "app.routers.discord_oauth.oauth_state.consume_state", _consume(_payload(purpose="own"))
    ), _exchange(_GUILD_OWN):
        res = await _callback(client)
    assert res.status_code in (302, 307)
    assert res.headers["location"] == f"{_FRONTEND}/admin/discord-config?tab=own&discord_status=connected"
    assert await _rows(factory) == [(_TENANT, "own", _GUILD_OWN)]


@pytest.mark.asyncio
async def test_06_callback_without_purpose_is_customer(client, factory):
    with patch(
        "app.routers.discord_oauth.oauth_state.consume_state", _consume(_payload())
    ), _exchange(_GUILD_CUSTOMER):
        res = await _callback(client, _GUILD_CUSTOMER)
    assert res.headers["location"] == f"{_FRONTEND}/channels?discord_status=connected"
    assert await _rows(factory) == [(_TENANT, "customer", _GUILD_CUSTOMER)]


@pytest.mark.asyncio
async def test_07_callback_unknown_purpose_is_invalid_payload(client, factory):
    with patch("app.routers.discord_oauth.oauth_state.consume_state", _consume(_payload(purpose="x"))):
        res = await _callback(client)
    assert res.headers["location"] == f"{_FRONTEND}/channels?discord_status=error&reason=invalid_payload"
    assert await _rows(factory) == []


@pytest.mark.asyncio
async def test_08_registering_own_keeps_customer_row(client, factory):
    await _insert(factory, _TENANT, "customer", _GUILD_CUSTOMER)
    with patch(
        "app.routers.discord_oauth.oauth_state.consume_state", _consume(_payload(purpose="own"))
    ), _exchange(_GUILD_OWN):
        res = await _callback(client)
    assert res.status_code in (302, 307)
    assert await _rows(factory) == [
        (_TENANT, "customer", _GUILD_CUSTOMER),
        (_TENANT, "own", _GUILD_OWN),
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("owner", [(_OTHER_TENANT, "customer"), (_TENANT, "customer")])
async def test_11_callback_guild_already_registered(client, factory, owner):
    """別の会社、または同じ会社の別の用途で登録済みのサーバーは 500 にならず戻り先で知らせる。"""
    await _insert(factory, owner[0], owner[1], _GUILD_OTHER)
    before = await _rows(factory)
    with patch(
        "app.routers.discord_oauth.oauth_state.consume_state", _consume(_payload(purpose="own"))
    ), _exchange(_GUILD_OTHER):
        res = await _callback(client, _GUILD_OTHER)
    assert res.status_code in (302, 307)
    assert res.headers["location"] == (
        f"{_FRONTEND}/admin/discord-config?tab=own&discord_status=error&reason=guild_already_registered"
    )
    assert await _rows(factory) == before


# ---------------------------------------------------------------------------
# 9: 取得と解除は用途ごと
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_09_get_and_delete_are_per_purpose(client, factory):
    await _insert(factory, _TENANT, "customer", _GUILD_CUSTOMER)
    await _insert(factory, _TENANT, "own", _GUILD_OWN)

    res = await client.get("/api/v1/admin/discord-config")
    assert res.status_code == 200
    assert res.json()["guild_id"] == _GUILD_CUSTOMER

    res = await client.get("/api/v1/admin/discord-config/own")
    assert res.status_code == 200
    assert res.json()["guild_id"] == _GUILD_OWN

    res = await client.delete("/api/v1/admin/discord-config")
    assert res.status_code == 204
    assert await _rows(factory) == [(_TENANT, "own", _GUILD_OWN)]

    await _insert(factory, _TENANT, "customer", _GUILD_CUSTOMER)
    res = await client.delete("/api/v1/admin/discord-config/own")
    assert res.status_code == 204
    assert await _rows(factory) == [(_TENANT, "customer", _GUILD_CUSTOMER)]

    res = await client.get("/api/v1/admin/discord-config/own")
    assert res.json()["guild_id"] is None


# ---------------------------------------------------------------------------
# 10, 12: 受け取り係（本物の SQL を SQLite で流す）
# ---------------------------------------------------------------------------


def _gateway(factory) -> JarvisDiscordClient:
    return JarvisDiscordClient(db_factory=factory, database_url="postgresql://unused")


@pytest.mark.asyncio
async def test_10_gateway_resolves_customer_only(factory):
    await _insert(factory, _TENANT, "customer", _GUILD_CUSTOMER)
    await _insert(factory, _TENANT, "own", _GUILD_OWN)
    gw = _gateway(factory)
    assert await gw._resolve_tenant_id(_GUILD_CUSTOMER) == _TENANT
    assert await gw._resolve_tenant_id(_GUILD_OWN) is None


def _message(guild_id: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=1,
        author=SimpleNamespace(bot=False),
        guild=SimpleNamespace(id=int(guild_id)),
    )


@pytest.mark.asyncio
async def test_12_gateway_ignores_own_server_messages(factory):
    await _insert(factory, _TENANT, "customer", _GUILD_CUSTOMER)
    await _insert(factory, _TENANT, "own", _GUILD_OWN)
    gw = _gateway(factory)
    target = "app.discord_gateway.client.ticket_channel_writer.process_ticket_channel_message"
    with patch(target, AsyncMock(return_value=None)) as writer:
        await gw.on_message(_message(_GUILD_OWN))
        writer.assert_not_called()
        await gw.on_message(_message(_GUILD_CUSTOMER))
        writer.assert_awaited_once()
