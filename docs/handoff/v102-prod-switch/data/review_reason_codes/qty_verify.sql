-- quantity_not_in_text 追加の verify（読み取り）。
SELECT code || '|' || source || '|' || fix_stage FROM public.review_reason_codes WHERE code='quantity_not_in_text';
SELECT 'ROWS|' || count(*) FROM public.review_reason_codes;
SELECT 'VERIFY_DONE';
