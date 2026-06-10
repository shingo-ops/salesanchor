# Recon: 監査ログ カバレッジ補完（中重要度4系統）

## 対象ファイル（file:line 引用）

### 監査サービス

- `backend/app/services/audit.py:277` — `record_audit_log()` 本体

### Google Drive 連携解除

- `backend/app/routers/integrations.py:43` — `from app.services.audit import record_audit_log`
- `backend/app/routers/integrations.py:388` — `await record_audit_log(...)` (disconnect)

### 顧客優先度オーバーライド

- `backend/app/routers/customer_priority.py:33` — `from app.services.audit import record_audit_log`
- `backend/app/routers/customer_priority.py:133` — `await record_audit_log(...)` (upsert)

### 登録トークン発行

- `backend/app/routers/registration_tokens.py:45` — `from app.services.audit import record_audit_log`
- `backend/app/routers/registration_tokens.py:86` — `await record_audit_log(...)` (create)

### 在庫可視性設定

- `backend/app/routers/tenant_admin_inventory_visibility.py:35` — `from app.services.audit import record_audit_log`
- `backend/app/routers/tenant_admin_inventory_visibility.py:186` — `await record_audit_log(...)` (update)

### テスト

- `backend/tests/test_audit_medium.py:1` — 中重要度4系統テスト（8件）
- `backend/tests/conftest.py:1` — テスト用テーブル・権限・_audit_targets 定義

## センシティブ列の除外確認

- `integrations.py`: `SELECT *` 不使用、明示カラム列挙（`access_token_encrypted` 等除外）
- `registration_tokens.py`: `raw_token`・`token_hash` を `new_data` から除外
