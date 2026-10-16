"""S6: 全件取得・ファイル出力の GET 記録と閲覧の大量検知の試験（docs/specs/get-access-audit/）。

DB 不要。AsyncSessionLocal と Redis は差し替える。
"""

from __future__ import annotations

import asyncio
import base64
import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from httpx import ASGITransport, AsyncClient

_EXPORT_PATHS = [
    "/api/v1/financials/orders",
    "/api/v1/companies/duplicates",
    "/api/v1/conditions/export",
    "/api/v1/note-master/export",
    "/api/v1/product-categories/export",
    "/api/v1/status-master/export",
    "/api/v1/suppliers/export",
    "/api/v1/units/export",
    "/api/v1/super-admin/aliases/export",
    "/api/v1/super-admin/conditions/export",
    "/api/v1/super-admin/knowledge/export",
    "/api/v1/super-admin/note-master/export",
    "/api/v1/super-admin/product-categories/export",
    "/api/v1/super-admin/status-master/export",
    "/api/v1/super-admin/suppliers/export",
    "/api/v1/super-admin/units/export",
    "/api/v1/tcg/products/export",
    "/api/v1/tcg/review/csv/export",
    "/api/v1/shipping/elogi-csv",
    "/api/v1/orders/123/shipping/elogi-csv",
    "/api/v1/reports/task-abc/download",
]

_NOT_EXPORT = [
    ("GET", "/api/v1/companies"),
    ("GET", "/api/v1/leads/55/attachments/9"),
    ("GET", "/api/v1/leads/stream"),
    ("GET", "/api/v1/public/staff/avatar"),
    ("GET", "/api/v1/realtime/events"),
    ("POST", "/api/v1/suppliers/export"),
]


def _jwt(email: str) -> str:
    def b64(d: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(d).encode()).decode().rstrip("=")

    return f"{b64({'alg': 'none'})}.{b64({'email': email})}.sig"


def _fake_session(captured: list):
    class _Db:
        async def execute(self, stmt, params=None):
            captured.append(params)

        async def commit(self):
            pass

    class _Session:
        async def __aenter__(self):
            return _Db()

        async def __aexit__(self, *exc):
            return False

    return lambda: _Session()


def _app() -> FastAPI:
    from app.middleware.audit import AuditMiddleware

    app = FastAPI()
    app.add_middleware(AuditMiddleware)

    @app.get("/api/v1/suppliers/export")
    async def export_ok():
        return {"ok": True}

    @app.get("/api/v1/units/export")
    async def export_forbidden():
        return JSONResponse({"detail": "forbidden"}, status_code=403)

    @app.get("/api/v1/companies")
    async def companies():
        return {"ok": True}

    return app


async def _get(path: str, captured: list, redis) -> int:
    transport = ASGITransport(app=_app())
    headers = {"Authorization": f"Bearer {_jwt('user@example.com')}"}
    with patch("app.middleware.audit.AsyncSessionLocal", _fake_session(captured)), \
            patch("app.cache._redis", redis):
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.get(path, headers=headers)
        for _ in range(5):
            await asyncio.sleep(0.02)
    return resp.status_code


# T1
@pytest.mark.parametrize("path", _EXPORT_PATHS)
def test_t1_export_paths_are_recorded(path):
    from app.middleware.audit import _is_export_get

    assert _is_export_get("GET", path) is True


@pytest.mark.parametrize("method,path", _NOT_EXPORT)
def test_t1_non_export_paths_are_not_recorded(method, path):
    from app.middleware.audit import _is_export_get

    assert _is_export_get(method, path) is False


# T2
async def test_t2_export_get_records_data_export():
    captured: list = []
    status = await _get("/api/v1/suppliers/export", captured, None)
    assert status == 200
    assert len(captured) == 1, captured
    p = captured[0]
    assert p["event_type"] == "data_export"
    assert p["method"] == "GET"
    assert p["path"] == "/api/v1/suppliers/export"
    assert p["user_email"] == "user@example.com"


async def test_t2_export_get_403_not_recorded():
    captured: list = []
    status = await _get("/api/v1/units/export", captured, None)
    assert status == 403
    assert not [p for p in captured if p and p.get("event_type") == "data_export"]


async def test_t2_plain_get_no_insert():
    captured: list = []
    status = await _get("/api/v1/companies", captured, None)
    assert status == 200
    assert captured == []


# T3
class TestCountReadAndCheck:
    async def _run(self, incr_value, email="user@example.com"):
        from app.middleware.audit import _count_read_and_check

        r = AsyncMock()
        r.incr = AsyncMock(return_value=incr_value)
        r.expire = AsyncMock()
        with patch("app.cache._redis", r):
            result = await _count_read_and_check(email)
        return result, r

    async def test_500_false(self):
        assert (await self._run(500))[0] is False

    async def test_501_true(self):
        assert (await self._run(501))[0] is True

    async def test_502_false(self):
        assert (await self._run(502))[0] is False

    async def test_no_email_does_not_incr(self):
        result, r = await self._run(501, email=None)
        assert result is False
        r.incr.assert_not_called()

    async def test_redis_down_fail_open(self):
        from app.middleware.audit import _count_read_and_check

        with patch("app.cache._redis", None):
            assert await _count_read_and_check("user@example.com") is False

    async def test_first_call_sets_ttl_and_key_prefix(self):
        from app.middleware.audit import BULK_EXPORT_WINDOW_SEC

        _, r = await self._run(1)
        r.expire.assert_called_once()
        key, ttl = r.expire.call_args[0]
        assert ttl == BULK_EXPORT_WINDOW_SEC + 60
        assert key.startswith("bulk_read:")
        assert not key.startswith("bulk_access:")


# T4
async def test_t4_bulk_read_alert_recorded():
    r = AsyncMock()
    r.incr = AsyncMock(return_value=501)
    r.expire = AsyncMock()
    captured: list = []
    status = await _get("/api/v1/companies", captured, r)
    assert status == 200
    assert len(captured) == 1, captured
    assert captured[0]["event_type"] == "bulk_read_alert"
