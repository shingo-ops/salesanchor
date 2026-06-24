# recon — discord-oauth-rls-fix

**仕事名**: discord-oauth-rls-fix
**日付**: 2026-06-24
**対象ADR**: ADR-091（Discord Bot OAuth フロー）
**担当**: architect

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `backend/app/routers/discord_oauth.py:138-143` | callback は公開エンドポイント（`get_db` のみ依存・JWT 認証なし） |
| `backend/app/routers/discord_oauth.py:179` | `tenant_id = int(tenant_id)` — state 由来の tenant_id 確定箇所 |
| `backend/app/routers/discord_oauth.py:184-195` | `public.tenant_discord_config` upsert（RLS なし） |
| `backend/app/routers/discord_oauth.py:196-204` | `record_audit_log(db, tenant_id=tenant_id, ...)` 呼び出し |
| `backend/app/services/audit.py:303` | `schema_name = f"tenant_{tenant_id:03d}"` — INSERT 先スキーマ決定 |
| `backend/app/services/audit.py:311-328` | `INSERT INTO {schema_name}.audit_logs` — RLS 対象のクエリ |
| `backend/app/services/tenant.py:1094` | `ALTER TABLE {schema}.audit_logs ENABLE ROW LEVEL SECURITY` |
| `backend/app/services/tenant.py:1152-1155` | `CREATE POLICY tenant_isolation_audit_logs ... USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER)` |
| `backend/app/auth/dependencies.py:255-277` | `set_tenant_context` — SET search_path / SET app.tenant_id / SET app.is_operator |
| `backend/app/database.py:56-61` | `get_db` finally → `clear_tenant_context`（全経路でリセット保証） |
| `backend/app/services/oauth_state.py:98-107` | payload `{tenant_id, staff_id}` を Fernet 暗号化して Redis に保存 |
| `backend/app/services/oauth_state.py:148-157` | `GET+DEL` アトミックパイプライン（one-time・再利用防止） |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | `public.tenant_discord_config` に RLS があるか | `migrations/099_add_discord_guild_config.sql` と `20260602_200000_add_discord_config_connected_by_staff.sql` に ENABLE ROW LEVEL SECURITY 記述なしを確認 | ✅ 解消済み |
| 2 | `tenant_id` はなりすまし可能か | `oauth_state.py:98-107` で Fernet 暗号化済みサーバー保持値から取得・外部改ざん不可 | ✅ 解消済み |
| 3 | 例外時にテナントコンテキストがリセットされるか | `database.py:56-61` の `get_db` finally が全経路を担保 | ✅ 解消済み |
| 4 | 同種バグが他のエンドポイントにあるか | `record_audit_log` 使用ルーター全確認 → 他は全て `get_current_tenant` 依存あり | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み
