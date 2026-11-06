-- D2: 名簿に無い値の後始末（PO 2026-11-06）。設計 docs/handoff/channel-master-shared/design.md §9 D2・§3-2。
-- verify（読み取りだけ）。
SELECT 1 / (CASE WHEN (SELECT count(*) FROM tenant_001.leads WHERE id=6 AND channel_type='discord')=1 AND (SELECT count(*) FROM tenant_001.leads WHERE channel_type='unknown')=0 THEN 1 ELSE 0 END) AS t001_done;
SELECT 1 / (CASE WHEN (SELECT count(*) FROM tenant_004.leads WHERE channel_type='messenger' AND id IN (35,36,37,38,96,97,98,99,100,101,102,103,104,105,106,107,108,109,110,111,112,113,114,115,116,117,118,119,120,121,122,123,124,125,126,127,128,129,130,131,132,133,134,135,136,137,138,139,140,141,142,143,144,148))=54 AND (SELECT count(*) FROM tenant_004.leads WHERE channel_type='unknown')=0 AND (SELECT count(*) FROM tenant_004.conversation_logs WHERE channel_type='meta_messenger')=0 THEN 1 ELSE 0 END) AS t004_done;
SELECT 1 / (CASE WHEN (SELECT count(*) FROM tenant_006.message_translations)=0 THEN 1 ELSE 0 END) AS t006_message_translations_empty;
SELECT 1 / (CASE WHEN (SELECT count(*) FROM tenant_006.outbound_translation_drafts)=0 THEN 1 ELSE 0 END) AS t006_outbound_translation_drafts_empty;
SELECT 1 / (CASE WHEN (SELECT count(*) FROM tenant_006.meta_messages)=0 THEN 1 ELSE 0 END) AS t006_meta_messages_empty;
SELECT 1 / (CASE WHEN (SELECT count(*) FROM tenant_006.lead_attachments)=0 THEN 1 ELSE 0 END) AS t006_lead_attachments_empty;
SELECT 1 / (CASE WHEN (SELECT count(*) FROM tenant_006.lead_channels)=0 THEN 1 ELSE 0 END) AS t006_lead_channels_empty;
SELECT 1 / (CASE WHEN (SELECT count(*) FROM tenant_006.invoice_items)=0 THEN 1 ELSE 0 END) AS t006_invoice_items_empty;
SELECT 1 / (CASE WHEN (SELECT count(*) FROM tenant_006.invoices)=0 THEN 1 ELSE 0 END) AS t006_invoices_empty;
SELECT 1 / (CASE WHEN (SELECT count(*) FROM tenant_006.quote_items)=0 THEN 1 ELSE 0 END) AS t006_quote_items_empty;
SELECT 1 / (CASE WHEN (SELECT count(*) FROM tenant_006.quotes)=0 THEN 1 ELSE 0 END) AS t006_quotes_empty;
SELECT 1 / (CASE WHEN (SELECT count(*) FROM tenant_006.order_financials)=0 THEN 1 ELSE 0 END) AS t006_order_financials_empty;
SELECT 1 / (CASE WHEN (SELECT count(*) FROM tenant_006.orders)=0 THEN 1 ELSE 0 END) AS t006_orders_empty;
SELECT 1 / (CASE WHEN (SELECT count(*) FROM tenant_006.contacts)=0 THEN 1 ELSE 0 END) AS t006_contacts_empty;
SELECT 1 / (CASE WHEN (SELECT count(*) FROM tenant_006.companies)=0 THEN 1 ELSE 0 END) AS t006_companies_empty;
SELECT 1 / (CASE WHEN (SELECT count(*) FROM tenant_006.leads)=0 THEN 1 ELSE 0 END) AS t006_leads_empty;
SELECT 1 / (CASE WHEN (SELECT count(*) FROM tenant_006.staff)=4 AND (SELECT count(*) FROM tenant_006.roles)=7 AND (SELECT count(*) FROM public.users WHERE tenant_id=6)=5 THEN 1 ELSE 0 END) AS t006_staff_kept;
