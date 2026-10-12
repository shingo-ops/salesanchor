-- 段2a 理由コード1つ追加の verify（読み取り）。
SELECT code || '|' || source || '|' || fix_stage FROM public.review_reason_codes WHERE code = 'gemini_gap_suspect';
SELECT 'ROWS|' || count(*) FROM public.review_reason_codes;
SELECT 'VERIFY_DONE';
