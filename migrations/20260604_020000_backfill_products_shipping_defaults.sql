-- ADR-093 / 2026-06-04: TCG カード商品の発送ラベル既定値を全商品へ一括設定。
--   品目(item)   = 'Playing card'
--   HSコード(hs_code) = '9504400000'
--   素材(material) = 'Paper'
-- （ひとしさん確定。新規作成時のフォーム既定値は frontend ProductsPage 側で対応済み。）
--
-- 列が存在しない baseline でも失敗しないよう information_schema でガードする
-- （migration-test は単体 baseline で対象列が無い場合があるため。
--  cf. project_seed_migration_column_guard）。
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.columns
             WHERE table_schema = 'public' AND table_name = 'products' AND column_name = 'item')
     AND EXISTS (SELECT 1 FROM information_schema.columns
             WHERE table_schema = 'public' AND table_name = 'products' AND column_name = 'hs_code')
     AND EXISTS (SELECT 1 FROM information_schema.columns
             WHERE table_schema = 'public' AND table_name = 'products' AND column_name = 'material')
  THEN
    UPDATE public.products
       SET item     = 'Playing card',
           hs_code  = '9504400000',
           material = 'Paper';
  END IF;
END $$;
