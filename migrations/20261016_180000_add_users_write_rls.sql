-- S1 段階③便C（ADR-1018）: public.users に「書込だけ RLS」
-- 読取は全行可（ログイン・パスワード再設定・get_current_user が文脈なしで users を引くため）。
-- 書込（INSERT / UPDATE / DELETE）は、書く行の tenant_id と会社文脈（app.tenant_id）が一致するとき、
-- または運営文脈（app.is_operator = 'true'）のときだけ。文脈なしは NULL/偽となり拒否（フェイルクローズ）。冪等。

ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.users FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS users_select ON public.users;
CREATE POLICY users_select ON public.users FOR SELECT USING (true);

DROP POLICY IF EXISTS users_insert ON public.users;
CREATE POLICY users_insert ON public.users FOR INSERT
  WITH CHECK (
    tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
    OR current_setting('app.is_operator', true) = 'true'
  );

DROP POLICY IF EXISTS users_update ON public.users;
CREATE POLICY users_update ON public.users FOR UPDATE
  USING (
    tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
    OR current_setting('app.is_operator', true) = 'true'
  )
  WITH CHECK (
    tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
    OR current_setting('app.is_operator', true) = 'true'
  );

DROP POLICY IF EXISTS users_delete ON public.users;
CREATE POLICY users_delete ON public.users FOR DELETE
  USING (
    tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
    OR current_setting('app.is_operator', true) = 'true'
  );
