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
-- Only if public.analysis_results exists, has product_id column, AND product_id is still UUID type.
-- Guard: 20260915_120000 (phase_b_fk_rewire_uuid_to_int) converts product_id to INTEGER.
-- If already INTEGER, FK to uuid tcg_uuid would fail with type mismatch.
DO $$
DECLARE
  _pid_type OID;
BEGIN
  -- 型チェック: product_id が UUID 型でなければ FK 作成をスキップ
  SELECT a.atttypid INTO _pid_type
  FROM pg_attribute a
  JOIN pg_class c ON c.oid = a.attrelid
  JOIN pg_namespace n ON n.oid = c.relnamespace
  WHERE n.nspname = 'public'
    AND c.relname = 'analysis_results'
    AND a.attname = 'product_id'
    AND NOT a.attisdropped;

  IF _pid_type IS DISTINCT FROM (SELECT oid FROM pg_type WHERE typname = 'uuid') THEN
    RAISE NOTICE 'Skipped: public.analysis_results.product_id is not UUID (atttypid=%). FK rewire not applicable.', _pid_type;
  ELSIF EXISTS (
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
