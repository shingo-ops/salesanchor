"""tcg_shadow_accuracy router と SQL 組み立ての単体テスト（解析精度管理・新方式、サービス層モック）。"""
from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

pytestmark = pytest.mark.asyncio

_JOB_ID = "11111111-1111-1111-1111-111111111111"
_SUMMARY = {"days": 7, "supplier_id": None, "totals": {"blocks": 0}, "signals": {}, "conditions": [], "by_supplier": []}
_POSTS = {"items": [], "total": 0, "offset": 0, "limit": 20}
_DETAIL = {"job_id": _JOB_ID, "run": {}, "raw_text": "", "blocks": []}


@pytest.fixture
def super_admin_override():
    from app.auth.dependencies import require_super_admin
    from app.main import app

    async def _bypass():
        return {"id": 1, "is_super_admin": True}

    app.dependency_overrides[require_super_admin] = _bypass
    yield
    app.dependency_overrides.pop(require_super_admin, None)


async def _get(path: str, **params):
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.get(path, params=params)


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/tcg/shadow-accuracy/summary",
        "/api/v1/tcg/shadow-accuracy/posts",
        f"/api/v1/tcg/shadow-accuracy/posts/{_JOB_ID}",
    ],
)
async def test_requires_auth(path):
    r = await _get(path)
    assert r.status_code in (401, 403)


async def test_summary_ok_passes_arguments(super_admin_override):
    mock = AsyncMock(return_value=_SUMMARY)
    with patch("app.routers.tcg_shadow_accuracy.fetch_summary", new=mock):
        r = await _get("/api/v1/tcg/shadow-accuracy/summary", days=30, supplier_id=5)
    assert r.status_code == 200
    assert r.json() == _SUMMARY
    assert mock.await_args.kwargs == {"days": 30, "supplier_id": 5}


@pytest.mark.parametrize("days", [7, 30, 0])
async def test_summary_accepts_allowed_days(super_admin_override, days):
    with patch("app.routers.tcg_shadow_accuracy.fetch_summary", new=AsyncMock(return_value=_SUMMARY)):
        r = await _get("/api/v1/tcg/shadow-accuracy/summary", days=days)
    assert r.status_code == 200


@pytest.mark.parametrize("path", ["summary", "posts"])
@pytest.mark.parametrize("days", [1, 14, 90, -1])
async def test_rejects_invalid_days(super_admin_override, path, days):
    r = await _get(f"/api/v1/tcg/shadow-accuracy/{path}", days=days)
    assert r.status_code == 422


async def test_posts_ok_passes_filters(super_admin_override):
    mock = AsyncMock(return_value=_POSTS)
    with patch("app.routers.tcg_shadow_accuracy.fetch_posts", new=mock):
        r = await _get(
            "/api/v1/tcg/shadow-accuracy/posts",
            days=0, supplier_id=3, needs_review="true", signal="S4", offset=40, limit=20,
        )
    assert r.status_code == 200
    assert mock.await_args.kwargs == {
        "days": 0, "supplier_id": 3, "needs_review": True, "signal": "S4", "offset": 40, "limit": 20,
    }


async def test_posts_rejects_unknown_signal(super_admin_override):
    r = await _get("/api/v1/tcg/shadow-accuracy/posts", signal="S7")
    assert r.status_code == 422


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 101}, {"offset": -1}])
async def test_posts_rejects_bad_paging(super_admin_override, params):
    r = await _get("/api/v1/tcg/shadow-accuracy/posts", **params)
    assert r.status_code == 422


async def test_detail_ok(super_admin_override):
    with patch("app.routers.tcg_shadow_accuracy.fetch_post_detail", new=AsyncMock(return_value=_DETAIL)):
        r = await _get(f"/api/v1/tcg/shadow-accuracy/posts/{_JOB_ID}")
    assert r.status_code == 200
    assert r.json() == _DETAIL


async def test_detail_not_found(super_admin_override):
    with patch("app.routers.tcg_shadow_accuracy.fetch_post_detail", new=AsyncMock(return_value=None)):
        r = await _get(f"/api/v1/tcg/shadow-accuracy/posts/{_JOB_ID}")
    assert r.status_code == 404


async def test_detail_rejects_non_uuid(super_admin_override):
    r = await _get("/api/v1/tcg/shadow-accuracy/posts/not-a-uuid")
    assert r.status_code == 422


# --- SQL の SSOT（同じ定義を summary と posts の両方が使うこと） -----------------------------


async def test_summary_and_posts_share_the_signal_definitions():
    from app.services.shadow_accuracy_signals import SIGNAL_CODES, SIGNAL_EXPRS
    from app.services.tcg_shadow_accuracy_svc import posts_query, summary_queries

    summary_sql = summary_queries(30, None)[0][0]
    posts_sql, _ = posts_query(
        days=30, supplier_id=None, needs_review=None, signal=None, offset=0, limit=20
    )
    for code in SIGNAL_CODES:
        assert SIGNAL_EXPRS[code] in summary_sql
        assert SIGNAL_EXPRS[code] in posts_sql


async def test_period_zero_means_all_time_and_has_no_days_param():
    from app.services.tcg_shadow_accuracy_svc import summary_queries

    sql, params = summary_queries(0, None)[0]
    assert "run.started_at >=" not in sql
    assert params == {}


async def test_period_and_supplier_are_bind_parameters():
    from app.services.tcg_shadow_accuracy_svc import summary_queries

    sql, params = summary_queries(7, 12)[0]
    assert "make_interval(days => :days)" in sql and "sup.id = :supplier_id" in sql
    assert params == {"days": 7, "supplier_id": 12}


async def test_posts_filters_use_whitelisted_columns():
    from app.services.tcg_shadow_accuracy_svc import posts_query

    sql, params = posts_query(
        days=7, supplier_id=None, needs_review=False, signal="S2", offset=0, limit=10
    )
    assert "needs_review_count = 0" in sql
    assert "s2 > 0" in sql
    assert params == {"days": 7, "offset": 0, "limit": 10}


async def test_sql_is_read_only():
    from app.services.tcg_shadow_accuracy_svc import posts_query, summary_queries

    statements = [q for q, _ in summary_queries(0, None)]
    statements.append(posts_query(days=0, supplier_id=None, needs_review=None, signal=None, offset=0, limit=1)[0])
    for sql in statements:
        head = sql.lstrip().upper()
        assert head.startswith("WITH")
        for word in ("INSERT ", "UPDATE ", "DELETE ", "DROP ", "ALTER ", "TRUNCATE "):
            assert word not in sql.upper()
