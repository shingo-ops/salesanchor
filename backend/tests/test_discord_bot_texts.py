"""
Discord Bot 顧客向け文言の英語化テスト（SSOT: app/discord_gateway/bot_texts.py）。

カバー:
- bot_texts の文言（PO 指定の英語）
- ボタン押下への ephemeral 応答が bot_texts から供給されること（client.on_interaction）
- ウェルカム既定文・設定 API の既定値が bot_texts と一致すること
- DB 既定値を英語へ揃える migration が bot_texts と同一の文言であること（乖離防止）

実行:
    pytest backend/tests/test_discord_bot_texts.py -v
"""
from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

import discord
import pytest

from app.discord_gateway import bot_texts, ticket_channel_creator
from app.discord_gateway.client import JarvisDiscordClient
from app.routers.discord_ticket_config import (
    DiscordTicketConfigResponse,
    DiscordTicketConfigUpdate,
)

MIGRATION = (
    Path(__file__).resolve().parents[2]
    / "migrations"
    / "20260930_130000_set_discord_welcome_template_english.sql"
)
OLD_JAPANESE_DEFAULT = "ご連絡ありがとうございます。こちらのチャンネルでサポートいたします。"


def test_bot_texts_match_po_specified_english():
    assert bot_texts.TICKET_BUTTON_MESSAGE == "Need help? Click the button below to open a private support ticket."
    assert bot_texts.TICKET_BUTTON_LABEL == "Open a ticket"
    assert bot_texts.TICKET_READY_TEMPLATE.format(mention="#c") == "Your private channel is ready → #c"
    assert bot_texts.GUILD_ONLY == "This can only be used inside a server."
    assert bot_texts.GUILD_NOT_REGISTERED == "This server is not registered. Please contact the administrator."
    assert bot_texts.TICKET_NOT_CONFIGURED == "The ticket feature is not set up. Please contact the administrator."
    assert bot_texts.TICKET_CREATE_FAILED == "Failed to create the channel. Please contact the administrator."


def test_button_payload_keeps_custom_id_and_emoji():
    button = bot_texts.ticket_button_payload()["components"][0]["components"][0]
    assert button["custom_id"] == "ticket_open"
    assert button["emoji"] == {"name": "🎫"}
    assert button["label"] == bot_texts.TICKET_BUTTON_LABEL


def test_welcome_defaults_come_from_bot_texts():
    assert ticket_channel_creator._DEFAULT_WELCOME == bot_texts.DEFAULT_WELCOME_TEMPLATE
    assert DiscordTicketConfigResponse().welcome_template == bot_texts.DEFAULT_WELCOME_TEMPLATE
    update = DiscordTicketConfigUpdate(
        ticket_category_id="1" * 18, ticket_button_channel_id="2" * 18,
    )
    assert update.welcome_template == bot_texts.DEFAULT_WELCOME_TEMPLATE


def test_migration_uses_same_welcome_text_and_only_replaces_old_default():
    sql = MIGRATION.read_text(encoding="utf-8")
    escaped = bot_texts.DEFAULT_WELCOME_TEMPLATE.replace("'", "''")
    assert f"SET DEFAULT '{escaped}'" in sql
    assert f"SET welcome_template = '{escaped}'" in sql
    assert f"WHERE welcome_template = '{OLD_JAPANESE_DEFAULT}'" in sql
    statements = "\n".join(ln for ln in sql.splitlines() if not ln.lstrip().startswith("--")).upper()
    assert "DROP " not in statements and "DELETE " not in statements


def _interaction(guild=None, user=None) -> MagicMock:
    interaction = MagicMock()
    interaction.type = discord.InteractionType.component
    interaction.data = {"custom_id": "ticket_open"}
    interaction.response.defer = AsyncMock()
    interaction.followup.send = AsyncMock()
    interaction.guild = guild
    interaction.user = user
    return interaction


def _client() -> JarvisDiscordClient:
    client = JarvisDiscordClient(database_url="postgresql://unused")
    client._db_factory = MagicMock()
    return client


def _member() -> MagicMock:
    return MagicMock(spec=discord.Member)


@pytest.mark.asyncio
async def test_outside_guild_reply_is_english():
    interaction = _interaction(guild=None, user=MagicMock())
    await _client().on_interaction(interaction)
    interaction.followup.send.assert_awaited_once_with(bot_texts.GUILD_ONLY, ephemeral=True)


