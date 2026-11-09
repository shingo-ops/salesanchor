-- precheck.sql (READ ONLY; raises on any mismatch)
-- Target: DB jarvis_db. Schemas: tenant_001, tenant_003, tenant_004, tenant_005, tenant_006.
-- 前例: docs/handoff/roles-system-key-data/（形を写した。手で書いた一度きりの SQL）
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL lock_timeout = '10s';
SET LOCAL statement_timeout = '60s';
DO $do$
DECLARE
  specs jsonb := $j$[{"schema":"tenant_001","tid":1,"id":2536,"role":"マネージャー","key":"manager","stored":1},{"schema":"tenant_003","tid":3,"id":2536,"role":"マネージャー","key":"manager","stored":1},{"schema":"tenant_004","tid":4,"id":2514,"role":"マネージャー","key":"manager","stored":1},{"schema":"tenant_005","tid":5,"id":2514,"role":"マネージャー","key":"manager","stored":1},{"schema":"tenant_006","tid":6,"id":3,"role":"マネージャー","key":"manager","stored":1},{"schema":"tenant_001","tid":1,"id":2611,"role":"点検用（見るだけ）","key":"inspector","stored":1},{"schema":"tenant_004","tid":4,"id":2589,"role":"スモーク専用","key":"smoke","stored":0}]$j$::jsonb;
  spec jsonb; sch text; n int;
BEGIN
  FOR spec IN SELECT * FROM jsonb_array_elements(specs) LOOP
    sch := spec->>'schema';
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = sch AND table_name = 'roles' AND column_name = 'system_key') THEN
      RAISE EXCEPTION '% has no roles.system_key column', sch;
    END IF;
    -- 名前と id の両方で1件だけ当たり、system_key がまだ空
    EXECUTE format('SELECT count(*) FROM %I.roles WHERE id = $1 AND name = $2 AND tenant_id = $3 AND system_key IS NULL', sch)
      INTO n USING (spec->>'id')::int, spec->>'role', (spec->>'tid')::int;
    IF n <> 1 THEN RAISE EXCEPTION '% role id % name % is not (one row, system_key NULL, tenant_id %)', sch, spec->>'id', spec->>'role', spec->>'tid'; END IF;
    EXECUTE format('SELECT count(*) FROM %I.roles WHERE name = $1', sch) INTO n USING spec->>'role';
    IF n <> 1 THEN RAISE EXCEPTION '% role % name count = % (expected 1)', sch, spec->>'role', n; END IF;
    -- 同じ system_key が既に別のロールに入っていない（テナント内一意の索引で SQL ごと失敗するのを先に見つける）
    EXECUTE format('SELECT count(*) FROM %I.roles WHERE system_key = $1', sch) INTO n USING spec->>'key';
    IF n <> 0 THEN RAISE EXCEPTION '% already has system_key % on % roles', sch, spec->>'key', n; END IF;
    -- 保存済みの roles.* の行: 件数が想定どおりで、roles.view だけ
    EXECUTE format($q$SELECT count(*) FROM %I.role_permissions rp JOIN public.permissions p ON p.id = rp.permission_id
                      WHERE rp.role_id = $1 AND p.key IN ('roles.view','roles.create','roles.update','roles.delete','roles.assign')$q$, sch)
      INTO n USING (spec->>'id')::int;
    IF n <> (spec->>'stored')::int THEN RAISE EXCEPTION '% role id % stored roles.* rows = % (expected %)', sch, spec->>'id', n, spec->>'stored'; END IF;
    EXECUTE format($q$SELECT count(*) FROM %I.role_permissions rp JOIN public.permissions p ON p.id = rp.permission_id
                      WHERE rp.role_id = $1 AND p.key IN ('roles.create','roles.update','roles.delete','roles.assign')$q$, sch)
      INTO n USING (spec->>'id')::int;
    IF n <> 0 THEN RAISE EXCEPTION '% role id % has % stored roles.* rows other than roles.view', sch, spec->>'id', n; END IF;
  END LOOP;
  -- 各会社とも、既に system_key を持つのはオーナーとシステム管理者の2件だけ
  FOR sch IN SELECT DISTINCT value->>'schema' FROM jsonb_array_elements(specs) LOOP
    EXECUTE format('SELECT count(*) FROM %I.roles WHERE system_key IS NOT NULL', sch) INTO n;
    IF n <> 2 THEN RAISE EXCEPTION '% has % roles with system_key (expected 2: owner and admin)', sch, n; END IF;
    EXECUTE format('SELECT count(*) FROM %I.roles', sch) INTO n;
    RAISE NOTICE '% roles total = %', sch, n;
  END LOOP;
  RAISE NOTICE 'precheck OK: % spec rows', jsonb_array_length(specs);
END
$do$;
ROLLBACK;
