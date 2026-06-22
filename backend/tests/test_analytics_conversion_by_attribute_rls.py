from __future__ import annotations

import os
from contextlib import suppress

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.auth.dependencies import get_current_user
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
            yield session

    inserted_rows: list[tuple[str, int]] = []
    company_rows: list[tuple[str, int]] = []
    contact_rows: list[tuple[str, int]] = []
    deal_rows: list[tuple[str, int]] = []
    extra_tenant_row: tuple[str, int] | None = None

    try:
        async with admin_engine.connect() as conn:
            schema_exists = await conn.scalar(
                text("SELECT 1 FROM information_schema.schemata WHERE schema_name = 'tenant_006'")
            )
            if not schema_exists:
                pytest.skip('tenant_006 schema is not present in this CI PostgreSQL database')
            tenant_id = 6

            user_row = await conn.execute(
                text("""
                    SELECT u.id, COALESCE(u.role, '') AS role
                    FROM public.users u
                    LEFT JOIN user_roles ur ON ur.user_id = u.id
                    LEFT JOIN role_permissions rp ON rp.role_id = ur.role_id
                    LEFT JOIN public.permissions p ON p.id = rp.permission_id
                    WHERE u.tenant_id = :tenant_id
                      AND u.is_active = true
                    GROUP BY u.id, u.role
                    HAVING u.role = 'admin' OR COUNT(*) FILTER (WHERE p.key = 'dashboard.view') > 0
                    ORDER BY CASE WHEN u.role = 'admin' THEN 0 ELSE 1 END, u.id
                    LIMIT 1
                """),
                {"tenant_id": tenant_id},
            )
            user = user_row.mappings().first()
            assert user is not None

            other_tenant_row = await conn.execute(
                text("""
                    SELECT schema_name
                    FROM information_schema.schemata
                    WHERE schema_name LIKE 'tenant\\_%' ESCAPE '\\'
                      AND schema_name NOT IN ('tenant_004', 'tenant_006', 'public')
                    ORDER BY schema_name
                    LIMIT 1
                """),
            )
            extra_tenant_row = other_tenant_row.mappings().first()

        async def override_get_current_user():
            return _build_user(int(user["id"]), int(tenant_id), str(user["role"] or "admin"))

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        async with admin_engine.begin() as conn:
            company_result = await conn.execute(
                text("""
                    INSERT INTO tenant_006.companies (tenant_id, company_code, name, status)
                    VALUES (:tenant_id, :company_code, :name, 'active')
                    RETURNING id
                """),
                {
                    "tenant_id": int(tenant_id),
                    "company_code": "ANALYTICS-RLS-CO-006",
                    "name": "Analytics RLS Co 006",
                },
            )
            company_id = int(company_result.scalar_one())
            company_rows.append(("tenant_006", company_id))

            contact_result = await conn.execute(
                text("""
                    INSERT INTO tenant_006.contacts (
                        tenant_id, company_id, contact_code, display_name, status
                    )
                    VALUES (:tenant_id, :company_id, :contact_code, :display_name, 'active')
                    RETURNING id
                """),
                {
                    "tenant_id": int(tenant_id),
                    "company_id": company_id,
                    "contact_code": "ANALYTICS-RLS-CT-006",
                    "display_name": "Analytics RLS Contact 006",
                },
            )
            contact_id = int(contact_result.scalar_one())
            contact_rows.append(("tenant_006", contact_id))

            deal_result = await conn.execute(
                text("""
                    INSERT INTO tenant_006.deals (
                        tenant_id, company_id, contact_id, title, amount, status, assigned_to, created_at, updated_at
                    )
                    VALUES
                        (:tenant_id, :company_id, :contact_id, 'RLS-Deal-1', 1000, 'won', :uid, NOW(), NOW()),
                        (:tenant_id, :company_id, :contact_id, 'RLS-Deal-2', 2000, 'won', :uid, NOW(), NOW())
                    RETURNING id
                """),
                {
                    "tenant_id": int(tenant_id),
                    "company_id": company_id,
                    "contact_id": contact_id,
                    "uid": int(user["id"]),
                },
            )
            deal_ids = [int(row_id) for row_id in deal_result.scalars().all()]
            deal_rows.extend(("tenant_006", deal_id) for deal_id in deal_ids)

            result = await conn.execute(
                text("""
                    INSERT INTO tenant_006.leads (
                        tenant_id, customer_name, channel_type, country, sales_form,
                        temperature, response_speed, assigned_to, converted_deal_id, created_at
                    )
                    VALUES
                        (:tenant_id, 'RLS-Lead-1', 'instagram', 'JP', 'physical_store', 'Hot', '24h以内', :uid, :deal_1, NOW()),
                        (:tenant_id, 'RLS-Lead-2', 'instagram', 'JP', 'physical_store', 'Warm', '3日以内', :uid, NULL, NOW()),
                        (:tenant_id, 'RLS-Lead-3', 'cold_call', 'US', 'ec_site', 'Cold', '3日超', :uid, NULL, NOW()),
                        (:tenant_id, 'RLS-Lead-4', 'cold_call', 'US', 'other', 'Hot', '24h以内', :other_uid, :deal_2, NOW())
                    RETURNING id
                """),
                {
                    "tenant_id": int(tenant_id),
                    "uid": int(user["id"]),
                    "other_uid": int(user["id"]) + 1,
                    "deal_1": deal_ids[0],
                    "deal_2": deal_ids[1],
                },
            )
            inserted_rows.extend(("tenant_006", int(row_id)) for row_id in result.scalars().all())

            if extra_tenant_row is not None:
                extra_code = str(extra_tenant_row["schema_name"])
                extra_tenant_id = int(extra_code.split("_")[-1]) if extra_code.rsplit("_", 1)[-1].isdigit() else 7
                extra_company_result = await conn.execute(
                    text(f"""
                        INSERT INTO {extra_code}.companies (tenant_id, company_code, name, status)
                        VALUES (:tenant_id, :company_code, :name, 'active')
                        RETURNING id
                    """),
                    {
                        "tenant_id": extra_tenant_id,
                        "company_code": f"ANALYTICS-RLS-CO-{extra_tenant_id}",
                        "name": f"Analytics RLS Co {extra_tenant_id}",
                    },
                )
                extra_company_id = int(extra_company_result.scalar_one())
                company_rows.append((extra_code, extra_company_id))

                extra_contact_result = await conn.execute(
                    text(f"""
                        INSERT INTO {extra_code}.contacts (
                            tenant_id, company_id, contact_code, display_name, status
                        )
                        VALUES (:tenant_id, :company_id, :contact_code, :display_name, 'active')
                        RETURNING id
                    """),
                    {
                        "tenant_id": extra_tenant_id,
                        "company_id": extra_company_id,
                        "contact_code": f"ANALYTICS-RLS-CT-{extra_tenant_id}",
                        "display_name": f"Analytics RLS Contact {extra_tenant_id}",
                    },
                )
                extra_contact_id = int(extra_contact_result.scalar_one())
                contact_rows.append((extra_code, extra_contact_id))

                extra_deal_result = await conn.execute(
                    text(f"""
                        INSERT INTO {extra_code}.deals (
                            tenant_id, company_id, contact_id, title, amount, status, assigned_to, created_at, updated_at
                        )
                        VALUES (:tenant_id, :company_id, :contact_id, 'RLS-Other-Deal', 3000, 'won', :uid, NOW(), NOW())
                        RETURNING id
                    """),
                    {
                        "tenant_id": extra_tenant_id,
                        "company_id": extra_company_id,
                        "contact_id": extra_contact_id,
                        "uid": int(user["id"]),
                    },
                )
                extra_deal_id = int(extra_deal_result.scalar_one())
                deal_rows.append((extra_code, extra_deal_id))

                extra_result = await conn.execute(
                    text(f"""
                        INSERT INTO {extra_code}.leads (
                            tenant_id, customer_name, channel_type, country, sales_form,
                            temperature, response_speed, assigned_to, converted_deal_id, created_at
                        )
                        VALUES
                            (:tenant_id, 'RLS-Other-Lead', 'instagram', 'JP', 'physical_store',
                             'Hot', '24h以内', :uid, :deal_id, NOW())
                        RETURNING id
                    """),
                    {
                        "tenant_id": extra_tenant_id,
                        "uid": int(user["id"]),
                        "deal_id": extra_deal_id,
                    },
                )
                extra_row_id = extra_result.scalar_one()
                inserted_rows.append((extra_code, int(extra_row_id)))

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            team_res = await ac.get("/api/v1/analytics/conversion-by-attribute?scope=team")
            assert team_res.status_code == 200, team_res.text
            team = team_res.json()

            assert team["channel_type"]["overall_rate"] == pytest.approx(0.5, abs=1e-4)
            team_channels = {row["value"]: row for row in team["channel_type"]["items"]}
            assert team_channels["instagram"]["n"] == 2
            assert team_channels["instagram"]["conversions"] == 1
            assert team_channels["cold_call"]["n"] == 2
            assert team_channels["cold_call"]["conversions"] == 1

            mine_res = await ac.get("/api/v1/analytics/conversion-by-attribute?scope=mine")
            assert mine_res.status_code == 200, mine_res.text
            mine = mine_res.json()

            assert mine["channel_type"]["overall_rate"] == pytest.approx(1 / 3, abs=1e-4)
            mine_channels = {row["value"]: row for row in mine["channel_type"]["items"]}
            assert mine_channels["instagram"]["n"] == 2
            assert mine_channels["instagram"]["conversions"] == 1
            assert mine_channels["cold_call"]["n"] == 1
            assert mine_channels["cold_call"]["conversions"] == 0
            assert mine_channels["cold_call"]["smoothed_rate"] == pytest.approx((10 * (1 / 3)) / 11, abs=1e-4)

        async with app_session_factory() as session:
            async with session.begin():
                await session.execute(
                    text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
                    {"tenant_id": str(int(tenant_id))},
                )
                tenant_006_count = (
                    await session.execute(text("SELECT COUNT(*) FROM tenant_006.leads"))
                ).scalar_one()
                assert tenant_006_count >= 4
                if extra_tenant_row is not None:
                    extra_code = str(extra_tenant_row["schema_name"])
                    extra_count = (
                        await session.execute(text(f"SELECT COUNT(*) FROM {extra_code}.leads"))
                    ).scalar_one()
                    assert extra_count == 0
    finally:
        app.dependency_overrides.clear()
        with suppress(Exception):
            async with admin_engine.begin() as conn:
                for schema, row_id in inserted_rows:
                    await conn.execute(
                        text(f"DELETE FROM {schema}.leads WHERE id = :id"),
                        {"id": row_id},
                    )
                for schema, row_id in deal_rows:
                    await conn.execute(
                        text(f"DELETE FROM {schema}.deals WHERE id = :id"),
                        {"id": row_id},
                    )
                for schema, row_id in contact_rows:
                    await conn.execute(
                        text(f"DELETE FROM {schema}.contacts WHERE id = :id"),
                        {"id": row_id},
                    )
                for schema, row_id in company_rows:
                    await conn.execute(
                        text(f"DELETE FROM {schema}.companies WHERE id = :id"),
                        {"id": row_id},
                    )
        await admin_engine.dispose()
        await app_engine.dispose()
