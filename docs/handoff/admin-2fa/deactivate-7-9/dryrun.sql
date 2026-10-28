-- dryrun.sql (deactivate.sql と同じ処理。最後が ROLLBACK。何も残らない)
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL app.is_operator = 'true';
SET LOCAL lock_timeout = '10s';
SET LOCAL statement_timeout = '30s';
DO $do$
DECLARE c int;
BEGIN
  SELECT count(*) INTO c FROM public.users
   WHERE id IN (7,9) AND is_active = true AND is_super_admin = false;
  IF c != 2 THEN RAISE EXCEPTION 'GUARD(before): expected 2 rows, got %', c; END IF;
  UPDATE public.users SET is_active = false, updated_at = now()
   WHERE id IN (7,9) AND is_active = true AND is_super_admin = false;
  GET DIAGNOSTICS c = ROW_COUNT;
  IF c != 2 THEN RAISE EXCEPTION 'GUARD(update): expected 2 rows updated, got %', c; END IF;
  RAISE NOTICE 'OK: 2 rows set is_active=false';
END
$do$;
SELECT id, tenant_id, is_active, updated_at FROM public.users WHERE id IN (7,9) ORDER BY id;
ROLLBACK;
