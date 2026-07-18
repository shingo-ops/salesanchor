"""便1a: 取引フロー背骨の制約テスト（負のテスト + 正順ライフサイクル通し）

設計正本: docs/handoff/txn-flow-asis-recon/design.md（便1a）
- deals.lead_id 必須化
- companies.lead_id 必須化
- orders.deal_id 必須化（company は deal から自動導出）
"""

import pytest
from tests.helpers_txn import create_deal


# ────────────────────────────────────────────
# 負のテスト: 必須フィールド欠落 → 422
# ────────────────────────────────────────────

class TestBackboneConstraintsNegative:
    """必須フィールド未指定は Pydantic 422 を返す"""

    async def test_create_deal_without_lead_rejected(self, client):
        """lead_id 欠落の POST /deals は 405（deal-removal 段階① による封鎖）"""
        res = await client.post("/api/v1/deals", json={
            "title": "lead なし案件",
        })
        # POST /deals 封鎖(deal-removal 段階①) による
        assert res.status_code == 405

    async def test_create_company_without_lead_rejected(self, client):
        """lead_id 欠落の POST /companies は 422"""
        res = await client.post("/api/v1/companies", json={
            "name": "lead なし会社",
        })
        assert res.status_code == 422

    async def test_create_order_without_deal_rejected(self, client):
        """deal_id 欠落の POST /orders は 422"""
        res = await client.post("/api/v1/orders", json={
            "order_number": "ORD-NO-DEAL",
        })
        assert res.status_code == 422


# ────────────────────────────────────────────
# 正順ライフサイクル通しテスト
# lead → deal(companyなし) → company(deal_id指定) → order(deal_idのみ)
# ────────────────────────────────────────────

class TestBackboneLifecycleNormalized:
    """正順ライフサイクル: 背骨が繋がった注文が作れる"""

    async def test_lifecycle_order_normalized(self, client):
        """lead→deal(company未定)→company(deal_id指定で紐づけ)→order(deal_idのみ・company自動導出)"""

        # (1) lead 作成
        lead_res = await client.post("/api/v1/leads", json={
            "customer_name": "便1aテスト顧客",
        })
        assert lead_res.status_code == 201, f"lead 作成失敗: {lead_res.text}"
        lead_id = lead_res.json()["id"]

        # (2) deal 作成（lead_id のみ・company 未定）
        deal_id = await create_deal(client, lead_id, title="便1a 正順案件")

        # (3) company 作成（lead_id + deal_id を指定 → deal.company_id が更新される）
        company_res = await client.post("/api/v1/companies", json={
            "name": "便1a テスト会社",
            "lead_id": lead_id,
            "deal_id": deal_id,
        })
        assert company_res.status_code == 201, f"company 作成失敗: {company_res.text}"
        company_id = company_res.json()["id"]

        # (3b) deal.company_id が更新されたか確認
        deal_check = await client.get(f"/api/v1/deals/{deal_id}")
        assert deal_check.status_code == 200, f"deal 取得失敗: {deal_check.text}"
        assert deal_check.json()["company_id"] == company_id, \
            f"deal.company_id 未更新: {deal_check.json()}"

        # (4) order 作成（deal_id のみ・company は自動導出）
        order_res = await client.post("/api/v1/orders", json={
            "deal_id": deal_id,
            "order_number": f"ORD-BEN1A-{lead_id}",
        })
        assert order_res.status_code == 201, f"order 作成失敗: {order_res.text}"
        order_data = order_res.json()
        assert order_data["deal_id"] == deal_id
        assert order_data["company_id"] == company_id, \
            f"order.company_id が deal から自動導出されていない: {order_data}"
