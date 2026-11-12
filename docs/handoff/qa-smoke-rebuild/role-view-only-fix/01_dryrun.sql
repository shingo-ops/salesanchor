-- 点検用の役割から書き込みの 25 個を外す DRY-RUN。01_apply.sql と同じ中身。最後に必ず ROLLBACK。
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL app.is_operator = 'true';
SELECT set_config('app.tenant_id', '1', true);

-- テナント 001 の役割 2611「点検用（見るだけ）」から、書き込み・出力・承認の 25 個を外す。
-- id と鍵の名前の両方で照合し、1 つでも違えば RAISE EXCEPTION（ON_ERROR_STOP で止まる）。
DO $guard$
DECLARE
    want_remove text[] := ARRAY[
        'customers.create','customers.delete','customers.update',
        'deals.create','deals.delete','deals.update',
        'leads.convert','leads.create','leads.delete','leads.update',
        'leads.discord_ban','leads.discord_invite','leads.discord_kick','leads.discord_remove_channel','leads.discord_resync',
        'orders.create','orders.delete','orders.update',
        'reports.export','staff_reports.create','staff_reports.review',
        'teams.create','teams.delete','teams.manage_members','teams.update'];
    want_ids integer[] := ARRAY[9,11,10,18,20,19,16,13,15,14,53623,53619,53622,53621,53620,22,24,23,32,117,118,26,28,29,27];
    want_keep text[] := ARRAY[
        'archive.view','bots.view','channels.view','conditions.view','customers.view','dashboard.view','deals.view',
        'erp.view','goals.view','invoices.view','leads.view','menu.dashboard','messaging.view','notifications.view',
        'orders.view','product_categories.view','products.view','quotes.view','reports.view','roles.view','shifts.view',
        'staff_reports.view_own','staff_reports.view_team','staff.view','suppliers.view','teams.view','tenant.profile.view'];
    n integer;
    n_before integer;
    n_deleted integer;
    n_after integer;
    n_other_before integer;
    n_other_after integer;
BEGIN
    -- 事前: 役割が 1 つあり、権限は 52 個
    SELECT count(*) INTO n FROM tenant_001.roles WHERE id = 2611;
    IF n <> 1 THEN RAISE EXCEPTION 'role 2611 must exist once but was %', n; END IF;
    SELECT count(*) INTO n_before FROM tenant_001.role_permissions WHERE role_id = 2611;
    IF n_before <> 52 THEN RAISE EXCEPTION 'before must be 52 but was %', n_before; END IF;
    SELECT count(*) INTO n_other_before FROM tenant_001.role_permissions WHERE role_id <> 2611;
    -- id と名前の対応が 25 組とも合っている
    SELECT count(*) INTO n FROM public.permissions p
      JOIN unnest(want_ids, want_remove) AS w(id, key) ON w.id = p.id AND w.key = p.key;
    IF n <> 25 THEN RAISE EXCEPTION 'id-key match must be 25 but was %', n; END IF;

    DELETE FROM tenant_001.role_permissions WHERE role_id = 2611 AND permission_id = ANY(want_ids);
    GET DIAGNOSTICS n_deleted = ROW_COUNT;
    IF n_deleted <> 25 THEN RAISE EXCEPTION 'deleted must be 25 but was %', n_deleted; END IF;

    -- 事後: 27 個で、残りは「残す」27 個とちょうど同じ。ほかの役割の行数は不変
    SELECT count(*) INTO n_after FROM tenant_001.role_permissions WHERE role_id = 2611;
    IF n_after <> 27 THEN RAISE EXCEPTION 'after must be 27 but was %', n_after; END IF;
    SELECT count(*) INTO n FROM tenant_001.role_permissions rp JOIN public.permissions p ON p.id = rp.permission_id
     WHERE rp.role_id = 2611 AND p.key = ANY(want_keep);
    IF n <> 27 THEN RAISE EXCEPTION 'keep match must be 27 but was %', n; END IF;
    SELECT count(*) INTO n_other_after FROM tenant_001.role_permissions WHERE role_id <> 2611;
    IF n_other_after <> n_other_before THEN RAISE EXCEPTION 'other roles changed % -> %', n_other_before, n_other_after; END IF;
    RAISE NOTICE 'before=% deleted=% after=% other=%', n_before, n_deleted, n_after, n_other_after;
END
$guard$;

SELECT p.key FROM tenant_001.role_permissions rp JOIN public.permissions p ON p.id = rp.permission_id
 WHERE rp.role_id = 2611 ORDER BY p.key;
ROLLBACK;
SELECT 'DRYRUN_OK';
