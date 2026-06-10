# ADR-128: 監査ログ カバレッジ補完（高重要度2系統）

**日付**: 2026-06-10  
**ステータス**: Accepted  
**担当**: Hikky-dev

---

## 背景

`record_audit_log` サービスは既存（`backend/app/services/audit.py`）だが、
goals CRUD と carrier credentials の PUT/DELETE に記録が付いていなかった。
これらは「誰が・いつ・何を変更したか」を後から追跡すべき高重要度操作。

## 決定

以下2系統に `record_audit_log` を追加する。

### 1. goals CRUD（`backend/app/routers/goals.py`）
- **POST（upsert）**: 既存行を pre-SELECT で確認し `action=create/update` を判別してから記録
- **PATCH**: `old_data` に変更前の全フィールドを取得してから UPDATE → 記録
- **DELETE**: `old_data` に削除対象を取得してから DELETE → 記録。この変更で既存の「404を commit 後に返す」バグも修正

### 2. carrier credentials（`backend/app/routers/integrations.py`）
- **PUT**: `get_status()` で変更前後の非機密情報（hint/mask済み）のみを記録。`client_secret`・`account_number`平文は記録しない
- **DELETE**: 同様に非機密情報のみ記録

## 制約

- `save_credentials()` / `delete_credentials()` は内部で `db.commit()` 済み（`carrier_credentials.py:182/190`）。
  audit INSERT は別トランザクションになる（既知の構造的制約。サービス内 commit の移譲は本PRスコープ外）。
- 機密値（`client_id`・`client_secret`・`account_number` 平文）は audit_logs に一切記録しない。
  `get_status()` の返すマスク済みヒント値のみ記録する（KPI #6 最重要）。

## 検証

`backend/tests/test_audit_goals_carrier.py` の9テストで検証済み。
特に `test_put_carrier_records_create_audit_no_secrets` 他2テストで
機密値非混入を機械的に assert。

## スコープ外（次PR）

- google-drive disconnect・priority score override・registration tokens・inventory visibility（中重要度4系統）
