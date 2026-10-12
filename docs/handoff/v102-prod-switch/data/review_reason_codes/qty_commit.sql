-- quantity_not_in_text commit: dryrun 成功の印がある時だけ実行する。
\set ON_ERROR_STOP on
BEGIN;
INSERT INTO public.review_reason_codes (code, source, fix_stage) VALUES
    ('quantity_not_in_text', 'system', 'extraction');
DO $$
DECLARE n int; c int;
BEGIN
    SELECT count(*) INTO n FROM public.review_reason_codes;
    SELECT count(*) INTO c FROM public.review_reason_codes
     WHERE code='quantity_not_in_text' AND source='system' AND fix_stage='extraction';
    IF n <> 30 OR c <> 1 THEN
        RAISE EXCEPTION 'CHECK_NG rows=% qty=%', n, c;
    END IF;
END $$;
SELECT 'CHECK_OK 1';
COMMIT;
SELECT 'COMMIT_DONE';
