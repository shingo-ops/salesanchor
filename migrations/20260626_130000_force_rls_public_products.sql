-- ADR-145: public.products に FORCE-RLS を付与（共通=運営のみ/固有=自テナント）
-- 前例 translation_glossary（ADR-SA-17）移植。dry-run（段階2-a・本番ROLLBACK保証）で全経路実証済み。
-- 冪等。

ALTER TABLE public.products ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.products FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS products_select ON public.products;
CREATE POLICY products_select ON public.products FOR SELECT
  USING (
    tenant_id IS NULL
    OR tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
  );

DROP POLICY IF EXISTS products_insert ON public.products;
CREATE POLICY products_insert ON public.products FOR INSERT
  WITH CHECK (
    CASE WHEN tenant_id IS NULL THEN current_setting('app.is_operator', true) = 'true'
         ELSE tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER END
  );

DROP POLICY IF EXISTS products_update ON public.products;
CREATE POLICY products_update ON public.products FOR UPDATE
  USING (
    CASE WHEN tenant_id IS NULL THEN current_setting('app.is_operator', true) = 'true'
         ELSE tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER END
  )
  WITH CHECK (
    CASE WHEN tenant_id IS NULL THEN current_setting('app.is_operator', true) = 'true'
         ELSE tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER END
  );

DROP POLICY IF EXISTS products_delete ON public.products;
CREATE POLICY products_delete ON public.products FOR DELETE
  USING (
    CASE WHEN tenant_id IS NULL THEN current_setting('app.is_operator', true) = 'true'
         ELSE tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER END
  );
