"""
DB-A2: TCG 診断 API テスト。

カバー:
  - 認証なし → 401/403
  - 未知のキー → 400（許可キー一覧をエラーメッセージに含む）
  - 8つの許可キーそれぞれ → 200 + 想定形状の JSON
"""
from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

pytestmark = pytest.mark.asyncio

# ---------------------------------------------------------------------------
# テスト用の mock 返却データ
# ---------------------------------------------------------------------------

_SUPPLIERS_ROWS = [
    {"code": "SP0001", "name": "仕入元A", "is_active": True},
    {"code": "SP0002", "name": "仕入元B", "is_active": False},
]

_SUPPLIER_NAME_DUPES_ROWS = [
    {"name_lower": "duplicate supplier", "cnt": 2},
]

_SUPPLIER_CHANNELS_ROWS = [
    {"supplier_code": "SP0001", "supplier_name": "仕入元A", "channel_count": 3},
]

_ORPHAN_MESSAGES_ROWS = [
    {"null_channel_count": 5},
]

_EXTRACTION_ERRORS_ROWS = [
    {
        "id": "ej-uuid-001",
        "source_message_id": "sm-uuid-001",
        "error_message": "Gemini API timeout",
        "prompt_version": "v1.0",
        "created_at": "2026-09-01T10:00:00Z",
    },
]

_EXTRACTION_PENDING_ROWS = [
    {
        "id": "ej-uuid-002",
        "source_message_id": "sm-uuid-002",
        "created_at": "2026-09-01T11:00:00Z",
    },
]

_EXTRACTION_RUNNING_STALE_ROWS = [
    {
        "id": "ej-uuid-003",
        "source_message_id": "sm-uuid-003",
        "created_at": "2026-09-01T09:00:00Z",
        "age_minutes": 65,
    },
]

_ANALYSIS_MISSING_ROWS = [
    {
        "extraction_job_id": "ej-uuid-004",
        "source_message_id": "sm-uuid-004",
        "item_count": 3,
        "extracted_at": "2026-09-01T12:00:00Z",
    },
]

_KEY_MOCK_MAP = {
    "suppliers": _SUPPLIERS_ROWS,
    "supplier-name-dupes": _SUPPLIER_NAME_DUPES_ROWS,
    "supplier-channels": _SUPPLIER_CHANNELS_ROWS,
    "orphan-messages": _ORPHAN_MESSAGES_ROWS,
    "extraction-errors": _EXTRACTION_ERRORS_ROWS,
    "extraction-pending": _EXTRACTION_PENDING_ROWS,
    "extraction-running-stale": _EXTRACTION_RUNNING_STALE_ROWS,
    "analysis-missing": _ANALYSIS_MISSING_ROWS,
}

# ---------------------------------------------------------------------------
# 共通フィクスチャ
# ---------------------------------------------------------------------------


@pytest.fixture
def super_admin_override():
    from app.main import app
    from app.auth.dependencies import require_super_admin

    async def _bypass():
        return {"id": 1, "is_super_admin": True}

    app.dependency_overrides[require_super_admin] = _bypass
    yield
    app.dependency_overrides.pop(require_super_admin, None)


# ---------------------------------------------------------------------------
# 認証テスト
# ---------------------------------------------------------------------------


async def test_diagnostics_requires_auth():
    """認証なしで 401/403 が返ること。"""
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/api/v1/tcg/diagnostics/suppliers")
    assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# 未知キー → 400
# ---------------------------------------------------------------------------


async def test_unknown_key_returns_400(super_admin_override):
    """許可リスト外のキーは 400 を返し、許可キー一覧をエラーに含む。"""
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/api/v1/tcg/diagnostics/unknown-key")

    assert r.status_code == 400
    body = r.json()
    detail = body.get("detail", "")
    # 許可キーの一覧がエラーメッセージに含まれていること
    for key in (
        "suppliers",
        "supplier-name-dupes",
        "supplier-channels",
        "orphan-messages",
        "extraction-errors",
        "extraction-pending",
        "extraction-running-stale",
        "analysis-missing",
    ):
        assert key in detail, f"Expected '{key}' in error detail: {detail}"


# ---------------------------------------------------------------------------
# 許可キー → 200 + 形状検証
# ---------------------------------------------------------------------------


