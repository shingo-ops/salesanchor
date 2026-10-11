-- 便UP 理由コード1つ追加の precheck（読み取り）。
SELECT 'TABLE|' || COALESCE(to_regclass('public.review_reason_codes')::text, 'NULL');
SELECT 'ROWS|' || count(*) FROM public.review_reason_codes;
SELECT 'HAS_NEW|' || count(*) FROM public.review_reason_codes WHERE code = 'unit_price_mismatch';
SELECT 'PRECHECK_DONE';
