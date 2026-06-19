from __future__ import annotations

import sys
import types
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

if "discord" not in sys.modules:
    discord_stub = types.ModuleType("discord")

    class _DummyIntents:
        @staticmethod
        def none():
            return _DummyIntents()

        def __init__(self) -> None:
            self.guilds = False
            self.guild_messages = False
            self.dm_messages = False
            self.message_content = False
            self.members = False

    class _DummyClient:
        def __init__(self, *, intents=None) -> None:
            self.intents = intents

    class _DummyHTTPException(Exception):
        pass

    class _DummyInteractionType:
        component = object()

    class _DummyMessage:
        pass

    class _DummyInteraction:
        pass

    discord_stub.Intents = _DummyIntents
    discord_stub.Client = _DummyClient
    discord_stub.HTTPException = _DummyHTTPException
    discord_stub.InteractionType = _DummyInteractionType
    discord_stub.Message = _DummyMessage
    discord_stub.Interaction = _DummyInteraction
    sys.modules["discord"] = discord_stub

from app.discord_gateway import client, ticket_channel_writer
from app.tasks.translation import _run_translate_inbound_message, translate_inbound_message


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


def test_translate_inbound_message_task_wrapper_runs_and_disposes_engine():
    fake_engine = MagicMock()
    fake_engine.dispose = AsyncMock(return_value=None)
    with patch(
        "app.tasks.translation._run_translate_inbound_message",
        AsyncMock(return_value={"status": "ok"}),
    ) as run_mock, patch(
        "app.database.engine",
        fake_engine,
    ):
        result = translate_inbound_message(
            tenant_id=7,
            table_ref="meta_messages",
            message_id="mid-1",
            message_text="hello",
            target_language="ja",
        )

    assert result["status"] == "ok"
    run_mock.assert_awaited_once()
    fake_engine.dispose.assert_awaited_once()


@pytest.mark.asyncio
async def test_worker_translation_task_translates_then_publishes():
    session = AsyncMock()
    translate_result = MagicMock(
        cached=False,
        engine="gemini-1.5-flash",
        confidence=0.97,
        translated_text="こんにちは",
    )

    with patch("app.database.AsyncSessionLocal", return_value=_DBContext(session)), patch(
        "app.services.message_translator.translate_inbound",
        AsyncMock(return_value=translate_result),
    ) as translate_mock, patch(
        "app.services.sse_pubsub.publish_inbox_update",
        AsyncMock(return_value=None),
    ) as publish_mock:
        result = await _run_translate_inbound_message(
            tenant_id=7,
            table_ref="meta_messages",
            message_id="mid-1",
            message_text="hello",
            target_language="ja",
        )

    assert result["status"] == "ok"
    translate_mock.assert_awaited_once()
    translate_kwargs = translate_mock.await_args.kwargs
    assert translate_kwargs["table_ref"] == "tenant_007.message_translations"
    assert translate_kwargs["message_id"] == "mid-1"
    assert translate_kwargs["target_language"] == "ja"
    publish_mock.assert_awaited_once_with(7)


@pytest.mark.asyncio
async def test_client_routes_ticket_channel_message_before_inventory_parser():
    session = AsyncMock()
    session.execute.side_effect = [
        _mock_result((45, "1234567890", "Shingo")),
        _mock_result((1,)),
    ]
    session.commit = AsyncMock()
    db_factory = MagicMock(return_value=_DBContext(session))

    message = _FakeMessage(
        id=1517435280951349311,
        content="Do you accept PayPal?",
        author=_FakeAuthor(id=1234567890, display_name="Shingo"),
        channel=_FakeChannel(id=1517435280951349310),
        guild=_FakeGuild(id=1),
    )

    mock_client = client.JarvisDiscordClient.__new__(client.JarvisDiscordClient)
    mock_client.tenant = MagicMock(tenant_id=4, tenant_code="tenant-4")
    mock_client._db_factory = MagicMock(return_value=db_factory)
    mock_client._process_message = AsyncMock(return_value=None)
    mock_client._process_dm_message = AsyncMock(return_value=None)

    with patch.object(
        ticket_channel_writer, "set_tenant_context", new=AsyncMock(return_value=None)
    ), patch(
        "app.tasks.translation.translate_inbound_message.delay",
        MagicMock(return_value=None),
    ) as delay_mock:
        await client.JarvisDiscordClient._process_guild_message(mock_client, message)

    mock_client._process_message.assert_not_awaited()
    delay_mock.assert_called_once_with(
        tenant_id=4,
        table_ref="meta_messages",
        message_id="1517435280951349311",
        message_text="Do you accept PayPal?",
        target_language="ja",
    )


@pytest.mark.asyncio
async def test_ticket_channel_writer_ignores_staff_messages_without_publish():
    session = AsyncMock()
    session.execute.side_effect = [
        _mock_result((45, "1234567890", "Shingo")),
    ]
    session.commit = AsyncMock()
    db_factory = MagicMock(return_value=_DBContext(session))

    message = _FakeMessage(
        id=1517435280951349312,
        content="Please check this order.",
        author=_FakeAuthor(id=9876543210, display_name="Staff"),
        channel=_FakeChannel(id=1517435280951349310),
        guild=_FakeGuild(id=1),
    )

    with patch.object(
        ticket_channel_writer, "set_tenant_context", new=AsyncMock(return_value=None)
    ), patch(
        "app.tasks.translation.translate_inbound_message.delay",
        MagicMock(return_value=None),
    ) as delay_mock, patch(
        "app.services.sse_pubsub.publish_inbox_update",
        AsyncMock(return_value=None),
    ) as publish_mock:
        handled = await ticket_channel_writer.process_ticket_channel_message(
            db_factory,
            tenant_id=4,
            message=message,
        )

    assert handled is True
    delay_mock.assert_not_called()
    publish_mock.assert_not_called()
