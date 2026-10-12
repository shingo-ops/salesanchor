-- 便BB 設定4keyの verify（読み取り）。4行（box_max|2、box_min|0.5、case_min|6、max_age_days|7）が出ること。
SELECT key || '|' || value FROM public.tcg_distribution_settings
 WHERE key IN ('unit_buyback_box_min', 'unit_buyback_box_max', 'unit_buyback_case_min', 'unit_buyback_max_age_days') ORDER BY key;
SELECT 'VERIFY_DONE';
