-- Opened box search_kw 追加の verify（読み取り）。
SELECT 'ROW18|' || id || '|' || code || '|' || search_kw FROM public.conditions WHERE id = 18;
SELECT 'EXACT_NEW|' || (search_kw = 'ペリ無,ペリなし,ペリ無し,ぺりぺり無し,ぺりぺり無,検品のため一度開封済み,確認のため開封済み,検品のため開封済み') FROM public.conditions WHERE id = 18;
SELECT 'ROWS|' || count(*) FROM public.conditions;
SELECT 'VERIFY_DONE';
