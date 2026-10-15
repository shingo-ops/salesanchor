"""celery の健康の記録と読み取り（ADR-1012 段階1 便5）。

記録は worker が行い、読み取りは backend の /metrics が行う。置き場は broker と同じ Redis（CELERY_BROKER_URL）。
どちらも失敗してもログのみで例外を出さない（本来の処理を止めない）。
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Optional

import redis
import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/1")

HEARTBEAT_KEY = "ai_ops:celery:heartbeat_ts"
FAILURES_KEY = "ai_ops:celery:task_failures"
QUEUE_KEY = "celery"

_sync_client: Optional[redis.Redis] = None
_async_client: Optional[aioredis.Redis] = None


def _get_sync() -> redis.Redis:
    global _sync_client
    if _sync_client is None:
        _sync_client = redis.from_url(
            BROKER_URL, decode_responses=True, socket_connect_timeout=2, socket_timeout=2
        )
    return _sync_client


def _get_async() -> aioredis.Redis:
    global _async_client
    if _async_client is None:
        _async_client = aioredis.from_url(
            BROKER_URL, decode_responses=True, socket_connect_timeout=2, socket_timeout=2
        )
    return _async_client


def record_heartbeat() -> None:
    """worker が 1 分ごとに呼ぶ。今の時刻（秒）を書く。"""
    try:
        _get_sync().set(HEARTBEAT_KEY, str(time.time()))
    except Exception:
        logger.warning("celery heartbeat の記録に失敗（処理は継続）", exc_info=True)


def record_task_failure(task_name: str) -> None:
    """worker の task_failure から呼ぶ。タスク名ごとの失敗の数を 1 増やす。"""
    try:
        _get_sync().hincrby(FAILURES_KEY, task_name or "unknown", 1)
    except Exception:
        logger.warning("celery 失敗数の記録に失敗（処理は継続）: task=%s", task_name, exc_info=True)


READ_TIMEOUT_SEC = 1.5  # /metrics を遅らせない上限（Prometheus の scrape の制限時間より十分短く）


async def _read_raw():
    pipe = _get_async().pipeline(transaction=False)
    pipe.get(HEARTBEAT_KEY)
    pipe.hgetall(FAILURES_KEY)
    pipe.llen(QUEUE_KEY)
    return await pipe.execute()


async def read_celery_health() -> Optional[tuple[float, dict[str, int], int]]:
    """(最後の heartbeat の時刻, タスク名ごとの失敗の数, 待ち行列の長さ) を返す。読めなければ None。

    Redis へは 1 往復（pipeline）で、全体を READ_TIMEOUT_SEC で打ち切る。
    heartbeat のキーが無いときは時刻 0.0 を返す（見張りは「古い」と判定して鳴る）。
    """
    try:
        ts_raw, failures_raw, queue_len = await asyncio.wait_for(_read_raw(), READ_TIMEOUT_SEC)
        ts = float(ts_raw) if ts_raw else 0.0
        failures = {name: int(count) for name, count in (failures_raw or {}).items()}
        return ts, failures, int(queue_len)
    except Exception:
        logger.warning("celery の健康の読み取りに失敗", exc_info=True)
        return None
