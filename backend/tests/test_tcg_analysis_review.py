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
        "condition_basis": "MANUAL_CONDITION_REVIEW",
        "unit": "BOX",
        "unit_resolved": "YES",
        "condition": "NEW",
        "status": "ACTIVE",
        "note": "",
        "exclusion": "",
    },
    "review_issues": [],
    "review_reason_details": [{"code": "pid_unresolved", "source": "system", "fix_stage": "analysis"}],
}

_DUMMY_FETCH_RESULT = {
    "items": [_DUMMY_ITEM],
    "total": 1,
    "item_total": 1,
    "offset": 0,
    "limit": 10,
    "providers": ["仕入元A"],
    "works": [],
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
    assert item["review_reason_details"] == [{"code": "pid_unresolved", "source": "system", "fix_stage": "analysis", "ackable": True}]

    gemini = item["gemini"]
    for f in ("name", "quantity", "price", "unit", "state", "memo", "span"):
        assert f in gemini, f"gemini.{f} missing"

    system = item["system"]
    for f in ("product_id", "pid_resolved", "pid_basis", "condition_basis", "unit",
              "unit_resolved", "condition", "status", "note", "exclusion"):
        assert f in system, f"system.{f} missing"
    assert system["condition_basis"] == "MANUAL_CONDITION_REVIEW"


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


async def test_list_analysis_results_returns_gap_suspect(fake_super_admin_override):
    """gap_suspect（間の行番号と候補）が応答に載る。無い件は null。"""
    from app.main import app

    suspect = {"gap_lines": [14, 15], "candidates": [{"product_id": "1001", "name": "商品A"}]}
    result = dict(_DUMMY_FETCH_RESULT, items=[
        dict(_DUMMY_ITEM, gap_suspect=suspect),
        dict(_DUMMY_ITEM, extraction_item_id="other"),
    ])
    with patch("app.routers.tcg_analysis_review.fetch_analysis_results", new=AsyncMock(return_value=result)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/tcg/analysis-results")

    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    assert items[0]["gap_suspect"] == suspect
    assert items[1]["gap_suspect"] is None


async def test_with_candidate_names_queries_names_once_for_all_candidates():
    from types import SimpleNamespace
    from unittest.mock import MagicMock

    from app.services.v102_gap_suspect_view import with_candidate_names

    db = MagicMock()
    rows = MagicMock()
    rows.fetchall.return_value = [SimpleNamespace(id=1001, name="商品A"), SimpleNamespace(id=1002, name=None)]
    db.execute = AsyncMock(return_value=rows)

    out = await with_candidate_names(db, {
        "i1": {"gap_lines": [3], "candidates": [1001, 1002]},
        "i2": {"gap_lines": [5], "candidates": [1001, 9999]},
    })

    assert db.execute.await_count == 1
    assert out["i1"]["candidates"] == [{"product_id": "1001", "name": "商品A"}, {"product_id": "1002", "name": ""}]
    assert out["i2"]["candidates"] == [{"product_id": "1001", "name": "商品A"}, {"product_id": "9999", "name": ""}]


async def test_with_candidate_names_skips_query_without_candidates():
    from unittest.mock import MagicMock

    from app.services.v102_gap_suspect_view import with_candidate_names

    db = MagicMock()
    db.execute = AsyncMock()

    out = await with_candidate_names(db, {"i1": {"gap_lines": [3], "candidates": []}})

    assert out == {"i1": {"gap_lines": [3], "candidates": []}}
    db.execute.assert_not_awaited()
