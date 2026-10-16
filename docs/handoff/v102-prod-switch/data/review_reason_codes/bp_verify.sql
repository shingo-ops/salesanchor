-- 便2 理由コード1つ追加（bulk_price_basis_unknown）の verify（読み取り）。
SELECT code || '|' || source || '|' || fix_stage FROM public.review_reason_codes WHERE code = 'bulk_price_basis_unknown';
SELECT 'ROWS|' || count(*) FROM public.review_reason_codes;
SELECT 'VERIFY_DONE';
