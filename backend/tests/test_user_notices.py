"""アプリ内の鈴（user_notices）の試験。設計 docs/handoff/in-app-notice-bell/design.md §2・§4・§6・§7。

独立した in-memory SQLite に最小の表を作って流す（tenant_table_ref は SQLite ではスキーマ名なし）。
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import discord
import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.discord_gateway import outside_ticket_notice as ot
from app.routers import notices as notices_router
from app.services import user_notices as un

BODY = "secret-customer-body-xyz"
DISCORD_AUTHOR = "900000000000000001"

DDL = [
    "CREATE TABLE users (id INTEGER PRIMARY KEY, tenant_id INTEGER, is_active BOOLEAN, is_super_admin BOOLEAN,"
    " full_name TEXT, username TEXT, email TEXT)",
    "CREATE TABLE notice_fallback_recipients (user_id INTEGER PRIMARY KEY, updated_by INTEGER, updated_at TIMESTAMP)",
    "CREATE TABLE leads (id INTEGER PRIMARY KEY, tenant_id INTEGER, discord_user_id TEXT, assigned_to INTEGER, discord_guild_channel_id TEXT)",
    "CREATE TABLE lead_channels (id INTEGER PRIMARY KEY, lead_id INTEGER, platform TEXT, external_id TEXT)",
    "CREATE TABLE roles (id INTEGER PRIMARY KEY, system_key TEXT)",
    "CREATE TABLE user_roles (user_id INTEGER, role_id INTEGER)",
    "CREATE TABLE staff (id INTEGER PRIMARY KEY, tenant_id INTEGER, user_id INTEGER, discord_user_id TEXT)",
    "CREATE TABLE user_notices (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, kind TEXT NOT NULL,"
    " actor_name TEXT, channel_name TEXT, link_url TEXT, created_at TIMESTAMP NOT NULL, read_at TIMESTAMP)",
]


@pytest_asyncio.fixture
async def maker():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    async with engine.begin() as conn:
        for ddl in DDL:
            await conn.execute(text(ddl))
        await conn.execute(text("INSERT INTO roles (id, system_key) VALUES (1,'owner'),(2,'admin'),(3,NULL)"))
    yield async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    await engine.dispose()


async def _run(maker, sql, **params):
    async with maker() as s:
        await s.execute(text(sql), params)
        await s.commit()


async def add_user(maker, uid, tenant=1, active=True, role_id=None, discord=None):
    await _run(maker, "INSERT INTO users (id, tenant_id, is_active, is_super_admin, full_name, username, email)"
               " VALUES (:i,:t,:a,0,:fn,:un,:em)",
               i=uid, t=tenant, a=active, fn=(f"氏名{uid}" if uid % 2 == 0 else ""), un=f"user{uid}",
               em=f"user{uid}@example.com")
    if role_id:
        await _run(maker, "INSERT INTO user_roles (user_id, role_id) VALUES (:u,:r)", u=uid, r=role_id)
    if discord:
        await _run(maker, "INSERT INTO staff (tenant_id, user_id, discord_user_id) VALUES (:t,:u,:d)",
                   t=tenant, u=uid, d=discord)


async def add_lead(maker, lid, assigned, discord_uid=DISCORD_AUTHOR, via_channel=False):
    await _run(maker, "INSERT INTO leads (id, tenant_id, discord_user_id, assigned_to) VALUES (:i,1,:d,:a)",
               i=lid, d=None if via_channel else discord_uid, a=assigned)
    if via_channel:
        await _run(maker, "INSERT INTO lead_channels (lead_id, platform, external_id) VALUES (:l,'discord',:e)",
                   l=lid, e=discord_uid)


async def recipients(maker):
    async with maker() as s:
        return await un.resolve_notice_recipients(s, 1, DISCORD_AUTHOR)


# ---- §4-改訂1・2 宛先（K6） ----

async def set_fallback(maker, *user_ids):
    for uid in user_ids:
        await _run(maker, "INSERT INTO notice_fallback_recipients (user_id) VALUES (:u)", u=uid)


@pytest.mark.asyncio
async def test_assignee_only_no_owner_or_admin(maker):
    await add_user(maker, 10)
    await add_user(maker, 20, role_id=1)
    await add_user(maker, 21, role_id=2)
    await add_lead(maker, 1, 10)
    assert await recipients(maker) == [10]


@pytest.mark.asyncio
async def test_same_person_on_many_leads_once(maker):
    await add_user(maker, 10)
    await add_user(maker, 20, role_id=1)
    await add_lead(maker, 1, 10)
    await add_lead(maker, 2, 10, via_channel=True)
    assert await recipients(maker) == [10]


@pytest.mark.asyncio
async def test_multiple_assignees_all_of_them(maker):
    await add_user(maker, 10)
    await add_user(maker, 11)
    await add_user(maker, 20, role_id=1)
    await add_lead(maker, 1, 10)
    await add_lead(maker, 2, 11)
    assert await recipients(maker) == [10, 11]


@pytest.mark.asyncio
async def test_no_lead_no_setting_owners_only(maker):
    await add_user(maker, 20, role_id=1)
    await add_user(maker, 21, role_id=1)
    await add_user(maker, 22, role_id=2)  # admin は入らない
    assert await recipients(maker) == [20, 21]


@pytest.mark.asyncio
async def test_lead_without_assignee_goes_to_owner(maker):
    await add_user(maker, 20, role_id=1)
    await add_lead(maker, 1, None)
    assert await recipients(maker) == [20]


@pytest.mark.asyncio
async def test_assignee_inactive_other_tenant_or_missing_goes_to_owner(maker):
    await add_user(maker, 20, role_id=1)
    await add_user(maker, 11, active=False)
    await add_user(maker, 12, tenant=2)
    await add_lead(maker, 1, 11)
    await add_lead(maker, 2, 12)
    await add_lead(maker, 3, 999)
    assert await recipients(maker) == [20]


@pytest.mark.asyncio
async def test_setting_used_when_no_assignee(maker):
    await add_user(maker, 20, role_id=1)
    await add_user(maker, 30)
    await add_user(maker, 31)
    await set_fallback(maker, 30, 31)
    assert await recipients(maker) == [30, 31]


@pytest.mark.asyncio
async def test_setting_ignored_when_assignee_exists(maker):
    await add_user(maker, 10)
    await add_user(maker, 30)
    await set_fallback(maker, 30)
    await add_lead(maker, 1, 10)
    assert await recipients(maker) == [10]


@pytest.mark.asyncio
async def test_setting_all_inactive_or_other_tenant_goes_back_to_owner(maker):
    await add_user(maker, 20, role_id=1)
    await add_user(maker, 30, active=False)
    await add_user(maker, 31, tenant=2)
    await set_fallback(maker, 30, 31, 999)
    assert await recipients(maker) == [20]


@pytest.mark.asyncio
async def test_setting_partly_inactive_keeps_valid_only(maker):
    await add_user(maker, 20, role_id=1)
    await add_user(maker, 30, active=False)
    await add_user(maker, 31)
    await set_fallback(maker, 30, 31)
    assert await recipients(maker) == [31]


@pytest.mark.asyncio
async def test_owner_inactive_or_other_tenant_excluded_and_normal_role_not_owner(maker):
    await add_user(maker, 20, role_id=1, active=False)
    await add_user(maker, 21, role_id=1, tenant=2)
    await add_user(maker, 22, role_id=3)  # system_key NULL の通常ロール
    await add_user(maker, 23, role_id=2)  # admin
    assert await recipients(maker) == []


# ---- K7 Discord の id ----

@pytest.mark.asyncio
async def test_discord_ids_numeric_only_and_capped(maker):
    await add_user(maker, 10, discord="123")
    await add_user(maker, 11, discord="abc")
    await add_user(maker, 12)
    async with maker() as s:
        assert await un.discord_ids_for_users(s, 1, [10, 11, 12]) == ["123"]
    for i in range(100, 170):
        await add_user(maker, i, discord=str(5000 + i))
    async with maker() as s:
        got = await un.discord_ids_for_users(s, 1, list(range(100, 170)))
    assert len(got) == un.MAX_MENTIONS


# ---- 通知の流れ ----

class FakeRedis:
    def __init__(self):
        self.keys = set()

    async def set(self, key, val, nx=False, ex=None):
        if nx and key in self.keys:
            return None
        self.keys.add(key)
        return True


def make_msg(author_id=int(DISCORD_AUTHOR), channel_id=555):
    return SimpleNamespace(
        type=discord.MessageType.default,
        author=SimpleNamespace(
            id=author_id, bot=False, display_name="Taro", name="taro",
            roles=[], guild_permissions=SimpleNamespace(administrator=False),
        ),
        webhook_id=None,
        channel=SimpleNamespace(id=channel_id, name="general", parent_id=None),
        jump_url="https://discord.com/channels/1/2/3",
        content=BODY,
    )


@pytest.fixture
def env():
    redis = FakeRedis()
    send = AsyncMock()
    publish = AsyncMock()
    with patch.object(ot, "get_redis", return_value=redis), \
         patch("app.routers.notifications.send_discord_notification", new=send), \
         patch.object(un, "publish_user_change", new=publish):
        yield send, publish


async def notice_rows(maker):
    async with maker() as s:
        return (await s.execute(text("SELECT user_id, kind, actor_name, channel_name, link_url FROM user_notices ORDER BY id"))).all()


@pytest.mark.asyncio
async def test_notify_creates_bell_mentions_and_signals(maker, env):
    send, publish = env
    await add_user(maker, 10, discord="111")
    await add_user(maker, 20, role_id=1, discord="222")
    await add_lead(maker, 1, 10)
    async with maker() as s:
        assert await ot.notify_outside_ticket_post(s, tenant_id=1, message=make_msg()) is True
    assert send.await_count == 1
    assert send.await_args.kwargs["mention_user_ids"] == ["111"]
    assert BODY not in send.await_args.args[4]
    rows = await notice_rows(maker)
    assert [r[0] for r in rows] == [10]
    assert rows[0][1:] == ("discord_outside_ticket_post", "Taro", "general", "https://discord.com/channels/1/2/3")
    assert sorted(c.args[0] for c in publish.await_args_list) == [10]
    assert all(c.args[1] == "notices" for c in publish.await_args_list)


@pytest.mark.asyncio
async def test_k8_no_body_or_discord_id_stored(maker, env):
    await add_user(maker, 20, role_id=1, discord="222")
    async with maker() as s:
        await ot.notify_outside_ticket_post(s, tenant_id=1, message=make_msg())
    async with maker() as s:
        cols = [r[1] for r in (await s.execute(text("PRAGMA table_info(user_notices)"))).all()]
    assert not {"body", "content", "message", "discord_user_id", "author_id"} & set(cols)
    flat = " ".join(str(v) for row in await notice_rows(maker) for v in row)
    assert BODY not in flat and DISCORD_AUTHOR not in flat and "222" not in flat


@pytest.mark.asyncio
async def test_dedup_gate_shared_with_bell(maker, env):
    send, _ = env
    await add_user(maker, 20, role_id=1)
    async with maker() as s:
        await ot.notify_outside_ticket_post(s, tenant_id=1, message=make_msg())
        await ot.notify_outside_ticket_post(s, tenant_id=1, message=make_msg())
    assert send.await_count == 1
    assert len(await notice_rows(maker)) == 1


@pytest.mark.asyncio
async def test_discord_failure_still_creates_bell(maker, env):
    send, publish = env
    send.side_effect = RuntimeError("discord down")
    await add_user(maker, 20, role_id=1)
    async with maker() as s:
        await ot.notify_outside_ticket_post(s, tenant_id=1, message=make_msg())
    assert [r[0] for r in await notice_rows(maker)] == [20]
    assert publish.await_count == 1


@pytest.mark.asyncio
async def test_bell_failure_does_not_raise_and_discord_still_sent(maker, env):
    send, publish = env
    await add_user(maker, 20, role_id=1)
    with patch.object(un, "insert_notices", new=AsyncMock(side_effect=RuntimeError("db"))):
        async with maker() as s:
            assert await ot.notify_outside_ticket_post(s, tenant_id=1, message=make_msg()) is True
    assert send.await_count == 1
    assert publish.await_count == 0


@pytest.mark.asyncio
async def test_signal_failure_does_not_raise(maker, env):
    _, publish = env
    publish.side_effect = RuntimeError("redis")
    await add_user(maker, 20, role_id=1)
    async with maker() as s:
        assert await ot.notify_outside_ticket_post(s, tenant_id=1, message=make_msg()) is True
    assert len(await notice_rows(maker)) == 1


@pytest.mark.asyncio
async def test_no_recipients_no_bell_discord_still_sent_without_mention(maker, env):
    send, publish = env
    async with maker() as s:
        assert await ot.notify_outside_ticket_post(s, tenant_id=1, message=make_msg()) is True
    assert send.await_count == 1
    assert send.await_args.kwargs["mention_user_ids"] is None
    assert await notice_rows(maker) == []
    assert publish.await_count == 0


# ---- API（K2・K3・K5） ----

def make_app(maker, user):
    app = FastAPI()
    app.include_router(notices_router.router, prefix="/api/v1")

    async def _db():
        async with maker() as s:
            yield s

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_current_user] = lambda: user
    return app


def client_for(app):
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t")


async def seed_notices(maker, user_id, n, start=0):
    base = datetime(2026, 11, 3, tzinfo=timezone.utc)
    for i in range(n):
        await _run(
            maker,
            "INSERT INTO user_notices (user_id, kind, actor_name, channel_name, link_url, created_at) "
            "VALUES (:u,'discord_outside_ticket_post',:a,'general','https://discord.com/channels/1/2/3',:c)",
            u=user_id, a=f"n{start + i}", c=base + timedelta(minutes=start + i),
        )


@pytest.mark.asyncio
async def test_k2_list_max_50_newest_first(maker):
    await seed_notices(maker, 10, 51)
    app = make_app(maker, SimpleNamespace(id=10, tenant_id=1))
    async with client_for(app) as c:
        data = (await c.get("/api/v1/notices")).json()
    assert len(data["items"]) == 50
    assert data["unread_count"] == 51
    assert data["items"][0]["actor_name"] == "n50"
    assert data["items"][-1]["actor_name"] == "n1"


@pytest.mark.asyncio
async def test_k2_empty(maker):
    app = make_app(maker, SimpleNamespace(id=10, tenant_id=1))
    async with client_for(app) as c:
        assert (await c.get("/api/v1/notices")).json() == {"items": [], "unread_count": 0}


@pytest.mark.asyncio
async def test_k3_read_decrements_once(maker):
    await seed_notices(maker, 10, 3)
    app = make_app(maker, SimpleNamespace(id=10, tenant_id=1))
    async with client_for(app) as c:
        first_id = (await c.get("/api/v1/notices")).json()["items"][0]["id"]
        assert (await c.post(f"/api/v1/notices/{first_id}/read")).json() == {"unread_count": 2}
        assert (await c.post(f"/api/v1/notices/{first_id}/read")).json() == {"unread_count": 2}
        data = (await c.get("/api/v1/notices")).json()
    assert data["unread_count"] == 2
    assert data["items"][0]["read_at"] is not None


@pytest.mark.asyncio
async def test_k5_other_user_not_visible_and_read_404(maker):
    await seed_notices(maker, 10, 2)
    await seed_notices(maker, 11, 1)
    app = make_app(maker, SimpleNamespace(id=11, tenant_id=1))
    async with client_for(app) as c:
        data = (await c.get("/api/v1/notices")).json()
        assert len(data["items"]) == 1 and data["unread_count"] == 1
        async with maker() as s:
            other_id = (await s.execute(text("SELECT id FROM user_notices WHERE user_id = 10 LIMIT 1"))).scalar()
        assert (await c.post(f"/api/v1/notices/{other_id}/read")).status_code == 404
    async with maker() as s:
        unread = (await s.execute(text("SELECT COUNT(*) FROM user_notices WHERE user_id=10 AND read_at IS NULL"))).scalar()
    assert unread == 2


@pytest.mark.asyncio
async def test_k5_user_without_tenant_gets_empty_and_404(maker):
    await seed_notices(maker, 10, 1)
    app = make_app(maker, SimpleNamespace(id=10, tenant_id=None))
    async with client_for(app) as c:
        assert (await c.get("/api/v1/notices")).json() == {"items": [], "unread_count": 0}
        assert (await c.post("/api/v1/notices/1/read")).status_code == 404


# ---- 担当者がいないときの受け取り人の設定 API（K9） ----

def make_fb_app(maker, user):
    from app.auth.dependencies import get_current_tenant
    from app.routers import notice_fallback_recipients as fb_router

    app = FastAPI()
    app.include_router(fb_router.router, prefix="/api/v1")

    async def _db():
        async with maker() as s:
            yield s

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_tenant] = lambda: user.tenant_id
    return app


def allow_perms(perms):
    return patch("app.auth.dependencies.load_user_permissions", AsyncMock(return_value=set(perms)))


@pytest.mark.asyncio
async def test_fallback_api_forbidden_without_permission(maker):
    await add_user(maker, 10)
    app = make_fb_app(maker, SimpleNamespace(id=10, tenant_id=1))
    with allow_perms({"notifications.view"}):
        async with client_for(app) as c:
            assert (await c.get("/api/v1/notice-fallback-recipients")).status_code == 403
            assert (await c.put("/api/v1/notice-fallback-recipients", json={"user_ids": [10]})).status_code == 403
    async with maker() as s:
        assert (await s.execute(text("SELECT COUNT(*) FROM notice_fallback_recipients"))).scalar() == 0


@pytest.mark.asyncio
async def test_fallback_api_get_defaults_and_candidates_have_no_discord_or_email(maker):
    await add_user(maker, 10, discord="123456")   # 氏名10
    await add_user(maker, 11)                      # full_name 空 → username
    await add_user(maker, 12, active=False)
    await add_user(maker, 13, tenant=2)
    app = make_fb_app(maker, SimpleNamespace(id=10, tenant_id=1))
    with allow_perms({"notifications.manage"}):
        async with client_for(app) as c:
            r = await c.get("/api/v1/notice-fallback-recipients")
    assert r.status_code == 200
    data = r.json()
    assert data["selected"] == [] and data["defaulted_to_owner"] is True
    assert data["candidates"] == [
        {"user_id": 10, "name": "氏名10"},
        {"user_id": 11, "name": "user11"},
    ]
    raw = r.text
    assert "123456" not in raw and "@example.com" not in raw
    for cand in data["candidates"]:
        assert set(cand) == {"user_id", "name"}


@pytest.mark.asyncio
async def test_fallback_api_put_replaces_and_get_reflects(maker):
    await add_user(maker, 10)
    await add_user(maker, 11)
    await add_user(maker, 20, role_id=1)
    app = make_fb_app(maker, SimpleNamespace(id=10, tenant_id=1))
    with allow_perms({"notifications.manage"}):
        async with client_for(app) as c:
            r = await c.put("/api/v1/notice-fallback-recipients", json={"user_ids": [10, 11, 10]})
            assert r.status_code == 200
            assert r.json()["selected"] == [10, 11] and r.json()["defaulted_to_owner"] is False
            r = await c.put("/api/v1/notice-fallback-recipients", json={"user_ids": [11]})
            assert r.json()["selected"] == [11]
            r = await c.put("/api/v1/notice-fallback-recipients", json={"user_ids": []})
            assert r.json()["selected"] == [] and r.json()["defaulted_to_owner"] is True
    await set_fallback(maker, 11)
    assert await recipients(maker) == [11]  # 保存後の次の知らせはその人へ


@pytest.mark.asyncio
async def test_fallback_api_put_rejects_other_tenant_inactive_unknown(maker):
    await add_user(maker, 10)
    await add_user(maker, 11, active=False)
    await add_user(maker, 12, tenant=2)
    await set_fallback(maker, 10)
    app = make_fb_app(maker, SimpleNamespace(id=10, tenant_id=1))
    with allow_perms({"notifications.manage"}):
        async with client_for(app) as c:
            for bad in ([11], [12], [999], [10, 12]):
                r = await c.put("/api/v1/notice-fallback-recipients", json={"user_ids": bad})
                assert r.status_code == 422, bad
            assert (await c.get("/api/v1/notice-fallback-recipients")).json()["selected"] == [10]
