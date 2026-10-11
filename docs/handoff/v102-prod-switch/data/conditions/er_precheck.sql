-- 状態「Error」(CN0012) 追加の precheck（読み取り）。
SELECT 'TABLE|' || COALESCE(to_regclass('public.conditions')::text, 'NULL');
SELECT 'ROWS|' || count(*) FROM public.conditions;
SELECT 'CN0012_ROWS|' || count(*) FROM public.conditions WHERE code = 'CN0012';
SELECT 'ERROR_CANONICAL_ROWS|' || count(*) FROM public.conditions WHERE canonical = 'Error';
SELECT 'EXCLUDE_ROWS|' || count(*) FROM public.conditions WHERE effect = 'EXCLUDE';
SELECT 'PRECHECK_DONE';
