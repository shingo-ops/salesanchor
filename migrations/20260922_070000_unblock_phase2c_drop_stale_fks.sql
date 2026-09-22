-- ============================================================
-- Unblock Phase 2c: Drop stale FKs referencing tcg_products
-- ============================================================
-- Background:
--   Phase 2a Step 1 failed to create UNIQUE constraint uq_products_tcg_uuid,
--   which prevented Step 3 from rewiring FKs to public.products(tcg_uuid).
--   As a result, product_search_keywords and product_exclude_keywords still
--   reference tenant_*.tcg_products, blocking Phase 2c.
--
-- This migration:
--   Step 1: Creates the missing UNIQUE constraint (safe: duplicates cause NOTICE)
--   Step 2: Drops all FKs referencing tcg_products in any tenant schema
--
-- Safety: Idempotent. Only drops FKs to a table that Phase 2c will remove.
-- Phase B handles UUID to INTEGER conversion and creates new FKs.
-- Values: DDL only. No INSERT/UPDATE/DELETE.
-- ============================================================

-- Step 1: Create UNIQUE constraint on public.products(tcg_uuid) if missing
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints WHERE table_schema = 'public' AND table_name = 'products' AND constraint_name = 'uq_products_tcg_uuid'
    ) THEN
        BEGIN
            ALTER TABLE public.products ADD CONSTRAINT uq_products_tcg_uuid UNIQUE (tcg_uuid);
            RAISE NOTICE 'Created UNIQUE constraint uq_products_tcg_uuid on public.products';
        EXCEPTION WHEN unique_violation THEN
            RAISE NOTICE 'Cannot create uq_products_tcg_uuid (duplicate values): %', SQLERRM;
        END;
    ELSE
        RAISE NOTICE 'uq_products_tcg_uuid already exists — skipping';
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
            JOIN pg_class fc ON fc.oid = con.confrelid AND fc.relname = 'tcg_products'
            WHERE n.nspname = _schema AND con.contype = 'f'
        LOOP
            EXECUTE format(
                'ALTER TABLE %I.%I DROP CONSTRAINT %I',
                _schema, _rec.table_name, _rec.conname
            );
            RAISE NOTICE 'Dropped FK %.% constraint % (referenced tcg_products)', _schema, _rec.table_name, _rec.conname;
        END LOOP;
    END LOOP;
END $$;
