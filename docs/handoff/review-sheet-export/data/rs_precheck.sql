-- 要確認タブ名の設定 precheck（読み取り）。
SELECT 'COLUMN|' || count(*) FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'tcg_distribution_targets' AND column_name = 'review_sheet_name';
SELECT 'TARGET_ROWS|' || count(*) FROM public.tcg_distribution_targets WHERE name = '配信テスト' AND spreadsheet_id = '1unwFM3MZikSmQjZ744uxhvzG2ENhuhcDsvse1dfSrm4';
SELECT 'TARGET_NULL|' || count(*) FROM public.tcg_distribution_targets WHERE name = '配信テスト' AND spreadsheet_id = '1unwFM3MZikSmQjZ744uxhvzG2ENhuhcDsvse1dfSrm4' AND review_sheet_name IS NULL;
SELECT 'OTHER_NOT_NULL|' || count(*) FROM public.tcg_distribution_targets WHERE review_sheet_name IS NOT NULL;
SELECT 'ALL_ROWS|' || count(*) FROM public.tcg_distribution_targets;
SELECT 'PRECHECK_DONE';
