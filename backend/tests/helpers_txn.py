"""テスト用の lead→company→order 生成ヘルパー。"""

async def _resolve_db_session(client):
    from app.database import get_db
    from app.main import app

    transport = getattr(client, "_transport", None)
    app_obj = getattr(transport, "app", None) or app
    override_get_db = app_obj.dependency_overrides.get(get_db)
    if override_get_db is None:
        raise RuntimeError("db_session override not found for test client")
    db_session_gen = override_get_db()
    db_session = await db_session_gen.__anext__()
    await db_session_gen.aclose()
    return db_session


async def create_lead(client, name="テストリード"):
    r = await client.post("/api/v1/leads", json={"customer_name": name})
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def create_company(client, lead_id, deal_id=None, name="テスト会社", **kw):
    body = {"lead_id": lead_id, "name": name, **({"deal_id": deal_id} if deal_id else {}), **kw}
    r = await client.post("/api/v1/companies", json=body)
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def create_txn_chain(client, order_number="ORD-TEST-1", **order_kw):
    """lead→company→order まで一気通貫。戻り値: dict(ids)"""
    lead_id = await create_lead(client)
    company_id = await create_company(client, lead_id)
    r = await client.post("/api/v1/orders", json={"company_id": company_id, "order_number": order_number, **order_kw})
    assert r.status_code == 201, r.text
    return {"lead_id": lead_id, "company_id": company_id, "order_id": r.json()["id"]}
