"""お客さんが自分の部屋の外に書いたとき、担当者へ通知先（Discord Webhook）で知らせる。

お客さんへは何も送らない。本文・添付・Discord の id は通知にもログにも載せない。
重複の抑え: Redis キー discord_outside_ticket_notice:{tenant}:{channel}:{author} を SET NX EX 1800。
Redis が使えないときは送らない（二重に送るより送らない方を選ぶ）。
"""
from __future__ import annotations

import logging
from typing import Any

import discord
from sqlalchemy import text

from app.cache import get_redis

logger = logging.getLogger(__name__)

EVENT_TYPE = "discord_outside_ticket_post"
NOTICE_TITLE = "部屋の外の書き込み（Discord）"
DEDUP_TTL_SECONDS = 1800
_KEY_PREFIX = "discord_outside_ticket_notice:"
_ALLOWED_TYPES = (discord.MessageType.default, discord.MessageType.reply)


def _log(tenant_id: int, result: str) -> None:
    logger.info("[discord-gateway] outside-ticket notice tenant=%s result=%s", tenant_id, result)


async def _is_staff(db: Any, tenant_id: int, message: Any) -> bool:
    author = message.author
    author_id = str(getattr(author, "id", ""))
    # (a) staff 表
    row = (
        await db.execute(
            text("SELECT 1 FROM staff WHERE tenant_id = :tid AND discord_user_id = :uid LIMIT 1"),
            {"tid": tenant_id, "uid": author_id},
        )
    ).first()
    if row is not None:
        return True
    # (b) 担当者の役割
    roles = getattr(author, "roles", None)
    if roles:
        cfg = (
            await db.execute(
                text(
                    "SELECT staff_role_id FROM public.tenant_discord_ticket_config "
                    "WHERE tenant_id = :tid"
                ),
                {"tid": tenant_id},
            )
        ).first()
        staff_role_id = cfg[0] if cfg else None
        if staff_role_id and str(staff_role_id) in {str(getattr(r, "id", "")) for r in roles}:
            return True
    # (c) 管理者
    perms = getattr(author, "guild_permissions", None)
    return bool(getattr(perms, "administrator", False))


async def _parent_is_ticket_room(db: Any, tenant_id: int, channel: Any) -> bool:
    parent_id = getattr(channel, "parent_id", None)
    if not parent_id:
        return False
    row = (
        await db.execute(
            text(
                "SELECT 1 FROM leads WHERE tenant_id = :tid "
                "AND discord_guild_channel_id = :cid LIMIT 1"
            ),
            {"tid": tenant_id, "cid": str(parent_id)},
        )
    ).first()
    return row is not None


async def notify_outside_ticket_post(db: Any, *, tenant_id: int, message: Any) -> bool:
    """送ったら True。例外は外に出さない。"""
    try:
        if getattr(message, "type", None) not in _ALLOWED_TYPES:
            _log(tenant_id, "skipped_message_type")
            return False
        author = message.author
        if getattr(author, "bot", False) or getattr(message, "webhook_id", None):
            _log(tenant_id, "skipped_bot")
            return False
        if await _is_staff(db, tenant_id, message):
            _log(tenant_id, "skipped_staff")
            return False
        channel = message.channel
        if await _parent_is_ticket_room(db, tenant_id, channel):
            _log(tenant_id, "skipped_thread_in_ticket_room")
            return False
        redis = get_redis()
        if redis is None:
            _log(tenant_id, "skipped_no_redis")
            return False
        key = f"{_KEY_PREFIX}{tenant_id}:{getattr(channel, 'id', '')}:{getattr(author, 'id', '')}"
        if not await redis.set(key, "1", nx=True, ex=DEDUP_TTL_SECONDS):
            _log(tenant_id, "skipped_dedup")
            return False
        # 循環 import を避けるため遅延 import
        from app.routers.notifications import send_discord_notification

        name = getattr(author, "display_name", None) or getattr(author, "name", None) or "-"
        ch_name = getattr(channel, "name", None) or "-"
        body = f"書いた人: {name}\nチャンネル: #{ch_name}\n{message.jump_url}"
        # 呼んだあとはこのセッションで続きの処理をしない（commit と reset_tenant_context が走る）
        await send_discord_notification(db, tenant_id, EVENT_TYPE, NOTICE_TITLE, body)
        _log(tenant_id, "sent")
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[discord-gateway] outside-ticket notice failed tenant=%s err=%s",
            tenant_id,
            type(exc).__name__,
        )
        return False
