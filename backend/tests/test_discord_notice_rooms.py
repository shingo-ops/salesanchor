"""知らせの部屋 3 つと送り先のつなぎを自動で作る（discord-server-management 第2段 2c・設計 D2-11）の試験。

build_plan は純粋な関数なので Discord の返事の作り物で直接呼ぶ。
apply_plan と画面の口の試験は Discord を AsyncMock に差し替える（本物の Discord には繋がない）。
notification_channels は conftest の SQLite 版を使う。
"""
from __future__ import annotations

import copy
import json
import os
import shutil
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
from app.schemas.notification import NotificationEventType
from app.services.discord_blueprint import BLUEPRINT_DIR, NOTICE_ROOMS, Blueprint, build_plan
from app.services.discord_blueprint_apply import apply_plan
from app.services.discord_rest import DiscordAPIError
from tests.test_discord_own_server_plan import (
    _BOT_ROLE,
    _TEXT_CAT,
    _production_channels,
    _production_roles,
)
from tests.test_discord_own_server_plan import _G as _GUILD

_TENANT = 7
_BOT_USER = "800000000000000001"
_PLAN_URL = "/api/v1/admin/discord/own-server/plan"
_APPLY_URL = "/api/v1/admin/discord/own-server/apply"
_PERMS_FULL = {"channels.manage", "tenant.profile.view", "tenant.profile.edit"}
_ROOM_KEYS = ["assign_notice", "reply_notice", "outside_notice"]
_ROOM_NAMES = {"assign_notice": "アサイン連絡", "reply_notice": "返信連絡", "outside_notice": "部屋の外の書き込み"}
_WEBHOOK_PREFIX = "https://discord.com/api/webhooks/"


def _tenant_1_blueprint() -> Blueprint:
    data = json.loads((BLUEPRINT_DIR / "tenant_1.json").read_text(encoding="utf-8"))
    return Blueprint.model_validate(data)


def _plan(notice_links, channels: list[dict] | None = None) -> dict:
    bp = _tenant_1_blueprint()
    chans = _production_channels() if channels is None else channels
    return build_plan(bp, _production_roles(), chans, _GUILD, [_BOT_ROLE], notice_links=notice_links)


def _link_rows(plan: dict) -> list[dict]:
    return [c for c in plan["changes"] if c["kind"] == "link_notice"]


def _link_actions(plan: dict) -> list[dict]:
    return [a for c, a in zip(plan["changes"], plan["actions"]) if c["kind"] == "link_notice"]


def _existing_room(room_id: str, key: str) -> dict:
    return {"id": room_id, "type": 0, "name": _ROOM_NAMES[key], "parent_id": _TEXT_CAT, "topic": None,
            "permission_overwrites": []}


# ---------------------------------------------------------------- 確認（build_plan だけ・DB 無し）


def test_notice_links_none_keeps_plan_identical():
    bp = _tenant_1_blueprint()
    omitted = build_plan(bp, _production_roles(), _production_channels(), _GUILD, [_BOT_ROLE])
    explicit_none = build_plan(
        bp, _production_roles(), _production_channels(), _GUILD, [_BOT_ROLE], notice_links=None,
    )
    assert omitted == explicit_none
    assert omitted["plan_digest"] == explicit_none["plan_digest"]
    assert _link_rows(omitted) == []


def test_notice_rooms_missing_on_discord_get_link_rows_last():
    plan = _plan([])
    assert [c["kind"] for c in plan["changes"][-3:]] == ["link_notice"] * 3
    assert [c["key"] for c in plan["changes"][-3:]] == _ROOM_KEYS
    for key, row, action in zip(_ROOM_KEYS, _link_rows(plan), _link_actions(plan)):
        assert action == {
            "method": "POST",
            "path": "/channels/{ref:channel:" + key + "}/webhooks",
            "json": {"name": "Sales Anchor"},
            "creates": None,
            "webhook_for": key,
        }
        assert row["after"] == f"event={NOTICE_ROOMS[key]}"
        assert "reason" not in row


def test_notice_room_existing_on_discord_uses_its_id():
    plan = _plan([], _production_channels() + [_existing_room("5001", "assign_notice")])
    paths = {c["key"]: a["path"] for c, a in zip(_link_rows(plan), _link_actions(plan))}
    assert paths["assign_notice"] == "/channels/5001/webhooks"
    assert paths["reply_notice"] == "/channels/{ref:channel:reply_notice}/webhooks"


def test_inactive_blueprint_link_row_is_still_skipped_when_linked():
    links = [{"blueprint_key": "reply_notice", "event_types": json.dumps([NOTICE_ROOMS["reply_notice"]]),
              "is_active": False}]
    plan = _plan(links)
    assert [c["key"] for c in _link_rows(plan)] == ["assign_notice", "outside_notice"]


