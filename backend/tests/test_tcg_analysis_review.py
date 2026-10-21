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


# ---------------------------------------------------------------------------
# 在庫表の解析パネル用: extraction_item_ids 指定（inventory-row-drawer 便）
# ---------------------------------------------------------------------------

# B3: include_inactive=False の出力が、変更前の _BASE_FROM（review_joins を含む全文）と1文字も変わらないこと。


async def test_base_from_default_is_identical_to_the_previous_constant():
    from app.services import tcg_analysis_review_svc as svc
    from app.services.tcg_condition_review_svc import review_joins

    schema = svc.TCG_SCHEMA
    previous = f"""
    FROM {schema}.analysis_results ar
    JOIN {schema}.extraction_items ei ON ei.id = ar.extraction_item_id
    JOIN {schema}.extraction_jobs ej ON ej.id = ei.extraction_job_id
    JOIN {schema}.source_messages sm ON sm.id = ej.source_message_id AND sm.is_active = TRUE
    JOIN public.supplier_channels sc ON sc.id = sm.supplier_channel_id
    LEFT JOIN public.suppliers ps ON ps.id = sc.supplier_id
    LEFT JOIN public.products p ON p.id = ar.product_id
    LEFT JOIN public.type_master ws ON ws.id = p.work_id
    {review_joins(schema=schema)}
"""
    assert svc._base_from() == previous
    assert svc._BASE_FROM == previous
    inactive_ok = svc._base_from(include_inactive=True)
    assert "sm.is_active" not in inactive_ok and "ar.is_current = TRUE" in inactive_ok


async def test_build_where_puts_item_ids_condition_first():
    from app.services import tcg_analysis_review_svc as svc

    where, params = svc._build_where(
        query="x", provider=None, status_tab="ALL", review_only=False, unregistered_only=False,
        unresolved_unit_only=False, extraction_item_ids=["a"],
    )
    assert where.startswith("WHERE ei.id = ANY(CAST(:item_ids AS uuid[]))")
    assert params["item_ids"] == ["a"]


async def test_item_ids_are_passed_to_the_service_with_all_tab_and_matching_limit(fake_super_admin_override):
    from app.main import app

    ids = ["aaaaaaaa-0000-0000-0000-000000000001", "aaaaaaaa-0000-0000-0000-000000000002"]
    mock = AsyncMock(return_value=_DUMMY_FETCH_RESULT)
    with patch("app.routers.tcg_analysis_review.fetch_analysis_results", new=mock):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(
                "/api/v1/tcg/analysis-results?status_tab=NEEDS_REVIEW&offset=5&limit=10"
                f"&extraction_item_ids={ids[0]}&extraction_item_ids={ids[1]}"
            )
    assert resp.status_code == 200, resp.text
    kwargs = mock.await_args.kwargs
    assert kwargs["extraction_item_ids"] == ids
    assert (kwargs["status_tab"], kwargs["offset"], kwargs["limit"]) == ("ALL", 0, 2)


async def test_item_ids_not_given_keeps_the_previous_call(fake_super_admin_override):
    from app.main import app

    mock = AsyncMock(return_value=_DUMMY_FETCH_RESULT)
    with patch("app.routers.tcg_analysis_review.fetch_analysis_results", new=mock):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/tcg/analysis-results?status_tab=NEEDS_REVIEW&offset=5&limit=10")
    assert resp.status_code == 200, resp.text
    kwargs = mock.await_args.kwargs
    assert kwargs["extraction_item_ids"] is None
    assert (kwargs["status_tab"], kwargs["offset"], kwargs["limit"]) == ("NEEDS_REVIEW", 5, 10)


async def test_item_ids_with_non_uuid_value_is_422(fake_super_admin_override):
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/tcg/analysis-results?extraction_item_ids=not-a-uuid")
    assert resp.status_code == 422, resp.text


async def test_item_ids_over_50_is_422(fake_super_admin_override):
    from uuid import uuid4

    from app.main import app

    query = "&".join(f"extraction_item_ids={uuid4()}" for _ in range(51))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/api/v1/tcg/analysis-results?{query}")
    assert resp.status_code == 422, resp.text


async def test_item_ids_50_is_accepted(fake_super_admin_override):
    from uuid import uuid4

    from app.main import app

    query = "&".join(f"extraction_item_ids={uuid4()}" for _ in range(50))
    with patch("app.routers.tcg_analysis_review.fetch_analysis_results", new=AsyncMock(return_value=_DUMMY_FETCH_RESULT)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"/api/v1/tcg/analysis-results?{query}")
    assert resp.status_code == 200, resp.text


