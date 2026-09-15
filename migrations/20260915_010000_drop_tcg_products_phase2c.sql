-- Phase 2c: DROP tcg_products（ADR-1001）
-- 前提: Phase 2a (20260914_140000) で全データを public.products に移行済み、FK 張替え済み
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
DO $body$
DECLARE
    schema_record RECORD;
    remaining_fk_count INTEGER;
BEGIN
    FOR schema_record IN
        SELECT n.nspname AS schema_name
        FROM pg_namespace n
        JOIN pg_class c ON c.relnamespace = n.oid
        WHERE n.nspname LIKE 'tenant_%'
          AND c.relname = 'tcg_products'
          AND c.relkind = 'r'
        ORDER BY n.nspname
    LOOP
        -- Safety: verify no FKs still reference tcg_products
        SELECT count(*) INTO remaining_fk_count
        FROM pg_constraint con
        JOIN pg_class ref ON con.confrelid = ref.oid
        JOIN pg_namespace ns ON ref.relnamespace = ns.oid
        WHERE ns.nspname = schema_record.schema_name
          AND ref.relname = 'tcg_products'
          AND con.contype = 'f';

        IF remaining_fk_count > 0 THEN
            RAISE EXCEPTION 'Phase 2c blocked: % FK(s) still reference %.tcg_products',
                remaining_fk_count, schema_record.schema_name;
        END IF;

        EXECUTE format('DROP TABLE %I.tcg_products', schema_record.schema_name);
        RAISE NOTICE 'Phase 2c: dropped %.tcg_products', schema_record.schema_name;
    END LOOP;
END;
$body$;
COMMIT;
