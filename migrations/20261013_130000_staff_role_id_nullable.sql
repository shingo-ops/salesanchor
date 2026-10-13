-- staff.role_id を NULL 可にする（ADR-1008 P4a・構造のみ・冪等）
--
-- 名簿のロールの正本は user_roles。staff.role_id は読まない・書かない（列と外部キーは P4c まで残す）。
-- 値は変えない。全テナント（tenant_NNN）で、staff 表と role_id 列があるときだけ実行する。
-- すでに NULL 可なら何も起きない。
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN
        SELECT n.nspname AS schema_name
        FROM pg_namespace n
        WHERE n.nspname ~ '^tenant_[0-9]+$'
          AND EXISTS (
              SELECT 1 FROM information_schema.columns c
              WHERE c.table_schema = n.nspname
                AND c.table_name = 'staff'
                AND c.column_name = 'role_id'
          )
    LOOP
        EXECUTE format('ALTER TABLE %I.staff ALTER COLUMN role_id DROP NOT NULL', r.schema_name);
    END LOOP;
END $$;
