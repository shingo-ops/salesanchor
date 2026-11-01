-- テスト用データ（lead_code が TLR- で始まるリード）を消す SQL（design §6-1。PO 本人が流す。今回は流さない）
-- 流し方: psql の ON_ERROR_STOP を有効にして、このファイル全体を 1 回で流す。途中で止まったら全体が取り消される。
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL statement_timeout = '600s';
SET LOCAL lock_timeout = '10s';

-- 手順0 の記録を入れる一時表（セッションが終わると消える）
CREATE TEMP TABLE tlr_record_started (started_at timestamptz NOT NULL);
CREATE TEMP TABLE tlr_record_orig_leads (id integer PRIMARY KEY);
CREATE TEMP TABLE tlr_record_orig_meta (id integer PRIMARY KEY, lead_id integer);
CREATE TEMP TABLE tlr_record_orig_conv (id integer PRIMARY KEY, lead_id integer);
CREATE TEMP TABLE tlr_record_orig_options (id integer PRIMARY KEY);
CREATE TEMP TABLE tlr_record_orig_counts (whatsapp_conv integer NOT NULL, close_reasons integer NOT NULL, selections integer NOT NULL);

-- 手順0 の記録をここに貼る
-- 貼るもの: 書き込みを始めた時刻を tlr_record_started に 1 行、元のリードの id を tlr_record_orig_leads に、
-- 元の meta_messages・conversation_logs の id と lead_id の組を tlr_record_orig_meta・tlr_record_orig_conv に、
-- 元の店舗の形の選択肢の id を tlr_record_orig_options に、元のリードの WhatsApp の会話の記録・失注の理由・
-- 店舗の形の選択の件数を tlr_record_orig_counts に 1 行。どれも pg_temp. の表への INSERT で貼る。

-- テスト用リード・メッセージ・選択肢の id を、消す前に記録する（目印の TLR- と、手順0 の記録から決まる）
CREATE TEMP TABLE tlr_record_leads AS
  SELECT id FROM tenant_001.leads WHERE lead_code LIKE 'TLR-%';
CREATE TEMP TABLE tlr_conv_ids AS
  SELECT id FROM tenant_001.conversation_logs WHERE lead_id IN (SELECT id FROM pg_temp.tlr_record_leads);
CREATE TEMP TABLE tlr_meta_ids AS
  SELECT id FROM tenant_001.meta_messages WHERE lead_id IN (SELECT id FROM pg_temp.tlr_record_leads);
CREATE TEMP TABLE tlr_option_ids AS
  SELECT id FROM tenant_001.tenant_sales_form_options
  WHERE id NOT IN (SELECT id FROM pg_temp.tlr_record_orig_options)
    AND value IN ('physical_store', 'ec_site', 'live_streaming', 'wholesale', 'other');

