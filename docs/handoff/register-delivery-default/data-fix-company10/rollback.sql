-- rollback.sql (WRITES; 1 transaction; COMMIT) — 未実行。apply.sql を戻すときだけ使う
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL search_path = tenant_001, public;
SET LOCAL app.tenant_id = '1';
DO $do$
DECLARE c int;
BEGIN
  UPDATE tenant_001.company_addresses SET is_default = false, updated_at = now()
   WHERE id = 10 AND company_id = 10 AND address_type = 'delivery' AND is_default = true;
  GET DIAGNOSTICS c = ROW_COUNT;
  IF c != 1 THEN RAISE EXCEPTION 'GUARD: expected 1 row, got %', c; END IF;
END
$do$;
COMMIT;
