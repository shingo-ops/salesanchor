"""
販売形態複数選択 API テスト（ADR-108 Phase B-1）

対象:
  GET  /api/v1/leads/sales-form-options
  GET  /api/v1/leads/{id}  — sales_form_selections / sales_form_options フィールド
  PATCH /api/v1/leads/{id} — sales_form_selections 更新・クリア

テスト方針:
  - SQLite + 既存テスト基盤（conftest）を使用
  - conftest のデフォルト選択肢シード（id=1〜5, tenant_id=999）を利用
"""
import pytest

pytestmark = pytest.mark.asyncio


async def _create_lead(client) -> int:
    """テスト用リードを作成して id を返す。"""
    res = await client.post("/api/v1/leads", json={"customer_name": "選択テスト顧客"})
    assert res.status_code == 201, res.text
    return res.json()["id"]


class TestSalesFormOptionsEndpoint:
    """GET /api/v1/leads/sales-form-options"""

    async def test_returns_active_options(self, client):
        """is_active な選択肢が返る（conftest シード: 5件）"""
        res = await client.get("/api/v1/leads/sales-form-options")
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 5
        values = [o["value"] for o in data]
        assert "physical_store" in values
        assert "ec_site" in values
        assert "live_streaming" in values
        assert "wholesale" in values
        assert "other" in values

    async def test_options_have_required_fields(self, client):
        """各選択肢が id / label / value / sort_order / is_active を持つ"""
        res = await client.get("/api/v1/leads/sales-form-options")
        assert res.status_code == 200
        for opt in res.json():
            assert "id" in opt
            assert "label" in opt
            assert "value" in opt
            assert "sort_order" in opt
            assert "is_active" in opt

    async def test_options_sorted_by_sort_order(self, client):
        """sort_order 昇順で返る"""
        res = await client.get("/api/v1/leads/sales-form-options")
        assert res.status_code == 200
        orders = [o["sort_order"] for o in res.json()]
        assert orders == sorted(orders)


class TestLeadGetWithSelections:
    """GET /api/v1/leads/{id} — sales_form_selections / sales_form_options 付加"""

    async def test_new_lead_has_empty_selections(self, client):
        """新規リードの selections は空リスト"""
        lead_id = await _create_lead(client)
        res = await client.get(f"/api/v1/leads/{lead_id}")
        assert res.status_code == 200
        data = res.json()
        assert "sales_form_selections" in data
        assert data["sales_form_selections"] == []

    async def test_new_lead_has_options_attached(self, client):
        """新規リードのレスポンスに sales_form_options が付いてくる"""
        lead_id = await _create_lead(client)
        res = await client.get(f"/api/v1/leads/{lead_id}")
        assert res.status_code == 200
        data = res.json()
        assert "sales_form_options" in data
        assert len(data["sales_form_options"]) == 5


