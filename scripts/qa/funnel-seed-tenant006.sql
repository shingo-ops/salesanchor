-- ============================================================================
-- Funnel dashboard stage1 seed for tenant_006 only
--
-- Scope:
--   - tenant_006 schema only
--   - app.tenant_id = 6 is required for RLS-protected tables
--
-- Purpose:
--   Rebuild the funnel dashboard known state idempotently by removing the
--   existing tenant_006 funnel rows in FK-safe order, then reinserting the
--   expected rows with relative timestamps.
--
-- Preconditions:
--   - tenant_id=6 maps to tenant_code='tenant-review'
-- ============================================================================

\set ON_ERROR_STOP on
\set TENANT_ID 6
\set TENANT_CODE '''tenant-review'''
\set SCHEMA tenant_006

BEGIN;

-- ---------------------------------------------------------------------------
-- 1. RLS context for tenant_006
-- ---------------------------------------------------------------------------
SET app.tenant_id = '6';
SET search_path = tenant_006;

-- ---------------------------------------------------------------------------
-- 2. Cleanup existing funnel rows in FK-safe order
--    only tenant_006 schema is touched.
-- ---------------------------------------------------------------------------
UPDATE tenant_006.leads
   SET converted_deal_id = NULL
 WHERE lead_code LIKE 'QA-FN-LD-%'
   AND converted_deal_id IS NOT NULL;

UPDATE tenant_006.companies
   SET lead_id = NULL
 WHERE (company_code LIKE 'QA-CO-%' OR company_code LIKE 'QA-FN-CO-%')
   AND lead_id IS NOT NULL;

DELETE FROM tenant_006.deal_close_reasons
 WHERE deal_id IN (
       SELECT id FROM tenant_006.deals WHERE deal_code LIKE 'QA-FN-D%'
   );

DELETE FROM tenant_006.order_financials
 WHERE order_id IN (
       SELECT id FROM tenant_006.orders WHERE order_number LIKE 'QA-FN-OR-%'
   );

DELETE FROM tenant_006.goals
 WHERE period_type = 'monthly'
   AND period_year = 2026
   AND period_num = 6
   AND team_id IN (
       SELECT id FROM tenant_006.teams WHERE name = 'QA営業チーム'
   );

DELETE FROM tenant_006.meta_messages
 WHERE message_id LIKE 'qa-%';

DELETE FROM tenant_006.contacts
 WHERE contact_code LIKE 'QA-CT-%';

DELETE FROM tenant_006.orders
 WHERE order_number LIKE 'QA-FN-OR-%';

DELETE FROM tenant_006.deals
 WHERE deal_code LIKE 'QA-FN-D%';

DELETE FROM tenant_006.companies
 WHERE company_code LIKE 'QA-CO-%'
    OR company_code LIKE 'QA-FN-CO-%';

DELETE FROM tenant_006.leads
 WHERE lead_code LIKE 'QA-LD-%'
    OR lead_code LIKE 'QA-FN-LD-%';

DELETE FROM tenant_006.products
 WHERE product_code LIKE 'QA-PR-%';

-- ---------------------------------------------------------------------------
-- 3. Teams
-- ---------------------------------------------------------------------------
INSERT INTO tenant_006.teams (tenant_id, name)
VALUES (6, 'QA営業チーム')
ON CONFLICT (tenant_id, name) DO NOTHING;

-- ---------------------------------------------------------------------------
-- 4. Leads
-- ---------------------------------------------------------------------------
INSERT INTO tenant_006.leads (
    tenant_id, lead_code, customer_name, company_name, email, status,
    ai_collection_state, created_at
)
VALUES
    (6, 'QA-LD-001', 'QA Lead New',       'QA Company A', 'qa-lead-new@example.com',       'lead',              'completed', NOW() - INTERVAL '400 days'),
    (6, 'QA-LD-002', 'QA Lead Contacted',  'QA Company B', 'qa-lead-contacted@example.com',  'negotiating',       'completed', NOW() - INTERVAL '399 days'),
    (6, 'QA-LD-003', 'QA Lead Qualified',  'QA Company C', 'qa-lead-qualified@example.com',  'existing_customer', 'completed', NOW() - INTERVAL '398 days'),
    (6, 'QA-LD-004', 'QA Lead Lost',       'QA Company D', 'qa-lead-lost@example.com',       'lost',              'completed', NOW() - INTERVAL '397 days'),
    (6, 'QA-LD-005', 'QA Lead Won',        'QA Company E', 'qa-lead-won@example.com',        'existing_customer', 'completed', NOW() - INTERVAL '396 days');

