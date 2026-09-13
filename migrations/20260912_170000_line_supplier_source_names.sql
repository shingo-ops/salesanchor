-- Import-source aliases do not rename the existing PC supplier master.
CREATE TABLE IF NOT EXISTS public.line_supplier_source_names (
    tcg_schema text NOT NULL CHECK (tcg_schema ~ '^tenant_[0-9]{3}$'),
    source_format text NOT NULL CHECK (source_format IN ('pc', 'android')),
    display_name text NOT NULL CHECK (length(display_name) BETWEEN 1 AND 200),
    supplier_id uuid NOT NULL,
    evidence_sha256 text NOT NULL CHECK (evidence_sha256 ~ '^[0-9a-f]{64}$'),
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tcg_schema, source_format, display_name)
);
-- Supplier IDs live in tenant schemas; the application validates the scoped
-- active supplier on registration and on every read. Dangling aliases fail closed.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='salesanchor_app') THEN
        GRANT SELECT, INSERT ON public.line_supplier_source_names TO salesanchor_app;
    END IF;
END $$;
