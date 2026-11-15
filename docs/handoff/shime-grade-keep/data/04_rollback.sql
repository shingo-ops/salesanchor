-- 便1 戻し。本番での実行は Opus。id 13 の search_kw の末尾の ,切れ込み だけを外す。変わった行数が1でなければ失敗する。
\set ON_ERROR_STOP on
BEGIN;
WITH u AS (
    UPDATE public.line_conditions SET search_kw = left(search_kw, length(search_kw) - length(',切れ込み')), updated_at = NOW()
     WHERE id = 13 AND search_kw LIKE '%,切れ込み'
    RETURNING id
)
SELECT CASE WHEN count(*) = 1 THEN 'ROLLBACK|1' ELSE (1 / (count(*) - count(*)))::text END FROM u;
COMMIT;
SELECT 'ROLLBACK_DONE';
