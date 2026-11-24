-- apply.sql (WRITES; 1 transaction; COMMIT)
-- 対象: tenant_001.company_addresses id=10（試験の会社 id=10・lead 946・配送先）。is_default を false から true にするだけ。
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL search_path = tenant_001, public;
SET LOCAL app.tenant_id = '1';
SET LOCAL lock_timeout = '10s';
SET LOCAL statement_timeout = '30s';
DO $do$
DECLARE c int;
BEGIN
  SELECT count(*) INTO c FROM tenant_001.company_addresses
   WHERE company_id = 10 AND address_type = 'delivery' AND is_default = true;
  IF c != 0 THEN RAISE EXCEPTION 'GUARD(before): company 10 already has % default delivery', c; END IF;
  UPDATE tenant_001.company_addresses SET is_default = true, updated_at = now()
   WHERE id = 10 AND company_id = 10 AND address_type = 'delivery' AND is_default = false;
  GET DIAGNOSTICS c = ROW_COUNT;
  IF c != 1 THEN RAISE EXCEPTION 'GUARD(update): expected 1 row, got %', c; END IF;
  RAISE NOTICE 'OK: 1 row set is_default=true';
END
$do$;
SELECT id, company_id, address_type, is_default, updated_at FROM tenant_001.company_addresses WHERE company_id = 10 ORDER BY id;
COMMIT;
