-- 20260623_030000_drop_inventory_offer_key.sql
-- 2b 後段: 新コード（uq_inventory_offer_v2 へ ON CONFLICT）をデプロイした後にだけ、
-- 旧キー uq_inventory_offer_key を削除する。
--
-- 注意:
-- - これは新キー作成と同日に自動適用する想定ではない。
-- - 新コードが稼働し、実データで衝突がないことを確認した後の別 GO でのみ適用する。

DROP INDEX IF EXISTS uq_inventory_offer_key;
