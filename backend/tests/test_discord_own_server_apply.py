"""自社用 Discord サーバーへの反映（discord-server-management 便3b）の API の試験。

Discord への呼び出しは AsyncMock に差し替える（読み取りと書き込みは別の作り物。本物の Discord には繋がない）。
Redis は set・delete を持つ作り物。表は conftest の SQLite 版を使う。
"""
from __future__ import annotations

import copy
import json
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
from app.models import User
from app.routers import discord_own_server
from app.services.discord_blueprint import BLUEPRINT_DIR, NOTICE_ROOMS

_TENANT = 7
_OTHER_TENANT = 8
_GUILD_OWN = "222222222222222222"
_BOT_USER = "800000000000000001"
_BOT_ROLE = "1567709769337409100"
_TEXT_CAT = "1567709769337409726"
_VOICE_CAT = "1567709769337409727"
_GENERAL = "1567709769337409728"
_VOICE = "1567709769337409729"
_EVERYONE_PERMS = "2248473465835073"
_BOT_PERMS = "805432407"
_PLAN_URL = "/api/v1/admin/discord/own-server/plan"
_APPLY_URL = "/api/v1/admin/discord/own-server/apply"
_PERMS_FULL = {"channels.manage", "tenant.profile.view", "tenant.profile.edit"}
_PERMS_VIEW_ONLY = {"tenant.profile.view"}


def _roles() -> list[dict]:
    return [
        {"id": _GUILD_OWN, "name": "@everyone", "permissions": _EVERYONE_PERMS, "position": 0,
         "color": 0, "hoist": False, "mentionable": False, "managed": False},
        {"id": _BOT_ROLE, "name": "SalesAnchor", "permissions": _BOT_PERMS, "position": 1,
         "color": 0, "hoist": False, "mentionable": False, "managed": True},
    ]


def _channels() -> list[dict]:
    return [
        {"id": _TEXT_CAT, "type": 4, "name": "テキストチャンネル", "parent_id": None, "permission_overwrites": []},
        {"id": _VOICE_CAT, "type": 4, "name": "ボイスチャンネル", "parent_id": None, "permission_overwrites": []},
        {"id": _GENERAL, "type": 0, "name": "一般", "parent_id": _TEXT_CAT, "topic": None,
         "permission_overwrites": []},
        {"id": _VOICE, "type": 2, "name": "ボイス", "parent_id": _VOICE_CAT, "permission_overwrites": []},
    ]


def _bp_data() -> dict:
    # 第2段 2b で足した「スタッフ」は本番の Discord にまだ無いので、本番の今の形と比べる試験では除く
    # （「スタッフ」が確認で「作る」1 行になることは test_discord_own_staff_sync.py で確かめる）
    data = json.loads((BLUEPRINT_DIR / "tenant_1.json").read_text(encoding="utf-8"))
    data["roles"] = [r for r in data["roles"] if r["key"] != "staff"]
    # 第2段 2c で足した知らせの部屋 3 つも本番の Discord にまだ無いので除く（test_discord_notice_rooms.py で確かめる）
    data["channels"] = [c for c in data["channels"] if c["key"] not in NOTICE_ROOMS]
    # ADR-1068 で足したスタッフ登録のカテゴリと受付の部屋も本番の Discord にまだ無いので除く（test_staff_join_api.py で確かめる）
    data["categories"] = [c for c in data["categories"] if c["key"] != "staff_join_rooms"]
    data["channels"] = [c for c in data["channels"] if c["key"] != "staff_join_reception"]
    return data


def _four_kinds() -> dict:
    """ロールを作る・チャンネルを作る・チャンネルを直す・上書きを直す の 4 種類の差が出る設計図。"""
    data = _bp_data()
    data["roles"].append({"key": "newrole", "name": "新しいロール"})
    data["channels"][0]["name"] = "ippan"
    data["channels"].append({"key": "news", "name": "news", "type": "text", "category": "text_cat",
                             "topic": "お知らせ", "overwrites": []})
    data["categories"][0]["overwrites"] = [{"target": "@everyone", "deny": ["SEND_MESSAGES"]}]
    return data


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
    async with test_engine.begin() as conn:
        await conn.execute(text("DELETE FROM discord_server_apply_runs"))
        await conn.execute(text("DELETE FROM discord_server_snapshots"))
        await conn.execute(text("DELETE FROM tenant_discord_config"))
    yield test_engine
    async with test_engine.begin() as conn:
        await conn.execute(text("DELETE FROM discord_server_apply_runs"))
        await conn.execute(text("DELETE FROM discord_server_snapshots"))
        await conn.execute(text("DELETE FROM tenant_discord_config"))


@pytest.fixture
def factory(engine):
    return sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture
def perms():
    return set(_PERMS_FULL)


