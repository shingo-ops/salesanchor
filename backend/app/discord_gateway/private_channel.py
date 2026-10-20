"""本人だけが見られる部屋を作る共通の部品（顧客用チケットと閲覧者の受付が使う）。

ticket_channel_creator.py から切り出した。ログの文字列は切り出し前と同じ
（`tenant=%d` の部分だけ log_context に置き換わる）。
"""
from __future__ import annotations

import logging
from typing import Any

import discord

logger = logging.getLogger(__name__)


def _bot_permission_overwrites(guild: discord.Guild) -> dict[Any, discord.PermissionOverwrite]:
    """gateway bot に必要な可視性を付与する。

    welcome メッセージ送信と受信箱への後続投稿を安定させるため、
    read_message_history / send_messages も付与する。
    """
    bot_member = getattr(guild, "me", None)
    if bot_member is None:
        logger.warning("[ticket] guild.me unavailable; bot overwrite skipped")
        return {}
    return {
        bot_member: discord.PermissionOverwrite(
            view_channel=True,
            read_message_history=True,
            send_messages=True,
        ),
    }


def resolve_category(
    guild: discord.Guild, category_id: int, log_context: str
) -> discord.CategoryChannel | None:
    """カテゴリを取得する。無い・カテゴリでないときはログを出して None。"""
    category = guild.get_channel(category_id)
    if not isinstance(category, discord.CategoryChannel):
        logger.error(
            "[ticket] category not found or not a CategoryChannel: %s %s",
            category_id,
            log_context,
        )
        return None
    return category


async def create_private_text_channel(
    guild: discord.Guild,
    category: discord.CategoryChannel,
    member: discord.Member,
    staff_role_id: str | None,
    name: str,
    reason: str,
    log_context: str,
    topic: str | None = None,
    log_name: str | None = None,
) -> discord.TextChannel | None:
    """本人・スタッフのロール・bot だけが見られるテキスト部屋を作る。失敗時は None。"""
    overwrites: dict[Any, discord.PermissionOverwrite] = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        member: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
        ),
    }
    overwrites.update(_bot_permission_overwrites(guild))
    if staff_role_id:
        staff_role = guild.get_role(int(staff_role_id))
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
            )
        else:
            logger.warning(
                "[ticket] staff_role_id=%s not found in guild %s",
                staff_role_id,
                log_context,
            )

    create_kwargs: dict[str, Any] = {
        "name": name,
        "category": category,
        "overwrites": overwrites,
        "reason": reason,
    }
    if topic is not None:
        create_kwargs["topic"] = topic
    try:
        new_channel = await guild.create_text_channel(**create_kwargs)
    except discord.Forbidden:
        logger.error(
            "[ticket] Forbidden: cannot create channel in category=%s %s",
            category.id,
            log_context,
        )
        return None
    except discord.HTTPException as exc:
        if log_name is not None:
            # 名前（LINE 名）が文面に入る可能性があるので status だけ出す
            logger.error(
                "[ticket] HTTPException creating channel %s: status=%s",
                log_context,
                exc.status,
            )
        else:
            logger.error(
                "[ticket] HTTPException creating channel %s: %s",
                log_context,
                exc,
            )
        return None

    logger.info(
        "[ticket] created channel=%s (%s) for user=%s %s",
        new_channel.id,
        log_name if log_name is not None else name,
        member.id,
        log_context,
    )
    return new_channel