-- 手順1: 消す前の点検（当たれば RAISE EXCEPTION で止まる。PO へ報告する）
DO $$
BEGIN
  IF (SELECT count(*) FROM pg_temp.tlr_record_started) <> 1
     OR (SELECT count(*) FROM pg_temp.tlr_record_orig_leads) = 0
     OR (SELECT count(*) FROM pg_temp.tlr_record_orig_counts) <> 1 THEN
    RAISE EXCEPTION '止める: 手順0 の記録が貼られていない';
  END IF;
  IF (SELECT count(*) FROM pg_temp.tlr_record_leads) = 0 THEN
    RAISE EXCEPTION '止める: 消す対象のテスト用リードが 0 件';
  END IF;

  -- 人が画面で何かを作った印
  IF (SELECT count(*) FROM tenant_001.quotes WHERE lead_id IN (SELECT id FROM pg_temp.tlr_record_leads)) > 0 THEN
    RAISE EXCEPTION '止める: テスト用リードに見積がある（PO へ報告）';
  END IF;
  IF (SELECT count(*) FROM tenant_001.companies WHERE lead_id IN (SELECT id FROM pg_temp.tlr_record_leads)) > 0 THEN
    RAISE EXCEPTION '止める: テスト用リードに会社がある（PO へ報告）';
  END IF;
  IF (SELECT count(*) FROM tenant_001.contacts WHERE lead_id IN (SELECT id FROM pg_temp.tlr_record_leads)) > 0 THEN
    RAISE EXCEPTION '止める: テスト用リードに担当者がある（PO へ報告）';
  END IF;
  IF (SELECT count(*) FROM tenant_001.outbound_translation_drafts WHERE lead_id IN (SELECT id FROM pg_temp.tlr_record_leads)) > 0 THEN
    RAISE EXCEPTION '止める: テスト用リードに送信の下書きがある（PO へ報告）';
  END IF;
  IF (SELECT count(*) FROM public.registration_tokens WHERE tenant_id = 1 AND lead_id IN (SELECT id FROM pg_temp.tlr_record_leads)) > 0 THEN
    RAISE EXCEPTION '止める: テスト用リードに登録リンクがある（PO へ報告）';
  END IF;
  IF (SELECT count(*) FROM tenant_001.lead_attachments WHERE lead_id IN (SELECT id FROM pg_temp.tlr_record_leads)) > 0 THEN
    RAISE EXCEPTION '止める: テスト用リードに添付がある（PO へ報告。消す場合はファイルの実体も別手順）';
  END IF;

  -- 統合でテスト用の行が元のリードへ付け替わった印（逆の向き）
  IF (SELECT count(*) FROM tenant_001.lead_channels WHERE external_id LIKE 'tlr-%' AND lead_id IN (SELECT id FROM pg_temp.tlr_record_orig_leads)) > 0
     OR (SELECT count(*) FROM tenant_001.meta_messages WHERE message_id LIKE 'tlr-%' AND lead_id IN (SELECT id FROM pg_temp.tlr_record_orig_leads)) > 0
     OR (SELECT count(*) FROM tenant_001.conversation_logs WHERE external_message_id LIKE 'tlr-%' AND lead_id IN (SELECT id FROM pg_temp.tlr_record_orig_leads)) > 0 THEN
    RAISE EXCEPTION '止める: 元のリードに目印 tlr- の行が付いている（統合の印。PO へ報告）';
  END IF;
  IF (SELECT count(*) FROM tenant_001.conversation_logs WHERE channel_type = 'whatsapp' AND lead_id IN (SELECT id FROM pg_temp.tlr_record_orig_leads))
       > (SELECT whatsapp_conv FROM pg_temp.tlr_record_orig_counts)
     OR (SELECT count(*) FROM tenant_001.deal_close_reasons WHERE lead_id IN (SELECT id FROM pg_temp.tlr_record_orig_leads))
       > (SELECT close_reasons FROM pg_temp.tlr_record_orig_counts)
     OR (SELECT count(*) FROM tenant_001.lead_sales_form_selections WHERE lead_id IN (SELECT id FROM pg_temp.tlr_record_orig_leads))
       > (SELECT selections FROM pg_temp.tlr_record_orig_counts) THEN
    RAISE EXCEPTION '止める: 元のリードの会話・失注の理由・店舗の形の選択が増えている（統合の印。PO へ報告）';
  END IF;

  -- 統合でテスト用リードの行が付け替わった印（起こり得る向き）
  IF (SELECT count(*) FROM tenant_001.leads WHERE id IN (SELECT id FROM pg_temp.tlr_record_orig_leads))
       <> (SELECT count(*) FROM pg_temp.tlr_record_orig_leads) THEN
    RAISE EXCEPTION '止める: 元のリードが leads に残っていない（統合の印。PO へ報告）';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_temp.tlr_record_orig_meta r LEFT JOIN tenant_001.meta_messages m ON m.id = r.id
             WHERE m.id IS NULL OR COALESCE(m.lead_id, -1) <> COALESCE(r.lead_id, -1)) THEN
    RAISE EXCEPTION '止める: 元の meta_messages の持ち主が記録と違う（統合の印。PO へ報告）';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_temp.tlr_record_orig_conv r LEFT JOIN tenant_001.conversation_logs c ON c.id = r.id
             WHERE c.id IS NULL OR COALESCE(c.lead_id, -1) <> COALESCE(r.lead_id, -1)) THEN
    RAISE EXCEPTION '止める: 元の conversation_logs の持ち主が記録と違う（統合の印。PO へ報告）';
  END IF;
  IF (SELECT count(*) FROM tenant_001.audit_logs
      WHERE action IN ('merge_absorb', 'merge_delete')
        AND table_name = 'leads'
        AND created_at > (SELECT started_at FROM pg_temp.tlr_record_started)
        AND (record_id IN (SELECT id FROM pg_temp.tlr_record_leads) OR record_id IN (SELECT id FROM pg_temp.tlr_record_orig_leads))) > 0 THEN
    RAISE EXCEPTION '止める: 書き込み後にテスト用リードか元のリードの統合の記録がある（PO へ報告）';
  END IF;
