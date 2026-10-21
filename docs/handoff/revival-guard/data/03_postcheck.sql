-- 03_postcheck.sql (READ-ONLY)
-- 修正後の確認。K3: 一覧の行の現行数 = 0。監査行がちょうど 1 件。
\set ON_ERROR_STOP on
BEGIN READ ONLY;
DO $do$
DECLARE n int;
BEGIN
  SELECT count(*) INTO n FROM public.analysis_results
   WHERE id IN ('349eaef0-1958-4a82-80eb-74d9c6fe5212','f61f1ea7-40d4-454e-ac52-3e3e6e8fcffe') AND is_current;
  IF n <> 0 THEN RAISE EXCEPTION 'K3 NG: 一覧の行で現行のまま % 件', n; END IF;
  SELECT count(*) INTO n FROM public.audit_log WHERE table_name = 'analysis_results' AND new_values LIKE '%revival-guard-20261019%';
  IF n <> 1 THEN RAISE EXCEPTION '監査行 % 件 (期待 1)', n; END IF;
  RAISE NOTICE 'POSTCHECK OK: 現行 0 件, 監査行 1 件';
END
$do$;
SELECT id, is_current, updated_at FROM public.analysis_results
 WHERE id IN ('349eaef0-1958-4a82-80eb-74d9c6fe5212','f61f1ea7-40d4-454e-ac52-3e3e6e8fcffe') ORDER BY id;
ROLLBACK;