INSERT INTO tenant_006.leads (
    tenant_id, lead_code, customer_name, company_name, email, initiative,
    channel_type, status, ai_collection_state, created_at
)
VALUES
    (6, 'QA-FN-LD-001', 'FN リードIG1',  'FN社IG1',  'qa-fn-ld-001@example.com', 'inbound',  'instagram', 'existing_customer', 'completed', NOW() - INTERVAL '12 days'),
    (6, 'QA-FN-LD-002', 'FN リードIG2',  'FN社IG2',  'qa-fn-ld-002@example.com', 'inbound',  'instagram', 'existing_customer', 'completed', NOW() - INTERVAL '11 days'),
    (6, 'QA-FN-LD-003', 'FN リードIG3',  'FN社IG3',  'qa-fn-ld-003@example.com', 'inbound',  'instagram', 'lost',              'completed', NOW() - INTERVAL '10 days'),
    (6, 'QA-FN-LD-004', 'FN リードIG4',  'FN社IG4',  'qa-fn-ld-004@example.com', 'inbound',  'instagram', 'negotiating',       'completed', NOW() - INTERVAL '9 days'),
    (6, 'QA-FN-LD-005', 'FN リードIG5',  'FN社IG5',  'qa-fn-ld-005@example.com', 'inbound',  'instagram', 'lead',              'completed', NOW() - INTERVAL '8 days'),
    (6, 'QA-FN-LD-006', 'FN リードIG6',  'FN社IG6',  'qa-fn-ld-006@example.com', 'inbound',  'instagram', 'lead',              'completed', NOW() - INTERVAL '7 days'),
    (6, 'QA-FN-LD-007', 'FN リードIG7',  'FN社IG7',  'qa-fn-ld-007@example.com', 'inbound',  'instagram', 'lead',              'completed', NOW() - INTERVAL '6 days'),
    (6, 'QA-FN-LD-008', 'FN リードIG8',  'FN社IG8',  'qa-fn-ld-008@example.com', 'inbound',  'instagram', 'lead',              'completed', NOW() - INTERVAL '5 days'),
    (6, 'QA-FN-LD-009', 'FN リードMS1',  'FN社MS1',  'qa-fn-ld-009@example.com', 'inbound',  'messenger', 'existing_customer', 'completed', NOW() - INTERVAL '13 days'),
    (6, 'QA-FN-LD-010', 'FN リードMS2',  'FN社MS2',  'qa-fn-ld-010@example.com', 'inbound',  'messenger', 'negotiating',       'completed', NOW() - INTERVAL '12 days'),
    (6, 'QA-FN-LD-011', 'FN リードMS3',  'FN社MS3',  'qa-fn-ld-011@example.com', 'inbound',  'messenger', 'lead',              'completed', NOW() - INTERVAL '11 days'),
    (6, 'QA-FN-LD-012', 'FN リードMS4',  'FN社MS4',  'qa-fn-ld-012@example.com', 'inbound',  'messenger', 'lead',              'completed', NOW() - INTERVAL '10 days'),
    (6, 'QA-FN-LD-013', 'FN リードMS5',  'FN社MS5',  'qa-fn-ld-013@example.com', 'inbound',  'messenger', 'lead',              'completed', NOW() - INTERVAL '9 days'),
    (6, 'QA-FN-LD-014', 'FN リードMS6',  'FN社MS6',  'qa-fn-ld-014@example.com', 'inbound',  'messenger', 'lead',              'completed', NOW() - INTERVAL '8 days'),
    (6, 'QA-FN-LD-015', 'FN リードEM1',  'FN社EM1',  'qa-fn-ld-015@example.com', 'outbound', 'email',     'existing_customer', 'completed', NOW() - INTERVAL '14 days'),
    (6, 'QA-FN-LD-016', 'FN リードEM2',  'FN社EM2',  'qa-fn-ld-016@example.com', 'outbound', 'email',     'lost',              'completed', NOW() - INTERVAL '13 days'),
    (6, 'QA-FN-LD-017', 'FN リードEM3',  'FN社EM3',  'qa-fn-ld-017@example.com', 'outbound', 'email',     'lead',              'completed', NOW() - INTERVAL '12 days'),
    (6, 'QA-FN-LD-018', 'FN リードEM4',  'FN社EM4',  'qa-fn-ld-018@example.com', 'outbound', 'email',     'lead',              'completed', NOW() - INTERVAL '11 days'),
    (6, 'QA-FN-LD-019', 'FN リードEM5',  'FN社EM5',  'qa-fn-ld-019@example.com', 'outbound', 'email',     'lead',              'completed', NOW() - INTERVAL '10 days'),
    (6, 'QA-FN-LD-020', 'FN リードEM6',  'FN社EM6',  'qa-fn-ld-020@example.com', 'outbound', 'email',     'lead',              'completed', NOW() - INTERVAL '9 days');

-- ---------------------------------------------------------------------------
-- 5. Companies / Contacts / Products
-- ---------------------------------------------------------------------------
INSERT INTO tenant_006.companies (tenant_id, company_code, lead_id, name, name_en, industry, status)
SELECT 6, 'QA-CO-001', l.id, 'QA Company A', 'QA Company A Ltd.', 'B2B EC', 'active' FROM tenant_006.leads l WHERE l.lead_code = 'QA-LD-001';
INSERT INTO tenant_006.companies (tenant_id, company_code, lead_id, name, name_en, industry, status)
SELECT 6, 'QA-CO-002', l.id, 'QA Company B', 'QA Company B Ltd.', 'B2B EC', 'active' FROM tenant_006.leads l WHERE l.lead_code = 'QA-LD-002';
INSERT INTO tenant_006.companies (tenant_id, company_code, lead_id, name, name_en, industry, status)
SELECT 6, 'QA-CO-003', l.id, 'QA Company C', 'QA Company C Ltd.', 'B2B EC', 'active' FROM tenant_006.leads l WHERE l.lead_code = 'QA-LD-003';
INSERT INTO tenant_006.companies (tenant_id, company_code, lead_id, name, name_en, industry, status)
SELECT 6, 'QA-CO-004', l.id, 'QA Company D', 'QA Company D Ltd.', 'B2B EC', 'active' FROM tenant_006.leads l WHERE l.lead_code = 'QA-LD-004';
INSERT INTO tenant_006.companies (tenant_id, company_code, lead_id, name, name_en, industry, status)
SELECT 6, 'QA-CO-005', l.id, 'QA Company E', 'QA Company E Ltd.', 'B2B EC', 'active' FROM tenant_006.leads l WHERE l.lead_code = 'QA-LD-005';

