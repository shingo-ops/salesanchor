-- 価格で単位を決める 便2 札と組の一覧の verify（読み取り）。ADR-1036 設計 B2・ADR-1007。commit の後に流す。
-- 全部 VERIFY_OK なら成功。1つでも違えば止まる（1/0）。違ったときは、直前の DIFF| 行が 群・種類・code・canonical を出す。
-- 各 SELECT は 1 文で自己完結（reader 鍵の道は 1 回 1 文。public. を ai_ro.public__ に読み替えれば流せる）。
\set ON_ERROR_STOP on

-- 0. 状態マスタ全行（precheck の ROW 行と突き合わせ、札を入れた 8 行だけが変わったことを確かめる）
SELECT 'ROW|' || id || '|' || code || '|' || canonical || '|' || coalesce(value_group, 'NULL') || '|' || coalesce(unit_id::text, 'NULL') || '|' || coalesce(condition_def_id::text, 'NULL') || '|' || is_active || '|' || coalesce(tenant_id::text, 'NULL')
  FROM public.line_conditions ORDER BY id;

-- 1. B の表 15 組（期待値は下の VALUES。検査側の期待値で、判定のコードには持たない）と、B2 の読み方で組み立てた結果が全組一致
--    読み方: 群(Box→box・Case→case・Pack→pack)の有効・tenant なしの行から、札の種類（SEALED・UNSEARCHED は DEFAULT）が同じ行がちょうど 1 行ならその code、0 行なら NULL(決めない)、2 行以上は DUP
SELECT 'DIFF pair|kind=' || kind || '|unit=' || unit || '|expected=' || coalesce(exp_code, 'NULL(決めない)') || '|actual=' || coalesce(act_code, 'NULL(決めない)')
  FROM (SELECT x.kind, x.unit, x.exp_code,
       CASE WHEN count(r.code) = 0 THEN NULL WHEN count(r.code) = 1 THEN min(r.code) ELSE 'DUP' END AS act_code
  FROM (SELECT e.kind, e.unit, e.exp_code, g.grp
          FROM (VALUES
    ('DEFAULT',   'Box',  'CN0003'),
    ('DEFAULT',   'Case', 'CN0001'),
    ('DEFAULT',   'Pack', 'CN0007'),
    ('DAMAGED',   'Box',  'CN0004'),
    ('DAMAGED',   'Case', 'CN0002'),
    ('DAMAGED',   'Pack', NULL),
    ('OPENED',    'Box',  'CN0006'),
    ('OPENED',    'Case', 'CN0009'),
    ('OPENED',    'Pack', NULL),
    ('SEARCHED',  'Box',  'CN20261008072213'),
    ('SEARCHED',  'Case', NULL),
    ('SEARCHED',  'Pack', 'CN0010'),
    ('NO_SHRINK', 'Box',  'CN0005'),
    ('NO_SHRINK', 'Case', NULL),
    ('NO_SHRINK', 'Pack', NULL)
) AS e(kind, unit, exp_code)
          JOIN (VALUES ('Box', 'box'), ('Case', 'case'), ('Pack', 'pack')) AS g(unit, grp) ON g.unit = e.unit) x
  LEFT JOIN (SELECT lc.code, lc.value_group, CASE WHEN cd.code IN ('SEALED', 'UNSEARCHED') THEN 'DEFAULT' ELSE cd.code END AS kind
               FROM public.line_conditions lc
               JOIN public.condition_definitions cd ON cd.id = lc.condition_def_id
              WHERE lc.is_active AND lc.tenant_id IS NULL AND lc.value_group IN ('box', 'case', 'pack')) r
    ON r.value_group = x.grp AND r.kind = x.kind
 GROUP BY x.kind, x.unit, x.exp_code) z
 WHERE exp_code IS DISTINCT FROM act_code ORDER BY kind, unit;
SELECT CASE WHEN count(*) = 15 AND count(*) FILTER (WHERE exp_code IS NOT DISTINCT FROM act_code) = 15 THEN 'VERIFY_OK pairs 15/15' ELSE (1 / (count(*) - count(*)))::text END
  FROM (SELECT x.kind, x.unit, x.exp_code,
       CASE WHEN count(r.code) = 0 THEN NULL WHEN count(r.code) = 1 THEN min(r.code) ELSE 'DUP' END AS act_code
  FROM (SELECT e.kind, e.unit, e.exp_code, g.grp
          FROM (VALUES
    ('DEFAULT',   'Box',  'CN0003'),
    ('DEFAULT',   'Case', 'CN0001'),
    ('DEFAULT',   'Pack', 'CN0007'),
    ('DAMAGED',   'Box',  'CN0004'),
    ('DAMAGED',   'Case', 'CN0002'),
    ('DAMAGED',   'Pack', NULL),
    ('OPENED',    'Box',  'CN0006'),
    ('OPENED',    'Case', 'CN0009'),
    ('OPENED',    'Pack', NULL),
    ('SEARCHED',  'Box',  'CN20261008072213'),
    ('SEARCHED',  'Case', NULL),
    ('SEARCHED',  'Pack', 'CN0010'),
    ('NO_SHRINK', 'Box',  'CN0005'),
    ('NO_SHRINK', 'Case', NULL),
    ('NO_SHRINK', 'Pack', NULL)
) AS e(kind, unit, exp_code)
          JOIN (VALUES ('Box', 'box'), ('Case', 'case'), ('Pack', 'pack')) AS g(unit, grp) ON g.unit = e.unit) x
  LEFT JOIN (SELECT lc.code, lc.value_group, CASE WHEN cd.code IN ('SEALED', 'UNSEARCHED') THEN 'DEFAULT' ELSE cd.code END AS kind
               FROM public.line_conditions lc
               JOIN public.condition_definitions cd ON cd.id = lc.condition_def_id
              WHERE lc.is_active AND lc.tenant_id IS NULL AND lc.value_group IN ('box', 'case', 'pack')) r
    ON r.value_group = x.grp AND r.kind = x.kind
 GROUP BY x.kind, x.unit, x.exp_code) z;

