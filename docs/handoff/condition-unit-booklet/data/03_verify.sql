-- ADR-1035 便1 確認（読むだけ）。適用後に流す。K1 を判定する。全部 VERIFY_OK なら期待どおり。
-- ROW 行は 01_precheck.sql の ROW 行と同じ書式。実行者が前後で 18 行の一致を手で突き合わせる（README 手順 4）。
\set ON_ERROR_STOP on
SELECT 'ROW|' || id || '|' || canonical || '|' || coalesce(unit_id::text, 'NULL') || '|' || priority || '|' || coalesce(value_group, 'NULL') || '|' || is_active
  FROM public.line_conditions ORDER BY id;
-- K1-1: 上の 6 行が新しい値（Pack 5・Case 1）
SELECT CASE WHEN count(*) = 5 THEN 'VERIFY_OK pack 5' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions WHERE id IN (22, 21, 44, 60, 61) AND unit_id = 11;
SELECT CASE WHEN count(*) = 1 THEN 'VERIFY_OK case 1' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions WHERE id = 20 AND unit_id = 9;
-- K1-2: 行数 24、ほかの 18 行は触っていない（更新時刻が 6 行より前）。値の一致は 01 の ROW 行と手で突き合わせる（README 手順 4）
SELECT CASE WHEN count(*) = 24 THEN 'VERIFY_OK conditions 24' ELSE (1 / (count(*) - count(*)))::text END FROM public.line_conditions;
SELECT CASE WHEN count(*) = 18 THEN 'VERIFY_OK others_untouched 18' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions
 WHERE id NOT IN (22, 21, 44, 60, 61, 20)
   AND updated_at < (SELECT min(updated_at) FROM public.line_conditions WHERE id IN (22, 21, 44, 60, 61, 20));
-- PSA10（62）は空のまま
SELECT CASE WHEN count(*) = 1 THEN 'VERIFY_OK psa10_62_null 1' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions WHERE id = 62 AND unit_id IS NULL;
