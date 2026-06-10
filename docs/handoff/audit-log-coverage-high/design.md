# Phase 3 設計 — audit-log-coverage-high（監査ログ カバレッジ補完 高重要度2系統）

**対象ADR**: ADR-128  
**recon**: docs/handoff/audit-log-coverage-high/recon.md  
**日付**: 2026-06-10  
**担当**: Hikky-dev

---

## 外部・過去事例の参照と我々への応用

- 事例1: GDPR/SOC2 準拠要件（EU・米国）→ 変更操作に「誰が・いつ・変更前後の値」を記録する監査ログは規制要件として義務化。我々への応用: goals（目標値の改ざん追跡）と carrier credentials（認証情報変更の追跡）は高重要度として優先対応。
- 事例2: Stripe の audit log 設計（Stripe Docs 2024）→ 機密フィールド（カード番号・シークレット）は audit log に一切書かず、マスク済みヒントのみ記録する設計。我々への応用: `client_secret`・`account_number` 平文を `get_status()` のマスク済みヒントに置き換えて記録する。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| goals POST（新規）→ audit_logs に action=create が1行 | `pytest backend/tests/test_audit_goals_carrier.py::TestGoalsAuditLog::test_create_goal_records_audit_create` |
| goals POST（upsert）→ audit_logs に action=update、old_data に変更前 target_value | `pytest backend/tests/test_audit_goals_carrier.py::TestGoalsAuditLog::test_upsert_goal_records_audit_update` |
| goals PATCH → old_data/new_data 双方に target_value | `pytest backend/tests/test_audit_goals_carrier.py::TestGoalsAuditLog::test_patch_goal_records_old_and_new` |
| goals DELETE → old_data に削除行全体、new_data=None | `pytest backend/tests/test_audit_goals_carrier.py::TestGoalsAuditLog::test_delete_goal_records_old_data` |
| carrier PUT → audit_logs に action=create/update、client_secret が混入しない | `pytest backend/tests/test_audit_goals_carrier.py::TestCarrierCredentialsAuditLog::test_put_carrier_records_create_audit_no_secrets` |
| carrier PUT 更新 → old_data に変更前 hint、機密値非混入 | `pytest backend/tests/test_audit_goals_carrier.py::TestCarrierCredentialsAuditLog::test_put_carrier_records_update_audit_with_old_data` |
| carrier DELETE → action=delete、new_data=None、client_secret 非混入 | `pytest backend/tests/test_audit_goals_carrier.py::TestCarrierCredentialsAuditLog::test_delete_carrier_records_delete_audit_no_secrets` |

---

## 技術 How・KPI

- KPI #3: goals POST upsert → action=create/update の正確な判別（pre-SELECT）
- KPI #4: goals PATCH → old_data に変更前 target_value
- KPI #5: goals DELETE → old_data に削除行全体
- KPI #6（最重要）: audit_logs に client_secret / account_number 平文が入らない
- 技術選択: `get_status()` の返すマスク済みヒントのみを記録（平文は参照しない）

---

## 弊害・トレードオフ

- carrier audit は `save_credentials/delete_credentials` の内部 commit 後に別 tx で INSERT される。障害時に audit だけ欠落する可能性があるが、機密非混入を優先した設計で許容。（サービス内 commit 移譲は次フェーズ課題）

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | goals.py に record_audit_log 追加（POST/PATCH/DELETE） | Generator |
| 2 | integrations.py に record_audit_log 追加（PUT/DELETE） | Generator |
| 3 | conftest.py に goals/carrier テーブル・権限追加 | Generator |
| 4 | test_audit_goals_carrier.py 新規作成（9テスト） | Generator |
| 5 | ADR-128 + handoff 成果物作成 | Generator |

---

## 継続

- 完了後の監視: CI pytest で9テストが常時 PASS を維持
- 次フェーズ: 中重要度4系統（google-drive disconnect / priority score override / registration tokens / inventory visibility）
