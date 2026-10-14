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
# 期待値は review-excluded-ack 便（cr_review_ack LATERAL 追加）で再生成した。元は変更前（origin/main 4803be067）の distribution_rows_sql を age_condition=" AND x = :y" で呼んだ出力の
# 長さと SHA-256。旧実装をテスト内で再現せず、変更前版から生成した値を固定する。
_GOLDEN = {
    (False, False): (23948, "6417168e8a472e2e73019f7e2833751b9228cefd0b73eaf4583e51fd501f11b0"),
    (False, True): (24929, "4c8990fabcf386a946a742187d0d2e9a8ae028816707a8e5a2dad2987f2b07e6"),
    (True, False): (23982, "c7ce4b593c93ea7e7474813f8fed45596fa1ee47b608edff32688a992c54aabd"),
    (True, True): (24963, "2343c3a08c754c560c771fa9bd2c5ecdd22b3b4f1b93451d9def7add691abbad"),
}


@pytest.mark.parametrize(("flag_single", "merge"), list(_GOLDEN))
def test_distribution_rows_sql_is_byte_identical_to_before(flag_single: bool, merge: bool) -> None:
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
