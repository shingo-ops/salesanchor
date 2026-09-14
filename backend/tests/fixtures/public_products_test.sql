
CREATE TABLE IF NOT EXISTS public.products (
    id                   SERIAL PRIMARY KEY,
    tenant_id            INTEGER,
    product_code         VARCHAR(50),
    name                 VARCHAR(255) NOT NULL,
    name_en              VARCHAR(255),
    mark                 VARCHAR(100),
    release_date         DATE,
    tcg_uuid             UUID UNIQUE,
    division_id          UUID,
    work_id              UUID,
    manufacturer_id      UUID,
    product_category_id  UUID,
    category_class       TEXT,
    required_output_value VARCHAR(255),
    is_active            BOOLEAN DEFAULT true,
    is_archived          BOOLEAN NOT NULL DEFAULT FALSE,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_public_products_code
    ON public.products (product_code) WHERE product_code IS NOT NULL;

-- Ensure Phase 2b columns exist even if table was pre-created by migration 062
ALTER TABLE public.products ADD COLUMN IF NOT EXISTS name_en VARCHAR(255);
ALTER TABLE public.products ADD COLUMN IF NOT EXISTS mark VARCHAR(100);
ALTER TABLE public.products ADD COLUMN IF NOT EXISTS release_date DATE;
ALTER TABLE public.products ADD COLUMN IF NOT EXISTS tcg_uuid UUID;
ALTER TABLE public.products ADD COLUMN IF NOT EXISTS division_id UUID;
ALTER TABLE public.products ADD COLUMN IF NOT EXISTS work_id UUID;
ALTER TABLE public.products ADD COLUMN IF NOT EXISTS manufacturer_id UUID;
ALTER TABLE public.products ADD COLUMN IF NOT EXISTS product_category_id UUID;
ALTER TABLE public.products ADD COLUMN IF NOT EXISTS category_class TEXT;
ALTER TABLE public.products ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT true;
ALTER TABLE public.products ADD COLUMN IF NOT EXISTS is_archived BOOLEAN DEFAULT FALSE;
ALTER TABLE public.products ADD COLUMN IF NOT EXISTS required_output_value VARCHAR(255);
CREATE UNIQUE INDEX IF NOT EXISTS uq_public_products_tcg_uuid
    ON public.products (tcg_uuid);
