"""監査ログ カバレッジ補完テスト（高重要度2系統）

対象:
  - goals CRUD (POST/PATCH/DELETE) の record_audit_log 記録
  - 配送キャリア認証情報 PUT/DELETE の record_audit_log 記録

設計doc §4 KPI 検証:
  #3  目標作成: action=create / action=update (upsert 判別)
  #4  目標更新: old_data に変更前 target_value
  #5  目標削除: old_data に削除レコード全体
  #6  機密非混入: audit_logs に client_secret / raw credentials が入らない
  #7  既存無傷: 既存テストは別ファイルで管理
"""

import json
from unittest.mock import AsyncMock, patch

import pytest


# ─────────────────────────────────────────────────────────────
# goals CRUD
# ─────────────────────────────────────────────────────────────


class TestGoalsAuditLog:
    async def test_create_goal_records_audit_create(self, client, db_session):
        """新規目標 POST → audit_logs に action=create が1行記録される"""
        res = await client.post("/api/v1/goals", json={
            "user_id": 999,
            "period_type": "monthly",
            "period_year": 2026,
            "period_num": 6,
            "kpi_type": "revenue",
            "target_value": 500000,
        })
        assert res.status_code == 201

        from sqlalchemy import text
        rows = (await db_session.execute(
            text("SELECT action, table_name, old_data, new_data FROM audit_logs "
                 "WHERE table_name='goals' ORDER BY id DESC LIMIT 1")
        )).mappings().all()
        assert len(rows) == 1
        assert rows[0]["action"] == "create"
        assert rows[0]["table_name"] == "goals"
        assert rows[0]["old_data"] is None
        new_data = json.loads(rows[0]["new_data"])
        assert new_data["kpi_type"] == "revenue"

    async def test_upsert_goal_records_audit_update(self, client, db_session):
        """既存キーへの POST → audit_logs に action=update が記録される"""
        # 1回目: create
        await client.post("/api/v1/goals", json={
            "user_id": 999,
            "period_type": "monthly",
            "period_year": 2026,
            "period_num": 7,
            "kpi_type": "deal_count",
            "target_value": 10,
        })
        # 2回目: 同じキーで upsert → update
        res = await client.post("/api/v1/goals", json={
            "user_id": 999,
            "period_type": "monthly",
            "period_year": 2026,
            "period_num": 7,
            "kpi_type": "deal_count",
            "target_value": 20,
        })
        assert res.status_code == 201

        from sqlalchemy import text
        rows = (await db_session.execute(
            text("SELECT action, old_data, new_data FROM audit_logs "
                 "WHERE table_name='goals' ORDER BY id DESC LIMIT 1")
        )).mappings().all()
        assert rows[0]["action"] == "update"
        old_data = json.loads(rows[0]["old_data"])
        assert float(old_data["target_value"]) == 10.0
        new_data = json.loads(rows[0]["new_data"])
        assert float(new_data["target_value"]) == 20.0

    async def test_patch_goal_records_old_and_new(self, client, db_session):
        """PATCH → old_data に変更前 target_value、new_data に変更後が記録される"""
        create_res = await client.post("/api/v1/goals", json={
            "user_id": 999,
            "period_type": "weekly",
            "period_year": 2026,
            "period_num": 24,
            "kpi_type": "revenue",
            "target_value": 100000,
        })
        goal_id = create_res.json()["id"]

        from sqlalchemy import text
        await db_session.execute(text("DELETE FROM audit_logs"))
        await db_session.commit()

        res = await client.patch(f"/api/v1/goals/{goal_id}", json={"target_value": 150000})
        assert res.status_code == 200

        rows = (await db_session.execute(
            text("SELECT action, old_data, new_data FROM audit_logs "
                 "WHERE table_name='goals' ORDER BY id DESC LIMIT 1")
        )).mappings().all()
        assert rows[0]["action"] == "update"
        old_data = json.loads(rows[0]["old_data"])
        assert float(old_data["target_value"]) == 100000.0
        new_data = json.loads(rows[0]["new_data"])
        assert float(new_data["target_value"]) == 150000.0

    async def test_delete_goal_records_old_data(self, client, db_session):
        """DELETE → old_data に削除されたレコード全体が記録される"""
        create_res = await client.post("/api/v1/goals", json={
            "user_id": 999,
            "period_type": "monthly",
            "period_year": 2026,
            "period_num": 8,
            "kpi_type": "close_rate",
            "target_value": 75,
        })
        goal_id = create_res.json()["id"]

        from sqlalchemy import text
        await db_session.execute(text("DELETE FROM audit_logs"))
        await db_session.commit()

        res = await client.delete(f"/api/v1/goals/{goal_id}")
        assert res.status_code == 204

        rows = (await db_session.execute(
            text("SELECT action, old_data, new_data FROM audit_logs "
                 "WHERE table_name='goals' ORDER BY id DESC LIMIT 1")
        )).mappings().all()
        assert rows[0]["action"] == "delete"
        old_data = json.loads(rows[0]["old_data"])
        assert old_data["id"] == goal_id
        assert float(old_data["target_value"]) == 75.0
        assert rows[0]["new_data"] is None

    async def test_delete_nonexistent_goal_returns_404(self, client):
        """存在しない目標の DELETE → 404（コミット前に弾かれる）"""
        res = await client.delete("/api/v1/goals/99999")
        assert res.status_code == 404

    async def test_patch_nonexistent_goal_returns_404(self, client):
        """存在しない目標の PATCH → 404"""
        res = await client.patch("/api/v1/goals/99999", json={"target_value": 1000})
        assert res.status_code == 404


