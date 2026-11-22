-- 会社006（審査用）に Meta 審査用の印を付ける（ADR-1055 What 11）。設計 docs/handoff/auth-new-device-approval/review-exempt-design.md 3-10。
-- 会社は code と名前の2つで当てる。番号は書かない。
-- commit（1行でなければ 0 で割って止まり、何も残らない）。
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL app.is_operator = 'true';
UPDATE public.tenants SET meta_review_tenant = true WHERE tenant_code = 'tenant-review' AND tenant_name = 'Sales Anchor App Review' AND meta_review_tenant = false RETURNING id, tenant_code, tenant_name;
SELECT 1 / (CASE WHEN (SELECT count(*) FROM public.tenants WHERE tenant_code = 'tenant-review' AND tenant_name = 'Sales Anchor App Review' AND meta_review_tenant AND meta_review_login_until IS NULL)=1 AND (SELECT count(*) FROM public.tenants WHERE meta_review_tenant)=1 THEN 1 ELSE 0 END) AS marked_one;
COMMIT;
