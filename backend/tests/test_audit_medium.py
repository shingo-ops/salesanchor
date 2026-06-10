"""監査ログ カバレッジ補完テスト（中重要度4系統）

対象:
  - Google Drive 連携解除 DELETE → action=delete, トークン非混入
  - 未接続時 DELETE → 記録しない
  - 優先度スコア上書き POST → action=create/update, old/new 記録
  - 登録リンク発行 POST → action=create, raw_token 非混入
  - 在庫可視性設定 PUT → action=update, old/new 権限キー

KPI:
  #1 Drive解除: action=delete, old_data に account_email
  #2 Drive未接続: DELETE → audit_logs 行数変化なし
  #3 優先度新規: action=create
  #4 優先度更新: action=update, old/new override_score
  #5 登録リンク: action=create, new_data に lead_id（raw_token 非混入）
  #6 在庫可視性: action=update, old/new visibility_keys
  #7 機密非混入（最重点）: audit_logs に Drive トークン・raw_token・token_hash が現れない
"""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import text


# ─────────────────────────────────────────────────────────────
# Google Drive 連携解除 DELETE
# ─────────────────────────────────────────────────────────────


class TestGoogleDriveAudit:
    """DELETE /integrations/google-drive/connect の監査ログ検証。"""

    async def _insert_drive_config(self, db_session, tenant_id: int = 999) -> int:
        """テスト用 Google Drive 設定行を挿入し、id を返す。"""
        await db_session.execute(
            text("""
                INSERT INTO tenant_google_drive_config
                    (tenant_id, access_token_encrypted, refresh_token_encrypted,
                     account_email, connected_by_user_id)
                VALUES
                    (:tid, 'ENC_ACCESS_TOKEN_SECRET', 'ENC_REFRESH_TOKEN_SECRET',
                     'test@example.com', 999)
            """),
            {"tid": tenant_id},
        )
        await db_session.commit()
        row = (await db_session.execute(
            text("SELECT id FROM tenant_google_drive_config WHERE tenant_id = :tid"),
            {"tid": tenant_id},
        )).first()
        return row[0]

    async def test_delete_connected_records_audit(self, client, db_session):
        """接続済み状態で DELETE → audit_logs に action=delete, old_data に account_email,
        new_data=None が記録される（KPI #1）。"""
        await self._insert_drive_config(db_session)

        res = await client.delete("/api/v1/integrations/google-drive/connect")
        assert res.status_code == 204

        rows = (await db_session.execute(
            text("""
                SELECT action, table_name, old_data, new_data
                FROM audit_logs
                WHERE table_name = 'tenant_google_drive_config'
                ORDER BY id DESC LIMIT 1
            """)
        )).mappings().all()

        assert len(rows) == 1
        assert rows[0]["action"] == "delete"
        assert rows[0]["table_name"] == "tenant_google_drive_config"
        assert rows[0]["new_data"] is None

        old_data = json.loads(rows[0]["old_data"])
        assert old_data["account_email"] == "test@example.com"

    async def test_delete_not_connected_no_audit(self, client, db_session):
        """未接続状態で DELETE → audit_logs に行が増えない（KPI #2）。"""
        # テーブルに該当テナントの行がない状態
        before_count = (await db_session.execute(
            text("SELECT COUNT(*) FROM audit_logs WHERE table_name = 'tenant_google_drive_config'")
        )).scalar()

        res = await client.delete("/api/v1/integrations/google-drive/connect")
        # 行が存在しなくても DELETE 自体は 204 を返す
        assert res.status_code == 204

        after_count = (await db_session.execute(
            text("SELECT COUNT(*) FROM audit_logs WHERE table_name = 'tenant_google_drive_config'")
        )).scalar()

        assert after_count == before_count  # 行が増えていない

    async def test_delete_no_token_in_audit(self, client, db_session):
        """old_data に access_token_encrypted / refresh_token_encrypted が含まれない（KPI #7）。"""
        await self._insert_drive_config(db_session)

        await client.delete("/api/v1/integrations/google-drive/connect")

        rows = (await db_session.execute(
            text("""
                SELECT old_data FROM audit_logs
                WHERE table_name = 'tenant_google_drive_config'
                ORDER BY id DESC LIMIT 1
            """)
        )).mappings().all()

        assert len(rows) == 1
        old_data_str = rows[0]["old_data"]

        # old_data に暗号化トークン値が入っていないことを確認
        assert "ENC_ACCESS_TOKEN_SECRET" not in old_data_str
        assert "ENC_REFRESH_TOKEN_SECRET" not in old_data_str
        # カラム名 access_token_encrypted / refresh_token_encrypted もキーとして含まない
        assert "access_token_encrypted" not in old_data_str
        assert "refresh_token_encrypted" not in old_data_str


# ─────────────────────────────────────────────────────────────
# 優先度スコア上書き POST
# ─────────────────────────────────────────────────────────────


