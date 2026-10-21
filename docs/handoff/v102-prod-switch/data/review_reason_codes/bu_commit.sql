-- ADR-1027 理由コード1つ追加（bundle_unverified） commit: dryrun 成功の印がある時だけ実行する。件数が合わなければゼロ除算で失敗し、COMMIT に進まない。
\set ON_ERROR_STOP on
BEGIN;
WITH ins AS (
    INSERT INTO public.review_reason_codes (code, source, fix_stage) VALUES
        ('bundle_unverified', 'system', 'analysis')
    RETURNING code
)
SELECT CASE WHEN count(*) = 1 THEN 'INSERTED|1' ELSE (1 / (count(*) - count(*)))::text END FROM ins;
SELECT CASE WHEN count(*) = 1 THEN 'CHECK_OK 1' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.review_reason_codes
 WHERE source = 'system' AND fix_stage = 'analysis' AND code = 'bundle_unverified';
SELECT CASE WHEN count(*) = 39 THEN 'ROWS_OK 39' ELSE (1 / (count(*) - count(*)))::text END FROM public.review_reason_codes;
COMMIT;
SELECT 'COMMIT_DONE';
