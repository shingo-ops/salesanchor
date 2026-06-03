-- ADR-093 / 2026-06-04: TCG カード商品の発送ラベル既定値を「未設定の行のみ」設定する。
--   品目(item)        = 'Playing card'
--   HSコード(hs_code)  = '9504400000'
--   素材(material)     = 'Paper'
-- （ひとしさん確定。新規作成時のフォーム既定値は frontend ProductsPage 側で対応済み。）
--
-- 冪等性（重要 / Reviewer PR#1595 Major 対応）:
--   scripts/run_all_migrations.sh はバージョン管理テーブルを持たず、毎デプロイで
--   全 migration を無条件再実行する。無条件 UPDATE にすると、管理者が画面で直した
--   品目/HS/素材を毎回 TCG 既定値へ巻き戻してしまう。さらに product_kind は 'TCG'
--   以外も取り得るため、将来の非 TCG 商品にまで毎回スタンプしてしまう。
--   → 「product_kind='TCG' かつ 当該3列が未設定(NULL/空)の行」だけを COALESCE で埋め、
--     編集済みの値は保持する冪等 UPDATE とする。初回は全 TCG 商品が NULL のため全件埋まる。
--
-- 列が存在しない baseline でも失敗しないよう information_schema でガードする
-- （cf. project_seed_migration_column_guard）。
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.columns
             WHERE table_schema = 'public' AND table_name = 'products' AND column_name = 'item')
     AND EXISTS (SELECT 1 FROM information_schema.columns
             WHERE table_schema = 'public' AND table_name = 'products' AND column_name = 'hs_code')
     AND EXISTS (SELECT 1 FROM information_schema.columns
             WHERE table_schema = 'public' AND table_name = 'products' AND column_name = 'material')
     AND EXISTS (SELECT 1 FROM information_schema.columns
             WHERE table_schema = 'public' AND table_name = 'products' AND column_name = 'product_kind')
  THEN
    UPDATE public.products
       SET item     = COALESCE(NULLIF(item, ''),     'Playing card'),
           hs_code  = COALESCE(NULLIF(hs_code, ''),  '9504400000'),
           material = COALESCE(NULLIF(material, ''), 'Paper')
     WHERE product_kind = 'TCG'
       AND (NULLIF(item, '')     IS NULL
            OR NULLIF(hs_code, '')  IS NULL
            OR NULLIF(material, '') IS NULL);
  END IF;
END $$;
