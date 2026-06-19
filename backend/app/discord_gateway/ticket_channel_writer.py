"""Discord ticket channel 受信 → 受信箱 DB 書き込みヘルパ。

チケット専用チャンネルのメッセージを meta_messages に保存し、
必要なら保存直後に翻訳を走らせる。

DM 受信経路(dm_writer.py) とは独立した ticket channel 専用経路。
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
from app.services.message_translator import translate_inbound

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TicketChannelLead:
    """チケットチャンネルに紐づく lead 情報。"""

    lead_id: int
    discord_user_id: str | None
    customer_name: str | None


def _schema(tenant_id: int) -> str:
    return f"tenant_{tenant_id:03d}"


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
    """チケットチャンネルの guild メッセージを meta_messages に保存する。

    Returns:
        True  = チケットチャンネルとして処理した（INSERT の成否を問わない）
        False = チケットチャンネルではない（通常の guild 解析へ委譲してよい）
    """
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
    async with db_factory_result as db:  # type: ignore[misc]
        await set_tenant_context(db, tenant_id)
        lead = await _lookup_ticket_channel_lead(
            db,
            tenant_id=tenant_id,
            channel_id=channel_id,
        )
        if lead is None:
            return False

        schema = _schema(tenant_id)
        if getattr(author, "bot", False) or webhook_id:
            logger.info(
                "[discord-gateway] ticket channel skip bot/webhook tenant=%s lead=%s msg=%s",
                tenant_id,
                lead.lead_id,
                message_id,
            )
            return True

        inbound = bool(lead.discord_user_id) and author_id == str(lead.discord_user_id)
        if inbound:
            insert_sql = text(f"""
                INSERT INTO {schema}.meta_messages
                    (tenant_id, lead_id, platform, sender_id, sender_name,
                     message_text, direction, message_id, created_at)
                VALUES
                    (:tenant_id, :lead_id, 'discord', :sender_id, :sender_name,
                     :message_text, 'inbound', :message_id, :created_at)
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
            }
        else:
            insert_sql = text(f"""
                INSERT INTO {schema}.meta_messages
                    (tenant_id, lead_id, platform, sender_id, sender_name,
                     message_text, direction, message_id, recipient_id,
                     sent_by_staff_id, created_at)
                VALUES
                    (:tenant_id, :lead_id, 'discord', :sender_id, :sender_name,
                     :message_text, 'outbound', :message_id, :recipient_id,
                     :sent_by_staff_id, :created_at)
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
                "recipient_id": lead.discord_user_id,
                "sent_by_staff_id": None,
                "created_at": received_at,
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

        if inbound and message_text.strip():
            try:
                await translate_inbound(
                    db=db,
                    tenant_id=tenant_id,
                    table_ref=f"{schema}.message_translations",
                    message_id=message_id,
                    message_text=message_text,
                )
            except Exception:  # noqa: BLE001
                logger.warning(
                    "[discord-gateway] ticket channel translation failed tenant=%s lead=%s msg=%s",
                    tenant_id,
                    lead.lead_id,
                    message_id,
                    exc_info=True,
                )

        try:
            from app.services.sse_pubsub import publish_inbox_update

            await publish_inbox_update(tenant_id)
        except Exception:  # noqa: BLE001
            logger.debug("[discord-gateway] SSE publish skipped for ticket channel")

    return True
