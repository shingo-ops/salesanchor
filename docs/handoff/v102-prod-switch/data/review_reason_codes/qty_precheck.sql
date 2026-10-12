-- quantity_not_in_text 追加の precheck（読み取り）。
SELECT 'TABLE|' || COALESCE(to_regclass('public.review_reason_codes')::text, 'NULL');
SELECT 'ROWS|' || count(*) FROM public.review_reason_codes;
SELECT 'HAS_QTY|' || count(*) FROM public.review_reason_codes WHERE code='quantity_not_in_text';
SELECT 'PRECHECK_DONE';
