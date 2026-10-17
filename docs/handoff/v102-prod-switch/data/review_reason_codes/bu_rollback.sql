-- 便2 理由コード1つ追加（bundle_unverified）の戻し: 使うのは戻すときだけ。
\set ON_ERROR_STOP on
BEGIN;
DELETE FROM public.review_reason_codes WHERE code = 'bundle_unverified' RETURNING code;
COMMIT;
SELECT 'ROLLBACK_DONE';
