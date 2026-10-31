"""合図の送り手（ADR-1016）。Redis pub/sub（DB3、sse_pubsub と同じ決め方）へ流す。失敗してもログのみ（fail-open）。"""

from __future__ import annotations

import json
import logging
import os
from typing import Optional

import redis
import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

# sse_pubsub.py と同じ: REDIS_URL の DB 番号を 3 に置換
_base = os.getenv("REDIS_URL", "redis://redis:6379/0")
RT_REDIS_URL = _base.rsplit("/", 1)[0] + "/3"

CHANNEL_GLOBAL = "rt:global"
CHANNEL_SHARED = "rt:shared"
CHANNEL_TENANT_PREFIX = "rt:t:"
CHANNEL_USER_PREFIX = "rt:u:"
CHANNEL_PATTERN = "rt:*"

_async_client: Optional[aioredis.Redis] = None
_sync_client: Optional[redis.Redis] = None


def tenant_channel(tenant_id: int) -> str:
    return f"{CHANNEL_TENANT_PREFIX}{int(tenant_id)}"


def user_channel(user_id: int) -> str:
    return f"{CHANNEL_USER_PREFIX}{int(user_id)}"


def _channel_for(scope: str, tenant_id: Optional[int]) -> Optional[str]:
    if scope == "global":
        return CHANNEL_GLOBAL
    if scope == "shared":
        return CHANNEL_SHARED
    if scope == "tenant" and tenant_id is not None:
        return tenant_channel(tenant_id)
    return None


def _payload(topic: str, origin: Optional[str]) -> str:
    return json.dumps({"topic": topic, "origin": origin}, ensure_ascii=False)


def _get_async() -> aioredis.Redis:
    global _async_client
    if _async_client is None:
        _async_client = aioredis.from_url(
            RT_REDIS_URL, decode_responses=True, socket_connect_timeout=2, socket_timeout=2
        )
    return _async_client


def _get_sync() -> redis.Redis:
    global _sync_client
    if _sync_client is None:
        _sync_client = redis.from_url(
            RT_REDIS_URL, decode_responses=True, socket_connect_timeout=2, socket_timeout=2
        )
    return _sync_client


async def publish_change(
    topic: str, scope: str, tenant_id: Optional[int] = None, origin: Optional[str] = None
) -> None:
    """合図を1つ送る。Redis 障害時はログのみで例外を出さない。"""
    channel = _channel_for(scope, tenant_id)
    if channel is None:
        logger.warning("realtime publish スキップ: 宛先なし topic=%s scope=%s", topic, scope)
        return
    try:
        await _get_async().publish(channel, _payload(topic, origin))
    except Exception:
        logger.warning("realtime publish 失敗（処理は継続）: topic=%s", topic, exc_info=True)


def publish_change_sync(
    topic: str, scope: str, tenant_id: Optional[int] = None, origin: Optional[str] = None
) -> None:
    """Celery 等の同期コード用。中身は publish_change と同じ。"""
    channel = _channel_for(scope, tenant_id)
    if channel is None:
        logger.warning("realtime publish(sync) スキップ: 宛先なし topic=%s scope=%s", topic, scope)
        return
    try:
        _get_sync().publish(channel, _payload(topic, origin))
    except Exception:
        logger.warning("realtime publish(sync) 失敗（処理は継続）: topic=%s", topic, exc_info=True)


async def publish_user_change(user_id: int, topic: str, origin: Optional[str] = None) -> None:
    """人宛ての合図を1つ送る（ADR-1055）。中身は topic と origin だけ（依頼の id などは入れない）。
    人宛ての送り口は、この async と publish_user_change_sync の2つだけ。"""
    try:
        await _get_async().publish(user_channel(user_id), _payload(topic, origin))
    except Exception:
        logger.warning("realtime publish(user) 失敗（処理は継続）: topic=%s", topic, exc_info=True)


def publish_user_change_sync(user_id: int, topic: str, origin: Optional[str] = None) -> None:
    """Celery 等の同期コード用。中身は publish_user_change と同じ。"""
    try:
        _get_sync().publish(user_channel(user_id), _payload(topic, origin))
    except Exception:
        logger.warning("realtime publish(user,sync) 失敗（処理は継続）: topic=%s", topic, exc_info=True)
