"""
ADR-136: v_company_stats 集計テスト

公式定義: paid_at IS NOT NULL AND voided_at IS NULL の請求書のみ合計。
（ADR-108 定義と同一）

カバーするケース:
  - paid（数える）
  - issued 未払い（数えない）
  - voided（数えない）
  - draft（数えない）
  - 複数請求書の合算（paid のみ）
  - 請求書ゼロ件（取引実績なし・ゼロ値）
  - 会社未登録リード（ゼロ値）
  - 他社の請求書は含まない（テナント内分離）
"""

import pytest_asyncio
from sqlalchemy import text  # noqa: F401  (used in fixture)

# ---------------------------------------------------------------------------
# SQLite 互換 v_company_stats ビュー（公式定義 ADR-136 / ADR-108）
# ---------------------------------------------------------------------------
_VIEW_SQL = """
CREATE VIEW IF NOT EXISTS v_company_stats AS
SELECT
    c.id AS company_id,
    COALESCE(SUM(i.total_amount), 0) AS total_deal_amount,
    COUNT(DISTINCT i.id)              AS paid_invoice_count,
    MAX(i.paid_at)                    AS last_paid_at,
    COUNT(DISTINCT d.id)              AS deal_count,
    0                                 AS conversation_count,
    NULL                              AS last_conversation_at
FROM companies c
LEFT JOIN invoices i
    ON i.company_id = c.id
    AND i.paid_at IS NOT NULL
    AND i.voided_at IS NULL
LEFT JOIN deals d ON d.company_id = c.id
GROUP BY c.id
"""


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------

async def _setup_lead_with_company(client, db_session) -> tuple[int, int]:
    """テスト用リードと会社を作成し companies.lead_id で紐づける"""
    lead_res = await client.post("/api/v1/leads", json={"customer_name": "統計テスト顧客"})
    assert lead_res.status_code == 201, lead_res.text
    lead_id = lead_res.json()["id"]

    co_res = await client.post("/api/v1/companies", json={"name": "統計テスト会社"})
    assert co_res.status_code == 201, co_res.text
    company_id = co_res.json()["id"]

    await db_session.execute(
        text("UPDATE companies SET lead_id = :lid WHERE id = :cid"),
        {"lid": lead_id, "cid": company_id},
    )
    await db_session.commit()
    return lead_id, company_id


async def _create_contact(client, company_id: int) -> int:
    ct = await client.post("/api/v1/contacts", json={
        "company_id": company_id,
        "display_name": "テスト担当者",
    })
    assert ct.status_code == 201, ct.text
    return ct.json()["id"]


async def _create_invoice(client, company_id: int, contact_id: int, amount: float = 10000.0) -> int:
    res = await client.post("/api/v1/invoices", json={
        "company_id": company_id,
        "contact_id": contact_id,
        "items": [{"product_name": "テスト商品", "quantity": 1, "unit_price": str(amount)}],
    })
    assert res.status_code == 201, res.text
    return res.json()["id"]


async def _pay_invoice(client, invoice_id: int) -> None:
    r = await client.post(f"/api/v1/invoices/{invoice_id}/issue")
    assert r.status_code == 200, r.text
    r = await client.post(f"/api/v1/invoices/{invoice_id}/pay")
    assert r.status_code == 200, r.text


async def _void_invoice(client, invoice_id: int) -> None:
    r = await client.post(f"/api/v1/invoices/{invoice_id}/void", json={"reason": "テスト取消"})
    assert r.status_code == 200, r.text


# ---------------------------------------------------------------------------
# テストクラス
# ---------------------------------------------------------------------------

