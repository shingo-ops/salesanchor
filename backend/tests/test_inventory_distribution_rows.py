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


def test_flag_single_changes_condition_filter() -> None:
    off = svc.distribution_rows_sql(include_flag_single=False, age_condition="", merge_same_post=False)
    on = svc.distribution_rows_sql(include_flag_single=True, age_condition="", merge_same_post=False)
    assert "FLAG_SINGLE" not in off and "FLAG_SINGLE" in on
    assert "IS DISTINCT FROM 'EXCLUDE'" in off and "IS DISTINCT FROM 'EXCLUDE'" in on


def test_fetch_functions_do_not_define_their_own_where() -> None:
    import inspect

    assert "ar.pid_resolved" not in inspect.getsource(svc.fetch_output_rows)
    # プレビューの件数は同じ関数を使う（除外の内訳は解析の行単位の数え方のまま別に残る）
    assert "distribution_rows_sql(" in inspect.getsource(svc.fetch_preview_data)


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
