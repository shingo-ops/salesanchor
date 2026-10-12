-- staff.user_id を NOT NULL にする（ADR-1008 P3・構造のみ・冪等）
--
-- 全テナント（tenant_NNN）で、staff 表と user_id 列があるときだけ実行する。
-- user_id が NULL の行が1行でもあるテナントは WARNING を出して飛ばす（デプロイは止めない）。
-- すでに NOT NULL なら何も起きない。
DO $$
DECLARE
    r RECORD;
    null_count BIGINT;
BEGIN
    FOR r IN
        SELECT n.nspname AS schema_name
        FROM pg_namespace n
        WHERE n.nspname ~ '^tenant_[0-9]+$'
          AND EXISTS (
              SELECT 1 FROM information_schema.columns c
              WHERE c.table_schema = n.nspname
                AND c.table_name = 'staff'
                AND c.column_name = 'user_id'
          )
    LOOP
        EXECUTE format('SELECT count(*) FROM %I.staff WHERE user_id IS NULL', r.schema_name)
            INTO null_count;
        IF null_count > 0 THEN
            RAISE WARNING '% の staff.user_id が NULL の行が % 件あるため NOT NULL 化を飛ばしました', r.schema_name, null_count;
        ELSE
            EXECUTE format('ALTER TABLE %I.staff ALTER COLUMN user_id SET NOT NULL', r.schema_name);
        END IF;
    END LOOP;
END $$;
