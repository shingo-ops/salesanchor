"""GET /events/stream: 接続数上限・DB 接続を握らないこと・認証失敗（ADR-1016）。"""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

import httpx
from fastapi import FastAPI, Request

from app.routers import realtime_events as ev


def _app():
    app = FastAPI()
    app.include_router(ev.router, prefix="/api/v1")
    return app


def _patch_auth(monkeypatch, log):
    async def fake_get_db():
        log.append("open")
        try:
            yield object()
        finally:
            log.append("closed")

    async def fake_user(request, cred, db):
        log.append("auth")
        return SimpleNamespace(id=42, tenant_id=1, is_super_admin=False)

    async def fake_tenant(request, user, db):
        return 1

    monkeypatch.setattr(ev, "get_db", fake_get_db)
    monkeypatch.setattr(ev, "get_current_user", fake_user)
    monkeypatch.setattr(ev, "get_current_tenant", fake_tenant)


async def test_sixth_connection_returns_503(monkeypatch):
    ev._active_by_user.clear()
    log = []
    _patch_auth(monkeypatch, log)
    for _ in range(ev.MAX_CONN_PER_USER):
        assert ev._try_acquire(42)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=_app()), base_url="http://t") as c:
        r = await c.get("/api/v1/events/stream", headers={"Authorization": "Bearer x"})
    assert r.status_code == 503
    assert log[-1] == "closed"
    ev._active_by_user.clear()


async def test_db_session_is_closed_before_first_chunk(monkeypatch):
    ev._active_by_user.clear()
    log = []
    _patch_auth(monkeypatch, log)
    monkeypatch.setattr(ev, "_HEARTBEAT_SEC", 0.05)
    registered = []
    monkeypatch.setattr(ev.hub, "register", registered.append)
    monkeypatch.setattr(ev.hub, "unregister", lambda c: None)

    async def receive():
        await asyncio.sleep(3600)

    request = Request({"type": "http", "method": "GET", "path": "/api/v1/events/stream", "headers": []}, receive)
    response = await ev.stream_change_signals(request, SimpleNamespace(credentials="x"))
    body = response.body_iterator
    chunk = await asyncio.wait_for(body.__anext__(), timeout=5)
    # 最初のチャンクを受け取った時点で、DB セッションは閉じている
    assert log == ["open", "auth", "closed"]
    assert chunk.startswith(": ping")
    assert len(registered) == 1
    await body.aclose()
    assert ev._active_by_user == {}


async def test_missing_token_is_rejected_without_opening_db(monkeypatch):
    log = []
    _patch_auth(monkeypatch, log)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=_app()), base_url="http://t") as c:
        r = await c.get("/api/v1/events/stream")
    assert r.status_code in (401, 403)
    assert log == []


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
