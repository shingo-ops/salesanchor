from __future__ import annotations

import os
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.auth.dependencies import get_current_tenant, get_current_user
from app.database import get_db
from app.models import User
from app.routers import products as products_router

ADMIN_PG_URL = os.getenv("RLS_ADMIN_DATABASE_URL") or os.getenv("TEST_PG_URL")
APP_PG_URL = os.getenv("RLS_TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not ADMIN_PG_URL or not APP_PG_URL,
    reason="実 PostgreSQL 環境が必要 (RLS_ADMIN_DATABASE_URL / RLS_TEST_DATABASE_URL / TEST_PG_URL 未設定)。",
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MIGRATIONS_DIR = _REPO_ROOT / "migrations"
_PG_BOOTSTRAP_MIGRATIONS = [
    "056_add_suppliers_type_and_promote_public.sql",
    "062_create_inventory_movements_and_budget.sql",
    "082_extend_products_box_attributes.sql",       # products.category 追加（020000 の backfill に必須）
    "085_create_tcg_type_master.sql",
    "086_seed_additional_tcg_types.sql",
    "20260602_000000_add_products_central_columns.sql",
    "20260602_020000_add_products_tcg_type.sql",
    "20260602_030000_add_products_unit.sql",
    "20260602_170000_add_products_master_label_columns.sql",
    "20260603_000000_add_products_product_kind.sql",
    "20260603_040000_add_products_set_type.sql",        # products.set_type 追加
    "20260605_000000_add_products_display_order.sql",   # products.display_order 追加
    "20260616_000000_fix_tcg_type_dedup.sql",
    "20260623_060000_add_products_tcg_type_fk.sql",
]


def _mock_user(tenant_id: int) -> User:
    user = User()
    user.id = 9006
    user.tenant_id = tenant_id
    user.username = "tcg-type-tester"
    user.email = "tcg-type@test.example.com"
    user.role = "admin"
    user.is_active = True
    return user


def _split_sql_preserving_do_blocks(sql: str) -> list[str]:
    statements: list[str] = []
    buf: list[str] = []
    i = 0
    in_dollar = False
    dollar_tag = ""
    while i < len(sql):
        if sql[i] == "$":
            j = i + 1
            while j < len(sql) and (sql[j].isalnum() or sql[j] == "_"):
                j += 1
            if j < len(sql) and sql[j] == "$":
                tag = sql[i : j + 1]
                if not in_dollar:
                    in_dollar = True
                    dollar_tag = tag
                    buf.append(tag)
                    i = j + 1
                    continue
                if tag == dollar_tag:
                    in_dollar = False
                    dollar_tag = ""
                    buf.append(tag)
                    i = j + 1
                    continue
        if sql[i] == ";" and not in_dollar:
            statements.append("".join(buf))
            buf = []
        else:
            buf.append(sql[i])
        i += 1
    if buf:
        statements.append("".join(buf))
    return statements


async def _apply_migration(admin_engine, filename: str) -> None:
    sql = (_MIGRATIONS_DIR / filename).read_text("utf-8")
    async with admin_engine.begin() as conn:
        for stmt in _split_sql_preserving_do_blocks(sql):
            stmt = stmt.strip()
            if stmt:
                await conn.exec_driver_sql(stmt)


async def _bootstrap_public_products(admin_engine) -> None:
    for filename in _PG_BOOTSTRAP_MIGRATIONS:
        await _apply_migration(admin_engine, filename)

    async with admin_engine.connect() as conn:
        fk_exists = await conn.scalar(
            text("""
                SELECT 1
                FROM pg_constraint c
                JOIN pg_class rel ON rel.oid = c.conrelid
                JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
                WHERE nsp.nspname = 'public'
                  AND rel.relname = 'products'
                  AND c.conname = 'fk_products_tcg_type'
            """)
        )
    assert fk_exists == 1, "FK migration が public.products に適用されていません"


async def _build_app(app_session_factory, tenant_id: int) -> FastAPI:
    app = FastAPI()
    app.include_router(products_router.router, prefix="/api/v1")

    async def override_get_db():
        async with app_session_factory() as session:
            yield session

    async def override_get_current_user():
        return _mock_user(tenant_id)

    async def override_get_current_tenant():
        return tenant_id

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_current_tenant] = override_get_current_tenant
    return app


