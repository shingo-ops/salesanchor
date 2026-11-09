-- dryrun.sql (same as apply.sql; ends in ROLLBACK so nothing is kept)
-- Target: DB jarvis_db. Schemas: tenant_001, tenant_003, tenant_004, tenant_005, tenant_006.
-- 7 roles get system_key (manager x5, inspector x1, smoke x1) and 4 stored roles.view rows are removed.
-- 順番: このデータ SQL を先に入れ、そのあとでコードを反映する（design §5）。
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL lock_timeout = '10s';
SET LOCAL statement_timeout = '60s';
DO $do$
DECLARE
  specs jsonb := $j$[{"schema":"tenant_001","tid":1,"id":2536,"role":"マネージャー","key":"manager","stored":1},{"schema":"tenant_003","tid":3,"id":2536,"role":"マネージャー","key":"manager","stored":1},{"schema":"tenant_004","tid":4,"id":2514,"role":"マネージャー","key":"manager","stored":1},{"schema":"tenant_005","tid":5,"id":2514,"role":"マネージャー","key":"manager","stored":0},{"schema":"tenant_006","tid":6,"id":3,"role":"マネージャー","key":"manager","stored":0},{"schema":"tenant_001","tid":1,"id":2611,"role":"点検用（見るだけ）","key":"inspector","stored":1},{"schema":"tenant_004","tid":4,"id":2589,"role":"スモーク専用","key":"smoke","stored":0}]$j$::jsonb;
  spec jsonb; sch text; n int; c int; ids jsonb; dkeys jsonb; touched int := 0; removed int := 0;
BEGIN
  -- precheck.sql と同じ照合（実行時に読み直して、1つでも違えば全体を止める）
  FOR spec IN SELECT * FROM jsonb_array_elements(specs) LOOP
    sch := spec->>'schema';
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = sch AND table_name = 'roles' AND column_name = 'system_key') THEN
      RAISE EXCEPTION '% has no roles.system_key column', sch;
    END IF;
    EXECUTE format('SELECT count(*) FROM %I.roles WHERE id = $1 AND name = $2 AND tenant_id = $3 AND system_key IS NULL', sch)
      INTO n USING (spec->>'id')::int, spec->>'role', (spec->>'tid')::int;
    IF n <> 1 THEN RAISE EXCEPTION '% role id % name % is not (one row, system_key NULL, tenant_id %)', sch, spec->>'id', spec->>'role', spec->>'tid'; END IF;
    EXECUTE format('SELECT count(*) FROM %I.roles WHERE name = $1', sch) INTO n USING spec->>'role';
    IF n <> 1 THEN RAISE EXCEPTION '% role % name count = % (expected 1)', sch, spec->>'role', n; END IF;
    EXECUTE format('SELECT count(*) FROM %I.roles WHERE system_key = $1', sch) INTO n USING spec->>'key';
    IF n <> 0 THEN RAISE EXCEPTION '% already has system_key % on % roles', sch, spec->>'key', n; END IF;
    EXECUTE format($q$SELECT count(*) FROM %I.role_permissions rp JOIN public.permissions p ON p.id = rp.permission_id
                      WHERE rp.role_id = $1 AND p.key IN ('roles.view','roles.create','roles.update','roles.delete','roles.assign')$q$, sch)
      INTO n USING (spec->>'id')::int;
    IF n <> (spec->>'stored')::int THEN RAISE EXCEPTION '% role id % stored roles.* rows = % (expected %)', sch, spec->>'id', n, spec->>'stored'; END IF;
    EXECUTE format($q$SELECT count(*) FROM %I.role_permissions rp JOIN public.permissions p ON p.id = rp.permission_id
                      WHERE rp.role_id = $1 AND p.key IN ('roles.create','roles.update','roles.delete','roles.assign')$q$, sch)
      INTO n USING (spec->>'id')::int;
    IF n <> 0 THEN RAISE EXCEPTION '% role id % has % stored roles.* rows other than roles.view', sch, spec->>'id', n; END IF;
  END LOOP;
  FOR sch IN SELECT DISTINCT value->>'schema' FROM jsonb_array_elements(specs) LOOP
    EXECUTE format('SELECT count(*) FROM %I.roles WHERE system_key IS NOT NULL', sch) INTO n;
    IF n <> 2 THEN RAISE EXCEPTION '% has % roles with system_key (expected 2: owner and admin)', sch, n; END IF;
  END LOOP;

  -- 書き込み: 会社ごとに system_key を入れ、保存済みの roles.* の行を消し、audit_log に1行
  FOR sch IN SELECT DISTINCT value->>'schema' FROM jsonb_array_elements(specs) LOOP
    ids := '[]'::jsonb;
    FOR spec IN SELECT * FROM jsonb_array_elements(specs) WHERE value->>'schema' = sch LOOP
      EXECUTE format('UPDATE %I.roles SET system_key = $1, updated_at = NOW() WHERE id = $2 AND name = $3 AND system_key IS NULL', sch)
        USING spec->>'key', (spec->>'id')::int, spec->>'role';
      GET DIAGNOSTICS c = ROW_COUNT;
      IF c <> 1 THEN RAISE EXCEPTION '% update of role id % rows=% (expected 1)', sch, spec->>'id', c; END IF;
      touched := touched + 1;

      EXECUTE format($q$WITH d AS (
                          DELETE FROM %I.role_permissions rp USING public.permissions p
                          WHERE rp.role_id = $1 AND p.id = rp.permission_id
                            AND p.key IN ('roles.view','roles.create','roles.update','roles.delete','roles.assign')
                          RETURNING p.key)
                        SELECT COALESCE(jsonb_agg(key), '[]'::jsonb) FROM d$q$, sch)
        INTO dkeys USING (spec->>'id')::int;
      IF jsonb_array_length(dkeys) <> (spec->>'stored')::int THEN
        RAISE EXCEPTION '% role id % removed % stored rows (expected %)', sch, spec->>'id', jsonb_array_length(dkeys), spec->>'stored';
      END IF;
      removed := removed + jsonb_array_length(dkeys);
      ids := ids || jsonb_build_array(jsonb_build_object('id', (spec->>'id')::int, 'role', spec->>'role', 'old', NULL, 'new', spec->>'key', 'removed_keys', dkeys));
    END LOOP;
    INSERT INTO public.audit_log (table_name, record_id, action, changed_by, old_values, new_values)
    VALUES ('roles', gen_random_uuid(), 'UPDATE', 'claude-opus (PO GO 後・role-edit-hierarchy)',
            jsonb_build_object('schema', sch, 'system_key', 'NULL for all changed rows')::text,
            jsonb_build_object('system_key_step', 'role-edit-hierarchy-20261109', 'schema', sch, 'roles', ids)::text);
    GET DIAGNOSTICS c = ROW_COUNT;
    IF c <> 1 THEN RAISE EXCEPTION 'audit_log insert for % rows=% (expected 1)', sch, c; END IF;
  END LOOP;
  IF touched <> 7 THEN RAISE EXCEPTION 'touched % roles (expected 7)', touched; END IF;
  IF removed <> 4 THEN RAISE EXCEPTION 'removed % stored rows (expected 4)', removed; END IF;
  RAISE NOTICE 'DONE: % roles updated, % stored roles.* rows removed', touched, removed;
END
$do$;
ROLLBACK;
