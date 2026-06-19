from __future__ import annotations

import sys
import types
from dataclasses import dataclass
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.discord_gateway.config import TenantBotConfig

if "discord" not in sys.modules:
    discord_stub = types.ModuleType("discord")

    class _DummyIntents:
        def __init__(self) -> None:
            self.guilds = False
            self.guild_messages = False
            self.dm_messages = False
            self.message_content = False
            self.members = False

        @classmethod
        def none(cls) -> "_DummyIntents":
            return cls()

    class _DummyClient:
        def __init__(self, *, intents=None) -> None:
            self.intents = intents
            self.guilds = []
            self.user = None

    class _DummyHTTPException(Exception):
        pass

    class _DummyMessage:
        pass

    class _DummyInteraction:
        pass

    class _DummyGuild:
        pass

    class _DummyMember:
        pass

    class _DummyCategoryChannel:
        pass

    class _DummyTextChannel:
        pass

    discord_stub.Intents = _DummyIntents
    discord_stub.Client = _DummyClient
    discord_stub.HTTPException = _DummyHTTPException
    discord_stub.Message = _DummyMessage
    discord_stub.Interaction = _DummyInteraction
    discord_stub.Guild = _DummyGuild
    discord_stub.Member = _DummyMember
    discord_stub.CategoryChannel = _DummyCategoryChannel
    discord_stub.TextChannel = _DummyTextChannel
    discord_stub.InteractionType = types.SimpleNamespace(component=object())
    sys.modules["discord"] = discord_stub

from app.discord_gateway.client import JarvisDiscordClient


@dataclass
class _FakeAuthor:
    id: int
    bot: bool = False
    display_name: str = "staff"
    name: str = "staff"


@dataclass
class _FakeGuild:
    id: int


@dataclass
class _FakeChannel:
    id: int


@dataclass
class _FakeMessage:
    id: int
    content: str
    author: _FakeAuthor
    guild: _FakeGuild | None
    channel: _FakeChannel
    created_at: datetime
    webhook_id: str | None = None


class _DBContext:
    def __init__(self, session: AsyncMock) -> None:
        self.session = session

    async def __aenter__(self) -> AsyncMock:
        return self.session

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


def _mock_result(first_value):
    result = MagicMock()
    result.first.return_value = first_value
    return result


def _make_message(
    *,
    msg_id: int = 1001,
    channel_id: int = 2001,
    author_id: int = 3001,
    content: str = "hello",
    bot: bool = False,
    guild_id: int = 4001,
    webhook_id: str | None = None,
) -> _FakeMessage:
    return _FakeMessage(
        id=msg_id,
        content=content,
        author=_FakeAuthor(id=author_id, bot=bot),
        guild=_FakeGuild(id=guild_id) if guild_id else None,
        channel=_FakeChannel(id=channel_id),
        created_at=datetime.now(timezone.utc),
        webhook_id=webhook_id,
    )


@pytest.mark.asyncio
async def test_ticket_channel_inbound_triggers_translation_and_publish():
    from app.discord_gateway import ticket_channel_writer

    session = AsyncMock()
    session.execute.side_effect = [
        _mock_result((7, "3001", "Customer")),
        _mock_result((101,)),
    ]
    session.commit = AsyncMock()
    db_factory = MagicMock(return_value=_DBContext(session))
    message = _make_message(author_id=3001, content="incoming hello")

    with patch.object(
        ticket_channel_writer, "set_tenant_context", new=AsyncMock(return_value=None)
    ), patch.object(
        ticket_channel_writer, "translate_inbound", new=AsyncMock(return_value=SimpleNamespace())
    ) as mock_translate, patch(
        "app.services.sse_pubsub.publish_inbox_update",
        new=AsyncMock(return_value=None),
    ) as mock_publish:
        handled = await ticket_channel_writer.process_ticket_channel_message(
            db_factory,
            tenant_id=4,
            message=message,
        )

    assert handled is True
    assert session.execute.await_count == 2
    assert session.commit.await_count == 1
    mock_translate.assert_awaited_once()
    assert mock_translate.await_args.kwargs["message_id"] == "1001"
    assert mock_translate.await_args.kwargs["message_text"] == "incoming hello"
    mock_publish.assert_awaited_once_with(4)

    insert_sql = session.execute.await_args_list[1].args[0]
    assert "direction, message_id, created_at" in str(insert_sql)
    assert "'inbound'" in str(insert_sql)


