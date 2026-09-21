-- Fix: DROP stale FK constraints that block Phase 2c (DROP tenant_004.tcg_products)
--
-- Problem: Phase 2a (20260914_140000) only looped over tenant_% schemas,
-- missing public.analysis_results. Two stale FKs remain:
--   1. public.analysis_results.analysis_results_product_id_fkey → tenant_004.tcg_products
--   2. tenant_004.analysis_results.analysis_results_product_id_fkey → tenant_004.tcg_products
--
-- Fix: DROP both stale FKs. Phase 2a already added the correct FK
-- (fk_analysis_results_product_public → public.products(tcg_uuid))
-- for tenant schemas. public.analysis_results gets the same treatment.

BEGIN;

-- 1. Drop stale FK on public.analysis_results
ALTER TABLE IF EXISTS public.analysis_results
  DROP CONSTRAINT IF EXISTS analysis_results_product_id_fkey;

-- 2. Drop stale FK on tenant_004.analysis_results
ALTER TABLE IF EXISTS tenant_004.analysis_results
  DROP CONSTRAINT IF EXISTS analysis_results_product_id_fkey;

-- 3. Add correct FK on public.analysis_results (same as Phase 2a does for tenant schemas)
-- Only if public.analysis_results exists and has product_id column
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'analysis_results' AND column_name = 'product_id'
  ) AND NOT EXISTS (
    SELECT 1 FROM information_schema.table_constraints
    WHERE table_schema = 'public' AND table_name = 'analysis_results'
      AND constraint_name = 'fk_analysis_results_product_public'
  ) THEN
    ALTER TABLE public.analysis_results
      ADD CONSTRAINT fk_analysis_results_product_public
      FOREIGN KEY (product_id)
      REFERENCES public.products(tcg_uuid);
    RAISE NOTICE 'Added fk_analysis_results_product_public on public.analysis_results';
  ELSE
    RAISE NOTICE 'Skipped: FK already exists or table/column not found';
  END IF;
END $$;

COMMIT;
