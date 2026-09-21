# Recon: pipeline-rewire-public (Step 4/5)

## 対象ブランチ
release/pipeline-rewire-public

## 調査結果

TCG_SCHEMA参照の全走査結果（`grep -rn "TCG_SCHEMA" backend/app/ --include="*.py"`）:

- 17テーブルへの参照: 202箇所（25ファイル）
- 非移行テーブルへの参照（TCG_SCHEMA維持）: LOOKUP_TABLES（tcg_major_categories, tcg_manufacturers, tcg_product_categories）
- metadata用途（変更不要）: line_import_devices.tcg_schema列値, Redisキープレフィックス, リビジョンハッシュ

## 変更箇所（file:line引用）

代表的な変更箇所:

- `backend/app/services/tcg_line_import_svc.py:348` — `public.supplier_channels` への参照（変更後）
- `backend/app/services/tcg_line_import_svc.py:407` — `public.source_messages` INTO句（変更後）
- `backend/app/tasks/tcg_extraction.py:109` — `public.extraction_jobs` regclass参照（変更後）
- `backend/app/tasks/tcg_extraction.py:158` — `public.extraction_jobs` UPDATE（変更後）
- `backend/app/services/tcg_analyzer_svc.py:77` — `public.products` SELECT（変更後）

## 移行対象17テーブル

supplier_channels, source_messages, import_jobs, import_job_messages,
extraction_jobs, extraction_items, extraction_attempts, analysis_runs,
analysis_results, analysis_run_snapshots, item_corrections,
tcg_normalization_rules, tcg_distribution_settings, tcg_distribution_targets,
tcg_product_import_jobs, tcg_product_import_rows, audit_log

## 参照パターン

1. `{TCG_SCHEMA}.tablename` → `public.tablename` (直接参照)
2. `schema = schema or TCG_SCHEMA` → `schema = schema or "public"` (デフォルト値)
3. `schema=TCG_SCHEMA` → `schema="public"` (関数呼び出し時)
4. `tenant_schema: str = "tenant_004"` → `tenant_schema: str = "public"` (デフォルト値)
5. information_schema クエリの WHERE分割 (tcg_mirror.py)

## 前提PR

- PR #3625: Step 1 (DDL作成) - public schema に17テーブルを作成
