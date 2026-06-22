from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch

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
                await session.execute(text("SELECT set_config('search_path', 'tenant_006, public', true)"))
                await session.execute(text("SELECT set_config('app.tenant_id', '6', true)"))
                yield session

    extra_tenant_row: tuple[str, int] | None = None

    try:
        async with admin_engine.connect() as conn:
            schema_exists = await conn.scalar(
                text("SELECT 1 FROM information_schema.schemata WHERE schema_name = 'tenant_006'")
            )
            if not schema_exists:
                pytest.skip('tenant_006 schema is not present in this CI PostgreSQL database')
            tenant_id = 6

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
            return _build_user(999, int(tenant_id), "admin")

        async def override_get_current_tenant():
            return tenant_id

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
        app.dependency_overrides[get_current_tenant] = override_get_current_tenant

        with patch("app.auth.dependencies.load_user_permissions", new=AsyncMock(return_value={"dashboard.view"})):
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
        await admin_engine.dispose()
        await app_engine.dispose()