class TestLeadUpdateSelections:
    """PATCH /api/v1/leads/{id} — sales_form_selections"""

    async def test_save_single_selection(self, client):
        """単一オプションを選択して保存・復元できる"""
        lead_id = await _create_lead(client)
        # option id=1 (physical_store) を選択
        res = await client.patch(f"/api/v1/leads/{lead_id}", json={
            "sales_form_selections": [{"option_id": 1, "other_text": None}],
        })
        assert res.status_code == 200
        data = res.json()
        assert len(data["sales_form_selections"]) == 1
        sel = data["sales_form_selections"][0]
        assert sel["option_id"] == 1
        assert sel["option_value"] == "physical_store"
        assert sel["other_text"] is None

    async def test_save_multiple_selections(self, client):
        """複数オプションを同時に選択できる"""
        lead_id = await _create_lead(client)
        res = await client.patch(f"/api/v1/leads/{lead_id}", json={
            "sales_form_selections": [
                {"option_id": 1, "other_text": None},
                {"option_id": 2, "other_text": None},
                {"option_id": 3, "other_text": None},
            ],
        })
        assert res.status_code == 200
        data = res.json()
        assert len(data["sales_form_selections"]) == 3
        option_ids = {s["option_id"] for s in data["sales_form_selections"]}
        assert option_ids == {1, 2, 3}

    async def test_save_other_option_with_text(self, client):
        """「その他」選択時に other_text が保存される"""
        lead_id = await _create_lead(client)
        res = await client.patch(f"/api/v1/leads/{lead_id}", json={
            "sales_form_selections": [{"option_id": 5, "other_text": "自社ECプラットフォーム"}],
        })
        assert res.status_code == 200
        data = res.json()
        assert len(data["sales_form_selections"]) == 1
        sel = data["sales_form_selections"][0]
        assert sel["option_id"] == 5
        assert sel["option_value"] == "other"
        assert sel["other_text"] == "自社ECプラットフォーム"

    async def test_clear_selections(self, client):
        """空リストを送ると既存選択がクリアされる"""
        lead_id = await _create_lead(client)
        # まず選択を保存
        await client.patch(f"/api/v1/leads/{lead_id}", json={
            "sales_form_selections": [{"option_id": 1, "other_text": None}],
        })
        # 空リストで上書き
        res = await client.patch(f"/api/v1/leads/{lead_id}", json={
            "sales_form_selections": [],
        })
        assert res.status_code == 200
        assert res.json()["sales_form_selections"] == []

    async def test_replace_selections(self, client):
        """既存選択を別のオプションで上書きできる（DELETE+INSERT 方式）"""
        lead_id = await _create_lead(client)
        await client.patch(f"/api/v1/leads/{lead_id}", json={
            "sales_form_selections": [{"option_id": 1, "other_text": None}],
        })
        res = await client.patch(f"/api/v1/leads/{lead_id}", json={
            "sales_form_selections": [{"option_id": 2, "other_text": None}],
        })
        assert res.status_code == 200
        data = res.json()
        assert len(data["sales_form_selections"]) == 1
        assert data["sales_form_selections"][0]["option_id"] == 2

    async def test_invalid_option_id_rejected(self, client):
        """存在しない option_id は 400"""
        lead_id = await _create_lead(client)
        res = await client.patch(f"/api/v1/leads/{lead_id}", json={
            "sales_form_selections": [{"option_id": 99999, "other_text": None}],
        })
        assert res.status_code == 400
        assert "99999" in res.json()["detail"]

    async def test_other_text_on_non_other_option_rejected(self, client):
        """'other' 以外のオプションに other_text を付けると 400"""
        lead_id = await _create_lead(client)
        res = await client.patch(f"/api/v1/leads/{lead_id}", json={
            "sales_form_selections": [{"option_id": 1, "other_text": "不正なテキスト"}],
        })
        assert res.status_code == 400

    async def test_duplicate_option_id_rejected(self, client):
        """同一 option_id を2回送ると 400（DB UNIQUE 制約前に API レベルで弾く）"""
        lead_id = await _create_lead(client)
        res = await client.patch(f"/api/v1/leads/{lead_id}", json={
            "sales_form_selections": [
                {"option_id": 1, "other_text": None},
                {"option_id": 1, "other_text": None},
            ],
        })
        assert res.status_code == 400
        assert "重複" in res.json()["detail"]

    async def test_persist_across_get(self, client):
        """保存した選択が GET で読み取れる（永続性確認）"""
        lead_id = await _create_lead(client)
        await client.patch(f"/api/v1/leads/{lead_id}", json={
            "sales_form_selections": [
                {"option_id": 1, "other_text": None},
                {"option_id": 5, "other_text": "卸専門"},
            ],
        })
        res = await client.get(f"/api/v1/leads/{lead_id}")
        assert res.status_code == 200
        data = res.json()
        ids = {s["option_id"] for s in data["sales_form_selections"]}
        assert ids == {1, 5}
        other = next(s for s in data["sales_form_selections"] if s["option_id"] == 5)
        assert other["other_text"] == "卸専門"
