-- ADR-1001: public.products.work_id を NOT NULL に変更
-- 前提: 全1,830件で work_id が設定済み（NULL 0件、2026-09-16確認済み）
-- CI環境: public.products は Python migration が作成するため SQL-only テストでは存在しない場合がある
DO $$ BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'products'
      AND column_name = 'work_id'
  ) THEN
    ALTER TABLE public.products ALTER COLUMN work_id SET NOT NULL;
  END IF;
END $$;
