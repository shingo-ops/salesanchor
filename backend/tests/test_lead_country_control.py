from __future__ import annotations

import os
from contextlib import ExitStack

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import AsyncMock, patch

from app.auth.dependencies import get_current_tenant, get_current_user
from app.database import get_db
from app.models import User
from app.routers import leads as leads_router
from scripts.migrate_20260621_020000_backfill_lead_country import backfill_schema

ADMIN_PG_URL = os.getenv("RLS_ADMIN_DATABASE_URL") or os.getenv("TEST_PG_URL")
APP_PG_URL = os.getenv("RLS_TEST_DATABASE_URL")


def _mock_user(tenant_id: int = 999):
    user = User()
    user.id = 999
    user.tenant_id = tenant_id
    user.username = "country-tester"
    user.email = "country@test.example.com"
    user.role = "admin"
    user.is_active = True
    return user


@pytest.mark.asyncio
async def test_lead_country_create_and_update_normalizes_with_sqlite(client):
    create = await client.post(
        "/api/v1/leads",
        json={
            "customer_name": "Country Validation Lead",
            "country": "Japan",
        },
    )
    assert create.status_code == 201, create.text
    body = create.json()
    assert body["country"] == "JP"

    lead_id = body["id"]
    patch_res = await client.patch(
        f"/api/v1/leads/{lead_id}",
        json={"country": "us"},
    )
    assert patch_res.status_code == 200, patch_res.text
    assert patch_res.json()["country"] == "US"

    invalid = await client.post(
        "/api/v1/leads",
        json={
            "customer_name": "Invalid Country Lead",
            "country": "Not-A-Country",
        },
    )
    assert invalid.status_code == 422


@pytest.mark.skipif(
    not ADMIN_PG_URL or not APP_PG_URL,
    reason="実 PostgreSQL 環境が必要 (RLS_ADMIN_DATABASE_URL / RLS_TEST_DATABASE_URL / TEST_PG_URL 未設定)。",
)
@pytest.mark.asyncio
async def test_lead_country_backfill_and_rls_readability_under_tenant_006():
    admin_engine = create_async_engine(ADMIN_PG_URL, echo=False)
    app_engine = create_async_engine(APP_PG_URL, echo=False)
    app_session_factory = sessionmaker(app_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with app_session_factory() as session:
            yield session

    leads_to_cleanup: list[int] = []

    try:
        async with admin_engine.connect() as conn:
            tenant_row = await conn.execute(
                text("SELECT id FROM public.tenants WHERE tenant_code = 'tenant_006'")
            )
            tenant_id = tenant_row.scalar_one_or_none()
        assert tenant_id is not None

        async def override_get_current_user():
            return _mock_user(tenant_id=tenant_id)

        async def override_get_current_tenant():
            return tenant_id

        schema = "tenant_006"
        async with admin_engine.begin() as conn:
            result = await conn.execute(
                text(
                    f"""
                    INSERT INTO {schema}.leads (tenant_id, customer_name, status, country)
                    VALUES (:tenant_id, :customer_name, 'lead', :country)
                    RETURNING id
                    """
                ),
                {"tenant_id": tenant_id, "customer_name": "Backfill JP", "country": "Japan"},
            )
            lead_jp = result.scalar_one()
            leads_to_cleanup.append(lead_jp)

            result = await conn.execute(
                text(
                    f"""
                    INSERT INTO {schema}.leads (tenant_id, customer_name, status, country)
                    VALUES (:tenant_id, :customer_name, 'lead', :country)
                    RETURNING id
                    """
                ),
                {"tenant_id": tenant_id, "customer_name": "Backfill Invalid", "country": "Atlantis"},
            )
            lead_invalid = result.scalar_one()
            leads_to_cleanup.append(lead_invalid)

        async with admin_engine.begin() as conn:
            counts = await backfill_schema(conn, schema)

        assert int(counts["normalized"]) >= 1
        assert int(counts["nulled"]) >= 1

        app = FastAPI()
        app.include_router(leads_router.router, prefix="/api/v1")
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
        app.dependency_overrides[get_current_tenant] = override_get_current_tenant

        with ExitStack() as stack:
            stack.enter_context(
                patch("app.routers.leads.invalidate_dashboard_cache", new=AsyncMock(return_value=None))
            )
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                lead_res = await ac.get(f"/api/v1/leads/{lead_jp}")
                assert lead_res.status_code == 200
                assert lead_res.json()["country"] == "JP"

        async with app_session_factory() as session:
            async with session.begin():
                await session.execute(
                    text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
                    {"tenant_id": str(tenant_id)},
                )
                country_count = (
                    await session.execute(text("SELECT count(*) FROM public.countries"))
                ).scalar_one()
                assert country_count == 190
                lead_rows = []
                for lead_id in leads_to_cleanup:
                    row = await session.execute(
                        text(f"SELECT country FROM {schema}.leads WHERE id = :id"),
                        {"id": lead_id},
                    )
                    lead_rows.append(row.scalar_one_or_none())
                assert set(lead_rows) == {"JP", None}
    finally:
        async with admin_engine.begin() as conn:
            if leads_to_cleanup:
                for lead_id in leads_to_cleanup:
                    await conn.execute(
                        text("DELETE FROM tenant_006.leads WHERE id = :id"),
                        {"id": lead_id},
                    )
        await admin_engine.dispose()
        await app_engine.dispose()
