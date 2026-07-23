"""案件管理API（deals）のテスト

Phase 1-B-2 Step 5d 以降は会社 + 担当者 (company_id + contact_id) を必須とする。
Stage 1 では POST /api/v1/deals を 405 に封鎖し、商談化は leads に直接保存する。
"""

from sqlalchemy import text


async def _create_company_contact(client, company_name="テスト顧客"):
    """テスト用に会社 + 担当者ペアを作成する共通ヘルパー。

    backend が deals/orders/quotes/invoices/leads.convert で要求する
    (company_id, contact_id, lead_id) を返す。
    """
    from tests.helpers_txn import create_lead

    lead_id = await create_lead(client, company_name)
    co = await client.post("/api/v1/companies", json={"name": company_name, "lead_id": lead_id})
    assert co.status_code == 201, co.text
    company_id = co.json()["id"]
    ct = await client.post("/api/v1/contacts", json={
        "company_id": company_id,
        "display_name": f"{company_name}の担当",
    })
    assert ct.status_code == 201, ct.text
    return company_id, ct.json()["id"], lead_id


async def _insert_deal(
    db_session,
    *,
    company_id,
    contact_id,
    lead_id,
    title="テスト商談",
    amount=1000000,
    currency="JPY",
    status="open",
    stage="open",
    probability=10,
    assigned_to=None,
    expected_close_date=None,
    notes="重要案件",
    lead_source=None,
):
    result = await db_session.execute(
        text("""
            INSERT INTO deals (
                tenant_id, company_id, contact_id, lead_id,
                title, amount, currency, status, stage, probability,
                assigned_to, expected_close_date, notes, lead_source
            ) VALUES (
                999, :company_id, :contact_id, :lead_id,
                :title, :amount, :currency, :status, :stage, :probability,
                :assigned_to, :expected_close_date, :notes, :lead_source
            )
        """),
        {
            "company_id": company_id,
            "contact_id": contact_id,
            "lead_id": lead_id,
            "title": title,
            "amount": amount,
            "currency": currency,
            "status": status,
            "stage": stage,
            "probability": probability,
            "assigned_to": assigned_to,
            "expected_close_date": expected_close_date,
            "notes": notes,
            "lead_source": lead_source,
        },
    )
    await db_session.commit()
    return result.lastrowid