@pytest.fixture
def world():
    """Discord の今の姿（試験が書き換える）。"""
    return {"roles": _roles(), "channels": _channels()}


@pytest.fixture
def discord_mock(world):
    async def _fake_get(**kwargs):
        assert kwargs["method"] == "GET"
        path = kwargs["path"]
        if path.endswith("/roles"):
            return copy.deepcopy(world["roles"])
        if path.endswith("/channels"):
            return copy.deepcopy(world["channels"])
        if path == "/users/@me":
            return {"id": _BOT_USER}
        if path.endswith(f"/members/{_BOT_USER}"):
            return {"roles": [_BOT_ROLE]}
        raise AssertionError(f"unexpected path {path}")

    return AsyncMock(side_effect=_fake_get)


@pytest.fixture
def write_mock():
    counter = {"n": 900}

    async def _fake_write(**kwargs):
        if kwargs["method"] == "PUT":
            return None
        counter["n"] += 1
        return {"id": str(counter["n"])}

    return AsyncMock(side_effect=_fake_write)


@pytest.fixture
def redis_holder():
    return {"r": SimpleNamespace(set=AsyncMock(return_value=True), delete=AsyncMock(return_value=1))}


@pytest.fixture
def bp_file(tmp_path):
    path = tmp_path / "tenant_7.json"
    path.write_text(json.dumps(_four_kinds(), ensure_ascii=False), encoding="utf-8")
    return path


