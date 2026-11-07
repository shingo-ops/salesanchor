-- 会話の一本化 便1: 名簿の会話の置き場を meta_messages にそろえる（PO 2026-11-07「1」K6〜K9）。設計 docs/handoff/conversation-unification/design.md §4 便1・card-bin1.md §11。
-- precheck（読み取りだけ）。名簿が設計の形と違えばゼロ除算で止まる。
SELECT 1 / (CASE WHEN (SELECT count(*) FROM public.channel_masters)=6 THEN 1 ELSE 0 END) AS total_must_be_6;
SELECT 1 / (CASE WHEN (SELECT count(*) FROM public.channel_masters WHERE tenant_id IS NULL AND conversation_store='meta_messages' AND id IN (7,8,9) AND platform IN ('messenger','instagram','discord'))=3 THEN 1 ELSE 0 END) AS ids_7_8_9_must_be_meta;
SELECT 1 / (CASE WHEN (SELECT count(*) FROM public.channel_masters WHERE tenant_id IS NULL AND conversation_store='conversation_logs' AND id IN (10,11,12) AND platform IN ('phone','in_person','whatsapp'))=3 THEN 1 ELSE 0 END) AS ids_10_11_12_must_be_logs;
SELECT id, platform, conversation_store, updated_at FROM public.channel_masters ORDER BY id;
