-- Device-specific, Android LINE import-only credentials. No plaintext key is stored.
-- One public control table: applies once to existing and future tenants alike.
CREATE TABLE IF NOT EXISTS public.line_import_devices (
    id UUID PRIMARY KEY,
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    user_code_hash VARCHAR(64) NOT NULL UNIQUE,
    name VARCHAR(80) NOT NULL,
    scope VARCHAR(40) NOT NULL DEFAULT 'line:import:android'
        CHECK (scope = 'line:import:android'),
    tcg_schema VARCHAR(32) NOT NULL,
    owner_user_id INTEGER REFERENCES public.users(id) ON DELETE CASCADE,
    created_ip_hash VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    pending_expires_at TIMESTAMPTZ NOT NULL,
    approved_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    CHECK (length(token_hash) = 64),
    CHECK (length(user_code_hash) = 64)
);
CREATE INDEX IF NOT EXISTS ix_line_import_devices_owner
    ON public.line_import_devices(owner_user_id);
CREATE INDEX IF NOT EXISTS ix_line_import_devices_created
    ON public.line_import_devices(created_at);
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'salesanchor_app') THEN
        GRANT SELECT, INSERT, UPDATE, DELETE ON public.line_import_devices TO salesanchor_app;
    END IF;
END $$;
