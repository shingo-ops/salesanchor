"""tenant_profile router のテスト (Sprint 8 / F8 → ADR-1061 便2-2c2b)

SQLite ベースで読み書き + 認可を検証する。
会社名・住所・電話・メール・サイトは issuer_profiles へ移したので、この口は返さず受け取らない。

カバー範囲:
  - GET /admin/tenant-profile: 既定の行が返る（古い6欄は返さない）
  - PUT /admin/tenant-profile: 既定の言語が反映され、古い欄は無視される
  - PUT validation: default_language の不正値で 422
"""
from __future__ import annotations

import pytest
from sqlalchemy import text


@pytest.mark.asyncio
async def test_get_tenant_profile_returns_seeded_row(client, db_session):
    """既定行 (空) が seed されている前提で 200 を返す。"""
    await db_session.execute(text("INSERT INTO tenant_profile (default_language) VALUES ('ja')"))
    await db_session.commit()

    resp = await client.get("/api/v1/admin/tenant-profile")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["default_language"] == "ja"
    assert "company_name" not in body


@pytest.mark.asyncio
async def test_get_tenant_profile_404_when_not_seeded(client, db_session):
    """seed 未投入なら 404 (migration 069 適用要)。"""
    await db_session.execute(text("DELETE FROM tenant_profile"))
    await db_session.commit()

    resp = await client.get("/api/v1/admin/tenant-profile")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_tenant_profile_persists_fields(client, db_session):
    """既定の言語は保存され、古い欄は保存されない。"""
    await db_session.execute(text("INSERT INTO tenant_profile (default_language) VALUES ('ja')"))
    await db_session.commit()

    payload = {
        "company_name": "QA テナント株式会社",
        "company_name_en": "QA Tenant Inc.",
        "address": "東京都渋谷区 1-2-3",
        "phone": "03-1234-5678",
        "email": "po@qa-tenant.example.com",
        "website": "https://qa-tenant.example.com",
        "default_language": "en",
    }
    resp = await client.put("/api/v1/admin/tenant-profile", json=payload)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "company_name" not in body
    assert body["default_language"] == "en"

    row = (await db_session.execute(text(
        "SELECT company_name, default_language FROM tenant_profile ORDER BY id LIMIT 1"
    ))).first()
    assert row[0] is None
    assert row[1] == "en"


@pytest.mark.asyncio
async def test_update_tenant_profile_partial_update(client, db_session):
    """古い欄だけを送っても何も変わらない。"""
    await db_session.execute(text(
        "INSERT INTO tenant_profile (company_name, default_language) VALUES ('既存', 'ja')"
    ))
    await db_session.commit()

    resp = await client.put(
        "/api/v1/admin/tenant-profile",
        json={"phone": "06-9999-0000"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "phone" not in body
    assert body["default_language"] == "ja"

    row = (await db_session.execute(text(
        "SELECT company_name, phone FROM tenant_profile ORDER BY id LIMIT 1"
    ))).first()
    assert (row[0], row[1]) == ("既存", None)


@pytest.mark.asyncio
async def test_update_tenant_profile_rejects_invalid_language(client, db_session):
    """default_language のホワイトリスト外は 422。"""
    await db_session.execute(text("INSERT INTO tenant_profile (default_language) VALUES ('ja')"))
    await db_session.commit()

    resp = await client.put(
        "/api/v1/admin/tenant-profile",
        json={"default_language": "fr"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_update_tenant_profile_404_when_not_seeded(client, db_session):
    """既定行が無い (migration 069 未適用) → 404。"""
    await db_session.execute(text("DELETE FROM tenant_profile"))
    await db_session.commit()

    resp = await client.put(
        "/api/v1/admin/tenant-profile",
        json={"default_language": "en"},
    )
    assert resp.status_code == 404
