"""自社用 Discord サーバーの設計図と今のサーバーの差を出す確認（discord-server-management 便3a）の試験。

build_plan は純粋な関数なので Discord の返事の作り物で直接呼ぶ。
API の試験は Discord を AsyncMock に差し替える（本物の Discord には繋がない）。表は conftest の SQLite 版を使う。
"""
from __future__ import annotations

import json
import os
from contextlib import ExitStack
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
from app.services.discord_blueprint import BLUEPRINT_DIR, NOTICE_ROOMS, Blueprint, build_plan
from app.services.discord_rest import DiscordAPIError

_G = "1567709769337409000"
_BOT_ROLE = "1567709769337409100"
_TEXT_CAT = "1567709769337409726"
_VOICE_CAT = "1567709769337409727"
_GENERAL = "1567709769337409728"
_VOICE = "1567709769337409729"
_EVERYONE_PERMS = "2248473465835073"
_BOT_PERMS = "805432407"


def _production_roles() -> list[dict]:
    return [
        {"id": _G, "name": "@everyone", "permissions": _EVERYONE_PERMS, "position": 0,
         "color": 0, "hoist": False, "mentionable": False, "managed": False},
        {"id": _BOT_ROLE, "name": "SalesAnchor", "permissions": _BOT_PERMS, "position": 1,
         "color": 0, "hoist": False, "mentionable": False, "managed": True},
    ]


def _production_channels() -> list[dict]:
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
    return data


def _plan(bp_data: dict | None = None, roles: list[dict] | None = None, channels: list[dict] | None = None,
          bot_ids: list[str] | None = None) -> dict:
    bp = Blueprint.model_validate(bp_data if bp_data is not None else _bp_data())
    return build_plan(
        bp,
        roles if roles is not None else _production_roles(),
        channels if channels is not None else _production_channels(),
        _G,
        bot_ids if bot_ids is not None else [_BOT_ROLE],
    )


def _counts(plan: dict) -> tuple[int, int, int]:
    return len(plan["changes"]), len(plan["blocked"]), len(plan["delete_candidates"])


def test_production_shape_has_no_differences():
    plan = _plan()
    assert _counts(plan) == (0, 0, 0), plan


def test_voice_channels_and_managed_roles_are_never_delete_candidates():
    roles = _production_roles() + [
        {"id": "1567709769337409101", "name": "Other Bot", "permissions": "0", "position": 1,
         "color": 0, "hoist": False, "mentionable": False, "managed": True},
    ]
    channels = _production_channels() + [
        {"id": "1567709769337409730", "type": 2, "name": "もう一つの声", "parent_id": _VOICE_CAT,
         "permission_overwrites": []},
        {"id": "1567709769337409731", "type": 13, "name": "stage", "parent_id": None, "permission_overwrites": []},
    ]
    assert _counts(_plan(roles=roles, channels=channels)) == (0, 0, 0)


def _four_kinds() -> dict:
    data = _bp_data()
    data["roles"].append({"key": "newrole", "name": "新しいロール"})
    data["channels"][0]["name"] = "ippan"
    data["channels"].append({"key": "news", "name": "news", "type": "text", "category": "text_cat",
                             "topic": "お知らせ", "overwrites": []})
    data["categories"][0]["overwrites"] = [{"target": "@everyone", "deny": ["SEND_MESSAGES"]}]
    return data


def test_four_kinds_of_changes():
    plan = _plan(_four_kinds())
    kinds = sorted(r["kind"] for r in plan["changes"])
    assert kinds == sorted(["create_channel", "update_channel", "update_overwrite", "create_role"])
    assert plan["blocked"] == []
    assert plan["delete_candidates"] == []
    # 並び: ロール → カテゴリ → チャンネル → 上書き
    order = [r["kind"] for r in plan["changes"]]
    assert order[0] == "create_role"
    assert order[-1] == "update_overwrite"


