-- ADR-156 Phase 3A: Add product_kind_id FK to products table
-- Replaces division_id (UUID → tenant_004.tcg_major_categories) with
-- product_kind_id (INTEGER → public.product_kinds) for SSOT compliance.

ALTER TABLE public.products
  ADD COLUMN IF NOT EXISTS product_kind_id INTEGER REFERENCES public.product_kinds(id);

-- Index for lookup performance
CREATE INDEX IF NOT EXISTS idx_products_product_kind_id ON public.products (product_kind_id);
