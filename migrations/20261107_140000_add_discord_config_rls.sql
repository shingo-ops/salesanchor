-- ADR-1067 段階④ 便④-3: public.tenant_discord_config と public.tenant_discord_ticket_config に会社ごとの RLS（型C）を付ける。
-- 読む: 全行（Discord の受け口が会社を決める前に guild_id から会社を引くため。design.md §2）。書く: 自社の会社文脈か運営文脈だけ。
-- 冪等（DROP POLICY IF EXISTS）・1 取引（ENABLE とポリシーの間に全拒否の間を作らない）。design.md §2-2。
BEGIN;
ALTER TABLE public.tenant_discord_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tenant_discord_config FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_discord_config_select ON public.tenant_discord_config;
CREATE POLICY tenant_discord_config_select ON public.tenant_discord_config FOR SELECT USING (true);
DROP POLICY IF EXISTS tenant_discord_config_insert ON public.tenant_discord_config;
CREATE POLICY tenant_discord_config_insert ON public.tenant_discord_config FOR INSERT
  WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
              OR current_setting('app.is_operator', true) = 'true');
DROP POLICY IF EXISTS tenant_discord_config_update ON public.tenant_discord_config;
CREATE POLICY tenant_discord_config_update ON public.tenant_discord_config FOR UPDATE
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
         OR current_setting('app.is_operator', true) = 'true')
  WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
              OR current_setting('app.is_operator', true) = 'true');
DROP POLICY IF EXISTS tenant_discord_config_delete ON public.tenant_discord_config;
CREATE POLICY tenant_discord_config_delete ON public.tenant_discord_config FOR DELETE
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
         OR current_setting('app.is_operator', true) = 'true');
ALTER TABLE public.tenant_discord_ticket_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tenant_discord_ticket_config FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_discord_ticket_config_select ON public.tenant_discord_ticket_config;
CREATE POLICY tenant_discord_ticket_config_select ON public.tenant_discord_ticket_config FOR SELECT USING (true);
DROP POLICY IF EXISTS tenant_discord_ticket_config_insert ON public.tenant_discord_ticket_config;
CREATE POLICY tenant_discord_ticket_config_insert ON public.tenant_discord_ticket_config FOR INSERT
  WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
              OR current_setting('app.is_operator', true) = 'true');
DROP POLICY IF EXISTS tenant_discord_ticket_config_update ON public.tenant_discord_ticket_config;
CREATE POLICY tenant_discord_ticket_config_update ON public.tenant_discord_ticket_config FOR UPDATE
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
         OR current_setting('app.is_operator', true) = 'true')
  WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
              OR current_setting('app.is_operator', true) = 'true');
DROP POLICY IF EXISTS tenant_discord_ticket_config_delete ON public.tenant_discord_ticket_config;
CREATE POLICY tenant_discord_ticket_config_delete ON public.tenant_discord_ticket_config FOR DELETE
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
         OR current_setting('app.is_operator', true) = 'true');
COMMIT;
