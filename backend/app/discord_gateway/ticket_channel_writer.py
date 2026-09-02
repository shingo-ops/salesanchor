"""Discord ticket channel inbound 保存ヘルパ。

チケット専用チャンネルの customer 投稿を meta_messages に保存し、
保存後に worker へ即時翻訳を enqueue する。
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import httpx
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


_ATTACHMENT_ROOT = os.environ.get("ATTACHMENT_ROOT", "/data/attachments")
_DOWNLOAD_TIMEOUT_SEC = 30.0


async def _save_attachment_to_disk(
    *,
    tenant_id: int,
    lead_id: int,
    message_id: str,
    url: str,
    filename: str | None,
) -> tuple[str | None, int | None, str | None]:
    """添付の実体をダウンロードして自社ディスクへ保存する。

    Discord CDN の署名付きURLは約24時間で失効し、元投稿が削除されると
    実体も消えるため、受信時に自社側へ保存する（attachment-storage テーマ）。

    戻り値は (相対パス, バイト数, content_type)。
    失敗した場合は (None, None, None) を返し、受信処理は止めない。
    画像が取れなくても本文は受信箱に残すべきであるため。
    """
    schema = _schema(tenant_id)
    ext = ""
    if filename and "." in filename:
        ext = "." + filename.rsplit(".", 1)[1][:10]
    rel_path = f"{schema}/lead_{lead_id}/{message_id}{ext}"
    abs_path = Path(_ATTACHMENT_ROOT) / rel_path

    try:
        async with httpx.AsyncClient(timeout=_DOWNLOAD_TIMEOUT_SEC) as client:
            response = await client.get(url)
        if response.status_code != 200:
            logger.warning(
                "[attachment-save] ダウンロード失敗 tenant=%s lead=%s msg=%s status=%s",
                tenant_id, lead_id, message_id, response.status_code,
            )
            return None, None, None

        abs_path.parent.mkdir(parents=True, exist_ok=True)
        abs_path.write_bytes(response.content)
        content_type = response.headers.get("content-type")
        logger.info(
            "[attachment-save] 保存完了 tenant=%s lead=%s msg=%s bytes=%d path=%s",
            tenant_id, lead_id, message_id, len(response.content), rel_path,
        )
        return rel_path, len(response.content), content_type
    except Exception:
        logger.warning(
            "[attachment-save] 保存失敗 tenant=%s lead=%s msg=%s",
            tenant_id, lead_id, message_id, exc_info=True,
        )
        return None, None, None


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

        if attachment_url:
            original_filename = None
            attachments = getattr(message, "attachments", None) or []
            if attachments:
                original_filename = getattr(attachments[0], "filename", None)

            saved_path, saved_size, saved_type = await _save_attachment_to_disk(
                tenant_id=tenant_id,
                lead_id=lead.lead_id,
                message_id=message_id,
                url=attachment_url,
                filename=original_filename,
            )
            if saved_path is not None and saved_size is not None:
                try:
                    result_la = await db.execute(
                        text(f"""
                            INSERT INTO {schema}.lead_attachments
                                (tenant_id, lead_id, message_id, platform,
                                 file_path, file_size, content_type, original_filename)
                            VALUES
                                (:tenant_id, :lead_id, :message_id, 'discord',
                                 :file_path, :file_size, :content_type, :original_filename)
                            ON CONFLICT (message_id) DO NOTHING
                                RETURNING id
                        """),
                        {
                            "tenant_id": tenant_id,
                            "lead_id": lead.lead_id,
                            "message_id": message_id,
                            "file_path": saved_path,
                            "file_size": saved_size,
                            "content_type": saved_type,
                            "original_filename": original_filename,
                        },
                    )
                    attachment_row = result_la.first()
                    if attachment_row is not None:
                        attachment_id = int(attachment_row[0])
                        serve_url = (
                            f"/api/v1/leads/{lead.lead_id}"
                            f"/attachments/{attachment_id}"
                        )
                        await db.execute(
                            text(f"""
                                UPDATE {schema}.meta_messages
                                   SET attachment_url = :url
                                 WHERE message_id = :message_id
                                   AND tenant_id = :tenant_id
                            """),
                            {
                                "url": serve_url,
                                "message_id": message_id,
                                "tenant_id": tenant_id,
                            },
                        )
                        logger.info(
                            "[attachment-save] 配信URL設定 tenant=%s lead=%s id=%s url=%s",
                            tenant_id, lead.lead_id, attachment_id, serve_url,
                        )
                    await db.commit()
                except Exception:
                    logger.warning(
                        "[attachment-save] 台帳記録失敗 tenant=%s lead=%s msg=%s",
                        tenant_id, lead.lead_id, message_id, exc_info=True,
                    )

        if message_text.strip():
            enqueue_inbound_translation(
                "meta_messages",
                message_id,
                message_text,
                tenant_id=tenant_id,
            )

    return True
