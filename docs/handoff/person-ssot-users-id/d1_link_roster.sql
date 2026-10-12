-- D1: 名簿（tenant.staff）をログイン用の表（public.users）へ紐付ける（ADR-1008 段階 D1）
-- PO 決定 2026-10-12: (1) t6 商談8件は users 10 (2) 名簿の人は全員 users 行を持つ・ログインしない人は is_active=false (3) t4 staff 7 を名簿から外す
-- 1トランザクション・件数ガード付き。DRY-RUN は末尾 COMMIT を ROLLBACK に置き換えて流す。
BEGIN;

DO $$
DECLARE n integer;
BEGIN
  -- 事前状態の確認（想定外なら中止）
  SELECT count(*) INTO n FROM tenant_001.staff WHERE id = 1 AND user_id IS NULL;
  IF n <> 1 THEN RAISE EXCEPTION 'pre t1 staff1 unlinked expected 1 got %', n; END IF;
  SELECT count(*) INTO n FROM tenant_004.staff WHERE id = 1 AND user_id IS NULL;
  IF n <> 1 THEN RAISE EXCEPTION 'pre t4 staff1 unlinked expected 1 got %', n; END IF;
  SELECT count(*) INTO n FROM tenant_006.staff WHERE id IN (8, 9, 10) AND user_id IS NULL;
  IF n <> 3 THEN RAISE EXCEPTION 'pre t6 staff8-10 unlinked expected 3 got %', n; END IF;
  SELECT count(*) INTO n FROM public.users u JOIN tenant_006.staff s ON lower(u.email) = lower(s.primary_email) WHERE s.id IN (8, 9, 10);
  IF n <> 0 THEN RAISE EXCEPTION 'pre t6 staff8-10 email already in users: %', n; END IF;
  SELECT count(*) INTO n FROM tenant_004.tenant_meta_config WHERE id IN (2, 3) AND connected_by_staff_id = 7;
  IF n <> 2 THEN RAISE EXCEPTION 'pre t4 meta_config by staff7 expected 2 got %', n; END IF;

  -- 1. メール一致の2行を紐付け（t1 staff1→users1、t4 staff1→users3）
  UPDATE tenant_001.staff SET user_id = 1, updated_at = now() WHERE id = 1 AND user_id IS NULL;
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 1 THEN RAISE EXCEPTION 'link t1 expected 1 got %', n; END IF;
  UPDATE tenant_004.staff SET user_id = 3, updated_at = now() WHERE id = 1 AND user_id IS NULL;
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 1 THEN RAISE EXCEPTION 'link t4 expected 1 got %', n; END IF;

  -- 2. t6 のログインしない3人（staff 8,9,10）に「ログイン不可」の users 行を作る
  INSERT INTO public.users (tenant_id, username, email, full_name, role, is_active)
  SELECT 6, s.surname_jp || ' ' || s.given_name_jp, s.primary_email, s.surname_jp || ' ' || s.given_name_jp, 'user', false
  FROM tenant_006.staff s WHERE s.id IN (8, 9, 10) AND s.user_id IS NULL;
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 3 THEN RAISE EXCEPTION 'insert users expected 3 got %', n; END IF;
  UPDATE tenant_006.staff s SET user_id = u.id, updated_at = now()
  FROM public.users u WHERE u.tenant_id = 6 AND lower(u.email) = lower(s.primary_email) AND s.id IN (8, 9, 10) AND s.user_id IS NULL;
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 3 THEN RAISE EXCEPTION 'link t6 expected 3 got %', n; END IF;

  -- 3. 3人のロールを権限の正本 user_roles に写す（名簿の role_id と同じ値）
  INSERT INTO tenant_006.user_roles (user_id, role_id)
  SELECT s.user_id, s.role_id FROM tenant_006.staff s WHERE s.id IN (8, 9, 10);
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 3 THEN RAISE EXCEPTION 'user_roles expected 3 got %', n; END IF;

  -- 4. t4 staff 7（review@ と同じメール・users 10 は t6 所属）を名簿から外す
  UPDATE tenant_004.tenant_meta_config SET connected_by_staff_id = NULL WHERE id IN (2, 3) AND connected_by_staff_id = 7;
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 2 THEN RAISE EXCEPTION 'meta_config expected 2 got %', n; END IF;
  DELETE FROM tenant_004.staff WHERE id = 7;
  GET DIAGNOSTICS n = ROW_COUNT; IF n <> 1 THEN RAISE EXCEPTION 'remove staff7 expected 1 got %', n; END IF;

  -- 事後確認: 全テナントで user_id の無い名簿行が 0
  SELECT (SELECT count(*) FROM tenant_001.staff WHERE user_id IS NULL)
       + (SELECT count(*) FROM tenant_003.staff WHERE user_id IS NULL)
       + (SELECT count(*) FROM tenant_004.staff WHERE user_id IS NULL)
       + (SELECT count(*) FROM tenant_005.staff WHERE user_id IS NULL)
       + (SELECT count(*) FROM tenant_006.staff WHERE user_id IS NULL) INTO n;
  IF n <> 0 THEN RAISE EXCEPTION 'post unlinked staff expected 0 got %', n; END IF;
  RAISE NOTICE 'D1 ok';
END $$;

COMMIT;
