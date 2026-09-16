-- Add resolved_product_code to extraction_items for Gemini v5 product identification
-- 全テナントスキーマを走査し、extraction_items テーブルがあれば列を追加する
-- (CI テスト環境では tenant_901 等を使うため tenant_004 ハードコード不可)
DO $$
DECLARE
    target record;
BEGIN
    FOR target IN
        SELECT nspname FROM pg_namespace WHERE nspname LIKE 'tenant_%' ORDER BY nspname
    LOOP
        -- extraction_items が存在するテナントだけに適用
        IF EXISTS (
            SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = target.nspname AND c.relname = 'extraction_items' AND c.relkind = 'r'
        ) THEN
            EXECUTE format(
                'ALTER TABLE %I.extraction_items ADD COLUMN IF NOT EXISTS resolved_product_code text',
                target.nspname
            );
            EXECUTE format(
                'COMMENT ON COLUMN %I.extraction_items.resolved_product_code IS '
                '''Gemini v5 が商品マスタ参照から解決した商品コード (PM0263等)。NULL=未解決/v4以前''',
                target.nspname
            );
        END IF;
    END LOOP;
END $$;
