"""閲覧者の状態を変えた直後に、その人の Discord の部屋へお知らせを送る（ADR-1019 段10 便2）。

文はテンプレート（DB）から作る。DB を読むのは commit の前（状態変更と同じトランザクション。prepare_notice）、
送るのは commit の後（notify_prepared。Discord を待つ間 DB を開けない）。commit の後に DB を読まない。
テンプレートが無い・検査に通らないときも状態は変え、送らず "no_template" を返す。
送れなくても操作は成功のまま。ログにはチャンネル ID と結果だけを出す（本文・名簿の中身は出さない）。
"""
from __future__ import annotations

import logging
import os
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.discord_gateway import viewer_bot_texts
from app.services import viewer_message_templates as vmt
from app.services.discord_rest import discord_api_request

logger = logging.getLogger(__name__)

RoomNotice = Literal["sent", "failed", "no_room", "no_template"]


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


async def prepare_notice(db: AsyncSession, action: str, item: dict) -> tuple[bool, str | None]:
    """commit の前に呼ぶ。(お知らせの対象か, 文) を返す。

    対象でない操作（unsuspend、期限なしの延長）は (False, None)。対象でテンプレートが使えないときは (True, None)。
    """
    if action == "extend":
        expires = item.get("trial_expires_at")
        if expires is None:
            return False, None
        text = await vmt.load_rendered(
            db, "notice_extended", until_date=viewer_bot_texts.format_jst_date(expires)
        )
        return True, text
    if action == "activate":
        return True, await vmt.load_rendered(db, "notice_activated")
    if action == "suspend":
        return True, await vmt.load_rendered(db, "notice_suspended")
    return False, None


async def notify_prepared(
    prepared: tuple[bool, str | None], item: dict
) -> tuple[RoomNotice | None, str | None]:
    """commit の後に呼ぶ。prepare_notice の結果を部屋へ送り、(room_notice, room_notice_text) を返す。"""
    applicable, text = prepared
    if not applicable:
        return None, None
    if text is None:
        return "no_template", None
    channel_id = item.get("discord_channel_id")
    if not channel_id:
        return "no_room", text
    if await send_room_notice(str(channel_id), text):
        return "sent", text
    return "failed", text
