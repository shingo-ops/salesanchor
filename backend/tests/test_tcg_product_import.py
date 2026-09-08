"""IMPORT-01: 商品マスタ CSV 取り込み API テスト。"""
from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
pytestmark = pytest.mark.asyncio

_HEADER = (
    "mark,japanese_title,english_title,release_date,"
    "search_keywords,exclude_keywords,"
    "division_code,work_code,manufacturer_code,product_category_code\n"
)
_ROW = "FB09,DUAL EVOLUTION,Dual Evolution,2026-03-14,DE,,DIV01,IP003,MK002,PC_BOX\n"
_CSV = (_HEADER + _ROW).encode("utf-8")
_PREVIEW = {"filename": "sample.csv", "digest": "d" * 64, "file_errors": [], "total": 1, "ok": 1, "blocked": 0, "rows": [{"row_no": "1", "japanese_title": "DUAL EVOLUTION", "mark": "FB09", "blocking": [], "warnings": []}]}


async def _client():
    from app.main import app
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_preview_requires_auth():
    async with await _client() as client:
        res = await client.post("/api/v1/tcg/products/import/preview", files={"file": ("sample.csv", _CSV, "text/csv")})
    assert res.status_code in (401, 403)


async def test_commit_requires_auth():
    async with await _client() as client:
        res = await client.post("/api/v1/tcg/products/import/commit", files={"file": ("sample.csv", _CSV, "text/csv")}, data={"confirmed_digest": "d" * 64})
    assert res.status_code in (401, 403)


async def test_list_requires_auth():
    async with await _client() as client:
        res = await client.get("/api/v1/tcg/products/list")
    assert res.status_code in (401, 403)


@patch("app.routers.tcg_product_import.preview", new_callable=AsyncMock)
async def test_preview_returns_rows(mock_preview):
    mock_preview.return_value = _PREVIEW
    from app.auth.dependencies import require_super_admin
    from app.database import get_db
    from app.main import app
    app.dependency_overrides[require_super_admin] = lambda: {"email": "po@example.com"}
    app.dependency_overrides[get_db] = lambda: None
    try:
        async with await _client() as client:
            res = await client.post("/api/v1/tcg/products/import/preview", files={"file": ("sample.csv", _CSV, "text/csv")})
        assert res.status_code == 200
        assert res.json()["total"] == 1
        assert res.json()["blocked"] == 0
    finally:
        app.dependency_overrides.clear()


@patch("app.routers.tcg_product_import.preview", new_callable=AsyncMock)
async def test_commit_rejects_digest_mismatch(mock_preview):
    mock_preview.return_value = _PREVIEW
    from app.auth.dependencies import require_super_admin
    from app.database import get_db
    from app.main import app
    app.dependency_overrides[require_super_admin] = lambda: {"email": "po@example.com"}
    app.dependency_overrides[get_db] = lambda: None
    try:
        async with await _client() as client:
            res = await client.post("/api/v1/tcg/products/import/commit", files={"file": ("sample.csv", _CSV, "text/csv")}, data={"confirmed_digest": "x" * 64})
        assert res.status_code == 409
    finally:
        app.dependency_overrides.clear()


async def test_preview_rejects_non_csv():
    from app.auth.dependencies import require_super_admin
    from app.database import get_db
    from app.main import app
    app.dependency_overrides[require_super_admin] = lambda: {"email": "po@example.com"}
    app.dependency_overrides[get_db] = lambda: None
    try:
        async with await _client() as client:
            res = await client.post("/api/v1/tcg/products/import/preview", files={"file": ("sample.txt", _CSV, "text/plain")})
        assert res.status_code == 422
    finally:
        app.dependency_overrides.clear()
