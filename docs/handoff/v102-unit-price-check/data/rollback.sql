-- 便UP 設定3keyの戻し: 使うのは戻すときだけ。消すと単位と価格の確認は止まる（何もしない）。
\set ON_ERROR_STOP on
BEGIN;
DELETE FROM public.tcg_distribution_settings
 WHERE key IN ('unit_price_check_ratio', 'unit_price_check_min_posts', 'unit_price_check_single_ratio')
RETURNING key;
COMMIT;
SELECT 'ROLLBACK_DONE';
