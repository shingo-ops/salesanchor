-- 状態「Error」(CN0012) 追加の verify（読み取り）。
SELECT 'ROWS|' || count(*) FROM public.conditions;
SELECT 'CN0012|' || id || '|' || code || '|' || canonical || '|' || COALESCE(app_kubun, 'NULL') || '|' || is_active || '|' || priority
       || '|' || search_kw || '|' || exclude_kw || '|' || match_type || '|' || effect || '|' || note
  FROM public.conditions WHERE code = 'CN0012';
SELECT 'EXCLUDE_ROWS|' || count(*) FROM public.conditions WHERE effect = 'EXCLUDE';
SELECT 'VERIFY_DONE';
