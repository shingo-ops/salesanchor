-- 便BB 設定4keyの戻し: 使うのは戻すときだけ。消すと買取価格による判定は止まる（何もしない）。
\set ON_ERROR_STOP on
BEGIN;
DELETE FROM public.tcg_distribution_settings
 WHERE key IN ('unit_buyback_box_min', 'unit_buyback_box_max', 'unit_buyback_case_min', 'unit_buyback_max_age_days')
RETURNING key;
COMMIT;
SELECT 'ROLLBACK_DONE';
