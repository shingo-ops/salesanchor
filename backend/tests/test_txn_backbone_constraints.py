"""便1a: 取引フロー背骨の制約テスト（負のテスト + 正順ライフサイクル通し）

設計正本: docs/handoff/txn-flow-asis-recon/design.md（便1a）
- deals.lead_id 必須化
- companies.lead_id 必須化
- orders.company_id 必須化
"""

import pytest


# ────────────────────────────────────────────
# 負のテスト: 必須フィールド欠落 → 422
# ────────────────────────────────────────────

class TestBackboneConstraintsNegative:
    """必須フィールド未指定は Pydantic 422 を返す"""

    async def test_create_company_without_lead_rejected(self, client):
        """lead_id 欠落の POST /companies は 422"""
        res = await client.post("/api/v1/companies", json={
            "name": "lead なし会社",
        })
        assert res.status_code == 422

    async def test_create_order_without_company_rejected(self, client):
        """company_id 欠落の POST /orders は 422"""
        res = await client.post("/api/v1/orders", json={
            "order_number": "ORD-NO-DEAL",
        })
        assert res.status_code == 422


# ────────────────────────────────────────────
# 正順ライフサイクル通しテスト
# lead → company → order(company_id 直参照)
# ────────────────────────────────────────────

class TestBackboneLifecycleNormalized:
    """正順ライフサイクル: 背骨が繋がった注文が作れる"""

    async def test_lifecycle_order_normalized(self, client):
        """lead→company→order(company_id 直参照)"""

        # (1) lead 作成
        lead_res = await client.post("/api/v1/leads", json={
            "customer_name": "便1aテスト顧客",
        })
        assert lead_res.status_code == 201, f"lead 作成失敗: {lead_res.text}"
        lead_id = lead_res.json()["id"]

        # (2) company 作成（lead_id を指定）
        company_res = await client.post("/api/v1/companies", json={
            "name": "便1a テスト会社",
            "lead_id": lead_id,
        })
        assert company_res.status_code == 201, f"company 作成失敗: {company_res.text}"
        company_id = company_res.json()["id"]

        # (3) order 作成（company_id 直参照）
        order_res = await client.post("/api/v1/orders", json={
            "company_id": company_id,
            "order_number": f"ORD-BEN1A-{lead_id}",
        })
        assert order_res.status_code == 201, f"order 作成失敗: {order_res.text}"
        order_data = order_res.json()
        assert order_data["company_id"] == company_id, \
            f"order.company_id が指定値になっていない: {order_data}"
