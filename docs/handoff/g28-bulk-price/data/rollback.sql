-- 状態「Bulk」(CN0014) 追加の戻し: 行は消さず is_active=false にする（analysis_results.condition_id が参照しているため DELETE しない）。本番での実行は Opus。
-- 順番（必ずこの通り）:
--   1. コードの PR を revert してデプロイする（R6:バルク既定 の分岐を外す）。
--   2. Bulk で保存された行を先に reanalyze する（対象 job を reanalyze_v102_job（backend/app/tasks/tcg_extraction.py:706）でやり直す）。
--      確認: 下の ROWS_STILL_BULK が 0 になること。0 になる前にこの SQL を実行しない。
--   3. この SQL で is_active=false にする（load_condition_entries が is_active の行だけ読むため、Bulk は返らなくなる）。
\set ON_ERROR_STOP on
BEGIN;
SELECT CASE WHEN count(*) = 0 THEN 'ROWS_STILL_BULK|0' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.analysis_results ar JOIN public.line_conditions c ON c.id = ar.condition_id
 WHERE c.code = 'CN0014' AND ar.is_current IS TRUE;
WITH u AS (
    UPDATE public.line_conditions SET is_active = false, updated_at = now() WHERE code = 'CN0014' AND canonical = 'Bulk' AND is_active IS TRUE
    RETURNING id
)
SELECT CASE WHEN count(*) = 1 THEN 'ROLLED_BACK|1' ELSE (1 / (count(*) - count(*)))::text END FROM u;
SELECT CASE WHEN count(*) = 16 THEN 'CHECK_OK 16' ELSE (1 / (count(*) - count(*)))::text END FROM public.line_conditions;
COMMIT;
SELECT 'ROLLBACK_DONE';
