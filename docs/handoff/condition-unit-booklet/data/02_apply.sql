-- ADR-1035 便1 適用。本番での実行は Opus（担当は実行しない）。
-- 使い方（終わり方を必ず指定する）:
--   DRY-RUN : psql -v end=ROLLBACK -f 02_apply.sql   （件数を確かめて最後に ROLLBACK。何も残らない）
--   本番    : psql -v end=COMMIT   -f 02_apply.sql   （DRY-RUN が OK だった後だけ）
-- 6 行の unit_id を直す（Pack 5・Case 1）。WHERE は id と unit_id IS NULL の両方。変わった行数が 6 でなければ 1/0 で失敗し、COMMIT に進まない。
\set ON_ERROR_STOP on
\if :{?end}
\else
  \echo 'end を指定してください: -v end=ROLLBACK または -v end=COMMIT'
  SELECT 1 / 0;
\endif
BEGIN;

-- 1. Pack（line_units id 11）: Unsearched pack 22・Searched pack 21・AR confirmed pack 44・未開封 60・開封済み 61
WITH u AS (
    UPDATE public.line_conditions SET unit_id = 11, updated_at = NOW()
     WHERE id IN (22, 21, 44, 60, 61) AND unit_id IS NULL
       AND EXISTS (SELECT 1 FROM public.line_units WHERE id = 11 AND canonical = 'Pack')
    RETURNING id
)
SELECT CASE WHEN count(*) = 5 THEN 'UPDATED pack|5' ELSE (1 / (count(*) - count(*)))::text END FROM u;

-- 2. Case（line_units id 9）: Opened case 20
WITH u AS (
    UPDATE public.line_conditions SET unit_id = 9, updated_at = NOW()
     WHERE id = 20 AND unit_id IS NULL
       AND EXISTS (SELECT 1 FROM public.line_units WHERE id = 9 AND canonical = 'Case')
    RETURNING id
)
SELECT CASE WHEN count(*) = 1 THEN 'UPDATED case|1' ELSE (1 / (count(*) - count(*)))::text END FROM u;

-- 3. 適用後の確認（合計 6 でなければ失敗）
SELECT CASE WHEN count(*) = 6 THEN 'CHECK_OK changed 6' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions
 WHERE (id IN (22, 21, 44, 60, 61) AND unit_id = 11) OR (id = 20 AND unit_id = 9);
SELECT CASE WHEN count(*) = 24 THEN 'CHECK_OK conditions 24' ELSE (1 / (count(*) - count(*)))::text END FROM public.line_conditions;

:end;
SELECT 'APPLY_END';
