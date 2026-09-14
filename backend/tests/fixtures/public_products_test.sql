
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
    is_active            BOOLEAN DEFAULT true,
    is_archived          BOOLEAN NOT NULL DEFAULT FALSE,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_public_products_code
    ON public.products (product_code) WHERE product_code IS NOT NULL;
