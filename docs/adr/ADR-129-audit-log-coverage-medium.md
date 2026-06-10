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

---

## 未対応バックログ（実装見送り・記録のみ）

### 低重要度: 監査ログ未記録（実装見送り）

以下4系統は「お金・顧客マスタに直結しない / 業務影響が薄い」理由で本サイクルは対象外とした。
将来のカバレッジ拡張時の候補として記録する。

| 系統 | 理由 |
|------|------|
| 翻訳辞書 CRUD | 業務影響軽微・参照頻度低 |
| 個人フィルタ設定 | ユーザー個人設定・共有リソースではない |
| メッセージ翻訳キャッシュ | 自動生成・再生成可能なデータ |
| メッセージラベル訂正 | 個人作業の補助データ |

### super-admin 操作: 別手段で代替

在庫オファー・サプライヤー・商品マスタ CRUD は `require_super_admin` で入口が絞られており、
アクセス制御＋サーバーログで監査代替可能と判断し本サイクルは実装しない。

**注意**: 在庫オファーの `unit_price` は金額データ。将来 super-admin 操作ログを整備する際は
このテーブルを優先対象とすること。

### 構造的制約: carrier commit 境界による audit 欠落の小窓（既知）

`carrier_credentials` の save/delete はサービス内部で `db.commit()` を持つため、
audit 記録が別トランザクションになる。コンテナクラッシュ時に記録欠落の可能性がある。
完全解決にはサービス層の commit 再設計が必要（別件・ADR起案待ち）。

### process-artifacts gate: バッククォート誤検知（実例記録）

PR #1916 の PR 本文で `recon:` と `設計:` の値にバッククォートを付けたところ、
`/recon:\s*(docs\/handoff\/...\.md)/` regex がマッチせず gate が FAIL した。
改善案: パスの前後バッククォートを trim する正規化処理を `check-process-artifacts.js` に追加。
