from __future__ import annotations

import sys
import types
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

if "discord" not in sys.modules:
    discord_stub = types.ModuleType("discord")

    class _DummyPermissionOverwrite:
        def __init__(self, **kwargs) -> None:
            self.__dict__.update(kwargs)

    class _DummyHTTPException(Exception):
        pass

    class _DummyForbidden(Exception):
        pass

    class _DummyGuild:
        pass

    class _DummyMember:
        pass

    class _DummyCategoryChannel:
        pass

    class _DummyTextChannel:
        pass

    discord_stub.PermissionOverwrite = _DummyPermissionOverwrite
    discord_stub.HTTPException = _DummyHTTPException
    discord_stub.Forbidden = _DummyForbidden
    discord_stub.Guild = _DummyGuild
    discord_stub.Member = _DummyMember
    discord_stub.CategoryChannel = _DummyCategoryChannel
    discord_stub.TextChannel = _DummyTextChannel
    sys.modules["discord"] = discord_stub

from app.discord_gateway import ticket_channel_creator


@dataclass(frozen=True)
class _FakeRole:
    id: int
    name: str


@dataclass(frozen=True)
class _FakeMember:
    id: int
    display_name: str


@dataclass(frozen=True)
class _FakeCategoryChannel(sys.modules["discord"].CategoryChannel):
    id: int


class _FakeTextChannel(sys.modules["discord"].TextChannel):
    def __init__(self, *, id: int, mention_text: str, send: AsyncMock) -> None:
        self.id = id
        self.mention_text = mention_text
        self.send = send

    @property
    def mention(self):
        return self.mention_text

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


def _make_guild(*, category_id: int, bot_member: _FakeMember, staff_role: _FakeRole | None = None):
    category = _FakeCategoryChannel(category_id)
    guild = MagicMock()
    guild.default_role = _FakeRole(id=0, name="@everyone")
    guild.me = bot_member
    guild._category = category
    guild.get_role = MagicMock(return_value=staff_role)
    created_channel = _FakeTextChannel(
        id=1517435280951349310,
        mention_text="#ticket-shingo-9692",
        send=AsyncMock(return_value=None),
    )
    guild.create_text_channel = AsyncMock(return_value=created_channel)
    guild.get_channel = MagicMock(side_effect=lambda channel_id: category if channel_id == category_id else None)
    return guild, category, created_channel


@pytest.mark.asyncio
async def test_ticket_channel_adds_bot_visibility_and_updates_existing_lead():
    session = AsyncMock()
    session.execute.side_effect = [
        _mock_result((7, None, "Shingo")),
        _mock_result((1,)),
        _mock_result((1,)),
    ]
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    db_factory = MagicMock(return_value=_DBContext(session))

    bot_member = _FakeMember(id=9999, display_name="SalesAnchor Bot")
    staff_role = _FakeRole(id=456, name="Staff")
    guild, category, created_channel = _make_guild(
        category_id=123,
        bot_member=bot_member,
        staff_role=staff_role,
    )
    member = _FakeMember(id=1255555836776939692, display_name="Shingo")

    with patch.object(
        ticket_channel_creator, "set_tenant_context", new=AsyncMock(return_value=None)
    ):
        channel = await ticket_channel_creator.get_or_create_ticket_channel(
            guild=guild,
            config={
                "ticket_category_id": "123",
                "staff_role_id": "456",
                "welcome_template": "Welcome!",
            },
            member=member,
            tenant_id=4,
            db_factory=db_factory,
        )

    assert channel is created_channel
    assert session.execute.await_count == 3
    assert session.commit.await_count == 1
    guild.create_text_channel.assert_awaited_once()
    guild.get_channel.assert_called_with(123)
    guild.get_role.assert_called_with(456)
    created_kwargs = guild.create_text_channel.await_args.kwargs
    overwrites = created_kwargs["overwrites"]
    assert overwrites[guild.default_role].view_channel is False
    assert overwrites[member].view_channel is True
    assert overwrites[member].send_messages is True
    assert overwrites[member].read_message_history is True
    assert overwrites[staff_role].view_channel is True
    assert overwrites[bot_member].view_channel is True
    assert overwrites[bot_member].read_message_history is True
    assert overwrites[bot_member].send_messages is True
    created_channel.send.assert_awaited_once_with("Welcome!")

    update_sql = session.execute.await_args_list[1].args[0]
    ensure_sql = session.execute.await_args_list[2].args[0]
    assert "SET discord_guild_channel_id" in str(update_sql)
    assert "INSERT INTO tenant_004.lead_channels" in str(ensure_sql)


