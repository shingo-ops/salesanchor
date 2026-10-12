-- 便G 理由コード4つ追加 dryrun: 入れて検査して必ず ROLLBACK。入れた件数が4でなければゼロ除算で失敗する。
\set ON_ERROR_STOP on
BEGIN;
WITH ins AS (
    INSERT INTO public.review_reason_codes (code, source, fix_stage) VALUES
        ('price_source_mismatch', 'system', 'analysis'),
        ('quantity_source_mismatch', 'system', 'analysis'),
        ('value_out_of_range', 'system', 'analysis'),
        ('item_mapping_mismatch', 'system', 'analysis')
    RETURNING code
)
SELECT CASE WHEN count(*) = 4 THEN 'INSERTED|4' ELSE (1 / (count(*) - count(*)))::text END FROM ins;
SELECT CASE WHEN count(*) = 4 THEN 'CHECK_OK 4' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.review_reason_codes
 WHERE source = 'system' AND fix_stage = 'analysis'
   AND code IN ('price_source_mismatch', 'quantity_source_mismatch', 'value_out_of_range', 'item_mapping_mismatch');
SELECT CASE WHEN count(*) = 35 THEN 'ROWS_OK 35' ELSE (1 / (count(*) - count(*)))::text END FROM public.review_reason_codes;
ROLLBACK;
SELECT 'DRYRUN_OK';
