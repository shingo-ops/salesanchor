"""お客さんの返信の知らせ（第2段 2d・KGI 13）。

対象:
  - app.services.customer_reply_notifier（send_customer_reply_notice / schedule_customer_reply_notice）
  - app.discord_gateway.ticket_channel_writer（新しい行のときだけ予約する）
  （webhook の 2 件は test_webhook_instagram.py の末尾）
"""
from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

import pytest
from sqlalchemy import text

from app.discord_gateway import ticket_channel_writer
from app.services import customer_reply_notifier
from app.services.customer_reply_notifier import send_customer_reply_notice

# Discord のユーザー ID は 18 桁の数字。直書きすると gitleaks が誤検知するため組み立てる（架空の値）。
FAKE_DISCORD_ID = "9" * 18


# ---------------------------------------------------------------------------
# ヘルパー（test_notification_event_routing.py の作法を写す）
# ---------------------------------------------------------------------------

class _SessionCtx:
    def __init__(self, session):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, exc_type, exc, tb):
        return False


async def _insert_channel(db, *, tenant_id, channel_name, webhook_url, event_types, is_active=True):
    await db.execute(
        text("""
            INSERT INTO notification_channels (tenant_id, channel_name, webhook_url, event_types, is_active)
            VALUES (:tenant_id, :name, :url, :events, :is_active)
        """),
        {"tenant_id": tenant_id, "name": channel_name, "url": webhook_url,
         "events": json.dumps(event_types), "is_active": is_active},
    )


async def _insert_staff(db, *, tenant_id, user_id, surname_jp, given_name_jp, discord_user_id=None):
    await db.execute(
        text("""
            INSERT INTO staff (tenant_id, user_id, staff_code, surname_jp, given_name_jp, discord_user_id)
            VALUES (:tenant_id, :user_id, :staff_code, :surname_jp, :given_name_jp, :discord_user_id)
        """),
        {"tenant_id": tenant_id, "user_id": user_id, "staff_code": f"S{user_id:04d}",
         "surname_jp": surname_jp, "given_name_jp": given_name_jp,
         "discord_user_id": discord_user_id},
    )


async def _insert_lead(db, *, tenant_id, lead_id, customer_name, lead_code, assigned_to=None):
    await db.execute(
        text("""
            INSERT INTO leads (id, tenant_id, customer_name, lead_code, assigned_to)
            VALUES (:id, :tenant_id, :customer_name, :lead_code, :assigned_to)
        """),
        {"id": lead_id, "tenant_id": tenant_id, "customer_name": customer_name,
         "lead_code": lead_code, "assigned_to": assigned_to},
    )


class _FakeDiscordResponse:
    status_code = 204


class _FakeDiscordAsyncClient:
    """httpx.AsyncClient の代わりに送り先と payload を捕捉する。"""

    captured_payloads: list = []
    captured_urls: list = []

    def __init__(self, *_a, **_kw):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_a):
        return False

    async def post(self, url, json):  # noqa: A002 - httpx の引数名に合わせる
        _FakeDiscordAsyncClient.captured_urls.append(url)
        _FakeDiscordAsyncClient.captured_payloads.append(json)
        return _FakeDiscordResponse()


@pytest.fixture
def fake_discord():
    _FakeDiscordAsyncClient.captured_payloads = []
    _FakeDiscordAsyncClient.captured_urls = []
    with patch("app.routers.notifications.httpx.AsyncClient", _FakeDiscordAsyncClient):
        yield _FakeDiscordAsyncClient


async def _seed_basic(db, *, assigned_to=5, discord_user_id=FAKE_DISCORD_ID, customer_name="山田商事"):
    await _insert_channel(db, tenant_id=999, channel_name="reply",
                          webhook_url="https://discord.example/webhooks/1",
                          event_types=["customer_reply_received"])
    if assigned_to is not None:
        await _insert_staff(db, tenant_id=999, user_id=assigned_to, surname_jp="谷澤",
                            given_name_jp="伸吾", discord_user_id=discord_user_id)
    await _insert_lead(db, tenant_id=999, lead_id=10, customer_name=customer_name,
                       lead_code="L-00010", assigned_to=assigned_to)
    await db.commit()


# ---------------------------------------------------------------------------
# send_customer_reply_notice
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_notice_mentions_assignee_with_numeric_discord_id(db_session, fake_discord):
    await _seed_basic(db_session)

    ok = await send_customer_reply_notice(db_session, tenant_id=999, lead_id=10, source="messenger")

    assert ok is True
    assert len(fake_discord.captured_payloads) == 1
    payload = fake_discord.captured_payloads[0]
    assert payload["content"] == f"<@{FAKE_DISCORD_ID}>"
    assert payload["allowed_mentions"] == {"parse": [], "users": [FAKE_DISCORD_ID]}


