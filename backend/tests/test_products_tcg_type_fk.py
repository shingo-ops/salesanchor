from __future__ import annotations

import os
from contextlib import ExitStack
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


def _mock_user(tenant_id: int) -> User:
    user = User()
    user.id = 9006
    user.tenant_id = tenant_id
    user.username = "tcg-type-tester"
    user.email = "tcg-type@test.example.com"
    user.role = "admin"
    user.is_active = True
    return user


def _tcg_type_seed_rows() -> list[tuple[str, str, str | None]]:
    return [
        ("pokemon_booster_box", "ポケモンカード", "Pokémon Card"),
        ("one_piece", "ワンピース", "One Piece TCG"),
        ("dragon_ball", "ドラゴンボール", "Dragon Ball TCG"),
        ("union_arena", "ユニオンアリーナ", "Union Arena"),
        ("yugioh", "遊戯王", "Yu-Gi-Oh!"),
        ("other", "その他", "Other"),
        ("gundam", "ガンダムカードゲーム", "Gundam Card Game"),
        ("weiss_schwarz", "ヴァイスシュヴァルツ", "Weiß Schwarz"),
        ("digimon", "デジモンカードゲーム", "Digimon Card Game"),
        ("hololive", "ホロライブ", "hololive Official Card Game"),
        ("lorcana", "ディズニー ロルカナ", "Disney Lorcana"),
        ("xross_stars", "クロススタァ", "Xross Stars"),
    ]


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

    try:
        async with admin_engine.begin() as conn:
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS public.tcg_type_master (
                    code VARCHAR(50) PRIMARY KEY,
                    name_ja VARCHAR(100) NOT NULL,
                    name_en VARCHAR(100),
                    sort_order INTEGER NOT NULL DEFAULT 100,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE
                )
            """))
            for code, name_ja, name_en in _tcg_type_seed_rows():
                await conn.execute(
                    text("""
                        INSERT INTO public.tcg_type_master (code, name_ja, name_en, sort_order, is_active)
                        VALUES (:code, :name_ja, :name_en, 100, TRUE)
                        ON CONFLICT (code) DO NOTHING
                    """),
                    {"code": code, "name_ja": name_ja, "name_en": name_en},
                )

        async with admin_engine.connect() as conn:
            schema_exists = await conn.scalar(
                text("SELECT 1 FROM information_schema.schemata WHERE schema_name = 'tenant_006'")
            )
        if not schema_exists:
            pytest.skip("tenant_006 schema is not present in this CI PostgreSQL database")
        tenant_id = 6

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
