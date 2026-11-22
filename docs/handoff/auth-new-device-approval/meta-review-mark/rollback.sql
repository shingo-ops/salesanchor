-- 会社006（審査用）に Meta 審査用の印を付ける（ADR-1055 What 11）。設計 docs/handoff/auth-new-device-approval/review-exempt-design.md 3-10。
-- rollback（印とスイッチを外す。設計 3-10 の戻し）。
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL app.is_operator = 'true';
UPDATE public.tenants SET meta_review_login_until = NULL, meta_review_tenant = false WHERE meta_review_tenant RETURNING id, tenant_code, tenant_name;
SELECT 1 / (CASE WHEN (SELECT count(*) FROM public.tenants WHERE meta_review_tenant)=0 THEN 1 ELSE 0 END) AS unmarked;
COMMIT;
