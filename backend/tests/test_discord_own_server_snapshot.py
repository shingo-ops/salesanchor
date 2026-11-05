"""自社用 Discord サーバーの今の姿の読み取り（discord-server-management 便2）の試験。

Discord への呼び出しは AsyncMock に差し替える（本物の Discord には繋がない）。
表は conftest の SQLite 版を使う。
"""
from __future__ import annotations

import json
import os
from contextlib import ExitStack
from pathlib import Path
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
from app.models import User
from app.routers import discord_own_server
from app.services.discord_rest import DiscordAPIError

_TENANT = 7
_OTHER_TENANT = 8
_GUILD_CUSTOMER = "111111111111111111"
_GUILD_OWN = "222222222222222222"
_GUILD_OTHER = "333333333333333333"
_MEMBER_ID = "900000000000000001"
_URL = "/api/v1/admin/discord/own-server/snapshot"

_PERMS_FULL = {"channels.manage", "tenant.profile.view", "tenant.profile.edit"}
_PERMS_VIEW_ONLY = {"tenant.profile.view"}

_ROLES = [
    {"id": _GUILD_OWN, "name": "@everyone", "permissions": "1024", "position": 0,
     "color": 0, "hoist": False, "mentionable": False, "managed": False},
    {"id": "401", "name": "営業", "permissions": "2048", "position": 1,
     "color": 0, "hoist": True, "mentionable": True, "managed": False},
    {"id": "402", "name": "SalesAnchor", "permissions": "8", "position": 2,
     "color": 0, "hoist": False, "mentionable": False, "managed": True},
]
_CHANNELS = [
    {"id": "501", "type": 4, "name": "営業", "position": 0, "parent_id": None,
     "permission_overwrites": [
         {"id": _GUILD_OWN, "type": 0, "allow": "0", "deny": "1024"},
         {"id": "401", "type": 0, "allow": "1024", "deny": "0"},
         {"id": _MEMBER_ID, "type": 1, "allow": "1024", "deny": "0"},
     ]},
    {"id": "502", "type": 0, "name": "営業通知", "position": 1, "parent_id": "501",
     "topic": "お知らせ", "permission_overwrites": []},
]


def _mock_user() -> User:
    user = User()
    user.id = 42
    user.tenant_id = _TENANT
    user.username = "testuser"
    user.email = "test@example.com"
    user.role = "admin"
    user.is_active = True
    return user


async def _fake_discord(**kwargs):
    path = kwargs["path"]
    if path.endswith("/roles"):
        return _ROLES
    if path.endswith("/channels"):
        return _CHANNELS
    raise AssertionError(f"unexpected path {path}")


@pytest_asyncio.fixture
async def engine(test_engine, setup_test_db):
    async with test_engine.begin() as conn:
        await conn.execute(text("DELETE FROM discord_server_snapshots"))
        await conn.execute(text("DELETE FROM tenant_discord_config"))
    yield test_engine
    async with test_engine.begin() as conn:
        await conn.execute(text("DELETE FROM discord_server_snapshots"))
        await conn.execute(text("DELETE FROM tenant_discord_config"))


@pytest.fixture
def factory(engine):
    return sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture
def perms():
    return set(_PERMS_FULL)


@pytest.fixture
def discord_mock():
    return AsyncMock(side_effect=_fake_discord)


@pytest_asyncio.fixture
async def client(factory, perms, discord_mock, monkeypatch):
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "test-token")
    app = FastAPI()
    app.include_router(discord_own_server.router, prefix="/api/v1")
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
        stack.enter_context(
            patch("app.routers.discord_own_server.record_audit_log", AsyncMock(return_value=None))
        )
        stack.enter_context(
            patch("app.routers.discord_own_server.reset_tenant_context", AsyncMock(return_value=None))
        )
        stack.enter_context(
            patch("app.routers.discord_own_server.discord_api_request", discord_mock)
        )
        stack.enter_context(
            patch("app.auth.dependencies.set_tenant_context", AsyncMock(return_value=None))
        )
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test", follow_redirects=False
        ) as ac:
            yield ac


async def _insert_config(factory, tenant_id: int, purpose: str, guild_id: str) -> None:
    async with factory() as s:
        await s.execute(
            text(
                "INSERT INTO tenant_discord_config (tenant_id, purpose, guild_id)"
                " VALUES (:t, :p, :g)"
            ),
            {"t": tenant_id, "p": purpose, "g": guild_id},
        )
        await s.commit()


async def _snapshots(factory) -> list[tuple]:
    async with factory() as s:
        result = await s.execute(
            text("SELECT id, tenant_id, purpose, body, taken_by FROM discord_server_snapshots ORDER BY id")
        )
        return [tuple(r) for r in result.fetchall()]


