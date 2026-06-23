from __future__ import annotations

import os
from contextlib import suppress

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.auth.dependencies import get_current_tenant, get_current_user
from app.database import get_db
from app.models import User
from app.routers import analytics as analytics_router
from app.services.tenant import create_tenant_schema

ADMIN_PG_URL = os.getenv("RLS_ADMIN_DATABASE_URL") or os.getenv("TEST_PG_URL")
APP_PG_URL = os.getenv("RLS_TEST_DATABASE_URL")

TENANT_ID = 6
TENANT_SCHEMA = "tenant_006"
FOREIGN_TENANT_ID = 998
FOREIGN_SCHEMA = "tenant_998"


def _build_user(user_id: int, tenant_id: int, role: str = "admin") -> User:
    user = User()
    user.id = user_id
    user.tenant_id = tenant_id
    user.username = "analytics-rls"
    user.email = "analytics-rls@example.com"
    user.role = role
    user.is_active = True
    return user


async def _bootstrap_tenant_schema(admin_engine, tenant_id: int) -> None:
    async with admin_engine.begin() as session:
        await session.execute(text(f"DROP SCHEMA IF EXISTS tenant_{tenant_id:03d} CASCADE"))
        await create_tenant_schema(session, tenant_id, admin_db=session)


async def _seed_conversion_fixture(admin_engine, schema: str, tenant_id: int, assigned_uid: int, other_uid: int) -> dict[str, list[int]]:
    async with admin_engine.begin() as conn:
        lead_ids: list[int] = []
        company_ids: list[int] = []
        order_ids: list[int] = []

        lead_specs = [
            ("RLS-Lead-1", "instagram", "JP", "physical_store", "Hot", "24h以内", assigned_uid, 100.0),
            ("RLS-Lead-2", "instagram", "JP", "physical_store", "Warm", "3日以内", assigned_uid, 300.0),
            ("RLS-Lead-3", "cold_call", "US", None, "Cold", "3日超", assigned_uid, None),
            ("RLS-Lead-4", "messenger", "CA", "online", "Warm", "3日以内", other_uid, 9999.0),
        ]
        for customer_name, channel_type, country, sales_form, temperature, response_speed, assigned_to, monthly_forecast in lead_specs:
            row = await conn.execute(
                text(
                    f"""
                    INSERT INTO {schema}.leads (
                        tenant_id, customer_name, channel_type, country, sales_form,
                        temperature, response_speed, assigned_to, monthly_forecast, status, created_at, updated_at
                    )
                    VALUES (
                        :tenant_id, :customer_name, :channel_type, :country, :sales_form,
                        :temperature, :response_speed, :assigned_to, :monthly_forecast, 'lead', NOW(), NOW()
                    )
                    RETURNING id
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "customer_name": customer_name,
                    "channel_type": channel_type,
                    "country": country,
                    "sales_form": sales_form,
                    "temperature": temperature,
                    "response_speed": response_speed,
                    "assigned_to": assigned_to,
                    "monthly_forecast": monthly_forecast,
                },
            )
            lead_ids.append(int(row.scalar_one()))

        company_specs = [
            (lead_ids[0], "RLS-COMP-1A", "RLS Lead 1 Co A"),
            (lead_ids[0], "RLS-COMP-1B", "RLS Lead 1 Co B"),
            (lead_ids[1], "RLS-COMP-2", "RLS Lead 2 Co"),
            (lead_ids[3], "RLS-COMP-4", "RLS Lead 4 Co"),
        ]
        for lead_id, company_code, name in company_specs:
            row = await conn.execute(
                text(
                    f"""
                    INSERT INTO {schema}.companies (
                        tenant_id, company_code, lead_id, name, created_at, updated_at
                    )
                    VALUES (:tenant_id, :company_code, :lead_id, :name, NOW(), NOW())
                    RETURNING id
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "company_code": company_code,
                    "lead_id": lead_id,
                    "name": name,
                },
            )
            company_ids.append(int(row.scalar_one()))

        order_specs = [
            (company_ids[0], "RLS-ORD-1A", 100.0, "pending"),
            (company_ids[1], "RLS-ORD-1B", 150.0, "completed"),
            (company_ids[2], "RLS-ORD-2", 200.0, "cancelled"),
            (company_ids[3], "RLS-ORD-4", 400.0, "pending"),
        ]
        for company_id, order_number, total_amount, status in order_specs:
            row = await conn.execute(
                text(
                    f"""
                    INSERT INTO {schema}.orders (
                        tenant_id, company_id, order_number, total_amount, status, created_at, updated_at
                    )
                    VALUES (:tenant_id, :company_id, :order_number, :total_amount, :status, NOW(), NOW())
                    RETURNING id
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "company_id": company_id,
                    "order_number": order_number,
                    "total_amount": total_amount,
                    "status": status,
                },
            )
            order_ids.append(int(row.scalar_one()))

        return {"lead_ids": lead_ids, "company_ids": company_ids, "order_ids": order_ids}


@pytest.mark.skipif(
    not ADMIN_PG_URL or not APP_PG_URL,
    reason="実 PostgreSQL 環境が必要 (RLS_ADMIN_DATABASE_URL / RLS_TEST_DATABASE_URL / TEST_PG_URL 未設定)。",
)
@pytest.mark.asyncio
async def test_conversion_by_attribute_rls_team_and_mine_under_tenant_006():
    admin_engine = create_async_engine(ADMIN_PG_URL, echo=False)
    app_engine = create_async_engine(APP_PG_URL, echo=False)
    app_session_factory = sessionmaker(app_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with app_session_factory() as session:
            async with session.begin():
                await session.execute(text(f"SET search_path = {TENANT_SCHEMA}, public"))
                await session.execute(text("SET app.tenant_id = '6'"))
                await session.execute(text("SET app.is_operator = ''"))
                yield session

    inserted: dict[str, list[int]] = {"lead_ids": [], "company_ids": [], "order_ids": []}
    foreign_inserted: dict[str, list[int]] = {"lead_ids": [], "company_ids": [], "order_ids": []}

    try:
        tenant_id = TENANT_ID
        current_user = _build_user(999, tenant_id, "admin")

        async def override_get_current_user():
            return current_user

        async def override_get_current_tenant():
            return tenant_id

        app = FastAPI()
        app.include_router(analytics_router.router, prefix="/api/v1")
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
        app.dependency_overrides[get_current_tenant] = override_get_current_tenant

        await _bootstrap_tenant_schema(admin_engine, TENANT_ID)
        await _bootstrap_tenant_schema(admin_engine, FOREIGN_TENANT_ID)
        inserted = await _seed_conversion_fixture(
            admin_engine,
            TENANT_SCHEMA,
            TENANT_ID,
            current_user.id,
            current_user.id + 1,
        )
        foreign_inserted = await _seed_conversion_fixture(
            admin_engine,
            FOREIGN_SCHEMA,
            FOREIGN_TENANT_ID,
            current_user.id,
            current_user.id + 1,
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            team_res = await ac.get("/api/v1/analytics/conversion-by-attribute?scope=team")
            assert team_res.status_code == 200, team_res.text
            team = team_res.json()
            assert team["channel_type"]["overall_rate"] == pytest.approx(0.5, abs=1e-4)
            team_channels = {row["value"]: row for row in team["channel_type"]["items"]}
            assert team_channels["instagram"]["n"] == 2
            assert team_channels["instagram"]["conversions"] == 1
            assert team_channels["cold_call"]["n"] == 1
            assert team_channels["cold_call"]["conversions"] == 0
            assert team_channels["cold_call"]["smoothed_rate"] == pytest.approx((10 * 0.5) / 11, abs=1e-4)

            mine_res = await ac.get("/api/v1/analytics/conversion-by-attribute?scope=mine")
            assert mine_res.status_code == 200, mine_res.text
            mine = mine_res.json()
            assert mine["channel_type"]["overall_rate"] == pytest.approx(1 / 3, abs=1e-4)
            mine_channels = {row["value"]: row for row in mine["channel_type"]["items"]}
            assert mine_channels["instagram"]["n"] == 2
            assert mine_channels["instagram"]["conversions"] == 1
            assert mine_channels["cold_call"]["n"] == 1
            assert mine_channels["cold_call"]["conversions"] == 0

            priority_res = await ac.get("/api/v1/analytics/priority-prospects?scope=mine")
            assert priority_res.status_code == 200, priority_res.text
            priority = priority_res.json()
            assert priority["scope"] == "mine"
            assert len(priority["items"]) == 3
            assert priority["items"] == sorted(
                priority["items"],
                key=lambda row: (-row["rank_score"], row["lead_id"]),
            )
            items = {item["lead_id"]: item for item in priority["items"]}
            assert set(items) == set(inserted["lead_ids"][:3])
            assert all(item["type"] == "priority_prospect" for item in items.values())
            for lead_id, item in items.items():
                expected_ease = sum(b["smoothed_rate"] for b in item["axis_breakdown"]) / len(item["axis_breakdown"])
                assert item["ease_pct"] == pytest.approx(expected_ease * 100, abs=1e-4)
                assert item["rank_score"] == pytest.approx(item["ease_pct"] * item["monthly_forecast"], abs=1e-4)
                assert any(flag.endswith(":low_sample") for flag in item["low_sample_flags"])
                if lead_id == inserted["lead_ids"][2]:
                    assert len(item["axis_breakdown"]) == 4
                    assert "monthly_forecast_unset" in item["low_sample_flags"]
                    assert item["monthly_forecast"] == pytest.approx(200, abs=1e-4)
                else:
                    assert len(item["axis_breakdown"]) == 5
                    assert "monthly_forecast_unset" not in item["low_sample_flags"]

        async with app_session_factory() as session:
            async with session.begin():
                await session.execute(
                    text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
                    {"tenant_id": str(tenant_id)},
                )
                tenant_count = (await session.execute(text(f"SELECT COUNT(*) FROM {TENANT_SCHEMA}.leads"))).scalar_one()
                foreign_count = (await session.execute(text(f"SELECT COUNT(*) FROM {FOREIGN_SCHEMA}.leads"))).scalar_one()
                assert tenant_count >= 4
                assert foreign_count == 0
    finally:
        with suppress(Exception):
            async with admin_engine.begin() as conn:
                for schema, payload in ((TENANT_SCHEMA, inserted), (FOREIGN_SCHEMA, foreign_inserted)):
                    for table, ids in (("orders", payload["order_ids"]), ("companies", payload["company_ids"]), ("leads", payload["lead_ids"])):
                        for row_id in ids:
                            await conn.execute(text(f"DELETE FROM {schema}.{table} WHERE id = :id"), {"id": row_id})
        with suppress(Exception):
            await app_engine.dispose()
        with suppress(Exception):
            await admin_engine.dispose()