END $$;

-- 手順2: message_translations（message_id が tlr- で始まる行と、会話の記録の conv_log_<id> の行）
DELETE FROM tenant_001.message_translations
  WHERE message_id LIKE 'tlr-%'
     OR message_id IN (SELECT 'conv_log_' || id::text FROM pg_temp.tlr_conv_ids);

-- 手順3: customer_scores・message_labels（テスト用リードの id で）
DELETE FROM tenant_001.customer_scores WHERE lead_id IN (SELECT id FROM pg_temp.tlr_record_leads);
DELETE FROM tenant_001.message_labels WHERE lead_id IN (SELECT id FROM pg_temp.tlr_record_leads);

-- 手順4: meta_messages（リアクションは一緒に消える）
DELETE FROM tenant_001.meta_messages
  WHERE message_id LIKE 'tlr-%' AND lead_id IN (SELECT id FROM pg_temp.tlr_record_leads);

-- 手順5: conversation_logs
DELETE FROM tenant_001.conversation_logs WHERE lead_id IN (SELECT id FROM pg_temp.tlr_record_leads);

-- 手順6: deal_close_reasons
DELETE FROM tenant_001.deal_close_reasons WHERE lead_id IN (SELECT id FROM pg_temp.tlr_record_leads);

-- 手順7: leads（lead_channels・lead_sales_form_selections・lead_attachments は一緒に消える）
DELETE FROM tenant_001.leads
  WHERE lead_code LIKE 'TLR-%' AND id IN (SELECT id FROM pg_temp.tlr_record_leads);

-- 手順8: tenant_sales_form_options（選択が残っていると止まるので最後）
DELETE FROM tenant_001.tenant_sales_form_options WHERE id IN (SELECT id FROM pg_temp.tlr_option_ids);

