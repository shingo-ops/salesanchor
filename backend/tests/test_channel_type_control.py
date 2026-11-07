from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.services import tenant as tenant_service


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
async def test_create_tenant_schema_does_not_copy_channel_masters(monkeypatch):
    """K6: 新しい会社に名簿の表を作らない・6行を写さない（共用行をそのまま読む）。"""
    db = AsyncMock()
    ddl_db = AsyncMock()
    ddl_statements: list[str] = []

    async def record_ddl(_db, sql):
        ddl_statements.append(sql)

    monkeypatch.setattr(tenant_service, "_execute_statements_preserving_do_blocks", record_ddl)
    monkeypatch.setattr(tenant_service, "seed_system_roles", AsyncMock())
    monkeypatch.setattr(tenant_service, "_META_PAGE_ROUTING_TRIGGER_SQL", "SELECT 1")
    monkeypatch.setattr(ddl_db, "execute", AsyncMock())
    monkeypatch.setattr(db, "execute", AsyncMock())

    assert not hasattr(tenant_service, "seed_default_channel_masters")

    schema = await tenant_service.create_tenant_schema(db, 7, admin_db=ddl_db)
    assert schema == "tenant_007"
    assert ddl_statements, "DDL が1つも流れていない（試験の前提が崩れた）"
    assert all("channel_masters" not in sql for sql in ddl_statements)
    for mocked in (db, ddl_db):
        for call in mocked.execute.await_args_list:
            assert "channel_masters" not in str(call.args)
