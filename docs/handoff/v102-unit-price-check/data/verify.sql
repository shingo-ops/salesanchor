-- 便UP 設定3keyの verify（読み取り）。3行（ratio|3、min_posts|3、single_ratio|5）が出ること。
SELECT key || '|' || value FROM public.tcg_distribution_settings
 WHERE key IN ('unit_price_check_ratio', 'unit_price_check_min_posts', 'unit_price_check_single_ratio') ORDER BY key;
SELECT 'VERIFY_DONE';
