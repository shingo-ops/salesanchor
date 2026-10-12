-- 便G 理由コード4つ追加の precheck（読み取り）。
SELECT 'TABLE|' || COALESCE(to_regclass('public.review_reason_codes')::text, 'NULL');
SELECT 'ROWS|' || count(*) FROM public.review_reason_codes;
SELECT 'HAS_NEW|' || count(*) FROM public.review_reason_codes
 WHERE code IN ('price_source_mismatch', 'quantity_source_mismatch', 'value_out_of_range', 'item_mapping_mismatch');
SELECT 'PRECHECK_DONE';