def test_manual_row_adds_note_only_for_same_event_when_active():
    outside_event = NotificationEventType.discord_outside_ticket_post.value
    manual = {"blueprint_key": None, "event_types": f'["{outside_event}"]', "is_active": True}
    plan = _plan([manual])
    notes = {c["key"]: c.get("reason") for c in _link_rows(plan)}
    assert notes == {"assign_notice": None, "reply_notice": None, "outside_notice": "notice_other_route"}

    inactive = dict(manual, is_active=False)
    notes = {c["key"]: c.get("reason") for c in _link_rows(_plan([inactive]))}
    assert set(notes.values()) == {None}

    broken = dict(manual, event_types="not json")
    notes = {c["key"]: c.get("reason") for c in _link_rows(_plan([broken]))}
    assert set(notes.values()) == {None}


def test_ambiguous_room_blocks_its_link_row():
    channels = _production_channels() + [
        _existing_room("5001", "assign_notice"),
        _existing_room("5002", "assign_notice"),
    ]
    plan = _plan([], channels)
    assert "assign_notice" not in [c["key"] for c in _link_rows(plan)]
    blocked = [b for b in plan["blocked"] if b["kind"] == "link_notice"]
    assert [(b["key"], b["reason"]) for b in blocked] == [("assign_notice", "notice_room_unavailable")]


def test_notice_rooms_table_matches_enum_and_blueprint():
    values = {e.value for e in NotificationEventType}
    assert set(NOTICE_ROOMS.values()) <= values
    bp_keys = {c.key for c in _tenant_1_blueprint().channels}
    assert set(NOTICE_ROOMS) <= bp_keys


# ---------------------------------------------------------------- 反映（apply_plan・Discord は mock）


def _mini_blueprint() -> Blueprint:
    return Blueprint.model_validate({
        "version": 1,
        "roles": [{"key": "everyone", "discord_id": "@everyone", "name": "@everyone", "permissions": []}],
        "categories": [],
        "channels": [{"key": "assign_notice", "discord_id": None, "name": "アサイン連絡", "type": "text",
                      "category": None, "topic": None, "overwrites": []}],
    })


def _mini_plan() -> dict:
    roles = [
        {"id": _GUILD, "name": "@everyone", "permissions": "0", "position": 0,
         "color": 0, "hoist": False, "mentionable": False, "managed": False},
        {"id": _BOT_ROLE, "name": "SalesAnchor", "permissions": "0", "position": 10,
         "color": 0, "hoist": False, "mentionable": False, "managed": True},
    ]
    return build_plan(_mini_blueprint(), roles, [], _GUILD, [_BOT_ROLE], notice_links=[])


def _hook_reply(**kwargs):
    path = kwargs["path"]
    if path.endswith("/webhooks"):
        return {"id": "901", "token": "tok-secret"}
    return {"id": "900"}


@pytest.mark.asyncio
async def test_apply_creates_webhook_and_keeps_token_out_of_results():
    plan = _mini_plan()
    assert [c["kind"] for c in plan["changes"]] == ["create_channel", "link_notice"]
    fake = AsyncMock(side_effect=_hook_reply)
    urls: dict[str, str] = {}
    with patch("app.services.discord_blueprint_apply.discord_api_request", fake):
        results = await apply_plan(plan, _GUILD, "bot-tok", webhook_urls=urls)
    assert urls["assign_notice"] == "https://discord.com/api/webhooks/901/tok-secret"
    assert [c.kwargs["path"] for c in fake.call_args_list][-1] == "/channels/900/webhooks"
    link = [r for r in results if r["kind"] == "link_notice"][0]
    assert link["status"] == "success"
    assert link["discord_id"] is None
    assert "tok-secret" not in json.dumps(results)


@pytest.mark.asyncio
async def test_apply_webhook_reply_without_token_fails():
    plan = _mini_plan()

    async def _reply(**kwargs):
        return {"id": "901"} if kwargs["path"].endswith("/webhooks") else {"id": "900"}

    urls: dict[str, str] = {}
    with patch("app.services.discord_blueprint_apply.discord_api_request", AsyncMock(side_effect=_reply)):
        results = await apply_plan(plan, _GUILD, "bot-tok", webhook_urls=urls)
    link = [r for r in results if r["kind"] == "link_notice"][0]
    assert (link["status"], link["reason"]) == ("failed", "webhook_token_missing")
    assert urls == {}


@pytest.mark.asyncio
async def test_apply_without_webhook_urls_never_creates_webhook():
    plan = _mini_plan()
    fake = AsyncMock(side_effect=_hook_reply)
    with patch("app.services.discord_blueprint_apply.discord_api_request", fake):
        results = await apply_plan(plan, _GUILD, "bot-tok")
    link = [r for r in results if r["kind"] == "link_notice"][0]
    assert (link["status"], link["reason"]) == ("failed", "method_not_allowed")
    assert [c for c in fake.call_args_list if c.kwargs["path"].endswith("/webhooks")] == []


