-- ADR-1067 段階④ 便④-2: public.discord_server_snapshots と public.discord_server_apply_runs に会社ごとの RLS（型A）を付ける。
-- 読む: 自社の会社文脈か運営文脈。書く: 自社の会社文脈だけ。文脈が空なら 0 行（エラーにしない）。
-- 冪等（DROP POLICY IF EXISTS）・1 取引（ENABLE とポリシーの間に全拒否の間を作らない）。design.md §2-1。
BEGIN;
ALTER TABLE public.discord_server_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.discord_server_snapshots FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS discord_server_snapshots_select ON public.discord_server_snapshots;
CREATE POLICY discord_server_snapshots_select ON public.discord_server_snapshots FOR SELECT
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
         OR current_setting('app.is_operator', true) = 'true');
DROP POLICY IF EXISTS discord_server_snapshots_insert ON public.discord_server_snapshots;
CREATE POLICY discord_server_snapshots_insert ON public.discord_server_snapshots FOR INSERT
  WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER);
DROP POLICY IF EXISTS discord_server_snapshots_update ON public.discord_server_snapshots;
CREATE POLICY discord_server_snapshots_update ON public.discord_server_snapshots FOR UPDATE
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER)
  WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER);
DROP POLICY IF EXISTS discord_server_snapshots_delete ON public.discord_server_snapshots;
CREATE POLICY discord_server_snapshots_delete ON public.discord_server_snapshots FOR DELETE
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER);
ALTER TABLE public.discord_server_apply_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.discord_server_apply_runs FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS discord_server_apply_runs_select ON public.discord_server_apply_runs;
CREATE POLICY discord_server_apply_runs_select ON public.discord_server_apply_runs FOR SELECT
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
         OR current_setting('app.is_operator', true) = 'true');
DROP POLICY IF EXISTS discord_server_apply_runs_insert ON public.discord_server_apply_runs;
CREATE POLICY discord_server_apply_runs_insert ON public.discord_server_apply_runs FOR INSERT
  WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER);
DROP POLICY IF EXISTS discord_server_apply_runs_update ON public.discord_server_apply_runs;
CREATE POLICY discord_server_apply_runs_update ON public.discord_server_apply_runs FOR UPDATE
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER)
  WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER);
DROP POLICY IF EXISTS discord_server_apply_runs_delete ON public.discord_server_apply_runs;
CREATE POLICY discord_server_apply_runs_delete ON public.discord_server_apply_runs FOR DELETE
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER);
COMMIT;
