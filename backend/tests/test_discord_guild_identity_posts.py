"""ボタン案内（auto-setup / deploy-button）をサーバー名義で投稿し、失敗時に Bot 名義へ戻すことのテスト。"""
from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.discord_gateway import bot_texts
from app.routers import discord_auto_setup, discord_ticket_config
from app.services.discord_guild_identity import GuildIdentity

_IDENTITY = GuildIdentity(name="My Shop", icon_url="https://cdn.discordapp.com/icons/1/abc.png")


def _setup_patches(identity, sent_id):
    return (
        patch.object(discord_auto_setup, "fetch_guild_identity", new=AsyncMock(return_value=identity)),
        patch.object(discord_auto_setup, "try_send_as_identity", new=AsyncMock(return_value=sent_id)),
    )


@pytest.mark.asyncio
async def test_auto_setup_button_posts_as_guild_identity_with_components():
    fetch_p, send_p = _setup_patches(_IDENTITY, "WH-MSG")
    bot_post = AsyncMock()
    with fetch_p, send_p as send, patch.object(discord_auto_setup, "discord_api_request", new=bot_post):
        step = await discord_auto_setup._post_ticket_button_step(
            step_name="button", ticket_ch_id="CH-1", bot_token="t", db=MagicMock(), tenant_id=4, guild_id="1",
        )

    assert (step.status, step.discord_id) == ("posted", "WH-MSG")
    kwargs = send.await_args.kwargs
    assert kwargs["identity"] == _IDENTITY
    assert kwargs["channel_id"] == "CH-1"
    assert kwargs["components"] == bot_texts.ticket_button_payload()["components"]
    bot_post.assert_not_awaited()


@pytest.mark.asyncio
async def test_auto_setup_button_falls_back_to_bot_post_when_identity_send_fails():
    fetch_p, send_p = _setup_patches(_IDENTITY, None)
    bot_post = AsyncMock(return_value={"id": "BOT-MSG"})
    with fetch_p, send_p, patch.object(discord_auto_setup, "discord_api_request", new=bot_post):
        step = await discord_auto_setup._post_ticket_button_step(
            step_name="button", ticket_ch_id="CH-1", bot_token="t", db=MagicMock(), tenant_id=4, guild_id="1",
        )

    assert (step.status, step.discord_id) == ("posted", "BOT-MSG")
    assert bot_post.await_args.kwargs["json"] == bot_texts.ticket_button_payload()


def _deploy_db(guild_id):
    db = AsyncMock()
    result = MagicMock()
    result.first.return_value = ("CH-9", guild_id)
    db.execute.return_value = result
    return db


async def _deploy(db):
    user = MagicMock(id=3)
    with patch.object(discord_ticket_config, "record_audit_log", new=AsyncMock()), \
         patch.object(discord_ticket_config, "reset_tenant_context", new=AsyncMock()):
        return await discord_ticket_config.deploy_ticket_button(db=db, tenant_id=4, current_user=user)


@pytest.mark.asyncio
async def test_deploy_button_posts_as_guild_identity(monkeypatch):
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "tok")
    send = AsyncMock(return_value="WH-MSG")
    with patch.object(discord_ticket_config, "fetch_guild_identity", new=AsyncMock(return_value=_IDENTITY)), \
         patch.object(discord_ticket_config, "try_send_as_identity", new=send), \
         patch.object(discord_ticket_config.httpx, "AsyncClient") as client:
        resp = await _deploy(_deploy_db("1"))

    assert (resp.message_id, resp.channel_id) == ("WH-MSG", "CH-9")
    assert send.await_args.kwargs["identity"] == _IDENTITY
    assert send.await_args.kwargs["components"] == bot_texts.ticket_button_payload()["components"]
    client.assert_not_called()


@pytest.mark.asyncio
async def test_deploy_button_falls_back_to_bot_post(monkeypatch):
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "tok")
    http_resp = MagicMock(status_code=200)
    http_resp.json.return_value = {"id": "BOT-MSG"}
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.post = AsyncMock(return_value=http_resp)
    with patch.object(discord_ticket_config, "fetch_guild_identity", new=AsyncMock(return_value=None)), \
         patch.object(discord_ticket_config, "try_send_as_identity", new=AsyncMock(return_value=None)), \
         patch.object(discord_ticket_config.httpx, "AsyncClient", return_value=client):
        resp = await _deploy(_deploy_db("1"))

    assert resp.message_id == "BOT-MSG"
    assert client.post.await_args.kwargs["json"] == bot_texts.ticket_button_payload()
