-- Migration: invoices に PayPal 決済リンク列を追加（全テナント）
--
-- 目的 (ADR-101 §6 PayPal mode1 / Increment 1):
--   請求書から PayPal 決済リンク（Orders API）を発行し、入金確認で paid 化するために
--   PayPal の order id・承認リンク・手数料を保存する列を追加する。
--
-- 影響テーブル: {tenant_NNN}.invoices
-- 適用対象: 全テナント（pg_namespace 走査で冪等適用）
-- 冪等・安全: ADD COLUMN IF NOT EXISTS（nullable 追加のみ・既存データ不変・破壊操作なし）

DO $$
DECLARE
    schema_record RECORD;
BEGIN
    FOR schema_record IN
        SELECT nspname AS schema_name
        FROM pg_namespace
        WHERE nspname LIKE 'tenant_%'
        ORDER BY nspname
    LOOP
        RAISE NOTICE 'Processing schema: %', schema_record.schema_name;

        -- invoices: PayPal 決済列追加（全て nullable）
        EXECUTE format(
            'ALTER TABLE %I.invoices
             ADD COLUMN IF NOT EXISTS paypal_order_id     TEXT,
             ADD COLUMN IF NOT EXISTS paypal_approval_url TEXT,
             ADD COLUMN IF NOT EXISTS payment_fee         NUMERIC(15,2)',
            schema_record.schema_name
        );

        EXECUTE format(
            'COMMENT ON COLUMN %I.invoices.paypal_order_id IS '
            '''ADR-101: PayPal Orders API の order id（リンク発行時に保存）''',
            schema_record.schema_name
        );
        EXECUTE format(
            'COMMENT ON COLUMN %I.invoices.paypal_approval_url IS '
            '''ADR-101: 顧客が支払う PayPal 承認 URL（links[rel=approve]）''',
            schema_record.schema_name
        );
        EXECUTE format(
            'COMMENT ON COLUMN %I.invoices.payment_fee IS '
            '''ADR-101/104: 決済手数料（capture で取得。将来の合計/P&L 算入用に保存）''',
            schema_record.schema_name
        );
    END LOOP;
END
$$;
