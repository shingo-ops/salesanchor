"""解析の止まりと Gemini への道の切り替えを5分ごとに見て、管理者用 Discord へ知らせる（ADR-1062）。

- 止まり: 直前 STALL_WINDOW_MINUTES 分に終わった試みで completed が 0、failed が 1 以上。
- 戻り: 止まりの知らせを出したあと completed が 1 以上になったら 1 通。
- 道の切り替え: gemini_route が Redis に数えた切り替えを、向きごと 24 時間に 1 通。
DB は読むだけ。Redis・送り先が使えないときは何もしない（送りすぎを防ぐ）。
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.services import gemini_route
from app.services.tcg_extraction_record_svc import TCG_SCHEMA

logger = logging.getLogger(__name__)

STALL_WINDOW_MINUTES = 30
STALL_REDIS_KEY = "gemini_route_watch:stalled"
STALL_REDIS_TTL_SECONDS = 7 * 24 * 60 * 60
SWITCH_NOTIFIED_PREFIX = "gemini_route_watch:switch_notified:"
SWITCH_NOTIFIED_TTL_SECONDS = 24 * 60 * 60
_DIRECTIONS = ("direct_to_relay", "relay_to_direct")
_JST = timezone(timedelta(hours=9))

_DATABASE_URL = os.getenv("DATABASE_URL", "").replace(
    "postgresql+asyncpg://", "postgresql://"
)


def _get_sync_engine():
    return create_engine(_DATABASE_URL, echo=False)


def find_stall(session, at: datetime | None = None) -> dict:
    """直前 STALL_WINDOW_MINUTES 分の成功・失敗の数と、最後の失敗の理由を読む（読むだけ）。"""
    if at is None:
        at = datetime.now(timezone.utc)
    params = {"at": at, "window": STALL_WINDOW_MINUTES}
    counts = session.execute(
        text(
            f"""
            SELECT
                COUNT(*) FILTER (WHERE phase = 'completed') AS completed,
                COUNT(*) FILTER (WHERE phase = 'failed') AS failed
            FROM {TCG_SCHEMA}.extraction_attempts
            WHERE finished_at > :at - make_interval(mins => :window)
              AND finished_at <= :at
            """
        ),
        params,
    ).mappings().first() or {}
    completed = int(counts.get("completed") or 0)
    failed = int(counts.get("failed") or 0)
    last_reason = None
    if failed:
        row = session.execute(
            text(
                f"""
                SELECT COALESCE(validation_result->>'reason', validation_result->>'raw', error_code) AS last_reason
                FROM {TCG_SCHEMA}.extraction_attempts
                WHERE phase = 'failed'
                  AND finished_at > :at - make_interval(mins => :window)
                  AND finished_at <= :at
                ORDER BY finished_at DESC
                LIMIT 1
                """
            ),
            params,
        ).mappings().first()
        last_reason = row["last_reason"] if row else None
    return {
        "completed": completed,
        "failed": failed,
        "last_reason": last_reason,
        "stalled": completed == 0 and failed >= 1,
        "at": at,
    }


def _jst_text(at: datetime) -> str:
    if at.tzinfo is None:
        at = at.replace(tzinfo=timezone.utc)
    return at.astimezone(_JST).strftime("%Y-%m-%d %H:%M")


def build_stall_message(info: dict) -> str:
    return "\n".join(
        [
            "⚠️ 解析が30分成功していません（ADR-1062）",
            f"直前30分の失敗: {info['failed']} 回",
            f"最後の失敗の理由: {info.get('last_reason') or '不明'}",
            f"判定の時刻: {_jst_text(info['at'])}",
        ]
    )


def build_recovered_message(info: dict) -> str:
    return f"✅ 解析が戻りました（ADR-1062）直前30分の成功: {info['completed']} 回"


def build_switch_message(direction: str, count: int) -> str:
    if direction == "direct_to_relay":
        label = "直接 → prod2 の中継"
    else:
        label = "prod2 の中継 → 直接"
    return f"🔀 Gemini への道を自動で切り替えました: {label}（24時間で {count} 回・ADR-1062）"


def _send(url: str, content: str) -> bool:
    from app.services.discord_notifier import _post_discord_webhook  # noqa: PLC0415

    return bool(asyncio.run(_post_discord_webhook(url, content)))


def run_watch(session, redis_client, url) -> dict:
    info = find_stall(session)
    result = {
        "stalled": info["stalled"],
        "stall_notified": False,
        "recovered_notified": False,
        "switch_notified": [],
    }
    marked = redis_client.get(STALL_REDIS_KEY)
    if info["stalled"] and not marked:
        if _send(url, build_stall_message(info)):
            redis_client.set(STALL_REDIS_KEY, "1", ex=STALL_REDIS_TTL_SECONDS)
            result["stall_notified"] = True
    elif info["completed"] >= 1 and marked:
        if _send(url, build_recovered_message(info)):
            redis_client.delete(STALL_REDIS_KEY)
            result["recovered_notified"] = True

    for direction in _DIRECTIONS:
        raw = redis_client.get(gemini_route.SWITCH_COUNT_PREFIX + direction)
        count = int(raw) if raw else 0
        if count < 1:
            continue
        notified_key = SWITCH_NOTIFIED_PREFIX + direction
        if redis_client.get(notified_key):
            continue
        if _send(url, build_switch_message(direction, count)):
            redis_client.set(notified_key, "1", ex=SWITCH_NOTIFIED_TTL_SECONDS)
            result["switch_notified"].append(direction)
    return result


def _run() -> dict:
    try:
        from app.services.discord_notifier import _get_webhook_url  # noqa: PLC0415

        url = _get_webhook_url()
        if not url:
            logger.warning("[gemini_route_watch] ADMIN_NOTIFICATION_DISCORD_WEBHOOK is not set; skip")
            return {"skipped": "no_webhook"}
        redis_client = gemini_route._get_redis()
        if redis_client is None:
            logger.warning("[gemini_route_watch] Redis unavailable; skip")
            return {"skipped": "no_redis"}
        engine = _get_sync_engine()
        try:
            Session = sessionmaker(engine)
            with Session() as session:
                return run_watch(session, redis_client, url)
        finally:
            engine.dispose()
    except Exception as exc:  # noqa: BLE001
        logger.exception("[gemini_route_watch] 見張りに失敗")
        return {"error": type(exc).__name__}


try:
    from app.celery_app import celery_app

    @celery_app.task(
        name="app.tasks.gemini_route_watch.watch_gemini_route",
        time_limit=120,
        soft_time_limit=100,
    )
    def watch_gemini_route() -> dict:
        """Celery タスク: 解析の止まりと道の切り替えを見て Discord へ知らせる（5分ごと）。"""
        return _run()

except Exception as _celery_init_err:  # noqa: BLE001
    logger.warning("[gemini_route_watch] Celery task registration skipped: %s", _celery_init_err)
