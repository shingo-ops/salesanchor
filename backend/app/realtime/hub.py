"""合図の受け手（ADR-1016）。プロセスにつき 1 本だけ psubscribe("rt:*") し、登録された接続へ配る。"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Optional

import redis.asyncio as aioredis

from app.realtime.publisher import (
    CHANNEL_GLOBAL,
    CHANNEL_PATTERN,
    CHANNEL_SHARED,
    CHANNEL_TENANT_PREFIX,
    CHANNEL_USER_PREFIX,
    RT_REDIS_URL,
)

logger = logging.getLogger(__name__)

_RECONNECT_DELAY_SEC = 3.0
_QUEUE_MAX = 100


@dataclass(eq=False)
class Connection:
    tenant_id: int
    is_super_admin: bool
    user_id: int | None = None  # 人宛ての合図（rt:u:）の宛先。None なら人宛ては届かない
    queue: asyncio.Queue = field(default_factory=lambda: asyncio.Queue(maxsize=_QUEUE_MAX))


def _targets(channel: str, conn: Connection) -> bool:
    if channel == CHANNEL_SHARED:
        # 会社共通データの合図は全接続へ（ADR-1016 改訂 2026-10-18）。名前と origin だけでデータは含まない
        return True
    if channel == CHANNEL_GLOBAL:
        return conn.is_super_admin
    if channel.startswith(CHANNEL_USER_PREFIX):
        if conn.user_id is None:
            return False
        try:
            return int(channel[len(CHANNEL_USER_PREFIX):]) == conn.user_id
        except ValueError:
            return False
    if channel.startswith(CHANNEL_TENANT_PREFIX):
        try:
            return int(channel[len(CHANNEL_TENANT_PREFIX):]) == conn.tenant_id
        except ValueError:
            return False
    return False


class RealtimeHub:
    def __init__(self) -> None:
        self._conns: set[Connection] = set()
        self._task: Optional[asyncio.Task] = None

    def register(self, conn: Connection) -> None:
        self._conns.add(conn)
        self._ensure_started()

    def unregister(self, conn: Connection) -> None:
        self._conns.discard(conn)

    def _ensure_started(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.get_running_loop().create_task(self._run())

    def dispatch(self, channel: str, data: str) -> None:
        """受けた合図を、宛先に合う接続のキューへ入れる（満杯なら捨てる。次の合図で追いつく）。"""
        try:
            payload = json.loads(data)
        except (TypeError, ValueError):
            logger.warning("realtime: 不正な合図を無視 channel=%s", channel)
            return
        for conn in list(self._conns):
            if _targets(channel, conn):
                try:
                    conn.queue.put_nowait(payload)
                except asyncio.QueueFull:
                    logger.warning("realtime: キュー満杯のため合図を破棄 channel=%s", channel)

    async def _run(self) -> None:
        while True:
            r = None
            pubsub = None
            try:
                r = aioredis.from_url(RT_REDIS_URL, decode_responses=True)
                pubsub = r.pubsub()
                await pubsub.psubscribe(CHANNEL_PATTERN)
                async for msg in pubsub.listen():
                    if msg.get("type") == "pmessage":
                        self.dispatch(msg["channel"], msg["data"])
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.warning("realtime hub: Redis 購読が切れた。再接続する", exc_info=True)
            finally:
                try:
                    if pubsub is not None:
                        await pubsub.aclose()
                    if r is not None:
                        await r.aclose()
                except Exception:
                    pass
            await asyncio.sleep(_RECONNECT_DELAY_SEC)


hub = RealtimeHub()
