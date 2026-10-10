-- quantity_not_in_text の追加（PR #4077）の戻し: 使うのは戻すときだけ。
\set ON_ERROR_STOP on
BEGIN;
DELETE FROM public.review_reason_codes WHERE code = 'quantity_not_in_text' RETURNING code;
COMMIT;
SELECT 'ROLLBACK_DONE';
