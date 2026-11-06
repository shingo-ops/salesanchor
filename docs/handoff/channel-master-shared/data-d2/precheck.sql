-- D2: 名簿に無い値の後始末（PO 2026-11-06）。設計 docs/handoff/channel-master-shared/design.md §9 D2・§3-2。
-- precheck（読み取りだけ）。件数が設計の数と違えばゼロ除算で止まる。
SELECT 1 / (CASE WHEN (SELECT count(*) FROM tenant_001.leads WHERE channel_type='unknown')=1 AND (SELECT count(*) FROM tenant_001.leads WHERE channel_type='unknown' AND id=6)=1 THEN 1 ELSE 0 END) AS t001_unknown_must_be_lead6;
SELECT 1 / (CASE WHEN (SELECT count(*) FROM tenant_004.leads WHERE channel_type='unknown')=54 AND (SELECT count(*) FROM tenant_004.leads WHERE channel_type='unknown' AND id IN (35,36,37,38,96,97,98,99,100,101,102,103,104,105,106,107,108,109,110,111,112,113,114,115,116,117,118,119,120,121,122,123,124,125,126,127,128,129,130,131,132,133,134,135,136,137,138,139,140,141,142,143,144,148))=54 THEN 1 ELSE 0 END) AS t004_unknown_must_be_54;
SELECT 1 / (CASE WHEN (SELECT count(*) FROM tenant_004.conversation_logs WHERE channel_type='meta_messenger' AND id IN (1,3,4))=3 AND (SELECT count(*) FROM tenant_004.conversation_logs WHERE channel_type='meta_messenger')=3 THEN 1 ELSE 0 END) AS t004_log_meta_messenger_must_be_3;
SELECT 1 / (CASE WHEN (SELECT count(*) FROM tenant_006.message_translations)=29 THEN 1 ELSE 0 END) AS t006_message_translations_must_be_29;
SELECT 1 / (CASE WHEN (SELECT count(*) FROM tenant_006.outbound_translation_drafts)=6 THEN 1 ELSE 0 END) AS t006_outbound_translation_drafts_must_be_6;
SELECT 1 / (CASE WHEN (SELECT count(*) FROM tenant_006.meta_messages)=46 THEN 1 ELSE 0 END) AS t006_meta_messages_must_be_46;
SELECT 1 / (CASE WHEN (SELECT count(*) FROM tenant_006.lead_attachments)=11 THEN 1 ELSE 0 END) AS t006_lead_attachments_must_be_11;
SELECT 1 / (CASE WHEN (SELECT count(*) FROM tenant_006.lead_channels)=4 THEN 1 ELSE 0 END) AS t006_lead_channels_must_be_4;
SELECT 1 / (CASE WHEN (SELECT count(*) FROM tenant_006.invoice_items)=1 THEN 1 ELSE 0 END) AS t006_invoice_items_must_be_1;
SELECT 1 / (CASE WHEN (SELECT count(*) FROM tenant_006.invoices)=1 THEN 1 ELSE 0 END) AS t006_invoices_must_be_1;
SELECT 1 / (CASE WHEN (SELECT count(*) FROM tenant_006.quote_items)=1 THEN 1 ELSE 0 END) AS t006_quote_items_must_be_1;
SELECT 1 / (CASE WHEN (SELECT count(*) FROM tenant_006.quotes)=1 THEN 1 ELSE 0 END) AS t006_quotes_must_be_1;
SELECT 1 / (CASE WHEN (SELECT count(*) FROM tenant_006.order_financials)=9 THEN 1 ELSE 0 END) AS t006_order_financials_must_be_9;
SELECT 1 / (CASE WHEN (SELECT count(*) FROM tenant_006.orders)=26 THEN 1 ELSE 0 END) AS t006_orders_must_be_26;
SELECT 1 / (CASE WHEN (SELECT count(*) FROM tenant_006.contacts)=8 THEN 1 ELSE 0 END) AS t006_contacts_must_be_8;
SELECT 1 / (CASE WHEN (SELECT count(*) FROM tenant_006.companies)=30 THEN 1 ELSE 0 END) AS t006_companies_must_be_30;
SELECT 1 / (CASE WHEN (SELECT count(*) FROM tenant_006.leads)=74 THEN 1 ELSE 0 END) AS t006_leads_must_be_74;
SELECT 't006_keep' AS k, (SELECT count(*) FROM tenant_006.staff) staff, (SELECT count(*) FROM tenant_006.roles) roles, (SELECT count(*) FROM tenant_006.goals) goals, (SELECT count(*) FROM tenant_006.products) products, (SELECT count(*) FROM public.users WHERE tenant_id=6) users;
