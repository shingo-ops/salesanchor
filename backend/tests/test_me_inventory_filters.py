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

    async def test_get_default_merge_same_post_is_false(self, client):
        """便SP2 / 便1: 同じ投稿のまとめは既定 OFF（ADR-1014 改訂 2026-10-14）。"""
        res = await client.get("/api/v1/me/inventory-filters")
        assert res.json()["merge_same_post"] is False

    async def test_patch_merge_same_post_false_echoes(self, client):
        res = await client.patch("/api/v1/me/inventory-filters", json={"merge_same_post": False})
        assert res.status_code == 200
        assert res.json()["merge_same_post"] is False

    async def test_patch_merge_same_post_wrong_type_422(self, client):
        res = await client.patch("/api/v1/me/inventory-filters", json={"merge_same_post": "maybe"})
        assert res.status_code == 422


class TestMergeSamePostPersistence:
    """便SP2: 保存 JSON に merge_same_post が入ること・キーの無い保存済みの行は False で読めること。"""

    async def test_saved_row_without_key_reads_as_false(self):
        from unittest.mock import AsyncMock, MagicMock, patch

        from app.routers import me_inventory_filters as mod

        row = {"enabled": True, "filters": {"hidden_columns": ["unit"]}}  # merge_same_post キー無し
        result = MagicMock()
        result.mappings.return_value.first.return_value = row
        db = MagicMock()
        db.execute = AsyncMock(return_value=result)
        with patch.object(mod, "is_postgresql", return_value=True):
            payload = await mod.get_my_inventory_filters(db=db, current_user=MagicMock(id=1))
        assert payload.merge_same_post is False
        assert payload.hidden_columns == ["unit"]

    async def test_saved_false_is_read_back_and_written_in_json(self):
        import json
        from unittest.mock import AsyncMock, MagicMock, patch

        from app.routers import me_inventory_filters as mod

        db = MagicMock()
        db.execute = AsyncMock()
        db.commit = AsyncMock()
        with patch.object(mod, "is_postgresql", return_value=True):
            await mod.update_my_inventory_filters(
                payload=mod.InventoryFilterPayload(merge_same_post=False), db=db, current_user=MagicMock(id=1)
            )
        saved = json.loads(db.execute.call_args.args[1]["filters"])
        assert saved["merge_same_post"] is False

        result = MagicMock()
        result.mappings.return_value.first.return_value = {"enabled": False, "filters": saved}
        db.execute = AsyncMock(return_value=result)
        with patch.object(mod, "is_postgresql", return_value=True):
            payload = await mod.get_my_inventory_filters(db=db, current_user=MagicMock(id=1))
        assert payload.merge_same_post is False
