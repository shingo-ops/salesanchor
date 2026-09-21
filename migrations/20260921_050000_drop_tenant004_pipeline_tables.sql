-- Migration: 20260921_050000_drop_tenant004_pipeline_tables.sql
-- Purpose: Drop tenant_004 pipeline tables after data migration to public (Step 5/5)
-- Prereqs: Steps 1-4 complete (public DDL, data migration, backend rewiring)
--
-- DROP order: reverse of creation order (children before parents due to FK)
-- Also drops legacy analysis backup tables

-- ============================================================
-- Legacy analysis backup tables (created by prior migrations)
-- ============================================================
DROP TABLE IF EXISTS tenant_004.analysis_results_gas_baseline_20260903;
DROP TABLE IF EXISTS tenant_004.analysis_results_pre_hist01_20260904;

-- ============================================================
-- Category D: analysis tables (children first)
-- ============================================================
DROP TABLE IF EXISTS tenant_004.analysis_run_snapshots;
DROP TABLE IF EXISTS tenant_004.analysis_results;
DROP TABLE IF EXISTS tenant_004.analysis_runs;

-- ============================================================
-- Category A: extraction tables (children first)
-- ============================================================
DROP TABLE IF EXISTS tenant_004.extraction_attempts;
DROP TABLE IF EXISTS tenant_004.extraction_items;
DROP TABLE IF EXISTS tenant_004.extraction_jobs;

-- ============================================================
-- Category B: import tables (children first)
-- ============================================================
DROP TABLE IF EXISTS tenant_004.import_job_messages;
DROP TABLE IF EXISTS tenant_004.import_jobs;

-- ============================================================
-- Category E: correction / normalization
-- ============================================================
DROP TABLE IF EXISTS tenant_004.item_corrections;
DROP TABLE IF EXISTS tenant_004.tcg_normalization_rules;

-- ============================================================
-- Category F: distribution / product import / audit
-- ============================================================
DROP TABLE IF EXISTS tenant_004.tcg_product_import_rows;
DROP TABLE IF EXISTS tenant_004.tcg_product_import_jobs;
DROP TABLE IF EXISTS tenant_004.tcg_distribution_targets;
DROP TABLE IF EXISTS tenant_004.tcg_distribution_settings;
DROP TABLE IF EXISTS tenant_004.audit_log;

-- ============================================================
-- Category C: source / channel tables (parents last)
-- ============================================================
DROP TABLE IF EXISTS tenant_004.source_messages;
DROP TABLE IF EXISTS tenant_004.supplier_channels;
