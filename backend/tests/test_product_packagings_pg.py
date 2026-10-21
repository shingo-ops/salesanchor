"""ADR-1028 便3: 入数・重さを荷姿の表（public.product_packagings）から読み書きする（実 PostgreSQL・巻き戻す schema）。"""
from pathlib import Path
from types import SimpleNamespace

import pytest
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

MIGRATIONS = Path(__file__).resolve().parents[2] / "migrations"

# 試験用の public.products は本番より列が少ない。商品 API が読み書きする列を、巻き戻す schema の中だけで足す
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
    # 荷姿の表と単位の行（PACK/BOX/CASE）は product_db が transaction の外で一度だけ確定させている（ensure_product_packagings）

    async def _perms(*_args, **_kwargs):
        return {"products.view", "products.create", "products.update"}

    async def _no_audit(*_args, **_kwargs):
        return None

    monkeypatch.setattr(auth_deps, "load_user_permissions", _perms)
    monkeypatch.setattr(products_router, "record_audit_log", _no_audit)
    # 9項目の検査はこの試験の対象ではない
    monkeypatch.setattr("app.routers.products.check_required_fields", lambda *a, **k: [])

    def make():
        app = FastAPI()
        app.include_router(products_router.router, prefix="/api/v1")
        app.dependency_overrides[products_router.get_db] = lambda: db
        app.dependency_overrides[auth_deps.get_db] = lambda: db
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=7, is_super_admin=False)
        app.dependency_overrides[get_current_tenant] = lambda: 1
        return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    return db, make


async def _units(db) -> dict:
    return dict((await db.execute(text("SELECT code, id FROM public.quantity_units"))).all())


async def _product(db, code, *, tenant_id=None) -> int:
    row = await db.execute(
        text("INSERT INTO public.products (product_code, name, tenant_id) VALUES (:c, 'JA', :t) RETURNING id"),
        {"c": code, "t": tenant_id},
    )
    return row.scalar_one()


async def _pack(db, pid, unit, *, contained=None, count=None, count_source=None, count_urls=(),
                weight=None, weight_source=None, weight_urls=(), by="seed"):
    ids = await _units(db)
    await db.execute(
        text(
            "INSERT INTO public.product_packagings (product_id, unit_id, contained_unit_id, contained_count, "
            "count_source, count_source_urls, weight_kg, weight_source, weight_source_urls, updated_by) "
            "VALUES (:p, :u, :cu, :cnt, :cs, :curls, :w, :ws, :wurls, :by)"
        ),
        {
            "p": pid, "u": ids[unit], "cu": ids[contained] if contained else None, "cnt": count,
            "cs": count_source, "curls": list(count_urls), "w": weight, "ws": weight_source,
            "wurls": list(weight_urls), "by": by,
        },
    )


async def _rows(db, pid) -> dict:
    result = await db.execute(
        text(
            "SELECT u.code AS unit, cu.code AS contained, pk.contained_count, pk.count_source, "
            "pk.count_source_urls, pk.weight_kg, pk.weight_source, pk.weight_source_urls, pk.updated_by "
            "FROM public.product_packagings pk JOIN public.quantity_units u ON u.id = pk.unit_id "
            "LEFT JOIN public.quantity_units cu ON cu.id = pk.contained_unit_id "
            "WHERE pk.product_id = :p"
        ),
        {"p": pid},
    )
    return {r["unit"]: dict(r) for r in result.mappings().all()}


async def _seed_standard(db, pid):
    await _pack(db, pid, "CASE", contained="BOX", count=12, count_source="official",
                count_urls=["https://example.com/a"], weight=6.5, weight_source="official",
                weight_urls=["https://example.com/w"])
    await _pack(db, pid, "BOX", contained="PACK", count=20, count_source="legacy",
                weight=0.236, weight_source="legacy")


async def test_t1_get_reads_four_fields_from_table(client_factory):
    db, make = client_factory
    pid = await _product(db, "T1-A")
    await _seed_standard(db, pid)
    async with make() as client:
        detail = (await client.get(f"/api/v1/products/{pid}")).json()
        listing = (await client.get("/api/v1/products", params={"search": "T1-A"})).json()
    for body in (detail, listing[0]):
        assert body["boxes_per_case"] == 12
        assert float(body["case_weight_kg"]) == 6.5
        assert body["packs_per_box"] == 20
        assert float(body["box_weight_kg"]) == 0.236
        assert len(body["packagings"]) == 2


async def test_t2_patch_changes_count_and_marks_legacy(client_factory):
    db, make = client_factory
    pid = await _product(db, "T2-A")
    await _seed_standard(db, pid)
    async with make() as client:
        response = await client.patch(f"/api/v1/products/{pid}", json={"boxes_per_case": 10})
    assert response.status_code == 200, response.text
    assert response.json()["boxes_per_case"] == 10
    case = (await _rows(db, pid))["CASE"]
    assert case["contained_count"] == 10 and case["count_source"] == "legacy"
    assert case["count_source_urls"] == [] and case["contained"] == "BOX"
    assert float(case["weight_kg"]) == 6.5 and case["weight_source"] == "official"
    assert case["weight_source_urls"] == ["https://example.com/w"]
    old = (await db.execute(text("SELECT boxes_per_case FROM public.products WHERE id = :i"), {"i": pid})).scalar_one()
    assert old is None


