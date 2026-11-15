-- 便1 適用。本番での実行は Opus（担当は実行しない）。
-- 使い方（終わり方を必ず指定する）:
--   DRY-RUN : psql -v end=ROLLBACK -f 02_apply.sql
--   本番    : psql -v end=COMMIT   -f 02_apply.sql   （DRY-RUN が OK だった後だけ）
-- id 13（CN0002 Damaged case）の search_kw の末尾に ,切れ込み を足す。変わった行数が1でなければ 1/0 で失敗し、COMMIT に進まない。
\set ON_ERROR_STOP on
\if :{?end}
\else
  \echo 'end を指定してください: -v end=ROLLBACK または -v end=COMMIT'
  SELECT 1 / 0;
\endif
BEGIN;
WITH u AS (
    UPDATE public.line_conditions SET search_kw = search_kw || ',切れ込み', updated_at = NOW()
     WHERE id = 13 AND code = 'CN0002' AND canonical = 'Damaged case'
       AND search_kw NOT LIKE '%切れ込み%'
       AND NOT EXISTS (SELECT 1 FROM public.line_conditions WHERE search_kw LIKE '%切れ込み%' OR coalesce(exclude_kw,'') LIKE '%切れ込み%')
    RETURNING id
)
SELECT CASE WHEN count(*) = 1 THEN 'UPDATED|1' ELSE (1 / (count(*) - count(*)))::text END FROM u;
SELECT CASE WHEN count(*) = 1 THEN 'CHECK_OK|1' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions WHERE search_kw LIKE '%切れ込み%' AND id = 13;
:end;
SELECT 'APPLY_END';
