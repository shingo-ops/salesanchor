-- 便2 理由コード1つ追加（bulk_price_basis_unknown）の戻し: 使うのは戻すときだけ。
\set ON_ERROR_STOP on
BEGIN;
DELETE FROM public.review_reason_codes WHERE code = 'bulk_price_basis_unknown' RETURNING code;
COMMIT;
SELECT 'ROLLBACK_DONE';
