-- S1 段階②a（ADR-1018）: Google 接続設定 2 表を会社別 RLS にする（tenant_carrier_credentials と同じ型）
ALTER TABLE public.tenant_google_calendar_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tenant_google_calendar_config FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_google_calendar_config_tenant ON public.tenant_google_calendar_config;
CREATE POLICY tenant_google_calendar_config_tenant ON public.tenant_google_calendar_config
    FOR ALL
    USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER);

ALTER TABLE public.tenant_google_drive_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tenant_google_drive_config FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_google_drive_config_tenant ON public.tenant_google_drive_config;
CREATE POLICY tenant_google_drive_config_tenant ON public.tenant_google_drive_config
    FOR ALL
    USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER)
    WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER);