@pytest.mark.asyncio
async def test_snapshot_saves_one_row(client, factory):
    await _insert_config(factory, _TENANT, "own", _GUILD_OWN)
    resp = await client.post(_URL)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["role_count"] == 3
    assert data["channel_count"] == 2
    assert isinstance(data["snapshot_id"], int)
    rows = await _snapshots(factory)
    assert len(rows) == 1
    assert rows[0][1] == _TENANT
    assert rows[0][2] == "own"
    assert rows[0][4] == 42


@pytest.mark.asyncio
async def test_snapshot_body_has_no_guild_or_member_ids(client, factory):
    await _insert_config(factory, _TENANT, "own", _GUILD_OWN)
    resp = await client.post(_URL)
    assert resp.status_code == 200, resp.text
    raw = (await _snapshots(factory))[0][3]
    body = json.loads(raw)
    assert body["version"] == 1
    everyone = [r for r in body["roles"] if r["name"] == "@everyone"][0]
    assert everyone["discord_id"] == "@everyone"
    category = [c for c in body["channels"] if c["discord_id"] == "501"][0]
    assert len(category["permission_overwrites"]) == 2
    assert category["permission_overwrites"][0]["target"] == "@everyone"
    assert category["member_overwrite_count"] == 1
    assert _MEMBER_ID not in raw
    assert _GUILD_OWN not in raw


@pytest.mark.asyncio
async def test_snapshot_customer_only_returns_422(client, factory, discord_mock):
    await _insert_config(factory, _TENANT, "customer", _GUILD_CUSTOMER)
    resp = await client.post(_URL)
    assert resp.status_code == 422
    assert await _snapshots(factory) == []
    discord_mock.assert_not_called()


@pytest.mark.asyncio
async def test_snapshot_other_tenant_only_returns_422(client, factory, discord_mock):
    await _insert_config(factory, _OTHER_TENANT, "own", _GUILD_OTHER)
    resp = await client.post(_URL)
    assert resp.status_code == 422
    assert await _snapshots(factory) == []
    discord_mock.assert_not_called()


@pytest.mark.asyncio
async def test_snapshot_without_bot_token_returns_503(client, factory, monkeypatch):
    await _insert_config(factory, _TENANT, "own", _GUILD_OWN)
    monkeypatch.delenv("DISCORD_BOT_TOKEN", raising=False)
    resp = await client.post(_URL)
    assert resp.status_code == 503
    assert await _snapshots(factory) == []


@pytest.mark.asyncio
async def test_snapshot_discord_error_returns_502(client, factory, discord_mock):
    await _insert_config(factory, _TENANT, "own", _GUILD_OWN)
    discord_mock.side_effect = DiscordAPIError("x", status_code=403)
    resp = await client.post(_URL)
    assert resp.status_code == 502
    assert await _snapshots(factory) == []


@pytest.mark.asyncio
async def test_snapshot_requires_edit_permission(client, factory, perms, discord_mock):
    await _insert_config(factory, _TENANT, "own", _GUILD_OWN)
    perms.clear()
    perms.update(_PERMS_VIEW_ONLY)
    resp = await client.post(_URL)
    assert resp.status_code == 403
    discord_mock.assert_not_called()


@pytest.mark.asyncio
async def test_snapshot_calls_discord_get_twice(client, factory, discord_mock):
    await _insert_config(factory, _TENANT, "own", _GUILD_OWN)
    resp = await client.post(_URL)
    assert resp.status_code == 200, resp.text
    assert discord_mock.await_count == 2
    methods = [c.kwargs["method"] for c in discord_mock.await_args_list]
    paths = [c.kwargs["path"] for c in discord_mock.await_args_list]
    assert methods == ["GET", "GET"]
    assert paths == [f"/guilds/{_GUILD_OWN}/roles", f"/guilds/{_GUILD_OWN}/channels"]


def test_router_has_only_get_calls_to_discord():
    source = Path(discord_own_server.__file__).read_text(encoding="utf-8")
    for forbidden in ('method="POST"', 'method="PATCH"', 'method="PUT"', 'method="DELETE"', '"DELETE"'):
        assert forbidden not in source, forbidden
    assert source.count('method="GET"') == 2


def test_insert_sql_casts_jsonb_only_on_postgresql():
    pg = SimpleNamespace(get_bind=lambda: SimpleNamespace(dialect=SimpleNamespace(name="postgresql")))
    lite = SimpleNamespace(get_bind=lambda: SimpleNamespace(dialect=SimpleNamespace(name="sqlite")))
    assert "CAST(:body AS JSONB)" in discord_own_server._insert_sql(pg)
    assert "CAST(:body AS JSONB)" not in discord_own_server._insert_sql(lite)


def test_build_snapshot_body_empty():
    assert discord_own_server.build_snapshot_body([], [], "1") == {
        "version": 1,
        "roles": [],
        "channels": [],
    }
