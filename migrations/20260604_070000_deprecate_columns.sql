-- Migration: deprecated 列のコメント追加
--
-- 目的:
--   C-2: companies.trust_level を deprecated 化
--   C-4: products.unit_price / unit_price_usd / unit_price_eur を deprecated 化
--
-- 影響テーブル:
--   {tenant_NNN}.companies (trust_level)
--   public.products (unit_price, unit_price_usd, unit_price_eur)
--
-- 冪等: COMMENT ON COLUMN は何度実行しても上書きのみ

-- === C-2: trust_level (tenant_NNN.companies) ===
DO $$
DECLARE
    schema_record RECORD;
BEGIN
    FOR schema_record IN
        SELECT nspname AS schema_name
        FROM pg_namespace
        WHERE nspname LIKE 'tenant_%'
        ORDER BY nspname
    LOOP
        -- trust_level カラムが存在する場合のみコメント追加
        IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = schema_record.schema_name
              AND table_name = 'companies'
              AND column_name = 'trust_level'
        ) THEN
            EXECUTE format(
                'COMMENT ON COLUMN %I.companies.trust_level IS '
                '''DEPRECATED C-2: ADR-SA-12で廃止確定。新規コードで参照禁止。UI撤去は別PR申し送り。''',
                schema_record.schema_name
            );
            RAISE NOTICE '% companies.trust_level deprecated comment added', schema_record.schema_name;
        END IF;
    END LOOP;
END
$$;

-- === C-4: products.unit_price 系 (public.products) ===
COMMENT ON COLUMN public.products.unit_price IS
    'DEPRECATED C-4: 新規コードで参照禁止。正式単価はpublic.inventory.unit_priceを使用。';
COMMENT ON COLUMN public.products.unit_price_usd IS
    'DEPRECATED C-4: 新規コードで参照禁止。';
COMMENT ON COLUMN public.products.unit_price_eur IS
    'DEPRECATED C-4: 新規コードで参照禁止。';
