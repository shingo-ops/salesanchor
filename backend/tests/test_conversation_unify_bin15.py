"""会話の一本化 便1.5: スマホのアプリから直接送った返信も受信箱に出す 試験（SQLite + モック）。

検証項目（カード 8-3）:
  1. Messenger の写し（app_id=26390203743090・知っている PSID）が outbound で1行入る（K6）
  2. 同じ写しが2回届いても1行のまま（K9）
  3. 写しの app_id が META_APP_ID と同じなら入れない（数字で届くものも含む）（K9）
  4. Instagram の A 形式の写し（app_id なし・知らない IGSID）で outbound とリードができる（K7）
  5. is_self の写しは入れない（K7）
  6. B 形式の is_echo は入れない
  7. 写しの後で受信の訳・Discord への知らせが呼ばれない
  8. 写しが先に入ってからアプリが同じ mid で送信しても 1 行・sent_by_staff_id が入る（K9）
  9. アプリの送信が先で同じ mid の写しが後でも 1 行・sent_by_staff_id が残る（K9）
 10. Discord: 担当の直接の投稿が outbound で入る・返信の知らせ・訳は呼ばれない（K8）
 11. Discord: 同じ message id が2回届いても 2回とも処理済み・INSERT に ON CONFLICT（K8・K9）
 12. Discord: お客さんは inbound・ボット / webhook / ピン留めの知らせは入れない（K8）
 13. Discord: discord_user_id が空のリードの部屋は入れない
 14. 購読の既定に message_echoes が入っている（K6）

メモ: 8・9 は Messenger の文で確かめる（Instagram の文も同じ SQL を通る）。
"""
from __future__ import annotations

import os
from contextlib import ExitStack
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

import discord
import pytest
import pytest_asyncio
from cryptography.fernet import Fernet
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.discord_gateway import ticket_channel_writer
from app.services import encryption, meta_graph
from tests import test_conv_backbone_ben1b as ben
from tests import test_message_send as ms
from tests.test_ticket_channel_translation import (
    _DBContext,
    _FakeAuthor,
    _FakeChannel,
    _FakeGuild,
    _FakeMessage,
    _mock_result,
)

_PAGE_ID = "page-1"
_IG_ACCOUNT_ID = "IG-ACC-1"
_CUSTOMER = "PSID-1"
_INBOX_APP_ID = "26390203743090"


@pytest_asyncio.fixture
async def env(monkeypatch):
    """webhook の処理と送信の API が、同じ SQLite を見る準備。"""
    encryption.reset_cache()
    monkeypatch.setenv("METADATA_FERNET_KEY", Fernet.generate_key().decode("ascii"))
    monkeypatch.delenv("META_APP_ID", raising=False)

    eng = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    @event.listens_for(eng.sync_engine, "connect")
    def _setup(dbapi_conn, _):
        dbapi_conn.create_function(
            "NOW", 0, lambda: datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S+00:00"),
        )
        dbapi_conn.execute("PRAGMA foreign_keys = ON")

    async with eng.begin() as conn:
        for ddl in (
            ms._LEAD_DDL,
            ben.LEAD_CHANNELS_DDL,
            ms._META_MESSAGES_DDL,
            ms._META_MESSAGES_MSGID_INDEX_DDL,
            ms._TENANT_META_CONFIG_DDL,
            ms._STAFF_DDL,
        ):
            await conn.execute(text(ddl))

    Session = sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        wh = ben._patch_webhook_runtime(monkeypatch, session)
        enqueue = MagicMock()
        notify = AsyncMock()
        monkeypatch.setattr(wh, "enqueue_inbound_translation", enqueue)
        monkeypatch.setattr(wh, "send_discord_notification", notify)
        monkeypatch.setattr("app.services.sse_pubsub.publish_inbox_update", AsyncMock())

        await ms._insert_tenant_meta_config(
            session, page_id=_PAGE_ID, ig_business_account_id=_IG_ACCOUNT_ID,
        )

        app = ms._build_app(session, tenant_id=999)
        transport = ASGITransport(app=app)
        with ExitStack() as stack:
            stack.enter_context(patch(
                "app.auth.dependencies.load_user_permissions",
                new=AsyncMock(return_value=ms._ALL_PERMS),
            ))
            stack.enter_context(patch(
                "app.routers.leads.invalidate_dashboard_cache", new=AsyncMock(return_value=None),
            ))
            stack.enter_context(patch(
                "app.routers.leads.record_audit_log", new=AsyncMock(return_value=None),
            ))
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                yield SimpleNamespace(
                    session=session, client=client, wh=wh, enqueue=enqueue, notify=notify,
                )
        app.dependency_overrides.clear()
    await eng.dispose()
    encryption.reset_cache()