async def test_item_ids_non_super_admin_is_forbidden():
    """is_super_admin=false の tenant admin は 403（test_inventory_offers_rbac.py と同じ差し替え方式）。"""
    from app.auth.dependencies import get_current_user
    from app.main import app
    from app.models import User

    async def _fake() -> User:
        u = User()
        u.id = 100
        u.is_super_admin = False
        u.role = "admin"
        u.tenant_id = 6
        return u

    mock = AsyncMock(return_value=_DUMMY_FETCH_RESULT)
    app.dependency_overrides[get_current_user] = _fake
    try:
        with patch("app.routers.tcg_analysis_review.fetch_analysis_results", new=mock):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.get(
                    "/api/v1/tcg/analysis-results?extraction_item_ids=aaaaaaaa-0000-0000-0000-000000000001"
                )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
    assert resp.status_code == 403, resp.text
    mock.assert_not_awaited()


# ---------------------------------------------------------------------------
# POST /tcg/analysis-results/client-timing（要確認パネルの計時）
# ---------------------------------------------------------------------------

_TIMING_URL = "/api/v1/tcg/analysis-results/client-timing"
_TIMING_BODY = {
    "panel_ms": 1234.5,
    "list_ms": 800.2,
    "doc_ms": 2345.6,
    "rows": 20,
    "page_size": 20,
    "entry": "first",
}


async def _post_timing(body):
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.post(_TIMING_URL, json=body)


async def test_client_timing_returns_204_and_logs_one_line(fake_super_admin_override, caplog):
    import logging

    with caplog.at_level(logging.WARNING, logger="app.routers.tcg_analysis_review"):
        resp = await _post_timing(_TIMING_BODY)
    assert resp.status_code == 204, resp.text
    assert resp.content == b""
    lines = [r for r in caplog.records if "review_timing" in r.getMessage()]
    assert len(lines) == 1
    assert lines[0].levelno == logging.WARNING
    assert lines[0].getMessage() == (
        "review_timing panel_ms=1234 list_ms=800 doc_ms=2346 rows=20 page_size=20 entry=first"
    )


async def test_client_timing_non_super_admin_is_forbidden():
    from app.auth.dependencies import get_current_user
    from app.main import app
    from app.models import User

    async def _fake() -> User:
        u = User()
        u.id = 100
        u.is_super_admin = False
        u.role = "admin"
        u.tenant_id = 6
        return u

    app.dependency_overrides[get_current_user] = _fake
    try:
        resp = await _post_timing(_TIMING_BODY)
    finally:
        app.dependency_overrides.pop(get_current_user, None)
    assert resp.status_code == 403, resp.text


@pytest.mark.parametrize(
    "patch_body",
    [
        {"panel_ms": 120001},
        {"panel_ms": -1},
        {"rows": 501},
        {"rows": -1},
        {"page_size": 30},
        {"entry": "x"},
        {"extra_field": "x"},
    ],
)
async def test_client_timing_out_of_range_or_extra_is_422(fake_super_admin_override, patch_body):
    resp = await _post_timing({**_TIMING_BODY, **patch_body})
    assert resp.status_code == 422, resp.text


async def test_client_timing_route_itself_does_not_take_db():
    """この受け口自身は get_db を依存に持たない（認証の中の DB 利用は既存どおり）。"""
    import inspect

    from app.auth.dependencies import require_super_admin
    from app.database import get_db
    from app.main import app

    route = next(r for r in app.routes if getattr(r, "path", "") == _TIMING_URL)
    direct = [d.call for d in route.dependant.dependencies]
    assert direct == [require_super_admin]
    assert get_db not in direct
    assert "db" not in inspect.signature(route.endpoint).parameters


# ---------------------------------------------------------------------------
# 便1: order / posted_within_hours（要確認タブの新しい道。ADR-1023 改訂 2026-10-21）
# ---------------------------------------------------------------------------


async def _get_with_mock(query: str):
    from app.main import app

    mock = AsyncMock(return_value=_DUMMY_FETCH_RESULT)
    with patch("app.routers.tcg_analysis_review.fetch_analysis_results", new=mock):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"/api/v1/tcg/analysis-results?{query}")
    return resp, mock


async def test_order_and_window_are_passed_to_the_service(fake_super_admin_override):
    resp, mock = await _get_with_mock("status_tab=NEEDS_REVIEW&order=posted_desc&posted_within_hours=24&limit=25")
    assert resp.status_code == 200, resp.text
    kwargs = mock.await_args.kwargs
    assert (kwargs["order"], kwargs["posted_within_hours"], kwargs["limit"]) == ("posted_desc", 24, 25)


async def test_order_and_window_default_to_the_previous_behaviour(fake_super_admin_override):
    resp, mock = await _get_with_mock("status_tab=NEEDS_REVIEW&offset=5&limit=10")
    assert resp.status_code == 200, resp.text
    kwargs = mock.await_args.kwargs
    assert (kwargs["order"], kwargs["posted_within_hours"]) == ("default", None)


@pytest.mark.parametrize(
    "query",
    ["order=oldest", "posted_within_hours=0", "posted_within_hours=721", "posted_within_hours=x"],
)
async def test_order_and_window_out_of_range_is_422(fake_super_admin_override, query):
    resp, _ = await _get_with_mock(query)
    assert resp.status_code == 422, resp.text
