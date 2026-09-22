-- 細分類(product_formats)に中分類(type_master)への直接リンクを追加
-- カードゲームごとの細分類フィルタリングを実現する

-- Step 1: type_master_id カラム追加（CI test DB 用。本番には既存）
DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'product_formats' AND column_name = 'type_master_id'
  ) THEN
    ALTER TABLE public.product_formats ADD COLUMN type_master_id INTEGER REFERENCES public.type_master(id) ON DELETE SET NULL;
    RAISE NOTICE 'Added type_master_id to product_formats';
  ELSE
    RAISE NOTICE 'type_master_id already exists on product_formats, skip';
  END IF;
END $$;

-- Step 2: kind_id カラム追加（CI test DB 用。本番には既存）
DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'product_formats' AND column_name = 'kind_id'
  ) THEN
    ALTER TABLE public.product_formats ADD COLUMN kind_id INTEGER REFERENCES public.product_kinds(id) ON DELETE SET NULL;
    RAISE NOTICE 'Added kind_id to product_formats';
  ELSE
    RAISE NOTICE 'kind_id already exists on product_formats, skip';
  END IF;
END $$;

-- Step 3: 商品データ実績に基づく type_master_id 設定（9件）
-- 根拠: public.products の product_format_id × type_master_id クロス集計結果
-- ポケモンカード(type_master_id=1): SPECIAL_BOX(17), DECK_BUILD_BOX(18), PREMIUM_TRAINER_BOX(19), COLLECTOR_BOX(20), HIGH_CLASS_DECK(21), BOOSTER_BOX(22)
UPDATE public.product_formats SET type_master_id = 1, updated_at = NOW() WHERE id IN (17, 18, 19, 20, 21, 22) AND type_master_id IS NULL;

-- 遊戯王(type_master_id=5): SPECIAL_SET(23)
UPDATE public.product_formats SET type_master_id = 5, updated_at = NOW() WHERE id = 23 AND type_master_id IS NULL;

-- One Piece(type_master_id=2): ILLUSTRATION_BOX(24), STORAGE_BOX(25)
UPDATE public.product_formats SET type_master_id = 2, updated_at = NOW() WHERE id IN (24, 25) AND type_master_id IS NULL;

-- id 1-16 は商品紐付け0件のため type_master_id = NULL 据置（PO判断待ち）
