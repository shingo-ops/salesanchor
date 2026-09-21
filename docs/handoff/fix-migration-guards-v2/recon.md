# Recon: fix-migration-guards-v2

## 問題の特定

### 現象
deploy が migration 191 (`20260901_120000_add_unit_inference_columns_t004.sql`) で失敗。

### 根本原因
`scripts/run_all_migrations.sh` は全マイグレーションを毎回実行する（冪等性必須）。
`20260921_050000_drop_tenant004_pipeline_tables.sql` がパイプラインテーブルを DROP した後、
先行マイグレーションが再実行されると2箇所で失敗する。

### 失敗箇所（調査結果）

**ファイル1**: `migrations/20260901_120000_add_unit_inference_columns_t004.sql:40-44`
- `information_schema.columns` で列の存在確認 → テーブル自体が存在しない場合は行なし
- `IF NOT EXISTS` が TRUE → `EXECUTE ALTER TABLE analysis_results ADD COLUMN ...` → テーブル不在で FAIL
- 参照: `migrations/20260921_050000_drop_tenant004_pipeline_tables.sql` (analysis_results を DROP)

**ファイル2**: `migrations/20260913_150000_tcg_empty_box_condition.sql:14-21`
- `table_count` を6テーブルで計算 → `conditions` は残存（table_count=1）、その他は削除（table_count<6）
- `IF table_count <> 6 THEN RAISE EXCEPTION 'empty box: incomplete TCG structure'` → FAIL
- `conditions` は削除対象外のため table_count = 1 となる

### PR #3641 との差分
PR #3641 は `20260905_*`〜`20260910_*` 6ファイルを修正したが、上記2ファイルを見落とした。

### ADR参照
- ADR-082: `scripts/run_all_migrations.sh` 統合ランナー（冪等性必須）
- 関連: `docs/adr/ADR-082*.md`（実在確認済み）

## 修正方針
- `20260901_120000`: テーブル存在チェックを追加（スキーマガード直後）
- `20260913_150000`: パイプラインテーブル全削除時のスキップを追加