def test_removing_a_text_channel_makes_a_delete_candidate():
    data = _bp_data()
    data["channels"] = []
    plan = _plan(data)
    assert plan["changes"] == []
    assert plan["blocked"] == []
    assert len(plan["delete_candidates"]) == 1
    cand = plan["delete_candidates"][0]
    assert cand["kind"] == "channel"
    assert cand["discord_id"] == _GENERAL
    assert cand["parent_name"] == "テキストチャンネル"


def test_role_at_or_above_bot_is_blocked():
    roles = _production_roles() + [
        {"id": "701", "name": "営業", "permissions": "0", "position": 1,
         "color": 0, "hoist": False, "mentionable": False, "managed": False},
    ]
    data = _bp_data()
    data["roles"].append({"key": "sales", "discord_id": "701", "name": "営業チーム"})
    plan = _plan(data, roles=roles)
    assert plan["changes"] == []
    assert [(r["kind"], r["reason"], r["field"]) for r in plan["blocked"]] == [
        ("update_role", "role_above_bot", "name")
    ]


def test_renaming_everyone_is_blocked():
    data = _bp_data()
    data["roles"][0]["name"] = "everyone-renamed"
    plan = _plan(data)
    assert plan["changes"] == []
    assert [(r["reason"], r["field"]) for r in plan["blocked"]] == [("everyone_name", "name")]


def test_permission_the_bot_lacks_is_blocked_unless_bot_is_admin():
    data = _bp_data()
    data["roles"].append({"key": "boss", "name": "boss", "permissions": ["ADMINISTRATOR"]})
    plan = _plan(data)
    assert plan["changes"] == []
    assert [(r["kind"], r["reason"]) for r in plan["blocked"]] == [("create_role", "permission_bot_lacks")]
    admin_roles = _production_roles()
    admin_roles[1]["permissions"] = str(int(_BOT_PERMS) | 8)
    plan = _plan(data, roles=admin_roles)
    assert [r["kind"] for r in plan["changes"]] == ["create_role"]
    assert plan["blocked"] == []


def test_manage_roles_in_overwrite_is_blocked():
    data = _bp_data()
    data["categories"][0]["overwrites"] = [{"target": "@everyone", "allow": ["MANAGE_ROLES"]}]
    plan = _plan(data)
    assert plan["changes"] == []
    assert [(r["kind"], r["reason"]) for r in plan["blocked"]] == [("update_overwrite", "overwrite_manage_roles")]


def test_bits_outside_the_table_are_not_compared():
    roles = _production_roles()
    roles[0]["permissions"] = str(int(_EVERYONE_PERMS) ^ (1 << 47))
    channels = _production_channels()
    channels[0]["permission_overwrites"] = [
        {"id": _G, "type": 0, "allow": str(1 << 47), "deny": "0"},
    ]
    plan = _plan(roles=roles, channels=channels)
    assert plan["changes"] == []
    assert plan["blocked"] == []
    assert [r["kind"] for r in plan["delete_candidates"]] == ["overwrite"]


def test_missing_on_discord_is_blocked_and_not_recreated():
    data = _bp_data()
    data["channels"][0]["discord_id"] = "999"
    plan = _plan(data)
    assert plan["changes"] == []
    assert [(r["kind"], r["reason"]) for r in plan["blocked"]] == [("update_channel", "missing_on_discord")]


def test_same_name_twice_is_ambiguous():
    channels = _production_channels() + [
        {"id": "1567709769337409740", "type": 0, "name": "news", "parent_id": _TEXT_CAT,
         "permission_overwrites": []},
        {"id": "1567709769337409741", "type": 0, "name": "news", "parent_id": _TEXT_CAT,
         "permission_overwrites": []},
    ]
    data = _bp_data()
    data["channels"].append({"key": "news", "name": "news", "type": "text", "category": "text_cat"})
    plan = _plan(data, channels=channels)
    assert [(r["kind"], r["reason"]) for r in plan["blocked"]] == [("update_channel", "ambiguous")]
    assert plan["changes"] == []
    assert plan["delete_candidates"] == []


