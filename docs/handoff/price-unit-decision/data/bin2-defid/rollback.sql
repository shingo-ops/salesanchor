-- 価格で単位を決める 便2 札と組の一覧の戻し: 戻すときだけ。ADR-1007・ADR-1036。
-- 順序: 先にコード（札を読む便2）を revert してからこれを流す。コードが札を読んでいる間に札を消すと、便BB の Box・Case も何もしなくなる。
-- commit の逆: 8 行の札を NULL に戻し（CN0002=3・CN20261008072213=8 は触らない）、組の一覧の 2 行（CASE×SEALED・BOX×SEARCHED）を消す。
-- 件数が合わなければゼロ除算で失敗し、COMMIT に進まない。
\set ON_ERROR_STOP on
BEGIN;
WITH upd AS (
    UPDATE public.line_conditions lc
       SET condition_def_id = NULL, updated_at = NOW()
      FROM (VALUES
    ('CN0001', 'Case',               'case', 'Case', 'SEALED'),
    ('CN0003', 'Sealed box',         'box',  'Box',  'SEALED'),
    ('CN0004', 'Damaged sealed box', 'box',  'Box',  'DAMAGED'),
    ('CN0005', 'No shrink box',      'box',  'Box',  'NO_SHRINK'),
    ('CN0006', 'Opened box',         'box',  'Box',  'OPENED'),
    ('CN0009', 'Opened case',        'case', 'Case', 'OPENED'),
    ('CN0007', 'Unsearched pack',    'pack', 'Pack', 'UNSEARCHED'),
    ('CN0010', 'Searched pack',      'pack', 'Pack', 'SEARCHED')
) AS t(code, canonical, grp, unit_canonical, def_code)
      JOIN public.condition_definitions cd ON cd.code = t.def_code
     WHERE lc.code = t.code AND lc.canonical = t.canonical AND lc.value_group = t.grp
       AND lc.condition_def_id = cd.id AND lc.tenant_id IS NULL
    RETURNING lc.code
)
SELECT CASE WHEN count(*) = 8 AND count(DISTINCT code) = 8 THEN 'REVERTED labels|8' ELSE (1 / (count(*) - count(*)))::text END FROM upd;
WITH del AS (
    DELETE FROM public.unit_condition_links l
     USING (VALUES ('CASE', 'SEALED'), ('BOX', 'SEARCHED')) AS v(qcode, dcode), public.quantity_units qu, public.condition_definitions cd
     WHERE qu.code = v.qcode AND cd.code = v.dcode
       AND l.quantity_unit_id = qu.id AND l.condition_def_id = cd.id
    RETURNING l.id
)
SELECT CASE WHEN count(*) = 2 THEN 'DELETED links|2' ELSE (1 / (count(*) - count(*)))::text END FROM del;
SELECT CASE WHEN count(*) = 11 THEN 'CHECK_OK links 11' ELSE (1 / (count(*) - count(*)))::text END FROM public.unit_condition_links;
SELECT CASE WHEN count(*) = 2 THEN 'CHECK_OK keep 2' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions
 WHERE (code = 'CN0002' AND condition_def_id = 3) OR (code = 'CN20261008072213' AND condition_def_id = 8);
SELECT CASE WHEN count(*) = 0 THEN 'CHECK_OK labels_null 8' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions WHERE code IN ('CN0001','CN0003','CN0004','CN0005','CN0006','CN0009','CN0007','CN0010') AND condition_def_id IS NOT NULL;
COMMIT;
SELECT 'ROLLBACK_DONE';
