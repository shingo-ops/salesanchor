-- S1 段階③便B（ADR-1018）: public.tenants に「書込だけ RLS」
-- 読取は全行可（Celery・認証前の読取が文脈なしで全行を引くため）。
-- 書込（INSERT / UPDATE / DELETE）は運営文脈（app.is_operator = 'true'）のときだけ。
-- 会社の利用者が tenants に書くアプリ経路は無い。文脈なし・会社文脈は偽/NULL となり拒否（フェイルクローズ）。冪等。

ALTER TABLE public.tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tenants FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenants_select ON public.tenants;
CREATE POLICY tenants_select ON public.tenants FOR SELECT USING (true);

DROP POLICY IF EXISTS tenants_insert ON public.tenants;
CREATE POLICY tenants_insert ON public.tenants FOR INSERT
  WITH CHECK (current_setting('app.is_operator', true) = 'true');

DROP POLICY IF EXISTS tenants_update ON public.tenants;
CREATE POLICY tenants_update ON public.tenants FOR UPDATE
  USING      (current_setting('app.is_operator', true) = 'true')
  WITH CHECK (current_setting('app.is_operator', true) = 'true');

DROP POLICY IF EXISTS tenants_delete ON public.tenants;
CREATE POLICY tenants_delete ON public.tenants FOR DELETE
  USING (current_setting('app.is_operator', true) = 'true');
