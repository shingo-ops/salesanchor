# recon: fix-supplier-table-name

## 目的

本番DBで `tcg_suppliers` が `tenant_suppliers` にリネーム済み（migration 適用済み）。
バックエンドコードが旧名のまま残っており、DBエラー（relation does not exist）が発生する。
全コード参照を `tenant_suppliers` に更新する。

## 影響ファイル（grep結果）

```
backend/app/tcg_config.py:13
backend/tests/conftest.py:64,84,90,100
backend/tests/test_tcg_import_progress_pg.py:68,71,72,372
backend/tests/test_tcg_work_matching_integration.py:223
backend/tests/test_tcg_sold_out_results.py:133,134
backend/tests/test_tcg_condition_review.py:64
backend/tcg_migration/scripts/ingest_to_prod.py:51,244
backend/tcg_migration/scripts/write_mirror_once.py:61,228,249,278
backend/tcg_migration/scripts/verify_acceptance.py:50,51,102,114,126,138
```

## 除外ファイル

- `backend/migrations/` 配下: 既適用済みmigrationのため変更しない
- フロントエンド: 影響なし

## ADR調査

- `git grep -i tcg_suppliers docs/adr/` — 該当ADRなし
- 本変更はテーブル名文字列置換のみ、設計変更なし
