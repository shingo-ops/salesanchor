# Recon: pipeline-drop-tenant004 (Step 5/5)

## 対象ADR
- ADR-1002: tenant_004 → public schema migration

## 関連PR
- PR #3625: Step 1 — public DDL作成
- PR #3627: Step 4 — バックエンド配線切替
- 本PR: Step 5 — tenant_004テーブルDROP

## 調査済みファイル
- `migrations/20260921_050000_drop_tenant004_pipeline_tables.sql`: 本PR作成ファイル（新規）

## DROPテーブル一覧（19本）

### バックアップ（2本）
- `tenant_004.analysis_results_gas_baseline_20260903`
- `tenant_004.analysis_results_pre_hist01_20260904`

### パイプライン（17本）
Category A (extraction): extraction_attempts, extraction_items, extraction_jobs
Category B (import): import_job_messages, import_jobs
Category C (source): source_messages, supplier_channels
Category D (analysis): analysis_run_snapshots, analysis_results, analysis_runs
Category E (correction): item_corrections, tcg_normalization_rules
Category F (distribution): tcg_product_import_rows, tcg_product_import_jobs, tcg_distribution_targets, tcg_distribution_settings, audit_log

## 制約・前提
- Steps 1-4が完全完了後にのみ適用可能
- DROP TABLE IF EXISTS により冪等
- DROP順序はFK依存の逆順（子テーブル → 親テーブル）
