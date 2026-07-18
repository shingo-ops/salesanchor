"""便1a: 背骨必須化に伴うテスト用生成チェーン（lead→deal→company→order）。
既存テストのローカルヘルパーから呼ぶ。実装契約: lead必須(deal/company)・deal必須(order)。

便1 stage1 では POST /api/v1/deals が封鎖されるため、create_deal は
テストDBへ direct insert する。
"""

from sqlalchemy import text


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


async def create_deal(client, lead_id, **kw):
    db_session = await _resolve_db_session(client)
    body = {
        "tenant_id": 999,
        "lead_id": lead_id,
        "company_id": kw.get("company_id"),
        "contact_id": kw.get("contact_id"),
        "deal_code": kw.get("deal_code"),
        "title": kw.get("title", "テスト商談"),
        "amount": kw.get("amount"),
        "currency": kw.get("currency", "JPY"),
        "status": kw.get("status", "open"),
        "stage": kw.get("stage", "open"),
        "probability": kw.get("probability"),
        "assigned_to": kw.get("assigned_to"),
        "expected_close_date": kw.get("expected_close_date"),
        "notes": kw.get("notes"),
        "lead_source": kw.get("lead_source"),
        "closed_at": kw.get("closed_at"),
        "close_reason_memo": kw.get("close_reason_memo"),
    }
    res = await db_session.execute(text("""
        INSERT INTO deals (
            tenant_id, lead_id, company_id, contact_id, deal_code,
            title, amount, currency, status, stage, probability,
            assigned_to, expected_close_date, notes, lead_source,
            closed_at, close_reason_memo
        ) VALUES (
            :tenant_id, :lead_id, :company_id, :contact_id, :deal_code,
            :title, :amount, :currency, :status, :stage, :probability,
            :assigned_to, :expected_close_date, :notes, :lead_source,
            :closed_at, :close_reason_memo
        )
        RETURNING id
    """), body)
    await db_session.commit()
    return res.scalar_one()


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
