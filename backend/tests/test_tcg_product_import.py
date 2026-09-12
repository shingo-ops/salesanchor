"""IMPORT-01: 商品マスタ CSV 取り込み API テスト。"""
from __future__ import annotations

import os
from contextlib import contextmanager
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


@patch("app.routers.tcg_product_import.commit_import", new_callable=AsyncMock)
async def test_preview_requires_auth(mock_commit):
    async with await _client() as client:
        res = await client.post("/api/v1/tcg/products/import/preview", files={"file": ("sample.csv", _CSV, "text/csv")})
    assert res.status_code in (401, 403)
    mock_commit.assert_not_awaited()


@patch("app.routers.tcg_product_import.commit_import", new_callable=AsyncMock)
async def test_commit_requires_auth(mock_commit):
    async with await _client() as client:
        res = await client.post("/api/v1/tcg/products/import/commit", files={"file": ("sample.csv", _CSV, "text/csv")}, data={"confirmed_digest": "d" * 64})
    assert res.status_code in (401, 403)
    mock_commit.assert_not_awaited()


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
    from app.models import User
    original_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[require_super_admin] = lambda: User(id=1, email="qa@example.com", is_super_admin=True)
    app.dependency_overrides[get_db] = lambda: None
    try:
        async with await _client() as client:
            res = await client.post("/api/v1/tcg/products/import/preview", files={"file": ("sample.csv", _CSV, "text/csv")})
        assert res.status_code == 200
        assert res.json()["total"] == 1
        assert res.json()["blocked"] == 0
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original_overrides)


@patch("app.routers.tcg_product_import.commit_import", new_callable=AsyncMock)
@patch("app.routers.tcg_product_import.preview", new_callable=AsyncMock)
async def test_commit_rejects_digest_mismatch(mock_preview, mock_commit):
    mock_preview.return_value = _PREVIEW
    from app.auth.dependencies import require_super_admin
    from app.database import get_db
    from app.main import app
    from app.models import User
    original_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[require_super_admin] = lambda: User(id=1, email="qa@example.com", is_super_admin=True)
    app.dependency_overrides[get_db] = lambda: None
    try:
        async with await _client() as client:
            res = await client.post("/api/v1/tcg/products/import/commit", files={"file": ("sample.csv", _CSV, "text/csv")}, data={"confirmed_digest": "x" * 64})
        assert res.status_code == 409
        mock_commit.assert_not_awaited()
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original_overrides)


async def test_preview_rejects_non_csv():
    from app.auth.dependencies import require_super_admin
    from app.database import get_db
    from app.main import app
    from app.models import User
    original_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[require_super_admin] = lambda: User(id=1, email="qa@example.com", is_super_admin=True)
    app.dependency_overrides[get_db] = lambda: None
    try:
        async with await _client() as client:
            res = await client.post("/api/v1/tcg/products/import/preview", files={"file": ("sample.txt", _CSV, "text/plain")})
        assert res.status_code == 422
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original_overrides)


@contextmanager
def _user_dependencies(user):
    """Keep the real authorization dependency and restore every prior override."""
    from app.auth.dependencies import get_current_user, require_super_admin
    from app.database import get_db
    from app.main import app

    original = app.dependency_overrides.copy()
    app.dependency_overrides.pop(require_super_admin, None)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: None
    try:
        yield
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original)


@pytest.mark.parametrize(
    ("email", "user_id", "executed_by"),
    [("qa@example.com", 1, "qa@example.com"), ("", 1, "1"), ("", None, "")],
)
@patch("app.routers.tcg_product_import.commit_import", new_callable=AsyncMock)
@patch("app.routers.tcg_product_import.preview", new_callable=AsyncMock)
async def test_commit_with_real_user(mock_preview, mock_commit, email, user_id, executed_by):
    from app.models import User

    mock_preview.return_value = _PREVIEW
    result = {"job_id": "receipt", "filename": "sample.csv", "total": 1, "created": 1, "skipped": 0}
    mock_commit.return_value = result
    with _user_dependencies(User(id=user_id, email=email, is_super_admin=True)):
        async with await _client() as client:
            res = await client.post(
                "/api/v1/tcg/products/import/commit",
                files={"file": ("sample.csv", _CSV, "text/csv")},
                data={"confirmed_digest": _PREVIEW["digest"]},
            )
        assert res.status_code == 200
        assert res.json() == result
        mock_preview.assert_awaited_once_with(None, _CSV, "sample.csv")
        mock_commit.assert_awaited_once_with(None, _CSV, "sample.csv", executed_by)


@pytest.mark.parametrize("endpoint", ["preview", "commit"])
@patch("app.routers.tcg_product_import.commit_import", new_callable=AsyncMock)
@patch("app.routers.tcg_product_import.preview", new_callable=AsyncMock)
async def test_non_admin_is_rejected_by_real_dependency(mock_preview, mock_commit, endpoint):
    from app.models import User

    with _user_dependencies(User(id=1, email="qa@example.com", is_super_admin=False)):
        async with await _client() as client:
            res = await client.post(
                "/api/v1/tcg/products/import/" + endpoint,
                files={"file": ("sample.csv", _CSV, "text/csv")},
                data={"confirmed_digest": _PREVIEW["digest"]},
            )
        assert res.status_code == 403
        mock_preview.assert_not_awaited()
        mock_commit.assert_not_awaited()


@pytest.mark.parametrize(
    ("filename", "raw", "detail"),
    [
        ("sample.txt", _CSV, "PRODUCT_IMPORT_NOT_CSV"),
        ("sample.csv", b"", "PRODUCT_IMPORT_EMPTY_FILE"),
        ("sample.csv", b"\xff", "PRODUCT_IMPORT_NOT_UTF8"),
    ],
)
@patch("app.routers.tcg_product_import.commit_import", new_callable=AsyncMock)
@patch("app.routers.tcg_product_import.preview", new_callable=AsyncMock)
async def test_commit_rejects_invalid_file(mock_preview, mock_commit, filename, raw, detail):
    from app.models import User

    with _user_dependencies(User(id=1, email="qa@example.com", is_super_admin=True)):
        async with await _client() as client:
            res = await client.post(
                "/api/v1/tcg/products/import/commit",
                files={"file": (filename, raw, "text/csv")},
                data={"confirmed_digest": _PREVIEW["digest"]},
            )
        assert res.status_code == 422
        assert res.json()["detail"] == detail
        mock_preview.assert_not_awaited()
        mock_commit.assert_not_awaited()


@patch("app.routers.tcg_product_import.commit_import", new_callable=AsyncMock)
@patch("app.routers.tcg_product_import.preview", new_callable=AsyncMock)
async def test_commit_rejects_file_errors(mock_preview, mock_commit):
    from app.models import User

    mock_preview.return_value = {**_PREVIEW, "file_errors": ["CSV_COLUMN_MISMATCH"]}
    with _user_dependencies(User(id=1, email="qa@example.com", is_super_admin=True)):
        async with await _client() as client:
            res = await client.post(
                "/api/v1/tcg/products/import/commit",
                files={"file": ("sample.csv", _CSV, "text/csv")},
                data={"confirmed_digest": _PREVIEW["digest"]},
            )
        assert res.status_code == 422
        assert res.json()["detail"] == ["CSV_COLUMN_MISMATCH"]
        mock_commit.assert_not_awaited()
