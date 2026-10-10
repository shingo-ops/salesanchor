-- quantity_unresolved 追加の verify（読み取り）。
SELECT code || '|' || source || '|' || fix_stage FROM public.review_reason_codes WHERE code='quantity_unresolved';
SELECT 'ROWS|' || count(*) FROM public.review_reason_codes;
SELECT 'VERIFY_DONE';
