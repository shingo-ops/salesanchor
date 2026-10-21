-- 価格で単位を決める 便2 札と組の一覧の precheck（読み取り）。ADR-1036 設計 B2・ADR-1007。
-- 全部 PRECHECK_OK なら commit に進める。1つでも違えば止まる（1/0 で失敗）。違ったときは、直前の DIFF| 行が違った行の code・名前を出す。
-- 各 SELECT は 1 文で自己完結（reader 鍵の道は 1 回 1 文。public. を ai_ro.public__ に読み替えれば流せる。README 参照）。
\set ON_ERROR_STOP on

-- 0. 基準: 状態マスタ全行の今の値（commit 後に verify の ROW 行と突き合わせる）
SELECT 'ROW|' || id || '|' || code || '|' || canonical || '|' || coalesce(value_group, 'NULL') || '|' || coalesce(unit_id::text, 'NULL') || '|' || coalesce(condition_def_id::text, 'NULL') || '|' || is_active || '|' || coalesce(tenant_id::text, 'NULL')
  FROM public.line_conditions ORDER BY id;

-- 1. 種類の一覧 condition_definitions: id と code が 2=SEALED・3=DAMAGED・4=NO_SHRINK・5=OPENED・7=UNSEARCHED・8=SEARCHED（有効）
SELECT 'DIFF defs|' || e.id || '|' || e.code || '|actual=' || coalesce(cd.code, 'NONE') || '|active=' || coalesce(cd.is_active::text, 'NONE')
  FROM (VALUES (2, 'SEALED'), (3, 'DAMAGED'), (4, 'NO_SHRINK'), (5, 'OPENED'), (7, 'UNSEARCHED'), (8, 'SEARCHED')) AS e(id, code) LEFT JOIN public.condition_definitions cd ON cd.id = e.id AND cd.code = e.code AND cd.is_active
 WHERE cd.id IS NULL;
SELECT CASE WHEN count(*) = 6 THEN 'PRECHECK_OK defs 6' ELSE (1 / (count(*) - count(*)))::text END
  FROM (VALUES (2, 'SEALED'), (3, 'DAMAGED'), (4, 'NO_SHRINK'), (5, 'OPENED'), (7, 'UNSEARCHED'), (8, 'SEARCHED')) AS e(id, code) JOIN public.condition_definitions cd ON cd.id = e.id AND cd.code = e.code AND cd.is_active;

-- 2. 単位の一覧 quantity_units: code が CASE・BOX で 1 行ずつ（今は id 1・2。id は commit では直書きしない）
SELECT 'DIFF qunits|' || v.code || '|rows=' || (SELECT count(*) FROM public.quantity_units q WHERE q.code = v.code)
  FROM (VALUES ('CASE'), ('BOX')) AS v(code)
 WHERE (SELECT count(*) FROM public.quantity_units q WHERE q.code = v.code) <> 1;
SELECT CASE WHEN count(*) = 2 THEN 'PRECHECK_OK quantity_units CASE,BOX 1x2' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.quantity_units WHERE code IN ('CASE', 'BOX');

-- 3. 札を入れる 8 行: code・canonical・群・単位(line_units の canonical)・有効・tenant_id なし・condition_def_id が NULL
SELECT 'DIFF targets|' || t.code || '|' || t.canonical || '|' || t.grp || '|' || t.unit_canonical
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
 WHERE NOT EXISTS (
     SELECT 1 FROM public.line_conditions lc JOIN public.line_units lu ON lu.id = lc.unit_id
      WHERE lc.code = t.code AND lc.canonical = t.canonical AND lc.value_group = t.grp
        AND lu.canonical = t.unit_canonical AND lc.is_active AND lc.tenant_id IS NULL AND lc.condition_def_id IS NULL);
SELECT CASE WHEN count(*) = 8 THEN 'PRECHECK_OK targets 8' ELSE (1 / (count(*) - count(*)))::text END
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
  JOIN public.line_conditions lc ON lc.code = t.code AND lc.canonical = t.canonical AND lc.value_group = t.grp
   AND lc.is_active AND lc.tenant_id IS NULL AND lc.condition_def_id IS NULL
  JOIN public.line_units lu ON lu.id = lc.unit_id AND lu.canonical = t.unit_canonical;

