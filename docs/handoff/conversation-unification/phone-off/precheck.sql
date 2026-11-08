-- 名簿から電話・対面を外す（PO 2026-11-08「3」全社の名簿から外す）。設計 docs/handoff/conversation-unification/phone-off/design.md。
-- precheck（読み取りだけ）。名簿が設計の形と違えばゼロ除算で止まる。
SELECT 1 / (CASE WHEN (SELECT count(*) FROM public.channel_masters WHERE tenant_id IS NULL)=6 THEN 1 ELSE 0 END) AS shared_must_be_6;
SELECT 1 / (CASE WHEN (SELECT count(*) FROM public.channel_masters WHERE tenant_id IS NULL AND is_active=true AND id IN (10,11) AND platform IN ('phone','in_person'))=2 THEN 1 ELSE 0 END) AS ids_10_11_must_be_active;
SELECT 1 / (CASE WHEN (SELECT count(*) FROM public.channel_masters WHERE tenant_id IS NULL AND is_active=true AND id IN (7,8,9,12))=4 THEN 1 ELSE 0 END) AS ids_7_8_9_12_must_be_active;
SELECT 1 / (CASE WHEN (SELECT count(*) FROM public.channel_masters WHERE tenant_id IS NULL AND id IN (10,11) AND conversion_item IS NULL)=2 THEN 1 ELSE 0 END) AS ids_10_11_no_conversion_item;
SELECT id, tenant_id, platform, display_name, is_active, updated_at FROM public.channel_masters ORDER BY id;