@pytest.mark.asyncio
async def test_unregistered_guild_reply_is_english():
    client = _client()
    client._resolve_tenant_id = AsyncMock(return_value=None)
    interaction = _interaction(guild=SimpleNamespace(id=1), user=_member())
    await client.on_interaction(interaction)
    interaction.followup.send.assert_awaited_once_with(bot_texts.GUILD_NOT_REGISTERED, ephemeral=True)


def _session_factory() -> MagicMock:
    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=MagicMock())
    session_cm.__aexit__ = AsyncMock(return_value=False)
    return MagicMock(return_value=session_cm)


@pytest.mark.asyncio
async def test_missing_config_reply_is_english():
    client = _client()
    client._resolve_tenant_id = AsyncMock(return_value=1)
    client._db_factory = MagicMock(return_value=_session_factory())
    interaction = _interaction(guild=SimpleNamespace(id=1), user=_member())
    with patch.object(ticket_channel_creator, "get_ticket_config", new=AsyncMock(return_value=None)):
        await client.on_interaction(interaction)
    interaction.followup.send.assert_awaited_once_with(bot_texts.TICKET_NOT_CONFIGURED, ephemeral=True)


@pytest.mark.asyncio
@pytest.mark.parametrize("channel", [None, SimpleNamespace(mention="<#42>", id=42)])
async def test_create_failed_and_ready_replies_are_english(channel):
    client = _client()
    client._resolve_tenant_id = AsyncMock(return_value=1)
    client._db_factory = MagicMock(return_value=_session_factory())
    interaction = _interaction(guild=SimpleNamespace(id=1), user=_member())
    with patch.object(ticket_channel_creator, "get_ticket_config", new=AsyncMock(return_value={"x": 1})), \
         patch.object(ticket_channel_creator, "get_or_create_ticket_channel", new=AsyncMock(return_value=channel)):
        await client.on_interaction(interaction)
    expected = (
        bot_texts.TICKET_CREATE_FAILED
        if channel is None
        else bot_texts.TICKET_READY_TEMPLATE.format(mention="<#42>")
    )
    interaction.followup.send.assert_awaited_once_with(expected, ephemeral=True)


def test_channel_invite_message_is_english_and_keeps_channel_mention():
    message = bot_texts.channel_invite_message("Small", "123456789012345678")
    assert message == (
        "[Notice] Here is the dedicated channel for our small-volume customers.\n"
        "Check the channel below for the latest news and special offers \U0001F447\n"
        "<#123456789012345678>"
    )
    assert "large-volume" in bot_texts.channel_invite_message("Large", "1")
    assert bot_texts.channel_invite_message("Custom", "1").count("Custom") == 1


@pytest.mark.asyncio
async def test_channel_invite_endpoint_posts_bot_texts_message(monkeypatch):
    from app.routers import discord_channel_invite as invite

    posted: dict = {}
    response = MagicMock(status_code=200, text="")
    response.json.return_value = {"id": "m1"}
    http_client = AsyncMock()

    async def _post(url, headers=None, json=None):
        posted["url"], posted["json"] = url, json
        return response

    http_client.post = _post
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "Bot-token-test")

    def _mapping_result(mapping):
        result = MagicMock()
        result.mappings.return_value.first.return_value = mapping
        return result

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[
        _mapping_result({"estimated_scale": "Small", "discord_guild_channel_id": "222222222222222222"}),
        _mapping_result({"small_channel_id": "333333333333333333", "large_channel_id": None}),
    ])
    with patch.object(invite, "tenant_table_ref", return_value="tenant_001.leads"), \
         patch.object(invite, "record_audit_log", new=AsyncMock()), \
         patch.object(invite, "reset_tenant_context", new=AsyncMock()), \
         patch("app.routers.discord_channel_invite.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=http_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        await invite.send_channel_invite(
            lead_id=1, db=db, tenant_id=1, current_user=SimpleNamespace(id=9),
        )

    assert posted["json"] == {
        "content": bot_texts.channel_invite_message("Small", "333333333333333333")
    }
    assert posted["url"].endswith("/channels/222222222222222222/messages")