INSERT INTO tenant_006.companies (tenant_id, company_code, name, industry, status) VALUES
    (6, 'QA-FN-CO-D01', 'FN社D01 instagram', 'B2B', 'active'),
    (6, 'QA-FN-CO-D02', 'FN社D02 instagram', 'B2B', 'active'),
    (6, 'QA-FN-CO-D03', 'FN社D03 instagram', 'B2B', 'active'),
    (6, 'QA-FN-CO-D04', 'FN社D04 instagram', 'B2B', 'active'),
    (6, 'QA-FN-CO-D05', 'FN社D05 messenger', 'B2B', 'active'),
    (6, 'QA-FN-CO-D06', 'FN社D06 messenger', 'B2B', 'active'),
    (6, 'QA-FN-CO-D07', 'FN社D07 email',     'B2B', 'active'),
    (6, 'QA-FN-CO-D08', 'FN社D08 email',     'B2B', 'active'),
    (6, 'QA-FN-CO-D09', 'FN社D09 active',    'B2B', 'active'),
    (6, 'QA-FN-CO-D10', 'FN社D10 active',    'B2B', 'active'),
    (6, 'QA-FN-CO-D11', 'FN社D11 active',    'B2B', 'active'),
    (6, 'QA-FN-CO-D12', 'FN社D12 won-noorder','B2B', 'active'),
    (6, 'QA-FN-CO-ON1', 'FN新規社ON1',      'B2B', 'active'),
    (6, 'QA-FN-CO-ON2', 'FN新規社ON2',      'B2B', 'active'),
    (6, 'QA-FN-CO-ON3', 'FN新規社ON3',      'B2B', 'active'),
    (6, 'QA-FN-CO-OR1', 'FN既存社OR1',      'B2B', 'active'),
    (6, 'QA-FN-CO-OR2', 'FN既存社OR2',      'B2B', 'active'),
    (6, 'QA-FN-CO-OR3', 'FN既存社OR3',      'B2B', 'active'),
    (6, 'QA-FN-CO-OR4', 'FN既存社OR4',      'B2B', 'active'),
    (6, 'QA-FN-CO-FS1', 'FN発注停止社FS1',   'B2B', 'active'),
    (6, 'QA-FN-CO-FS2', 'FN発注停止社FS2',   'B2B', 'active'),
    (6, 'QA-FN-CO-FN1', 'FN初回未フォロー社FN1', 'B2B', 'active');

INSERT INTO tenant_006.contacts (tenant_id, company_id, contact_code, lead_id, display_name, primary_email, status)
SELECT 6, c.id, 'QA-CT-001', c.lead_id, 'QA Contact A', 'qa-contact-a@example.com', 'active' FROM tenant_006.companies c WHERE c.company_code = 'QA-CO-001';
INSERT INTO tenant_006.contacts (tenant_id, company_id, contact_code, lead_id, display_name, primary_email, status)
SELECT 6, c.id, 'QA-CT-002', c.lead_id, 'QA Contact B', 'qa-contact-b@example.com', 'active' FROM tenant_006.companies c WHERE c.company_code = 'QA-CO-002';
INSERT INTO tenant_006.contacts (tenant_id, company_id, contact_code, lead_id, display_name, primary_email, status)
SELECT 6, c.id, 'QA-CT-003', c.lead_id, 'QA Contact C', 'qa-contact-c@example.com', 'active' FROM tenant_006.companies c WHERE c.company_code = 'QA-CO-003';
INSERT INTO tenant_006.contacts (tenant_id, company_id, contact_code, lead_id, display_name, primary_email, status)
SELECT 6, c.id, 'QA-CT-004', c.lead_id, 'QA Contact D', 'qa-contact-d@example.com', 'active' FROM tenant_006.companies c WHERE c.company_code = 'QA-CO-004';
INSERT INTO tenant_006.contacts (tenant_id, company_id, contact_code, lead_id, display_name, primary_email, status)
SELECT 6, c.id, 'QA-CT-005', c.lead_id, 'QA Contact E', 'qa-contact-e@example.com', 'active' FROM tenant_006.companies c WHERE c.company_code = 'QA-CO-005';

INSERT INTO tenant_006.products (tenant_id, product_code, category, name_ja, name_en, status, unit_price, quantity)
VALUES
    (6, 'QA-PR-001', 'TCG-pokemon', 'QA ポケモンカードA', 'QA Pokemon Card A',  'active', 1500.00, 10),
    (6, 'QA-PR-002', 'TCG-yugioh',  'QA 遊戯王カードB',   'QA Yu-Gi-Oh Card B', 'active', 2300.00, 5),
    (6, 'QA-PR-003', 'manga',       'QA 漫画C',           'QA Manga C',         'active',  880.00, 20),
    (6, 'QA-PR-004', 'figure',      'QA フィギュアD',     'QA Figure D',        'active', 4500.00, 3),
    (6, 'QA-PR-005', 'game',        'QA ゲームE',         'QA Game E',          'active', 6800.00, 7);

-- ---------------------------------------------------------------------------
-- 6. Meta messages
-- ---------------------------------------------------------------------------
INSERT INTO tenant_006.meta_messages (
    tenant_id, lead_id, platform, sender_id, sender_name, message_text,
    direction, message_id, raw_payload
)
SELECT 6, l.id, 'messenger', 'QA-PSID-001', 'QA Sender 1', 'Hello, do you ship to JP?', 'inbound',
       'qa-mid.' || repeat('a', 12), jsonb_build_object('platform','messenger','test',TRUE)
FROM tenant_006.leads l WHERE l.lead_code = 'QA-LD-001';

INSERT INTO tenant_006.meta_messages (
    tenant_id, lead_id, platform, sender_id, sender_name, message_text,
    direction, message_id, raw_payload
)
SELECT 6, l.id, 'messenger', 'QA-PSID-002', 'QA Sender 2', 'I have a question about pricing', 'inbound',
       'qa-mid.' || repeat('b', 14), jsonb_build_object('platform','messenger','test',TRUE)
FROM tenant_006.leads l WHERE l.lead_code = 'QA-LD-002';

