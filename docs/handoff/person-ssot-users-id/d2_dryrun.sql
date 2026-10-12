-- D2: t4 の会社の担当者（companies.sales_rep_id）を staff の番号から users の番号へ付け替える（ADR-1008 段階 D2）
-- 前提: P1 #4174 本番反映済み（外部キーは public.users(id)）。staff 1（谷澤 伸吾）= users 3（D1 と同じメール一致）。
-- 1トランザクション・件数ガード付き。DRY-RUN は末尾 COMMIT を ROLLBACK に置き換えて流す。
BEGIN;
DO $$
DECLARE n integer;
BEGIN
  SELECT count(*) INTO n FROM tenant_004.companies WHERE sales_rep_id = 1;
  IF n <> 42 THEN RAISE EXCEPTION 'pre sales_rep_id=1 expected 42 got %', n; END IF;
  SELECT count(*) INTO n FROM tenant_004.companies WHERE sales_rep_id IS NOT NULL AND sales_rep_id <> 1;
  IF n <> 0 THEN RAISE EXCEPTION 'pre other sales_rep values expected 0 got %', n; END IF;
  SELECT count(*) INTO n FROM public.users WHERE id = 3 AND tenant_id = 4;
  IF n <> 1 THEN RAISE EXCEPTION 'pre users 3 in tenant 4 expected 1 got %', n; END IF;

  UPDATE tenant_004.companies SET sales_rep_id = 3 WHERE sales_rep_id = 1;
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 42 THEN RAISE EXCEPTION 'update expected 42 got %', n; END IF;

  SELECT count(*) INTO n FROM tenant_004.companies WHERE sales_rep_id = 3;
  IF n <> 42 THEN RAISE EXCEPTION 'post sales_rep_id=3 expected 42 got %', n; END IF;
  RAISE NOTICE 'D2 ok';
END $$;
ROLLBACK;
