-- postcheck.sql (READ ONLY)
-- Target: DB jarvis_db. Schemas: tenant_001, tenant_003, tenant_004, tenant_005, tenant_006.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL lock_timeout = '10s';
SET LOCAL statement_timeout = '60s';
DO $do$
DECLARE
  specs jsonb := $j$[{"schema":"tenant_001","tid":1,"id":2536,"role":"マネージャー","key":"manager","stored":1},{"schema":"tenant_003","tid":3,"id":2536,"role":"マネージャー","key":"manager","stored":1},{"schema":"tenant_004","tid":4,"id":2514,"role":"マネージャー","key":"manager","stored":1},{"schema":"tenant_005","tid":5,"id":2514,"role":"マネージャー","key":"manager","stored":1},{"schema":"tenant_006","tid":6,"id":3,"role":"マネージャー","key":"manager","stored":1},{"schema":"tenant_001","tid":1,"id":2611,"role":"点検用（見るだけ）","key":"inspector","stored":1},{"schema":"tenant_004","tid":4,"id":2589,"role":"スモーク専用","key":"smoke","stored":0}]$j$::jsonb;
  spec jsonb; sch text; n int; total int := 0;
BEGIN
  FOR spec IN SELECT * FROM jsonb_array_elements(specs) LOOP
    sch := spec->>'schema';
    EXECUTE format('SELECT count(*) FROM %I.roles WHERE id = $1 AND name = $2 AND system_key = $3', sch)
      INTO n USING (spec->>'id')::int, spec->>'role', spec->>'key';
    IF n <> 1 THEN RAISE EXCEPTION '% role id % system_key % count = % (expected 1)', sch, spec->>'id', spec->>'key', n; END IF;
    EXECUTE format($q$SELECT count(*) FROM %I.role_permissions rp JOIN public.permissions p ON p.id = rp.permission_id
                      WHERE rp.role_id = $1 AND p.key IN ('roles.view','roles.create','roles.update','roles.delete','roles.assign')$q$, sch)
      INTO n USING (spec->>'id')::int;
    IF n <> 0 THEN RAISE EXCEPTION '% role id % still has % stored roles.* rows', sch, spec->>'id', n; END IF;
  END LOOP;
  -- 会社ごとの system_key の件数 = オーナー・システム管理者の2 + この SQL で足した数
  FOR sch IN SELECT DISTINCT value->>'schema' FROM jsonb_array_elements(specs) LOOP
    EXECUTE format('SELECT count(*) FROM %I.roles WHERE system_key IS NOT NULL', sch) INTO n;
    IF n <> 2 + (SELECT count(*) FROM jsonb_array_elements(specs) s WHERE s->>'schema' = sch) THEN
      RAISE EXCEPTION '% has % roles with system_key (unexpected)', sch, n;
    END IF;
    total := total + n;
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = sch AND indexname = 'uq_roles_system_key') THEN
      RAISE EXCEPTION '% is missing index uq_roles_system_key', sch;
    END IF;
  END LOOP;
  IF total <> 17 THEN RAISE EXCEPTION 'total system_key rows % (expected 17 = 10 owner/admin + 7)', total; END IF;
  RAISE NOTICE 'postcheck OK: % roles with system_key', total;
END
$do$;
SELECT id, table_name, changed_by, changed_at, length(new_values) AS new_len
  FROM public.audit_log WHERE table_name = 'roles' AND new_values LIKE '%role-edit-hierarchy-20261109%' ORDER BY id;
ROLLBACK;