@pytest.mark.asyncio
async def test_products_tcg_type_validation_and_fk_enforcement_under_tenant_006():
    admin_engine = create_async_engine(ADMIN_PG_URL, echo=False)
    app_engine = create_async_engine(APP_PG_URL, echo=False)
    app_session_factory = sessionmaker(app_engine, class_=AsyncSession, expire_on_commit=False)
    created_ids: list[int] = []

    # tenant_id=6 は public.products.tenant_id に挿入される値。
    # tenant_006 スキーマは不要（public.products は RLS なし中央テーブル）。
    tenant_id = 6

    try:
        await _bootstrap_public_products(admin_engine)

        app = await _build_app(app_session_factory, tenant_id)

        with ExitStack() as stack:
            stack.enter_context(
                patch("app.auth.dependencies.load_user_permissions", new=AsyncMock(return_value={
                    "products.view",
                    "products.create",
                    "products.update",
                }))
            )
            stack.enter_context(
                patch("app.routers.products.invalidate_dashboard_cache", new=AsyncMock(return_value=None))
            )
            stack.enter_context(
                patch("app.routers.products.record_audit_log", new=AsyncMock(return_value=None))
            )
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                valid_create = await ac.post(
                    "/api/v1/products",
                    json={
                        "name_ja": "PG TCG 種別 OK 商品",
                        "tcg_type": "pokemon_booster_box",
                    },
                )
                assert valid_create.status_code == 201, valid_create.text
                created_ids.append(valid_create.json()["id"])
                assert valid_create.json()["tcg_type"] == "pokemon_booster_box"

                null_create = await ac.post(
                    "/api/v1/products",
                    json={
                        "name_ja": "PG TCG 種別 NULL 商品",
                        "tcg_type": None,
                    },
                )
                assert null_create.status_code == 201, null_create.text
                created_ids.append(null_create.json()["id"])
                assert null_create.json()["tcg_type"] is None

                invalid_create = await ac.post(
                    "/api/v1/products",
                    json={
                        "name_ja": "PG TCG 種別 NG 商品",
                        "tcg_type": "bogus_type",
                    },
                )
                assert invalid_create.status_code == 400, invalid_create.text
                assert "tcg_type" in invalid_create.json()["detail"]

                update_target = await ac.post(
                    "/api/v1/products",
                    json={"name_ja": "PG 更新対象商品"},
                )
                assert update_target.status_code == 201, update_target.text
                product_id = update_target.json()["id"]
                created_ids.append(product_id)

                patch_ok = await ac.patch(
                    f"/api/v1/products/{product_id}",
                    json={"tcg_type": "one_piece"},
                )
                assert patch_ok.status_code == 200, patch_ok.text
                assert patch_ok.json()["tcg_type"] == "one_piece"

                patch_ng = await ac.patch(
                    f"/api/v1/products/{product_id}",
                    json={"tcg_type": "unknown_type"},
                )
                assert patch_ng.status_code == 400, patch_ng.text
                assert "tcg_type" in patch_ng.json()["detail"]

        async with admin_engine.begin() as conn:
            null_row = await conn.execute(
                text(
                    "INSERT INTO public.products (name, stock_quantity, tcg_type) "
                    "VALUES (:name, :stock_quantity, NULL) RETURNING id, tcg_type"
                ),
                {"name": "PG FK Enforcement NULL", "stock_quantity": 0},
            )
            inserted_null = null_row.mappings().first()
            assert inserted_null is not None
            assert inserted_null["tcg_type"] is None
            created_ids.append(inserted_null["id"])

        async with admin_engine.begin() as conn:
            with pytest.raises(IntegrityError):
                await conn.execute(
                    text(
                        "INSERT INTO public.products (name, stock_quantity, tcg_type) "
                        "VALUES (:name, :stock_quantity, :tcg_type)"
                    ),
                    {
                        "name": "PG FK Enforcement NG",
                        "stock_quantity": 0,
                        "tcg_type": "unknown_type",
                    },
                )

        async with admin_engine.begin() as conn:
            ok_row = await conn.execute(
                text(
                    "INSERT INTO public.products (name, stock_quantity, tcg_type) "
                    "VALUES (:name, :stock_quantity, :tcg_type) RETURNING id, tcg_type"
                ),
                {
                    "name": "PG FK Enforcement OK",
                    "stock_quantity": 0,
                    "tcg_type": "gundam",
                },
            )
            inserted = ok_row.mappings().first()
            assert inserted is not None
            assert inserted["tcg_type"] == "gundam"
            created_ids.append(inserted["id"])
    finally:
        async with admin_engine.begin() as conn:
            for product_id in created_ids:
                await conn.execute(
                    text("DELETE FROM public.products WHERE id = :id"),
                    {"id": product_id},
                )
        await admin_engine.dispose()
        await app_engine.dispose()
