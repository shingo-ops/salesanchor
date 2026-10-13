-- 名簿のメールの正本を users.email にする（ADR-1008 P4b・構造のみ・冪等）
--
-- 1) 全テナント（tenant_NNN）で staff.primary_email の NOT NULL を外す（列と値は P4c まで残す。読まない・書かない）。
-- 2) v_senders の contact_email（staff の枝）を users.email の結合で作り直す。
--    列の名前・順・型は今と同じ（id, tenant_id, sender_type, display_name, contact_email VARCHAR(255)）。
-- staff 表がないテナントは飛ばす。すでに NULL 可・作り直し済みなら結果は同じ。
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
                AND c.column_name = 'primary_email'
          )
    LOOP
        EXECUTE format('ALTER TABLE %I.staff ALTER COLUMN primary_email DROP NOT NULL', r.schema_name);

        IF EXISTS (
            SELECT 1 FROM information_schema.tables t
            WHERE t.table_schema = r.schema_name
              AND t.table_name = 'v_senders'
        ) THEN
            EXECUTE format($v$
                CREATE OR REPLACE VIEW %1$I.v_senders AS
                SELECT
                    s.id, s.tenant_id, 'staff'::VARCHAR(10) AS sender_type,
                    CONCAT(s.surname_jp, ' ', s.given_name_jp) AS display_name,
                    u.email::VARCHAR(255) AS contact_email
                FROM %1$I.staff s
                JOIN public.users u ON u.id = s.user_id
                UNION ALL
                SELECT
                    id, tenant_id, 'bot'::VARCHAR(10) AS sender_type,
                    display_name, sender_email AS contact_email
                FROM %1$I.bots
            $v$, r.schema_name);
        END IF;
    END LOOP;
END $$;
