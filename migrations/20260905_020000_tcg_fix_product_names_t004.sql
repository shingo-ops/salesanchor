-- 既存商品5件の名称・型番の訂正（tenant_004 専用・冪等）
--
-- 公式サイトと突き合わせて判明した誤りを直す。
-- 変更するのは japanese_title 4件と mark 1件のみ。
-- キーワード・除外キーワード・発売日・英語名は一切変更しない。
--
-- 承認: Shingo 2026-09-05
-- バックアップ: tenant_004.tcg_products_bak_20260905 (296)
--
-- 出典:
--   PM0056 公式商品一覧 pokemon-card.com/products/
--   PM0182 PM0186 PM0189 公式ニュース pokemon-card.com/info/005053.html
--   PM0200 公式商品ページURL pokemon-card.com/ex/mc/ ほか4サイト一致

-- NEUTRALIZED (ADR-1007 / ADR-155, 2026-10-09):
-- japanese_title 4件・mark 1件の訂正 UPDATE と、その検証を外した。
-- 元の内容は git history で参照可能。
DO $$ BEGIN RAISE NOTICE 'ADR-1007 neutralized: tcg_products name/mark fix removed'; END $$;
