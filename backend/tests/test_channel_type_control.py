from __future__ import annotations

import os
from contextlib import ExitStack
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
from app.routers import leads as leads_router
from app.services import tenant as tenant_service
from scripts.migrate_20260621_030000_backfill_lead_channel_type import backfill_schema

ADMIN_PG_URL = os.getenv("RLS_ADMIN_DATABASE_URL") or os.getenv("TEST_PG_URL")
APP_PG_URL = os.getenv("RLS_TEST_DATABASE_URL")


def _mock_user(tenant_id: int = 999):
    user = User()
    user.id = 999
    user.tenant_id = tenant_id
    user.username = "channel-tester"
    user.email = "channel@test.example.com"
    user.role = "admin"
    user.is_active = True
    return user


@pytest.mark.asyncio
async def test_channel_masters_seeded_and_lead_channel_type_is_dropdown_friendly(client):
    channel_res = await client.get("/api/v1/channel-masters")
    assert channel_res.status_code == 200, channel_res.text
    channels = channel_res.json()
    platforms = [row["platform"] for row in channels]
    assert "whatsapp" in platforms
    assert "messenger" in platforms
    assert "instagram" in platforms
    assert "discord" in platforms
    assert "phone" in platforms
    assert "in_person" in platforms

    create_res = await client.post(
        "/api/v1/leads",
        json={
            "customer_name": "Channel Control Lead",
            "channel_type": "whatsapp_personal",
        },
    )
    assert create_res.status_code == 201, create_res.text
    body = create_res.json()
    assert body["channel_type"] == "whatsapp"

    lead_id = body["id"]
    patch_res = await client.patch(
        f"/api/v1/leads/{lead_id}",
        json={
            "notes": "updated through controlled dropdown",
            "channel_type": "phone",
        },
    )
    assert patch_res.status_code == 200, patch_res.text
    assert patch_res.json()["channel_type"] == "phone"

    invalid = await client.post(
        "/api/v1/leads",
        json={
            "customer_name": "Invalid Channel Lead",
            "channel_type": "unknown_platform",
        },
    )
    assert invalid.status_code == 422


@pytest.mark.asyncio
async def test_create_tenant_schema_seeds_channel_masters(monkeypatch):
    db = AsyncMock()
    ddl_db = AsyncMock()

    async def noop(*args, **kwargs):
        return None

    monkeypatch.setattr(tenant_service, "_execute_statements_preserving_do_blocks", noop)
    monkeypatch.setattr(tenant_service, "seed_system_roles", AsyncMock())
    seed_mock = AsyncMock()
    monkeypatch.setattr(tenant_service, "seed_default_channel_masters", seed_mock)
    monkeypatch.setattr(tenant_service, "_META_PAGE_ROUTING_TRIGGER_SQL", "SELECT 1")
    monkeypatch.setattr(ddl_db, "execute", AsyncMock())
    monkeypatch.setattr(db, "execute", AsyncMock())

    schema = await tenant_service.create_tenant_schema(db, 7, admin_db=ddl_db)
    assert schema == "tenant_007"
    seed_mock.assert_awaited_once_with(db, 7, "tenant_007")


@pytest.mark.skipif(
    not ADMIN_PG_URL or not APP_PG_URL,
    reason="実 PostgreSQL 環境が必要 (RLS_ADMIN_DATABASE_URL / RLS_TEST_DATABASE_URL / TEST_PG_URL 未設定)。",
)
@pytest.mark.asyncio
async def test_channel_type_backfill_normalizes_and_seeds_whatsapp_under_tenant_006():
    admin_engine = create_async_engine(ADMIN_PG_URL, echo=False)
    app_engine = create_async_engine(APP_PG_URL, echo=False)
    app_session_factory = sessionmaker(app_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with app_session_factory() as session:
            yield session

    lead_ids: list[int] = []

    try:
        async with admin_engine.connect() as conn:
            tenant_row = await conn.execute(
                text("SELECT id FROM public.tenants WHERE tenant_code = 'tenant_006'")
            )
            tenant_id = tenant_row.scalar_one_or_none()
        assert tenant_id is not None

        async with admin_engine.begin() as conn:
            result = await conn.execute(
                text(
                    """
                    INSERT INTO tenant_006.leads (tenant_id, customer_name, status, channel_type)
                    VALUES (:tenant_id, :customer_name, 'lead', :channel_type)
                    RETURNING id
                    """
                ),
                {"tenant_id": tenant_id, "customer_name": "Channel Backfill WhatsApp", "channel_type": "whatsapp_personal"},
            )
            lead_ids.append(result.scalar_one())

            result = await conn.execute(
                text(
                    """
                    INSERT INTO tenant_006.leads (tenant_id, customer_name, status, channel_type)
                    VALUES (:tenant_id, :customer_name, 'lead', :channel_type)
                    RETURNING id
                    """
                ),
                {"tenant_id": tenant_id, "customer_name": "Channel Backfill Rare", "channel_type": "cold_call"},
            )
            lead_ids.append(result.scalar_one())

            result = await conn.execute(
                text(
                    """
                    INSERT INTO tenant_006.leads (tenant_id, customer_name, status, channel_type)
                    VALUES (:tenant_id, :customer_name, 'lead', :channel_type)
                    RETURNING id
                    """
                ),
                {"tenant_id": tenant_id, "customer_name": "Channel Backfill Messenger", "channel_type": "messenger"},
            )
            lead_ids.append(result.scalar_one())

        async with admin_engine.begin() as conn:
            counts = await backfill_schema(conn, "tenant_006", int(tenant_id), dry_run=False)

        assert int(counts["normalized"]) >= 1
        assert int(counts["nulled"]) >= 1

        app = FastAPI()
        app.include_router(leads_router.router, prefix="/api/v1")
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = lambda: _mock_user(tenant_id=int(tenant_id))
        app.dependency_overrides[get_current_tenant] = lambda: int(tenant_id)

        with ExitStack() as stack:
            stack.enter_context(
                patch("app.routers.leads.invalidate_dashboard_cache", new=AsyncMock(return_value=None))
            )
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                lead_res = await ac.get(f"/api/v1/leads/{lead_ids[0]}")
                assert lead_res.status_code == 200, lead_res.text
                assert lead_res.json()["channel_type"] == "whatsapp"

        async with app_session_factory() as session:
            async with session.begin():
                await session.execute(
                    text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
                    {"tenant_id": str(tenant_id)},
                )
                channel_rows = (
                    await session.execute(
                        text(
                            "SELECT platform, display_name, connection_type "
                            "FROM tenant_006.channel_masters ORDER BY platform"
                        )
                    )
                ).mappings().all()
                assert {row["platform"] for row in channel_rows} >= {
                    "messenger",
                    "instagram",
                    "discord",
                    "phone",
                    "in_person",
                    "whatsapp",
                }

                lead_rows = []
                for lead_id in lead_ids:
                    row = await session.execute(
                        text("SELECT channel_type FROM tenant_006.leads WHERE id = :id"),
                        {"id": lead_id},
                    )
                    lead_rows.append(row.scalar_one_or_none())
                assert set(lead_rows) == {"whatsapp", None, "messenger"}
    finally:
        async with admin_engine.begin() as conn:
            for lead_id in lead_ids:
                await conn.execute(
                    text("DELETE FROM tenant_006.leads WHERE id = :id"),
                    {"id": lead_id},
                )
        await admin_engine.dispose()
        await app_engine.dispose()
