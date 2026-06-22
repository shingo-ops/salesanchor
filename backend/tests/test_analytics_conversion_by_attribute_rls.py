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

ADMIN_PG_URL = os.getenv("RLS_ADMIN_DATABASE_URL") or os.getenv("TEST_PG_URL")
APP_PG_URL = os.getenv("RLS_TEST_DATABASE_URL")

app = FastAPI()
app.include_router(analytics_router.router, prefix="/api/v1")


def _build_user(user_id: int, tenant_id: int, role: str = "admin") -> User:
    user = User()
    user.id = user_id
    user.tenant_id = tenant_id
    user.username = "analytics-rls"
    user.email = "analytics-rls@example.com"
    user.role = role
    user.is_active = True
    return user


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
                await session.execute(text("SET search_path = tenant_006, public"))
                await session.execute(text("SET app.tenant_id = '6'"))
                await session.execute(text("SET app.is_operator = ''"))
                yield session

    inserted_rows: list[int] = []
    deal_rows: list[int] = []
    extra_rows: list[int] = []
    extra_code: str | None = None

    try:
        async with admin_engine.connect() as conn:
            schema_exists = await conn.scalar(
                text("SELECT 1 FROM information_schema.schemata WHERE schema_name = 'tenant_006'")
            )
        if not schema_exists:
            pytest.skip("tenant_006 schema is not present in this CI PostgreSQL database")

        tenant_id = 6
        current_user = _build_user(999, tenant_id, "admin")

        async def override_get_current_user():
            return current_user

        async def override_get_current_tenant():
            return tenant_id

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
        app.dependency_overrides[get_current_tenant] = override_get_current_tenant

        async with admin_engine.begin() as conn:
            deal_result = await conn.execute(
                text("""
                    INSERT INTO tenant_006.deals (
                        tenant_id, title, amount, status, assigned_to, created_at, updated_at
                    )
                    VALUES
                        (:tenant_id, 'RLS-Deal-1', 1000, 'won', :uid, NOW(), NOW()),
                        (:tenant_id, 'RLS-Deal-2', 2000, 'open', :uid, NOW(), NOW())
                    RETURNING id
                """),
                {"tenant_id": tenant_id, "uid": current_user.id},
            )
            deal_ids = [int(row_id) for row_id in deal_result.scalars().all()]
            deal_rows.extend(deal_ids)

            lead_result = await conn.execute(
                text("""
                    INSERT INTO tenant_006.leads (
                        tenant_id, customer_name, channel_type, country, sales_form,
                        temperature, response_speed, assigned_to, converted_deal_id, monthly_forecast, created_at
                    )
                    VALUES
                        (:tenant_id, 'RLS-Lead-1', 'instagram', 'JP', 'physical_store', 'Hot', '24h以内', :uid, :deal_1, 100, NOW()),
                        (:tenant_id, 'RLS-Lead-2', 'instagram', 'JP', 'physical_store', 'Hot', '24h以内', :uid, NULL, 300, NOW()),
                        (:tenant_id, 'RLS-Lead-3', 'cold_call', 'US', NULL, 'Cold', '3日超', :uid, NULL, NULL, NOW())
                    RETURNING id
                """),
                {
                    "tenant_id": tenant_id,
                    "uid": current_user.id,
                    "deal_1": deal_ids[0],
                },
            )
            inserted_rows.extend(int(row_id) for row_id in lead_result.scalars().all())

            extra_schema_result = await conn.execute(
                text("""
                    SELECT schema_name
                    FROM information_schema.schemata
                    WHERE schema_name LIKE 'tenant_%'
                      AND schema_name NOT IN ('tenant_006', 'tenant_004')
                    ORDER BY schema_name
                    LIMIT 1
                """),
            )
            extra_row = extra_schema_result.mappings().first()
            if extra_row is not None:
                extra_code = str(extra_row["schema_name"])
                extra_tenant_id = int(extra_code.split("_", 1)[1])
                extra_result = await conn.execute(
                    text(f"""
                        INSERT INTO {extra_code}.leads (
                            tenant_id, customer_name, channel_type, country, sales_form,
                            temperature, response_speed, assigned_to, converted_deal_id, monthly_forecast, created_at
                        )
                        VALUES (
                            :tenant_id, 'RLS-Other-Lead', 'messenger', 'CA', 'online',
                            'Warm', '3日以内', :other_uid, :converted_deal_id, 9999, NOW()
                        )
                        RETURNING id
                    """),
                    {
                        "tenant_id": extra_tenant_id,
                        "other_uid": current_user.id + 1,
                        "converted_deal_id": 9999,
                    },
                )
                extra_rows.extend(int(row_id) for row_id in extra_result.scalars().all())

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

            priority_res = await ac.get("/api/v1/analytics/priority-prospects?scope=mine")
            assert priority_res.status_code == 200, priority_res.text
            priority = priority_res.json()

            assert priority["scope"] == "mine"
            assert len(priority["items"]) == 3
            ordered_ids = [item["lead_id"] for item in priority["items"]]
            assert ordered_ids == [inserted_rows[1], inserted_rows[2], inserted_rows[0]]

            items = {item["lead_id"]: item for item in priority["items"]}
            assert set(items) == set(inserted_rows)
            assert all(item["type"] == "priority_prospect" for item in items.values())

            for lead_id, item in items.items():
                expected_ease = sum(b["smoothed_rate"] for b in item["axis_breakdown"]) / len(item["axis_breakdown"])
                assert item["ease_pct"] == pytest.approx(expected_ease * 100, abs=1e-4)
                assert item["rank_score"] == pytest.approx(item["ease_pct"] * item["monthly_forecast"], abs=1e-4)
                assert any(flag.endswith(":low_sample") for flag in item["low_sample_flags"])
                if lead_id == inserted_rows[2]:
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
                tenant_006_count = (await session.execute(text("SELECT COUNT(*) FROM tenant_006.leads"))).scalar_one()
                assert tenant_006_count >= 3
                if extra_code is not None:
                    extra_count = (await session.execute(text(f"SELECT COUNT(*) FROM {extra_code}.leads"))).scalar_one()
                    assert extra_count >= 1
    finally:
        app.dependency_overrides.clear()
        with suppress(Exception):
            async with admin_engine.begin() as conn:
                for row_id in inserted_rows:
                    await conn.execute(
                        text("DELETE FROM tenant_006.leads WHERE id = :id"),
                        {"id": row_id},
                    )
                if extra_code is not None:
                    for row_id in extra_rows:
                        await conn.execute(
                            text(f"DELETE FROM {extra_code}.leads WHERE id = :id"),
                            {"id": row_id},
                        )
                for row_id in deal_rows:
                    await conn.execute(
                        text("DELETE FROM tenant_006.deals WHERE id = :id"),
                        {"id": row_id},
                    )
        await admin_engine.dispose()
        await app_engine.dispose()
