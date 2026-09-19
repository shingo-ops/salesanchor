-- Backfill 7 NULL work_id values then apply NOT NULL constraint
-- This migration was never successfully applied (always failed on NULL values)
-- Backfill uses verified UUID→INTEGER mapping from existing products with same work_id_old_uuid
-- Idempotent: backfill only affects NULL rows; NOT NULL is no-op if already applied

DO $$
BEGIN
  -- Phase 1: Backfill NULL work_id (only when post-recast INTEGER column exists)
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'products'
    AND column_name = 'work_id' AND data_type = 'integer'
  ) AND EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'products'
    AND column_name = 'work_id_old_uuid'
  ) THEN
    UPDATE public.products
    SET work_id = CASE work_id_old_uuid
      WHEN '2fe437c0-5a47-4311-9b94-0c107f64adcd' THEN 1   -- Pokemon
      WHEN '1129cb04-6002-44a5-bf6f-acc609c17b9c' THEN 5   -- Yu-Gi-Oh
      WHEN 'c6acce0e-fe08-446a-adae-8e9bc946b8b0' THEN 2   -- One Piece
      WHEN '1f8c5b4b-94f2-4149-aa6f-b09dd63d1d27' THEN 23  -- LORCANA
    END
    WHERE work_id IS NULL
    AND work_id_old_uuid IN (
      '2fe437c0-5a47-4311-9b94-0c107f64adcd',
      '1129cb04-6002-44a5-bf6f-acc609c17b9c',
      'c6acce0e-fe08-446a-adae-8e9bc946b8b0',
      '1f8c5b4b-94f2-4149-aa6f-b09dd63d1d27'
    );
  END IF;

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
