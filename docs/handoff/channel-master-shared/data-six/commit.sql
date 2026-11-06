-- 共用6行の投入 commit（PO の同意の後だけ）。設計 design.md §3。数が違えばゼロ除算で失敗し、COMMIT に届かない。
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL app.is_operator = 'true';
INSERT INTO public.channel_masters (tenant_id, platform, display_name, connection_type, conversation_store, is_verbatim, conversion_item) VALUES
  (NULL, 'messenger', 'Messenger', 'auto',   'meta_messages',     TRUE,  'baseline'),
  (NULL, 'instagram', 'Instagram', 'auto',   'meta_messages',     TRUE,  'channel_instagram'),
  (NULL, 'discord',   'Discord',   'auto',   'meta_messages',     TRUE,  NULL),
  (NULL, 'phone',     '電話',      'manual', 'conversation_logs', FALSE, NULL),
  (NULL, 'in_person', '対面',      'manual', 'conversation_logs', FALSE, NULL),
  (NULL, 'whatsapp',  'WhatsApp',  'manual', 'conversation_logs', TRUE,  'channel_whatsapp')
ON CONFLICT DO NOTHING;
SELECT 1 / (CASE WHEN (SELECT count(*) FROM public.channel_masters WHERE tenant_id IS NULL AND is_active)=6
  AND (SELECT count(*) FROM public.channel_masters WHERE tenant_id IS NOT NULL)=0 THEN 1 ELSE 0 END) AS shared_must_be_6;
COMMIT;
