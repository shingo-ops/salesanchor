-- SSOT cleanup 1: products.category_classification 廃止
-- 目的:
--   - public.products から category_classification を物理削除する
--   - DROP 前に非NULL値を backup table に退避する
-- 注意:
--   - 危険変更のため release 時は dry-run で件数確認すること
--   - run_all_migrations.sh から実行される前提で idempotent にする

CREATE TABLE IF NOT EXISTS public.products_category_classification_backup (
    product_id BIGINT PRIMARY KEY,
    tenant_id INTEGER,
    product_code VARCHAR(20),
    name TEXT,
    category_classification VARCHAR(100) NOT NULL,
    captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

DO $$
DECLARE
    has_column boolean;
    backed_up_rows bigint := 0;
BEGIN
    SELECT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'products'
          AND column_name = 'category_classification'
    ) INTO has_column;

    IF has_column THEN
        EXECUTE $sql$
            INSERT INTO public.products_category_classification_backup (
                product_id,
                tenant_id,
                product_code,
                name,
                category_classification,
                captured_at
            )
            SELECT
                id,
                tenant_id,
                product_code,
                name,
                category_classification,
                NOW()
            FROM public.products
            WHERE category_classification IS NOT NULL
            ON CONFLICT (product_id) DO UPDATE SET
                tenant_id = EXCLUDED.tenant_id,
                product_code = EXCLUDED.product_code,
                name = EXCLUDED.name,
                category_classification = EXCLUDED.category_classification,
                captured_at = EXCLUDED.captured_at
        $sql$;
        GET DIAGNOSTICS backed_up_rows = ROW_COUNT;
        RAISE NOTICE 'migration 20260623_020000: backed up % products.category_classification rows', backed_up_rows;

        EXECUTE 'ALTER TABLE public.products DROP COLUMN IF EXISTS category_classification';
    END IF;
END $$;
