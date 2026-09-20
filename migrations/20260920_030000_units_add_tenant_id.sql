-- 単位マスタに tenant_id を追加（NULL=共用/LINE解析用、数値=テナント個別）
ALTER TABLE public.units ADD COLUMN IF NOT EXISTS tenant_id INTEGER REFERENCES public.tenants(id);
CREATE INDEX IF NOT EXISTS idx_units_tenant_id ON public.units (tenant_id);
