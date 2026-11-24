-- 受信箱カルテ（ADR-1089）の本番画面確認用テストデータ。テナント001のみ。
-- 目印: leads.lead_code が 'TST-KARTE-' で始まる／meta_messages.message_id が 'tst-karte-' で始まる。
-- 3件のリード（lead / negotiating / follow_up_short）と、それぞれ送信のメッセージ1件。
-- 受信（inbound）は入れない: 翻訳点検（backend/app/services/translation_monitor.py:66-74）が
--   直近60分の未翻訳の受信を数えて Discord に誤報を出すため。送信だけなら24時間の返信窓も開かない。
-- page_id は空: 顔写真の取り直し（backend/app/tasks/avatar.py）が外へ問い合わせないため。
-- created_at は今の時刻: 一覧は最新50件だけ読む（backend/app/routers/meta_inbox.py:877・1003）ため。
SET lock_timeout = '5s';
SET statement_timeout = '30s';
BEGIN;

DO $$
BEGIN
  IF (SELECT count(*) FROM tenant_001.leads WHERE lead_code LIKE 'TST-KARTE-%') <> 0 THEN
    RAISE EXCEPTION '前提が違う: TST-KARTE- のリードが既にある';
  END IF;
  IF (SELECT count(*) FROM tenant_001.meta_messages WHERE message_id LIKE 'tst-karte-%') <> 0 THEN
    RAISE EXCEPTION '前提が違う: tst-karte- のメッセージが既にある';
  END IF;
END $$;

INSERT INTO tenant_001.leads
  (tenant_id, lead_code, customer_name, nickname, channel_type, initiative, status,
   temperature, estimated_scale, customer_type, country, competitor_check, escalation_flag,
   created_at, updated_at)
VALUES
  (1, 'TST-KARTE-1', 'TEST リード（確認用）',   'TEST-lead',   'instagram', 'inbound', 'lead',
   'Hot',  'Medium', '信頼重視', 'AU', false, false, now(), now()),
  (1, 'TST-KARTE-2', 'TEST 商談中（確認用）',   'TEST-deal',   'instagram', 'inbound', 'negotiating',
   'Warm', 'Large',  '信頼重視', 'GB', false, false, now(), now()),
  (1, 'TST-KARTE-3', 'TEST 追客（確認用）',     'TEST-follow', 'instagram', 'inbound', 'follow_up_short',
   'Warm', 'Medium', '信頼重視', 'US', false, false, now(), now());

INSERT INTO tenant_001.meta_messages
  (tenant_id, lead_id, platform, sender_id, recipient_id, message_text, direction,
   message_id, messaging_type, status, created_at)
SELECT 1, l.id, 'instagram', 'tst-karte-page', 'tst-karte-psid-' || v.n,
       'TEST message for karte check ' || v.n, 'outbound',
       'tst-karte-' || v.n, 'RESPONSE', 'sent', now() - (v.n || ' seconds')::interval
FROM (VALUES ('1'), ('2'), ('3')) AS v(n)
JOIN tenant_001.leads l ON l.lead_code = 'TST-KARTE-' || v.n;

DO $$
BEGIN
  IF (SELECT count(*) FROM tenant_001.leads WHERE lead_code LIKE 'TST-KARTE-%') <> 3 THEN
    RAISE EXCEPTION '件数が違う: リードが3件でない';
  END IF;
  IF (SELECT count(*) FROM tenant_001.meta_messages WHERE message_id LIKE 'tst-karte-%') <> 3 THEN
    RAISE EXCEPTION '件数が違う: メッセージが3件でない';
  END IF;
END $$;

SELECT l.id, l.lead_code, l.status, m.message_id, m.created_at
FROM tenant_001.leads l JOIN tenant_001.meta_messages m ON m.lead_id = l.id
WHERE l.lead_code LIKE 'TST-KARTE-%' ORDER BY l.lead_code;

-- DRY-RUN では次の行を ROLLBACK のまま流す。本番の書き込みでは COMMIT に置き換えた写しを流す。
ROLLBACK;
