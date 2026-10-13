-- D1 の戻し（ADR-1008）。D1 実行後にだけ使う。新たな PO 合意なしに実行しない。
-- staff 7 の行は、D1 の前に設計者の手元に控えた row_to_json の1行（~/CC報告ファイル-keep/user-ssot/d1/t4_staff7_backup.txt。
-- メールアドレス等を含むためリポジトリには置かない）から戻す。先に次の1文を、控えの JSON を埋めて流す:
--   INSERT INTO tenant_004.staff SELECT * FROM json_populate_record(NULL::tenant_004.staff, '<控えの JSON>');
--   （このあと下の SQL を流す）
BEGIN;
DO $$
DECLARE n integer;
BEGIN
  SELECT count(*) INTO n FROM tenant_004.staff WHERE id = 7;
  IF n <> 1 THEN RAISE EXCEPTION 'restore staff7 first (found %)', n; END IF;

  UPDATE tenant_004.tenant_meta_config SET connected_by_staff_id = 7 WHERE id IN (2, 3) AND connected_by_staff_id IS NULL;
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 2 THEN RAISE EXCEPTION 'meta_config expected 2 got %', n; END IF;

  DELETE FROM tenant_006.user_roles ur USING tenant_006.staff s WHERE s.id IN (8, 9, 10) AND ur.user_id = s.user_id;
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 3 THEN RAISE EXCEPTION 'user_roles expected 3 got %', n; END IF;

  CREATE TEMP TABLE d1_new_users ON COMMIT DROP AS SELECT user_id FROM tenant_006.staff WHERE id IN (8, 9, 10);
  UPDATE tenant_006.staff SET user_id = NULL WHERE id IN (8, 9, 10);
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 3 THEN RAISE EXCEPTION 'unlink t6 expected 3 got %', n; END IF;
  DELETE FROM public.users WHERE id IN (SELECT user_id FROM d1_new_users) AND tenant_id = 6 AND is_active = false;
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 3 THEN RAISE EXCEPTION 'delete users expected 3 got %', n; END IF;

  UPDATE tenant_001.staff SET user_id = NULL WHERE id = 1 AND user_id = 1;
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 1 THEN RAISE EXCEPTION 'unlink t1 expected 1 got %', n; END IF;
  UPDATE tenant_004.staff SET user_id = NULL WHERE id = 1 AND user_id = 3;
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 1 THEN RAISE EXCEPTION 'unlink t4 expected 1 got %', n; END IF;
  RAISE NOTICE 'D1 rollback ok';
END $$;
COMMIT;
