"""GET /events/stream の接続数上限（ADR-1016）。"""
from __future__ import annotations

from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI

from app.auth.dependencies import get_current_tenant, get_current_user
from app.routers import realtime_events as ev


def _app():
    app = FastAPI()
    app.include_router(ev.router, prefix="/api/v1")
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=42, tenant_id=1, is_super_admin=False)
    app.dependency_overrides[get_current_tenant] = lambda: 1
    return app


async def test_sixth_connection_returns_503():
    ev._active_by_user.clear()
    app = _app()
    for _ in range(ev.MAX_CONN_PER_USER):
        assert ev._try_acquire(42)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v1/events/stream")
    assert r.status_code == 503
    ev._active_by_user.clear()


def test_release_frees_slot():
    ev._active_by_user.clear()
    for _ in range(ev.MAX_CONN_PER_USER):
        assert ev._try_acquire(7)
    assert not ev._try_acquire(7)
    ev._release(7)
    assert ev._try_acquire(7)
    ev._active_by_user.clear()


async def test_super_admin_judgement_reuses_require_super_admin():
    assert await ev._is_super_admin(SimpleNamespace(is_super_admin=True))
    assert not await ev._is_super_admin(SimpleNamespace(is_super_admin=False))
