"""閲覧ページの申込で返す、その人専用の Discord 招待リンクを作る（ADR-1019 D5・段4b）。

受付の部屋（viewer_discord_config.reception_channel_id）に、7日・1回だけ使える招待を1本作る。
作れなかったときは None（申込は成功のまま、画面が案内を出す）。招待は DB に保存しない（正本は Discord）。
ログには例外の種類と HTTP の状態だけを出す（email・申込コード・招待の文字列は出さない）。
"""
from __future__ import annotations

import logging
import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.discord_rest import DiscordAPIError, discord_api_request

logger = logging.getLogger(__name__)

INVITE_MAX_AGE_SEC = 604800  # 7日（Discord の上限）
INVITE_MAX_USES = 1


async def create_viewer_invite(db: AsyncSession) -> str | None:
    """招待リンク（https://discord.gg/<code>）を返す。作れなければ None。

    呼び出し側は、この関数を呼ぶ前に自分の書き込みを commit しておくこと（未 commit の変更は捨てられる）。
    """
    status_code: int | None = None
    try:
        row = (
            await db.execute(text("SELECT reception_channel_id FROM public.viewer_discord_config WHERE id = 1"))
        ).first()
        await db.rollback()  # 読み取りだけ。Discord を待つ間、トランザクションを開いたままにしない
        if row is None or not row[0]:
            return None
        bot_token = os.environ.get("DISCORD_BOT_TOKEN")
        if not bot_token:
            return None
        result = await discord_api_request(
            method="POST",
            path=f"/channels/{row[0]}/invites",
            bot_token=bot_token,
            json={"max_age": INVITE_MAX_AGE_SEC, "max_uses": INVITE_MAX_USES, "unique": True},
            expected_statuses=(200,),
            max_retries=1,
        )
        code = (result or {}).get("code")
        if not isinstance(code, str) or not code:
            return None
        return f"https://discord.gg/{code}"
    except DiscordAPIError as exc:
        status_code = exc.status_code
        logger.warning("viewer invite: 作成失敗 kind=%s status=%s", type(exc).__name__, status_code)
        return None
    except Exception as exc:
        logger.warning("viewer invite: 作成失敗 kind=%s status=%s", type(exc).__name__, status_code)
        return None
