-- 便BB 設定4key投入の precheck（読み取り）。HAS_NEW|0 が出ること。
SELECT 'TABLE|' || COALESCE(to_regclass('public.tcg_distribution_settings')::text, 'NULL');
SELECT 'HAS_NEW|' || count(*) FROM public.tcg_distribution_settings WHERE key IN ('unit_buyback_box_min', 'unit_buyback_box_max', 'unit_buyback_case_min', 'unit_buyback_max_age_days');
SELECT 'PRECHECK_DONE';
