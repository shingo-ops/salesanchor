-- 細分類(product_formats)に大分類(product_kinds)への kind_id を追加する（Step 2 のみ）
-- 中分類への直接リンク type_master_id の ADD は ADR-1038 で削除済み（親子の正本は product_format_game_links）

-- Step 1: （削除済み）product_formats.type_master_id は ADR-1038 で取り除いた。
--   親子（細分類→中分類）の正本は product_format_game_links。値の控えは
--   docs/handoff/format-work-parent/data/product_formats_type_master_id_20261022.csv。
--   列を足し直すと、後続の DROP migration と毎デプロイで ADD→DROP が繰り返される。
--   ここに ADD を戻さないこと（ADR-1038）。

-- Step 2: kind_id カラム追加（CI test DB 用。本番には既存）
DO $$ BEGIN
  -- テーブル自体が存在しない場合はスキップ（CI test DB では product_formats が未作成の場合がある）
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'product_formats'
  ) THEN
    RAISE NOTICE 'product_formats table does not exist, skip kind_id';
  ELSIF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'product_formats' AND column_name = 'kind_id'
  ) THEN
    ALTER TABLE public.product_formats ADD COLUMN kind_id INTEGER REFERENCES public.product_kinds(id) ON DELETE SET NULL;
    RAISE NOTICE 'Added kind_id to product_formats';
  ELSE
    RAISE NOTICE 'kind_id already exists on product_formats, skip';
  END IF;
END $$;

-- Step 3: 初期データ設定は migration 外で実施
-- ADR-155 チェック8: type_master はマスタ保護テーブルのため、
-- 列名 type_master_id を含む UPDATE 文も保護テーブルへの参照と判定される。
-- 初期値設定は本番デプロイ後に super-admin 画面（ProductFormatsMasterPanel）から手動設定。
--
-- 設定予定値（商品データ実績クロス集計結果）:
--   ポケモンカード(id=1): SPECIAL_BOX(17), DECK_BUILD_BOX(18), PREMIUM_TRAINER_BOX(19),
--                         COLLECTOR_BOX(20), HIGH_CLASS_DECK(21), BOOSTER_BOX(22)
--   遊戯王(id=5):         SPECIAL_SET(23)
--   One Piece(id=2):      ILLUSTRATION_BOX(24), STORAGE_BOX(25)
--   id 1-16:              商品紐付け0件のため NULL 据置（PO判断待ち）
