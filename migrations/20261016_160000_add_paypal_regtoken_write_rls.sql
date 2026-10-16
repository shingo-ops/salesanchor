-- S1 段階③便A（ADR-1018）: tenant_paypal_config / registration_tokens に「書込だけ RLS」
-- 読取は全行可（招待リンクを開いた時点・PayPal 不服申立通知は会社が決まる前に全行から探すため）。
-- 書込（INSERT / UPDATE / DELETE）は app.tenant_id と行の tenant_id が一致するときだけ。
-- 両表とも tenant_id は NOT NULL のため共通行の分岐は不要。運営の通り道は作らない。冪等。

-- tenant_paypal_config
ALTER TABLE public.tenant_paypal_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tenant_paypal_config FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_paypal_config_select ON public.tenant_paypal_config;
CREATE POLICY tenant_paypal_config_select ON public.tenant_paypal_config FOR SELECT
  USING (true);

DROP POLICY IF EXISTS tenant_paypal_config_insert ON public.tenant_paypal_config;
CREATE POLICY tenant_paypal_config_insert ON public.tenant_paypal_config FOR INSERT
  WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER);

DROP POLICY IF EXISTS tenant_paypal_config_update ON public.tenant_paypal_config;
CREATE POLICY tenant_paypal_config_update ON public.tenant_paypal_config FOR UPDATE
  USING      (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER)
  WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER);

DROP POLICY IF EXISTS tenant_paypal_config_delete ON public.tenant_paypal_config;
CREATE POLICY tenant_paypal_config_delete ON public.tenant_paypal_config FOR DELETE
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER);

-- registration_tokens
ALTER TABLE public.registration_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.registration_tokens FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS registration_tokens_select ON public.registration_tokens;
CREATE POLICY registration_tokens_select ON public.registration_tokens FOR SELECT
  USING (true);

DROP POLICY IF EXISTS registration_tokens_insert ON public.registration_tokens;
CREATE POLICY registration_tokens_insert ON public.registration_tokens FOR INSERT
  WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER);

DROP POLICY IF EXISTS registration_tokens_update ON public.registration_tokens;
CREATE POLICY registration_tokens_update ON public.registration_tokens FOR UPDATE
  USING      (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER)
  WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER);

DROP POLICY IF EXISTS registration_tokens_delete ON public.registration_tokens;
CREATE POLICY registration_tokens_delete ON public.registration_tokens FOR DELETE
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER);
