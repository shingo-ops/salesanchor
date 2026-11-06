"""アプリの役割を自社用 Discord サーバーの確認・反映に含める（discord-server-management 第2段 2a-2）の試験。

build_plan は純粋な関数なので Discord の返事の作り物で直接呼ぶ。
API の試験は Discord を AsyncMock に差し替える（本物の Discord には繋がない）。表は conftest の SQLite 版を使う。
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
from app.routers import roles as roles_router
from app.services.discord_blueprint import APP_ROLE_KEY_PREFIX, Blueprint, build_plan, hex_color_to_int
from app.services.discord_blueprint_apply import apply_plan

_TENANT = 7
_G = "222222222222222222"
_BOT_USER = "800000000000000001"
_BOT_ROLE = "1567709769337409100"
_PLAN_URL = "/api/v1/admin/discord/own-server/plan"
_APPLY_URL = "/api/v1/admin/discord/own-server/apply"
_PERMS_FULL = {"channels.manage", "tenant.profile.view", "tenant.profile.edit"}
_GRAY = "#6c757d"


def _roles() -> list[dict]:
    return [
        {"id": _G, "name": "@everyone", "permissions": "0", "position": 0,
         "color": 0, "hoist": False, "mentionable": False, "managed": False},
        {"id": _BOT_ROLE, "name": "SalesAnchor", "permissions": "0", "position": 10,
         "color": 0, "hoist": False, "mentionable": False, "managed": True},
    ]


def _d_role(role_id: str, name: str, color: int = 0, position: int = 1) -> dict:
    return {"id": role_id, "name": name, "permissions": "0", "position": position,
            "color": color, "hoist": False, "mentionable": False, "managed": False}


def _bp_data() -> dict:
    return {
        "version": 1,
        "roles": [{"key": "everyone", "discord_id": "@everyone", "name": "@everyone", "permissions": []}],
        "categories": [],
        "channels": [],
    }


def _app(role_id: int, name: str, color: str = _GRAY, discord_role_id: str | None = None) -> dict:
    return {"id": role_id, "name": name, "color": color, "discord_role_id": discord_role_id}


def _plan(app_roles, d_roles: list[dict] | None = None, bp_data: dict | None = None) -> dict:
    bp = Blueprint.model_validate(bp_data if bp_data is not None else _bp_data())
    return build_plan(bp, _roles() + (d_roles or []), [], _G, [_BOT_ROLE], app_roles=app_roles)


def _app_changes(plan: dict, key: str) -> list[dict]:
    return [c for c in plan["changes"] if c["key"] == key]


def _app_actions(plan: dict, key: str) -> list[dict]:
    return [a for c, a in zip(plan["changes"], plan["actions"]) if c["key"] == key]


# ---------------------------------------------------------------- 純粋な試験


def test_app_role_none_keeps_plan_identical():
    bp = Blueprint.model_validate(_bp_data())
    omitted = build_plan(bp, _roles(), [], _G, [_BOT_ROLE])
    explicit_none = build_plan(bp, _roles(), [], _G, [_BOT_ROLE], app_roles=None)
    assert omitted == explicit_none
    assert "app_roles" not in omitted
    with_empty = build_plan(bp, _roles(), [], _G, [_BOT_ROLE], app_roles=[])
    assert with_empty["app_roles"] == []
    assert with_empty["plan_digest"] == omitted["plan_digest"]


def test_app_role_create_when_no_same_name():
    plan = _plan([_app(5, "営業")])
    key = f"{APP_ROLE_KEY_PREFIX}5"
    rows = _app_changes(plan, key)
    assert len(rows) == 1
    assert rows[0]["kind"] == "create_role"
    act = _app_actions(plan, key)[0]
    assert act["method"] == "POST"
    assert act["path"] == "/guilds/{guild}/roles"
    assert act["json"]["permissions"] == "0"
    assert act["creates"] == key
    assert plan["app_roles"] == [{"role_id": 5, "name": "営業", "state": "create", "reason": None}]


def test_app_role_link_when_one_same_name():
    plan = _plan([_app(5, "営業")], [_d_role("901", "営業")])
    key = f"{APP_ROLE_KEY_PREFIX}5"
    rows = _app_changes(plan, key)
    assert len(rows) == 1
    assert rows[0]["kind"] == "link_role"
    assert rows[0]["after"] == "901"
    assert _app_actions(plan, key)[0]["method"] == "DB"
    assert all(d["discord_id"] != "901" for d in plan["delete_candidates"])
    assert plan["app_roles"][0]["state"] == "link"


def test_app_role_ambiguous_blocks_and_sends_nothing():
    plan = _plan([_app(5, "営業")], [_d_role("901", "営業"), _d_role("902", "営業")])
    key = f"{APP_ROLE_KEY_PREFIX}5"
    blocked = [b for b in plan["blocked"] if b["key"] == key]
    assert len(blocked) == 1
    assert blocked[0]["reason"] == "ambiguous"
    assert _app_changes(plan, key) == []
    assert not {"901", "902"} & {d["discord_id"] for d in plan["delete_candidates"]}
    assert plan["app_roles"][0]["state"] == "blocked"
    assert plan["app_roles"][0]["reason"] == "ambiguous"


def test_app_role_rename_patches_same_id():
    plan = _plan([_app(5, "セールス", discord_role_id="901")], [_d_role("901", "営業", color=hex_color_to_int(_GRAY))])
    key = f"{APP_ROLE_KEY_PREFIX}5"
    rows = _app_changes(plan, key)
    assert len(rows) == 1
    assert rows[0]["field"] == "name"
    assert rows[0]["before"] == "営業"
    assert rows[0]["after"] == "セールス"
    act = _app_actions(plan, key)[0]
    assert act["method"] == "PATCH"
    assert act["path"] == "/guilds/{guild}/roles/901"
    assert not [a for a in plan["actions"] if a["method"] == "POST"]
    assert plan["app_roles"][0]["state"] == "update"


def test_app_role_color_patch():
    plan = _plan([_app(5, "営業", color="#ff0000", discord_role_id="901")], [_d_role("901", "営業", color=0)])
    key = f"{APP_ROLE_KEY_PREFIX}5"
    rows = _app_changes(plan, key)
    assert len(rows) == 1
    assert rows[0]["field"] == "color"
    assert _app_actions(plan, key)[0]["json"] == {"colors": {"primary_color": 16711680}}


def test_app_role_unchanged():
    color = hex_color_to_int(_GRAY)
    plan = _plan(
        [_app(5, "営業", discord_role_id="901"), _app(6, "事務", discord_role_id="902")],
        [_d_role("901", "営業", color=color), _d_role("902", "事務", color=color)],
    )
    assert plan["changes"] == []
    assert len(plan["app_roles"]) == 2
    assert [a["state"] for a in plan["app_roles"]] == ["unchanged", "unchanged"]


def test_app_role_linked_missing_on_discord():
    plan = _plan([_app(5, "営業", discord_role_id="999")])
    key = f"{APP_ROLE_KEY_PREFIX}5"
    blocked = [b for b in plan["blocked"] if b["key"] == key]
    assert [b["reason"] for b in blocked] == ["app_role_missing_on_discord"]
    assert plan["app_roles"][0]["reason"] == "app_role_missing_on_discord"


def test_app_role_name_in_blueprint():
    data = _bp_data()
    data["roles"].append({"key": "staff", "name": "staff"})
    plan = _plan([_app(5, "staff")], bp_data=data)
    key = f"{APP_ROLE_KEY_PREFIX}5"
    blocked = [b for b in plan["blocked"] if b["key"] == key]
    assert [b["reason"] for b in blocked] == ["name_in_blueprint"]
    assert _app_changes(plan, key) == []
    assert plan["app_roles"][0]["reason"] == "name_in_blueprint"


def test_app_role_above_bot_is_blocked():
    plan = _plan(
        [_app(5, "セールス", discord_role_id="901")],
        [_d_role("901", "営業", color=hex_color_to_int(_GRAY), position=10)],
    )
    key = f"{APP_ROLE_KEY_PREFIX}5"
    blocked = [b for b in plan["blocked"] if b["key"] == key]
    assert [b["reason"] for b in blocked] == ["role_above_bot"]
    assert _app_changes(plan, key) == []
    assert plan["app_roles"][0]["state"] == "blocked"
    assert plan["app_roles"][0]["reason"] == "role_above_bot"


def test_app_role_name_search_skips_linked_ids():
    color = hex_color_to_int(_GRAY)
    plan = _plan(
        [_app(5, "X役", discord_role_id="901"), _app(6, "Y役")],
        [_d_role("901", "Y役", color=color)],
    )
    states = {a["role_id"]: a["state"] for a in plan["app_roles"]}
    assert states == {5: "update", 6: "create"}
    assert [c["kind"] for c in _app_changes(plan, f"{APP_ROLE_KEY_PREFIX}6")] == ["create_role"]


def test_hex_color_to_int():
    assert hex_color_to_int("#6c757d") == 7107965  # 0x6c757d。カードの 7108989 は計算違い
    assert hex_color_to_int(None) == 0
    assert hex_color_to_int("red") == 0


# ---------------------------------------------------------------- 反映の係の試験


@pytest.mark.asyncio
async def test_apply_db_row_does_not_call_discord():
    plan = {
        "changes": [{"kind": "link_role", "key": f"{APP_ROLE_KEY_PREFIX}5", "name": "営業", "field": None}],
        "blocked": [],
        "actions": [{"method": "DB", "path": "", "json": {"discord_role_id": "901"}, "creates": None}],
    }
    fake = AsyncMock()
    with patch("app.services.discord_blueprint_apply.discord_api_request", fake):
        results = await apply_plan(plan, _G, "tok")
    assert fake.call_count == 0
    assert len(results) == 1
    assert results[0]["status"] == "success"
    assert results[0]["discord_id"] == "901"


# ---------------------------------------------------------------- 画面の口の試験


def _mock_user() -> User:
    user = User()
    user.id = 42
    user.tenant_id = _TENANT
    user.username = "testuser"
    user.email = "test@example.com"
    user.role = "admin"
    user.is_active = True
    return user


async def _clean(conn) -> None:
    await conn.execute(text("DELETE FROM discord_server_apply_runs"))
    await conn.execute(text("DELETE FROM discord_server_snapshots"))
    await conn.execute(text("DELETE FROM tenant_discord_config"))
    await conn.execute(text("DELETE FROM user_roles"))
    await conn.execute(text("DELETE FROM role_permissions"))
    await conn.execute(text("DELETE FROM discord_retired_roles"))
    await conn.execute(text("DELETE FROM roles"))


@pytest_asyncio.fixture
async def engine(test_engine, setup_test_db):
    async with test_engine.begin() as conn:
        await _clean(conn)
    yield test_engine
    async with test_engine.begin() as conn:
        await _clean(conn)


@pytest.fixture
def factory(engine):
    return sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture
def perms():
    return set(_PERMS_FULL)


@pytest.fixture
def world():
    """Discord の今の姿（試験が書き換える）。"""
    return {"roles": _roles(), "channels": []}


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
        counter["n"] += 1
        return {"id": str(counter["n"])}

    return AsyncMock(side_effect=_fake_write)


@pytest.fixture
def redis_holder():
    return {"r": SimpleNamespace(set=AsyncMock(return_value=True), delete=AsyncMock(return_value=1))}


@pytest.fixture
def bp_file(tmp_path):
    path = tmp_path / "tenant_7.json"
    path.write_text(json.dumps(_bp_data(), ensure_ascii=False), encoding="utf-8")
    return path


@pytest_asyncio.fixture
async def client(factory, perms, discord_mock, write_mock, redis_holder, bp_file, monkeypatch):
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "test-token")
    app = FastAPI()
    app.include_router(discord_own_server.router, prefix="/api/v1")
    app.include_router(roles_router.router, prefix="/api/v1")
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
        stack.enter_context(patch("app.routers.roles.record_audit_log", AsyncMock(return_value=None)))
        stack.enter_context(patch("app.routers.roles.reset_tenant_context", AsyncMock(return_value=None)))
        stack.enter_context(
            patch("app.routers.roles.invalidate_tenant_permissions", AsyncMock(return_value=None))
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


async def _insert_role(factory, role_id: int, name: str, system_key: str | None = None,
                       discord_role_id: str | None = None, priority: int = 10) -> None:
    async with factory() as s:
        await s.execute(
            text(
                "INSERT INTO roles (id, tenant_id, name, color, priority, is_system, system_key, discord_role_id)"
                " VALUES (:id, :t, :n, :c, :p, :sys, :sk, :did)"
            ),
            {"id": role_id, "t": _TENANT, "n": name, "c": _GRAY, "p": priority,
             "sys": system_key is not None, "sk": system_key, "did": discord_role_id},
        )
        await s.commit()


async def _scalar_rows(factory, sql: str) -> list[tuple]:
    async with factory() as s:
        result = await s.execute(text(sql))
        return [tuple(r) for r in result.all()]


@pytest.mark.asyncio
async def test_plan_lists_app_roles_without_hidden_admin(client, factory):
    await _insert_config(factory, _TENANT, "own", _G)
    await _insert_role(factory, 1, "営業")
    await _insert_role(factory, 2, "事務")
    await _insert_role(factory, 3, "管理者", system_key="admin")
    resp = await client.get(_PLAN_URL)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert len(data["app_roles"]) == 2
    assert [a["name"] for a in data["app_roles"]] == ["営業", "事務"]


@pytest.mark.asyncio
async def test_apply_writes_discord_role_id_for_create_and_link(client, factory, world, write_mock):
    await _insert_config(factory, _TENANT, "own", _G)
    await _insert_role(factory, 1, "営業")
    await _insert_role(factory, 2, "事務")
    world["roles"].append(_d_role("777", "事務", color=hex_color_to_int(_GRAY)))
    async with factory() as s:
        await s.execute(text("INSERT INTO discord_retired_roles (discord_role_id) VALUES ('777')"))
        await s.commit()

    resp = await client.get(_PLAN_URL)
    assert resp.status_code == 200, resp.text
    digest = resp.json()["plan_digest"]
    resp = await client.post(_APPLY_URL, json={"plan_digest": digest})
    assert resp.status_code == 200, resp.text
    assert resp.json()["success_count"] == 2

    rows = await _scalar_rows(factory, "SELECT name, discord_role_id FROM roles ORDER BY id")
    assert rows == [("営業", "901"), ("事務", "777")]
    assert await _scalar_rows(factory, "SELECT discord_role_id FROM discord_retired_roles") == []
    assert write_mock.call_count == 1


@pytest.mark.asyncio
async def test_second_check_after_apply_is_unchanged(client, factory, world):
    await _insert_config(factory, _TENANT, "own", _G)
    await _insert_role(factory, 1, "営業")
    await _insert_role(factory, 2, "事務")
    color = hex_color_to_int(_GRAY)
    world["roles"].append(_d_role("777", "事務", color=color))

    resp = await client.get(_PLAN_URL)
    digest = resp.json()["plan_digest"]
    resp = await client.post(_APPLY_URL, json={"plan_digest": digest})
    assert resp.status_code == 200, resp.text

    world["roles"].append(_d_role("901", "営業", color=color))
    resp = await client.get(_PLAN_URL)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert len(data["app_roles"]) == 2
    assert [a["state"] for a in data["app_roles"]] == ["unchanged", "unchanged"]
    assert data["changes"] == []


@pytest.mark.asyncio
async def test_delete_role_moves_linked_id_to_retired(client, factory, perms):
    # 削除する人（user 42）に、消す役割より priority が高いロールを付ける
    await _insert_role(factory, 10, "上位", priority=100)
    async with factory() as s:
        await s.execute(
            text("INSERT INTO user_roles (user_id, role_id, assigned_by) VALUES (42, 10, 42)")
        )
        await s.commit()
    await _insert_role(factory, 11, "つないだ役割", discord_role_id="555")
    await _insert_role(factory, 12, "つないでいない役割")

    perms.add("roles.delete")  # 道具立ての権限の集合（client が参照している）に足す

    resp = await client.delete("/api/v1/roles/11")
    assert resp.status_code == 204, resp.text
    assert await _scalar_rows(factory, "SELECT discord_role_id FROM discord_retired_roles") == [("555",)]

    resp = await client.delete("/api/v1/roles/12")
    assert resp.status_code == 204, resp.text
    assert await _scalar_rows(factory, "SELECT discord_role_id FROM discord_retired_roles") == [("555",)]
