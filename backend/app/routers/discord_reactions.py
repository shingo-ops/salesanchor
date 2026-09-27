"""Discord リアクション送受信 REST API (discord-reaction テーマ).

受信箱から Discord リアクションを送信・取消する API と、
カスタム絵文字一覧を取得する API を提供する。

API:
  POST   /api/v1/leads/{lead_id}/messages/{message_id}/reactions — リアクション送信
  DELETE /api/v1/leads/{lead_id}/messages/{message_id}/reactions/{emoji} — リアクション取消
  GET    /api/v1/discord/guilds/{guild_id}/emojis — カスタム絵文字一覧

権限: messaging.view（送信・取消・取得すべて）
"""
from __future__ import annotations

import logging
import os
import urllib.parse
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import (
    get_current_tenant,
    get_current_user,
    require_permission,
    reset_tenant_context,
    tenant_table_ref,
)
from app.database import get_db
from app.models import User
from app.services import sse_pubsub

logger = logging.getLogger(__name__)
router = APIRouter()

_DISCORD_API_BASE = "https://discord.com/api/v10"


def _get_bot_token() -> str | None:
    """共通 Bot Token を取得する (ADR-146 B方式)."""
    return os.environ.get("DISCORD_BOT_TOKEN") or None


def _schema(tenant_id: int) -> str:
    return f"tenant_{tenant_id:03d}"


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class ReactionRequest(BaseModel):
    emoji_name: str = Field(..., min_length=1, max_length=100)
    emoji_id: Optional[str] = Field(default=None, pattern=r"^\d{17,20}$")


class ReactionResponse(BaseModel):
    success: bool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _encode_emoji(emoji_name: str, emoji_id: Optional[str]) -> str:
    """Discord API の emoji パラメータ用文字列を組み立てる。

    Unicode: URL encode した絵文字名（例: "%F0%9F%91%8D"）
    Custom:  "name:id" 形式（例: "custom_name:1234567890"）
    """
    if emoji_id:
        return urllib.parse.quote(f"{emoji_name}:{emoji_id}", safe=":")
    return urllib.parse.quote(emoji_name, safe="")


async def _get_discord_channel_id_for_lead(
    db: AsyncSession,
    tenant_id: int,
    lead_id: int,
) -> str | None:
    """lead_id から Discord チャンネル ID を取得する。"""
    leads_t = tenant_table_ref(db, tenant_id, "leads")
    result = await db.execute(
        text(
            f"SELECT discord_guild_channel_id FROM {leads_t}"
            " WHERE id = :id AND tenant_id = :tenant_id LIMIT 1"
        ),
        {"id": lead_id, "tenant_id": tenant_id},
    )
    row = result.first()
    return str(row[0]) if row and row[0] else None


async def _get_discord_message_id(
    db: AsyncSession,
    tenant_id: int,
    meta_message_id: int,
) -> str | None:
    """meta_messages.id から Discord message_id を取得する。"""
    schema = _schema(tenant_id)
    result = await db.execute(
        text(
            f"SELECT message_id FROM {schema}.meta_messages"
            " WHERE id = :id AND tenant_id = :tenant_id LIMIT 1"
        ),
        {"id": meta_message_id, "tenant_id": tenant_id},
    )
    row = result.first()
    return str(row[0]) if row and row[0] else None


# ---------------------------------------------------------------------------
# POST /leads/{lead_id}/messages/{message_id}/reactions
# ---------------------------------------------------------------------------


@router.post(
    "/leads/{lead_id}/messages/{message_id}/reactions",
    response_model=ReactionResponse,
    dependencies=[Depends(require_permission("messaging.view"))],
)
async def send_reaction(
    lead_id: int,
    message_id: int,
    data: ReactionRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
) -> ReactionResponse:
    """受信箱から Discord メッセージにリアクションを送信する（Bot 名義）。"""
    bot_token = _get_bot_token()
    if not bot_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Bot token is not configured. Set DISCORD_BOT_TOKEN.",
        )

    # meta_message_id → discord message_id
    discord_message_id = await _get_discord_message_id(db, tenant_id, message_id)
    if discord_message_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found.",
        )

    # lead → discord channel_id
    discord_channel_id = await _get_discord_channel_id_for_lead(db, tenant_id, lead_id)
    if discord_channel_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Discord channel not found for this lead.",
        )

    encoded_emoji = _encode_emoji(data.emoji_name, data.emoji_id)

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.put(
            f"{_DISCORD_API_BASE}/channels/{discord_channel_id}"
            f"/messages/{discord_message_id}/reactions/{encoded_emoji}/@me",
            headers={"Authorization": f"Bot {bot_token}"},
        )

    if resp.status_code not in (200, 204):
        logger.error(
            "[discord-reaction] send failed tenant=%d lead=%d msg=%d status=%d body=%s",
            tenant_id, lead_id, message_id, resp.status_code, resp.text[:200],
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Discord API error ({resp.status_code}): failed to add reaction.",
        )

    schema = _schema(tenant_id)
    await db.execute(
        text(f"""
            INSERT INTO {schema}.meta_message_reactions
                (tenant_id, meta_message_id, emoji_name, emoji_id,
                 emoji_animated, reactor_discord_user_id,
                 reactor_display_name, is_bot_reaction)
            SELECT :tenant_id, :meta_message_id, :emoji_name, :emoji_id,
                   false, bot.discord_bot_user_id, 'Bot', true
            FROM public.tenant_discord_config bot
            WHERE bot.tenant_id = :tenant_id
            ON CONFLICT ON CONSTRAINT uq_reaction_per_user_emoji DO NOTHING
        """),
        {
            "tenant_id": tenant_id,
            "meta_message_id": message_id,
            "emoji_name": data.emoji_name,
            "emoji_id": data.emoji_id,
        },
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)

    await sse_pubsub.publish_inbox_update(tenant_id)

    logger.info(
        "[discord-reaction] sent tenant=%d lead=%d msg=%d emoji=%s",
        tenant_id, lead_id, message_id, data.emoji_name,
    )
    return ReactionResponse(success=True)