def test_plan_digest_is_stable_and_changes_with_the_plan():
    first = _plan(_four_kinds())
    second = _plan(_four_kinds())
    assert first["plan_digest"] == second["plan_digest"]
    assert len(first["plan_digest"]) == 64
    data = _four_kinds()
    data["roles"][-1]["name"] = "別の名前"
    assert _plan(data)["plan_digest"] != first["plan_digest"]


def test_plan_has_no_guild_id():
    data = _four_kinds()
    data["categories"][0]["overwrites"] = [{"target": "@everyone", "deny": ["SEND_MESSAGES"]}]
    channels = _production_channels()
    channels[2]["permission_overwrites"] = [{"id": _G, "type": 0, "allow": "0", "deny": "1024"}]
    plan = _plan(data, channels=channels)
    dumped = json.dumps(plan, ensure_ascii=False)
    assert _G not in dumped
    assert any(r["target"] == "@everyone" for r in plan["delete_candidates"])


def test_null_and_empty_topic_are_the_same():
    channels = _production_channels()
    channels[2]["topic"] = ""
    assert _counts(_plan(channels=channels)) == (0, 0, 0)
    data = _bp_data()
    data["channels"][0]["topic"] = ""
    assert _counts(_plan(data)) == (0, 0, 0)


# ---------------------------------------------------------------- 便3b: M1 と actions

def test_channel_under_blocked_category_is_not_a_delete_candidate():
    # M1: 親のカテゴリが missing_on_discord でも、Discord にあるチャンネルは「消す候補」に出さない
    for channel_id in (_GENERAL, None):
        data = _bp_data()
        data["categories"][0]["discord_id"] = "999"
        data["channels"][0]["discord_id"] = channel_id
        plan = _plan(data)
        assert [(r["kind"], r["reason"]) for r in plan["blocked"]] == [
            ("update_category", "missing_on_discord"), ("update_channel", "missing_on_discord")
        ], plan
        assert plan["changes"] == []
        assert [c for c in plan["delete_candidates"] if c["kind"] == "channel"] == [], plan["delete_candidates"]


def test_actions_for_the_four_kinds():
    plan = _plan(_four_kinds())
    assert len(plan["actions"]) == len(plan["changes"]) == 4
    by_kind = {c["kind"]: a for c, a in zip(plan["changes"], plan["actions"])}
    role = by_kind["create_role"]
    assert (role["method"], role["path"], role["creates"]) == ("POST", "/guilds/{guild}/roles", "role:newrole")
    assert role["json"]["colors"] == {"primary_color": 0}
    assert "color" not in role["json"]
    assert role["json"]["name"] == "新しいロール"
    assert role["json"]["permissions"] == "0"
    rename = by_kind["update_channel"]
    assert (rename["method"], rename["path"], rename["json"], rename["creates"]) == (
        "PATCH", f"/channels/{_GENERAL}", {"name": "ippan"}, None
    )
    create = by_kind["create_channel"]
    assert (create["method"], create["path"], create["creates"]) == ("POST", "/guilds/{guild}/channels", "channel:news")
    assert create["json"] == {"name": "news", "type": 0, "permission_overwrites": [],
                              "topic": "お知らせ", "parent_id": _TEXT_CAT}
    overwrite = by_kind["update_overwrite"]
    assert (overwrite["method"], overwrite["path"]) == ("PUT", f"/channels/{_TEXT_CAT}/permissions/{{guild}}")
    assert overwrite["json"] == {"type": 0, "allow": "0", "deny": str(1 << 11)}


def test_moved_channel_under_a_new_category_uses_a_ref_for_the_parent():
    data = _bp_data()
    data["categories"].append({"key": "newcat", "name": "新カテゴリ", "overwrites": []})
    data["channels"][0]["category"] = "newcat"
    plan = _plan(data)
    pairs = list(zip(plan["changes"], plan["actions"]))
    assert [c["kind"] for c, _ in pairs] == ["create_category", "update_channel"]
    row, action = pairs[1]
    assert (row["field"], row["after"]) == ("parent", "新カテゴリ")
    assert (action["method"], action["path"]) == ("PATCH", f"/channels/{_GENERAL}")
    assert action["json"] == {"parent_id": "{ref:category:newcat}"}
    assert pairs[0][1]["creates"] == "category:newcat"


