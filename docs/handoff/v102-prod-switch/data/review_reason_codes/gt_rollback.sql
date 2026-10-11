-- 便G 理由コード4つ追加の戻し: 使うのは戻すときだけ。この4コードだけを消す。
\set ON_ERROR_STOP on
BEGIN;
DELETE FROM public.review_reason_codes
 WHERE code IN ('price_source_mismatch', 'quantity_source_mismatch', 'value_out_of_range', 'item_mapping_mismatch')
RETURNING code;
COMMIT;
SELECT 'ROLLBACK_DONE';
