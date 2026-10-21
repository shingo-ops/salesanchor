-- 価格で単位を決める 便2 札と組の一覧 commit: precheck が全部 PRECHECK_OK・dryrun 成功の後だけ。コードより先に流す（設計「反映の順」）。ADR-1007・ADR-1036。
-- 1 つの取引。id は直書きしない（札は condition_definitions.code、組の一覧は quantity_units.code と condition_definitions.code から引く）。
-- 各 UPDATE／INSERT は件数が合わなければゼロ除算で失敗し、COMMIT に進まない（ON_ERROR_STOP で取引は COMMIT されない）。
\set ON_ERROR_STOP on
BEGIN;
WITH upd AS (
    UPDATE public.line_conditions lc
       SET condition_def_id = cd.id, updated_at = NOW()
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
       AND lc.condition_def_id IS NULL AND lc.tenant_id IS NULL
    RETURNING lc.code
)
SELECT CASE WHEN count(*) = 8 AND count(DISTINCT code) = 8 THEN 'UPDATED labels|8' ELSE (1 / (count(*) - count(*)))::text END FROM upd;
SELECT CASE WHEN count(*) = 8 THEN 'CHECK_OK labels 8' ELSE (1 / (count(*) - count(*)))::text END
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
  JOIN public.line_conditions lc ON lc.code = t.code AND lc.canonical = t.canonical AND lc.value_group = t.grp
   AND lc.tenant_id IS NULL AND lc.condition_def_id = cd.id;
WITH ins AS (
    INSERT INTO public.unit_condition_links (quantity_unit_id, condition_def_id)
    SELECT qu.id, cd.id
      FROM (VALUES ('CASE', 'SEALED'), ('BOX', 'SEARCHED')) AS v(qcode, dcode)
      JOIN public.quantity_units qu ON qu.code = v.qcode
      JOIN public.condition_definitions cd ON cd.code = v.dcode
    RETURNING id
)
SELECT CASE WHEN count(*) = 2 THEN 'INSERTED links|2' ELSE (1 / (count(*) - count(*)))::text END FROM ins;
SELECT CASE WHEN count(*) = 13 THEN 'CHECK_OK links 13' ELSE (1 / (count(*) - count(*)))::text END FROM public.unit_condition_links;
SELECT CASE WHEN count(*) = 2 THEN 'CHECK_OK keep 2' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions
 WHERE (code = 'CN0002' AND condition_def_id = 3) OR (code = 'CN20261008072213' AND condition_def_id = 8);
COMMIT;
SELECT 'COMMIT_DONE';