-- 手順9: 数え直し（テスト用の行が残っていれば RAISE EXCEPTION で全体を取り消す）
DO $$
BEGIN
  IF (SELECT count(*) FROM tenant_001.leads WHERE lead_code LIKE 'TLR-%') <> 0
     OR (SELECT count(*) FROM tenant_001.leads WHERE id IN (SELECT id FROM pg_temp.tlr_record_leads)) <> 0 THEN
    RAISE EXCEPTION '残っている: leads のテスト用の行';
  END IF;
  IF (SELECT count(*) FROM tenant_001.lead_sales_form_selections WHERE lead_id IN (SELECT id FROM pg_temp.tlr_record_leads)) <> 0
     OR (SELECT count(*) FROM tenant_001.deal_close_reasons WHERE lead_id IN (SELECT id FROM pg_temp.tlr_record_leads)) <> 0
     OR (SELECT count(*) FROM tenant_001.lead_channels WHERE external_id LIKE 'tlr-%' OR lead_id IN (SELECT id FROM pg_temp.tlr_record_leads)) <> 0 THEN
    RAISE EXCEPTION '残っている: 選択・失注の理由・lead_channels のテスト用の行';
  END IF;
  IF (SELECT count(*) FROM tenant_001.meta_messages WHERE message_id LIKE 'tlr-%' OR lead_id IN (SELECT id FROM pg_temp.tlr_record_leads) OR id IN (SELECT id FROM pg_temp.tlr_meta_ids)) <> 0
     OR (SELECT count(*) FROM tenant_001.meta_message_reactions WHERE meta_message_id IN (SELECT id FROM pg_temp.tlr_meta_ids)) <> 0
     OR (SELECT count(*) FROM tenant_001.conversation_logs WHERE external_message_id LIKE 'tlr-%' OR lead_id IN (SELECT id FROM pg_temp.tlr_record_leads) OR id IN (SELECT id FROM pg_temp.tlr_conv_ids)) <> 0 THEN
    RAISE EXCEPTION '残っている: メッセージ・リアクション・会話の記録のテスト用の行';
  END IF;
  IF (SELECT count(*) FROM tenant_001.message_translations WHERE message_id LIKE 'tlr-%' OR message_id IN (SELECT 'conv_log_' || id::text FROM pg_temp.tlr_conv_ids)) <> 0
     OR (SELECT count(*) FROM tenant_001.customer_scores WHERE lead_id IN (SELECT id FROM pg_temp.tlr_record_leads)) <> 0
     OR (SELECT count(*) FROM tenant_001.message_labels WHERE lead_id IN (SELECT id FROM pg_temp.tlr_record_leads)) <> 0
     OR (SELECT count(*) FROM tenant_001.tenant_sales_form_options WHERE id IN (SELECT id FROM pg_temp.tlr_option_ids)) <> 0 THEN
    RAISE EXCEPTION '残っている: 翻訳・スコア・ラベル・選択肢のテスト用の行';
  END IF;

  -- 元の行がすべて残っている
  IF (SELECT count(*) FROM tenant_001.leads WHERE id IN (SELECT id FROM pg_temp.tlr_record_orig_leads))
       <> (SELECT count(*) FROM pg_temp.tlr_record_orig_leads)
     OR (SELECT count(*) FROM pg_temp.tlr_record_orig_meta r JOIN tenant_001.meta_messages m ON m.id = r.id)
       <> (SELECT count(*) FROM pg_temp.tlr_record_orig_meta)
     OR (SELECT count(*) FROM pg_temp.tlr_record_orig_conv r JOIN tenant_001.conversation_logs c ON c.id = r.id)
       <> (SELECT count(*) FROM pg_temp.tlr_record_orig_conv)
     OR (SELECT count(*) FROM pg_temp.tlr_record_orig_options r JOIN tenant_001.tenant_sales_form_options o ON o.id = r.id)
       <> (SELECT count(*) FROM pg_temp.tlr_record_orig_options) THEN
    RAISE EXCEPTION '消えている: 元の行が残っていない';
  END IF;
END $$;

-- audit_logs は消さない。書き込みを始めた時刻より後の関係する行の件数だけを報告する（action ごと）
SELECT a.table_name, a.action, count(*) AS rows_after_start
  FROM tenant_001.audit_logs a
  WHERE a.created_at > (SELECT started_at FROM pg_temp.tlr_record_started)
    AND ( (a.new_data ->> 'lead_id') ~ '^[0-9]+$'
          AND (a.new_data ->> 'lead_id')::integer IN (SELECT id FROM pg_temp.tlr_record_leads)
       OR (a.table_name = 'leads'
           AND a.record_id IN (SELECT id FROM pg_temp.tlr_record_leads UNION SELECT id FROM pg_temp.tlr_record_orig_leads)) )
  GROUP BY a.table_name, a.action
  ORDER BY a.table_name, a.action;

COMMIT;
