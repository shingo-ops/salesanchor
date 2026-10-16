-- 状態「Bulk」(CN0014) 追加 dry_run: 追加して検査して必ず ROLLBACK。id は identity に任せる。本番での実行は Opus（担当は実行しない）。
-- 前例: docs/handoff/v102-prod-switch/data/conditions/er_dryrun.sql。表名は改名後の public.line_conditions（migrations/20260922_080000_rename_line_analysis_tables.sql:72）。
-- 前提（読み取りで確認済み・2026-10-16）: 行数15、code=CN0014 は0行、canonical=Bulk は0行。
\set ON_ERROR_STOP on
BEGIN;
SELECT CASE WHEN count(*) = 0 THEN 'PRECHECK_OK 0' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions WHERE code = 'CN0014' OR canonical = 'Bulk';
WITH i AS (
    INSERT INTO public.line_conditions (code, canonical, app_kubun, is_active, priority, search_kw, exclude_kw, match_type, effect, unit_id, note)
    VALUES ('CN0014', 'Bulk', '', true, 10, '', '', 'KEYWORD', 'OUTPUT', NULL,
            'バルク系の商品で状態語が無いときの状態。配信する。search_kw は空（どの文にも当たらない。コードの R6:バルク既定 だけが返す）（ADR-1021・PO 2026-10-16 y）')
    RETURNING id
)
SELECT CASE WHEN count(*) = 1 THEN 'INSERTED|1' ELSE (1 / (count(*) - count(*)))::text END FROM i;
SELECT 'AFTER|' || id || '|' || code || '|' || canonical || '|' || priority || '|' || effect || '|' || match_type FROM public.line_conditions WHERE code = 'CN0014';
SELECT CASE WHEN count(*) = 16 THEN 'CHECK_OK 16' ELSE (1 / (count(*) - count(*)))::text END FROM public.line_conditions;
SELECT CASE WHEN count(*) = 1 THEN 'CHECK_OK 1' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.line_conditions
 WHERE code = 'CN0014' AND canonical = 'Bulk' AND app_kubun = '' AND is_active IS TRUE AND priority = 10
   AND search_kw = '' AND exclude_kw = '' AND match_type = 'KEYWORD' AND effect = 'OUTPUT' AND unit_id IS NULL;
ROLLBACK;
SELECT 'DRYRUN_OK';
