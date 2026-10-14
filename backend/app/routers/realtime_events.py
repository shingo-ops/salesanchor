"""即時反映の合図 SSE（ADR-1016）。GET /api/v1/events/stream"""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from app.auth.dependencies import get_current_tenant, get_current_user, require_super_admin
from app.models import User
from app.realtime.hub import Connection, hub

logger = logging.getLogger(__name__)

router = APIRouter()

_HEARTBEAT_SEC = 30
MAX_CONN_PER_USER = 5
_active_by_user: dict[int, int] = {}


async def _is_super_admin(user: User) -> bool:
    """require_super_admin と同じ判定（新しい判定は作らない）。"""
    try:
        await require_super_admin(user)
    except HTTPException:
        return False
    return True


def _try_acquire(user_id: int) -> bool:
    n = _active_by_user.get(user_id, 0)
    if n >= MAX_CONN_PER_USER:
        return False
    _active_by_user[user_id] = n + 1
    return True


def _release(user_id: int) -> None:
    n = _active_by_user.get(user_id, 0)
    if n <= 1:
        _active_by_user.pop(user_id, None)
    else:
        _active_by_user[user_id] = n - 1


@router.get("/events/stream")
async def stream_change_signals(
    request: Request,
    user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant),
) -> StreamingResponse:
    """書き込み成功の合図（"event: change"）を送る。30 秒ごとにハートビート ping。"""
    user_id = int(user.id)
    if not _try_acquire(user_id):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="接続数が上限に達しています",
        )
    conn = Connection(tenant_id=tenant_id, is_super_admin=await _is_super_admin(user))
    hub.register(conn)

    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    payload = await asyncio.wait_for(conn.queue.get(), timeout=_HEARTBEAT_SEC)
                    yield f"event: change\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
        finally:
            hub.unregister(conn)
            _release(user_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
