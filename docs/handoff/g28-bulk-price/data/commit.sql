-- 状態「Bulk」(CN0014) 追加 commit: dry_run 成功の印がある時だけ実行する。id は identity に任せる。本番での実行は Opus（担当は実行しない）。
-- 追加件数が1でなければ失敗（COMMIT に進まない）。追加後の行数が16でなければ失敗。事前に CN0014/Bulk が無いことも BEGIN 内で確かめる。
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
COMMIT;
SELECT 'COMMIT_DONE';
