-- Fix: DROP stale FK constraints that block Phase 2c (DROP tenant_004.tcg_products)
--
-- Problem: Phase 2a only looped over tenant_% schemas, missing
-- public.analysis_results. Two stale FKs remain pointing to tenant_004.tcg_products.
--
-- This migration ONLY drops the stale FKs. It does NOT add new FKs.
-- The correct FK (→ public.products) will be handled separately after
-- the tcg_uuid column exists (Phase 2b migration order dependency).
--
-- Fix (2026-09-24): Added SET lock_timeout to prevent deploy timeout.
-- DROP CONSTRAINT requires ACCESS EXCLUSIVE lock; if a long-running
-- transaction holds a lock on analysis_results, the ALTER waits indefinitely.
-- With lock_timeout='30s', the statement fails fast instead of blocking for 10min.
-- The constraint does not exist on prod (confirmed 2026-09-24), so the
-- IF NOT EXISTS path exits immediately once a lock is obtained.

BEGIN;

SET LOCAL lock_timeout = '30s';
SET LOCAL statement_timeout = '60s';

ALTER TABLE IF EXISTS public.analysis_results
  DROP CONSTRAINT IF EXISTS analysis_results_product_id_fkey;

ALTER TABLE IF EXISTS tenant_004.analysis_results
  DROP CONSTRAINT IF EXISTS analysis_results_product_id_fkey;

COMMIT;
