"""チケットチャンネル削除時の自動復旧 (PO決定 2026-10-02)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

from app.discord_gateway import ticket_channel_creator
from app.discord_gateway.client import JarvisDiscordClient

TENANT_ID = 1
TICKET_START_ID = 555
DELETED_ID = 777
USER_ID = 1255555836776939692


class _DBContext:
    def __init__(self, session: AsyncMock) -> None:
        self.session = session

    async def __aenter__(self) -> AsyncMock:
        return self.session

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


def _all_result(rows):
    result = MagicMock()
    result.all.return_value = rows
    return result


def _config_result(config):
    result = MagicMock()
    result.mappings.return_value.first.return_value = config
    return result


def _http_exc(status: int) -> discord.HTTPException:
    exc = discord.HTTPException.__new__(discord.HTTPException)
    exc.status = status
    return exc


def _setup(*, rows, config=None, member_present=True, guild_channels=None):
    session = AsyncMock()
    session.commit = AsyncMock()
    session.execute.side_effect = [
        _all_result(rows),
        _config_result(config or {"ticket_button_channel_id": str(TICKET_START_ID)}),
        MagicMock(),  # UPDATE
    ]
    db_factory = MagicMock(side_effect=lambda: _DBContext(session))
    ticket_start = MagicMock(spec=discord.TextChannel)
    ticket_start.id = TICKET_START_ID
    ticket_start.set_permissions = AsyncMock()
    guild = MagicMock()
    guild.id = 42
    channels = {TICKET_START_ID: ticket_start, **(guild_channels or {})}
    guild.get_channel = MagicMock(side_effect=lambda cid: channels.get(cid))
    member = MagicMock()
    guild.get_member = MagicMock(return_value=member if member_present else None)
    http = MagicMock()
    http.delete_channel_permissions = AsyncMock()
    return session, db_factory, guild, ticket_start, member, http


@pytest.fixture(autouse=True)
def _no_tenant_context():
    with patch.object(
        ticket_channel_creator, "set_tenant_context", new=AsyncMock(return_value=None)
    ):
        yield


@pytest.mark.asyncio
async def test_restore_removes_overwrite_and_nulls_channel_id():
    session, db_factory, guild, ticket_start, member, http = _setup(
        rows=[(str(USER_ID),)]
    )

    restored = await ticket_channel_creator.restore_after_ticket_deleted(
        guild, TENANT_ID, DELETED_ID, db_factory, http=http
    )

    assert restored == 1
    ticket_start.set_permissions.assert_awaited_once()
    assert ticket_start.set_permissions.await_args.args == (member,)
    assert ticket_start.set_permissions.await_args.kwargs["overwrite"] is None
    update_sql = str(session.execute.await_args_list[2].args[0])
    assert "SET discord_guild_channel_id = NULL" in update_sql
    assert "tenant_001.leads" in update_sql
    assert session.execute.await_args_list[2].args[1] == {"ch_id": str(DELETED_ID)}
    assert session.commit.await_count == 1
    assert "lead_channels" not in update_sql


@pytest.mark.asyncio
async def test_restore_is_noop_for_unrelated_channel():
    session, db_factory, guild, ticket_start, _, http = _setup(rows=[])

    restored = await ticket_channel_creator.restore_after_ticket_deleted(
        guild, TENANT_ID, 999, db_factory, http=http
    )

    assert restored == 0
    ticket_start.set_permissions.assert_not_awaited()
    http.delete_channel_permissions.assert_not_awaited()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_restore_uses_rest_when_member_left_guild():
    session, db_factory, guild, ticket_start, _, http = _setup(
        rows=[(str(USER_ID),)], member_present=False
    )

    restored = await ticket_channel_creator.restore_after_ticket_deleted(
        guild, TENANT_ID, DELETED_ID, db_factory, http=http
    )

    assert restored == 1
    ticket_start.set_permissions.assert_not_awaited()
    http.delete_channel_permissions.assert_awaited_once()
    assert http.delete_channel_permissions.await_args.args == (TICKET_START_ID, USER_ID)
    assert session.commit.await_count == 1


@pytest.mark.asyncio
async def test_restore_keeps_channel_id_when_member_left_and_no_http():
    session, db_factory, guild, _, _, _ = _setup(
        rows=[(str(USER_ID),)], member_present=False
    )

    restored = await ticket_channel_creator.restore_after_ticket_deleted(
        guild, TENANT_ID, DELETED_ID, db_factory, http=None
    )

    assert restored == 0
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_restore_keeps_channel_id_when_discord_call_fails():
    session, db_factory, guild, ticket_start, _, http = _setup(rows=[(str(USER_ID),)])
    ticket_start.set_permissions.side_effect = _http_exc(500)

    restored = await ticket_channel_creator.restore_after_ticket_deleted(
        guild, TENANT_ID, DELETED_ID, db_factory, http=http
    )

    assert restored == 0
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_restore_treats_overwrite_not_found_as_done():
    session, db_factory, guild, ticket_start, _, http = _setup(rows=[(str(USER_ID),)])
    ticket_start.set_permissions.side_effect = _http_exc(404)

    restored = await ticket_channel_creator.restore_after_ticket_deleted(
        guild, TENANT_ID, DELETED_ID, db_factory, http=http
    )

    assert restored == 1
    assert session.commit.await_count == 1


@pytest.mark.asyncio
async def test_restore_is_idempotent_on_second_call():
    session, db_factory, guild, _, _, http = _setup(rows=[(str(USER_ID),)])
    first = await ticket_channel_creator.restore_after_ticket_deleted(
        guild, TENANT_ID, DELETED_ID, db_factory, http=http
    )
    session.execute.side_effect = [_all_result([])]

    second = await ticket_channel_creator.restore_after_ticket_deleted(
        guild, TENANT_ID, DELETED_ID, db_factory, http=http
    )

    assert (first, second) == (1, 0)


@pytest.mark.asyncio
async def test_restore_nulls_id_even_when_lead_has_no_discord_user():
    session, db_factory, guild, ticket_start, _, http = _setup(rows=[(None,)])

    restored = await ticket_channel_creator.restore_after_ticket_deleted(
        guild, TENANT_ID, DELETED_ID, db_factory, http=http
    )

    assert restored == 1
    ticket_start.set_permissions.assert_not_awaited()
    assert session.commit.await_count == 1


@pytest.mark.asyncio
async def test_reconcile_restores_only_channels_confirmed_missing():
    session = AsyncMock()
    session.commit = AsyncMock()
    db_factory = MagicMock(side_effect=lambda: _DBContext(session))
    alive_id, gone_id, unknown_id = 100, 200, 300
    guild = MagicMock()
    alive = MagicMock(spec=discord.TextChannel)
    guild.get_channel = MagicMock(
        side_effect=lambda cid: alive if cid == alive_id else None
    )

    async def _fetch(cid):
        if cid == gone_id:
            raise _http_exc(404)
        raise _http_exc(500)  # 確認できないものは触らない

    guild.fetch_channel = AsyncMock(side_effect=_fetch)
    session.execute.side_effect = [
        _all_result([(str(alive_id),), (str(gone_id),), (str(unknown_id),)]),
    ]

    with patch.object(
        ticket_channel_creator,
        "restore_after_ticket_deleted",
        new=AsyncMock(return_value=1),
    ) as restore:
        restored = await ticket_channel_creator.reconcile_deleted_ticket_channels(
            guild, TENANT_ID, db_factory, http="http"
        )

    assert restored == 1
    restore.assert_awaited_once_with(
        guild, TENANT_ID, str(gone_id), db_factory, http="http"
    )


@pytest.mark.asyncio
async def test_client_delete_event_ignores_non_text_channel():
    client = JarvisDiscordClient(db_factory=MagicMock())
    voice = MagicMock(spec=discord.VoiceChannel)

    with patch.object(
        ticket_channel_creator, "restore_after_ticket_deleted", new=AsyncMock()
    ) as restore:
        await client.on_guild_channel_delete(voice)

    restore.assert_not_awaited()
    await client.close()


@pytest.mark.asyncio
async def test_client_delete_event_skips_unregistered_guild():
    client = JarvisDiscordClient(db_factory=MagicMock())
    channel = MagicMock(spec=discord.TextChannel)
    channel.guild = MagicMock(id=42)

    with patch.object(
        client, "_resolve_tenant_id", new=AsyncMock(return_value=None)
    ), patch.object(
        ticket_channel_creator, "restore_after_ticket_deleted", new=AsyncMock()
    ) as restore:
        await client.on_guild_channel_delete(channel)

    restore.assert_not_awaited()
    await client.close()


@pytest.mark.asyncio
async def test_client_delete_event_calls_restore_for_tenant_guild():
    client = JarvisDiscordClient(db_factory=MagicMock())
    channel = MagicMock(spec=discord.TextChannel)
    channel.id = DELETED_ID
    channel.guild = MagicMock(id=42)

    with patch.object(
        client, "_resolve_tenant_id", new=AsyncMock(return_value=TENANT_ID)
    ), patch.object(
        ticket_channel_creator,
        "restore_after_ticket_deleted",
        new=AsyncMock(return_value=1),
    ) as restore:
        await client.on_guild_channel_delete(channel)

    restore.assert_awaited_once()
    assert restore.await_args.args[:3] == (channel.guild, TENANT_ID, DELETED_ID)
    await client.close()


@pytest.mark.asyncio
async def test_client_delete_event_swallows_restore_failure():
    client = JarvisDiscordClient(db_factory=MagicMock())
    channel = MagicMock(spec=discord.TextChannel)
    channel.id = DELETED_ID
    channel.guild = MagicMock(id=42)

    with patch.object(
        client, "_resolve_tenant_id", new=AsyncMock(return_value=TENANT_ID)
    ), patch.object(
        ticket_channel_creator,
        "restore_after_ticket_deleted",
        new=AsyncMock(side_effect=RuntimeError("db down")),
    ):
        await client.on_guild_channel_delete(channel)  # 例外が漏れないこと

    await client.close()