class TestDealsCRUD:
    """案件の取得・更新・削除"""

    async def test_create_deal_is_disabled(self, client):
        """案件の新規作成APIは 405 を返す"""
        res = await client.post("/api/v1/deals", json={
            "lead_id": 1,
            "company_id": 1,
            "contact_id": 1,
            "title": "大型案件",
            "amount": 1000000,
            "status": "open",
            "notes": "重要案件",
        })
        assert res.status_code == 405
        assert res.json()["detail"] == "deals新規作成は廃止(deal-removal 段階①)"

    async def test_create_deal_invalid_contact(self, client):
        """存在しない担当者IDでも POST /deals は 405"""
        company_id, _, lead_id = await _create_company_contact(client)
        res = await client.post("/api/v1/deals", json={
            "lead_id": lead_id,
            "company_id": company_id,
            "contact_id": 99999,
            "title": "無効な案件",
        })
        assert res.status_code == 405

    async def test_create_deal_contact_company_mismatch(self, client):
        """company 不一致でも POST /deals は 405"""
        company_a, contact_a, lead_a = await _create_company_contact(client, "会社A")
        company_b, _, lead_b = await _create_company_contact(client, "会社B")
        res = await client.post("/api/v1/deals", json={
            "lead_id": lead_b,
            "company_id": company_b,
            "contact_id": contact_a,
            "title": "ミスマッチ案件",
        })
        assert res.status_code == 405

    async def test_list_deals(self, client, db_session):
        """案件一覧を取得できる"""
        company_id, contact_id, lead_id = await _create_company_contact(client)
        await _insert_deal(db_session, company_id=company_id, contact_id=contact_id, lead_id=lead_id, title="案件A")
        await _insert_deal(db_session, company_id=company_id, contact_id=contact_id, lead_id=lead_id, title="案件B")

        res = await client.get("/api/v1/deals")
        assert res.status_code == 200
        assert len(res.json()) >= 2

    async def test_list_deals_filter_by_status(self, client, db_session):
        """ステータスでフィルタリングできる"""
        company_id, contact_id, lead_id = await _create_company_contact(client)
        await _insert_deal(
            db_session,
            company_id=company_id,
            contact_id=contact_id,
            lead_id=lead_id,
            title="成約案件",
            status="won",
            stage="won",
        )
        await _insert_deal(db_session, company_id=company_id, contact_id=contact_id, lead_id=lead_id, title="進行中案件")

        res = await client.get("/api/v1/deals", params={"status": "won"})
        assert res.status_code == 200
        data = res.json()
        assert all(d["status"] == "won" for d in data)

    async def test_list_deals_filter_by_company(self, client, db_session):
        """会社IDでフィルタリングできる"""
        company_a, contact_a, lead_a = await _create_company_contact(client, "顧客A")
        company_b, contact_b, lead_b = await _create_company_contact(client, "顧客B")
        await _insert_deal(db_session, company_id=company_a, contact_id=contact_a, lead_id=lead_a, title="Aの案件")
        await _insert_deal(db_session, company_id=company_b, contact_id=contact_b, lead_id=lead_b, title="Bの案件")

        res = await client.get("/api/v1/deals", params={"company_id": company_a})
        assert res.status_code == 200
        data = res.json()
        assert all(d["company_id"] == company_a for d in data)

    async def test_get_deal(self, client, db_session):
        """案件詳細を取得できる"""
        company_id, contact_id, lead_id = await _create_company_contact(client)
        deal_id = await _insert_deal(db_session, company_id=company_id, contact_id=contact_id, lead_id=lead_id, title="詳細テスト案件")

        res = await client.get(f"/api/v1/deals/{deal_id}")
        assert res.status_code == 200
        assert res.json()["title"] == "詳細テスト案件"

    async def test_update_deal_status(self, client, db_session):
        """案件のステータスを更新できる"""
        company_id, contact_id, lead_id = await _create_company_contact(client)
        deal_id = await _insert_deal(db_session, company_id=company_id, contact_id=contact_id, lead_id=lead_id, title="進行中")

        res = await client.patch(f"/api/v1/deals/{deal_id}", json={
            "status": "won",
        })
        assert res.status_code == 200
        assert res.json()["status"] == "won"

    async def test_update_deal_with_date_and_amount(self, client, db_session):
        """date(expected_close_date)とDecimal(amount)を同時更新できる（asyncpg encoder対策の回帰テスト）"""
        company_id, contact_id, lead_id = await _create_company_contact(client)
        deal_id = await _insert_deal(db_session, company_id=company_id, contact_id=contact_id, lead_id=lead_id, title="日付更新テスト")

        res = await client.patch(f"/api/v1/deals/{deal_id}", json={
            "status": "negotiating",
            "amount": 10000,
            "expected_close_date": "2026-04-30",
            "notes": "備考更新",
        })
        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "negotiating"
        assert float(body["amount"]) == 10000.0
        assert body["expected_close_date"] == "2026-04-30"
        assert body["notes"] == "備考更新"

    async def test_delete_deal(self, client, db_session):
        """案件を削除できる"""
        company_id, contact_id, lead_id = await _create_company_contact(client)
        deal_id = await _insert_deal(db_session, company_id=company_id, contact_id=contact_id, lead_id=lead_id, title="削除案件")

        res = await client.delete(f"/api/v1/deals/{deal_id}")
        assert res.status_code == 204

        res = await client.get(f"/api/v1/deals/{deal_id}")
        assert res.status_code == 404

