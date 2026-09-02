"""
PARITY-03 第1段階: 解析レビュー API テスト。

カバー:
  - GET /api/v1/tcg/analysis-results         認証なし -> 401/403
  - サービス層モックで正常系レスポンス形状を検証
"""
from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

pytestmark = pytest.mark.asyncio

# ---------------------------------------------------------------------------
# ダミーレスポンス（サービス層の戻り値形状）
# ---------------------------------------------------------------------------

_DUMMY_ITEM = {
    "extraction_item_id": "aaaaaaaa-0000-0000-0000-000000000001",
    "source_message_id": "bbbbbbbb-0000-0000-0000-000000000001",
    "provider": "仕入元A",
    "raw_text": "ポケモンカード SV1a 1BOX",
    "gemini": {
        "name": "SV1a",
        "quantity": "1",
        "price": "5000",
        "unit": "BOX",
        "state": "新品",
        "memo": "",
        "span": "L1-1",
    },
    "system": {
        "product_id": "PM0001",
        "pid_resolved": "YES",
        "pid_basis": "EXACT",
        "unit": "BOX",
        "unit_resolved": "YES",
        "condition": "NEW",
        "status": "ACTIVE",
        "note": "",
        "exclusion": "",
    },
    "review_issues": [],
}

_DUMMY_FETCH_RESULT = {
    "items": [_DUMMY_ITEM],
    "total": 1,
    "item_total": 1,
    "offset": 0,
    "limit": 10,
    "providers": ["仕入元A"],
}


# ---------------------------------------------------------------------------
# 認証なし -> 401/403
# ---------------------------------------------------------------------------


async def test_list_analysis_results_requires_auth():
    """認証ヘッダーなしで GET /tcg/analysis-results -> 401 or 403。"""
    from app.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/v1/tcg/analysis-results")
    assert resp.status_code in (401, 403), resp.text


# ---------------------------------------------------------------------------
# サービス層をモックして正常系のレスポンス形状を検証
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_super_admin_override():
    """require_super_admin を bypass するフィクスチャ。"""
    from app.main import app
    from app.auth.dependencies import require_super_admin

    async def _bypass():
        return {"id": 1, "is_super_admin": True}

    app.dependency_overrides[require_super_admin] = _bypass
    yield
    app.dependency_overrides.pop(require_super_admin, None)


async def test_list_analysis_results_response_shape(fake_super_admin_override):
    """サービスをモックし、レスポンス JSON の形状が AnalysisResultsResponse と一致。"""
    from app.main import app

    with patch(
        "app.routers.tcg_analysis_review.fetch_analysis_results",
        new=AsyncMock(return_value=_DUMMY_FETCH_RESULT),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/tcg/analysis-results")

    assert resp.status_code == 200, resp.text
    body = resp.json()

    # トップレベルキー
    assert "items" in body
    assert "total" in body
    assert "item_total" in body
    assert "offset" in body
    assert "limit" in body
    assert "providers" in body

    # items[0] 構造
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert "extraction_item_id" in item
    assert "gemini" in item
    assert "system" in item
    assert "review_issues" in item

    gemini = item["gemini"]
    for f in ("name", "quantity", "price", "unit", "state", "memo", "span"):
        assert f in gemini, f"gemini.{f} missing"

    system = item["system"]
    for f in ("product_id", "pid_resolved", "pid_basis", "unit",
              "unit_resolved", "condition", "status", "note", "exclusion"):
        assert f in system, f"system.{f} missing"


async def test_status_tab_invalid_falls_back_to_all(fake_super_admin_override):
    """status_tab に不正値を渡すと ALL にフォールバックして 200 を返す。"""
    from app.main import app

    with patch(
        "app.routers.tcg_analysis_review.fetch_analysis_results",
        new=AsyncMock(return_value=_DUMMY_FETCH_RESULT),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/v1/tcg/analysis-results?status_tab=INVALID_VALUE"
            )

    assert resp.status_code == 200, resp.text
