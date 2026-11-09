-- rollback.sql (WRITES; needs a NEW PO decision before running)
-- Target: DB jarvis_db. Schemas: tenant_001, tenant_003, tenant_004, tenant_005, tenant_006.
-- apply.sql が audit_log に残した行（system_key_step = role-edit-hierarchy-20261109）から、
-- 入れた system_key を空に戻し、消した roles.* の保存行を戻す。
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL lock_timeout = '10s';
SET LOCAL statement_timeout = '60s';
DO $do$
DECLARE
  a record; r jsonb; k text; c int; undone int := 0; restored int := 0; sch text;
BEGIN
  FOR a IN SELECT id, new_values FROM public.audit_log
            WHERE table_name = 'roles' AND new_values LIKE '{%' AND (new_values::jsonb->>'system_key_step') = 'role-edit-hierarchy-20261109'
              AND NOT EXISTS (SELECT 1 FROM public.audit_log rb WHERE rb.table_name = 'roles' AND rb.new_values LIKE '{%'
                              AND (rb.new_values::jsonb->>'rolled_back_audit_id')::bigint = audit_log.id)
            ORDER BY id LOOP
    sch := a.new_values::jsonb->>'schema';
    FOR r IN SELECT * FROM jsonb_array_elements(a.new_values::jsonb->'roles') LOOP
      EXECUTE format('UPDATE %I.roles SET system_key = NULL, updated_at = NOW() WHERE id = $1 AND system_key = $2', sch)
        USING (r->>'id')::int, r->>'new';
      GET DIAGNOSTICS c = ROW_COUNT;
      IF c <> 1 THEN RAISE EXCEPTION 'rollback of % role id % rows=% (expected 1)', sch, r->>'id', c; END IF;
      undone := undone + 1;
      FOR k IN SELECT jsonb_array_elements_text(r->'removed_keys') LOOP
        EXECUTE format('INSERT INTO %I.role_permissions (role_id, permission_id) SELECT $1, id FROM public.permissions WHERE key = $2', sch)
          USING (r->>'id')::int, k;
        GET DIAGNOSTICS c = ROW_COUNT;
        IF c <> 1 THEN RAISE EXCEPTION 'restore of % role id % key % rows=% (expected 1)', sch, r->>'id', k, c; END IF;
        restored := restored + 1;
      END LOOP;
    END LOOP;
    INSERT INTO public.audit_log (table_name, record_id, action, changed_by, old_values, new_values)
    VALUES ('roles', gen_random_uuid(), 'UPDATE', 'claude-opus (rollback; PO decision required)', a.new_values,
            jsonb_build_object('rolled_back_audit_id', a.id, 'system_key_step', 'role-edit-hierarchy-20261109-rollback')::text);
  END LOOP;
  IF undone <> 7 THEN RAISE EXCEPTION 'rolled back % roles (expected 7)', undone; END IF;
  IF restored <> 4 THEN RAISE EXCEPTION 'restored % stored rows (expected 4)', restored; END IF;
  RAISE NOTICE 'ROLLED BACK: % roles, % stored rows restored', undone, restored;
END
$do$;
COMMIT;
