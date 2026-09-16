-- Add resolved_product_code to extraction_items for Gemini v5 product identification
-- CI環境: tenant_004 は Python migration が作成するため SQL-only テストでは存在しない場合がある
DO $$ BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'tenant_004'
      AND table_name  = 'extraction_items'
      AND column_name = 'resolved_work_id'
  ) THEN
    ALTER TABLE tenant_004.extraction_items
        ADD COLUMN IF NOT EXISTS resolved_product_code text;
    COMMENT ON COLUMN tenant_004.extraction_items.resolved_product_code
        IS 'Gemini v5 が商品マスタ参照から解決した商品コード (PM0263等)。NULL=未解決/v4以前';
  END IF;
END $$;