INSERT INTO tenant_006.meta_messages (
    tenant_id, lead_id, platform, sender_id, sender_name, message_text,
    direction, message_id, raw_payload
)
SELECT 6, l.id, 'messenger', 'QA-PSID-001', 'QA Sender 1', 'Sure, we ship worldwide via FedEx', 'outbound',
       'qa-mid.' || repeat('c', 16), jsonb_build_object('platform','messenger','test',TRUE)
FROM tenant_006.leads l WHERE l.lead_code = 'QA-LD-001';

INSERT INTO tenant_006.meta_messages (
    tenant_id, lead_id, platform, sender_id, sender_name, message_text,
    direction, message_id, raw_payload
)
SELECT 6, l.id, 'messenger', 'QA-PSID-003', 'QA Sender 3', 'Order confirmation?', 'inbound',
       'qa-mid.' || repeat('d', 18), jsonb_build_object('platform','messenger','test',TRUE)
FROM tenant_006.leads l WHERE l.lead_code = 'QA-LD-002';

INSERT INTO tenant_006.meta_messages (
    tenant_id, lead_id, platform, sender_id, sender_name, message_text,
    direction, message_id, raw_payload
)
SELECT 6, l.id, 'messenger', 'QA-PSID-004', 'QA Sender 4', 'Got the tracking number, thanks', 'inbound',
       'qa-mid.' || repeat('e', 20), jsonb_build_object('platform','messenger','test',TRUE)
FROM tenant_006.leads l WHERE l.lead_code = 'QA-LD-003';

INSERT INTO tenant_006.meta_messages (
    tenant_id, lead_id, platform, sender_id, sender_name, message_text,
    direction, message_id, raw_payload
)
SELECT 6, l.id, 'messenger', 'QA-PSID-005', 'QA Sender 5', 'Long message_id test (105 chars)', 'inbound',
       'qa-mid.' || repeat('x', 98), jsonb_build_object('platform','messenger','test',TRUE,'long_id_test',TRUE)
FROM tenant_006.leads l WHERE l.lead_code = 'QA-LD-001';

INSERT INTO tenant_006.meta_messages (
    tenant_id, lead_id, platform, sender_id, sender_name, message_text,
    direction, message_id, raw_payload
)
SELECT 6, l.id, 'instagram', 'QA-IGSID-001', 'qa_ig_user_1', 'Hi via Instagram DM', 'inbound',
       'qa-igmid.' || repeat('f', 20), jsonb_build_object('platform','instagram','test',TRUE)
FROM tenant_006.leads l WHERE l.lead_code = 'QA-LD-002';

INSERT INTO tenant_006.meta_messages (
    tenant_id, lead_id, platform, sender_id, sender_name, message_text,
    direction, message_id, raw_payload
)
SELECT 6, l.id, 'instagram', 'QA-IGSID-002', 'qa_ig_user_2', 'Are you open today?', 'inbound',
       'qa-igmid.' || repeat('g', 22), jsonb_build_object('platform','instagram','test',TRUE)
FROM tenant_006.leads l WHERE l.lead_code = 'QA-LD-003';

INSERT INTO tenant_006.meta_messages (
    tenant_id, lead_id, platform, sender_id, sender_name, message_text,
    direction, message_id, raw_payload
)
SELECT 6, l.id, 'instagram', 'QA-IGSID-001', 'qa_ig_user_1', 'Yes, we are open 24/7 online', 'outbound',
       'qa-igmid.' || repeat('h', 24), jsonb_build_object('platform','instagram','test',TRUE)
FROM tenant_006.leads l WHERE l.lead_code = 'QA-LD-002';

INSERT INTO tenant_006.meta_messages (
    tenant_id, lead_id, platform, sender_id, sender_name, message_text,
    direction, message_id, raw_payload
)
SELECT 6, l.id, 'instagram', 'QA-IGSID-003', 'qa_ig_user_3', 'Do you accept PayPal?', 'inbound',
       'qa-igmid.' || repeat('i', 26), jsonb_build_object('platform','instagram','test',TRUE)
FROM tenant_006.leads l WHERE l.lead_code = 'QA-LD-005';

-- ---------------------------------------------------------------------------
-- 7. Deals / reasons / converted leads
-- ---------------------------------------------------------------------------
INSERT INTO tenant_006.deals (tenant_id, company_id, deal_code, status, amount, stage, created_at, closed_at)
SELECT 6, c.id, 'QA-FN-D01', 'won', 800000, 'won', NOW() - INTERVAL '14 days', NOW() - INTERVAL '3 days'
FROM tenant_006.companies c WHERE c.company_code = 'QA-FN-CO-D01';

INSERT INTO tenant_006.deals (tenant_id, company_id, deal_code, status, amount, stage, created_at, closed_at)
SELECT 6, c.id, 'QA-FN-D02', 'won', 700000, 'won', NOW() - INTERVAL '14 days', NOW() - INTERVAL '5 days'
FROM tenant_006.companies c WHERE c.company_code = 'QA-FN-CO-D02';

INSERT INTO tenant_006.deals (tenant_id, company_id, deal_code, status, amount, stage, created_at, closed_at)
SELECT 6, c.id, 'QA-FN-D03', 'lost', 500000, 'lost', NOW() - INTERVAL '13 days', NOW() - INTERVAL '4 days'
FROM tenant_006.companies c WHERE c.company_code = 'QA-FN-CO-D03';

INSERT INTO tenant_006.deals (tenant_id, company_id, deal_code, status, amount, stage, created_at)
SELECT 6, c.id, 'QA-FN-D04', 'open', 900000, 'open', NOW() - INTERVAL '12 days'
FROM tenant_006.companies c WHERE c.company_code = 'QA-FN-CO-D04';

