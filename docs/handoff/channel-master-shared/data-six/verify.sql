-- 共用6行の投入 verify（読み取りだけ）。設計 design.md §3。
SELECT 1 / (CASE WHEN (SELECT count(*) FROM public.channel_masters WHERE tenant_id IS NULL AND is_active)=6
  AND (SELECT count(*) FROM public.channel_masters WHERE tenant_id IS NOT NULL)=0
  AND (SELECT count(*) FROM public.channel_masters WHERE tenant_id IS NULL AND (platform, display_name, connection_type, conversation_store, is_verbatim, COALESCE(conversion_item,'-')) IN (
    ('messenger','Messenger','auto','meta_messages',TRUE,'baseline'),
    ('instagram','Instagram','auto','meta_messages',TRUE,'channel_instagram'),
    ('discord','Discord','auto','meta_messages',TRUE,'-'),
    ('phone','電話','manual','conversation_logs',FALSE,'-'),
    ('in_person','対面','manual','conversation_logs',FALSE,'-'),
    ('whatsapp','WhatsApp','manual','conversation_logs',TRUE,'channel_whatsapp')))=6 THEN 1 ELSE 0 END) AS shared_6_match_design;
SELECT id, platform, display_name, connection_type, conversation_store, is_verbatim, conversion_item, is_active FROM public.channel_masters ORDER BY id;