async def test_suppliers_returns_200(super_admin_override):
    """`suppliers` キーが 200 を返し、code/name/is_active を持つ行リストになること。"""
    from app.main import app

    with patch(
        "app.routers.tcg_diagnostics.run_diagnostic",
        new=AsyncMock(return_value=_SUPPLIERS_ROWS),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get("/api/v1/tcg/diagnostics/suppliers")

    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["key"] == "suppliers"
    assert isinstance(body["rows"], list)
    assert len(body["rows"]) == 2
    assert body["rows"][0]["code"] == "SP0001"
    assert "name" in body["rows"][0]
    assert "is_active" in body["rows"][0]


async def test_supplier_name_dupes_returns_200(super_admin_override):
    """`supplier-name-dupes` キーが 200 を返し、name_lower/cnt を持つ行リストになること。"""
    from app.main import app

    with patch(
        "app.routers.tcg_diagnostics.run_diagnostic",
        new=AsyncMock(return_value=_SUPPLIER_NAME_DUPES_ROWS),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get("/api/v1/tcg/diagnostics/supplier-name-dupes")

    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["key"] == "supplier-name-dupes"
    assert len(body["rows"]) == 1
    assert body["rows"][0]["name_lower"] == "duplicate supplier"
    assert body["rows"][0]["cnt"] == 2


async def test_supplier_channels_returns_200(super_admin_override):
    """`supplier-channels` キーが 200 を返し、supplier_code/supplier_name/channel_count を持つこと。"""
    from app.main import app

    with patch(
        "app.routers.tcg_diagnostics.run_diagnostic",
        new=AsyncMock(return_value=_SUPPLIER_CHANNELS_ROWS),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get("/api/v1/tcg/diagnostics/supplier-channels")

    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["key"] == "supplier-channels"
    assert len(body["rows"]) == 1
    assert body["rows"][0]["supplier_code"] == "SP0001"
    assert body["rows"][0]["channel_count"] == 3


async def test_orphan_messages_returns_200(super_admin_override):
    """`orphan-messages` キーが 200 を返し、null_channel_count を持つ行リストになること。"""
    from app.main import app

    with patch(
        "app.routers.tcg_diagnostics.run_diagnostic",
        new=AsyncMock(return_value=_ORPHAN_MESSAGES_ROWS),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get("/api/v1/tcg/diagnostics/orphan-messages")

    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["key"] == "orphan-messages"
    assert len(body["rows"]) == 1
    assert body["rows"][0]["null_channel_count"] == 5


async def test_extraction_errors_returns_200(super_admin_override):
    """`extraction-errors` キーが 200 を返し、id/source_message_id/error_message/prompt_version/created_at を持つこと。"""
    from app.main import app

    with patch(
        "app.routers.tcg_diagnostics.run_diagnostic",
        new=AsyncMock(return_value=_EXTRACTION_ERRORS_ROWS),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get("/api/v1/tcg/diagnostics/extraction-errors")

    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["key"] == "extraction-errors"
    assert len(body["rows"]) == 1
    assert body["rows"][0]["error_message"] == "Gemini API timeout"
    assert "prompt_version" in body["rows"][0]
    assert "source_message_id" in body["rows"][0]


async def test_extraction_pending_returns_200(super_admin_override):
    """`extraction-pending` キーが 200 を返し、id/source_message_id/created_at を持つこと。"""
    from app.main import app

    with patch(
        "app.routers.tcg_diagnostics.run_diagnostic",
        new=AsyncMock(return_value=_EXTRACTION_PENDING_ROWS),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get("/api/v1/tcg/diagnostics/extraction-pending")

    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["key"] == "extraction-pending"
    assert len(body["rows"]) == 1
    assert "source_message_id" in body["rows"][0]
    assert "created_at" in body["rows"][0]


async def test_extraction_running_stale_returns_200(super_admin_override):
    """`extraction-running-stale` キーが 200 を返し、id/source_message_id/created_at/age_minutes を持つこと。"""
    from app.main import app

    with patch(
        "app.routers.tcg_diagnostics.run_diagnostic",
        new=AsyncMock(return_value=_EXTRACTION_RUNNING_STALE_ROWS),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get("/api/v1/tcg/diagnostics/extraction-running-stale")

    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["key"] == "extraction-running-stale"
    assert len(body["rows"]) == 1
    assert body["rows"][0]["age_minutes"] == 65
    assert "source_message_id" in body["rows"][0]


async def test_analysis_missing_returns_200(super_admin_override):
    """`analysis-missing` キーが 200 を返し、extraction_job_id/source_message_id/item_count/extracted_at を持つこと。"""
    from app.main import app

    with patch(
        "app.routers.tcg_diagnostics.run_diagnostic",
        new=AsyncMock(return_value=_ANALYSIS_MISSING_ROWS),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get("/api/v1/tcg/diagnostics/analysis-missing")

    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["key"] == "analysis-missing"
    assert len(body["rows"]) == 1
    assert body["rows"][0]["item_count"] == 3
    assert "extraction_job_id" in body["rows"][0]
    assert "extracted_at" in body["rows"][0]
