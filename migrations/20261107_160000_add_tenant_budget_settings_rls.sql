-- ADR-1067 段階④ 便④-5: public.tenant_llm_budgets・public.tenant_settings に会社ごとの RLS（型C）を付ける。
-- 読む: 全行（運営画面が全社を一覧するため。design.md §2）。書く: 自社の会社文脈か運営文脈だけ。
-- 冪等（DROP POLICY IF EXISTS）・1 取引（ENABLE とポリシーの間に全拒否の間を作らない）。design.md §2-2。
BEGIN;
ALTER TABLE public.tenant_llm_budgets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tenant_llm_budgets FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_llm_budgets_select ON public.tenant_llm_budgets;
CREATE POLICY tenant_llm_budgets_select ON public.tenant_llm_budgets FOR SELECT USING (true);
DROP POLICY IF EXISTS tenant_llm_budgets_insert ON public.tenant_llm_budgets;
CREATE POLICY tenant_llm_budgets_insert ON public.tenant_llm_budgets FOR INSERT
  WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
              OR current_setting('app.is_operator', true) = 'true');
DROP POLICY IF EXISTS tenant_llm_budgets_update ON public.tenant_llm_budgets;
CREATE POLICY tenant_llm_budgets_update ON public.tenant_llm_budgets FOR UPDATE
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
         OR current_setting('app.is_operator', true) = 'true')
  WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
              OR current_setting('app.is_operator', true) = 'true');
DROP POLICY IF EXISTS tenant_llm_budgets_delete ON public.tenant_llm_budgets;
CREATE POLICY tenant_llm_budgets_delete ON public.tenant_llm_budgets FOR DELETE
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
         OR current_setting('app.is_operator', true) = 'true');
ALTER TABLE public.tenant_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tenant_settings FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_settings_select ON public.tenant_settings;
CREATE POLICY tenant_settings_select ON public.tenant_settings FOR SELECT USING (true);
DROP POLICY IF EXISTS tenant_settings_insert ON public.tenant_settings;
CREATE POLICY tenant_settings_insert ON public.tenant_settings FOR INSERT
  WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
              OR current_setting('app.is_operator', true) = 'true');
DROP POLICY IF EXISTS tenant_settings_update ON public.tenant_settings;
CREATE POLICY tenant_settings_update ON public.tenant_settings FOR UPDATE
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
         OR current_setting('app.is_operator', true) = 'true')
  WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
              OR current_setting('app.is_operator', true) = 'true');
DROP POLICY IF EXISTS tenant_settings_delete ON public.tenant_settings;
CREATE POLICY tenant_settings_delete ON public.tenant_settings FOR DELETE
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
         OR current_setting('app.is_operator', true) = 'true');
COMMIT;