class TestCustomerPriorityAudit:
    """POST /leads/{lead_id}/priority-score/override の監査ログ検証。"""

    def _make_score_response(self):
        """モック用 CustomerScoreResponse を生成。"""
        from app.schemas.customer_priority import (
            CustomerScoreResponse,
            ScoreTier,
            SignalSummary,
        )
        return CustomerScoreResponse(
            lead_id=1,
            score=0.7,
            confidence=0.8,
            tier=ScoreTier.promising,
            signal_summary=SignalSummary(total_messages=10),
            sample_size=10,
            is_cold_start=False,
            override_score=None,
            override_note=None,
            scored_at=datetime.now(timezone.utc),
        )

    async def _insert_customer_score(
        self, db_session, lead_id: int = 1, override_score=None
    ) -> int:
        """customer_scores にテスト行を挿入し、id を返す。"""
        await db_session.execute(
            text("""
                INSERT INTO customer_scores
                    (lead_id, score, tier, confidence, signal_summary,
                     override_score, manually_overridden)
                VALUES
                    (:lid, 0.5, 'promising', 0.75, '{}',
                     :oscore, 0)
            """),
            {"lid": lead_id, "oscore": override_score},
        )
        await db_session.commit()
        row = (await db_session.execute(
            text("SELECT id FROM customer_scores WHERE lead_id = :lid"),
            {"lid": lead_id},
        )).first()
        return row[0]

    async def test_override_new_records_create(self, client, db_session):
        """override_score が NULL の状態から override → action=create（KPI #3）。"""
        score_id = await self._insert_customer_score(db_session, lead_id=1, override_score=None)
        mock_response = self._make_score_response()

        with patch(
            "app.services.priority_scoring.get_or_compute_score",
            new=AsyncMock(return_value=mock_response),
        ):
            res = await client.post(
                "/api/v1/leads/1/priority-score/override",
                json={"override_score": 0.9, "override_note": "初回上書き"},
            )

        assert res.status_code == 200

        rows = (await db_session.execute(
            text("""
                SELECT action, table_name, old_data, new_data
                FROM audit_logs
                WHERE table_name = 'customer_scores'
                ORDER BY id DESC LIMIT 1
            """)
        )).mappings().all()

        assert len(rows) == 1
        assert rows[0]["action"] == "create"

    async def test_override_existing_records_update(self, client, db_session):
        """既に override 済みの状態で再 override → action=update, old_data に旧 override_score
        （KPI #4）。"""
        score_id = await self._insert_customer_score(
            db_session, lead_id=2, override_score=0.6
        )
        mock_response = self._make_score_response()

        with patch(
            "app.services.priority_scoring.get_or_compute_score",
            new=AsyncMock(return_value=mock_response),
        ):
            res = await client.post(
                "/api/v1/leads/2/priority-score/override",
                json={"override_score": 0.85, "override_note": "再上書き"},
            )

        assert res.status_code == 200

        rows = (await db_session.execute(
            text("""
                SELECT action, table_name, old_data, new_data
                FROM audit_logs
                WHERE table_name = 'customer_scores'
                ORDER BY id DESC LIMIT 1
            """)
        )).mappings().all()

        assert len(rows) == 1
        assert rows[0]["action"] == "update"

        old_data = json.loads(rows[0]["old_data"])
        assert float(old_data["override_score"]) == pytest.approx(0.6)

        new_data = json.loads(rows[0]["new_data"])
        assert float(new_data["override_score"]) == pytest.approx(0.85)


# ─────────────────────────────────────────────────────────────
# 登録リンク発行 POST
# ─────────────────────────────────────────────────────────────


class TestRegistrationTokenAudit:
    """POST /registration-tokens の監査ログ検証。"""

    async def test_create_token_records_audit(self, client, db_session):
        """POST → audit_logs に action=create, lead_id が new_data に記録される（KPI #5）。"""
        raw_token_value = "test_raw_token_value_abc123"
        expires_at = datetime(2026, 12, 31, 0, 0, 0, tzinfo=timezone.utc)

        with patch(
            "app.services.registration_token.create_registration_token",
            new=AsyncMock(return_value=(raw_token_value, expires_at)),
        ):
            res = await client.post(
                "/api/v1/registration-tokens",
                json={"lead_id": 42, "type": "register"},
            )

        assert res.status_code == 201

        rows = (await db_session.execute(
            text("""
                SELECT action, table_name, old_data, new_data
                FROM audit_logs
                WHERE table_name = 'registration_tokens'
                ORDER BY id DESC LIMIT 1
            """)
        )).mappings().all()

        assert len(rows) == 1
        assert rows[0]["action"] == "create"
        assert rows[0]["old_data"] is None

        new_data = json.loads(rows[0]["new_data"])
        assert new_data["lead_id"] == 42

    async def test_no_raw_token_in_audit(self, client, db_session):
        """new_data に raw_token / token_hash が含まれない（KPI #7）。"""
        raw_token_value = "SUPER_SECRET_RAW_TOKEN_MUST_NOT_APPEAR"
        expires_at = datetime(2026, 12, 31, 0, 0, 0, tzinfo=timezone.utc)

        with patch(
            "app.services.registration_token.create_registration_token",
            new=AsyncMock(return_value=(raw_token_value, expires_at)),
        ):
            res = await client.post(
                "/api/v1/registration-tokens",
                json={"lead_id": 43, "type": "register"},
            )

        assert res.status_code == 201

        rows = (await db_session.execute(
            text("""
                SELECT new_data FROM audit_logs
                WHERE table_name = 'registration_tokens'
                ORDER BY id DESC LIMIT 1
            """)
        )).mappings().all()

        assert len(rows) == 1
        new_data_str = rows[0]["new_data"]

        # KPI #7: raw_token / token_hash が audit_logs に入っていない
        assert "SUPER_SECRET_RAW_TOKEN_MUST_NOT_APPEAR" not in new_data_str
        assert "token_hash" not in new_data_str
        assert "raw_token" not in new_data_str


