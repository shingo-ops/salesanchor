-- 段2a 理由コード1つ追加の戻し: 使うのは戻すときだけ。
\set ON_ERROR_STOP on
BEGIN;
DELETE FROM public.review_reason_codes WHERE code = 'gemini_gap_suspect' RETURNING code;
COMMIT;
SELECT 'ROLLBACK_DONE';