@pytest.mark.asyncio
async def test_notice_without_assignee_has_no_mention(db_session, fake_discord):
    await _seed_basic(db_session, assigned_to=None)

    await send_customer_reply_notice(db_session, tenant_id=999, lead_id=10, source="messenger")

    assert len(fake_discord.captured_payloads) == 1
    payload = fake_discord.captured_payloads[0]
    assert "<@" not in payload.get("content", "")


@pytest.mark.asyncio
async def test_notice_without_discord_id_has_no_mention(db_session, fake_discord):
    await _seed_basic(db_session, discord_user_id=None)

    await send_customer_reply_notice(db_session, tenant_id=999, lead_id=10, source="messenger")

    assert len(fake_discord.captured_payloads) == 1
    payload = fake_discord.captured_payloads[0]
    assert "<@" not in payload.get("content", "")
    assert "allowed_mentions" not in payload


@pytest.mark.asyncio
async def test_notice_empty_customer_name_uses_fixed_text(db_session, fake_discord):
    await _seed_basic(db_session, customer_name="")

    await send_customer_reply_notice(db_session, tenant_id=999, lead_id=10, source="instagram")

    description = fake_discord.captured_payloads[0]["embeds"][0]["description"]
    assert "お客さん: 名前の無いリード" in description


@pytest.mark.asyncio
async def test_notice_missing_lead_sends_nothing(db_session, fake_discord):
    await _seed_basic(db_session)

    ok = await send_customer_reply_notice(db_session, tenant_id=999, lead_id=404, source="messenger")

    assert ok is False
    assert fake_discord.captured_payloads == []


@pytest.mark.asyncio
async def test_notice_unknown_source_sends_nothing(db_session, fake_discord):
    await _seed_basic(db_session)

    ok = await send_customer_reply_notice(db_session, tenant_id=999, lead_id=10, source="line")

    assert ok is False
    assert fake_discord.captured_payloads == []


@pytest.mark.asyncio
async def test_notice_message_has_only_name_source_link(db_session, fake_discord, monkeypatch):
    monkeypatch.delenv("FRONTEND_BASE_URL", raising=False)
    await _seed_basic(db_session)

    await send_customer_reply_notice(db_session, tenant_id=999, lead_id=10, source="messenger")

    description = fake_discord.captured_payloads[0]["embeds"][0]["description"]
    assert description == (
        "お客さん: 山田商事\nどこから: Messenger\nhttps://app.salesanchor.jp/lead-chat?lead_id=10"
    )
    # 本文・送った人の番号が入る道が無い（関数の引数に本文・番号が無い）
    import inspect

    params = set(inspect.signature(send_customer_reply_notice).parameters)
    assert params == {"db", "tenant_id", "lead_id", "source"}


@pytest.mark.asyncio
async def test_notice_uses_frontend_base_url_env(db_session, fake_discord, monkeypatch):
    monkeypatch.setenv("FRONTEND_BASE_URL", "https://example.test/")
    await _seed_basic(db_session)

    await send_customer_reply_notice(db_session, tenant_id=999, lead_id=10, source="messenger")

    description = fake_discord.captured_payloads[0]["embeds"][0]["description"]
    assert description.split("\n")[-1] == "https://example.test/lead-chat?lead_id=10"


@pytest.mark.asyncio
async def test_notice_swallows_errors_and_returns_false(db_session):
    await _seed_basic(db_session)

    with patch("app.routers.notifications.send_discord_notification",
               new=AsyncMock(side_effect=RuntimeError("boom"))):
        ok = await send_customer_reply_notice(db_session, tenant_id=999, lead_id=10, source="messenger")

    assert ok is False


@pytest.mark.asyncio
async def test_notice_goes_only_to_customer_reply_channel(db_session, fake_discord):
    await _insert_channel(db_session, tenant_id=999, channel_name="reply",
                          webhook_url="https://discord.example/webhooks/reply",
                          event_types=["customer_reply_received"])
    await _insert_channel(db_session, tenant_id=999, channel_name="assign",
                          webhook_url="https://discord.example/webhooks/assign",
                          event_types=["lead_assigned"])
    await _insert_lead(db_session, tenant_id=999, lead_id=10, customer_name="山田商事", lead_code="L-00010")
    await db_session.commit()

    await send_customer_reply_notice(db_session, tenant_id=999, lead_id=10, source="messenger")

    assert fake_discord.captured_urls == ["https://discord.example/webhooks/reply"]


