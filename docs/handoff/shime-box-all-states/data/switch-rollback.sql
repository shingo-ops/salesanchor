-- ADR-1073 便4 設定 v102_shime_box_all_states の戻し: 行を 1 行消す（design.md §5・§6。行が無ければ規則12h は働かない）。件数が1でなければゼロ除算で失敗し、COMMIT に進まない。
-- 注意: それまでに規則12h が書いた 2 つ目以降の相手（analysis_soldout_extra_targets の行）は消えない。消えた在庫が戻るかは未確認（PO 2026-11-11「1」で承知のうえで切り替え）。
\set ON_ERROR_STOP on
BEGIN;
WITH del AS (
    DELETE FROM public.tcg_distribution_settings WHERE key = 'v102_shime_box_all_states' RETURNING key
)
SELECT CASE WHEN count(*) = 1 THEN 'DELETED|1' ELSE (1 / (count(*) - count(*)))::text END FROM del;
COMMIT;
SELECT 'ROLLBACK_DONE';