# ─────────────────────────────────────────────────────────────
# 配送キャリア認証情報 — 機密非混入テスト（KPI #6 最重要）
# ─────────────────────────────────────────────────────────────


class TestCarrierCredentialsAuditLog:
    """
    carrier_credentials サービスは DB に依存するため、サービス層をモックして
    ルーターの audit 呼び出しロジックのみを検証する。

    テスト戦略:
      - carriers.get_status / save_credentials / delete_credentials をモック
      - record_audit_log への引数を直接 assert
      - client_id / client_secret / account_number の平文が new_data/old_data に
        含まれないことを機械的に検証（KPI #6）
    """

    @pytest.fixture(autouse=True)
    def mock_carrier_services(self):
        """carrier_credentials サービス全体をモックする"""
        with (
            patch("app.services.carrier_credentials.get_status") as mock_status,
            patch("app.services.carrier_credentials.save_credentials", new_callable=AsyncMock) as mock_save,
            patch("app.services.carrier_credentials.delete_credentials", new_callable=AsyncMock) as mock_delete,
        ):
            self.mock_status = mock_status
            self.mock_save = mock_save
            self.mock_delete = mock_delete
            yield

    async def test_put_carrier_records_create_audit_no_secrets(self, client, db_session):
        """PUT（新規）→ action=create が audit_logs に記録され、機密値が含まれない"""
        self.mock_status.side_effect = [
            # 1回目: 変更前（未設定）
            {
                "configured": False, "environment": "production",
                "client_id_hint": None, "secret_configured": False,
                "account_number_hint": None,
            },
            # 2回目: 変更後（設定済み）
            {
                "configured": True, "environment": "production",
                "client_id_hint": "FEDEX_CLIENT_ID_HINT", "secret_configured": True,
                "account_number_hint": "******123",
            },
        ]

        res = await client.put("/api/v1/integrations/carriers/fedex/credentials", json={
            "client_id": "ACTUAL_SECRET_CLIENT_ID",
            "client_secret": "ACTUAL_SECRET_VALUE_MUST_NOT_APPEAR",
            "account_number": "123456789",
        })
        assert res.status_code == 204

        from sqlalchemy import text
        rows = (await db_session.execute(
            text("SELECT action, table_name, old_data, new_data FROM audit_logs "
                 "WHERE table_name='tenant_carrier_credentials' ORDER BY id DESC LIMIT 1")
        )).mappings().all()
        assert len(rows) == 1
        assert rows[0]["action"] == "create"
        assert rows[0]["old_data"] is None

        new_data_str = rows[0]["new_data"]
        # KPI #6: 平文シークレットが audit_logs に入っていないことを検証
        assert "ACTUAL_SECRET_CLIENT_ID" not in new_data_str
        assert "ACTUAL_SECRET_VALUE_MUST_NOT_APPEAR" not in new_data_str
        assert "123456789" not in new_data_str  # 平文 account_number
        # マスク済み hint は記録される
        new_data = json.loads(new_data_str)
        assert new_data["carrier"] == "fedex"
        assert new_data["account_number_hint"] == "******123"

    async def test_put_carrier_records_update_audit_with_old_data(self, client, db_session):
        """PUT（既存更新）→ action=update、old_data に変更前の非機密情報"""
        self.mock_status.side_effect = [
            # 変更前: 設定済み
            {
                "configured": True, "environment": "production",
                "client_id_hint": "OLD_HINT", "secret_configured": True,
                "account_number_hint": "******001",
            },
            # 変更後
            {
                "configured": True, "environment": "production",
                "client_id_hint": "NEW_HINT", "secret_configured": True,
                "account_number_hint": "******002",
            },
        ]

        res = await client.put("/api/v1/integrations/carriers/dhl/credentials", json={
            "client_id": "NEW_SECRET_ID",
            "client_secret": "NEW_SECRET_MUST_NOT_APPEAR",
        })
        assert res.status_code == 204

        from sqlalchemy import text
        rows = (await db_session.execute(
            text("SELECT action, old_data, new_data FROM audit_logs "
                 "WHERE table_name='tenant_carrier_credentials' ORDER BY id DESC LIMIT 1")
        )).mappings().all()
        assert rows[0]["action"] == "update"
        old_data = json.loads(rows[0]["old_data"])
        assert old_data["account_number_hint"] == "******001"
        # KPI #6: 機密値が入っていない
        assert "NEW_SECRET_MUST_NOT_APPEAR" not in rows[0]["new_data"]
        assert "NEW_SECRET_ID" not in rows[0]["new_data"]

    async def test_delete_carrier_records_delete_audit_no_secrets(self, client, db_session):
        """DELETE → action=delete が audit_logs に記録され、機密値が含まれない"""
        self.mock_status.return_value = {
            "configured": True, "environment": "production",
            "client_id_hint": "HINT_VALUE", "secret_configured": True,
            "account_number_hint": "******789",
        }

        res = await client.delete("/api/v1/integrations/carriers/ups/credentials")
        assert res.status_code == 204

        from sqlalchemy import text
        rows = (await db_session.execute(
            text("SELECT action, old_data, new_data FROM audit_logs "
                 "WHERE table_name='tenant_carrier_credentials' ORDER BY id DESC LIMIT 1")
        )).mappings().all()
        assert len(rows) == 1
        assert rows[0]["action"] == "delete"
        assert rows[0]["new_data"] is None

        old_data_str = rows[0]["old_data"]
        old_data = json.loads(old_data_str)
        assert old_data["carrier"] == "ups"
        assert old_data["account_number_hint"] == "******789"
        # KPI #6: HINT_VALUE は client_id_hint（非機密）だが確認
        # account_number の平文はそもそも mock にないので入り得ない
        assert "client_secret" not in old_data_str