# ---------------------------------------------------------------------------
# DELETE /leads/{lead_id}/messages/{message_id}/reactions/{emoji}
# ---------------------------------------------------------------------------


@router.delete(
    "/leads/{lead_id}/messages/{message_id}/reactions/{emoji}",
    response_model=ReactionResponse,
    dependencies=[Depends(require_permission("messaging.view"))],
)
async def delete_reaction(
    lead_id: int,
    message_id: int,
    emoji: str,
    emoji_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
) -> ReactionResponse:
    """受信箱から Discord メッセージのリアクションを取り消す（Bot 名義）。"""
    bot_token = _get_bot_token()
    if not bot_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Bot token is not configured. Set DISCORD_BOT_TOKEN.",
        )

    discord_message_id = await _get_discord_message_id(db, tenant_id, message_id)
    if discord_message_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found.",
        )

    discord_channel_id = await _get_discord_channel_id_for_lead(db, tenant_id, lead_id)
    if discord_channel_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Discord channel not found for this lead.",
        )

    encoded_emoji = _encode_emoji(emoji, emoji_id)

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.delete(
            f"{_DISCORD_API_BASE}/channels/{discord_channel_id}"
            f"/messages/{discord_message_id}/reactions/{encoded_emoji}/@me",
            headers={"Authorization": f"Bot {bot_token}"},
        )

    if resp.status_code not in (200, 204):
        logger.error(
            "[discord-reaction] delete failed tenant=%d lead=%d msg=%d status=%d body=%s",
            tenant_id, lead_id, message_id, resp.status_code, resp.text[:200],
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Discord API error ({resp.status_code}): failed to remove reaction.",
        )

    schema = _schema(tenant_id)
    if emoji_id:
        await db.execute(
            text(f"""
                DELETE FROM {schema}.meta_message_reactions
                WHERE tenant_id = :tenant_id
                  AND meta_message_id = :meta_message_id
                  AND emoji_name = :emoji_name
                  AND emoji_id = :emoji_id
                  AND is_bot_reaction = true
            """),
            {
                "tenant_id": tenant_id,
                "meta_message_id": message_id,
                "emoji_name": emoji,
                "emoji_id": emoji_id,
            },
        )
    else:
        await db.execute(
            text(f"""
                DELETE FROM {schema}.meta_message_reactions
                WHERE tenant_id = :tenant_id
                  AND meta_message_id = :meta_message_id
                  AND emoji_name = :emoji_name
                  AND emoji_id IS NULL
                  AND is_bot_reaction = true
            """),
            {
                "tenant_id": tenant_id,
                "meta_message_id": message_id,
                "emoji_name": emoji,
            },
        )
    await db.commit()
    await reset_tenant_context(db, tenant_id)

    await sse_pubsub.publish_inbox_update(tenant_id)

    logger.info(
        "[discord-reaction] deleted tenant=%d lead=%d msg=%d emoji=%s",
        tenant_id, lead_id, message_id, emoji,
    )
    return ReactionResponse(success=True)


# ---------------------------------------------------------------------------
# GET /discord/guilds/{guild_id}/emojis
# ---------------------------------------------------------------------------


@router.get(
    "/discord/guilds/{guild_id}/emojis",
    dependencies=[Depends(require_permission("messaging.view"))],
)
async def list_guild_emojis(
    guild_id: str,
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    """Discord サーバーのカスタム絵文字一覧を取得する（絵文字パレット用）。"""
    bot_token = _get_bot_token()
    if not bot_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Bot token is not configured. Set DISCORD_BOT_TOKEN.",
        )

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{_DISCORD_API_BASE}/guilds/{guild_id}/emojis",
            headers={"Authorization": f"Bot {bot_token}"},
        )

    if resp.status_code != 200:
        logger.error(
            "[discord-reaction] list_emojis failed tenant=%d guild=%s status=%d body=%s",
            tenant_id, guild_id, resp.status_code, resp.text[:200],
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Discord API error ({resp.status_code}): failed to fetch emojis.",
        )

    return resp.json()
