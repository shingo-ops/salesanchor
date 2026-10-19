"""ADR-1020 便4a: 在庫の商品画面の口（POST/PATCH /products）の9項目検査（実 PostgreSQL・巻き戻す schema）。"""
from types import SimpleNamespace

import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.auth import dependencies as auth_deps
from app.auth.dependencies import get_current_tenant, get_current_user
from app.routers import products as products_router
from tests import test_tcg_product_list_pg as fixtures

product_db = fixtures.product_db
pytestmark = fixtures.pytestmark


# 試験用の public.products（tests/fixtures/public_products_test.sql）は本番より列が少ない。
# 在庫の商品画面の口が読み書きする列を、巻き戻す試験用 schema の中だけで足す。
_ROUTE_COLUMNS = (
    "category VARCHAR(100)", "status VARCHAR(20) NOT NULL DEFAULT 'active'", "unit_price NUMERIC(15,2)",
    "stock_quantity INTEGER NOT NULL DEFAULT 0", "weight NUMERIC(10,3)", "notes TEXT",
    "jan_code VARCHAR(20)", "card_number VARCHAR(50)", "expansion_code VARCHAR(20)", "rarity VARCHAR(20)",
    "language VARCHAR(10)", "unit_price_usd NUMERIC(15,2)", "unit_price_eur NUMERIC(15,2)",
    "image_url VARCHAR(500)", "archived_at TIMESTAMPTZ", "supplier_default_id INTEGER",
    "boxes_per_case INTEGER", "packs_per_box INTEGER", "box_weight_kg NUMERIC(8,3)", "case_weight_kg NUMERIC(8,3)",
    "volume_weight NUMERIC(8,3)", "moq INTEGER", "hs_code VARCHAR(20)", "material VARCHAR(50)", "item VARCHAR(255)",
    "search_keywords TEXT", "exclude_keywords TEXT", "related_series VARCHAR(255)",
    "product_kind VARCHAR(50)", "set_type VARCHAR(50)", "display_order INTEGER",
)


@pytest_asyncio.fixture
async def client_factory(product_db, monkeypatch):
    db, _ = product_db
    for column in _ROUTE_COLUMNS:
        await db.execute(text(f"ALTER TABLE public.products ADD COLUMN IF NOT EXISTS {column}"))

    async def _perms(*_args, **_kwargs):
        return {"products.create", "products.update"}

    async def _no_audit(*_args, **_kwargs):
        return None

    monkeypatch.setattr(auth_deps, "load_user_permissions", _perms)
    # 監査ログはテナント schema の表に書くが、試験用 schema には無い。この試験の対象ではない
    monkeypatch.setattr(products_router, "record_audit_log", _no_audit)

    def make():
        app = FastAPI()
        app.include_router(products_router.router, prefix="/api/v1")
        app.dependency_overrides[products_router.get_db] = lambda: db
        app.dependency_overrides[auth_deps.get_db] = lambda: db
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1, is_super_admin=False)
        app.dependency_overrides[get_current_tenant] = lambda: 1
        return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    return db, make


async def _insert(db, code, *, name_en=None, mark=None, tenant_id=None) -> int:
    row = await db.execute(
        text(
            "INSERT INTO public.products (product_code, name, name_en, mark, tenant_id) "
            "VALUES (:code, 'JA', :en, :mark, :tid) RETURNING id"
        ),
        {"code": code, "en": name_en, "mark": mark, "tid": tenant_id},
    )
    return row.scalar_one()


async def _row(db, pid):
    return (await db.execute(
        text("SELECT name_en, mark, notes FROM public.products WHERE id = :id"), {"id": pid}
    )).mappings().first()


async def test_post_without_nine_fields_is_422_and_creates_no_row(client_factory):
    db, make = client_factory
    before = (await db.execute(text("SELECT count(*) FROM public.products"))).scalar_one()
    async with make() as client:
        response = await client.post("/api/v1/products", json={"name_ja": "only name"})
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail.startswith("REQUIRED_FIELDS_MISSING:")
    for field in ("work_id", "product_format_id", "product_category_id", "search_keywords"):
        assert field in detail
    after = (await db.execute(text("SELECT count(*) FROM public.products"))).scalar_one()
    assert after == before


async def test_patch_clearing_valued_field_on_shared_row_is_422(client_factory):
    db, make = client_factory
    pid = await _insert(db, "BIN4A-1", name_en="English", mark="M-1")
    async with make() as client:
        response = await client.patch(f"/api/v1/products/{pid}", json={"name_en": ""})
    assert response.status_code == 422
    assert response.json()["detail"] == "REQUIRED_FIELDS_CLEARED:name_en"
    assert (await _row(db, pid))["name_en"] == "English"


async def test_patch_clearing_is_allowed_when_blank_confirmed(client_factory):
    db, make = client_factory
    pid = await _insert(db, "BIN4A-2", name_en="English", mark="M-2")
    await db.execute(
        text("INSERT INTO public.product_blank_confirmations (product_id, field_code, confirmed_by) "
             "VALUES (:pid, 'name_en', 'test')"),
        {"pid": pid},
    )
    async with make() as client:
        response = await client.patch(f"/api/v1/products/{pid}", json={"name_en": ""})
    assert response.status_code == 200, response.text


async def test_patch_leaves_old_blank_alone(client_factory):
    db, make = client_factory
    pid = await _insert(db, "BIN4A-3", name_en="English", mark=None)
    async with make() as client:
        response = await client.patch(f"/api/v1/products/{pid}", json={"notes": "memo"})
    assert response.status_code == 200, response.text
    assert (await _row(db, pid))["notes"] == "memo"


async def test_patch_on_tenant_row_is_out_of_scope(client_factory):
    db, make = client_factory
    pid = await _insert(db, "BIN4A-4", name_en="English", mark="M-4", tenant_id=1)
    async with make() as client:
        response = await client.patch(f"/api/v1/products/{pid}", json={"name_en": ""})
    assert response.status_code == 200, response.text