def test_new_role_as_overwrite_target_uses_a_ref():
    data = _bp_data()
    data["roles"].append({"key": "newrole", "name": "新しいロール"})
    data["categories"][0]["overwrites"] = [{"target": "role:newrole", "allow": ["VIEW_CHANNEL"]}]
    plan = _plan(data)
    assert [c["kind"] for c in plan["changes"]] == ["create_role", "update_overwrite"]
    action = plan["actions"][1]
    assert action["method"] == "PUT"
    assert action["path"] == f"/channels/{_TEXT_CAT}/permissions/{{ref:role:newrole}}"
    assert action["json"]["allow"] == str(1 << 10)


def test_bits_outside_the_table_are_kept_in_the_actions():
    unknown = 1 << 47
    roles = _production_roles()
    roles[0]["permissions"] = str(int(_EVERYONE_PERMS) | unknown)
    channels = _production_channels()
    channels[0]["permission_overwrites"] = [{"id": _G, "type": 0, "allow": str(unknown), "deny": str(unknown)}]
    data = _bp_data()
    data["roles"][0]["permissions"] = [p for p in data["roles"][0]["permissions"] if p != "CREATE_INSTANT_INVITE"]
    data["categories"][0]["overwrites"] = [{"target": "@everyone", "allow": ["VIEW_CHANNEL"]}]
    plan = _plan(data, roles=roles, channels=channels)
    assert [c["kind"] for c in plan["changes"]] == ["update_role", "update_overwrite"]
    role_action, ow_action = plan["actions"]
    assert role_action["path"] == "/guilds/{guild}/roles/{guild}"
    assert int(role_action["json"]["permissions"]) & unknown
    assert not int(role_action["json"]["permissions"]) & 1
    assert int(ow_action["json"]["allow"]) == unknown | (1 << 10)
    assert int(ow_action["json"]["deny"]) == unknown


def test_plan_with_actions_has_no_guild_id():
    data = _four_kinds()
    data["roles"][0]["permissions"] = [p for p in data["roles"][0]["permissions"] if p != "CREATE_INSTANT_INVITE"]
    channels = _production_channels()
    channels[2]["permission_overwrites"] = [{"id": _G, "type": 0, "allow": "0", "deny": "1024"}]
    plan = _plan(data, channels=channels)
    dumped = json.dumps(plan, ensure_ascii=False)
    assert _G not in dumped
    assert "{guild}" in dumped


def test_plan_digest_does_not_include_actions():
    import hashlib

    plan = _plan(_four_kinds())
    assert "actions" in plan
    expected = hashlib.sha256(
        json.dumps(
            {"changes": plan["changes"], "blocked": plan["blocked"], "delete_candidates": plan["delete_candidates"]},
            sort_keys=True, ensure_ascii=False, separators=(",", ":"),
        ).encode()
    ).hexdigest()
    assert plan["plan_digest"] == expected


# ---------------------------------------------------------------- API

_TENANT = 7
_OTHER_TENANT = 8
_GUILD_OWN = "222222222222222222"
_BOT_USER = "800000000000000001"
_URL = "/api/v1/admin/discord/own-server/plan"
_PERMS_FULL = {"channels.manage", "tenant.profile.view", "tenant.profile.edit"}
_PERMS_VIEW_ONLY = {"tenant.profile.view"}


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
        roles = _production_roles()
        roles[0]["id"] = _GUILD_OWN
        return roles
    if path.endswith("/channels"):
        return _production_channels()
    if path == "/users/@me":
        return {"id": _BOT_USER}
    if path.endswith(f"/members/{_BOT_USER}"):
        return {"roles": [_BOT_ROLE]}
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