# ─────────────────────────────────────────────────────────────
# 在庫可視性設定 PUT
# ─────────────────────────────────────────────────────────────


class TestInventoryVisibilityAudit:
    """PUT /admin/inventory-visibility/roles/{role_id} の監査ログ検証。

    テスト戦略:
      SQLite は PostgreSQL の ANY(:array) 演算子をサポートしないため、
      DB クエリを AsyncMock でモックしてルーターの audit 呼び出しロジックのみを検証する。
      carrier テスト（TestCarrierCredentialsAuditLog）と同じモック方式。
    """

    @pytest.fixture(autouse=True)
    def mock_db_and_cache(self):
        """SQLite 非互換の DB クエリとキャッシュ無効化をモックする。"""
        with patch("app.cache.invalidate_tenant_permissions", new=AsyncMock()):
            yield

    async def test_put_visibility_records_update(self, client, db_session):
        """PUT → record_audit_log が action=update, old/new visibility_keys で呼ばれる（KPI #6）。"""
        captured_calls: list[dict] = []

        async def capturing_audit(**kwargs):
            captured_calls.append(kwargs)

        # roles チェック用モック行
        mock_role_row = MagicMock()
        mock_role_row.__getitem__ = lambda self, idx: (10 if idx == 0 else 0)
        mock_role_row.__bool__ = lambda self: True

        mock_role_result = MagicMock()
        mock_role_result.first = MagicMock(return_value=mock_role_row)

        # permissions key_to_id 取得用モック
        key_to_id_rows = [
            {"key": "inventory.visibility.full", "id": 101},
            {"key": "inventory.visibility.staff", "id": 102},
            {"key": "inventory.visibility.viewer", "id": 103},
        ]
        mock_key_to_id_result = MagicMock()
        mock_key_to_id_result.mappings = MagicMock(
            return_value=MagicMock(all=MagicMock(return_value=key_to_id_rows))
        )

        # old_keys 取得用モック（変更前: full が付与済み）
        old_key_rows = [{"key": "inventory.visibility.full"}]
        mock_old_keys_result = MagicMock()
        mock_old_keys_result.mappings = MagicMock(
            return_value=MagicMock(all=MagicMock(return_value=old_key_rows))
        )

        # noop の DELETE / INSERT 結果
        mock_noop_result = MagicMock()

        execute_return_values = [
            mock_role_result,       # 1: SELECT id, is_system FROM roles
            mock_key_to_id_result,  # 2: SELECT id, key FROM permissions (key_to_id)
            mock_old_keys_result,   # 3: SELECT key FROM permissions (old_keys)
            mock_noop_result,       # 4: DELETE FROM role_permissions
            mock_noop_result,       # 5: INSERT INTO role_permissions (staff)
            mock_noop_result,       # 6: INSERT INTO role_permissions (viewer)
        ]

        execute_call_count = 0

        original_execute = db_session.execute

        async def mock_execute(query_or_text, params=None):
            nonlocal execute_call_count
            sql = str(query_or_text)
            # audit_logs への INSERT は実 execute に通す
            if "INSERT INTO audit_logs" in sql:
                return await original_execute(query_or_text, params)
            # その他はモック値を順番に返す
            if execute_call_count < len(execute_return_values):
                result = execute_return_values[execute_call_count]
                execute_call_count += 1
                return result
            return mock_noop_result

        with patch(
            "app.routers.tenant_admin_inventory_visibility.record_audit_log",
            new=capturing_audit,
        ):
            with patch.object(db_session, "execute", side_effect=mock_execute):
                res = await client.put(
                    "/api/v1/admin/inventory-visibility/roles/10",
                    json={
                        "role_id": 10,
                        "visibility_keys": [
                            "inventory.visibility.staff",
                            "inventory.visibility.viewer",
                        ],
                    },
                )

        assert res.status_code == 200

        # record_audit_log が正しい引数で呼ばれたことを検証（KPI #6）
        assert len(captured_calls) == 1
        call = captured_calls[0]
        assert call["action"] == "update"
        assert call["table_name"] == "role_permissions"
        assert "inventory.visibility.full" in call["old_data"]["visibility_keys"]
        assert "inventory.visibility.staff" in call["new_data"]["visibility_keys"]
        assert "inventory.visibility.viewer" in call["new_data"]["visibility_keys"]
        assert "inventory.visibility.full" not in call["new_data"]["visibility_keys"]