# ---------------------------------------------------------------------------
# schedule_customer_reply_notice
# ---------------------------------------------------------------------------

def test_schedule_does_nothing_when_disabled():
    # conftest の autouse fixture が SCHEDULE_ENABLED=False にしている
    assert customer_reply_notifier.SCHEDULE_ENABLED is False
    with patch("app.services.customer_reply_notifier.asyncio.create_task") as create_task:
        customer_reply_notifier.schedule_customer_reply_notice(
            MagicMock(), tenant_id=999, lead_id=10, source="messenger",
        )
    create_task.assert_not_called()


@pytest.mark.asyncio
async def test_schedule_runs_send_once_when_enabled(monkeypatch):
    monkeypatch.setattr(customer_reply_notifier, "SCHEDULE_ENABLED", True)
    send_mock = AsyncMock(return_value=True)
    monkeypatch.setattr(customer_reply_notifier, "send_customer_reply_notice", send_mock)
    fake_db = MagicMock()
    db_factory = MagicMock(return_value=_SessionCtx(fake_db))

    customer_reply_notifier.schedule_customer_reply_notice(
        db_factory, tenant_id=999, lead_id=10, source="discord",
    )
    pending = list(customer_reply_notifier._pending)
    assert len(pending) == 1
    await asyncio.gather(*pending)

    send_mock.assert_awaited_once()
    assert send_mock.await_args.args == (fake_db,)
    assert send_mock.await_args.kwargs == {"tenant_id": 999, "lead_id": 10, "source": "discord"}


# ---------------------------------------------------------------------------
# ticket_channel_writer（test_ticket_channel_translation.py の作りを写す）
# ---------------------------------------------------------------------------

class _DBContext:
    def __init__(self, session: AsyncMock) -> None:
        self.session = session

    async def __aenter__(self) -> AsyncMock:
        return self.session

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


@dataclass(frozen=True)
class _FakeAuthor:
    id: int
    display_name: str
    bot: bool = False


@dataclass(frozen=True)
class _FakeChannel:
    id: int


@dataclass(frozen=True)
class _FakeGuild:
    id: int


@dataclass(frozen=True)
class _FakeMessage:
    id: int
    content: str
    author: _FakeAuthor
    channel: _FakeChannel
    guild: _FakeGuild
    created_at: object | None = None
    webhook_id: object | None = None


def _mock_result(first_value):
    result = MagicMock()
    result.first.return_value = first_value
    return result


async def _run_writer(*, insert_result, author_id):
    session = AsyncMock()
    session.execute.side_effect = [
        _mock_result((45, "1234567890", "Shingo")),
        insert_result,
    ]
    session.commit = AsyncMock()
    db_factory = MagicMock(return_value=_DBContext(session))
    message = _FakeMessage(
        id=1517435280951349311,
        content="Do you accept PayPal?",
        author=_FakeAuthor(id=author_id, display_name="Shingo"),
        channel=_FakeChannel(id=1517435280951349310),
        guild=_FakeGuild(id=1),
    )
    with patch.object(
        ticket_channel_writer, "set_tenant_context", new=AsyncMock(return_value=None)
    ), patch(
        "app.discord_gateway.ticket_channel_writer.enqueue_inbound_translation",
        MagicMock(return_value=True),
    ), patch(
        "app.discord_gateway.ticket_channel_writer.customer_reply_notifier.schedule_customer_reply_notice",
        MagicMock(),
    ) as schedule_mock:
        await ticket_channel_writer.process_ticket_channel_message(
            db_factory, tenant_id=4, message=message,
        )
    return schedule_mock, db_factory


@pytest.mark.asyncio
async def test_ticket_writer_schedules_notice_for_new_row():
    schedule_mock, db_factory = await _run_writer(insert_result=_mock_result((1,)), author_id=1234567890)

    schedule_mock.assert_called_once_with(db_factory, tenant_id=4, lead_id=45, source="discord")


@pytest.mark.asyncio
async def test_ticket_writer_does_not_schedule_for_duplicate():
    schedule_mock, _ = await _run_writer(insert_result=_mock_result(None), author_id=1234567890)

    schedule_mock.assert_not_called()


@pytest.mark.asyncio
async def test_ticket_writer_does_not_schedule_for_staff_message():
    schedule_mock, _ = await _run_writer(insert_result=_mock_result((1,)), author_id=9876543210)

    schedule_mock.assert_not_called()
