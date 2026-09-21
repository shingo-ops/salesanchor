-- Fix: DROP stale FK constraints that block Phase 2c (DROP tenant_004.tcg_products)
--
-- Problem: Phase 2a only looped over tenant_% schemas, missing
-- public.analysis_results. Two stale FKs remain pointing to tenant_004.tcg_products.
--
-- This migration ONLY drops the stale FKs. It does NOT add new FKs.
-- The correct FK (→ public.products) will be handled separately after
-- the tcg_uuid column exists (Phase 2b migration order dependency).

BEGIN;

ALTER TABLE IF EXISTS public.analysis_results
  DROP CONSTRAINT IF EXISTS analysis_results_product_id_fkey;

ALTER TABLE IF EXISTS tenant_004.analysis_results
  DROP CONSTRAINT IF EXISTS analysis_results_product_id_fkey;

COMMIT;
