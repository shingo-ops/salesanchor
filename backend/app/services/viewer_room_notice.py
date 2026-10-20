"""閲覧者の状態を変えた直後に、その人の Discord の部屋へお知らせを送る（ADR-1019 段10 便2）。

呼び出し側は、自分の書き込みを commit した後に呼ぶこと（Discord を待つ間 DB を開けない）。
送れなくても操作は成功のまま。ログにはチャンネル ID と結果だけを出す（本文・名簿の中身は出さない）。
"""
from __future__ import annotations

import logging
import os
from typing import Literal

from app.discord_gateway import viewer_bot_texts
from app.services.discord_rest import discord_api_request

logger = logging.getLogger(__name__)

RoomNotice = Literal["sent", "failed", "no_room"]


async def send_room_notice(channel_id: str, text: str) -> bool:
    """部屋に text を1通送る。送れたら True、何があっても例外は外へ出さず False。"""
    try:
        bot_token = os.environ.get("DISCORD_BOT_TOKEN")
        if not bot_token:
            logger.warning("viewer room notice: channel=%s result=failed reason=no_token", channel_id)
            return False
        await discord_api_request(
            method="POST",
            path=f"/channels/{channel_id}/messages",
            bot_token=bot_token,
            json={"content": text, "allowed_mentions": {"parse": []}},
            expected_statuses=(200, 201),
            max_retries=1,
        )
    except Exception as exc:
        logger.warning(
            "viewer room notice: channel=%s result=failed kind=%s", channel_id, type(exc).__name__
        )
        return False
    logger.info("viewer room notice: channel=%s result=sent", channel_id)
    return True


def notice_text(action: str, item: dict) -> str | None:
    """操作ごとのお知らせの文。unsuspend など文面が無い操作は None。"""
    if action == "extend":
        expires = item.get("trial_expires_at")
        if expires is None:
            return None
        return viewer_bot_texts.NOTICE_EXTENDED.format(
            until_date=viewer_bot_texts.format_jst_date(expires)
        )
    if action == "activate":
        return viewer_bot_texts.NOTICE_ACTIVATED
    if action == "suspend":
        return viewer_bot_texts.NOTICE_SUSPENDED
    return None


async def notify_status_change(action: str, item: dict) -> tuple[RoomNotice | None, str | None]:
    """状態変更の後に部屋へ送る。(room_notice, room_notice_text) を返す。文面なしは (None, None)。"""
    text = notice_text(action, item)
    if text is None:
        return None, None
    channel_id = item.get("discord_channel_id")
    if not channel_id:
        return "no_room", text
    if await send_room_notice(str(channel_id), text):
        return "sent", text
    return "failed", text
