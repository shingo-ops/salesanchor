"""お客さんが自分の部屋の外に書いたとき、担当者へ通知先（Discord Webhook）で知らせる。

お客さんへは何も送らない。同じ関門を通った回に、宛先（担当者＋管理者）の名前を呼び、アプリ内の鈴（user_notices）も作る。
本文・添付・Discord の id は通知にもログにも載せない。
重複の抑え: Redis キー discord_outside_ticket_notice:{tenant}:{channel}:{author} を SET NX EX 1800。
Redis が使えないときは送らない（二重に送るより送らない方を選ぶ）。
"""
from __future__ import annotations

import logging
from typing import Any

import discord
from sqlalchemy import text

from app.auth.dependencies import reset_tenant_context
from app.cache import get_redis
from app.services import user_notices

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


async def _recover_session(db: Any, tenant_id: int) -> None:
    """失敗した処理の後でセッションを使える状態に戻す（戻せなければ何もしない）。"""
    try:
        await db.rollback()
        await reset_tenant_context(db, tenant_id)
    except Exception:  # noqa: BLE001
        pass


async def _create_bell(
    db: Any, tenant_id: int, recipients: list[int], name: str, ch_name: str, link: str
) -> None:
    """知らせの行を宛先の人数分作り、commit の後に合図を出す。1 度だけ立て直して再試行する。"""
    if not recipients:
        return
    for attempt in (1, 2):
        try:
            await user_notices.insert_notices(
                db, tenant_id, recipients,
                kind=user_notices.KIND_OUTSIDE_TICKET_POST,
                actor_name=name, channel_name=ch_name, link_url=link,
            )
            await db.commit()
            await reset_tenant_context(db, tenant_id)  # ADR-072
            break
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "[discord-gateway] outside-ticket bell insert failed tenant=%s attempt=%s err=%s",
                tenant_id, attempt, type(exc).__name__,
            )
            await _recover_session(db, tenant_id)
    else:
        return
    try:
        await user_notices.signal_notices_changed(recipients)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[discord-gateway] outside-ticket bell signal failed tenant=%s err=%s",
            tenant_id, type(exc).__name__,
        )


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
        link = str(message.jump_url)
        body = f"書いた人: {name}\nチャンネル: #{ch_name}\n{link}"

        # 宛先（担当者＋管理者）と名前を呼ぶ Discord の id。決められなくても通知は今までどおり送る
        recipients: list[int] = []
        mention_ids: list[str] = []
        try:
            recipients = await user_notices.resolve_notice_recipients(
                db, tenant_id, str(getattr(author, "id", ""))
            )
            mention_ids = await user_notices.discord_ids_for_users(db, tenant_id, recipients)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "[discord-gateway] outside-ticket recipients failed tenant=%s err=%s",
                tenant_id,
                type(exc).__name__,
            )
            recipients, mention_ids = [], []
            await _recover_session(db, tenant_id)

        # Discord の送信（失敗は中で握る）。中で commit と reset_tenant_context が走る
        try:
            await send_discord_notification(
                db, tenant_id, EVENT_TYPE, NOTICE_TITLE, body,
                mention_user_ids=mention_ids or None,
            )
        except Exception as exc:  # noqa: BLE001  本物は中で握るが、握れなかった場合も鈴は作る
            logger.warning(
                "[discord-gateway] outside-ticket discord send failed tenant=%s err=%s",
                tenant_id,
                type(exc).__name__,
            )
            await _recover_session(db, tenant_id)
        _log(tenant_id, f"sent recipients={len(recipients)} mentions={len(mention_ids)}")

        # 鈴は Discord の成否と独立に作る。失敗しても外へ出さない
        await _create_bell(db, tenant_id, recipients, name, ch_name, link)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[discord-gateway] outside-ticket notice failed tenant=%s err=%s",
            tenant_id,
            type(exc).__name__,
        )
        return False
