-- S1 段階②b（ADR-1018）: public.suppliers に FORCE-RLS（共通=運営のみ書込／会社固有=自社のみ）
-- ポリシーは migrations/20260626_130000_force_rls_public_products.sql（ADR-145 products）と同文。冪等。

ALTER TABLE public.suppliers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.suppliers FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS suppliers_select ON public.suppliers;
CREATE POLICY suppliers_select ON public.suppliers FOR SELECT
  USING (
    tenant_id IS NULL
    OR tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
  );

DROP POLICY IF EXISTS suppliers_insert ON public.suppliers;
CREATE POLICY suppliers_insert ON public.suppliers FOR INSERT
  WITH CHECK (
    CASE WHEN tenant_id IS NULL THEN current_setting('app.is_operator', true) = 'true'
         ELSE tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER END
  );

DROP POLICY IF EXISTS suppliers_update ON public.suppliers;
CREATE POLICY suppliers_update ON public.suppliers FOR UPDATE
  USING (
    CASE WHEN tenant_id IS NULL THEN current_setting('app.is_operator', true) = 'true'
         ELSE tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER END
  )
  WITH CHECK (
    CASE WHEN tenant_id IS NULL THEN current_setting('app.is_operator', true) = 'true'
         ELSE tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER END
  );

DROP POLICY IF EXISTS suppliers_delete ON public.suppliers;
CREATE POLICY suppliers_delete ON public.suppliers FOR DELETE
  USING (
    CASE WHEN tenant_id IS NULL THEN current_setting('app.is_operator', true) = 'true'
         ELSE tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER END
  );
