-- ADR-157 Phase 3: 買取商品と自社マスタの自動紐付け
-- product_id を UUID → INTEGER に変更（現在全件NULL、データ影響なし）
-- match_status / match_candidates 列を追加

DO $$
BEGIN
  -- Step 1: product_id の型変更 (UUID → INTEGER)
  -- 全件NULLなので安全に変更可能
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'buyback_shop_products'
      AND column_name = 'product_id'
      AND data_type = 'uuid'
  ) THEN
    ALTER TABLE public.buyback_shop_products
      ALTER COLUMN product_id TYPE INTEGER USING NULL;
  END IF;

  -- Step 2: FK制約追加
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.table_constraints
    WHERE constraint_name = 'fk_buyback_shop_products_product_id'
      AND table_name = 'buyback_shop_products'
  ) THEN
    ALTER TABLE public.buyback_shop_products
      ADD CONSTRAINT fk_buyback_shop_products_product_id
      FOREIGN KEY (product_id) REFERENCES public.products(id);
  END IF;

  -- Step 3: match_status 列追加
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'buyback_shop_products'
      AND column_name = 'match_status'
  ) THEN
    ALTER TABLE public.buyback_shop_products
      ADD COLUMN match_status TEXT NOT NULL DEFAULT 'unmatched';
  END IF;

  -- Step 4: match_candidates 列追加
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'buyback_shop_products'
      AND column_name = 'match_candidates'
  ) THEN
    ALTER TABLE public.buyback_shop_products
      ADD COLUMN match_candidates JSONB;
  END IF;
END $$;
