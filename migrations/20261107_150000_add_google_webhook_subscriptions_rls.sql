-- ADR-1067 段階④ 便④-4: public.google_webhook_subscriptions に会社ごとの RLS（型C）を付ける。
-- 読む: 全行（Google の通知の受け口が会社を決める前に channel_id から会社を引くため。design.md §2）。書く: 自社の会社文脈か運営文脈だけ。
-- 冪等（DROP POLICY IF EXISTS）・1 取引（ENABLE とポリシーの間に全拒否の間を作らない）。design.md §2-2。
BEGIN;
ALTER TABLE public.google_webhook_subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.google_webhook_subscriptions FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS google_webhook_subscriptions_select ON public.google_webhook_subscriptions;
CREATE POLICY google_webhook_subscriptions_select ON public.google_webhook_subscriptions FOR SELECT USING (true);
DROP POLICY IF EXISTS google_webhook_subscriptions_insert ON public.google_webhook_subscriptions;
CREATE POLICY google_webhook_subscriptions_insert ON public.google_webhook_subscriptions FOR INSERT
  WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
              OR current_setting('app.is_operator', true) = 'true');
DROP POLICY IF EXISTS google_webhook_subscriptions_update ON public.google_webhook_subscriptions;
CREATE POLICY google_webhook_subscriptions_update ON public.google_webhook_subscriptions FOR UPDATE
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
         OR current_setting('app.is_operator', true) = 'true')
  WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
              OR current_setting('app.is_operator', true) = 'true');
DROP POLICY IF EXISTS google_webhook_subscriptions_delete ON public.google_webhook_subscriptions;
CREATE POLICY google_webhook_subscriptions_delete ON public.google_webhook_subscriptions FOR DELETE
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
         OR current_setting('app.is_operator', true) = 'true');
COMMIT;
