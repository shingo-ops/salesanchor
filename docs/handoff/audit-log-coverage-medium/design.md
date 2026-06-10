# 設計: 監査ログ カバレッジ補完（中重要度4系統）

- ADR: ADR-129
- recon: docs/handoff/audit-log-coverage-medium/recon.md

## 概要

中重要度4系統（Google Drive 連携解除 / 顧客優先度 / 登録トークン / 在庫可視性）に
`record_audit_log()` を追加し、全 write 操作を `audit_logs` テーブルへ記録する。

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| Google Drive 連携解除時に `action=delete` が audit_logs に記録される | `test_audit_medium.py::TestGoogleDriveAudit::test_disconnect_creates_audit_log` |
| 暗号化トークン列が audit_logs の old_data/new_data に含まれない | `test_audit_medium.py::TestGoogleDriveAudit::test_token_not_in_audit` |
| 顧客優先度新規設定で `action=create` が記録される | `test_audit_medium.py::TestCustomerPriorityAudit::test_new_score_creates_audit_log` |
| 顧客優先度既存更新で `action=update` が記録される | `test_audit_medium.py::TestCustomerPriorityAudit::test_existing_score_updates_audit_log` |
| 登録トークン発行で `action=create` が記録される | `test_audit_medium.py::TestRegistrationTokenAudit::test_create_token_creates_audit_log` |
| 登録トークンの raw_token が audit_logs に含まれない | `test_audit_medium.py::TestRegistrationTokenAudit::test_raw_token_not_in_audit` |
| 在庫可視性変更で old/new visibility_keys が記録される | `test_audit_medium.py::TestInventoryVisibilityAudit::test_update_visibility_creates_audit_log` |

## 外部・過去事例の参照と我々への応用

ADR-128（高重要度2系統）にて同方式を採用済み。本 ADR はその範囲拡張。
OWASP ASVS 7.1「監査可能なイベントはすべてログに記録する」に準拠。
センシティブ列除外パターンは PCI-DSS のトークンマスキング要件を参考にした。
