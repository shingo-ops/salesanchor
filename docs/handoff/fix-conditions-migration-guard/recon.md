# recon: fix-conditions-migration-guard

## 調査日
2026-09-21

## 問題
デプロイ失敗 [190]: `tenant_004.conditions` が存在しない状態で
`migrations/20260901_090000_add_condition_resolution_columns.sql` が実行されエラー。

## 失敗箇所（file:line）

`migrations/20260901_090000_add_condition_resolution_columns.sql:99`
```sql
SELECT 1 FROM tenant_004.conditions WHERE code = 'CN0001' AND search_kw = ''
```

## 根本原因

- `scripts/run_all_migrations.sh:532` — `20260901_090000` が Step 164 で実行
- `migrations/20260920_040000_conditions_ssot_phase1.sql` — 注釈「事後実行（SSH手動・PO許可）:
  DROP TABLE tenant_NNN.conditions（全テナント）」→ 本番で `tenant_004.conditions` が削除済み
- Step 3 seed チェック（行 99）が直接 `tenant_004.conditions` をクエリ → テーブル不在でエラー
- Step 1〜2 も `information_schema.columns` チェックが FALSE → `ALTER TABLE tenant_004.conditions`
  が実行されてエラーになる可能性あり（to_regclass ガードで同時対処）

## 参照 ADR

- `docs/adr/ADR-1002-unify-product-id-and-fix-migration-compat.md` — 既存 migration 編集パターン
  (Phase A: 先頭にテーブル存在チェックを追加。テーブル存在時の動作は変更しない)

## 影響範囲

- `migrations/20260901_090000_add_condition_resolution_columns.sql` のみ（1ファイル）
- 呼び出し元: `scripts/run_all_migrations.sh:532`
- テーブルが存在する場合（新規DB等）は従来通り動作
