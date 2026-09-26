-- Fix resolved_work_id column type from UUID to INTEGER
-- Root cause: Column was manually altered to UUID on production,
-- but master SSOT Phase 2 changed work_ids from UUID to INTEGER.
-- Old UUID values reference deprecated tcg_series table and are invalid.
--
-- Affected schemas: tenant_001, tenant_004 (all with extraction_items table)
-- Impact: 3,971 rows with UUID values will be set to NULL
-- Idempotent: Uses IF checks for safe re-execution

DO $$
DECLARE
    schema_name text;
    col_type text;
BEGIN
    FOR schema_name IN
        SELECT schemaname FROM pg_tables
        WHERE tablename = 'extraction_items'
        ORDER BY schemaname
    LOOP
        -- Check current column type
        SELECT udt_name INTO col_type
        FROM information_schema.columns
        WHERE table_schema = schema_name
          AND table_name = 'extraction_items'
          AND column_name = 'resolved_work_id';

        -- Only alter if column is UUID (idempotent)
        IF col_type = 'uuid' THEN
            RAISE NOTICE 'Fixing %.extraction_items.resolved_work_id: uuid → integer', schema_name;

            -- NULL out old UUID values (deprecated tcg_series references)
            EXECUTE format('UPDATE %I.extraction_items SET resolved_work_id = NULL WHERE resolved_work_id IS NOT NULL', schema_name);

            -- Change column type to INTEGER (matches migration 20260912_020000)
            EXECUTE format('ALTER TABLE %I.extraction_items ALTER COLUMN resolved_work_id TYPE INTEGER USING NULL', schema_name);

            RAISE NOTICE 'Fixed %.extraction_items.resolved_work_id', schema_name;
        ELSE
            RAISE NOTICE '%.extraction_items.resolved_work_id already % — skipping', schema_name, col_type;
        END IF;
    END LOOP;
END
$$;
