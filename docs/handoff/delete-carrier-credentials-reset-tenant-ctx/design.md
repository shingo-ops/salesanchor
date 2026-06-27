# design: delete-carrier-credentials-reset-tenant-ctx

- recon 参照: `docs/handoff/delete-carrier-credentials-reset-tenant-ctx/recon.md`
- 対象 ADR: ADR-072（write endpoint の内部 commit 後に reset_tenant_context 必須）

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

## 外部・過去事例の参照と我々への応用

ADR-072 は #2621（save）で初適用済みの既知パターン。SQLAlchemy 2.0 の connection pool 動作により `db.commit()` 後にコネクションが返却され、次の SQL は `app.tenant_id = ''` の新規コネクションで実行される（`audit_logs` RLS は NULLIF ガードなし → クラッシュ）。save との同根確認済みのため外部事例の追加調査は不要。
