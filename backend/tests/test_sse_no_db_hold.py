"""流し続ける口（SSE）は DB の取引を依存に持たない見張り＋受信箱の流れの試験（ADR-1016 追記）。"""
from __future__ import annotations

import asyncio
import inspect
import typing
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.dependencies.models import Dependant
from fastapi.responses import StreamingResponse
from fastapi.routing import APIRoute

from app.realtime import stream_db
from app.routers import meta_inbox as mi

EXPECTED_STREAMS = {
    ("GET", "/api/v1/events/stream"),
    ("GET", "/api/v1/conversations/stream"),
    ("GET", "/api/v1/leads/stream"),
}
# 理由: /leads/{lead_id} が先に登録されていて流れに入らない（recon B の別の不具合）。直すときに例外を消す。
ALLOWED_GET_DB = {("GET", "/api/v1/leads/stream")}


def _stream_routes():
    from app.main import app

    found = {}
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        ep = route.endpoint
        hit = False
        try:
            ret = typing.get_type_hints(ep).get("return")
        except Exception:
            ret = None
        if inspect.isclass(ret) and issubclass(ret, StreamingResponse):
            hit = True
        try:
            if "text/event-stream" in inspect.getsource(ep):
                hit = True
        except (OSError, TypeError):
            pass
        rc = route.response_class
        rc = getattr(rc, "value", rc)
        if inspect.isclass(rc) and issubclass(rc, StreamingResponse):
            hit = True
        if inspect.isasyncgenfunction(ep) or inspect.isgeneratorfunction(ep):
            hit = True
        if hit:
            for m in route.methods:
                found[(m, route.path)] = route
    return found


def _gen_deps(dep: Dependant, seen=None):
    seen = seen if seen is not None else set()
    out = []
    for sub in dep.dependencies:
        if id(sub) in seen:
            continue
        seen.add(id(sub))
        if sub.is_gen_callable() or sub.is_async_gen_callable():
            out.append(getattr(sub.call, "__name__", repr(sub.call)))
        out.extend(_gen_deps(sub, seen))
    return out


def test_stream_routes_are_exactly_the_known_three():
    found = set(_stream_routes())
    assert found == EXPECTED_STREAMS, f"流し口の集合が変わった: {sorted(found)}"


def test_stream_routes_have_no_yield_dependency():
    routes = _stream_routes()
    bad = {}
    for key, route in routes.items():
        deps = _gen_deps(route.dependant)
        if key in ALLOWED_GET_DB:
            assert deps, f"例外 {key} はもう yield 依存を持たない。例外の表から消す"
            continue
        if deps:
            bad[f"{key[0]} {key[1]}"] = deps
    assert not bad, f"流し口が yield 依存を持っている: {bad}"


# ---- 受信箱の流れ（§5-4） ----


def _app():
    app = FastAPI()
    app.include_router(mi.stream_router, prefix="/api/v1")
    return app


def _patch(monkeypatch, log, perm_exc=None):
    async def fake_get_db():
        log.append("open")
        try:
            yield object()
        finally:
            log.append("closed")

    async def fake_user(request, cred, db):
        log.append("auth")
        return SimpleNamespace(id=42, tenant_id=1)

    async def fake_tenant(request, user, db):
        log.append("tenant")
        return 1

    async def fake_perm(current_user, tenant_id, db):
        log.append("perm")
        if perm_exc:
            raise perm_exc

    async def fake_incr(kind, tenant_id):
        return True

    async def fake_decr(kind, tenant_id):
        return None

    async def fake_sub(tenant_id):
        await asyncio.sleep(3600)
        yield None

    import app.services.sse_pubsub as ps

    monkeypatch.setattr(stream_db, "get_db", fake_get_db)
    monkeypatch.setattr(mi, "get_current_user", fake_user)
    monkeypatch.setattr(mi, "get_current_tenant", fake_tenant)
    monkeypatch.setattr(mi, "_MESSAGING_VIEW", fake_perm)
    monkeypatch.setattr(ps, "increment_connection", fake_incr)
    monkeypatch.setattr(ps, "decrement_connection", fake_decr)
    monkeypatch.setattr(ps, "subscribe_inbox", fake_sub)


async def test_t1_db_closed_before_first_chunk(monkeypatch):
    log = []
    _patch(monkeypatch, log)
    monkeypatch.setattr(mi, "_SSE_HEARTBEAT_SEC", 0.05)

    async def receive():
        await asyncio.sleep(3600)

    request = Request(
        {"type": "http", "method": "GET", "path": "/api/v1/conversations/stream", "headers": []}, receive
    )
    response = await mi.stream_inbox_updates(request, SimpleNamespace(credentials="x"))
    body = response.body_iterator
    chunk = await asyncio.wait_for(body.__anext__(), timeout=5)
    assert log == ["open", "auth", "tenant", "perm", "closed"]
    assert chunk.startswith(": ping")
    await body.aclose()


async def test_t2_missing_token_rejected_without_db(monkeypatch):
    log = []
    _patch(monkeypatch, log)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=_app()), base_url="http://t") as c:
        r = await c.get("/api/v1/conversations/stream")
    assert r.status_code in (401, 403)
    assert log == []


async def test_t3_permission_denied_returns_403_and_closes_db(monkeypatch):
    log = []
    _patch(monkeypatch, log, perm_exc=HTTPException(status_code=403, detail="権限が不足しています"))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=_app()), base_url="http://t") as c:
        r = await c.get("/api/v1/conversations/stream", headers={"Authorization": "Bearer x"})
    assert r.status_code == 403
    assert log[-1] == "closed"


def test_t4_single_route_in_app():
    from app.main import app

    n = sum(
        1
        for r in app.routes
        if isinstance(r, APIRoute) and r.path == "/api/v1/conversations/stream" and "GET" in r.methods
    )
    assert n == 1