-- 4. 8 行の code は状態マスタに 1 行ずつ（重複なし）
SELECT 'DIFF dupcode|' || code || '|rows=' || count(*)
  FROM public.line_conditions WHERE code IN ('CN0001','CN0003','CN0004','CN0005','CN0006','CN0009','CN0007','CN0010')
 GROUP BY code HAVING count(*) <> 1;
SELECT CASE WHEN count(*) = 8 THEN 'PRECHECK_OK codes 8x1' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions WHERE code IN ('CN0001','CN0003','CN0004','CN0005','CN0006','CN0009','CN0007','CN0010');

-- 5. 触らない 2 行: CN0002=3(DAMAGED)・CN20261008072213=8(SEARCHED) が今のまま
SELECT 'DIFF keep|' || e.code || '|expected_def=' || e.def_id || '|actual=' || coalesce(lc.condition_def_id::text, 'NULL')
  FROM (VALUES ('CN0002', 3), ('CN20261008072213', 8)) AS e(code, def_id)
  LEFT JOIN public.line_conditions lc ON lc.code = e.code AND lc.condition_def_id = e.def_id AND lc.is_active AND lc.tenant_id IS NULL
 WHERE lc.id IS NULL;
SELECT CASE WHEN count(*) = 2 THEN 'PRECHECK_OK keep 2' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions
 WHERE (code = 'CN0002' AND condition_def_id = 3) OR (code = 'CN20261008072213' AND condition_def_id = 8);

-- 6. CN0013（AR confirmed pack）の札は空のまま（札を入れない）
SELECT 'DIFF cn0013|' || code || '|' || canonical || '|def=' || condition_def_id
  FROM public.line_conditions WHERE code = 'CN0013' AND condition_def_id IS NOT NULL;
SELECT CASE WHEN count(*) = 1 THEN 'PRECHECK_OK cn0013 null' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions WHERE code = 'CN0013' AND condition_def_id IS NULL;

-- 7. box／case／pack の群で札が入っているのは今の 2 行だけ・テナント別の行は 0
SELECT 'DIFF labeled|' || code || '|' || canonical || '|' || value_group || '|def=' || condition_def_id
  FROM public.line_conditions WHERE value_group IN ('box','case','pack') AND condition_def_id IS NOT NULL AND code NOT IN ('CN0002','CN20261008072213');
SELECT CASE WHEN count(*) = 2 THEN 'PRECHECK_OK labeled_in_groups 2' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions WHERE value_group IN ('box','case','pack') AND condition_def_id IS NOT NULL;
SELECT 'DIFF tenant|' || code || '|' || canonical || '|tenant=' || tenant_id
  FROM public.line_conditions WHERE value_group IN ('box','case','pack') AND tenant_id IS NOT NULL;
SELECT CASE WHEN count(*) = 0 THEN 'PRECHECK_OK tenant_rows 0' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions WHERE value_group IN ('box','case','pack') AND tenant_id IS NOT NULL;

-- 8. 種類と単位の組の一覧 unit_condition_links: 11 行・CASE×SEALED と BOX×SEARCHED はまだ無い
SELECT 'DIFF links_exist|' || qu.code || '|' || cd.code
  FROM public.unit_condition_links l
  JOIN public.quantity_units qu ON qu.id = l.quantity_unit_id
  JOIN public.condition_definitions cd ON cd.id = l.condition_def_id
 WHERE (qu.code, cd.code) IN (('CASE', 'SEALED'), ('BOX', 'SEARCHED'));
SELECT CASE WHEN count(*) = 0 THEN 'PRECHECK_OK links_new_absent' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.unit_condition_links l
  JOIN public.quantity_units qu ON qu.id = l.quantity_unit_id
  JOIN public.condition_definitions cd ON cd.id = l.condition_def_id
 WHERE (qu.code, cd.code) IN (('CASE', 'SEALED'), ('BOX', 'SEARCHED'));
SELECT 'DIFF links_total|rows=' || count(*) FROM public.unit_condition_links HAVING count(*) <> 11;
SELECT CASE WHEN count(*) = 11 THEN 'PRECHECK_OK links 11' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.unit_condition_links;
SELECT 'PRECHECK_DONE';