def _write_bp(path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


@pytest_asyncio.fixture
async def client(factory, perms, discord_mock, write_mock, redis_holder, bp_file, monkeypatch):
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
        stack.enter_context(patch("app.routers.discord_own_server.discord_api_request", discord_mock))
        stack.enter_context(patch("app.services.discord_blueprint_apply.discord_api_request", write_mock))
        stack.enter_context(patch("app.routers.discord_own_server.get_redis", lambda: redis_holder["r"]))
        stack.enter_context(
            patch("app.routers.discord_own_server.blueprint_path", lambda tenant_id: bp_file)
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
            text("INSERT INTO tenant_discord_config (tenant_id, purpose, guild_id) VALUES (:t, :p, :g)"),
            {"t": tenant_id, "p": purpose, "g": guild_id},
        )
        await s.commit()


async def _run_rows(factory) -> list[tuple]:
    async with factory() as s:
        result = await s.execute(text("SELECT plan_digest, result, purpose, applied_by FROM discord_server_apply_runs"))
        return [tuple(r) for r in result.all()]


async def _plan_digest(client) -> str:
    resp = await client.get(_PLAN_URL)
    assert resp.status_code == 200, resp.text
    return resp.json()["plan_digest"]


@pytest.mark.asyncio
async def test_apply_four_kinds_writes_four_times_and_records_one_run(client, factory, write_mock, redis_holder):
    await _insert_config(factory, _TENANT, "own", _GUILD_OWN)
    digest = await _plan_digest(client)
    resp = await client.post(_APPLY_URL, json={"plan_digest": digest})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["success_count"] == 4
    assert data["blocked_count"] == 0
    assert data["failed_count"] == 0
    assert write_mock.await_count == 4
    rows = await _run_rows(factory)
    assert len(rows) == 1
    assert rows[0][0] == digest
    assert rows[0][2] == "own"
    assert rows[0][3] == 42
    assert data["run_id"] > 0
    assert len(json.loads(rows[0][1])["rows"]) == 4
    redis_holder["r"].set.assert_awaited_once()
    assert redis_holder["r"].set.await_args.kwargs.get("nx") is True
    redis_holder["r"].delete.assert_awaited_once()


@pytest.mark.asyncio
async def test_apply_never_sends_delete_and_delete_candidates_remain(client, factory, bp_file, write_mock):
    await _insert_config(factory, _TENANT, "own", _GUILD_OWN)
    data = _bp_data()
    data["roles"].append({"key": "newrole", "name": "新しいロール"})
    data["channels"] = []  # 文字のチャンネルを 1 つ外す → 消す候補になる
    _write_bp(bp_file, data)
    digest = await _plan_digest(client)
    resp = await client.post(_APPLY_URL, json={"plan_digest": digest})
    assert resp.status_code == 200, resp.text
    assert write_mock.await_count >= 1
    methods = {c.kwargs["method"] for c in write_mock.await_args_list}
    assert methods <= {"POST", "PATCH", "PUT"}
    after = await client.get(_PLAN_URL)
    assert after.status_code == 200
    candidates = after.json()["delete_candidates"]
    assert [(c["kind"], c["discord_id"]) for c in candidates] == [("channel", _GENERAL)]


@pytest.mark.asyncio
async def test_apply_blocked_row_is_not_written(client, factory, bp_file, world, write_mock):
    await _insert_config(factory, _TENANT, "own", _GUILD_OWN)
    world["roles"].append({"id": "701", "name": "営業", "permissions": "0", "position": 1,
                           "color": 0, "hoist": False, "mentionable": False, "managed": False})
    data = _bp_data()
    data["roles"].append({"key": "sales", "discord_id": "701", "name": "営業チーム"})
    _write_bp(bp_file, data)
    digest = await _plan_digest(client)
    resp = await client.post(_APPLY_URL, json={"plan_digest": digest})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["blocked_count"] == 1
    assert body["success_count"] == 0
    assert [r["reason"] for r in body["results"]] == ["role_above_bot"]
    assert not any("/roles/701" in c.kwargs["path"] for c in write_mock.await_args_list)
    write_mock.assert_not_called()


@pytest.mark.asyncio
async def test_apply_with_another_digest_returns_409_and_writes_nothing(client, factory, write_mock, redis_holder):
    await _insert_config(factory, _TENANT, "own", _GUILD_OWN)
    resp = await client.post(_APPLY_URL, json={"plan_digest": "0" * 64})
    assert resp.status_code == 409
    write_mock.assert_not_called()
    assert await _run_rows(factory) == []
    redis_holder["r"].delete.assert_awaited_once()


@pytest.mark.asyncio
async def test_apply_while_another_apply_runs_returns_409(client, factory, discord_mock, write_mock, redis_holder):
    await _insert_config(factory, _TENANT, "own", _GUILD_OWN)
    redis_holder["r"].set = AsyncMock(return_value=False)
    resp = await client.post(_APPLY_URL, json={"plan_digest": "0" * 64})
    assert resp.status_code == 409
    discord_mock.assert_not_called()
    write_mock.assert_not_called()
    redis_holder["r"].delete.assert_not_called()


@pytest.mark.asyncio
async def test_apply_without_redis_returns_503(client, factory, discord_mock, write_mock, redis_holder):
    await _insert_config(factory, _TENANT, "own", _GUILD_OWN)
    redis_holder["r"] = None
    resp = await client.post(_APPLY_URL, json={"plan_digest": "0" * 64})
    assert resp.status_code == 503
    discord_mock.assert_not_called()
    write_mock.assert_not_called()


@pytest.mark.asyncio
async def test_apply_without_own_server_returns_422(client, factory, discord_mock, write_mock):
    await _insert_config(factory, _OTHER_TENANT, "own", _GUILD_OWN)
    resp = await client.post(_APPLY_URL, json={"plan_digest": "0" * 64})
    assert resp.status_code == 422
    discord_mock.assert_not_called()
    write_mock.assert_not_called()


@pytest.mark.asyncio
async def test_apply_without_blueprint_file_returns_404(client, factory, tmp_path, write_mock):
    await _insert_config(factory, _TENANT, "own", _GUILD_OWN)
    missing = tmp_path / "none" / "tenant_7.json"
    with patch("app.routers.discord_own_server.blueprint_path", lambda tenant_id: missing):
        resp = await client.post(_APPLY_URL, json={"plan_digest": "0" * 64})
    assert resp.status_code == 404
    write_mock.assert_not_called()


@pytest.mark.asyncio
async def test_unreadable_blueprint_file_returns_422_for_apply_and_plan(client, factory, discord_mock, write_mock):
    await _insert_config(factory, _TENANT, "own", _GUILD_OWN)
    with patch("app.routers.discord_own_server.load_blueprint", side_effect=OSError("cannot read")):
        applied = await client.post(_APPLY_URL, json={"plan_digest": "0" * 64})
        checked = await client.get(_PLAN_URL)
    assert applied.status_code == 422
    assert checked.status_code == 422
    assert "cannot read" not in applied.text
    discord_mock.assert_not_called()
    write_mock.assert_not_called()


@pytest.mark.asyncio
async def test_apply_view_only_returns_403(client, factory, perms, discord_mock, write_mock):
    await _insert_config(factory, _TENANT, "own", _GUILD_OWN)
    perms.clear()
    perms.update(_PERMS_VIEW_ONLY)
    resp = await client.post(_APPLY_URL, json={"plan_digest": "0" * 64})
    assert resp.status_code == 403
    discord_mock.assert_not_called()
    write_mock.assert_not_called()


@pytest.mark.asyncio
async def test_apply_response_and_record_do_not_contain_the_guild_id(client, factory):
    await _insert_config(factory, _TENANT, "own", _GUILD_OWN)
    digest = await _plan_digest(client)
    resp = await client.post(_APPLY_URL, json={"plan_digest": digest})
    assert resp.status_code == 200, resp.text
    assert _GUILD_OWN not in resp.text
    rows = await _run_rows(factory)
    assert len(rows) == 1
    assert _GUILD_OWN not in rows[0][1]
