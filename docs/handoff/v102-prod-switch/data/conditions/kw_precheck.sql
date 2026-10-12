-- Opened box (id=18, CN0006) の search_kw 追加の precheck（読み取り）。
SELECT 'TABLE|' || COALESCE(to_regclass('public.conditions')::text, 'NULL');
SELECT 'ROWS|' || count(*) FROM public.conditions;
SELECT 'ROW18|' || id || '|' || code || '|' || canonical FROM public.conditions WHERE id = 18;
SELECT 'EXACT_CURRENT|' || (search_kw = 'ペリ無,ペリなし,ペリ無し,ぺりぺり無し,ぺりぺり無,検品のため一度開封済み,確認のため開封済み') FROM public.conditions WHERE id = 18;
SELECT 'HAS_NEW_WORD|' || count(*) FROM public.conditions WHERE search_kw LIKE '%検品のため開封済み%' OR exclude_kw LIKE '%検品のため開封済み%';
SELECT 'PRECHECK_DONE';
