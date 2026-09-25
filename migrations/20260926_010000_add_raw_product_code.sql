-- Add raw_product_code to extraction_items for Gemini v6 raw code extraction
-- Phase 2 of ADR-158: extract the literal product code/model number from supplier messages
ALTER TABLE public.extraction_items ADD COLUMN IF NOT EXISTS raw_product_code text;
COMMENT ON COLUMN public.extraction_items.raw_product_code IS 'Gemini v6 が原文から抽出した型番/製品コード (OP-14, SV8a等)。NULL=v5以前/原文に型番なし';
