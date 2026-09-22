-- ステータスマスタに tenant_id を追加（NULL=共用/LINE解析用、数値=テナント個別）
ALTER TABLE public.tcg_status_master ADD COLUMN IF NOT EXISTS tenant_id INTEGER REFERENCES public.tenants(id);
CREATE INDEX IF NOT EXISTS idx_tcg_status_master_tenant_id ON public.tcg_status_master (tenant_id);