INSERT INTO tenant_006.deals (tenant_id, company_id, deal_code, status, amount, stage, created_at, closed_at)
SELECT 6, c.id, 'QA-FN-D05', 'won', 900000, 'won', NOW() - INTERVAL '13 days', NOW() - INTERVAL '6 days'
FROM tenant_006.companies c WHERE c.company_code = 'QA-FN-CO-D05';

INSERT INTO tenant_006.deals (tenant_id, company_id, deal_code, status, amount, stage, created_at)
SELECT 6, c.id, 'QA-FN-D06', 'negotiating', 1100000, 'negotiating', NOW() - INTERVAL '11 days'
FROM tenant_006.companies c WHERE c.company_code = 'QA-FN-CO-D06';

INSERT INTO tenant_006.deals (tenant_id, company_id, deal_code, status, amount, stage, created_at, closed_at)
SELECT 6, c.id, 'QA-FN-D07', 'won', 600000, 'won', NOW() - INTERVAL '14 days', NOW() - INTERVAL '7 days'
FROM tenant_006.companies c WHERE c.company_code = 'QA-FN-CO-D07';

INSERT INTO tenant_006.deals (tenant_id, company_id, deal_code, status, amount, stage, created_at, closed_at)
SELECT 6, c.id, 'QA-FN-D08', 'lost', 400000, 'lost', NOW() - INTERVAL '13 days', NOW() - INTERVAL '8 days'
FROM tenant_006.companies c WHERE c.company_code = 'QA-FN-CO-D08';

INSERT INTO tenant_006.deals (tenant_id, company_id, deal_code, status, amount, stage, created_at)
SELECT 6, c.id, 'QA-FN-D09', 'open', 800000, 'open', NOW() - INTERVAL '10 days'
FROM tenant_006.companies c WHERE c.company_code = 'QA-FN-CO-D09';

INSERT INTO tenant_006.deals (tenant_id, company_id, deal_code, status, amount, stage, created_at)
SELECT 6, c.id, 'QA-FN-D10', 'negotiating', 700000, 'negotiating', NOW() - INTERVAL '9 days'
FROM tenant_006.companies c WHERE c.company_code = 'QA-FN-CO-D10';

INSERT INTO tenant_006.deals (tenant_id, company_id, deal_code, status, amount, stage, created_at)
SELECT 6, c.id, 'QA-FN-D11', 'on_hold', 500000, 'on_hold', NOW() - INTERVAL '8 days'
FROM tenant_006.companies c WHERE c.company_code = 'QA-FN-CO-D11';

INSERT INTO tenant_006.deals (tenant_id, company_id, deal_code, status, amount, stage, created_at, closed_at)
SELECT 6, c.id, 'QA-FN-D12', 'won', 500000, 'won', NOW() - INTERVAL '50 days', NOW() - INTERVAL '35 days'
FROM tenant_006.companies c WHERE c.company_code = 'QA-FN-CO-D12';

INSERT INTO tenant_006.deal_close_reasons (deal_id, reason_id, is_primary)
SELECT d.id,
       (SELECT id FROM tenant_006.close_reasons WHERE type = 'won' AND label = '在庫・品揃え' LIMIT 1),
       TRUE
  FROM tenant_006.deals d
 WHERE d.deal_code = 'QA-FN-D01';

INSERT INTO tenant_006.deal_close_reasons (deal_id, reason_id, is_primary)
SELECT d.id,
       (SELECT id FROM tenant_006.close_reasons WHERE type = 'won' AND label = '安心感' LIMIT 1),
       FALSE
  FROM tenant_006.deals d
 WHERE d.deal_code = 'QA-FN-D01';

INSERT INTO tenant_006.deal_close_reasons (deal_id, reason_id, is_primary)
SELECT d.id,
       (SELECT id FROM tenant_006.close_reasons WHERE type = 'won' AND label = '在庫・品揃え' LIMIT 1),
       TRUE
  FROM tenant_006.deals d
 WHERE d.deal_code = 'QA-FN-D02';

INSERT INTO tenant_006.deal_close_reasons (deal_id, reason_id, is_primary)
SELECT d.id,
       (SELECT id FROM tenant_006.close_reasons WHERE type = 'won' AND label = '価格' LIMIT 1),
       TRUE
  FROM tenant_006.deals d
 WHERE d.deal_code = 'QA-FN-D05';

INSERT INTO tenant_006.deal_close_reasons (deal_id, reason_id, is_primary)
SELECT d.id,
       (SELECT id FROM tenant_006.close_reasons WHERE type = 'won' AND label = '安心感' LIMIT 1),
       FALSE
  FROM tenant_006.deals d
 WHERE d.deal_code = 'QA-FN-D05';

INSERT INTO tenant_006.deal_close_reasons (deal_id, reason_id, is_primary)
SELECT d.id,
       (SELECT id FROM tenant_006.close_reasons WHERE type = 'won' AND label = 'スピード' LIMIT 1),
       TRUE
  FROM tenant_006.deals d
 WHERE d.deal_code = 'QA-FN-D07';

INSERT INTO tenant_006.deal_close_reasons (deal_id, reason_id, is_primary)
SELECT d.id,
       (SELECT id FROM tenant_006.close_reasons WHERE type = 'lost' AND label = '価格が合わなかった' LIMIT 1),
       TRUE
  FROM tenant_006.deals d
 WHERE d.deal_code = 'QA-FN-D03';

INSERT INTO tenant_006.deal_close_reasons (deal_id, reason_id, is_primary)
SELECT d.id,
       (SELECT id FROM tenant_006.close_reasons WHERE type = 'lost' AND label = '連絡が途絶えた' LIMIT 1),
       TRUE
  FROM tenant_006.deals d
 WHERE d.deal_code = 'QA-FN-D08';

