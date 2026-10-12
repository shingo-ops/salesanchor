-- 便UP 理由コード1つ追加の戻し: 使うのは戻すときだけ。
\set ON_ERROR_STOP on
BEGIN;
DELETE FROM public.review_reason_codes WHERE code = 'unit_price_mismatch' RETURNING code;
COMMIT;
SELECT 'ROLLBACK_DONE';
