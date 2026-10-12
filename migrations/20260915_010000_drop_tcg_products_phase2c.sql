-- Phase 2c: DROP tcg_products（ADR-1001）
-- 前提: Phase 2a (20260914_140000) で全データを public.products に移行済み、FK 張替え済み
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
DO $body$
DECLARE
    schema_record RECORD;
    remaining_fk_count INTEGER;
    _tcg_uuid_exists BOOLEAN;
    _tcg_products_rows BIGINT;
    fk_record RECORD;
    _ref_rows BIGINT;
BEGIN
    -- incident 2026-10-04 (deploy run 37139483973): every steady-state deploy re-creates
    -- tenant_004.tcg_products and its keyword copies (product_search_keywords /
    -- product_exclude_keywords) fresh with FKs pointing at tcg_products, because the prior
    -- successful deploy already dropped them here. migrations/20260914_140000's Step3
    -- (which used to move those FKs off tcg_products onto public.products(tcg_uuid)) now
    -- skips entirely once tcg_uuid is gone, so the FK never gets moved and this file's own
    -- safety check below raises "Phase 2c blocked" every single deploy.
    -- Pre-cleanup (only runs when tcg_uuid is already gone AND this schema's tcg_products
    -- is empty, i.e. there is nothing left for the FK to meaningfully protect): for each FK
    -- still referencing tcg_products, drop it only if the referencing table itself is also
    -- empty. A referencing table with rows is left untouched — the existing EXCEPTION below
    -- will still fire for it, since mapping existing data needs a human decision.
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'products' AND column_name = 'tcg_uuid'
    ) INTO _tcg_uuid_exists;

    FOR schema_record IN
        SELECT n.nspname AS schema_name
        FROM pg_namespace n
        JOIN pg_class c ON c.relnamespace = n.oid
        WHERE n.nspname LIKE 'tenant_%'
          AND c.relname = 'tcg_products'
          AND c.relkind = 'r'
        ORDER BY n.nspname
    LOOP
        IF NOT _tcg_uuid_exists THEN
            EXECUTE format('SELECT count(*) FROM %I.tcg_products', schema_record.schema_name)
                INTO _tcg_products_rows;

            IF _tcg_products_rows = 0 THEN
                FOR fk_record IN
                    SELECT con.conname AS conname, cl.relname AS ref_table_name
                    FROM pg_constraint con
                    JOIN pg_class ref ON con.confrelid = ref.oid
                    JOIN pg_namespace ns ON ref.relnamespace = ns.oid
                    JOIN pg_class cl ON cl.oid = con.conrelid
                    WHERE ns.nspname = schema_record.schema_name
                      AND ref.relname = 'tcg_products'
                      AND con.contype = 'f'
                LOOP
                    EXECUTE format('SELECT count(*) FROM %I.%I', schema_record.schema_name, fk_record.ref_table_name)
                        INTO _ref_rows;

                    IF _ref_rows = 0 THEN
                        EXECUTE format('ALTER TABLE %I.%I DROP CONSTRAINT %I',
                            schema_record.schema_name, fk_record.ref_table_name, fk_record.conname);
                        RAISE NOTICE 'Phase 2c pre-cleanup: dropped stale FK % on %.% (tcg_uuid absent, tcg_products 0 rows, referencing table 0 rows)',
                            fk_record.conname, schema_record.schema_name, fk_record.ref_table_name;
                    ELSE
                        RAISE NOTICE 'Phase 2c pre-cleanup: %.% has % row(s) — leaving FK % in place (needs a human decision)',
                            schema_record.schema_name, fk_record.ref_table_name, _ref_rows, fk_record.conname;
                    END IF;
                END LOOP;
            END IF;
        END IF;

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
