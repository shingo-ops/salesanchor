-- 便UP 理由コード1つ追加 dryrun: 入れて検査して必ず ROLLBACK。
\set ON_ERROR_STOP on
BEGIN;
WITH ins AS (
    INSERT INTO public.review_reason_codes (code, source, fix_stage) VALUES
        ('unit_price_mismatch', 'system', 'analysis')
    RETURNING code
)
SELECT CASE WHEN count(*) = 1 THEN 'INSERTED|1' ELSE (1 / (count(*) - count(*)))::text END FROM ins;
SELECT CASE WHEN count(*) = 1 THEN 'CHECK_OK 1' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.review_reason_codes
 WHERE source = 'system' AND fix_stage = 'analysis' AND code = 'unit_price_mismatch';
SELECT CASE WHEN count(*) = 36 THEN 'ROWS_OK 36' ELSE (1 / (count(*) - count(*)))::text END FROM public.review_reason_codes;
ROLLBACK;
SELECT 'DRYRUN_OK';
