"""部屋の外の書き込みを担当者へ知らせる部品の試験（design T1〜T9）。"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

from app.discord_gateway import outside_ticket_notice as ot
from app.discord_gateway import ticket_channel_writer as tcw

BODY = "secret-customer-body-xyz"


class FakeRedis:
    def __init__(self):
        self.keys = set()

    async def set(self, key, val, nx=False, ex=None):
        if nx and key in self.keys:
            return None
        self.keys.add(key)
        return True


class FakeDb:
    """staff / config / leads の問い合わせに固定で答える。"""

    def __init__(self, staff=False, staff_role_id=None, parent_room=False):
        self.staff, self.staff_role_id, self.parent_room = staff, staff_role_id, parent_room

    async def execute(self, stmt, params=None):
        sql = str(stmt)
        res = MagicMock()
        if "FROM staff" in sql:
            res.first.return_value = (1,) if self.staff else None
        elif "tenant_discord_ticket_config" in sql:
            res.first.return_value = (self.staff_role_id,) if self.staff_role_id else None
        elif "FROM leads" in sql:
            res.first.return_value = (1,) if self.parent_room else None
        return res


def make_msg(author_id=100, mtype=discord.MessageType.default, bot=False, webhook_id=None,
             roles=(), admin=False, channel_id=555, parent_id=None):
    return SimpleNamespace(
        type=mtype,
        author=SimpleNamespace(
            id=author_id, bot=bot, display_name="Taro", name="taro",
            roles=[SimpleNamespace(id=r) for r in roles],
            guild_permissions=SimpleNamespace(administrator=admin),
        ),
        webhook_id=webhook_id,
        channel=SimpleNamespace(id=channel_id, name="general", parent_id=parent_id),
        jump_url="https://discord.com/channels/1/2/3",
        content=BODY,
    )


@pytest.fixture
def env():
    redis = FakeRedis()
    send = AsyncMock()
    with patch.object(ot, "get_redis", return_value=redis), \
         patch("app.routers.notifications.send_discord_notification", new=send):
        yield redis, send


@pytest.mark.asyncio
async def test_t1_non_staff_sends_once_without_body(env):
    _, send = env
    assert await ot.notify_outside_ticket_post(FakeDb(), tenant_id=1, message=make_msg()) is True
    assert send.await_count == 1
    args = send.await_args.args
    assert args[2] == "discord_outside_ticket_post"
    assert args[3] == "部屋の外の書き込み（Discord）"
    assert len(args[4].split("\n")) == 3
    assert BODY not in args[4]
    assert send.await_args.kwargs.get("mention_user_ids") is None  # 宛先が決まらなければ名前は呼ばない


@pytest.mark.asyncio
async def test_t2_staff_table_no_send(env):
    _, send = env
    await ot.notify_outside_ticket_post(FakeDb(staff=True), tenant_id=1, message=make_msg())
    assert send.await_count == 0


@pytest.mark.asyncio
async def test_t3_staff_role_no_send(env):
    _, send = env
    await ot.notify_outside_ticket_post(
        FakeDb(staff_role_id="77"), tenant_id=1, message=make_msg(roles=(5, 77))
    )
    assert send.await_count == 0


@pytest.mark.asyncio
async def test_t4_admin_no_send(env):
    _, send = env
    await ot.notify_outside_ticket_post(FakeDb(), tenant_id=1, message=make_msg(admin=True))
    assert send.await_count == 0


@pytest.mark.asyncio
async def test_t5_dedup_per_author_and_channel(env):
    _, send = env
    db = FakeDb()
    await ot.notify_outside_ticket_post(db, tenant_id=1, message=make_msg())
    await ot.notify_outside_ticket_post(db, tenant_id=1, message=make_msg())
    assert send.await_count == 1
    await ot.notify_outside_ticket_post(db, tenant_id=1, message=make_msg(author_id=101))
    await ot.notify_outside_ticket_post(db, tenant_id=1, message=make_msg(channel_id=556))
    assert send.await_count == 3


@pytest.mark.asyncio
async def test_t6_non_default_type_bot_webhook_no_send(env):
    _, send = env
    db = FakeDb()
    await ot.notify_outside_ticket_post(
        db, tenant_id=1, message=make_msg(mtype=discord.MessageType.new_member))
    await ot.notify_outside_ticket_post(db, tenant_id=1, message=make_msg(bot=True))
    await ot.notify_outside_ticket_post(db, tenant_id=1, message=make_msg(webhook_id=9))
    assert send.await_count == 0


@pytest.mark.asyncio
async def test_t6b_reply_is_sent(env):
    _, send = env
    await ot.notify_outside_ticket_post(
        FakeDb(), tenant_id=1, message=make_msg(mtype=discord.MessageType.reply))
    assert send.await_count == 1


@pytest.mark.asyncio
async def test_t7_no_redis_no_send():
    send = AsyncMock()
    with patch.object(ot, "get_redis", return_value=None), \
         patch("app.routers.notifications.send_discord_notification", new=send):
        assert await ot.notify_outside_ticket_post(
            FakeDb(), tenant_id=1, message=make_msg()) is False
    assert send.await_count == 0


@pytest.mark.asyncio
async def test_t8_thread_in_ticket_room_no_send(env):
    _, send = env
    await ot.notify_outside_ticket_post(
        FakeDb(parent_room=True), tenant_id=1, message=make_msg(parent_id=999))
    assert send.await_count == 0


class _DbCtx:
    def __init__(self, db):
        self.db = db

    async def __aenter__(self):
        return self.db

    async def __aexit__(self, *a):
        return False


@pytest.mark.asyncio
@pytest.mark.parametrize("has_lead", [False, True])
async def test_t9_writer_calls_notify_only_outside_room(has_lead):
    msg = make_msg()
    msg.guild = SimpleNamespace(id=1)
    msg.id = 42
    msg.created_at = None
    lead = tcw.TicketChannelLead(lead_id=1, discord_user_id="999", customer_name="x")
    notify = AsyncMock()
    db = MagicMock()
    with patch.object(tcw, "set_tenant_context", new=AsyncMock()), \
         patch.object(tcw, "_lookup_ticket_channel_lead",
                      new=AsyncMock(return_value=lead if has_lead else None)), \
         patch.object(tcw.outside_ticket_notice, "notify_outside_ticket_post", new=notify):
        await tcw.process_ticket_channel_message(
            lambda: _DbCtx(db), tenant_id=1, message=msg)
    assert notify.await_count == (0 if has_lead else 1)
