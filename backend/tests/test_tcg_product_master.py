"""
PARITY-03 Phase 3: 商品マスタ登録 API テスト。

カバー:
  - 認証なし → 401/403
  - B-1 GET /tcg/products/registration-form
  - B-4 GET /tcg/products/search
  - B-2 POST /tcg/products/check-duplicates
  - B-3 POST /tcg/products
  - B-5 POST /tcg/products/{code}/search-keywords
  - サービス層モックで正常系・エラー系レスポンス形状を検証
"""
from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

pytestmark = pytest.mark.asyncio

_FORM_DATA = {
    "item": {
        "extraction_item_id": "aaaaaaaa-0000-0000-0000-000000000001",
        "source_message_id": "bbbbbbbb-0000-0000-0000-000000000001",
        "raw_name": "ポケモン SV1a 1BOX",
        "mark": "",
        "english_title": "",
    },
    "lookups": {
        "division_id": [{"id": "cccc-0001", "name": "TCG"}],
        "work_id": [{"id": "dddd-0001", "name": "Pokemon"}],
        "manufacturer_id": [{"id": "eeee-0001", "name": "The Pokemon Company"}],
        "product_category_id": [{"id": "ffff-0001", "name": "Box"}],
    },
}

_SEARCH_DATA = {
    "candidates": [
        {
            "product_id": "PM0001",
            "product_uuid": "aaaaaaaa-0000-0000-0000-000000000001",
            "japanese_title": "SV1a",
            "search_keywords": "sv1a,SV1a",
        },
    ]
}

_DUP_DATA = {"candidates": []}

_CREATE_OK = {"ok": True, "product_id": "PM0042"}
_CREATE_DUP = {
    "ok": False,
    "code": "DUPLICATE_CANDIDATE",
    "candidates": [{"product_id": "PM0001", "japanese_title": "SV1a"}],
}

_KEYWORD_OK = {"ok": True}
_KEYWORD_DUP = {"ok": False, "code": "KEYWORD_ALREADY_EXISTS"}

