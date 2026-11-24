-- insert.sql で入れたテストデータを消す。テナント001のみ。
-- メッセージを先に消す（leads を消すと meta_messages.lead_id は SET NULL になり目印で追えるが、順を固定する）。
-- 画面で翻訳を押した場合の翻訳の写しも消す（message_translations は message_id で結ぶ）。
-- 人が画面で見積・会社・担当者などを作っていたら止める。
SET lock_timeout = '5s';
SET statement_timeout = '30s';
BEGIN;

DO $$
DECLARE ids int[];
BEGIN
  SELECT array_agg(id) INTO ids FROM tenant_001.leads WHERE lead_code LIKE 'TST-KARTE-%';
  IF coalesce(array_length(ids, 1), 0) > 3 THEN
    RAISE EXCEPTION '前提が違う: TST-KARTE- のリードが3件より多い';
  END IF;
  IF (SELECT count(*) FROM tenant_001.meta_messages
      WHERE lead_id = ANY(ids) AND message_id NOT LIKE 'tst-karte-%') <> 0 THEN
    RAISE EXCEPTION '止める: テスト用リードに目印のないメッセージがある（画面から送った等）';
  END IF;
END $$;

DELETE FROM tenant_001.message_translations WHERE message_id LIKE 'tst-karte-%';
DELETE FROM tenant_001.meta_messages WHERE message_id LIKE 'tst-karte-%';
DELETE FROM tenant_001.leads WHERE lead_code LIKE 'TST-KARTE-%';

DO $$
BEGIN
  IF (SELECT count(*) FROM tenant_001.leads WHERE lead_code LIKE 'TST-KARTE-%') <> 0
     OR (SELECT count(*) FROM tenant_001.meta_messages WHERE message_id LIKE 'tst-karte-%') <> 0 THEN
    RAISE EXCEPTION '消し残りがある';
  END IF;
END $$;

-- DRY-RUN では ROLLBACK のまま流す。本番では COMMIT に置き換えた写しを流す。
ROLLBACK;
