-- ADR-1067 段階④ 便④-1: public.inventory_movements に会社ごとの RLS（型A）を付ける。
-- 読む: 自社の会社文脈か運営文脈。書く: 自社の会社文脈だけ。文脈が空なら 0 行（エラーにしない）。
-- 冪等（DROP POLICY IF EXISTS）・1 取引（ENABLE とポリシーの間に全拒否の間を作らない）。design.md §2-1。
BEGIN;
ALTER TABLE public.inventory_movements ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.inventory_movements FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS inventory_movements_select ON public.inventory_movements;
CREATE POLICY inventory_movements_select ON public.inventory_movements FOR SELECT
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
         OR current_setting('app.is_operator', true) = 'true');
DROP POLICY IF EXISTS inventory_movements_insert ON public.inventory_movements;
CREATE POLICY inventory_movements_insert ON public.inventory_movements FOR INSERT
  WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER);
DROP POLICY IF EXISTS inventory_movements_update ON public.inventory_movements;
CREATE POLICY inventory_movements_update ON public.inventory_movements FOR UPDATE
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER)
  WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER);
DROP POLICY IF EXISTS inventory_movements_delete ON public.inventory_movements;
CREATE POLICY inventory_movements_delete ON public.inventory_movements FOR DELETE
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER);
COMMIT;