@pytest.mark.asyncio
async def test_ticket_channel_outbound_skips_translation():
    from app.discord_gateway import ticket_channel_writer

    session = AsyncMock()
    session.execute.side_effect = [
        _mock_result((7, "3001", "Customer")),
        _mock_result((202,)),
    ]
    session.commit = AsyncMock()
    db_factory = MagicMock(return_value=_DBContext(session))
    message = _make_message(author_id=9999, content="staff reply")

    with patch.object(
        ticket_channel_writer, "set_tenant_context", new=AsyncMock(return_value=None)
    ), patch.object(
        ticket_channel_writer, "translate_inbound", new=AsyncMock(return_value=SimpleNamespace())
    ) as mock_translate, patch(
        "app.services.sse_pubsub.publish_inbox_update",
        new=AsyncMock(return_value=None),
    ) as mock_publish:
        handled = await ticket_channel_writer.process_ticket_channel_message(
            db_factory,
            tenant_id=4,
            message=message,
        )

    assert handled is True
    assert session.execute.await_count == 2
    assert session.commit.await_count == 1
    mock_translate.assert_not_awaited()
    mock_publish.assert_awaited_once_with(4)

    insert_sql = session.execute.await_args_list[1].args[0]
    assert "direction, message_id, recipient_id" in str(insert_sql)
    assert "'outbound'" in str(insert_sql)


@pytest.mark.asyncio
async def test_ticket_channel_non_ticket_returns_false():
    from app.discord_gateway import ticket_channel_writer

    session = AsyncMock()
    session.execute.side_effect = [_mock_result(None)]
    session.commit = AsyncMock()
    db_factory = MagicMock(return_value=_DBContext(session))
    message = _make_message()

    with patch.object(
        ticket_channel_writer, "set_tenant_context", new=AsyncMock(return_value=None)
    ):
        handled = await ticket_channel_writer.process_ticket_channel_message(
            db_factory,
            tenant_id=4,
            message=message,
        )

    assert handled is False
    assert session.commit.await_count == 0


@pytest.mark.asyncio
async def test_ticket_channel_webhook_is_skipped():
    from app.discord_gateway import ticket_channel_writer

    session = AsyncMock()
    session.execute.side_effect = [_mock_result((7, "3001", "Customer"))]
    session.commit = AsyncMock()
    db_factory = MagicMock(return_value=_DBContext(session))
    message = _make_message(webhook_id="wh_123")

    with patch.object(
        ticket_channel_writer, "set_tenant_context", new=AsyncMock(return_value=None)
    ), patch.object(
        ticket_channel_writer, "translate_inbound", new=AsyncMock(return_value=SimpleNamespace())
    ) as mock_translate, patch(
        "app.services.sse_pubsub.publish_inbox_update",
        new=AsyncMock(return_value=None),
    ) as mock_publish:
        handled = await ticket_channel_writer.process_ticket_channel_message(
            db_factory,
            tenant_id=4,
            message=message,
        )

    assert handled is True
    assert session.execute.await_count == 1
    assert session.commit.await_count == 0
    mock_translate.assert_not_awaited()
    mock_publish.assert_not_awaited()


@pytest.mark.asyncio
async def test_client_routes_ticket_channel_before_guild_parser():
    client = JarvisDiscordClient(
        TenantBotConfig(tenant_id=4, tenant_code="tenant_4", bot_token="x"),
        db_factory=lambda: _DBContext(AsyncMock()),
    )
    message = _make_message()

    with patch(
        "app.discord_gateway.client.ticket_channel_writer.process_ticket_channel_message",
        new=AsyncMock(return_value=True),
    ) as mock_ticket, patch.object(
        client, "_process_message", new=AsyncMock(return_value=None)
    ) as mock_process:
        await client.on_message(message)

    mock_ticket.assert_awaited_once()
    mock_process.assert_not_awaited()


@pytest.mark.asyncio
async def test_client_routes_non_ticket_guild_to_existing_parser():
    client = JarvisDiscordClient(
        TenantBotConfig(tenant_id=4, tenant_code="tenant_4", bot_token="x"),
        db_factory=lambda: _DBContext(AsyncMock()),
    )
    message = _make_message()

    with patch(
        "app.discord_gateway.client.ticket_channel_writer.process_ticket_channel_message",
        new=AsyncMock(return_value=False),
    ) as mock_ticket, patch.object(
        client, "_process_message", new=AsyncMock(return_value=None)
    ) as mock_process:
        await client.on_message(message)

    mock_ticket.assert_awaited_once()
    mock_process.assert_awaited_once()


@pytest.mark.asyncio
async def test_client_ignores_dm_messages():
    client = JarvisDiscordClient(
        TenantBotConfig(tenant_id=4, tenant_code="tenant_4", bot_token="x"),
        db_factory=lambda: _DBContext(AsyncMock()),
    )
    message = _make_message(guild_id=0)
    message.guild = None

    with patch(
        "app.discord_gateway.client.ticket_channel_writer.process_ticket_channel_message",
        new=AsyncMock(return_value=True),
    ) as mock_ticket, patch.object(
        client, "_process_message", new=AsyncMock(return_value=None)
    ) as mock_process:
        await client.on_message(message)

    mock_ticket.assert_not_awaited()
    mock_process.assert_not_awaited()
