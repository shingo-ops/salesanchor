"""接続元 IP を決める唯一の関数 get_client_ip の試験（S5・docs/specs/client-ip/README.md）。

DB 不要。Redis は app.cache._redis にメモリ上の FakeRedis を差す。
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict = {}
        self.ttls: dict = {}

    async def get(self, key):
        return self.store.get(key)

    async def exists(self, key):
        return 1 if key in self.store else 0

    async def incr(self, key):
        self.store[key] = int(self.store.get(key, 0)) + 1
        return self.store[key]

    async def expire(self, key, ttl):
        self.ttls[key] = ttl

    async def delete(self, key):
        self.store.pop(key, None)


async def test_t5_xff_rotation_does_not_evade_auth_lockout(monkeypatch):
    """T5(K2): X-Real-IP 固定・X-Forwarded-For 毎回別でも 11 回目は 429。"""
    from app.auth.dependencies import get_current_user
    from app.database import get_db

    fake = FakeRedis()
    monkeypatch.setattr("app.cache._redis", fake)

    app = FastAPI()

    @app.get("/api/protected")
    async def protected(user=Depends(get_current_user)):
        return {"ok": True}

    async def _no_db():
        yield AsyncMock()

    app.dependency_overrides[get_db] = _no_db

    statuses = []
    with patch("app.auth.dependencies._init_firebase"), patch(
        "firebase_admin.auth.verify_id_token", side_effect=Exception("invalid token")
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            for i in range(11):
                resp = await client.get(
                    "/api/protected",
                    headers={
                        "Authorization": "Bearer invalid-firebase-token",
                        "X-Real-IP": "10.3.0.1",
                        "X-Forwarded-For": f"6.6.{i}.{i + 1}",
                    },
                )
                statuses.append(resp.status_code)

    assert statuses[:10] == [401] * 10, statuses
    assert statuses[10] == 429, statuses


def _req(headers: dict, client):
    from starlette.requests import Request

    scope = {
        "type": "http",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        "client": client,
    }
    return Request(scope)


def test_t1_x_real_ip_wins_over_xff():
    from app.client_ip import get_client_ip

    req = _req({"X-Real-IP": "10.3.0.1", "X-Forwarded-For": "6.6.6.6"}, ("192.0.2.5", 1))
    assert get_client_ip(req) == "10.3.0.1"


def test_t2_xff_is_never_read():
    from app.client_ip import get_client_ip

    req = _req({"X-Forwarded-For": "6.6.6.6"}, ("192.0.2.5", 1))
    assert get_client_ip(req) == "192.0.2.5"


@pytest.mark.parametrize("bad", ["evil", "1" * 60])
def test_t3_invalid_x_real_ip_falls_back_to_client_host(bad):
    from app.client_ip import get_client_ip

    req = _req({"X-Real-IP": bad}, ("192.0.2.5", 1))
    assert get_client_ip(req) == "192.0.2.5"


def test_t4_no_header_no_client_is_unknown():
    from app.client_ip import get_client_ip

    assert get_client_ip(_req({}, None)) == "unknown"


async def test_t6_audit_records_x_real_ip_not_xff():
    """T6: 監査記録の client_ip は X-Real-IP の値（X-Forwarded-For は無視）。"""
    from app.middleware.audit import AuditMiddleware

    captured: list = []

    class _FakeDb:
        async def execute(self, stmt, params=None):
            captured.append(params)

        async def commit(self):
            pass

    class _FakeSession:
        async def __aenter__(self):
            return _FakeDb()

        async def __aexit__(self, *exc):
            return False

    app = FastAPI()
    app.add_middleware(AuditMiddleware)

    @app.post("/api/v1/auth/x")
    async def auth_x():
        return {"ok": True}

    with patch("app.middleware.audit.AsyncSessionLocal", lambda: _FakeSession()):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/x",
                headers={"X-Real-IP": "10.3.0.1", "X-Forwarded-For": "203.0.113.77"},
            )
        # 記録は応答後のバックグラウンドタスクの場合に備えて少し待つ
        import asyncio

        for _ in range(20):
            if captured:
                break
            await asyncio.sleep(0.05)

    assert resp.status_code == 200
    assert captured, "監査記録の INSERT が呼ばれていない"
    assert all(p["client_ip"] == "10.3.0.1" for p in captured), captured
