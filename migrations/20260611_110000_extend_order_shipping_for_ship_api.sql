-- Migration 20260611_110000: ADR-128 — order_shipping_details に Ship/Pickup 用カラム追加
--
-- FedEx Ship API（ラベル発行）と Pickup API（集荷予約）に必要な 6 カラムを
-- order_shipping_details テーブルへ additive 追加する。
--
-- 追加カラム:
--   address_type           VARCHAR(20) — 配送先区分（RESIDENTIAL / BUSINESS）
--   confirmed_shipping_fee NUMERIC(12,2) — Ship API で確定した送料
--   confirmed_currency     VARCHAR(10) — 確定送料の通貨コード
--   label_drive_url        TEXT — Google Drive ラベル PDF の URL
--   pickup_confirmation_code VARCHAR(100) — 集荷確認番号
--   surcharges             JSONB — 追加料金の内訳配列
--
-- 冪等: ADD COLUMN IF NOT EXISTS + to_regclass() で再実行 no-op
-- 実行形式: psql 直実行可能（プレースホルダなし）。DO ブロックで全 tenant_NNN スキーマに適用。

DO $$
DECLARE
    sch text;
BEGIN
    FOR sch IN
        SELECT nspname FROM pg_namespace WHERE nspname ~ '^tenant_[0-9]+$'
    LOOP
        -- order_shipping_details が存在しないテナント（CI 用最小 schema 等）は skip
        IF to_regclass(sch || '.order_shipping_details') IS NULL THEN
            CONTINUE;
        END IF;

        EXECUTE format(
            'ALTER TABLE %I.order_shipping_details
                ADD COLUMN IF NOT EXISTS address_type VARCHAR(20)
                    CHECK (address_type IS NULL OR address_type IN (''RESIDENTIAL'', ''BUSINESS''))',
            sch
        );

        EXECUTE format(
            'ALTER TABLE %I.order_shipping_details
                ADD COLUMN IF NOT EXISTS confirmed_shipping_fee NUMERIC(12, 2)',
            sch
        );

        EXECUTE format(
            'ALTER TABLE %I.order_shipping_details
                ADD COLUMN IF NOT EXISTS confirmed_currency VARCHAR(10)',
            sch
        );

        EXECUTE format(
            'ALTER TABLE %I.order_shipping_details
                ADD COLUMN IF NOT EXISTS label_drive_url TEXT',
            sch
        );

        EXECUTE format(
            'ALTER TABLE %I.order_shipping_details
                ADD COLUMN IF NOT EXISTS pickup_confirmation_code VARCHAR(100)',
            sch
        );

        EXECUTE format(
            'ALTER TABLE %I.order_shipping_details
                ADD COLUMN IF NOT EXISTS surcharges JSONB',
            sch
        );
    END LOOP;
END $$;
