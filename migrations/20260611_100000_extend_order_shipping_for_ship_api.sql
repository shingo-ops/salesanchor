-- ============================================================================
-- !! 警告 !! このSQLファイルは **テンプレート** です。
-- {schema}, {tenant_id} のプレースホルダを含むため、
-- そのまま psql で実行するとシンタックスエラーになります。
--
-- 必ず scripts/migrate_adr128_extend_order_shipping.py 経由で実行してください:
--   docker compose exec backend python /app/scripts/migrate_adr128_extend_order_shipping.py
-- ============================================================================
--
-- ADR-128: order_shipping_details に Ship API / Pickup API 用カラム追加
--
-- 目的:
--   FedEx Ship API によるラベル発行と Pickup API による集荷予約に必要な
--   追加カラムを order_shipping_details テーブルに additive 追加する。
--   - address_type: 配送先区分（住宅/法人）
--   - confirmed_shipping_fee: Ship API で確定した送料
--   - confirmed_currency: 確定送料の通貨コード
--   - label_drive_url: Google Drive にアップロードしたラベル PDF の URL
--   - pickup_confirmation_code: 集荷確認番号
--   - surcharges: 追加料金の内訳（JSONB）
--
-- 冪等性:
--   ADD COLUMN IF NOT EXISTS で再実行 no-op
--
-- 変更履歴:
--   2026-06-11: 初版（ADR-128）
-- ============================================================================

ALTER TABLE {schema}.order_shipping_details
    ADD COLUMN IF NOT EXISTS address_type VARCHAR(20)
        CHECK (address_type IS NULL OR address_type IN ('RESIDENTIAL', 'BUSINESS'));

ALTER TABLE {schema}.order_shipping_details
    ADD COLUMN IF NOT EXISTS confirmed_shipping_fee NUMERIC(12, 2);

ALTER TABLE {schema}.order_shipping_details
    ADD COLUMN IF NOT EXISTS confirmed_currency VARCHAR(10);

ALTER TABLE {schema}.order_shipping_details
    ADD COLUMN IF NOT EXISTS label_drive_url TEXT;

ALTER TABLE {schema}.order_shipping_details
    ADD COLUMN IF NOT EXISTS pickup_confirmation_code VARCHAR(100);

ALTER TABLE {schema}.order_shipping_details
    ADD COLUMN IF NOT EXISTS surcharges JSONB;
