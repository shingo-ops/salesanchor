-- 便G 理由コード4つ追加の verify（読み取り）。
SELECT code || '|' || source || '|' || fix_stage FROM public.review_reason_codes
 WHERE code IN ('price_source_mismatch', 'quantity_source_mismatch', 'value_out_of_range', 'item_mapping_mismatch')
 ORDER BY code;
SELECT 'ROWS|' || count(*) FROM public.review_reason_codes;
SELECT 'VERIFY_DONE';
