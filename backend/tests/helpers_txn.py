"""便1a: 背骨必須化に伴うテスト用生成チェーン（lead→deal→company→order）。
既存テストのローカルヘルパーから呼ぶ。実装契約: lead必須(deal/company)・deal必須(order)。"""


async def create_lead(client, name="テストリード"):
    r = await client.post("/api/v1/leads", json={"customer_name": name})
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def create_deal(client, lead_id, **kw):
    body = {"lead_id": lead_id, "title": "テスト商談", **kw}
    r = await client.post("/api/v1/deals", json=body)
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def create_company(client, lead_id, deal_id=None, name="テスト会社", **kw):
    body = {"lead_id": lead_id, "name": name, **({"deal_id": deal_id} if deal_id else {}), **kw}
    r = await client.post("/api/v1/companies", json=body)
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def create_txn_chain(client, order_number="ORD-TEST-1", **order_kw):
    """lead→deal→company(deal紐づけ)→order まで一気通貫。戻り値: dict(ids)"""
    lead_id = await create_lead(client)
    deal_id = await create_deal(client, lead_id)
    company_id = await create_company(client, lead_id, deal_id=deal_id)
    r = await client.post("/api/v1/orders", json={"deal_id": deal_id, "order_number": order_number, **order_kw})
    assert r.status_code == 201, r.text
    return {"lead_id": lead_id, "deal_id": deal_id, "company_id": company_id, "order_id": r.json()["id"]}
