-- Add resolved_product_code to extraction_items for Gemini v5 product identification
ALTER TABLE tenant_004.extraction_items
    ADD COLUMN IF NOT EXISTS resolved_product_code text;

COMMENT ON COLUMN tenant_004.extraction_items.resolved_product_code
    IS 'Gemini v5 が商品マスタ参照から解決した商品コード (PM0263等)。NULL=未解決/v4以前';
