"""在庫表（GET /inventory）を LINE 解析の配信行に切り替える便SP2の、PostgreSQL 不要の試験。

配信行の定義が distribution_rows_sql の1か所だけであること、offer_type と status の写像、
権限（products.view）と LINE 解析 API の super admin 限定を固める。
PostgreSQL が要る T1〜T4 は test_inventory_distribution_rows_pg.py（CI 専用）。
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.models import User
from app.services import tcg_distribution_svc as svc

_COND = {"include_flag_single": False, "age_condition": ""}


def test_merge_off_sql_has_no_grouping() -> None:
    sql = svc.distribution_rows_sql(**_COND, merge_same_post=False)
    assert "dist_groups" not in sql
    assert "ROW_NUMBER() OVER" in sql


def test_merge_on_sql_uses_cr_columns_and_ship_in_key() -> None:
    sql = svc.distribution_rows_sql(**_COND, merge_same_post=True)
    assert "dist_groups" in sql
    assert "cr.condition_id" in sql and "cr.basis" in sql
    assert "ar.condition_id" not in sql and "ar.condition_basis" not in sql
    assert "ar.ship_ja" in sql.split("dist_groups")[0]  # 鍵（gkey）に ship_ja が入る


def test_sold_out_filter_is_shared_by_dist_base_and_preview_count() -> None:
    import inspect

    cond = svc._sold_out_filter()
    assert cond == "lower(btrim(COALESCE(ar.status, ''))) NOT IN ('sold out', 'soldout')"
    assert "ar." in svc._sold_out_filter.__doc__  # ar. 別名が前提であることを docstring に書く
    for merge in (False, True):
        assert cond in svc.distribution_rows_sql(**_COND, merge_same_post=merge)
    assert "_sold_out_filter(" in inspect.getsource(svc.fetch_preview_data)


def test_fresh_window_is_24_hours_and_fresh_filter_is_bound() -> None:
    from app.routers.inventory_offers import _build_view_filters

    none = dict.fromkeys(("q", "tcg_type", "category", "offer_type", "hide_supplier_ids", "hide_categories", "condition",
                          "condition_in", "unit_in", "offer_type_in", "qty_min", "qty_max", "price_min", "price_max"))
    assert svc.FRESH_WINDOW_HOURS == 24
    assert _build_view_filters(**none) == ([], {})  # 既定は False: 既存の呼び出しは変わらない
    conds, params = _build_view_filters(**none, fresh_only=True)
    assert conds == ["d.posted_ts >= NOW() - make_interval(hours => :fresh_hours)"]
    assert params == {"fresh_hours": 24}


def test_view_sql_order_by_groups_by_release_date_first() -> None:
    from app.routers.inventory_offers import _SORT_COLUMNS, _build_inventory_view_sql, _build_view_order_by

    group_asc = "NULLIF(d.release_date, '') ASC NULLS LAST, d.english_title ASC, d.japanese_title ASC NULLS LAST, d.product_id ASC"
    group_desc = group_asc.replace("ASC NULLS LAST, d.english_title", "DESC NULLS LAST, d.english_title", 1)
    rel = _SORT_COLUMNS["release_date"]
    price = _SORT_COLUMNS["unit_price"]
    assert _build_view_order_by(sort_col=rel, order_dir="ASC") == f"ORDER BY {group_asc}, d.sort_ord ASC"
    assert _build_view_order_by(sort_col=rel, order_dir="DESC") == f"ORDER BY {group_desc}, d.sort_ord ASC"
    assert _build_view_order_by(sort_col=price, order_dir="DESC") == f"ORDER BY {group_asc}, d.price_num DESC NULLS LAST, d.sort_ord ASC"
    assert _build_view_order_by(sort_col=_SORT_COLUMNS["name"], order_dir="DESC") == (
        "ORDER BY d.english_title DESC, d.japanese_title DESC NULLS LAST, d.sort_ord ASC"
    )
    head, final = svc.distribution_rows_parts(**_COND, merge_same_post=False)
    kw = {"head": head, "final_main": final, "merge": False, "where": ""}
    sql = _build_inventory_view_sql(**kw, sort_col=rel, order_dir="ASC")
    assert sql.count(f"ORDER BY {group_asc}, d.sort_ord ASC") == 2


def test_inventory_endpoint_defaults_merge_off_and_fresh_off() -> None:
    import inspect

    from app.routers import inventory_offers as io

    params = inspect.signature(io.list_inventory_view).parameters
    assert params["merge_same_post"].default.default is False
    assert params["fresh_only"].default.default is False


def test_round_half_up_matches_sql_round() -> None:
    from app.routers.inventory_offers import round_half_up

    assert [round_half_up(x) for x in (2.5, 3.5, 0.5, 1.4, 1.6)] == [3, 4, 1, 1, 2]


def test_flag_single_changes_condition_filter() -> None:
    off = svc.distribution_rows_sql(include_flag_single=False, age_condition="", merge_same_post=False)
    on = svc.distribution_rows_sql(include_flag_single=True, age_condition="", merge_same_post=False)
    assert "FLAG_SINGLE" not in off and "FLAG_SINGLE" in on
    assert "IS DISTINCT FROM 'EXCLUDE'" in off and "IS DISTINCT FROM 'EXCLUDE'" in on


def test_output_rows_use_shared_sql_and_preview_count_does_not_join_products() -> None:
    import inspect

    assert "ar.pid_resolved" not in inspect.getsource(svc.fetch_output_rows)
    # プレビューの件数は変更前の問い合わせ（products を結合しない）。状態の条件は _condition_filter と共通。
    src = inspect.getsource(svc.fetch_preview_data)
    assert "_condition_filter(" in src and "public.products" not in src


def test_inventory_router_has_no_distribution_where() -> None:
    import inspect

    from app.routers import inventory_offers

    src = inspect.getsource(inventory_offers.list_inventory_view)
    for token in ("pid_resolved", "is_current", "line_posted_at", "needs_review"):
        assert token not in src


def test_offer_type_status_mapping_is_one_constant() -> None:
    from app.routers import inventory_offers as io

    assert io.OFFER_TYPE_TO_STATUS == {"in_stock": "In Stock", "pre_order": "Pre-order"}
    assert io.status_to_offer_type("In Stock") == "in_stock"
    assert io.status_to_offer_type("Pre-order") == "pre_order"
    assert io.status_to_offer_type("Other") is None
    assert io.status_to_offer_type(None) is None


# --- T8: 権限 ---------------------------------------------------------------------------------


def _user(*, super_admin: bool) -> User:
    user = User()
    user.id = 321
    user.tenant_id = 6
    user.is_super_admin = super_admin
    user.role = "sales"
    user.is_active = True
    return user


@asynccontextmanager
async def _client(*, perms: frozenset[str], super_admin: bool = False):
    from app.auth.dependencies import get_current_tenant, get_current_user
    from app.database import get_db
    from app.main import app

    async def _db():
        yield object()

    saved = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_current_tenant] = lambda: 6
    app.dependency_overrides[get_current_user] = lambda: _user(super_admin=super_admin)
    try:
        with patch("app.auth.dependencies.load_user_permissions", AsyncMock(return_value=perms)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                yield client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(saved)


@pytest.mark.asyncio
async def test_inventory_view_allowed_with_products_view_and_empty_when_window_unset() -> None:
    from app.routers import inventory_offers as io

    async with _client(perms=frozenset({"products.view"})) as client:
        with patch.object(io, "load_distribution_settings", AsyncMock(return_value={})):
            res = await client.get("/api/v1/inventory")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["items"] == [] and body["total"] == 0 and body["window_hours"] is None
    assert body["fresh_window_hours"] == 24


@pytest.mark.asyncio
async def test_inventory_view_forbidden_without_products_view() -> None:
    async with _client(perms=frozenset({"customers.view"})) as client:
        res = await client.get("/api/v1/inventory")
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_line_analysis_api_forbidden_for_non_super_admin() -> None:
    async with _client(perms=frozenset({"products.view"})) as client:
        res = await client.get("/api/v1/tcg/distribution/targets")
    assert res.status_code == 403


# --- 在庫表を1文にする便: distribution_rows_sql の文字列が変更前と1文字も違わないこと ---------------------------
# 期待値は distribution_rows_sql を age_condition=" AND x = :y" で呼んだ出力の長さと SHA-256。
# 便1（2026-10-14）で Sold out の条件（_sold_out_filter）を足した版に更新した。
# review-ack-revoke 便で cr_review_ack を bool_or の集計にし review_acked 列を足して再生成した（差分は golden-diff: 同じ cr_review_ack の形変更が4通りに出るだけ）。
# inventory-row-drawer 便で、行の元 ID の列（item_key・item_keys_agg・extraction_item_ids の3か所だけ）を足して再生成した。
# review-excluded-ack 便で cr_review_ack LATERAL（excluded の確認済み除外）を足して再生成した。差は4点のみ（distribution_sql_after_merge.diff）。
# bundle-sale 便1（ADR-1027）で商品名を bundle_title_sql の2列にし、line_units の JOIN と gkey の bundle_size を足して再生成した。
# g28 便1（バルク状態）で RESULT_CONDITION_ORDER に Bulk を足して再生成した。差は Bulk の WHEN 句1つのみ（golden_diff.txt）。
# result-order-condition-value 便（2026-10-18）で、状態の並びを固定の表（RESULT_CONDITION_ORDER）から状態マスタ（public.conditions の value_group / value_rank・ADR-1023）の副問い合わせに替えて再生成した。差は ORDER BY の状態の部分1か所のみ（4通りとも同じ差）。CI で全体が約2倍遅くなったため、行ごとの副問い合わせを InitPlan（1回だけ評価する jsonb）に替えて再生成した。
_GOLDEN = {
    (False, False): (25287, "2c56bcc55f7b22ea6d6ad972d96fd0a262114313e4547327f4ac0df6aebae8c1"),
    (False, True): (26438, "8522e964c651fd7544d4caf4ea1df5f3cb59635634e632578a7d751c3ba5fbfb"),
    (True, False): (25321, "013d67c1e4324dc3d036b23bd7a85f42200b6786daf8a89f426281745e326124"),
    (True, True): (26472, "cf77f10b54846e9492f7714a16b1bcf3607e6f1faaf788a8713105d064962f19"),
}


@pytest.mark.parametrize(("flag_single", "merge"), list(_GOLDEN))
def test_distribution_rows_sql_is_pinned(flag_single: bool, merge: bool) -> None:
    import hashlib

    kwargs = {"include_flag_single": flag_single, "age_condition": " AND x = :y", "merge_same_post": merge}
    sql = svc.distribution_rows_sql(**kwargs)
    assert (len(sql), hashlib.sha256(sql.encode()).hexdigest()) == _GOLDEN[(flag_single, merge)]
    head, final = svc.distribution_rows_parts(**kwargs)
    assert sql == f"{head}\n        {final}"


def test_parts_head_has_dist_base_and_final_is_plain_when_not_merged() -> None:
    head, final = svc.distribution_rows_parts(**_COND, merge_same_post=False)
    assert "dist_base AS (" in head and "dist_groups" not in head
    assert final == svc.distribution_final_select_plain()
    head_m, final_m = svc.distribution_rows_parts(**_COND, merge_same_post=True)
    assert head_m.startswith(head) and head_m.rstrip().endswith("dist_merged AS (SELECT * FROM dist_agg WHERE rn = 1)")
    assert final_m != final


def test_distribution_sql_has_no_double_underscore_alias() -> None:
    """在庫表の1文は __kind, __total, __ord, __f_* を足す。配信行の列に `__` で始まる名前があると衝突する。"""
    import re

    for merge in (False, True):
        head, final = svc.distribution_rows_parts(**_COND, merge_same_post=merge)
        assert not re.search(r"\bAS\s+__", head + final)


# --- 便3（検索と提供者）: PostgreSQL 不要の試験 -----------------------------------------------------------------
# 共通ベクタ: frontend/src/features/inventory/searchNormalize.vectors.json（frontend の vitest も同じ物を読む）。
# ベクタを変えるときは、このファイルと frontend/src/features/inventory/searchNormalize.test.ts の両方を触ること。

_NONE_FILTERS = dict.fromkeys(("q", "tcg_type", "category", "offer_type", "hide_supplier_ids", "hide_categories",
                               "condition", "condition_in", "unit_in", "offer_type_in", "qty_min", "qty_max",
                               "price_min", "price_max"))


def test_bin3_normalize_search_text_matches_the_shared_vectors() -> None:
    import json
    import pathlib

    from app.routers.inventory_offers import normalize_search_text

    path = pathlib.Path(__file__).resolve().parents[2] / "frontend/src/features/inventory/searchNormalize.vectors.json"
    vectors = json.loads(path.read_text())
    assert len(vectors) >= 10
    for v in vectors:
        assert normalize_search_text(v["input"]) == v["expected"], v


def test_bin3_kana_tables_are_86_chars_each() -> None:
    from app.routers.inventory_offers import _KANA_FROM, _KANA_TO

    assert len(_KANA_FROM) == len(_KANA_TO) == 86
    assert _KANA_FROM[0] == "ぁ" and _KANA_TO[0] == "ァ" and _KANA_FROM[-1] == "ゖ" and _KANA_TO[-1] == "ヶ"


def test_bin3_search_builds_one_strpos_per_term_and_caps_terms() -> None:
    from app.routers.inventory_offers import _SEARCH_MAX_TERMS, _build_view_filters

    conds, params = _build_view_filters(**{**_NONE_FILTERS, "q": "ぽけもん ＡＢＣ"})
    assert len(conds) == 2 and all(c.startswith("strpos(") and "CAST(:qt" in c for c in conds)
    assert (params["qt0"], params["qt1"]) == ("ポケモン", "abc")
    assert "provider" not in conds[0] and "product_id" not in conds[0] and "category" not in conds[0]
    assert "d.search_keywords" in conds[0] and "d.mark" in conds[0]
    many, many_params = _build_view_filters(**{**_NONE_FILTERS, "q": " ".join(f"w{i}" for i in range(30))})
    assert len(many) == _SEARCH_MAX_TERMS == 10 and f"qt{_SEARCH_MAX_TERMS}" not in many_params
    assert _build_view_filters(**{**_NONE_FILTERS, "q": "   "}) == ([], {})


def test_bin3_supplier_ids_filter_takes_integers_only() -> None:
    from app.routers.inventory_offers import _build_view_filters

    assert _build_view_filters(**_NONE_FILTERS) == ([], {})  # supplier_ids は既定値 None（既存の呼び出しは変わらない）
    conds, params = _build_view_filters(**_NONE_FILTERS, supplier_ids="1, x ,2")
    assert conds == ["d.supplier_id IN (:sid0, :sid1)"] and params == {"sid0": 1, "sid1": 2}
    assert _build_view_filters(**_NONE_FILTERS, supplier_ids="x,y") == ([], {})
    assert _build_view_filters(**_NONE_FILTERS, supplier_ids="") == ([], {})
    conds, params = _build_view_filters(**{**_NONE_FILTERS, "hide_supplier_ids": "3"}, supplier_ids="1")
    assert "d.supplier_id IN (:sid0)" in conds and "d.supplier_id NOT IN (:hsid0)" in conds


def test_bin3_endpoint_has_supplier_ids_query() -> None:
    import inspect

    from app.routers import inventory_offers as io

    p = inspect.signature(io.list_inventory_view).parameters["supplier_ids"]
    assert p.default.default is None
    assert any(getattr(m, "max_length", None) == 2000 for m in p.default.metadata)
