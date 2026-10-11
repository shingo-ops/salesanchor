-- 便UP 設定2key投入の precheck（読み取り）。
SELECT 'TABLE|' || COALESCE(to_regclass('public.tcg_distribution_settings')::text, 'NULL');
SELECT 'HAS_NEW|' || count(*) FROM public.tcg_distribution_settings WHERE key IN ('unit_price_check_ratio', 'unit_price_check_min_posts');
SELECT 'PRECHECK_DONE';