UPDATE tenant_006.deals SET close_reason_memo = '品揃えが豊富で決め手に' WHERE deal_code = 'QA-FN-D01';
UPDATE tenant_006.deals SET close_reason_memo = '価格面で折り合えた'     WHERE deal_code = 'QA-FN-D05';

UPDATE tenant_006.leads SET converted_deal_id = (SELECT id FROM tenant_006.deals WHERE deal_code = 'QA-FN-D01' LIMIT 1)
 WHERE lead_code = 'QA-FN-LD-001';
UPDATE tenant_006.leads SET converted_deal_id = (SELECT id FROM tenant_006.deals WHERE deal_code = 'QA-FN-D02' LIMIT 1)
 WHERE lead_code = 'QA-FN-LD-002';
UPDATE tenant_006.leads SET converted_deal_id = (SELECT id FROM tenant_006.deals WHERE deal_code = 'QA-FN-D03' LIMIT 1)
 WHERE lead_code = 'QA-FN-LD-003';
UPDATE tenant_006.leads SET converted_deal_id = (SELECT id FROM tenant_006.deals WHERE deal_code = 'QA-FN-D04' LIMIT 1)
 WHERE lead_code = 'QA-FN-LD-004';
UPDATE tenant_006.leads SET converted_deal_id = (SELECT id FROM tenant_006.deals WHERE deal_code = 'QA-FN-D05' LIMIT 1)
 WHERE lead_code = 'QA-FN-LD-009';
UPDATE tenant_006.leads SET converted_deal_id = (SELECT id FROM tenant_006.deals WHERE deal_code = 'QA-FN-D06' LIMIT 1)
 WHERE lead_code = 'QA-FN-LD-010';
UPDATE tenant_006.leads SET converted_deal_id = (SELECT id FROM tenant_006.deals WHERE deal_code = 'QA-FN-D07' LIMIT 1)
 WHERE lead_code = 'QA-FN-LD-015';
UPDATE tenant_006.leads SET converted_deal_id = (SELECT id FROM tenant_006.deals WHERE deal_code = 'QA-FN-D08' LIMIT 1)
 WHERE lead_code = 'QA-FN-LD-016';

-- ---------------------------------------------------------------------------
-- 8. Orders / order_financials
-- ---------------------------------------------------------------------------
INSERT INTO tenant_006.orders (tenant_id, company_id, order_number, total_amount, status, created_at)
SELECT 6, c.id, 'QA-FN-OR-N1A', 400000.00, 'completed', NOW() - INTERVAL '10 days'
FROM tenant_006.companies c WHERE c.company_code = 'QA-FN-CO-ON1';
INSERT INTO tenant_006.orders (tenant_id, company_id, order_number, total_amount, status, created_at)
SELECT 6, c.id, 'QA-FN-OR-N1B', 1.00, 'completed', NOW() - INTERVAL '9 days'
FROM tenant_006.companies c WHERE c.company_code = 'QA-FN-CO-ON1';
INSERT INTO tenant_006.orders (tenant_id, company_id, order_number, total_amount, status, created_at)
SELECT 6, c.id, 'QA-FN-OR-N2A', 300000.00, 'completed', NOW() - INTERVAL '8 days'
FROM tenant_006.companies c WHERE c.company_code = 'QA-FN-CO-ON2';
INSERT INTO tenant_006.orders (tenant_id, company_id, order_number, total_amount, status, created_at)
SELECT 6, c.id, 'QA-FN-OR-N2B', 1.00, 'completed', NOW() - INTERVAL '7 days'
FROM tenant_006.companies c WHERE c.company_code = 'QA-FN-CO-ON2';
INSERT INTO tenant_006.orders (tenant_id, company_id, order_number, total_amount, status, created_at)
SELECT 6, c.id, 'QA-FN-OR-N3A', 300000.00, 'completed', NOW() - INTERVAL '6 days'
FROM tenant_006.companies c WHERE c.company_code = 'QA-FN-CO-ON3';
INSERT INTO tenant_006.orders (tenant_id, company_id, order_number, total_amount, status, created_at)
SELECT 6, c.id, 'QA-FN-OR-N3B', 1.00, 'completed', NOW() - INTERVAL '5 days'
FROM tenant_006.companies c WHERE c.company_code = 'QA-FN-CO-ON3';
INSERT INTO tenant_006.orders (tenant_id, company_id, order_number, total_amount, status, created_at)
SELECT 6, c.id, 'QA-FN-OR-R1', 600000.00, 'completed', NOW() - INTERVAL '12 days'
FROM tenant_006.companies c WHERE c.company_code = 'QA-FN-CO-OR1';
INSERT INTO tenant_006.orders (tenant_id, company_id, order_number, total_amount, status, created_at)
SELECT 6, c.id, 'QA-FN-OR-R2', 500000.00, 'completed', NOW() - INTERVAL '11 days'
FROM tenant_006.companies c WHERE c.company_code = 'QA-FN-CO-OR2';
INSERT INTO tenant_006.orders (tenant_id, company_id, order_number, total_amount, status, created_at)
SELECT 6, c.id, 'QA-FN-OR-R3', 500000.00, 'completed', NOW() - INTERVAL '10 days'
FROM tenant_006.companies c WHERE c.company_code = 'QA-FN-CO-OR3';
INSERT INTO tenant_006.orders (tenant_id, company_id, order_number, total_amount, status, created_at)
SELECT 6, c.id, 'QA-FN-OR-R4', 400000.00, 'completed', NOW() - INTERVAL '9 days'
FROM tenant_006.companies c WHERE c.company_code = 'QA-FN-CO-OR4';
INSERT INTO tenant_006.orders (tenant_id, company_id, order_number, total_amount, status, created_at)
SELECT 6, c.id, 'QA-FN-OR-R1P', 100000.00, 'completed', NOW() - INTERVAL '70 days'
FROM tenant_006.companies c WHERE c.company_code = 'QA-FN-CO-OR1';
INSERT INTO tenant_006.orders (tenant_id, company_id, order_number, total_amount, status, created_at)
SELECT 6, c.id, 'QA-FN-OR-R2P', 100000.00, 'completed', NOW() - INTERVAL '70 days'
FROM tenant_006.companies c WHERE c.company_code = 'QA-FN-CO-OR2';
INSERT INTO tenant_006.orders (tenant_id, company_id, order_number, total_amount, status, created_at)
SELECT 6, c.id, 'QA-FN-OR-R3P', 100000.00, 'completed', NOW() - INTERVAL '70 days'
FROM tenant_006.companies c WHERE c.company_code = 'QA-FN-CO-OR3';
INSERT INTO tenant_006.orders (tenant_id, company_id, order_number, total_amount, status, created_at)
SELECT 6, c.id, 'QA-FN-OR-R4P', 100000.00, 'completed', NOW() - INTERVAL '70 days'
FROM tenant_006.companies c WHERE c.company_code = 'QA-FN-CO-OR4';
INSERT INTO tenant_006.orders (tenant_id, company_id, order_number, total_amount, status, created_at)
SELECT 6, c.id, 'QA-FN-OR-S1A', 200000.00, 'completed', NOW() - INTERVAL '90 days'
FROM tenant_006.companies c WHERE c.company_code = 'QA-FN-CO-FS1';
INSERT INTO tenant_006.orders (tenant_id, company_id, order_number, total_amount, status, created_at)
SELECT 6, c.id, 'QA-FN-OR-S1B', 150000.00, 'completed', NOW() - INTERVAL '75 days'
FROM tenant_006.companies c WHERE c.company_code = 'QA-FN-CO-FS1';
INSERT INTO tenant_006.orders (tenant_id, company_id, order_number, total_amount, status, created_at)
SELECT 6, c.id, 'QA-FN-OR-S2A', 180000.00, 'completed', NOW() - INTERVAL '90 days'
FROM tenant_006.companies c WHERE c.company_code = 'QA-FN-CO-FS2';
INSERT INTO tenant_006.orders (tenant_id, company_id, order_number, total_amount, status, created_at)
SELECT 6, c.id, 'QA-FN-OR-S2B', 120000.00, 'completed', NOW() - INTERVAL '75 days'
FROM tenant_006.companies c WHERE c.company_code = 'QA-FN-CO-FS2';
INSERT INTO tenant_006.orders (tenant_id, company_id, order_number, total_amount, status, created_at)
SELECT 6, c.id, 'QA-FN-OR-NR1', 80000.00, 'completed', NOW() - INTERVAL '25 days'
FROM tenant_006.companies c WHERE c.company_code = 'QA-FN-CO-FN1';

