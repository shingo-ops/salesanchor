"""
成約・失注理由マスタ API テスト（ADR-138 PR3）

対象:
  GET  /api/v1/close-reasons
  POST /api/v1/close-reasons
  PATCH /api/v1/close-reasons/{id}

  PATCH /api/v1/deals/{id} — won/lost 遷移時の close_reasons 登録

テスト方針:
  - SQLite + 既存テスト基盤（conftest）を使用
  - conftest のデフォルト close_reasons シード（id=1〜6）を利用
"""
import pytest
import pytest_asyncio


pytestmark = pytest.mark.asyncio


async def _create_deal(client) -> int:
    company_res = await client.post("/api/v1/companies", json={"name": "理由テスト株式会社"})
    company_id = company_res.json()["id"]
    contact_res = await client.post("/api/v1/contacts", json={
        "company_id": company_id, "name": "担当者", "email": "test-cr@example.com",
    })
    contact_id = contact_res.json()["id"]
    deal_res = await client.post("/api/v1/deals", json={
        "company_id": company_id, "contact_id": contact_id, "title": "理由テスト商談",
    })
    return deal_res.json()["id"]


class TestCloseReasonsAPI:
    """GET/POST/PATCH /close-reasons"""

    async def test_list_close_reasons_returns_defaults(self, client):
        """conftest シードのデフォルト理由が取得できる"""
        res = await client.get("/api/v1/close-reasons")
        assert res.status_code == 200
        data = res.json()
        assert len(data) >= 6
        labels = [r["label"] for r in data]
        assert "在庫・品揃え" in labels
        assert "価格が合わなかった" in labels

    async def test_list_close_reasons_filter_by_type(self, client):
        """type=won で won 理由のみ返る"""
        res = await client.get("/api/v1/close-reasons", params={"type": "won"})
        assert res.status_code == 200
        data = res.json()
        assert all(r["type"] == "won" for r in data)

    async def test_list_close_reasons_invalid_type(self, client):
        """type=invalid で 422"""
        res = await client.get("/api/v1/close-reasons", params={"type": "invalid"})
        assert res.status_code == 422

    async def test_create_close_reason(self, client):
        """新規理由を登録できる"""
        res = await client.post("/api/v1/close-reasons", json={
            "type": "won", "label": "テスト専用理由", "sort_order": 50,
        })
        assert res.status_code == 201
        data = res.json()
        assert data["type"] == "won"
        assert data["label"] == "テスト専用理由"
        assert data["sort_order"] == 50
        assert data["is_active"] is True

    async def test_update_close_reason_label(self, client):
        """理由のラベルを更新できる"""
        create_res = await client.post("/api/v1/close-reasons", json={
            "type": "lost", "label": "更新前ラベル",
        })
        reason_id = create_res.json()["id"]

        res = await client.patch(f"/api/v1/close-reasons/{reason_id}", json={
            "label": "更新後ラベル",
        })
        assert res.status_code == 200
        assert res.json()["label"] == "更新後ラベル"

    async def test_deactivate_close_reason(self, client):
        """is_active=false で非アクティブ化できる"""
        create_res = await client.post("/api/v1/close-reasons", json={
            "type": "lost", "label": "非アクティブテスト",
        })
        reason_id = create_res.json()["id"]

        res = await client.patch(f"/api/v1/close-reasons/{reason_id}", json={
            "is_active": False,
        })
        assert res.status_code == 200
        assert res.json()["is_active"] is False

        # include_inactive=false（デフォルト）では非表示
        list_res = await client.get("/api/v1/close-reasons")
        ids = [r["id"] for r in list_res.json()]
        assert reason_id not in ids

        # include_inactive=true では表示
        list_res2 = await client.get("/api/v1/close-reasons", params={"include_inactive": "true"})
        ids2 = [r["id"] for r in list_res2.json()]
        assert reason_id in ids2

    async def test_update_nonexistent_reason(self, client):
        """存在しない理由を更新しようとすると404"""
        res = await client.patch("/api/v1/close-reasons/99999", json={"label": "存在しない"})
        assert res.status_code == 404


class TestDealCloseReasons:
    """PATCH /deals/{id} — won/lost 遷移時の close_reasons 登録"""

    async def test_won_transition_requires_close_reasons(self, client):
        """won 遷移時に close_reasons なしは 422"""
        deal_id = await _create_deal(client)
        res = await client.patch(f"/api/v1/deals/{deal_id}", json={
            "status": "won",
            "close_reason_memo": "メモあり",
        })
        assert res.status_code == 422

    async def test_won_transition_requires_memo(self, client):
        """won 遷移時に close_reason_memo なしは 422"""
        deal_id = await _create_deal(client)
        res = await client.patch(f"/api/v1/deals/{deal_id}", json={
            "status": "won",
            "close_reasons": [{"reason_id": 1, "is_primary": True}],
        })
        assert res.status_code == 422

    async def test_won_transition_requires_exactly_one_primary(self, client):
        """主因0件は 422"""
        deal_id = await _create_deal(client)
        res = await client.patch(f"/api/v1/deals/{deal_id}", json={
            "status": "won",
            "close_reason_memo": "メモ",
            "close_reasons": [
                {"reason_id": 1, "is_primary": False},
                {"reason_id": 2, "is_primary": False},
            ],
        })
        assert res.status_code == 422

    async def test_won_transition_success(self, client):
        """won 遷移: close_reasons + memo 付きで成功"""
        deal_id = await _create_deal(client)
        res = await client.patch(f"/api/v1/deals/{deal_id}", json={
            "status": "won",
            "close_reason_memo": "在庫が揃っていた",
            "close_reasons": [
                {"reason_id": 1, "is_primary": True},
                {"reason_id": 2, "is_primary": False},
            ],
        })
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "won"
        assert data["close_reason_memo"] == "在庫が揃っていた"
        assert data["closed_at"] is not None

    async def test_lost_transition_success(self, client):
        """lost 遷移: close_reasons + memo 付きで成功"""
        deal_id = await _create_deal(client)
        res = await client.patch(f"/api/v1/deals/{deal_id}", json={
            "status": "lost",
            "close_reason_memo": "価格が折り合わなかった",
            "close_reasons": [{"reason_id": 4, "is_primary": True}],
        })
        assert res.status_code == 200
        assert res.json()["status"] == "lost"
        assert res.json()["closed_at"] is not None

    async def test_non_closing_transition_no_close_reasons_required(self, client):
        """open → negotiating は close_reasons 不要"""
        deal_id = await _create_deal(client)
        res = await client.patch(f"/api/v1/deals/{deal_id}", json={
            "status": "negotiating",
        })
        assert res.status_code == 200
        assert res.json()["status"] == "negotiating"
        assert res.json()["closed_at"] is None