@pytest.mark.asyncio
async def test_apply_webhook_depends_on_room_creation():
    plan = _mini_plan()

    async def _reply(**kwargs):
        raise DiscordAPIError("boom", status_code=500)

    urls: dict[str, str] = {}
    with patch("app.services.discord_blueprint_apply.discord_api_request", AsyncMock(side_effect=_reply)):
        results = await apply_plan(plan, _GUILD, "bot-tok", webhook_urls=urls)
    link = [r for r in results if r["kind"] == "link_notice"][0]
    assert (link["status"], link["reason"]) == ("failed", "depends_failed")
    assert urls == {}


# ---------------------------------------------------------------- 画面の道（router・SQLite）


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
    await conn.execute(text("DELETE FROM notification_channels"))
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
def world():
    return {"roles": _production_roles(), "channels": _production_channels()}


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
        reply = {"id": str(counter["n"])}
        if kwargs["path"].endswith("/webhooks"):
            reply["token"] = f"tok-secret-{counter['n']}"
        return reply

    return AsyncMock(side_effect=_fake_write)


@pytest.fixture
def audit_mock():
    return AsyncMock(return_value=None)


@pytest.fixture
def redis_holder():
    return {"r": SimpleNamespace(set=AsyncMock(return_value=True), delete=AsyncMock(return_value=1))}


@pytest.fixture
def bp_file(tmp_path):
    path = tmp_path / "tenant_7.json"
    shutil.copy(BLUEPRINT_DIR / "tenant_1.json", path)
    return path


@pytest_asyncio.fixture
async def client(factory, discord_mock, write_mock, audit_mock, redis_holder, bp_file, monkeypatch):
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
        return set(_PERMS_FULL)

    with ExitStack() as stack:
        stack.enter_context(patch("app.auth.dependencies.load_user_permissions", _perms))
        stack.enter_context(patch("app.routers.discord_own_server.record_audit_log", audit_mock))
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


async def _insert_config(factory) -> None:
    async with factory() as s:
        await s.execute(
            text("INSERT INTO tenant_discord_config (tenant_id, purpose, guild_id) VALUES (:t, 'own', :g)"),
            {"t": _TENANT, "g": _GUILD},
        )
        await s.commit()


async def _rows(factory, sql: str) -> list[tuple]:
    async with factory() as s:
        result = await s.execute(text(sql))
        return [tuple(r) for r in result.all()]


async def _check_and_apply(client) -> dict:
    resp = await client.get(_PLAN_URL)
    assert resp.status_code == 200, resp.text
    resp = await client.post(_APPLY_URL, json={"plan_digest": resp.json()["plan_digest"]})
    assert resp.status_code == 200, resp.text
    return resp.json()


@pytest.mark.asyncio
async def test_check_then_apply_writes_three_notice_rows(client, factory, audit_mock):
    await _insert_config(factory)
    await _check_and_apply(client)

    rows = await _rows(
        factory,
        "SELECT blueprint_key, event_types, webhook_url, channel_name FROM notification_channels ORDER BY id",
    )
    assert [r[0] for r in rows] == _ROOM_KEYS
    for key, row in zip(_ROOM_KEYS, rows):
        assert row[1] == json.dumps([NOTICE_ROOMS[key]])
        assert row[2].startswith(_WEBHOOK_PREFIX)
        assert row[3] == _ROOM_NAMES[key]

    runs = await _rows(factory, "SELECT result FROM discord_server_apply_runs")
    assert len(runs) == 1
    assert "tok-secret" not in str(runs[0][0])
    assert audit_mock.call_args.kwargs["new_data"]["notice_links_written"] == 3
    assert "tok-secret" not in json.dumps(audit_mock.call_args.kwargs["new_data"])


@pytest.mark.asyncio
async def test_second_check_has_no_link_rows(client, factory):
    await _insert_config(factory)
    await _check_and_apply(client)

    resp = await client.get(_PLAN_URL)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert [r for r in data["changes"] + data["blocked"] if r["kind"] == "link_notice"] == []


@pytest.mark.asyncio
async def test_manual_row_is_read_but_never_changed(client, factory):
    await _insert_config(factory)
    async with factory() as s:
        await s.execute(
            text(
                "INSERT INTO notification_channels (tenant_id, channel_name, webhook_url, event_types, is_active)"
                " VALUES (:t, 'manual', 'https://example.invalid/hook', :ev, TRUE)"
            ),
            {"t": _TENANT, "ev": '["discord_outside_ticket_post"]'},
        )
        await s.commit()
    select_manual = (
        "SELECT id, tenant_id, channel_type, channel_name, webhook_url, event_types, is_active, blueprint_key,"
        " created_at, updated_at FROM notification_channels WHERE blueprint_key IS NULL"
    )
    before = await _rows(factory, select_manual)
    assert len(before) == 1

    resp = await client.get(_PLAN_URL)
    assert resp.status_code == 200, resp.text
    notes = {r["key"]: r.get("reason") for r in resp.json()["changes"] if r["kind"] == "link_notice"}
    assert notes["outside_notice"] == "notice_other_route"
    assert notes["assign_notice"] is None

    await _check_and_apply(client)
    assert await _rows(factory, select_manual) == before
    assert len(await _rows(factory, "SELECT id FROM notification_channels")) == 4