class TestDealsValidation:
    """案件バリデーション"""

    async def test_create_without_title(self, client):
        """POST /deals はタイトルなしでも 405"""
        res = await client.post("/api/v1/deals", json={
            "lead_id": 1, "company_id": 1, "contact_id": 1,
        })
        assert res.status_code == 405

    async def test_create_without_company_or_contact(self, client):
        """POST /deals は会社/担当者なしでも 405"""
        res = await client.post("/api/v1/deals", json={"title": "顧客なし案件"})
        assert res.status_code == 405

    async def test_invalid_status(self, client):
        """POST /deals は無効なステータスでも 405"""
        company_id, contact_id, lead_id = await _create_company_contact(client)
        res = await client.post("/api/v1/deals", json={
            "lead_id": lead_id, "company_id": company_id, "contact_id": contact_id,
            "title": "無効ステータス", "status": "invalid",
        })
        assert res.status_code == 405

    async def test_negative_amount(self, client):
        """POST /deals は負の金額でも 405"""
        company_id, contact_id, lead_id = await _create_company_contact(client)
        res = await client.post("/api/v1/deals", json={
            "lead_id": lead_id, "company_id": company_id, "contact_id": contact_id,
            "title": "負の金額", "amount": -100,
        })
        assert res.status_code == 405


class TestLeadConvertStage1:
    """段階①の商談化テスト"""

    async def test_convert_lead_updates_lead_columns_without_creating_deal(self, client, db_session):
        from tests.helpers_txn import create_lead

        lead_id = await create_lead(client, "商談化対象")
        company_id, contact_id, _ = await _create_company_contact(client, "商談化対象")

        before = await db_session.execute(text("SELECT COUNT(*) FROM deals"))
        before_count = before.scalar_one()

        res = await client.post(f"/api/v1/leads/{lead_id}/convert", json={
            "company_id": company_id,
            "contact_id": contact_id,
            "title": "商談化案件",
            "amount": 123456,
            "currency": "USD",
            "expected_close_date": "2026-04-30",
        })
        assert res.status_code == 200, res.text

        after = await db_session.execute(text("SELECT COUNT(*) FROM deals"))
        after_count = after.scalar_one()
        assert after_count == before_count

        lead_row = await db_session.execute(text("""
            SELECT amount, currency, expected_close_date, status
            FROM leads WHERE id = :id
        """), {"id": lead_id})
        row = lead_row.mappings().first()
        assert float(row["amount"]) == 123456.0
        assert row["currency"] == "USD"
        assert str(row["expected_close_date"]) == "2026-04-30"
        assert row["status"] == "negotiating"

    async def test_convert_lead_twice_returns_409(self, client):
        from tests.helpers_txn import create_lead

        lead_id = await create_lead(client, "二重商談化")
        company_id, contact_id, _ = await _create_company_contact(client, "二重商談化")

        first = await client.post(f"/api/v1/leads/{lead_id}/convert", json={
            "company_id": company_id,
            "contact_id": contact_id,
            "title": "商談化案件",
            "amount": 1000,
        })
        assert first.status_code == 200, first.text

        second = await client.post(f"/api/v1/leads/{lead_id}/convert", json={
            "company_id": company_id,
            "contact_id": contact_id,
            "title": "商談化案件2",
            "amount": 2000,
        })
        assert second.status_code == 409


class TestDealResponseSchema:
    """DealResponse の堅牢性（後発テナントの NULL contact_id 行）。"""

    def _row(self, **overrides):
        from datetime import datetime

        row = {
            "id": 1,
            "deal_code": "D-001",
            "company_id": 10,
            "contact_id": 20,
            "lead_id": None,
            "title": "テスト商談",
            "amount": None,
            "currency": None,
            "status": "open",
            "stage": None,
            "probability": None,
            "assigned_to": None,
            "expected_close_date": None,
            "notes": None,
            "lead_source": None,
            "created_at": datetime(2026, 1, 1, 0, 0, 0),
            "updated_at": datetime(2026, 1, 1, 0, 0, 0),
        }
        row.update(overrides)
        return row

    def test_contact_id_null_does_not_raise(self):
        """tenant_006 等の NULL contact_id 行で GET /deals が 500 にならないこと。"""
        from app.schemas.deal import DealResponse

        resp = DealResponse(**self._row(contact_id=None))
        assert resp.contact_id is None
        assert resp.company_id == 10

    def test_contact_id_present_still_valid(self):
        from app.schemas.deal import DealResponse

        assert DealResponse(**self._row(contact_id=20)).contact_id == 20
