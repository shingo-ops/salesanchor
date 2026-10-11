-- 状態「Error」(CN0012) 追加の戻し: 使うのは戻すときだけ。CN0012 の1行だけを削除する。
-- 戻す前に: コードを戻して再解析し、analysis_results.condition_id が CN0012 の id を指す行を無くすこと（参照が残っていると失敗する）。
-- 削除件数が1でなければ失敗。
\set ON_ERROR_STOP on
BEGIN;
WITH d AS (
    DELETE FROM public.conditions WHERE code = 'CN0012' AND canonical = 'Error'
    RETURNING id
)
SELECT CASE WHEN count(*) = 1 THEN 'ROLLED_BACK|1' ELSE (1 / (count(*) - count(*)))::text END FROM d;
SELECT CASE WHEN count(*) = 13 THEN 'CHECK_OK 13' ELSE (1 / (count(*) - count(*)))::text END FROM public.conditions;
COMMIT;
SELECT 'ROLLBACK_DONE';
