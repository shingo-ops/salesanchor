-- 要確認タブ名の設定 dryrun: 更新して検査し必ず ROLLBACK。
\set ON_ERROR_STOP on
BEGIN;
WITH upd AS (
    UPDATE public.tcg_distribution_targets SET review_sheet_name = '要確認'
     WHERE name = '配信テスト' AND spreadsheet_id = '1unwFM3MZikSmQjZ744uxhvzG2ENhuhcDsvse1dfSrm4' AND review_sheet_name IS NULL
    RETURNING id
)
SELECT CASE WHEN count(*) = 1 THEN 'UPDATED|1' ELSE (1 / (count(*) - count(*)))::text END FROM upd;
SELECT CASE WHEN count(*) = 1 THEN 'CHECK_OK 1' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.tcg_distribution_targets WHERE name = '配信テスト' AND spreadsheet_id = '1unwFM3MZikSmQjZ744uxhvzG2ENhuhcDsvse1dfSrm4' AND review_sheet_name = '要確認';
SELECT CASE WHEN count(*) = 1 THEN 'SET_ROWS_OK 1' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.tcg_distribution_targets WHERE review_sheet_name IS NOT NULL;
ROLLBACK;
SELECT 'DRYRUN_OK';
