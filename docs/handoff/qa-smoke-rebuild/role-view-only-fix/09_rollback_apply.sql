-- 戻しの本実行。外した 25 個を役割 2611 に付け直す。ガードが通ったときだけ COMMIT。
-- 試すときは最後の 3 行を ROLLBACK; に替えた写しを流す（PO の使い捨て許可が要る）。
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL app.is_operator = 'true';
SELECT set_config('app.tenant_id', '1', true);
DO $guard$
DECLARE
    want_ids integer[] := ARRAY[9,11,10,18,20,19,16,13,15,14,53623,53619,53622,53621,53620,22,24,23,32,117,118,26,28,29,27];
    n integer;
BEGIN
    SELECT count(*) INTO n FROM tenant_001.role_permissions WHERE role_id = 2611;
    IF n <> 27 THEN RAISE EXCEPTION 'before must be 27 but was %', n; END IF;
    INSERT INTO tenant_001.role_permissions (role_id, permission_id)
    SELECT 2611, x FROM unnest(want_ids) AS x
    ON CONFLICT (role_id, permission_id) DO NOTHING;
    GET DIAGNOSTICS n = ROW_COUNT;
    IF n <> 25 THEN RAISE EXCEPTION 'inserted must be 25 but was %', n; END IF;
    SELECT count(*) INTO n FROM tenant_001.role_permissions WHERE role_id = 2611;
    IF n <> 52 THEN RAISE EXCEPTION 'after must be 52 but was %', n; END IF;
END
$guard$;
SELECT 'COMMIT_NEXT';
COMMIT;
SELECT 'COMMIT_DONE';