async def _seed_known_customer(env, *, platform: str = "messenger", external_id: str = _CUSTOMER) -> None:
    """lead 1 と、その相手の窓口（lead_channels）を作る。"""
    await ms._insert_lead(env.session, lead_id=1, channel_type=platform)
    await env.session.execute(
        text("INSERT INTO lead_channels (lead_id, platform, external_id) VALUES (1, :p, :e)"),
        {"p": platform, "e": external_id},
    )
    await env.session.commit()


def _echo_body(
    *,
    mid: str = "mid-echo-1",
    recipient: str = _CUSTOMER,
    app_id=_INBOX_APP_ID,
    is_self: bool = False,
    object_type: str = "page",
    entry_id: str = _PAGE_ID,
    text_value: str = "スマホから返信",
) -> dict:
    message: dict = {"mid": mid, "text": text_value, "is_echo": True}
    if app_id is not None:
        message["app_id"] = app_id
    if is_self:
        message["is_self"] = True
    return {
        "object": object_type,
        "entry": [{
            "id": entry_id,
            "messaging": [{
                "sender": {"id": entry_id},
                "recipient": {"id": recipient},
                "timestamp": 1714400000,
                "message": message,
            }],
        }],
    }


async def _meta_rows(session):
    res = await session.execute(text(
        "SELECT direction, platform, sender_id, recipient_id, sent_by_staff_id, message_id, raw_payload "
        "FROM meta_messages ORDER BY id"
    ))
    return res.mappings().all()


async def _scalar(session, sql: str):
    return (await session.execute(text(sql))).scalar()


# ---------------------------------------------------------------------------
# 1〜3. Messenger の写し
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_messenger_echo_is_stored_as_outbound(env):
    await _seed_known_customer(env)

    await env.wh.process_messenger_event(_echo_body())

    rows = await _meta_rows(env.session)
    assert len(rows) == 1
    assert rows[0]["direction"] == "outbound"
    assert rows[0]["platform"] == "messenger"
    assert rows[0]["sender_id"] == _PAGE_ID
    assert rows[0]["recipient_id"] == _CUSTOMER
    assert rows[0]["sent_by_staff_id"] is None
    assert await _scalar(env.session, "SELECT COUNT(*) FROM leads") == 1


@pytest.mark.asyncio
async def test_same_echo_twice_stays_one_row(env):
    await _seed_known_customer(env)

    await env.wh.process_messenger_event(_echo_body())
    await env.wh.process_messenger_event(_echo_body())

    assert len(await _meta_rows(env.session)) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("app_id", ["123456789012345", 123456789012345])
async def test_echo_from_own_app_is_not_stored(env, monkeypatch, app_id):
    monkeypatch.setenv("META_APP_ID", "123456789012345")
    await _seed_known_customer(env)

    await env.wh.process_messenger_event(_echo_body(app_id=app_id))

    assert await _meta_rows(env.session) == []


# ---------------------------------------------------------------------------
# 4〜6. Instagram の写し・自分宛て・B 形式
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_instagram_echo_creates_lead_and_outbound(env):
    body = _echo_body(
        mid="mid-ig-1", recipient="IGSID-NEW", app_id=None,
        object_type="instagram", entry_id=_IG_ACCOUNT_ID,
    )

    await env.wh.process_messenger_event(body)

    rows = await _meta_rows(env.session)
    assert len(rows) == 1
    assert rows[0]["direction"] == "outbound"
    assert rows[0]["platform"] == "instagram"
    assert rows[0]["recipient_id"] == "IGSID-NEW"

    lead = (await env.session.execute(
        text("SELECT channel_type, customer_name FROM leads")
    )).fetchall()
    assert len(lead) == 1
    assert lead[0][0] == "instagram"
    assert lead[0][1] == "Instagram User"
    channel = (await env.session.execute(
        text("SELECT platform, external_id FROM lead_channels")
    )).fetchall()
    assert [tuple(c) for c in channel] == [("instagram", "IGSID-NEW")]