@pytest.fixture
def bp_file(tmp_path):
    path = tmp_path / "tenant_7.json"
    path.write_text(json.dumps(_bp_data(), ensure_ascii=False), encoding="utf-8")
    return path


@pytest_asyncio.fixture
async def client(factory, perms, discord_mock, bp_file, monkeypatch):
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
            patch("app.routers.discord_own_server.discord_api_request", discord_mock)
        )
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
            text(
                "INSERT INTO tenant_discord_config (tenant_id, purpose, guild_id)"
                " VALUES (:t, :p, :g)"
            ),
            {"t": tenant_id, "p": purpose, "g": guild_id},
        )
        await s.commit()


async def _snapshot_count(factory) -> int:
    async with factory() as s:
        result = await s.execute(text("SELECT COUNT(*) FROM discord_server_snapshots"))
        return int(result.scalar_one())


@pytest.mark.asyncio
async def test_plan_returns_digest(client, factory):
    await _insert_config(factory, _TENANT, "own", _GUILD_OWN)
    resp = await client.get(_URL)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert len(data["plan_digest"]) == 64
    assert data["changes"] == []
    assert data["blocked"] == []
    assert data["delete_candidates"] == []


@pytest.mark.asyncio
async def test_plan_without_own_server_returns_422(client, factory, discord_mock):
    await _insert_config(factory, _OTHER_TENANT, "own", _GUILD_OWN)
    resp = await client.get(_URL)
    assert resp.status_code == 422
    discord_mock.assert_not_called()


@pytest.mark.asyncio
async def test_plan_without_blueprint_file_returns_404(client, factory, tmp_path):
    await _insert_config(factory, _TENANT, "own", _GUILD_OWN)
    missing = tmp_path / "none" / "tenant_7.json"
    with patch("app.routers.discord_own_server.blueprint_path", lambda tenant_id: missing):
        resp = await client.get(_URL)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_plan_with_broken_blueprint_returns_422(client, factory, bp_file, discord_mock):
    await _insert_config(factory, _TENANT, "own", _GUILD_OWN)
    data = _bp_data()
    data["channels"][0]["category"] = "nope"
    bp_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    resp = await client.get(_URL)
    assert resp.status_code == 422
    assert "nope" not in resp.text
    discord_mock.assert_not_called()


@pytest.mark.asyncio
async def test_plan_discord_error_returns_502(client, factory, discord_mock):
    await _insert_config(factory, _TENANT, "own", _GUILD_OWN)
    discord_mock.side_effect = DiscordAPIError("x", status_code=403)
    resp = await client.get(_URL)
    assert resp.status_code == 502


@pytest.mark.asyncio
async def test_plan_view_only_returns_403(client, factory, perms, discord_mock):
    await _insert_config(factory, _TENANT, "own", _GUILD_OWN)
    perms.clear()
    perms.update(_PERMS_VIEW_ONLY)
    resp = await client.get(_URL)
    assert resp.status_code == 403
    discord_mock.assert_not_called()


@pytest.mark.asyncio
async def test_plan_calls_only_get(client, factory, discord_mock):
    await _insert_config(factory, _TENANT, "own", _GUILD_OWN)
    resp = await client.get(_URL)
    assert resp.status_code == 200, resp.text
    assert discord_mock.await_count == 4
    assert {c.kwargs["method"] for c in discord_mock.await_args_list} == {"GET"}
    paths = [c.kwargs["path"] for c in discord_mock.await_args_list]
    assert f"/guilds/{_GUILD_OWN}/roles" in paths
    assert f"/guilds/{_GUILD_OWN}/channels" in paths
    assert "/users/@me" in paths
    assert f"/guilds/{_GUILD_OWN}/members/{_BOT_USER}" in paths


@pytest.mark.asyncio
async def test_plan_does_not_write_snapshots(client, factory):
    await _insert_config(factory, _TENANT, "own", _GUILD_OWN)
    before = await _snapshot_count(factory)
    resp = await client.get(_URL)
    assert resp.status_code == 200, resp.text
    assert await _snapshot_count(factory) == before
