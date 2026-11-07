-- 会話の一本化 便1: 名簿の会話の置き場を meta_messages にそろえる（PO 2026-11-07「1」K6〜K9）。設計 docs/handoff/conversation-unification/design.md §4 便1・card-bin1.md §11。
-- dryrun（試して必ず ROLLBACK する）。
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL app.is_operator = 'true';
UPDATE public.channel_masters SET conversation_store='meta_messages', updated_at=now() WHERE id IN (10,11,12) AND tenant_id IS NULL AND conversation_store='conversation_logs';
SELECT 1 / (CASE WHEN (SELECT count(*) FROM public.channel_masters WHERE tenant_id IS NULL AND id IN (7,8,9,10,11,12) AND conversation_store='meta_messages')=6 AND (SELECT count(*) FROM public.channel_masters WHERE tenant_id IS NULL AND conversation_store='conversation_logs')=0 THEN 1 ELSE 0 END) AS all_six_must_be_meta;
ROLLBACK;
