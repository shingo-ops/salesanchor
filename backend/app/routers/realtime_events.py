"""即時反映の合図 SSE（ADR-1016）。GET /api/v1/events/stream"""

from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials

from app.auth.dependencies import get_current_tenant, get_current_user, require_super_admin, security
from app.database import get_db
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


def _db_scope():
    """短命の DB セッション。get_db と同じ後始末（ロールバック・テナント文脈クリア）を使う。"""
    return asynccontextmanager(get_db)()


@router.get("/events/stream")
async def stream_change_signals(
    request: Request,
    cred: HTTPAuthorizationCredentials = Depends(security),
) -> StreamingResponse:
    """書き込み成功の合図（"event: change"）を送る。30 秒ごとにハートビート ping。

    DB 依存（Depends）は持たない。yield 依存はストリーム送出が終わるまで閉じず、
    SSE 1 本ごとに DB 接続を握り続けてしまうため。認証・会社 ID・super admin の判定だけ
    短いセッションで行い、ストリームを返す前に閉じる。
    """
    async with _db_scope() as db:
        user = await get_current_user(request, cred, db)
        tenant_id = await get_current_tenant(request, user, db)
        is_super_admin = await _is_super_admin(user)
        user_id = int(user.id)

    if not _try_acquire(user_id):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="接続数が上限に達しています",
        )
    conn = Connection(tenant_id=tenant_id, is_super_admin=is_super_admin, user_id=user_id)
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
