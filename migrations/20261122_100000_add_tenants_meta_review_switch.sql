-- ADR-1055 What 11: Meta 審査用の会社（会社006）だけのログインのスイッチ。ほかの会社に広げない。
-- 列を足すだけ。値は書かない（印は本番のデータの変更で1回だけ付ける。設計 3-10）。何度流しても同じになる。
ALTER TABLE public.tenants ADD COLUMN IF NOT EXISTS meta_review_tenant BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE public.tenants ADD COLUMN IF NOT EXISTS meta_review_login_until TIMESTAMPTZ NULL;
DO $meta_review$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
     WHERE conrelid = 'public.tenants'::regclass AND conname = 'tenants_meta_review_until_needs_marker'
  ) THEN
    ALTER TABLE public.tenants
      ADD CONSTRAINT tenants_meta_review_until_needs_marker
      CHECK (meta_review_login_until IS NULL OR meta_review_tenant);
  END IF;
END
$meta_review$;
CREATE UNIQUE INDEX IF NOT EXISTS tenants_meta_review_one_marker
  ON public.tenants ((meta_review_tenant)) WHERE meta_review_tenant;
COMMENT ON COLUMN public.tenants.meta_review_tenant IS
  'Meta 審査用の会社の印（ADR-1055 What 11）。1社だけ。ほかの会社に広げない';
COMMENT ON COLUMN public.tenants.meta_review_login_until IS
  'Meta 審査用のスイッチ。今より後なら ON（最長14日）。NULL か過去なら OFF';
-- 戻し方: ALTER TABLE public.tenants DROP CONSTRAINT IF EXISTS tenants_meta_review_until_needs_marker;
--         DROP INDEX IF EXISTS public.tenants_meta_review_one_marker;
--         ALTER TABLE public.tenants DROP COLUMN IF EXISTS meta_review_login_until, DROP COLUMN IF EXISTS meta_review_tenant;
