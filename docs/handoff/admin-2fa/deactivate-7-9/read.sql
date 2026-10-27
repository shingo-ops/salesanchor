-- read.sql (READ ONLY): id 7,9 の現在値
BEGIN READ ONLY;
SELECT id, tenant_id, role, is_active, is_super_admin, updated_at FROM public.users WHERE id IN (7,9) ORDER BY id;
ROLLBACK;
