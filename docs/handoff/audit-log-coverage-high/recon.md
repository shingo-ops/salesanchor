# Recon — 監査ログ カバレッジ補完（高重要度2系統）

**対象ADR**: ADR-128  
**日付**: 2026-06-10  
**担当**: Hikky-dev

---

## 調査対象ファイル

| ファイル | 役割 |
|---------|------|
| `backend/app/services/audit.py:277` | `record_audit_log` 本体（INSERT のみ、commit は呼び出し元責務） |
| `backend/app/routers/goals.py:103` | goals POST（upsert） |
| `backend/app/routers/goals.py:179` | goals PATCH |
| `backend/app/routers/goals.py:220` | goals DELETE |
| `backend/app/routers/integrations.py:330` | carrier credentials PUT |
| `backend/app/routers/integrations.py:385` | carrier credentials DELETE |
| `backend/app/services/carrier_credentials.py:67` | `get_status()` — マスク済みフィールド返却 |
| `backend/app/services/carrier_credentials.py:182` | `save_credentials` 内部 commit |
| `backend/app/services/carrier_credentials.py:190` | `delete_credentials` 内部 commit |

---

## 前提確認

### audit サービス
- `backend/app/services/audit.py:277`: `record_audit_log(db, tenant_id, user_id, action, table_name, record_id, old_data, new_data)` — INSERT のみ実行、commit は呼び出し元が行う
- `backend/app/services/audit.py:313`: `INSERT INTO {schema_name}.audit_logs ...` — テナントスキーマ内に書く

### goals ルーター（追加前）
- `backend/app/routers/goals.py:103`: POST に `record_audit_log` 呼び出しなし
- `backend/app/routers/goals.py:179`: PATCH に `record_audit_log` 呼び出しなし
- `backend/app/routers/goals.py:220`: DELETE に `record_audit_log` 呼び出しなし

### carrier credentials（構造的制約）
- `backend/app/services/carrier_credentials.py:182`: `save_credentials` が内部で `db.commit()` を呼ぶ
- `backend/app/services/carrier_credentials.py:190`: `delete_credentials` が内部で `db.commit()` を呼ぶ
- 結果: audit INSERT は変更後の別 tx になる（許容済み。サービス内 commit の移譲は本 PR スコープ外）

### 機密情報の取り扱い
- `backend/app/services/carrier_credentials.py:67`: `get_status()` が返すのは `configured`, `environment`, `client_id_hint`, `secret_configured`, `account_number_hint`（末尾3桁マスク済み）のみ
- `client_id`・`client_secret`・`account_number` 平文は `get_status()` に含まれない → audit 記録に混入不可

---

## 不明点（解決済み）

| 不明点 | 調査結果 |
|--------|---------|
| goals POST が upsert のため create/update 判別方法 | pre-SELECT で一意キー存在確認 (`backend/app/routers/goals.py:103`) |
| `tenant_carrier_credentials` の PK | `migrations/20260608_080000_add_carrier_credentials.sql` に `id SERIAL PRIMARY KEY` あり → `record_id=None` は許容 |
| テスト用 SQLite での `ON CONFLICT` 動作 | UNIQUE 制約が必要。`backend/tests/conftest.py` に追加 |