-- 2. 各群の unit_id が 1 種類で、期待の単位（box→Box・case→Case・pack→Pack）
SELECT 'DIFF unit_id|group=' || g.grp || '|unit_ids=' || coalesce((SELECT string_agg(DISTINCT coalesce(lc.unit_id::text, 'NULL'), ',') FROM public.line_conditions lc WHERE lc.value_group = g.grp AND lc.is_active AND lc.tenant_id IS NULL), 'none')
  FROM (VALUES ('box', 'Box'), ('case', 'Case'), ('pack', 'Pack')) AS g(grp, unit_canonical)
 WHERE (SELECT count(DISTINCT coalesce(lc.unit_id, -1)) FROM public.line_conditions lc WHERE lc.value_group = g.grp AND lc.is_active AND lc.tenant_id IS NULL) <> 1
    OR EXISTS (SELECT 1 FROM public.line_conditions lc LEFT JOIN public.line_units lu ON lu.id = lc.unit_id
                WHERE lc.value_group = g.grp AND lc.is_active AND lc.tenant_id IS NULL AND lu.canonical IS DISTINCT FROM g.unit_canonical);
SELECT CASE WHEN count(*) = 3 THEN 'VERIFY_OK group_unit 3' ELSE (1 / (count(*) - count(*)))::text END
  FROM (VALUES ('box', 'Box'), ('case', 'Case'), ('pack', 'Pack')) AS g(grp, unit_canonical)
 WHERE (SELECT count(DISTINCT coalesce(lc.unit_id, -1)) FROM public.line_conditions lc WHERE lc.value_group = g.grp AND lc.is_active AND lc.tenant_id IS NULL) = 1
   AND NOT EXISTS (SELECT 1 FROM public.line_conditions lc LEFT JOIN public.line_units lu ON lu.id = lc.unit_id
                    WHERE lc.value_group = g.grp AND lc.is_active AND lc.tenant_id IS NULL AND lu.canonical IS DISTINCT FROM g.unit_canonical);

-- 3. 同じ群で同じ種類（SEALED・UNSEARCHED は DEFAULT で 1 つ）の行が 2 行以上ある組が 0
SELECT 'DIFF dup|group=' || lc.value_group || '|kind=' || CASE WHEN cd.code IN ('SEALED', 'UNSEARCHED') THEN 'DEFAULT' ELSE cd.code END || '|n=' || count(*) || '|' || string_agg(lc.code || ':' || lc.canonical, ',' ORDER BY lc.code)
  FROM public.line_conditions lc JOIN public.condition_definitions cd ON cd.id = lc.condition_def_id
 WHERE lc.is_active AND lc.tenant_id IS NULL AND lc.value_group IN ('box', 'case', 'pack')
 GROUP BY lc.value_group, CASE WHEN cd.code IN ('SEALED', 'UNSEARCHED') THEN 'DEFAULT' ELSE cd.code END HAVING count(*) >= 2;
SELECT CASE WHEN count(*) = 0 THEN 'VERIFY_OK dup_groups 0' ELSE (1 / (count(*) - count(*)))::text END
  FROM (SELECT 1 FROM public.line_conditions lc JOIN public.condition_definitions cd ON cd.id = lc.condition_def_id
         WHERE lc.is_active AND lc.tenant_id IS NULL AND lc.value_group IN ('box', 'case', 'pack')
         GROUP BY lc.value_group, CASE WHEN cd.code IN ('SEALED', 'UNSEARCHED') THEN 'DEFAULT' ELSE cd.code END HAVING count(*) >= 2) d;

-- 4. CN0013（AR confirmed pack）の札は空のまま
SELECT 'DIFF cn0013|' || code || '|' || canonical || '|def=' || condition_def_id
  FROM public.line_conditions WHERE code = 'CN0013' AND condition_def_id IS NOT NULL;
SELECT CASE WHEN count(*) = 1 THEN 'VERIFY_OK cn0013 null' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions WHERE code = 'CN0013' AND condition_def_id IS NULL;

-- 5. 種類と単位の組の一覧が 13 行で、CASE×SEALED と BOX×SEARCHED がある
SELECT 'DIFF links_new|' || v.qcode || '|' || v.dcode
  FROM (VALUES ('CASE', 'SEALED'), ('BOX', 'SEARCHED')) AS v(qcode, dcode)
 WHERE NOT EXISTS (SELECT 1 FROM public.unit_condition_links l
                     JOIN public.quantity_units qu ON qu.id = l.quantity_unit_id AND qu.code = v.qcode
                     JOIN public.condition_definitions cd ON cd.id = l.condition_def_id AND cd.code = v.dcode);
SELECT CASE WHEN count(*) = 2 THEN 'VERIFY_OK links_new 2' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.unit_condition_links l
  JOIN public.quantity_units qu ON qu.id = l.quantity_unit_id
  JOIN public.condition_definitions cd ON cd.id = l.condition_def_id
 WHERE (qu.code, cd.code) IN (('CASE', 'SEALED'), ('BOX', 'SEARCHED'));
SELECT 'DIFF links_total|rows=' || count(*) FROM public.unit_condition_links HAVING count(*) <> 13;
SELECT CASE WHEN count(*) = 13 THEN 'VERIFY_OK links 13' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.unit_condition_links;
SELECT 'VERIFY_DONE';
