-- D2 の戻し（ADR-1008）。D2 実行後にだけ使う。新たな PO 合意なしに実行しない。
-- 対象は D2 実行前に sales_rep_id=1 だった 42 件（2026-10-13 読み取り）の id だけ。
BEGIN;
DO $$
DECLARE n integer;
BEGIN
  UPDATE tenant_004.companies SET sales_rep_id = 1
  WHERE sales_rep_id = 3 AND id IN (2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,34,35,36,37,38,39,40,41,42,44,45,46);
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 42 THEN RAISE EXCEPTION 'rollback expected 42 got %', n; END IF;
  RAISE NOTICE 'D2 rollback ok';
END $$;
COMMIT;
