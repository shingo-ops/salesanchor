-- ADR-1027 理由コード1つ追加（bundle_unverified）の verify（読み取り）。
SELECT code || '|' || source || '|' || fix_stage FROM public.review_reason_codes WHERE code = 'bundle_unverified';
SELECT 'ROWS|' || count(*) FROM public.review_reason_codes;
SELECT 'VERIFY_DONE';
