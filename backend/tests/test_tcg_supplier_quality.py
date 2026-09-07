"""
PARITY-03 第2段階: 仕入元品質サマリー API テスト。

カバー:
  - GET /api/v1/tcg/supplier-quality-summaries  認証なし -> 401/403
  - GET /api/v1/tcg/suppliers/{id}/source       認証なし -> 401/403
  - サービス層モックで正常系レスポンス形状を検証
  - source 起点（items=0 の仕入元も含む）の構造確認
"""
from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

pytestmark = pytest.mark.asyncio

_DUMMY_SUMMARIES = [
    {
        "supplier_id": "SP0001",
        "supplier_name": "仕入元A",
        "analysis_count": 10,
        "needs_review_count": 3,
        "product_id_unresolved_count": 2,
        "unit_unresolved_count": 1,
        "condition_fallback_count": None,
    },
    # items=0 の仕入元（SP0057/Hiroshi 相当）
    {
        "supplier_id": "SP0057",
        "supplier_name": "Hiroshi",
        "analysis_count": 0,
        "needs_review_count": 0,
        "product_id_unresolved_count": 0,
        "unit_unresolved_count": 0,
        "condition_fallback_count": None,
    },
]

_DUMMY_SOURCE = {
    "ok": True,
    "found": True,
    "source_message_id": "bbbbbbbb-0000-0000-0000-000000000001",
    "supplier_id": "SP0001",
    "supplier_name": "仕入元A",
    "raw_text": "ポケモンカード SV1a 1BOX 5000円",
}


# ---------------------------------------------------------------------------
# 認証なし -> 401/403
# ---------------------------------------------------------------------------


async def test_supplier_quality_summaries_requires_auth():
    from app.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/v1/tcg/supplier-quality-summaries")
    assert resp.status_code in (401, 403), resp.text


async def test_supplier_source_requires_auth():
    from app.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/v1/tcg/suppliers/SP0001/source")
    assert resp.status_code in (401, 403), resp.text


# ---------------------------------------------------------------------------
# フィクスチャ
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_super_admin_override():
    from app.main import app
    from app.auth.dependencies import require_super_admin

    async def _bypass():
        return {"id": 1, "is_super_admin": True}

    app.dependency_overrides[require_super_admin] = _bypass
    yield
    app.dependency_overrides.pop(require_super_admin, None)


# ---------------------------------------------------------------------------
# 正常系
# ---------------------------------------------------------------------------


async def test_supplier_quality_summaries_response_shape(fake_super_admin_override):
    from app.main import app

    with patch(
        "app.routers.tcg_supplier_quality.fetch_supplier_quality_summaries",
        new=AsyncMock(return_value=_DUMMY_SUMMARIES),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/tcg/supplier-quality-summaries")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ok"] is True
    assert "summaries" in body
    assert len(body["summaries"]) == 2
    s = body["summaries"][0]
    for key in (
        "supplier_id",
        "supplier_name",
        "analysis_count",
        "needs_review_count",
        "product_id_unresolved_count",
        "unit_unresolved_count",
        "condition_fallback_count",
    ):
        assert key in s, f"{key} missing"


async def test_zero_items_supplier_included(fake_super_admin_override):
    """items=0 の仕入元（SP0057/Hiroshi）がサマリーに含まれること。"""
    from app.main import app

    with patch(
        "app.routers.tcg_supplier_quality.fetch_supplier_quality_summaries",
        new=AsyncMock(return_value=_DUMMY_SUMMARIES),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/tcg/supplier-quality-summaries")
    body = resp.json()
    supplier_ids = [s["supplier_id"] for s in body["summaries"]]
    assert "SP0057" in supplier_ids, "SP0057 (items=0) がサマリーに含まれていない"
    hiroshi = next(s for s in body["summaries"] if s["supplier_id"] == "SP0057")
    assert hiroshi["analysis_count"] == 0


async def test_supplier_source_response_shape(fake_super_admin_override):
    from app.main import app

    with patch(
        "app.routers.tcg_supplier_quality.fetch_supplier_source",
        new=AsyncMock(return_value=_DUMMY_SOURCE),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/tcg/suppliers/SP0001/source")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    for key in (
        "ok",
        "found",
        "source_message_id",
        "supplier_id",
        "supplier_name",
        "raw_text",
    ):
        assert key in body, f"{key} missing"
    assert body["found"] is True
