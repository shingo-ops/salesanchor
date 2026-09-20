-- Add tenant_id to public.tcg_note_master for multi-tenant support
-- NULL = shared (operator-managed), integer = tenant-specific
ALTER TABLE public.tcg_note_master
  ADD COLUMN IF NOT EXISTS tenant_id INTEGER;

-- Index for tenant filtering
CREATE INDEX IF NOT EXISTS idx_tcg_note_master_tenant
  ON public.tcg_note_master (tenant_id);
