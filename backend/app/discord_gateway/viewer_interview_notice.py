"""お試し期限の前日に、その人の部屋へ面談のお願いを自動で送る（ADR-1019 段10 便3）。

送る条件: status='trial'・部屋あり・期限あり、期限の JST 日付の前日が今日（JST）、今が JST 10:00 以降。
重複防止: Redis キー viewer_interview_notice:{id}:{期限の JST 日付}。送れたときだけ TTL 30日で置く。
Redis が使えないときは誰にも送らない。ログは id と結果だけ（本文・メール・LINE名は出さない）。
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import text

from app.discord_gateway import viewer_bot_texts
from app.services import viewer_message_templates as vmt
from app.services.viewer_room_notice import send_room_notice

logger = logging.getLogger(__name__)

INTERVIEW_NOTICE_HOUR_JST = 10
LOOP_INTERVAL_SECONDS = 3600
REDIS_TTL_SECONDS = 30 * 24 * 60 * 60
_KEY_PREFIX = "viewer_interview_notice:"
_JST = timezone(timedelta(hours=9))


def _jst(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(_JST)


def expiry_jst_date(expires_at: datetime) -> date:
    return _jst(expires_at).date()


def redis_key(viewer_id: int, expires_at: datetime) -> str:
    return f"{_KEY_PREFIX}{viewer_id}:{expiry_jst_date(expires_at).isoformat()}"


def is_due(now_utc: datetime, expires_at: datetime) -> bool:
    """期限の JST 日付の前日が今日（JST）で、今が JST 10:00 以降なら True。"""
    now = _jst(now_utc)
    if now.hour < INTERVIEW_NOTICE_HOUR_JST:
        return False
    return expiry_jst_date(expires_at) - timedelta(days=1) == now.date()


async def _load_trials(db_factory: Any) -> list[tuple[int, str, datetime]]:
    async with db_factory() as session:
        rows = (
            await session.execute(
                text(
                    "SELECT id, discord_channel_id, trial_expires_at "
                    "FROM public.viewer_accounts "
                    "WHERE status = 'trial' AND discord_channel_id IS NOT NULL "
                    "AND trial_expires_at IS NOT NULL"
                )
            )
        ).all()
    return [(int(r[0]), str(r[1]), r[2]) for r in rows]


async def run_once(db_factory: Any, redis_client: Any, now_utc: datetime) -> int:
    """前日の人に1回だけ送る。送った件数を返す。Redis が無ければ 0。"""
    if redis_client is None:
        logger.warning("[viewer-interview] Redis unavailable (skip)")
        return 0
    # テンプレートは最初に1回読む。無い・読めない・検査に通らないときは誰にも送らず（Redis キーも作らず）次の周期で再試行
    try:
        async with db_factory() as session:
            body = await vmt.load_body(session, "interview_request")
    except Exception as exc:  # noqa: BLE001
        logger.warning("[viewer-interview] template read failed: %s", type(exc).__name__)
        return 0
    if body is None:
        logger.warning("[viewer-interview] template unavailable (skip)")
        return 0
    sent = 0
    for viewer_id, channel_id, expires_at in await _load_trials(db_factory):
        if not is_due(now_utc, expires_at):
            continue
        key = redis_key(viewer_id, expires_at)
        try:
            if await redis_client.exists(key):
                continue
        except Exception as exc:  # noqa: BLE001
            logger.warning("[viewer-interview] Redis check failed: %s", type(exc).__name__)
            continue
        text = vmt.render(
            "interview_request", body, expires_date=viewer_bot_texts.format_jst_date(expires_at)
        )
        if text is None:
            continue  # 差し込み後が長すぎるなど。送らず Redis キーも作らない（警告ログは render が出す）
        ok = await send_room_notice(channel_id, text)
        logger.info("[viewer-interview] id=%s result=%s", viewer_id, "sent" if ok else "failed")
        if not ok:
            continue
        sent += 1
        try:
            await redis_client.set(key, "1", ex=REDIS_TTL_SECONDS)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[viewer-interview] Redis set failed: %s", type(exc).__name__)
    return sent