INSERT INTO tenant_006.order_financials (order_id, purchase_cost)
SELECT o.id, 280000.00 FROM tenant_006.orders o WHERE o.order_number = 'QA-FN-OR-N1A';
INSERT INTO tenant_006.order_financials (order_id, purchase_cost)
SELECT o.id, 0.00 FROM tenant_006.orders o WHERE o.order_number = 'QA-FN-OR-N1B';
INSERT INTO tenant_006.order_financials (order_id, purchase_cost)
SELECT o.id, 210000.00 FROM tenant_006.orders o WHERE o.order_number = 'QA-FN-OR-N2A';
INSERT INTO tenant_006.order_financials (order_id, purchase_cost)
SELECT o.id, 0.00 FROM tenant_006.orders o WHERE o.order_number = 'QA-FN-OR-N2B';
INSERT INTO tenant_006.order_financials (order_id, purchase_cost)
SELECT o.id, 0.00 FROM tenant_006.orders o WHERE o.order_number = 'QA-FN-OR-N3B';
INSERT INTO tenant_006.order_financials (order_id, purchase_cost)
SELECT o.id, 420000.00 FROM tenant_006.orders o WHERE o.order_number = 'QA-FN-OR-R1';
INSERT INTO tenant_006.order_financials (order_id, purchase_cost)
SELECT o.id, 350000.00 FROM tenant_006.orders o WHERE o.order_number = 'QA-FN-OR-R2';
INSERT INTO tenant_006.order_financials (order_id, purchase_cost)
SELECT o.id, 350000.00 FROM tenant_006.orders o WHERE o.order_number = 'QA-FN-OR-R3';
INSERT INTO tenant_006.order_financials (order_id, purchase_cost)
SELECT o.id, 190000.00 FROM tenant_006.orders o WHERE o.order_number = 'QA-FN-OR-R4';

-- ---------------------------------------------------------------------------
-- 9. Goals
-- ---------------------------------------------------------------------------
INSERT INTO tenant_006.goals (team_id, user_id, period_type, period_year, period_num, kpi_type, target_value)
SELECT t.id, NULL, 'monthly', 2026, 6, 'lead_count', 30
  FROM tenant_006.teams t WHERE t.name = 'QA営業チーム' LIMIT 1;

INSERT INTO tenant_006.goals (team_id, user_id, period_type, period_year, period_num, kpi_type, target_value)
SELECT t.id, NULL, 'monthly', 2026, 6, 'conversion_rate', 50
  FROM tenant_006.teams t WHERE t.name = 'QA営業チーム' LIMIT 1;

INSERT INTO tenant_006.goals (team_id, user_id, period_type, period_year, period_num, kpi_type, target_value)
SELECT t.id, NULL, 'monthly', 2026, 6, 'won_count', 10
  FROM tenant_006.teams t WHERE t.name = 'QA営業チーム' LIMIT 1;

