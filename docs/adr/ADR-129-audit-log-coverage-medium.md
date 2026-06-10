# ADR-129: 監査ログ カバレッジ補完（中重要度4系統）

- **Status**: accepted
- **Date**: 2026-06-11
- **Deciders**: shingo-ops, Hikky-dev

## Context

ADR-128 で高重要度2系統（goals / carrier_credentials）の監査ログ記録を実装した。
中重要度として以下4系統が未記録であると判明した:

1. Google Drive 連携解除（`integrations.disconnect`）
2. 顧客優先度オーバーライド（`customer_priority.upsert`）
3. 登録トークン発行（`registration_tokens.create`）
4. 在庫可視性設定変更（`tenant_admin_inventory_visibility.update`）

## Decision

上記4系統に `record_audit_log()` 呼び出しを追加する。

- Google Drive: `action=delete`、センシティブ列（`access_token_encrypted` 等）は **除外**
- 顧客優先度: `action=create`（新規）/ `action=update`（既存）を動的分岐
- 登録トークン: `action=create`、`raw_token`・`token_hash` は **除外**
- 在庫可視性: `action=update`、`old_data`/`new_data` に `visibility_keys` のリストを記録

## Consequences

- 中重要度操作が全件 `audit_logs` テーブルに残るようになる
- センシティブ列（暗号化トークン・ハッシュ）は記録対象外（KPI #6 準拠）
- テスト: `backend/tests/test_audit_medium.py` 8件追加