@pytest.mark.asyncio
async def test_is_self_echo_is_not_stored(env):
    body = _echo_body(
        mid="mid-self", recipient="IGSID-SELF", app_id=None, is_self=True,
        object_type="instagram", entry_id=_IG_ACCOUNT_ID,
    )

    await env.wh.process_messenger_event(body)

    assert await _meta_rows(env.session) == []
    assert await _scalar(env.session, "SELECT COUNT(*) FROM leads") == 0


@pytest.mark.asyncio
async def test_format_b_echo_is_not_stored(env):
    body = {
        "object": "instagram",
        "entry": [{
            "id": _IG_ACCOUNT_ID,
            "changes": [{
                "field": "messages",
                "value": {"messages": [{
                    "id": "mid-b-1", "is_echo": True, "text": "B 形式の写し",
                    "from": {"id": _IG_ACCOUNT_ID}, "timestamp": 1714400000,
                }]},
            }],
        }],
    }

    await env.wh.process_messenger_event(body)

    assert await _meta_rows(env.session) == []
    assert await _scalar(env.session, "SELECT COUNT(*) FROM leads") == 0


# ---------------------------------------------------------------------------
# 7. 写しでは受信のための処理を呼ばない
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_echo_does_not_call_translation_or_discord_notice(env):
    await _seed_known_customer(env)

    await env.wh.process_messenger_event(_echo_body())

    assert len(await _meta_rows(env.session)) == 1
    env.enqueue.assert_not_called()
    env.notify.assert_not_awaited()


# ---------------------------------------------------------------------------
# 8・9. 写しとアプリの送信が同じ mid で重なる
# ---------------------------------------------------------------------------
async def _send_from_app(env, *, mid: str):
    async def fake_send(**kwargs):
        return {"recipient_id": kwargs["recipient_id"], "message_id": mid}

    with patch(
        "app.routers.leads.meta_graph.send_messenger_message",
        new=AsyncMock(side_effect=fake_send),
    ):
        return await env.client.post("/api/v1/leads/1/messages", json={"text": "アプリから送信"})


@pytest.mark.asyncio
async def test_echo_first_then_app_send_keeps_one_row_with_staff(env):
    await _seed_known_customer(env)
    await ms._insert_inbound(env.session, lead_id=1, minutes_ago=60)

    await env.wh.process_messenger_event(_echo_body(mid="mid-race-1", app_id=None))
    assert len(await _meta_rows(env.session)) == 2  # 受信1 + 写し1

    resp = await _send_from_app(env, mid="mid-race-1")

    assert resp.status_code == 201, resp.text
    res = await env.session.execute(text(
        "SELECT sent_by_staff_id FROM meta_messages WHERE message_id = 'mid-race-1'"
    ))
    rows = res.fetchall()
    assert len(rows) == 1
    assert rows[0][0] == 1


@pytest.mark.asyncio
async def test_app_send_first_then_echo_keeps_staff(env):
    await _seed_known_customer(env)
    await ms._insert_inbound(env.session, lead_id=1, minutes_ago=60)

    resp = await _send_from_app(env, mid="mid-race-2")
    assert resp.status_code == 201, resp.text

    await env.wh.process_messenger_event(_echo_body(mid="mid-race-2", app_id=None))

    res = await env.session.execute(text(
        "SELECT sent_by_staff_id FROM meta_messages WHERE message_id = 'mid-race-2'"
    ))
    rows = res.fetchall()
    assert len(rows) == 1
    assert rows[0][0] == 1


# ---------------------------------------------------------------------------
# 10〜13. Discord の担当者の直接の投稿
# ---------------------------------------------------------------------------
def _discord_message(*, author_id=9876543210, name="Staff", bot=False, webhook_id=None,
                     msg_id=1517435280951349400, type_=discord.MessageType.default):
    return _FakeMessage(
        id=msg_id,
        content="Please check this order.",
        author=_FakeAuthor(id=author_id, display_name=name, bot=bot),
        channel=_FakeChannel(id=1517435280951349310),
        guild=_FakeGuild(id=1),
        webhook_id=webhook_id,
        type=type_,
    )


