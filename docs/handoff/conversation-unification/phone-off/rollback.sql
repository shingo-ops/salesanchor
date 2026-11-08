-- 名簿から電話・対面を外す（PO 2026-11-08「3」全社の名簿から外す）。設計 docs/handoff/conversation-unification/phone-off/design.md。
-- rollback（id 10・11 を is_active=true に戻す）。
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL app.is_operator = 'true';
UPDATE public.channel_masters SET is_active=true, updated_at=now() WHERE id IN (10,11) AND tenant_id IS NULL AND platform IN ('phone','in_person') AND is_active=false;
SELECT 1 / (CASE WHEN (SELECT count(*) FROM public.channel_masters WHERE tenant_id IS NULL AND is_active=true)=6 THEN 1 ELSE 0 END) AS restored;
COMMIT;
