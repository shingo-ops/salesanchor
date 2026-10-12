-- 要確認タブ名の設定の戻し: 使うのは戻すときだけ（NULL に戻すと要確認タブには書かれない）。
\set ON_ERROR_STOP on
BEGIN;
UPDATE public.tcg_distribution_targets SET review_sheet_name = NULL
 WHERE name = '配信テスト' AND spreadsheet_id = '1unwFM3MZikSmQjZ744uxhvzG2ENhuhcDsvse1dfSrm4' RETURNING name;
COMMIT;
SELECT 'ROLLBACK_DONE';
