-- ============================================================
-- Unblock Phase 2c: Drop stale FKs referencing tcg_products
-- ============================================================
-- Background:
--   Phase 2a Step 1 failed to create UNIQUE constraint uq_products_tcg_uuid,
--   which prevented Step 3 from rewiring FKs to public.products(tcg_uuid).
--   As a result, product_search_keywords and product_exclude_keywords still
--   reference tenant_*.tcg_products, blocking Phase 2c (DROP tcg_products).
--
-- This migration:
--   Step 1: Creates the missing UNIQUE constraint (safe: duplicates -> NOTICE)
--   Step 2: Drops all FKs referencing tcg_products in any tenant schema
--
-- Safety: Idempotent. Only drops FKs to a table that Phase 2c will DROP.
-- Phase B handles UUID->INTEGER conversion and creates new FKs to public.products(id).
-- Values: DDL only -- no INSERT/UPDATE/DELETE.
-- ============================================================

-- Step 1: Create UNIQUE constraint on public.products(tcg_uuid) if missing
-- Phase 2a Step 1 was supposed to create this but it was not applied
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'uq_products_tcg_uuid'
          AND conrelid = 'public.products'::regclass
    ) THEN
        BEGIN
            ALTER TABLE public.products ADD CONSTRAINT uq_products_tcg_uuid UNIQUE (tcg_uuid);
            RAISE NOTICE 'Created UNIQUE constraint uq_products_tcg_uuid on public.products';
        EXCEPTION WHEN unique_violation THEN
            RAISE NOTICE 'Cannot create uq_products_tcg_uuid (duplicate values exist): %', SQLERRM;
        END;
    ELSE
        RAISE NOTICE 'uq_products_tcg_uuid already exists -- skipping';
    END IF;
END $$;

-- Step 2: Drop all FKs that reference tcg_products in any tenant schema
DO $$
DECLARE
    _schema TEXT;
    _rec RECORD;
BEGIN
    FOR _schema IN
        SELECT nspname FROM pg_namespace
        WHERE nspname LIKE 'tenant_%'
        ORDER BY nspname
    LOOP
        FOR _rec IN
            SELECT con.conname, c.relname AS table_name
            FROM pg_constraint con
            JOIN pg_class c ON c.oid = con.conrelid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            JOIN pg_class fc ON fc.oid = con.confrelid
            WHERE n.nspname = _schema
              AND fc.relname = 'tcg_products'
              AND con.contype = 'f'
        LOOP
            EXECUTE format(
                'ALTER TABLE %I.%I DROP CONSTRAINT %I',
                _schema, _rec.table_name, _rec.conname
            );
            RAISE NOTICE 'Dropped FK %.% constraint % (referenced tcg_products)',
                _schema, _rec.table_name, _rec.conname;
        END LOOP;
    END LOOP;
END $$;
