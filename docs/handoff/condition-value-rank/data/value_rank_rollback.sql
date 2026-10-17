-- 状態の価値順（ADR-1023）値の戻し: 使うのは戻すときだけ。11 行を NULL に戻す。
\set ON_ERROR_STOP on
BEGIN;
DO $$
DECLARE
    n integer;
BEGIN
    UPDATE public.line_conditions
       SET value_group = NULL, value_rank = NULL, updated_at = now()
     WHERE code IN ('CN0003','CN0004','CN0005','CN0006','CN20261008072213','CN0001','CN0002','CN0009','CN0007','CN0010','CN0013') AND tenant_id IS NULL AND value_rank IS NOT NULL;
    GET DIAGNOSTICS n = ROW_COUNT;
    IF n <> 11 THEN
        RAISE EXCEPTION 'ROLLED_BACK must be 11 but was %', n;
    END IF;
    RAISE NOTICE 'ROLLED_BACK|%', n;
END $$;
COMMIT;
SELECT 'ROLLBACK_DONE';
