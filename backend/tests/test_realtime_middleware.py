"""即時反映の合図ミドルウェア・配信先の試験（ADR-1016）。Redis は使わない。"""
from __future__ import annotations

import asyncio
import time

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request

from app.middleware import realtime as mw
from app.realtime.hub import Connection, RealtimeHub
from app.realtime.topics import SCOPE_GLOBAL, SCOPE_TENANT

TENANT_PATH = "/t/{i}"
GLOBAL_PATH = "/g"


def _make_app(monkeypatch, sent, delay=0.0):
    async def fake_publish(topic, scope, tenant_id=None, origin=None):
        if delay:
            await asyncio.sleep(delay)
        sent.append((topic, scope, tenant_id, origin))

    monkeypatch.setattr(mw, "publish_change", fake_publish)
    monkeypatch.setitem(mw.WRITE_ROUTE_TOPICS, ("POST", TENANT_PATH), ("tcg.review", SCOPE_TENANT))
    monkeypatch.setitem(mw.WRITE_ROUTE_TOPICS, ("POST", GLOBAL_PATH), ("tcg.review", SCOPE_GLOBAL))

    app = FastAPI()

    async def set_tenant(request: Request):
        request.state.rt_tenant_id = 1

    @app.post(TENANT_PATH)
    async def t(i: int, _=Depends(set_tenant)):
        if i == 400:
            raise HTTPException(400, "bad")
        return {"ok": True}

    @app.post("/t_no_tenant/{i}")
    async def t2(i: int):
        return {"ok": True}

    monkeypatch.setitem(mw.WRITE_ROUTE_TOPICS, ("POST", "/t_no_tenant/{i}"), ("tcg.review", SCOPE_TENANT))

    @app.post(GLOBAL_PATH)
    async def g():
        return {"ok": True}

    @app.get("/r")
    async def r():
        return {}

    app.add_middleware(mw.RealtimeSignalMiddleware)
    return app


async def _post(app, path, headers=None):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        return await c.post(path, headers=headers)


async def _drain():
    # mw._pending はモジュール共通。同じプロセスで先に走った別の試験（TestClient 等、別のイベントループ）が
    # 残した task が混ざるので、今のループの task だけを待つ（別ループの task を gather すると ValueError）
    loop = asyncio.get_running_loop()
    await asyncio.gather(*[t for t in list(mw._pending) if t.get_loop() is loop])


async def test_2xx_sends_and_4xx_does_not(monkeypatch):
    sent = []
    app = _make_app(monkeypatch, sent)
    assert (await _post(app, "/t/1")).status_code == 200
    assert (await _post(app, "/t/400")).status_code == 400
    await _drain()
    assert sent == [("tcg.review", SCOPE_TENANT, 1, None)]


async def test_tenant_scope_without_tenant_id_does_not_send_but_global_does(monkeypatch):
    sent = []
    app = _make_app(monkeypatch, sent)
    await _post(app, "/t_no_tenant/1")
    await _post(app, GLOBAL_PATH)
    await _drain()
    assert sent == [("tcg.review", SCOPE_GLOBAL, None, None)]


async def test_origin_from_header_only_when_valid(monkeypatch):
    sent = []
    app = _make_app(monkeypatch, sent)
    await _post(app, GLOBAL_PATH, {"X-Client-Id": "abc-123"})
    await _post(app, GLOBAL_PATH, {"X-Client-Id": "bad id!"})
    await _post(app, GLOBAL_PATH, {"X-Client-Id": "a" * 65})
    await _drain()
    assert [s[3] for s in sent] == ["abc-123", None, None]


INV_PATH = "/inv"


def _make_inventory_app(monkeypatch, sent):
    app = _make_app(monkeypatch, sent)
    monkeypatch.setattr(mw, "INVENTORY_SIGNAL_ROUTES", frozenset({("POST", INV_PATH), ("POST", GLOBAL_PATH)}))

    @app.post(INV_PATH)
    async def inv(fail: bool = False):
        if fail:
            raise HTTPException(400, "bad")
        return {"ok": True}

    return app


async def test_inventory_route_2xx_sends_shared_and_4xx_does_not(monkeypatch):
    sent = []
    app = _make_inventory_app(monkeypatch, sent)
    assert (await _post(app, INV_PATH)).status_code == 200
    assert (await _post(app, INV_PATH + "?fail=true")).status_code == 400
    await _drain()
    assert sent == [("tcg.inventory", "shared", None, None)]


async def test_route_in_both_tables_sends_review_and_inventory(monkeypatch):
    sent = []
    app = _make_inventory_app(monkeypatch, sent)
    await _post(app, GLOBAL_PATH)
    await _drain()
    assert sorted(sent) == sorted([("tcg.review", SCOPE_GLOBAL, None, None), ("tcg.inventory", "shared", None, None)])


async def test_inventory_signal_has_no_origin_but_review_keeps_it(monkeypatch):
    sent = []
    app = _make_inventory_app(monkeypatch, sent)
    await _post(app, INV_PATH, {"X-Client-Id": "abc-123"})
    await _post(app, GLOBAL_PATH, {"X-Client-Id": "abc-123"})
    await _drain()
    origins = {s[0]: s[3] for s in sent}
    assert origins == {"tcg.inventory": None, "tcg.review": "abc-123"}
    assert [s[3] for s in sent if s[0] == "tcg.inventory"] == [None, None]


async def test_get_and_unlisted_routes_do_not_send(monkeypatch):
    sent = []
    app = _make_app(monkeypatch, sent)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        await c.get("/r")
    await _drain() if mw._pending else None
    assert sent == []


async def test_slow_publish_does_not_delay_response(monkeypatch):
    sent = []
    app = _make_app(monkeypatch, sent, delay=1.0)
    t0 = time.monotonic()
    r = await _post(app, GLOBAL_PATH)
    elapsed = time.monotonic() - t0
    assert r.status_code == 200
    assert elapsed < 0.5
    assert sent == []  # まだ送り終わっていない
    await _drain()
    assert len(sent) == 1


def _conn(tenant, sa=False):
    return Connection(tenant_id=tenant, is_super_admin=sa)


def test_tenant_signal_not_delivered_to_other_tenant():
    hub = RealtimeHub()
    c1, c2 = _conn(1), _conn(2)
    hub._conns.update({c1, c2})
    hub.dispatch("rt:t:1", '{"topic":"x","origin":null}')
    assert c1.queue.qsize() == 1
    assert c2.queue.qsize() == 0


def test_global_signal_only_to_super_admin():
    hub = RealtimeHub()
    normal, sa = _conn(1), _conn(1, sa=True)
    hub._conns.update({normal, sa})
    hub.dispatch("rt:global", '{"topic":"tcg.review","origin":"o1"}')
    assert normal.queue.qsize() == 0
    assert sa.queue.get_nowait() == {"topic": "tcg.review", "origin": "o1"}


def test_shared_signal_to_every_connection():
    hub = RealtimeHub()
    t1, t2, sa = _conn(1), _conn(2), _conn(1, sa=True)
    hub._conns.update({t1, t2, sa})
    hub.dispatch("rt:shared", '{"topic":"tcg.inventory","origin":null}')
    for c in (t1, t2, sa):
        assert c.queue.get_nowait() == {"topic": "tcg.inventory", "origin": None}


def test_invalid_payload_is_ignored():
    hub = RealtimeHub()
    c = _conn(1, sa=True)
    hub._conns.add(c)
    hub.dispatch("rt:global", "not json")
    assert c.queue.qsize() == 0
