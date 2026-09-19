-- Backfill 7 products with NULL work_id (INTEGER) using verified UUID→ID mapping
-- Required before 20260916_130000_work_id_not_null.sql can apply NOT NULL constraint
-- Idempotent: only updates rows where work_id IS NULL
-- Guards: only runs when work_id is INTEGER and work_id_old_uuid column exists (post-recast state)

DO $$
BEGIN
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
    RAISE NOTICE 'Backfilled NULL work_id values';
  END IF;
END $$;