_REANALYZE_DATA = {
    "before": {"total": 10, "pid_resolved": 8, "unit_resolved": 9, "needs_review": 2},
    "after": {"total": 10, "pid_resolved": 9, "unit_resolved": 9, "needs_review": 1,
              "e3a_recovered": 0, "e5_changed": 0, "e3b_flagged": 0, "e4_resolved": 0},
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
# 認証なし → 401/403
# ---------------------------------------------------------------------------


async def test_registration_form_requires_auth():
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get(
            "/api/v1/tcg/products/registration-form",
            params={"extraction_item_id": "x", "source_message_id": "y"},
        )
    assert r.status_code in (401, 403)


async def test_search_requires_auth():
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/api/v1/tcg/products/search", params={"query": "ポケモン"})
    assert r.status_code in (401, 403)


async def test_check_duplicates_requires_auth():
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post(
            "/api/v1/tcg/products/check-duplicates",
            json={
                "extraction_item_id": "x", "source_message_id": "y",
                "division_id": "d", "work_id": "w",
                "manufacturer_id": "m", "product_category_id": "p",
                "japanese_title": "SV1a",
            },
        )
    assert r.status_code in (401, 403)


async def test_create_product_requires_auth():
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post(
            "/api/v1/tcg/products",
            json={
                "extraction_item_id": "x", "source_message_id": "y",
                "division_id": "d", "work_id": "w",
                "manufacturer_id": "m", "product_category_id": "p",
                "japanese_title": "SV1a",
            },
        )
    assert r.status_code in (401, 403)


async def test_add_keyword_requires_auth():
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post(
            "/api/v1/tcg/products/PM0001/search-keywords",
            json={"new_keyword": "sv1a"},
        )
    assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# B-1: 登録フォーム正常系
# ---------------------------------------------------------------------------


async def test_registration_form_ok(super_admin_override):
    from app.main import app
    with patch(
        "app.routers.tcg_product_master.fetch_registration_form",
        new=AsyncMock(return_value=_FORM_DATA),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            r = await client.get(
                "/api/v1/tcg/products/registration-form",
                params={
                    "extraction_item_id": "aaaaaaaa-0000-0000-0000-000000000001",
                    "source_message_id": "bbbbbbbb-0000-0000-0000-000000000001",
                },
            )
    assert r.status_code == 200
    body = r.json()
    assert body["item"]["raw_name"] == "ポケモン SV1a 1BOX"
    assert "mark" in body["item"]
    assert "english_title" in body["item"]
    assert "division_id" in body["lookups"]
    assert body["lookups"]["division_id"][0]["name"] == "TCG"


async def test_registration_form_not_found(super_admin_override):
    from app.main import app
    with patch(
        "app.routers.tcg_product_master.fetch_registration_form",
        new=AsyncMock(side_effect=ValueError("PRODUCT_MASTER_V2_EXTRACTION_ITEM_NOT_FOUND")),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            r = await client.get(
                "/api/v1/tcg/products/registration-form",
                params={"extraction_item_id": "x", "source_message_id": "y"},
            )
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# B-4: 商品名検索正常系
# ---------------------------------------------------------------------------


async def test_search_ok(super_admin_override):
    from app.main import app
    with patch(
        "app.routers.tcg_product_master.search_products_by_name",
        new=AsyncMock(return_value=_SEARCH_DATA),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            r = await client.get(
                "/api/v1/tcg/products/search", params={"query": "SV1a"}
            )
    assert r.status_code == 200
    body = r.json()
    assert len(body["candidates"]) == 1
    assert body["candidates"][0]["product_id"] == "PM0001"
    assert "search_keywords" in body["candidates"][0]


# ---------------------------------------------------------------------------
# B-2: 重複チェック正常系
# ---------------------------------------------------------------------------


async def test_check_duplicates_ok(super_admin_override):
    from app.main import app
    with patch(
        "app.routers.tcg_product_master.check_duplicates",
        new=AsyncMock(return_value=_DUP_DATA),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            r = await client.post(
                "/api/v1/tcg/products/check-duplicates",
                json={
                    "extraction_item_id": "aaaa",
                    "source_message_id": "bbbb",
                    "division_id": "dddd-0001",
                    "work_id": "eeee-0001",
                    "manufacturer_id": "ffff-0001",
                    "product_category_id": "gggg-0001",
                    "japanese_title": "新作SV1a",
                },
            )
    assert r.status_code == 200
    assert r.json()["candidates"] == []


# ---------------------------------------------------------------------------
# B-3: 登録正常系・重複時
# ---------------------------------------------------------------------------


async def test_create_product_ok(super_admin_override):
    from app.main import app
    with patch(
        "app.routers.tcg_product_master.create_product",
        new=AsyncMock(return_value=_CREATE_OK),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            r = await client.post(
                "/api/v1/tcg/products",
                json={
                    "extraction_item_id": "aaaa",
                    "source_message_id": "bbbb",
                    "division_id": "cccc",
                    "work_id": "dddd",
                    "manufacturer_id": "eeee",
                    "product_category_id": "ffff",
                    "japanese_title": "新作SV42",
                },
            )
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["product_id"] == "PM0042"


async def test_create_product_with_mark_english_title(super_admin_override):
    from app.main import app
    with patch(
        "app.routers.tcg_product_master.create_product",
        new=AsyncMock(return_value=_CREATE_OK),
    ) as mock_create:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            r = await client.post(
                "/api/v1/tcg/products",
                json={
                    "extraction_item_id": "aaaa",
                    "source_message_id": "bbbb",
                    "division_id": "cccc",
                    "work_id": "dddd",
                    "manufacturer_id": "eeee",
                    "product_category_id": "ffff",
                    "japanese_title": "新作SV42",
                    "mark": "MMD",
                    "english_title": "Mask of Change",
                },
            )
    assert r.status_code == 200
    assert mock_create.call_args.kwargs["mark"] == "MMD"
    assert mock_create.call_args.kwargs["english_title"] == "Mask of Change"


async def test_create_product_duplicate(super_admin_override):
    from app.main import app
    with patch(
        "app.routers.tcg_product_master.create_product",
        new=AsyncMock(return_value=_CREATE_DUP),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            r = await client.post(
                "/api/v1/tcg/products",
                json={
                    "extraction_item_id": "aaaa",
                    "source_message_id": "bbbb",
                    "division_id": "cccc",
                    "work_id": "dddd",
                    "manufacturer_id": "eeee",
                    "product_category_id": "ffff",
                    "japanese_title": "SV1a",
                },
            )
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is False
    assert body["code"] == "DUPLICATE_CANDIDATE"
    assert len(body["candidates"]) >= 1


async def test_create_product_empty_title(super_admin_override):
    from app.main import app
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        r = await client.post(
            "/api/v1/tcg/products",
            json={
                "extraction_item_id": "aaaa",
                "source_message_id": "bbbb",
                "division_id": "cccc",
                "work_id": "dddd",
                "manufacturer_id": "eeee",
                "product_category_id": "ffff",
                "japanese_title": "   ",
            },
        )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# B-5: キーワード追加正常系・重複時
# ---------------------------------------------------------------------------


async def test_add_keyword_ok(super_admin_override):
    from app.main import app
    with patch(
        "app.routers.tcg_product_master.add_search_keyword",
        new=AsyncMock(return_value=_KEYWORD_OK),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            r = await client.post(
                "/api/v1/tcg/products/PM0001/search-keywords",
                json={"new_keyword": "sv1a"},
            )
    assert r.status_code == 200
    assert r.json()["ok"] is True


async def test_reanalyze_requires_auth():
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post(
            "/api/v1/tcg/extraction-jobs/aaaa-bbbb/reanalyze"
        )
    assert r.status_code in (401, 403)


async def test_reanalyze_ok(super_admin_override):
    from app.main import app
    with patch(
        "app.routers.tcg_product_master.reanalyze_extraction_job",
        new=AsyncMock(return_value=_REANALYZE_DATA),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            r = await client.post(
                "/api/v1/tcg/extraction-jobs/aaaa-bbbb/reanalyze"
            )
    assert r.status_code == 200
    body = r.json()
    assert body["before"]["total"] == 10
    assert body["before"]["pid_resolved"] == 8
    assert "after" in body


async def test_add_keyword_duplicate(super_admin_override):
    from app.main import app
    with patch(
        "app.routers.tcg_product_master.add_search_keyword",
        new=AsyncMock(return_value=_KEYWORD_DUP),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            r = await client.post(
                "/api/v1/tcg/products/PM0001/search-keywords",
                json={"new_keyword": "sv1a"},
            )
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is False
    assert body["code"] == "KEYWORD_ALREADY_EXISTS"


# ---------------------------------------------------------------------------
# B-3: force=True — 重複候補があっても登録できる（GAS ソフトブロック準拠）
# ---------------------------------------------------------------------------


async def test_create_product_force_bypasses_duplicate(super_admin_override):
    """force=True: DUPLICATE_CANDIDATE を返さず登録まで進む。"""
    from app.main import app
    with patch(
        "app.routers.tcg_product_master.create_product",
        new=AsyncMock(return_value=_CREATE_OK),
    ) as mock_create:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            r = await client.post(
                "/api/v1/tcg/products",
                json={
                    "extraction_item_id": "aaaa",
                    "source_message_id": "bbbb",
                    "division_id": "cccc",
                    "work_id": "dddd",
                    "manufacturer_id": "eeee",
                    "product_category_id": "ffff",
                    "japanese_title": "新作SV42",
                    "force": True,
                },
            )
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert mock_create.call_args.kwargs["force"] is True


async def test_create_product_no_force_default(super_admin_override):
    """force 未指定: False がデフォルト。重複ありなら DUPLICATE_CANDIDATE を返す。"""
    from app.main import app
    with patch(
        "app.routers.tcg_product_master.create_product",
        new=AsyncMock(return_value=_CREATE_DUP),
    ) as mock_create:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            r = await client.post(
                "/api/v1/tcg/products",
                json={
                    "extraction_item_id": "aaaa",
                    "source_message_id": "bbbb",
                    "division_id": "cccc",
                    "work_id": "dddd",
                    "manufacturer_id": "eeee",
                    "product_category_id": "ffff",
                    "japanese_title": "SV1a",
                },
            )
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is False
    assert body["code"] == "DUPLICATE_CANDIDATE"
    assert mock_create.call_args.kwargs["force"] is False


# ---------------------------------------------------------------------------
# _build_duplicate_candidates: GAS 準拠ロジック単体テスト
# ---------------------------------------------------------------------------


def _make_row(**kwargs):
    """MagicMock を使わず SimpleNamespace でテスト用 row を作る。"""
    from types import SimpleNamespace
    return SimpleNamespace(**kwargs)


def test_build_dup_exact_title_always_matches():
    """exactTitle: タイトル完全一致は mark/search_keywords 不問で候補になる。"""
    from app.services.tcg_product_master_svc import _build_duplicate_candidates
    rows = [_make_row(
        product_id="PM0001",
        japanese_title="ポケカ SV1a",
        work_id="w1",
        manufacturer_id="m1",
        product_category_id="c1",
        mark="SV1a",
        search_keywords="sv1a",
    )]
    candidates = _build_duplicate_candidates(
        rows,
        japanese_title="ポケカ SV1a",
        work_id="w9",  # 分類が違っても
        manufacturer_id="m9",
        product_category_id="c9",
        mark="",
        search_keywords="",
    )
    assert len(candidates) == 1
    assert candidates[0]["product_id"] == "PM0001"


def test_build_dup_same_cls_no_mark_no_search_not_candidate():
    """GAS 準拠: mark も search_keywords も空なら同一分類だけでは候補にならない。"""
    from app.services.tcg_product_master_svc import _build_duplicate_candidates
    rows = [_make_row(
        product_id="PM0002",
        japanese_title="別商品 SV1b",
        work_id="w1",
        manufacturer_id="m1",
        product_category_id="c1",
        mark="SV1b",
        search_keywords="",
    )]
    candidates = _build_duplicate_candidates(
        rows,
        japanese_title="最強ジャンプ5月号",  # タイトル不一致
        work_id="w1",
        manufacturer_id="m1",
        product_category_id="c1",
        mark="",         # mark 空
        search_keywords="",  # search_keywords 空
    )
    assert candidates == []


def test_build_dup_same_cls_with_mark_matches():
    """same_cls + same_mark: 候補になる。"""
    from app.services.tcg_product_master_svc import _build_duplicate_candidates
    rows = [_make_row(
        product_id="PM0003",
        japanese_title="別商品 SV1b",
        work_id="w1",
        manufacturer_id="m1",
        product_category_id="c1",
        mark="SV1b",
        search_keywords="",
    )]
    candidates = _build_duplicate_candidates(
        rows,
        japanese_title="最強ジャンプ5月号",
        work_id="w1",
        manufacturer_id="m1",
        product_category_id="c1",
        mark="SV1b",  # mark 一致
        search_keywords="",
    )
    assert len(candidates) == 1


def test_build_dup_same_cls_mark_mismatch_no_candidate():
    """same_cls だが mark が異なり search_keywords も空: 候補にならない。"""
    from app.services.tcg_product_master_svc import _build_duplicate_candidates
    rows = [_make_row(
        product_id="PM0004",
        japanese_title="別商品 SV1c",
        work_id="w1",
        manufacturer_id="m1",
        product_category_id="c1",
        mark="SV1c",
        search_keywords="",
    )]
    candidates = _build_duplicate_candidates(
        rows,
        japanese_title="全然違うタイトル",
        work_id="w1",
        manufacturer_id="m1",
        product_category_id="c1",
        mark="SV1b",  # mark 不一致
        search_keywords="",
    )
    assert candidates == []
