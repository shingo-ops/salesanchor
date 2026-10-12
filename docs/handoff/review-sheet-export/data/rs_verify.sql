-- 要確認タブ名の設定 verify（読み取り）。
SELECT name || '|' || COALESCE(review_sheet_name, 'NULL') FROM public.tcg_distribution_targets ORDER BY name;
SELECT 'SET_ROWS|' || count(*) FROM public.tcg_distribution_targets WHERE review_sheet_name IS NOT NULL;
SELECT 'ALL_ROWS|' || count(*) FROM public.tcg_distribution_targets;
SELECT 'VERIFY_DONE';
