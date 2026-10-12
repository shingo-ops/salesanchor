-- Backfill 7 NULL work_id values then apply NOT NULL constraint
-- This migration was never successfully applied (always failed on NULL values)
-- Backfill uses verified UUID→INTEGER mapping from existing products with same work_id_old_uuid
-- Idempotent: backfill only affects NULL rows; NOT NULL is no-op if already applied

DO $$
BEGIN
  -- NEUTRALIZED (ADR-1007 / ADR-155, 2026-10-07): Phase 1（work_id_old_uuid からの work_id 補完）を外した（本番は work_id が NOT NULL）。
  RAISE NOTICE 'ADR-1007 neutralized: work_id backfill removed';

  -- Phase 2: Apply NOT NULL constraint
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'products'
    AND column_name = 'work_id' AND is_nullable = 'YES'
  ) THEN
    -- Verify no NULLs remain before applying constraint
    IF NOT EXISTS (SELECT 1 FROM public.products WHERE work_id IS NULL) THEN
      ALTER TABLE public.products ALTER COLUMN work_id SET NOT NULL;
    ELSE
      RAISE EXCEPTION 'Cannot apply NOT NULL: % rows still have NULL work_id',
        (SELECT COUNT(*) FROM public.products WHERE work_id IS NULL);
    END IF;
  END IF;
END $$;