class TestCompanyStatsSSot:
    """v_company_stats 集計ロジックの検証（ADR-136）"""

    @pytest_asyncio.fixture(autouse=True)
    async def create_view(self, db_session):
        """各テスト前に SQLite 互換 v_company_stats ビューを作成"""
        await db_session.execute(text("DROP VIEW IF EXISTS v_company_stats"))
        await db_session.execute(text(_VIEW_SQL))
        await db_session.commit()

    async def test_paid_invoice_counted(self, client, db_session):
        """入金済み請求書（paid_at IS NOT NULL, voided_at IS NULL）は合計に含まれる"""
        lead_id, company_id = await _setup_lead_with_company(client, db_session)
        contact_id = await _create_contact(client, company_id)

        inv_id = await _create_invoice(client, company_id, contact_id, 30000.0)
        await _pay_invoice(client, inv_id)

        res = await client.get(f"/api/v1/leads/{lead_id}/stats")
        assert res.status_code == 200
        data = res.json()
        assert float(data["total_deal_amount"]) == 30000.0
        assert data["paid_invoice_count"] == 1
        assert data["last_paid_at"] is not None

    async def test_issued_invoice_not_counted(self, client, db_session):
        """issued（未払い）請求書は合計に含まれない"""
        lead_id, company_id = await _setup_lead_with_company(client, db_session)
        contact_id = await _create_contact(client, company_id)

        inv_id = await _create_invoice(client, company_id, contact_id, 50000.0)
        r = await client.post(f"/api/v1/invoices/{inv_id}/issue")
        assert r.status_code == 200  # issued 状態のまま

        res = await client.get(f"/api/v1/leads/{lead_id}/stats")
        assert res.status_code == 200
        data = res.json()
        assert float(data["total_deal_amount"]) == 0.0
        assert data["paid_invoice_count"] == 0
        assert data["last_paid_at"] is None

    async def test_voided_invoice_not_counted(self, client, db_session):
        """void 済み請求書（voided_at IS NOT NULL）は合計に含まれない"""
        lead_id, company_id = await _setup_lead_with_company(client, db_session)
        contact_id = await _create_contact(client, company_id)

        inv_id = await _create_invoice(client, company_id, contact_id, 20000.0)
        await _void_invoice(client, inv_id)

        res = await client.get(f"/api/v1/leads/{lead_id}/stats")
        assert res.status_code == 200
        data = res.json()
        assert float(data["total_deal_amount"]) == 0.0
        assert data["paid_invoice_count"] == 0

    async def test_draft_invoice_not_counted(self, client, db_session):
        """draft 請求書（paid_at IS NULL）は合計に含まれない"""
        lead_id, company_id = await _setup_lead_with_company(client, db_session)
        contact_id = await _create_contact(client, company_id)

        await _create_invoice(client, company_id, contact_id, 15000.0)  # draft のまま

        res = await client.get(f"/api/v1/leads/{lead_id}/stats")
        assert res.status_code == 200
        data = res.json()
        assert float(data["total_deal_amount"]) == 0.0
        assert data["paid_invoice_count"] == 0

    async def test_multiple_invoices_only_paid_summed(self, client, db_session):
        """複数請求書のうち入金済みのみ合算される"""
        lead_id, company_id = await _setup_lead_with_company(client, db_session)
        contact_id = await _create_contact(client, company_id)

        paid1 = await _create_invoice(client, company_id, contact_id, 10000.0)
        paid2 = await _create_invoice(client, company_id, contact_id, 25000.0)
        unpaid = await _create_invoice(client, company_id, contact_id, 99999.0)

        await _pay_invoice(client, paid1)
        await _pay_invoice(client, paid2)
        r = await client.post(f"/api/v1/invoices/{unpaid}/issue")
        assert r.status_code == 200  # issued のまま（未払い）

        res = await client.get(f"/api/v1/leads/{lead_id}/stats")
        assert res.status_code == 200
        data = res.json()
        assert float(data["total_deal_amount"]) == 35000.0
        assert data["paid_invoice_count"] == 2

    async def test_zero_invoices_returns_zero(self, client, db_session):
        """請求書ゼロ件のとき合計 0・取引実績なし"""
        lead_id, _ = await _setup_lead_with_company(client, db_session)

        res = await client.get(f"/api/v1/leads/{lead_id}/stats")
        assert res.status_code == 200
        data = res.json()
        assert float(data["total_deal_amount"]) == 0.0
        assert data["paid_invoice_count"] == 0
        assert data["last_paid_at"] is None

    async def test_no_linked_company_returns_zero(self, client):
        """会社未登録のリードはゼロ値を返す（会社未登録＝取引実績なし）"""
        lead_res = await client.post("/api/v1/leads", json={"customer_name": "会社なしリード"})
        assert lead_res.status_code == 201
        lead_id = lead_res.json()["id"]

        res = await client.get(f"/api/v1/leads/{lead_id}/stats")
        assert res.status_code == 200
        data = res.json()
        assert float(data["total_deal_amount"]) == 0.0
        assert data["paid_invoice_count"] == 0
        assert data["last_paid_at"] is None

    async def test_other_company_invoices_isolated(self, client, db_session):
        """他の会社の請求書は含まれない（テナント内分離）"""
        lead_id, _ = await _setup_lead_with_company(client, db_session)

        # 別会社を作成してそちらの請求書を支払い済みにする
        other_co = await client.post("/api/v1/companies", json={"name": "他社"})
        assert other_co.status_code == 201
        other_company_id = other_co.json()["id"]
        other_ct = await client.post("/api/v1/contacts", json={
            "company_id": other_company_id,
            "display_name": "他社担当者",
        })
        assert other_ct.status_code == 201
        other_contact_id = other_ct.json()["id"]

        other_inv = await _create_invoice(client, other_company_id, other_contact_id, 99999.0)
        await _pay_invoice(client, other_inv)

        # 自社リードの stats にはゼロが返る
        res = await client.get(f"/api/v1/leads/{lead_id}/stats")
        assert res.status_code == 200
        data = res.json()
        assert float(data["total_deal_amount"]) == 0.0
        assert data["paid_invoice_count"] == 0
