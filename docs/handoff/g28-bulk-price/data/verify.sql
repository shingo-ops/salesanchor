-- 状態「Bulk」(CN0014) 追加の verify（読み取り）。期待: ROWS|16、CN0014 の1行、EXCLUDE_ROWS|1、BAD_CONFIG|0。
SELECT 'ROWS|' || count(*) FROM public.line_conditions;
SELECT 'CN0014|' || id || '|' || code || '|' || canonical || '|' || COALESCE(app_kubun, 'NULL') || '|' || is_active || '|' || priority
       || '|' || search_kw || '|' || exclude_kw || '|' || match_type || '|' || effect || '|' || COALESCE(unit_id::text, 'NULL') || '|' || note
  FROM public.line_conditions WHERE code = 'CN0014';
SELECT 'EXCLUDE_ROWS|' || count(*) FROM public.line_conditions WHERE effect = 'EXCLUDE';
-- 固定値と1つでも違えば 1。DEFAULT・search_kw 非空・unit_id 非NULL は禁止（配信 SQL: tcg_distribution_svc.py の状態条件を通るのは effect=OUTPUT かつ canonical が FLAG_ で始まらない行）
SELECT 'BAD_CONFIG|' || count(*) FROM public.line_conditions
 WHERE code = 'CN0014' AND NOT (canonical = 'Bulk' AND app_kubun = '' AND is_active IS TRUE AND priority = 10
   AND search_kw = '' AND exclude_kw = '' AND match_type = 'KEYWORD' AND effect = 'OUTPUT' AND unit_id IS NULL);
SELECT 'BULK_ROWS_CURRENT|' || count(*) FROM public.analysis_results ar JOIN public.line_conditions c ON c.id = ar.condition_id WHERE c.code = 'CN0014' AND ar.is_current IS TRUE;
SELECT 'VERIFY_DONE';
