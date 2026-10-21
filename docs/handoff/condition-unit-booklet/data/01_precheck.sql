-- ADR-1035 便1 事前確認（読むだけ）。本番への実行は Opus（担当は実行しない）。
-- 期待: 全部 PRECHECK_OK。1つでも違えば止まる（1/0 で失敗させる）。
\set ON_ERROR_STOP on
-- 1. 状態 24 行の今の値（適用後に 03_verify の ROW 行と突き合わせる基準）
SELECT 'ROW|' || id || '|' || canonical || '|' || coalesce(unit_id::text, 'NULL') || '|' || priority || '|' || coalesce(value_group, 'NULL') || '|' || is_active
  FROM public.line_conditions ORDER BY id;
SELECT CASE WHEN count(*) = 24 THEN 'PRECHECK_OK conditions 24' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions;
-- 2. 直す 6 行の unit_id がすべて NULL（id 22・21・44・60・61・20）
SELECT CASE WHEN count(*) = 6 THEN 'PRECHECK_OK six_rows_unit_null 6' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions WHERE id IN (22, 21, 44, 60, 61, 20) AND unit_id IS NULL;
-- 3. 単位の辞書: line_units の id 11 が Pack、id 9 が Case
SELECT CASE WHEN count(*) = 2 THEN 'PRECHECK_OK units 11=Pack 9=Case' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_units WHERE (id = 11 AND canonical = 'Pack') OR (id = 9 AND canonical = 'Case');
-- 4. 状態の名前が設計の表どおり（id と名前の取り違え防止）
SELECT CASE WHEN count(*) = 6 THEN 'PRECHECK_OK names 6' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions
 WHERE (id, canonical) IN ((22,'Unsearched pack'), (21,'Searched pack'), (44,'AR confirmed pack'), (60,'未開封'), (61,'開封済み'), (20,'Opened case'));
-- 5. 確認用: Searched pack(21) と AR confirmed pack(44) の priority
SELECT 'PRIORITY|' || id || '|' || canonical || '|' || priority FROM public.line_conditions WHERE id IN (21, 44) ORDER BY id;
