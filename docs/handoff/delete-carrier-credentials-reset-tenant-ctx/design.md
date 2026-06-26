# design: delete-carrier-credentials-reset-tenant-ctx

## KGI

| 基準 | 検証方法 |
|------|---------|
| 削除操作が 204 で完了し、audit_logs に DELETE レコードが記録される | 実機で削除→DB確認 |
| 既存 save (#2621) / test-connection の動作に変更なし | コードレビュー・CI |
| migration なし・frontend 変更なし | diff確認 |

## 設計

- 変更: `reset_tenant_context(db, tenant_id)` を `delete_credentials` 直後・`record_audit_log` 前に移動
- コメント: `# ADR-072: 内部 commit 後に...` を追記（save と同じ説明）
- 末尾の不要な `await reset_tenant_context` 行を削除（重複）

## #2621 との対比

| 項目 | save (#2621) | delete (本PR) |
|------|-------------|---------------|
| 内部commit箇所 | `save_credentials` (line 198) | `delete_credentials` (line 210) |
| fix 位置 | `save_credentials` 後・`get_status` 前 | `delete_credentials` 後・`record_audit_log` 前 |
| 構造 | 同根 | 同根 |

## 外部事例
- n/a（ADR-072 既知パターンの適用）
