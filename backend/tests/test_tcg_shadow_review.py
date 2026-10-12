"""tcg_shadow_review router の単体テスト（design.md PR-D、サービス層モック）。"""
from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

pytestmark = pytest.mark.asyncio

_RESULTS_DATA = {"items": [], "total": 0, "offset": 0, "limit": 20}
_BOTTLENECKS_DATA = {"days": 7, "by_supplier": [], "by_item": []}
_PREVIEW_DATA = {"checked": 3, "transitions": {"unmatched→matched": 1}}


@pytest.fixture
def super_admin_override():
    from app.auth.dependencies import require_super_admin
    from app.main import app

    async def _bypass():
        return {"id": 1, "is_super_admin": True}

    app.dependency_overrides[require_super_admin] = _bypass
    yield
    app.dependency_overrides.pop(require_super_admin, None)


async def test_shadow_results_requires_auth():
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/api/v1/tcg/shadow-results")
    assert r.status_code in (401, 403)


async def test_bottlenecks_requires_auth():
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/api/v1/tcg/shadow-results/bottlenecks")
    assert r.status_code in (401, 403)


async def test_keyword_preview_requires_auth():
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post(
            "/api/v1/tcg/shadow-results/keyword-preview",
            json={"product_id": 1, "kind": "search", "keyword": "x"},
        )
    assert r.status_code in (401, 403)


async def test_shadow_results_ok(super_admin_override):
    from app.main import app
    with patch(
        "app.routers.tcg_shadow_review.fetch_shadow_results",
        new=AsyncMock(return_value=_RESULTS_DATA),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get(
                "/api/v1/tcg/shadow-results",
                params={"needs_review": "true", "offset": 0, "limit": 20},
            )
    assert r.status_code == 200
    assert r.json() == _RESULTS_DATA


async def test_bottlenecks_ok(super_admin_override):
    from app.main import app
    with patch(
        "app.routers.tcg_shadow_review.fetch_bottlenecks",
        new=AsyncMock(return_value=_BOTTLENECKS_DATA),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get("/api/v1/tcg/shadow-results/bottlenecks", params={"days": 7})
    assert r.status_code == 200
    assert r.json() == _BOTTLENECKS_DATA


async def test_bottlenecks_rejects_invalid_days(super_admin_override):
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/api/v1/tcg/shadow-results/bottlenecks", params={"days": 14})
    assert r.status_code == 422


async def test_keyword_preview_ok(super_admin_override):
    from app.main import app
    with patch(
        "app.routers.tcg_shadow_review.preview_keyword_change",
        new=AsyncMock(return_value=_PREVIEW_DATA),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.post(
                "/api/v1/tcg/shadow-results/keyword-preview",
                json={"product_id": 1, "kind": "search", "keyword": "商品A"},
            )
    assert r.status_code == 200
    assert r.json() == _PREVIEW_DATA


async def test_keyword_preview_product_not_found(super_admin_override):
    from app.main import app
    from app.services.tcg_shadow_review_svc import KeywordPreviewProductNotFound
    with patch(
        "app.routers.tcg_shadow_review.preview_keyword_change",
        new=AsyncMock(side_effect=KeywordPreviewProductNotFound("PRODUCT_NOT_FOUND")),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.post(
                "/api/v1/tcg/shadow-results/keyword-preview",
                json={"product_id": 999999, "kind": "search", "keyword": "x"},
            )
    assert r.status_code == 404


async def test_keyword_preview_empty_keyword(super_admin_override):
    from app.main import app
    with patch(
        "app.routers.tcg_shadow_review.preview_keyword_change",
        new=AsyncMock(side_effect=ValueError("KEYWORD_EMPTY")),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.post(
                "/api/v1/tcg/shadow-results/keyword-preview",
                json={"product_id": 1, "kind": "search", "keyword": "   "},
            )
    assert r.status_code == 422


async def test_keyword_preview_invalid_kind_rejected(super_admin_override):
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post(
            "/api/v1/tcg/shadow-results/keyword-preview",
            json={"product_id": 1, "kind": "bogus", "keyword": "x"},
        )
    assert r.status_code == 422
