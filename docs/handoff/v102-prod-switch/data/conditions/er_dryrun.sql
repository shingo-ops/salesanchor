-- 状態「Error」(CN0012) 追加 dryrun: 追加して検査して必ず ROLLBACK。
\set ON_ERROR_STOP on
BEGIN;
WITH i AS (
    INSERT INTO public.conditions (id, code, canonical, app_kubun, is_active, priority, search_kw, exclude_kw, match_type, effect, note)
    VALUES (26, 'CN0012', 'Error', '', true, 99, '', '', 'KEYWORD', 'EXCLUDE', '状態を決められなかった（v102 の最終フォールバック）。配信しない。人が正しい状態を選ぶ（PO 2026-10-11）')
    RETURNING id
)
SELECT CASE WHEN count(*) = 1 THEN 'INSERTED|1' ELSE (1 / (count(*) - count(*)))::text END FROM i;
SELECT 'AFTER|' || id || '|' || code || '|' || canonical || '|' || priority || '|' || effect || '|' || match_type FROM public.conditions WHERE code = 'CN0012';
SELECT CASE WHEN count(*) = 14 THEN 'CHECK_OK 14' ELSE (1 / (count(*) - count(*)))::text END FROM public.conditions;
SELECT CASE WHEN count(*) = 1 THEN 'CHECK_OK 1' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.conditions
 WHERE id = 26 AND code = 'CN0012' AND canonical = 'Error' AND app_kubun = '' AND is_active IS TRUE AND priority = 99
   AND search_kw = '' AND exclude_kw = '' AND match_type = 'KEYWORD' AND effect = 'EXCLUDE';
ROLLBACK;
SELECT 'DRYRUN_OK';
