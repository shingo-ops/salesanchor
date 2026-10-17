-- 状態の価値順（ADR-1023）値の投入 dryrun: 更新して検査して必ず ROLLBACK。
\set ON_ERROR_STOP on
BEGIN;
DO $$
DECLARE
    n integer;
BEGIN
    WITH v(code, grp, rnk) AS (
        VALUES
        ('CN0003', 'box', 1),
        ('CN0004', 'box', 2),
        ('CN0005', 'box', 3),
        ('CN0006', 'box', 4),
        ('CN20261008072213', 'box', 5),
        ('CN0001', 'case', 1),
        ('CN0002', 'case', 2),
        ('CN0009', 'case', 3),
        ('CN0007', 'pack', 1),
        ('CN0010', 'pack', 2),
        ('CN0013', 'pack', 3)
    ), u AS (
        UPDATE public.line_conditions lc
           SET value_group = v.grp, value_rank = v.rnk, updated_at = now()
          FROM v
         WHERE lc.code = v.code AND lc.tenant_id IS NULL AND lc.value_rank IS NULL
        RETURNING lc.id
    )
    SELECT count(*) INTO n FROM u;
    IF n <> 11 THEN
        RAISE EXCEPTION 'UPDATED must be 11 but was %', n;
    END IF;
    RAISE NOTICE 'UPDATED|%', n;
END $$;
SELECT 'AFTER|' || code || '|' || canonical || '|' || value_group || '|' || value_rank
  FROM public.line_conditions WHERE value_rank IS NOT NULL AND tenant_id IS NULL ORDER BY value_group, value_rank;
ROLLBACK;
SELECT 'DRYRUN_OK';
