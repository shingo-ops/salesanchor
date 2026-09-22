-- Drop ALL remaining FKs referencing tcg_products in any tenant schema
-- This is the definitive fix: instead of guessing FK names, dynamically find and drop all.
-- Runs BEFORE Phase 2c (drop_tcg_products_phase2c.sql) in run_all_migrations.sh
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
DO $body$
DECLARE
    _schema TEXT;
    _fk RECORD;
    _dropped INTEGER := 0;
BEGIN
    FOR _schema IN
        SELECT n.nspname
        FROM pg_namespace n
        JOIN pg_class c ON c.relnamespace = n.oid
        WHERE n.nspname LIKE 'tenant_%'
          AND c.relname = 'tcg_products'
          AND c.relkind = 'r'
        ORDER BY n.nspname
    LOOP
        -- Find ALL foreign keys referencing <schema>.tcg_products from ANY table in ANY schema
        FOR _fk IN
            SELECT
                src_ns.nspname AS src_schema,
                src_cls.relname AS src_table,
                con.conname AS constraint_name
            FROM pg_constraint con
            JOIN pg_class ref ON con.confrelid = ref.oid
            JOIN pg_namespace ref_ns ON ref.relnamespace = ref_ns.oid
            JOIN pg_class src_cls ON con.conrelid = src_cls.oid
            JOIN pg_namespace src_ns ON src_cls.relnamespace = src_ns.oid
            WHERE ref_ns.nspname = _schema
              AND ref.relname = 'tcg_products'
              AND con.contype = 'f'
            ORDER BY src_ns.nspname, src_cls.relname
        LOOP
            EXECUTE format(
                'ALTER TABLE %I.%I DROP CONSTRAINT IF EXISTS %I',
                _fk.src_schema, _fk.src_table, _fk.constraint_name
            );
            RAISE NOTICE 'Dropped FK: %.%.% -> %.tcg_products',
                _fk.src_schema, _fk.src_table, _fk.constraint_name, _schema;
            _dropped := _dropped + 1;
        END LOOP;
    END LOOP;
    RAISE NOTICE 'Dynamic FK cleanup complete: % FK(s) dropped', _dropped;
END;
$body$;
COMMIT;
