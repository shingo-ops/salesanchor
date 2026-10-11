-- 状態「Error」(CN0012) 追加 commit: dryrun 成功の印がある時だけ実行する。id は identity に任せる。
-- 追加件数が1でなければ失敗（COMMIT に進まない）。追加後の行数が14でなければ失敗。
\set ON_ERROR_STOP on
BEGIN;
WITH i AS (
    INSERT INTO public.conditions (code, canonical, app_kubun, is_active, priority, search_kw, exclude_kw, match_type, effect, note)
    VALUES ('CN0012', 'Error', '', true, 99, '', '', 'KEYWORD', 'EXCLUDE', '状態を決められなかった（v102 の最終フォールバック）。配信しない。人が正しい状態を選ぶ（PO 2026-10-11）')
    RETURNING id
)
SELECT CASE WHEN count(*) = 1 THEN 'INSERTED|1' ELSE (1 / (count(*) - count(*)))::text END FROM i;
SELECT CASE WHEN count(*) = 14 THEN 'CHECK_OK 14' ELSE (1 / (count(*) - count(*)))::text END FROM public.conditions;
SELECT CASE WHEN count(*) = 1 THEN 'CHECK_OK 1' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.conditions
 WHERE code = 'CN0012' AND canonical = 'Error' AND app_kubun = '' AND is_active IS TRUE AND priority = 99
   AND search_kw = '' AND exclude_kw = '' AND match_type = 'KEYWORD' AND effect = 'EXCLUDE';
COMMIT;
SELECT 'COMMIT_DONE';
