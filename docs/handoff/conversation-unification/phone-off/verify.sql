-- 名簿から電話・対面を外す（PO 2026-11-08「3」全社の名簿から外す）。設計 docs/handoff/conversation-unification/phone-off/design.md。
-- verify（読み取りだけ）。
SELECT 1 / (CASE WHEN (SELECT count(*) FROM public.channel_masters WHERE tenant_id IS NULL)=6 AND (SELECT count(*) FROM public.channel_masters WHERE tenant_id IS NULL AND is_active=true)=4 AND (SELECT count(*) FROM public.channel_masters WHERE tenant_id IS NULL AND is_active=false AND id IN (10,11))=2 THEN 1 ELSE 0 END) AS phone_in_person_off;
SELECT id, tenant_id, platform, display_name, is_active, updated_at FROM public.channel_masters ORDER BY id;