@pytest.mark.asyncio
async def test_ticket_channel_creates_missing_lead_and_links_channel():
    session = AsyncMock()
    session.execute.side_effect = [
        _mock_result(None),
        _mock_result((77,)),
        _mock_result((1,)),
    ]
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    db_factory = MagicMock(return_value=_DBContext(session))

    bot_member = _FakeMember(id=9999, display_name="SalesAnchor Bot")
    guild, category, created_channel = _make_guild(
        category_id=123,
        bot_member=bot_member,
        staff_role=None,
    )
    member = _FakeMember(id=1255555836776939692, display_name="Shingo")

    with patch.object(
        ticket_channel_creator, "set_tenant_context", new=AsyncMock(return_value=None)
    ):
        channel = await ticket_channel_creator.get_or_create_ticket_channel(
            guild=guild,
            config={
                "ticket_category_id": "123",
                "staff_role_id": None,
                "welcome_template": "Welcome!",
            },
            member=member,
            tenant_id=4,
            db_factory=db_factory,
        )

    assert channel is created_channel
    assert session.execute.await_count == 3
    assert session.commit.await_count == 1
    created_kwargs = guild.create_text_channel.await_args.kwargs
    overwrites = created_kwargs["overwrites"]
    assert overwrites[bot_member].view_channel is True
    assert overwrites[bot_member].read_message_history is True
    assert overwrites[bot_member].send_messages is True
    assert "discord_guild_channel_id" in str(session.execute.await_args_list[1].args[0])
    assert "INSERT INTO tenant_004.lead_channels" in str(session.execute.await_args_list[2].args[0])
    created_channel.send.assert_awaited_once_with("Welcome!")


@pytest.mark.asyncio
async def test_ticket_channel_returns_existing_channel_without_recreate():
    session = AsyncMock()
    session.execute.side_effect = [_mock_result((7, "1517435280951349310", "Shingo"))]
    session.commit = AsyncMock()
    db_factory = MagicMock(return_value=_DBContext(session))

    bot_member = _FakeMember(id=9999, display_name="SalesAnchor Bot")
    existing_channel = _FakeTextChannel(
        id=1517435280951349310,
        mention_text="#ticket-shingo-9692",
        send=AsyncMock(return_value=None),
    )
    guild = MagicMock()
    guild.default_role = _FakeRole(id=0, name="@everyone")
    guild.me = bot_member
    category = _FakeCategoryChannel(123)
    guild.get_channel = MagicMock(
        side_effect=lambda channel_id: category if channel_id == 123 else existing_channel if channel_id == existing_channel.id else None
    )
    guild.get_role = MagicMock(return_value=None)
    guild.create_text_channel = AsyncMock()
    member = _FakeMember(id=1255555836776939692, display_name="Shingo")

    with patch.object(
        ticket_channel_creator, "set_tenant_context", new=AsyncMock(return_value=None)
    ):
        channel = await ticket_channel_creator.get_or_create_ticket_channel(
            guild=guild,
            config={
                "ticket_category_id": "123",
                "staff_role_id": None,
                "welcome_template": "Welcome!",
            },
            member=member,
            tenant_id=4,
            db_factory=db_factory,
        )

    assert channel is existing_channel
    guild.create_text_channel.assert_not_awaited()
    assert session.commit.await_count == 0