INSERT INTO tenant_006.goals (team_id, user_id, period_type, period_year, period_num, kpi_type, target_value)
SELECT t.id, NULL, 'monthly', 2026, 6, 'revenue', 10000000
  FROM tenant_006.teams t WHERE t.name = 'QA営業チーム' LIMIT 1;

-- ---------------------------------------------------------------------------
-- 10. Sanity asserts
-- ---------------------------------------------------------------------------
DO $assert_counts$
DECLARE
    n INTEGER;
BEGIN
    SELECT COUNT(*) INTO n FROM tenant_006.teams WHERE name = 'QA営業チーム';
    IF n <> 1 THEN RAISE EXCEPTION 'seed assert FAIL: teams expected=1, got=%', n; END IF;

    SELECT COUNT(*) INTO n FROM tenant_006.leads WHERE lead_code LIKE 'QA-LD-%';
    IF n <> 5 THEN RAISE EXCEPTION 'seed assert FAIL: leads(QA-LD-*) expected=5, got=%', n; END IF;

    SELECT COUNT(*) INTO n FROM tenant_006.leads WHERE lead_code LIKE 'QA-FN-LD-%';
    IF n <> 20 THEN RAISE EXCEPTION 'seed assert FAIL: leads(QA-FN-LD-*) expected=20, got=%', n; END IF;

    SELECT COUNT(*) INTO n FROM tenant_006.leads WHERE lead_code LIKE 'QA-FN-LD-%' AND converted_deal_id IS NOT NULL;
    IF n <> 8 THEN RAISE EXCEPTION 'seed assert FAIL: converted leads expected=8, got=%', n; END IF;

    SELECT COUNT(*) INTO n FROM tenant_006.leads WHERE lead_code LIKE 'QA-FN-LD-%' AND assigned_to IS NOT NULL;
    IF n <> 0 THEN RAISE EXCEPTION 'seed assert FAIL: assigned_to must be NULL for funnel leads, got=%', n; END IF;

    SELECT COUNT(*) INTO n FROM tenant_006.companies WHERE company_code LIKE 'QA-CO-%';
    IF n <> 5 THEN RAISE EXCEPTION 'seed assert FAIL: companies(QA-CO-*) expected=5, got=%', n; END IF;

    SELECT COUNT(*) INTO n FROM tenant_006.companies WHERE company_code LIKE 'QA-FN-CO-%';
    IF n <> 22 THEN RAISE EXCEPTION 'seed assert FAIL: companies(QA-FN-CO-*) expected=22, got=%', n; END IF;

    SELECT COUNT(*) INTO n FROM tenant_006.contacts WHERE contact_code LIKE 'QA-CT-%';
    IF n <> 5 THEN RAISE EXCEPTION 'seed assert FAIL: contacts expected=5, got=%', n; END IF;

    SELECT COUNT(*) INTO n FROM tenant_006.products WHERE product_code LIKE 'QA-PR-%';
    IF n <> 5 THEN RAISE EXCEPTION 'seed assert FAIL: products expected=5, got=%', n; END IF;

    SELECT COUNT(*) INTO n FROM tenant_006.meta_messages;
    IF n <> 10 THEN RAISE EXCEPTION 'seed assert FAIL: meta_messages expected=10, got=%', n; END IF;

    SELECT COUNT(*) INTO n FROM tenant_006.meta_messages WHERE length(message_id) > 100;
    IF n < 1 THEN RAISE EXCEPTION 'seed assert FAIL: long message_id row is missing'; END IF;

    SELECT COUNT(*) INTO n FROM tenant_006.deals WHERE deal_code LIKE 'QA-FN-D%';
    IF n <> 12 THEN RAISE EXCEPTION 'seed assert FAIL: deals expected=12, got=%', n; END IF;

    SELECT COUNT(*) INTO n FROM tenant_006.deals WHERE deal_code LIKE 'QA-FN-D%' AND assigned_to IS NOT NULL;
    IF n <> 0 THEN RAISE EXCEPTION 'seed assert FAIL: assigned_to must be NULL for funnel deals, got=%', n; END IF;

    SELECT COUNT(*) INTO n FROM tenant_006.deal_close_reasons WHERE deal_id IN (
        SELECT id FROM tenant_006.deals WHERE deal_code LIKE 'QA-FN-D%'
    );
    IF n <> 8 THEN RAISE EXCEPTION 'seed assert FAIL: deal_close_reasons expected=8, got=%', n; END IF;

    SELECT COUNT(*) INTO n FROM tenant_006.orders WHERE order_number LIKE 'QA-FN-OR-%';
    IF n <> 19 THEN RAISE EXCEPTION 'seed assert FAIL: orders(QA-FN-OR-*) expected=19, got=%', n; END IF;

    SELECT COUNT(*) INTO n FROM tenant_006.order_financials WHERE order_id IN (
        SELECT id FROM tenant_006.orders WHERE order_number LIKE 'QA-FN-OR-%'
    );
    IF n <> 9 THEN RAISE EXCEPTION 'seed assert FAIL: order_financials expected=9, got=%', n; END IF;

    SELECT COUNT(*) INTO n FROM tenant_006.goals
     WHERE period_type = 'monthly' AND period_year = 2026 AND period_num = 6 AND user_id IS NULL;
    IF n <> 4 THEN RAISE EXCEPTION 'seed assert FAIL: goals expected=4, got=%', n; END IF;

    SELECT COUNT(*) INTO n FROM tenant_006.goals
     WHERE period_type = 'monthly' AND period_year = 2026 AND period_num = 6 AND user_id IS NOT NULL;
    IF n <> 0 THEN RAISE EXCEPTION 'seed assert FAIL: goal user_id must be NULL, got=%', n; END IF;

    RAISE NOTICE 'funnel seed assert: ALL OK';
END
$assert_counts$;

COMMIT;
