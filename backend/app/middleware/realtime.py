"""書き込み成功を合図として配るミドルウェア（ADR-1016）。応答は遅らせない。"""

from __future__ import annotations

import asyncio
import re
from typing import Optional

from app.realtime.publisher import publish_change
from app.realtime.topics import (
    INVENTORY_SIGNAL_ROUTES,
    TASK_TOPICS,
    TOPIC_TCG_INVENTORY,
    WRITE_ROUTE_TOPICS,
)

_WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
_CLIENT_ID_RE = re.compile(r"^[A-Za-z0-9-]{1,64}$")

_pending: set[asyncio.Task] = set()


def parse_origin(raw: Optional[str]) -> Optional[str]:
    if raw and _CLIENT_ID_RE.fullmatch(raw):
        return raw
    return None


def _spawn(coro) -> None:
    task = asyncio.get_running_loop().create_task(coro)
    _pending.add(task)
    task.add_done_callback(_pending.discard)


class RealtimeSignalMiddleware:
    """純 ASGI。応答の状態コードを覚えておき、応答が終わった後に（task で）合図を出す。"""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http" or scope["method"] not in _WRITE_METHODS:
            await self.app(scope, receive, send)
            return

        status_holder: dict[str, int] = {}

        async def send_wrapper(message) -> None:
            if message["type"] == "http.response.start":
                status_holder["status"] = message["status"]
            await send(message)

        await self.app(scope, receive, send_wrapper)

        status = status_holder.get("status")
        if status is None or not (200 <= status < 300):
            return
        route = scope.get("route")
        route_path = getattr(route, "path", None)
        key = (scope["method"], route_path)
        entry = WRITE_ROUTE_TOPICS.get(key)
        inventory = key in INVENTORY_SIGNAL_ROUTES
        if entry is None and not inventory:
            return
        origin = None
        for k, v in scope.get("headers", []):
            if k == b"x-client-id":
                origin = parse_origin(v.decode("latin-1"))
                break
        if entry is not None:
            topic, sig_scope = entry
            tenant_id = None
            if sig_scope == "tenant":
                tenant_id = (scope.get("state") or {}).get("rt_tenant_id")
            if sig_scope != "tenant" or tenant_id is not None:
                _spawn(publish_change(topic, sig_scope, tenant_id=tenant_id, origin=origin))
        if inventory:
            # 全接続に届く合図なので origin は載せない（ADR-1016 改訂 2026-10-19）
            _spawn(
                publish_change(
                    TOPIC_TCG_INVENTORY,
                    TASK_TOPICS[TOPIC_TCG_INVENTORY],
                    tenant_id=None,
                    origin=None,
                )
            )
