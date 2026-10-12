-- Migration: 20260921_130000_drop_tenant004_master_copies.sql
-- ADR-156 Phase 5: Drop tenant_004 master table copies
--
-- All code now reads from public schema (SSOT).
-- Backend rewired: tcg_work_comparison_svc._PUBLIC_MASTER covers all 8 tables.
-- tcg_mirror._fetch_db_structure queries public for keyword/alias tables.
-- These tenant_004 copies are no longer referenced by any app code.
--
-- DROP order: children before parents (FK constraints within tenant_004).
--   - condition_aliases references conditions → drop aliases first
--   - unit_aliases references units → drop aliases first
--   - product_search_keywords / product_exclude_keywords reference tcg_products (not dropped)
--     → CASCADE will drop the FK constraints from those tables
--   - tcg_products references tcg_major_categories, tcg_product_categories (not dropped here)
--     → CASCADE will drop the FK constraints from tcg_products
-- analysis_results was already dropped by 20260921_050000_drop_tenant004_pipeline_tables.sql

-- ============================================================
-- Alias tables (children first)
-- ============================================================
DROP TABLE IF EXISTS tenant_004.condition_aliases CASCADE;
DROP TABLE IF EXISTS tenant_004.unit_aliases CASCADE;

-- ============================================================
-- Keyword tables
-- ============================================================
DROP TABLE IF EXISTS tenant_004.product_search_keywords CASCADE;
DROP TABLE IF EXISTS tenant_004.product_exclude_keywords CASCADE;

-- ============================================================
-- Parent master tables
-- ============================================================
DROP TABLE IF EXISTS tenant_004.conditions CASCADE;
DROP TABLE IF EXISTS tenant_004.units CASCADE;
DROP TABLE IF EXISTS tenant_004.tcg_product_categories CASCADE;
DROP TABLE IF EXISTS tenant_004.tcg_major_categories CASCADE;

-- ============================================================
-- Note / status master tables
-- ============================================================
DROP TABLE IF EXISTS tenant_004.tcg_note_master CASCADE;
DROP TABLE IF EXISTS tenant_004.tcg_status_master CASCADE;
