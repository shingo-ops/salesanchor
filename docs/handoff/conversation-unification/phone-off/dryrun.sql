-- 名簿から電話・対面を外す（PO 2026-11-08「3」全社の名簿から外す）。設計 docs/handoff/conversation-unification/phone-off/design.md。
-- dryrun（試して必ず ROLLBACK する）。
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL app.is_operator = 'true';
UPDATE public.channel_masters SET is_active=false, updated_at=now() WHERE id IN (10,11) AND tenant_id IS NULL AND platform IN ('phone','in_person') AND is_active=true;
SELECT 1 / (CASE WHEN (SELECT count(*) FROM public.channel_masters WHERE tenant_id IS NULL)=6 AND (SELECT count(*) FROM public.channel_masters WHERE tenant_id IS NULL AND is_active=true)=4 AND (SELECT count(*) FROM public.channel_masters WHERE tenant_id IS NULL AND is_active=false AND id IN (10,11))=2 THEN 1 ELSE 0 END) AS phone_in_person_off;
ROLLBACK;
