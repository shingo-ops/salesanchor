"""Inventory API 実 DB smoke.

public.inventory の実 row を seed し、/api/v1/inventory の実レスポンスで
best-pick / view_mode toggle / tenant best-fixed を確認する。
"""

from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Iterable
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

TEST_PG_URL = os.getenv("TEST_PG_URL") or os.getenv("RLS_TEST_DATABASE_URL")
SETUP_DB_URL = os.getenv("RLS_ADMIN_DATABASE_URL") or TEST_PG_URL

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(
        not TEST_PG_URL,
        reason="実 PostgreSQL 環境が必要 (TEST_PG_URL / RLS_TEST_DATABASE_URL 未設定)。",
    ),
]


async def _ensure_smoke_schema(engine) -> None:
    """空の実 Postgres でも smoke できるよう最小 schema を idempotent に整える。"""

    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS public.suppliers (
                    id BIGSERIAL PRIMARY KEY,
                    supplier_code VARCHAR(20) UNIQUE,
                    name VARCHAR(255) NOT NULL,
                    supplier_type VARCHAR(20) NOT NULL DEFAULT 'corporate',
                    default_language CHAR(2) NOT NULL DEFAULT 'ja',
                    contact_name VARCHAR(255),
                    email VARCHAR(255),
                    phone VARCHAR(50),
                    address TEXT,
                    notes TEXT,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    created_by INTEGER,
                    line_name VARCHAR(255),
                    postal_code VARCHAR(20),
                    prefecture VARCHAR(50),
                    city VARCHAR(100),
                    address1 VARCHAR(255),
                    address2 VARCHAR(255),
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
        )
        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS public.products (
                    id BIGSERIAL PRIMARY KEY,
                    product_code VARCHAR(50),
                    name VARCHAR(255) NOT NULL,
                    name_en VARCHAR(255),
                    description TEXT,
                    unit_price NUMERIC(15, 2),
                    unit_price_usd NUMERIC(15, 2),
                    unit_price_eur NUMERIC(15, 2),
                    stock_quantity INTEGER NOT NULL DEFAULT 0,
                    jan_code VARCHAR(20),
                    card_number VARCHAR(50),
                    expansion_code VARCHAR(20),
                    rarity VARCHAR(20),
                    language VARCHAR(10),
                    image_url VARCHAR(500),
                    is_archived BOOLEAN NOT NULL DEFAULT FALSE,
                    archived_at TIMESTAMPTZ,
                    supplier_default_id INTEGER REFERENCES public.suppliers(id) ON DELETE SET NULL,
                    category VARCHAR(100),
                    mark VARCHAR(100),
                    status VARCHAR(20) DEFAULT 'active',
                    condition VARCHAR(50),
                    weight NUMERIC(10, 3),
                    notes TEXT,
                    tcg_type VARCHAR(50),
                    product_kind VARCHAR(50) DEFAULT 'TCG',
                    set_type VARCHAR(50),
                    unit VARCHAR(20),
                    boxes_per_case INTEGER,
                    packs_per_box INTEGER,
                    box_weight_kg NUMERIC(8, 3),
                    case_weight_kg NUMERIC(8, 3),
                    release_date DATE,
                    moq INTEGER,
                    hs_code VARCHAR(20),
                    material VARCHAR(50),
                    volume_weight NUMERIC(8, 3),
                    search_keywords TEXT,
                    exclude_keywords TEXT,
                    related_series VARCHAR(255),
                    category_classification VARCHAR(100),
                    required_output_value VARCHAR(255),
                    item VARCHAR(255),
                    display_order INTEGER,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
        )
        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS public.inventory (
                    id BIGSERIAL PRIMARY KEY,
                    supplier_id INTEGER NOT NULL REFERENCES public.suppliers(id) ON DELETE CASCADE,
                    product_id INTEGER NOT NULL REFERENCES public.products(id) ON DELETE RESTRICT,
                    condition VARCHAR(50) NOT NULL,
                    quantity INTEGER NOT NULL DEFAULT 0,
                    unit_price INTEGER NOT NULL DEFAULT 0,
                    unit VARCHAR(20),
                    offer_type VARCHAR(20) NOT NULL DEFAULT 'in_stock',
                    ship_timing VARCHAR(20),
                    status VARCHAR(20) NOT NULL DEFAULT 'in_stock',
                    notes_ja TEXT,
                    notes_en TEXT,
                    offered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    expires_at TIMESTAMPTZ,
                    source VARCHAR(50) NOT NULL DEFAULT 'manual',
                    source_kind VARCHAR(10) NOT NULL DEFAULT 'B_feed',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
        )
        await conn.execute(
            text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_inventory_offer_key
                    ON public.inventory (
                        supplier_id, product_id, condition,
                        COALESCE(unit, ''), offer_type, COALESCE(ship_timing, '')
                    )
                """
            )
        )
        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS public.inventory_aggregation_rules (
                    id BIGSERIAL PRIMARY KEY,
                    condition TEXT NOT NULL UNIQUE,
                    price_tolerance INTEGER NOT NULL CHECK (price_tolerance >= 0),
                    stock_tolerance INTEGER NOT NULL CHECK (stock_tolerance >= 0),
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
        )
        await conn.execute(
            text(
                """
                INSERT INTO public.inventory_aggregation_rules
                    (condition, price_tolerance, stock_tolerance)
                VALUES
                    ('Case', 1000, 5),
                    ('Sealed box', 100, 30),
                    ('Damaged sealed box', 100, 10),
                    ('No shrink box', 100, 5)
                ON CONFLICT (condition) DO UPDATE SET
                    price_tolerance = EXCLUDED.price_tolerance,
                    stock_tolerance = EXCLUDED.stock_tolerance,
                    updated_at = NOW()
                """
            )
        )


async def _seed_inventory_smoke(engine) -> dict[str, object]:
    tag = uuid.uuid4().hex[:8]
    offered_at_base = datetime(2026, 6, 20, 12, 0, 0, tzinfo=timezone.utc)

    async with engine.begin() as conn:
        product_id = (
            await conn.execute(
                    text(
                        """
                        INSERT INTO public.products
                        (product_code, category, mark, name, name_en,
                         required_output_value, release_date, unit, tcg_type)
                    VALUES
                        (:code, 'Pokemon', 'SMOKE', :name, :name_en,
                         :series, DATE '2026-09-16', 'box', 'pokemon_booster_box')
                    RETURNING id
                    """
                ),
                {
                    "code": f"SMOKE-PRODUCT-{tag}",
                    "name": "拡張パック 30th CELEBRATION",
                    "name_en": "Expansion Pack 30th Celebration",
                    "series": "拡張パック 30th CELEBRATION",
                },
            )
        ).scalar_one()

        supplier_rows = [
            ("Supplier A", 1000, 5, 0),
            ("Supplier B", 1050, 60, 1),
            ("Supplier C", 1200, 100, 2),
        ]
        supplier_ids: list[int] = []
        inventory_ids: list[int] = []
        for name, price, qty, offset in supplier_rows:
            supplier_id = (
                await conn.execute(
                    text(
                        """
                        INSERT INTO public.suppliers
                            (supplier_code, name, supplier_type, default_language)
                        VALUES
                            (:code, :name, 'corporate', 'ja')
                        RETURNING id
                        """
                    ),
                    {"code": f"SMOKE-SUP-{tag}-{offset}", "name": name},
                )
            ).scalar_one()
            supplier_ids.append(int(supplier_id))
            inventory_id = (
                await conn.execute(
                    text(
                        """
                        INSERT INTO public.inventory
                            (supplier_id, product_id, condition, quantity, unit_price,
                             unit, offer_type, ship_timing, status, notes_ja, notes_en,
                             offered_at, expires_at, source, source_kind)
                        VALUES
                            (:supplier_id, :product_id, 'Sealed box', :quantity, :unit_price,
                             'box', 'in_stock', NULL, 'in_stock', NULL, NULL,
                             :offered_at, :expires_at, 'manual', 'B_feed')
                        RETURNING id
                        """
                    ),
                    {
                        "supplier_id": supplier_id,
                        "product_id": product_id,
                        "quantity": qty,
                        "unit_price": price,
                        "offered_at": offered_at_base + timedelta(minutes=offset),
                        "expires_at": offered_at_base + timedelta(days=1),
                    },
                )
            ).scalar_one()
            inventory_ids.append(int(inventory_id))

    return {
        "product_id": int(product_id),
        "supplier_ids": supplier_ids,
        "inventory_ids": inventory_ids,
        "tag": tag,
    }


async def _cleanup_inventory_smoke(engine, seed: dict[str, object]) -> None:
    async with engine.begin() as conn:
        if seed.get("inventory_ids"):
            await conn.execute(
                text("DELETE FROM public.inventory WHERE id = ANY(:ids)"),
                {"ids": seed["inventory_ids"]},
            )
        if seed.get("supplier_ids"):
            await conn.execute(
                text("DELETE FROM public.suppliers WHERE id = ANY(:ids)"),
                {"ids": seed["supplier_ids"]},
            )
        if seed.get("product_id"):
            await conn.execute(
                text("DELETE FROM public.products WHERE id = :pid"),
                {"pid": seed["product_id"]},
            )


@asynccontextmanager
async def _inventory_client(
    engine,
    permission_keys: Iterable[str],
    *,
    user_id: int,
    tenant_id: int,
    is_super_admin: bool,
):
    from app.auth.dependencies import get_current_tenant, get_current_user
    from app.database import get_db
    from app.main import app
    from app.models import User

    SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with SessionLocal() as session:
            yield session

    async def override_get_current_user():
        user = User()
        user.id = user_id
        user.tenant_id = tenant_id
        user.username = "inventory-smoke"
        user.email = "inventory-smoke@example.com"
        user.role = "admin" if is_super_admin else "staff"
        user.is_active = True
        user.is_super_admin = is_super_admin
        return user

    async def override_get_current_tenant():
        return tenant_id

    async def fake_load_user_permissions(_db, _tenant_id, _user_id):
        return set(permission_keys)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_current_tenant] = override_get_current_tenant

    transport = ASGITransport(app=app)
    try:
        with patch("app.auth.dependencies.load_user_permissions", fake_load_user_permissions):
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                yield client
    finally:
        app.dependency_overrides.clear()


async def _assert_best_row(payload: dict[str, object], *, supplier_name: str) -> dict[str, object]:
    assert payload["total"] == 1
    assert len(payload["items"]) == 1
    item = payload["items"][0]
    assert item["supplier_name"] == supplier_name
    assert item["is_best"] is True
    assert item["best_reason_category"] == "stock_priority"
    assert str(item["best_reason"]).startswith("在庫優先")
    return item


async def test_inventory_api_smoke_real_db_view_modes_and_tenant_best_fixed():
    if not SETUP_DB_URL:
        pytest.skip("DDL 用 PostgreSQL 接続が無いため smoke schema を準備できない。")

    setup_engine = create_async_engine(SETUP_DB_URL, echo=False)
    api_engine = create_async_engine(TEST_PG_URL, echo=False)
    seed: dict[str, object] | None = None
    try:
        await _ensure_smoke_schema(setup_engine)
        seed = await _seed_inventory_smoke(setup_engine)

        async with api_engine.connect() as conn:
            count = (
                await conn.execute(
                    text("SELECT COUNT(*) FROM public.inventory WHERE product_id = :pid"),
                    {"pid": seed["product_id"]},
                )
            ).scalar_one()
        assert count == 3

        staff_perms = {"products.view", "quotes.create"}
        tenant_perms = {"products.view"}

        async with _inventory_client(
            api_engine,
            staff_perms,
            user_id=5101,
            tenant_id=6,
            is_super_admin=False,
        ) as staff_client:
            resp_all = await staff_client.get("/api/v1/inventory", params={"view_mode": "all"})
            assert resp_all.status_code == 200
            all_payload = resp_all.json()
            assert all_payload["total"] == 3
            assert {item["supplier_name"] for item in all_payload["items"]} == {
                "Supplier A",
                "Supplier B",
                "Supplier C",
            }
            best_items = [item for item in all_payload["items"] if item["is_best"]]
            assert len(best_items) == 1
            assert best_items[0]["supplier_name"] == "Supplier B"
            assert best_items[0]["best_reason_category"] == "stock_priority"
            assert "価格差50円" in best_items[0]["best_reason"]

            resp_best = await staff_client.get("/api/v1/inventory", params={"view_mode": "best"})
            assert resp_best.status_code == 200
            best_payload = resp_best.json()
            best_item = await _assert_best_row(best_payload, supplier_name="Supplier B")
            assert best_item["product_id"] == seed["product_id"]

        async with _inventory_client(
            api_engine,
            tenant_perms,
            user_id=5102,
            tenant_id=6,
            is_super_admin=False,
        ) as tenant_client:
            resp_forbidden = await tenant_client.get("/api/v1/inventory", params={"view_mode": "all"})
            assert resp_forbidden.status_code == 403

            resp_tenant_best = await tenant_client.get("/api/v1/inventory", params={"view_mode": "best"})
            assert resp_tenant_best.status_code == 200
            tenant_payload = resp_tenant_best.json()
            tenant_best = await _assert_best_row(tenant_payload, supplier_name="Supplier B")
            assert tenant_best["product_id"] == seed["product_id"]
    finally:
        if seed is not None:
            await _cleanup_inventory_smoke(setup_engine, seed)
        await setup_engine.dispose()
        await api_engine.dispose()
