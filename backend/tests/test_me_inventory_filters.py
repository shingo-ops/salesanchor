"""ADR-093 Phase 4: 在庫表ユーザー別フィルタ API のテスト。

SQLite には public.user_inventory_filters が無いため is_postgresql 分岐で
GET=デフォルト / PATCH=受領値エコー となる（API 契約・バリデーションの検証）。
永続化の実検証（upsert / 再取得）は実 PostgreSQL E2E 側。
"""


class TestMeInventoryFilters:
    """GET/PATCH /api/v1/me/inventory-filters の契約。"""

    async def test_get_default(self, client):
        """未設定ユーザーはデフォルト（enabled=false, 空配列）を返す。"""
        res = await client.get("/api/v1/me/inventory-filters")
        assert res.status_code == 200
        d = res.json()
        assert d["enabled"] is False
        assert d["hidden_supplier_ids"] == []
        assert d["hidden_columns"] == []

    async def test_patch_echoes_payload(self, client):
        """PATCH は受領した設定をそのまま返す（SQLite では永続化 skip）。"""
        res = await client.patch(
            "/api/v1/me/inventory-filters",
            json={
                "enabled": True,
                "hidden_supplier_ids": [1, 2, 3],
                "hidden_categories": ["One Piece", "Pokemon"],
                "hidden_columns": ["unit", "unitPrice"],
            },
        )
        assert res.status_code == 200
        d = res.json()
        assert d["enabled"] is True
        assert d["hidden_supplier_ids"] == [1, 2, 3]
        assert d["hidden_categories"] == ["One Piece", "Pokemon"]
        assert d["hidden_columns"] == ["unit", "unitPrice"]

    async def test_patch_invalid_supplier_id_type_422(self, client):
        """hidden_supplier_ids に非整数 → 422。"""
        res = await client.patch(
            "/api/v1/me/inventory-filters",
            json={"hidden_supplier_ids": ["not-a-number"]},
        )
        assert res.status_code == 422

    async def test_patch_display_conditions_echoes(self, client):
        """ADR-093 表示条件（状態/形態/区分 + 数量/単価範囲）も受領値を返す。"""
        res = await client.patch(
            "/api/v1/me/inventory-filters",
            json={
                "enabled": True,
                "show_conditions": ["sealed", "shrink"],
                "show_units": ["box", "case"],
                "show_offer_types": ["in_stock"],
                "qty_min": 1,
                "qty_max": 100,
                "price_min": 500,
                "price_max": 9999,
            },
        )
        assert res.status_code == 200
        d = res.json()
        assert d["show_conditions"] == ["sealed", "shrink"]
        assert d["show_units"] == ["box", "case"]
        assert d["show_offer_types"] == ["in_stock"]
        assert d["qty_min"] == 1
        assert d["qty_max"] == 100
        assert d["price_min"] == 500
        assert d["price_max"] == 9999

    async def test_patch_negative_qty_min_422(self, client):
        """qty_min が負 → 422（ge=0 バリデーション）。"""
        res = await client.patch(
            "/api/v1/me/inventory-filters",
            json={"qty_min": -1},
        )
        assert res.status_code == 422

    async def test_get_default_display_conditions(self, client):
        """未設定ユーザーは表示条件もデフォルト（空配列 / None）。"""
        res = await client.get("/api/v1/me/inventory-filters")
        assert res.status_code == 200
        d = res.json()
        assert d["show_conditions"] == []
        assert d["show_units"] == []
        assert d["show_offer_types"] == []
        assert d["qty_min"] is None
        assert d["price_max"] is None
