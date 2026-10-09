-- 便A precheck（読み取り）: 表があり・空で・アプリの利用者が SELECT できること。
SELECT 'TABLE|' || COALESCE(to_regclass('public.review_reason_codes')::text, 'NULL');
SELECT 'ROWS|' || count(*) FROM public.review_reason_codes;
SELECT 'APP_SELECT|' || has_table_privilege('salesanchor_app', 'public.review_reason_codes', 'SELECT');
SELECT 'PRECHECK_DONE';
