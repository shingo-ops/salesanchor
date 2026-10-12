-- quantity_unresolved の追加（便PQ）の戻し: 使うのは戻すときだけ。
\set ON_ERROR_STOP on
BEGIN;
DELETE FROM public.review_reason_codes WHERE code = 'quantity_unresolved' RETURNING code;
COMMIT;
SELECT 'ROLLBACK_DONE';
