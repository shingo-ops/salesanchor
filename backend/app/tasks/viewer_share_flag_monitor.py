"""ADR-1019 段6: 閲覧者の使い回しの疑い（目印）が新しく出たら、運用の Discord へ1回だけ知らせる。

目印の条件は app.services.viewer_admin（share_flag_hits）が正。ここには書かない。
通知には email・LINE 名・IP を載せない（id だけ）。同じ知らせは Redis のキーで30日間送らない。
Redis が使えないときは送らない（同じ知らせを何度も送らないため）。
"""
from __future__ import annotations

import asyncio
import logging
import os

from celery import shared_task

from app.services.discord_notifier import _get_webhook_url, _post_discord_webhook
from app.services.viewer_admin import KIND_MANY_IPS, share_flag_hits

logger = logging.getLogger(__name__)

_REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
_REDIS_KEY_PREFIX = "viewer_share_flag:notified:"
_REDIS_TTL_SECONDS = 30 * 24 * 60 * 60

MESSAGE_MANY_IPS = (
    "閲覧者の使い回しの疑い：id {id} が24時間に3か所以上からログインしました。"
    "管理画面で確認してください。"
)
MESSAGE_SHARED_IP = (
    "閲覧者の使い回しの疑い：id {id} が id {others} と同じ場所からログインしました。"
    "管理画面で確認してください。"
)


def build_message(viewer_id: int, kind: str, others: list[int]) -> str:
    if kind == KIND_MANY_IPS:
        return MESSAGE_MANY_IPS.format(id=viewer_id)
    return MESSAGE_SHARED_IP.format(id=viewer_id, others=", ".join(str(o) for o in others))


def _redis_key(viewer_id: int, kind: str) -> str:
    return f"{_REDIS_KEY_PREFIX}{viewer_id}:{kind}"


def _get_redis():
    """同期 Redis クライアント。使えなければ None。"""
    try:
        import redis

        client = redis.from_url(_REDIS_URL, decode_responses=True)
        client.ping()
        return client
    except Exception as exc:  # noqa: BLE001
        logger.warning("[viewer-share-flag] Redis unavailable (skip): %s", type(exc).__name__)
        return None


async def _run_report() -> dict:
    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        hits = await share_flag_hits(db)
    result = {"hits": len(hits), "sent": 0}
    if not hits:
        return result
    url = _get_webhook_url()
    if not url:
        logger.warning("ADMIN_NOTIFICATION_DISCORD_WEBHOOK is not set; skip viewer share flag report")
        return result
    client = _get_redis()
    if client is None:
        return result
    for viewer_id, kind, others in hits:
        key = _redis_key(viewer_id, kind)
        try:
            if client.exists(key):
                continue
        except Exception as exc:  # noqa: BLE001
            logger.warning("[viewer-share-flag] Redis check failed: %s", type(exc).__name__)
            continue
        if await _post_discord_webhook(url, build_message(viewer_id, kind, others)):
            try:
                client.set(key, "1", ex=_REDIS_TTL_SECONDS)
            except Exception as exc:  # noqa: BLE001
                logger.warning("[viewer-share-flag] Redis set failed: %s", type(exc).__name__)
            result["sent"] += 1
    return result


@shared_task(name="app.tasks.viewer_share_flag_monitor.notify_viewer_share_flags")
def notify_viewer_share_flags() -> dict:
    from app.database import engine

    try:
        return asyncio.run(_run_report())
    finally:
        asyncio.run(engine.dispose())
