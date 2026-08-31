"""Discord ticket channel inbound 保存ヘルパ。

チケット専用チャンネルの customer 投稿を meta_messages に保存し、
保存後に worker へ即時翻訳を enqueue する。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import set_tenant_context
from app.services.inbound_translation import enqueue_inbound_translation
from app.services.message_translator import infer_original_language

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TicketChannelLead:
    lead_id: int
    discord_user_id: str | None
    customer_name: str | None


def _schema(tenant_id: int) -> str:
    return f"tenant_{tenant_id:03d}"


def _extract_first_attachment(message: Any) -> tuple[str | None, str | None]:
    """Discord メッセージから最初の添付の URL と種別を取り出す。

    添付が無ければ (None, None)。
    種別は content_type の先頭語から image / video / audio / file に丸める。
    Meta 経路（webhook.py）の attachment_url / attachment_type と同じ意味で使う。
    """
    attachments = getattr(message, "attachments", None) or []
    if not attachments:
        return None, None
    first = attachments[0]
    url = getattr(first, "url", None)
    if not url:
        return None, None
    content_type = getattr(first, "content_type", None) or ""
    head = content_type.split("/")[0]
    if head in ("image", "video", "audio"):
        kind = head
    else:
        kind = "file"
    return str(url), kind


async def _lookup_ticket_channel_lead(
    db: AsyncSession,
    *,
    tenant_id: int,
    channel_id: str,
) -> TicketChannelLead | None:
    schema = _schema(tenant_id)
    try:
        result = await db.execute(
            text(f"""
                SELECT id, discord_user_id, customer_name
                  FROM {schema}.leads
                 WHERE tenant_id = :tenant_id
                   AND discord_guild_channel_id = :channel_id
                 LIMIT 1
            """),
            {"tenant_id": tenant_id, "channel_id": channel_id},
        )
    except ProgrammingError:
        raise
    row = result.first()
    if row is None:
        return None
    return TicketChannelLead(
        lead_id=int(row[0]),
        discord_user_id=str(row[1]) if row[1] is not None else None,
        customer_name=str(row[2]) if row[2] is not None else None,
    )


async def process_ticket_channel_message(
    db_factory: Callable[[], Any],
    *,
    tenant_id: int,
    message: Any,
) -> bool:
    """チケットチャンネルの guild メッセージを meta_messages に保存する。"""
    channel = getattr(message, "channel", None)
    guild = getattr(message, "guild", None)
    if guild is None or channel is None:
        return False

    channel_id = str(getattr(channel, "id", ""))
    if not channel_id:
        return False

    author = getattr(message, "author", None)
    author_id = str(getattr(author, "id", ""))
    author_name = (
        getattr(author, "display_name", None)
        or getattr(author, "name", None)
        or author_id
    )
    message_text = getattr(message, "content", "") or ""
    message_id = str(getattr(message, "id", ""))
    webhook_id = getattr(message, "webhook_id", None)
    received_at = getattr(message, "created_at", None)
    if received_at is None:
        received_at = datetime.now(timezone.utc)
    elif received_at.tzinfo is None:
        received_at = received_at.replace(tzinfo=timezone.utc)

    db_factory_result = db_factory()
    async with db_factory_result as db:
        await set_tenant_context(db, tenant_id)
        lead = await _lookup_ticket_channel_lead(
            db,
            tenant_id=tenant_id,
            channel_id=channel_id,
        )
        if lead is None:
            logger.warning(
                "[discord-gateway] ticket channel lead not found tenant=%s ch=%s msg=%s",
                tenant_id,
                channel_id,
                message_id,
            )
            return True

        if getattr(author, "bot", False) or webhook_id:
            logger.info(
                "[discord-gateway] ticket channel skip bot/webhook tenant=%s lead=%s msg=%s",
                tenant_id,
                lead.lead_id,
                message_id,
            )
            return True

        inbound = bool(lead.discord_user_id) and author_id == str(lead.discord_user_id)
        if not inbound:
            logger.info(
                "[discord-gateway] ticket channel non-customer message ignored tenant=%s lead=%s msg=%s",
                tenant_id,
                lead.lead_id,
                message_id,
            )
            return True

        attachment_url, attachment_type = _extract_first_attachment(message)

        schema = _schema(tenant_id)
        insert_sql = text(f"""
            INSERT INTO {schema}.meta_messages
                (tenant_id, lead_id, platform, sender_id, sender_name,
                 message_text, direction, message_id, created_at, original_language,
                 attachment_url, attachment_type)
            VALUES
                (:tenant_id, :lead_id, 'discord', :sender_id, :sender_name,
                 :message_text, 'inbound', :message_id, :created_at, :original_language,
                 :attachment_url, :attachment_type)
            ON CONFLICT (message_id) WHERE message_id IS NOT NULL
            DO NOTHING
            RETURNING id
        """)
        insert_params = {
            "tenant_id": tenant_id,
            "lead_id": lead.lead_id,
            "sender_id": author_id,
            "sender_name": author_name,
            "message_text": message_text,
            "message_id": message_id,
            "created_at": received_at,
            "original_language": infer_original_language(message_text),
            "attachment_url": attachment_url,
            "attachment_type": attachment_type,
        }

        result = await db.execute(insert_sql, insert_params)
        inserted_row = result.first()
        await db.commit()

        if inserted_row is None:
            logger.debug(
                "[discord-gateway] ticket channel duplicate tenant=%s lead=%s msg=%s",
                tenant_id,
                lead.lead_id,
                message_id,
            )
            return True

        if message_text.strip():
            enqueue_inbound_translation(
                "meta_messages",
                message_id,
                message_text,
                tenant_id=tenant_id,
            )

    return True
