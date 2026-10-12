"""ADR-1008 P1: companies.sales_rep_id は public.users(id)（同テナント）を指す。"""
import pytest_asyncio
from sqlalchemy import text

from tests.helpers_txn import _resolve_db_session, create_lead

OTHER_TENANT_USER_ID = 9101
SAME_TENANT_USER_ID = 9102
MISSING_USER_ID = 987654


@pytest_asyncio.fixture
async def seeded_users(client):
    db = await _resolve_db_session(client)
    await db.execute(
        text(
            "INSERT OR IGNORE INTO users (id, tenant_id, username, email, role, is_active) "
            "VALUES (:id, 999, 'rep_same', 'rep_same@example.com', 'user', TRUE)"
        ),
        {"id": SAME_TENANT_USER_ID},
    )
    await db.execute(
        text(
            "INSERT OR IGNORE INTO users (id, tenant_id, username, email, role, is_active) "
            "VALUES (:id, 998, 'rep_other', 'rep_other@example.com', 'user', TRUE)"
        ),
        {"id": OTHER_TENANT_USER_ID},
    )
    await db.flush()


async def _create(client, name, sales_rep_id):
    lead_id = await create_lead(client, name)
    return await client.post(
        "/api/v1/companies",
        json={"name": name, "lead_id": lead_id, "sales_rep_id": sales_rep_id},
    )


class TestSalesRepUsers:
    async def test_post_same_tenant_user_succeeds(self, client, seeded_users):
        res = await _create(client, "担当者OK", SAME_TENANT_USER_ID)
        assert res.status_code == 201
        assert res.json()["sales_rep_id"] == SAME_TENANT_USER_ID

    async def test_post_other_tenant_user_is_422(self, client, seeded_users):
        res = await _create(client, "他テナント担当", OTHER_TENANT_USER_ID)
        assert res.status_code == 422

    async def test_post_missing_user_is_422(self, client, seeded_users):
        res = await _create(client, "存在しない担当", MISSING_USER_ID)
        assert res.status_code == 422

    async def test_patch_same_tenant_user_succeeds(self, client, seeded_users):
        created = await _create(client, "PATCH OK", None)
        cid = created.json()["id"]
        res = await client.patch(f"/api/v1/companies/{cid}", json={"sales_rep_id": SAME_TENANT_USER_ID})
        assert res.status_code == 200
        assert res.json()["sales_rep_id"] == SAME_TENANT_USER_ID

    async def test_patch_other_tenant_user_is_422(self, client, seeded_users):
        cid = (await _create(client, "PATCH 他", None)).json()["id"]
        res = await client.patch(f"/api/v1/companies/{cid}", json={"sales_rep_id": OTHER_TENANT_USER_ID})
        assert res.status_code == 422

    async def test_patch_missing_user_is_422(self, client, seeded_users):
        cid = (await _create(client, "PATCH 無", None)).json()["id"]
        res = await client.patch(f"/api/v1/companies/{cid}", json={"sales_rep_id": MISSING_USER_ID})
        assert res.status_code == 422

    async def test_patch_null_succeeds(self, client, seeded_users):
        cid = (await _create(client, "PATCH null", SAME_TENANT_USER_ID)).json()["id"]
        res = await client.patch(f"/api/v1/companies/{cid}", json={"sales_rep_id": None})
        assert res.status_code == 200
        assert res.json()["sales_rep_id"] is None
