-- 便UP 設定2keyの verify（読み取り）。
SELECT key || '|' || value FROM public.tcg_distribution_settings WHERE key IN ('unit_price_check_ratio', 'unit_price_check_min_posts') ORDER BY key;
SELECT 'VERIFY_DONE';
