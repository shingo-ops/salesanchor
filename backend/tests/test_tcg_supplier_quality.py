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
        "supplierId": "SP0001",
        "supplierName": "仕入元A",
        "analysisCount": 10,
        "needsReviewCount": 3,
        "productIdUnresolvedCount": 2,
        "unitUnresolvedCount": 1,
        "conditionFallbackCount": None,
    },
    # items=0 の仕入元（SP0057/Hiroshi 相当）
    {
        "supplierId": "SP0057",
        "supplierName": "Hiroshi",
        "analysisCount": 0,
        "needsReviewCount": 0,
        "productIdUnresolvedCount": 0,
        "unitUnresolvedCount": 0,
        "conditionFallbackCount": None,
    },
]

_DUMMY_SOURCE = {
    "ok": True,
    "found": True,
    "sourceMessageId": "bbbbbbbb-0000-0000-0000-000000000001",
    "supplierId": "SP0001",
    "supplierName": "仕入元A",
    "rawText": "ポケモンカード SV1a 1BOX 5000円",
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
        "supplierId",
        "supplierName",
        "analysisCount",
        "needsReviewCount",
        "productIdUnresolvedCount",
        "unitUnresolvedCount",
        "conditionFallbackCount",
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
    supplier_ids = [s["supplierId"] for s in body["summaries"]]
    assert "SP0057" in supplier_ids, "SP0057 (items=0) がサマリーに含まれていない"
    hiroshi = next(s for s in body["summaries"] if s["supplierId"] == "SP0057")
    assert hiroshi["analysisCount"] == 0


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
        "sourceMessageId",
        "supplierId",
        "supplierName",
        "rawText",
    ):
        assert key in body, f"{key} missing"
    assert body["found"] is True
