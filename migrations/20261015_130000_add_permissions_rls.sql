-- S1 段階①（ADR-1018）: public.permissions をアプリ接続から読み取り専用にする
ALTER TABLE public.permissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.permissions FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS permissions_read ON public.permissions;
CREATE POLICY permissions_read ON public.permissions
    FOR SELECT USING (true);

DROP POLICY IF EXISTS permissions_operator_write ON public.permissions;
CREATE POLICY permissions_operator_write ON public.permissions
    FOR ALL
    USING (current_setting('app.is_operator', true) = 'true')
    WITH CHECK (current_setting('app.is_operator', true) = 'true');