def _session_with(*results):
    session = AsyncMock()
    session.execute.side_effect = list(results)
    session.commit = AsyncMock()
    return session


async def _run_discord(session, message):
    db_factory = MagicMock(return_value=_DBContext(session))
    with patch.object(
        ticket_channel_writer, "set_tenant_context", new=AsyncMock(return_value=None)
    ), patch.object(
        ticket_channel_writer, "reset_tenant_context", new=AsyncMock(return_value=None)
    ), patch(
        "app.discord_gateway.ticket_channel_writer.enqueue_inbound_translation",
        MagicMock(return_value=True),
    ) as enqueue_mock, patch.object(
        ticket_channel_writer.customer_reply_notifier,
        "schedule_customer_reply_notice",
        MagicMock(),
    ) as notice_mock:
        handled = await ticket_channel_writer.process_ticket_channel_message(
            db_factory, tenant_id=4, message=message,
        )
    return handled, enqueue_mock, notice_mock


@pytest.mark.asyncio
async def test_discord_staff_post_is_stored_outbound():
    session = _session_with(_mock_result((45, "1234567890", "Shingo")), _mock_result((99,)))

    handled, enqueue_mock, notice_mock = await _run_discord(session, _discord_message())

    assert handled is True
    assert session.commit.await_count == 1
    insert_params = session.execute.call_args_list[1].args[1]
    assert insert_params["direction"] == "outbound"
    assert insert_params["sender_name"] == "Staff"
    assert insert_params["recipient_id"] == "1234567890"
    enqueue_mock.assert_not_called()
    notice_mock.assert_not_called()


@pytest.mark.asyncio
async def test_discord_same_message_twice_uses_on_conflict_and_does_not_raise():
    message = _discord_message()
    first = _session_with(_mock_result((45, "1234567890", "Shingo")), _mock_result((99,)))
    second = _session_with(_mock_result((45, "1234567890", "Shingo")), _mock_result(None))

    handled_1, _, _ = await _run_discord(first, message)
    handled_2, _, _ = await _run_discord(second, message)

    assert handled_1 is True
    assert handled_2 is True
    for session in (first, second):
        insert_sql = str(session.execute.call_args_list[1].args[0])
        assert "ON CONFLICT (message_id)" in insert_sql


@pytest.mark.asyncio
async def test_discord_customer_is_inbound_and_system_posts_are_not_stored():
    # お客さんの投稿は今までどおり inbound で1行
    customer = _session_with(_mock_result((45, "1234567890", "Shingo")), _mock_result((99,)))
    handled, _, notice_mock = await _run_discord(
        customer, _discord_message(author_id=1234567890, name="Shingo"),
    )
    assert handled is True
    assert customer.commit.await_count == 1
    assert customer.execute.call_args_list[1].args[1]["direction"] == "inbound"
    assert customer.execute.call_args_list[1].args[1]["recipient_id"] is None
    notice_mock.assert_called_once()

    # ボット・webhook・ピン留めの知らせは入れない（リードを探す1回だけ・commit 0）
    skipped = (
        _discord_message(author_id=111, name="Bot", bot=True),
        _discord_message(author_id=222, name="Hook", webhook_id=555),
        _discord_message(type_=discord.MessageType.pins_add),
    )
    for message in skipped:
        session = _session_with(_mock_result((45, "1234567890", "Shingo")))
        handled, _, _ = await _run_discord(session, message)
        assert handled is True
        assert session.execute.await_count == 1
        assert session.commit.await_count == 0


@pytest.mark.asyncio
async def test_discord_lead_without_discord_user_id_is_not_stored():
    session = _session_with(_mock_result((45, None, "Shingo")))

    handled, enqueue_mock, notice_mock = await _run_discord(session, _discord_message())

    assert handled is True
    assert session.execute.await_count == 1
    assert session.commit.await_count == 0
    enqueue_mock.assert_not_called()
    notice_mock.assert_not_called()


# ---------------------------------------------------------------------------
# 14. 購読の既定
# ---------------------------------------------------------------------------
def test_default_subscribed_fields_include_message_echoes():
    assert "message_echoes" in meta_graph._DEFAULT_SUBSCRIBED_FIELDS