async def test_t3_same_values_leave_rows_untouched(client_factory):
    db, make = client_factory
    pid = await _product(db, "T3-A")
    await _seed_standard(db, pid)
    before = await _rows(db, pid)
    async with make() as client:
        response = await client.patch(f"/api/v1/products/{pid}", json={
            "boxes_per_case": 12, "case_weight_kg": "6.500", "packs_per_box": 20, "box_weight_kg": "0.236",
        })
    assert response.status_code == 200, response.text
    assert await _rows(db, pid) == before
    # updated_at ではなく updated_by で比べる: 同じ transaction 内では NOW() が同じ値になり、updated_at では更新の有無を見分けられない
    assert all(r["updated_by"] == "seed" for r in before.values())


async def test_t4_null_clears_value_and_deletes_empty_row(client_factory):
    db, make = client_factory
    pid = await _product(db, "T4-A")
    await _seed_standard(db, pid)
    async with make() as client:
        r1 = await client.patch(f"/api/v1/products/{pid}", json={"box_weight_kg": None})
        assert r1.status_code == 200, r1.text
        box = (await _rows(db, pid))["BOX"]
        assert box["weight_kg"] is None and box["weight_source"] is None and box["weight_source_urls"] == []
        assert box["contained_count"] == 20
        r2 = await client.patch(f"/api/v1/products/{pid}", json={"packs_per_box": None})
        assert r2.status_code == 200, r2.text
    assert "BOX" not in await _rows(db, pid)
    assert "CASE" in await _rows(db, pid)


async def test_t5_post_writes_table_not_old_columns(client_factory):
    db, make = client_factory
    async with make() as client:
        response = await client.post("/api/v1/products", json={
            "name_ja": "T5 商品", "boxes_per_case": 12, "packs_per_box": 20,
            "box_weight_kg": "0.236", "case_weight_kg": "6.500",
        })
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["boxes_per_case"] == 12 and body["packs_per_box"] == 20
    assert len(body["packagings"]) == 2
    rows = await _rows(db, body["id"])
    assert set(rows) == {"CASE", "BOX"}
    assert rows["CASE"]["count_source"] == "legacy" and rows["BOX"]["weight_source"] == "legacy"
    assert rows["CASE"]["count_source_urls"] == [] and rows["CASE"]["weight_source_urls"] == []
    assert rows["BOX"]["count_source_urls"] == [] and rows["BOX"]["weight_source_urls"] == []
    assert rows["CASE"]["contained"] == "BOX" and rows["BOX"]["contained"] == "PACK"
    old = (await db.execute(
        text("SELECT boxes_per_case, packs_per_box, box_weight_kg, case_weight_kg FROM public.products WHERE id = :i"),
        {"i": body["id"]},
    )).first()
    assert tuple(old) == (None, None, None, None)


async def test_t6_zero_is_422(client_factory):
    db, make = client_factory
    pid = await _product(db, "T6-A")
    async with make() as client:
        response = await client.patch(f"/api/v1/products/{pid}", json={"boxes_per_case": 0})
    assert response.status_code == 422


async def test_t7_case_contained_pack_is_not_boxes_per_case(client_factory):
    db, make = client_factory
    pid = await _product(db, "T7-A")
    await _pack(db, pid, "CASE", contained="PACK", count=8, count_source="legacy")
    async with make() as client:
        assert (await client.get(f"/api/v1/products/{pid}")).json()["boxes_per_case"] is None
        response = await client.patch(f"/api/v1/products/{pid}", json={"boxes_per_case": 8})
        assert response.status_code == 200, response.text
    case = (await _rows(db, pid))["CASE"]
    assert case["contained"] == "BOX" and case["contained_count"] == 8


async def test_t8_tenant_product_is_rejected(client_factory):
    db, make = client_factory
    pid = await _product(db, "T8-A", tenant_id=1)
    async with make() as client:
        response = await client.patch(f"/api/v1/products/{pid}", json={"boxes_per_case": 5})
    assert response.status_code == 422
    assert response.json()["detail"] == "PACKAGING_SHARED_ONLY"
    assert await _rows(db, pid) == {}


async def test_t9_shared_row_without_operator_is_403_and_nothing_changes(client_factory):
    db, make = client_factory
    has_role = (await db.execute(text("SELECT 1 FROM pg_roles WHERE rolname = 'salesanchor_app'"))).first()
    if has_role is None:
        pytest.skip("salesanchor_app ロールが無い環境（ローカル）。CI では有る（.github/workflows/test.yml:187-205）")
    pid = await _product(db, "T9-A")
    await _seed_standard(db, pid)
    before = await _rows(db, pid)
    await fixtures._exec_multi_stmt(
        await db.connection(), (MIGRATIONS / "20260626_130000_force_rls_public_products.sql").read_text()
    )
    await db.execute(text("SET LOCAL ROLE salesanchor_app"))
    try:
        async with make() as client:
            response = await client.patch(f"/api/v1/products/{pid}", json={"boxes_per_case": 10, "moq": 3})
    finally:
        await db.execute(text("RESET ROLE"))
    assert response.status_code == 403, response.text
    assert response.json()["detail"] == "PRODUCT_NOT_WRITABLE"
    assert await _rows(db, pid) == before
    moq = (await db.execute(text("SELECT moq FROM public.products WHERE id = :i"), {"i": pid})).scalar_one()
    assert moq is None
