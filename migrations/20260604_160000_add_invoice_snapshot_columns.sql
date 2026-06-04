-- Migration: 請求書スナップショット列 + 為替レート列追加（全テナント）
--
-- 目的 (C-6 / C-7):
--   - invoices テーブルにスナップショット列（ship_to / bill_to / duty 等）を追加
--   - invoice_items / quote_items に hs_code 列を追加
--   - 外貨請求時に為替レートスナップショットを保存できるようにする
--
-- 影響テーブル:
--   {tenant_NNN}.invoices
--   {tenant_NNN}.invoice_items
--   {tenant_NNN}.quote_items
-- 適用対象: 全テナント（pg_namespace 走査で冪等適用）
-- 冪等: ADD COLUMN IF NOT EXISTS

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

        -- invoices: スナップショット列追加
        EXECUTE format(
            'ALTER TABLE %I.invoices
             ADD COLUMN IF NOT EXISTS ship_to_snapshot    JSONB,
             ADD COLUMN IF NOT EXISTS bill_to_snapshot    JSONB,
             ADD COLUMN IF NOT EXISTS issue_mode         VARCHAR(20),
             ADD COLUMN IF NOT EXISTS duty_amount        NUMERIC(15,2),
             ADD COLUMN IF NOT EXISTS duty_policy_snapshot JSONB,
             ADD COLUMN IF NOT EXISTS fx_rate_snapshot   JSONB',
            schema_record.schema_name
        );

        -- invoices: 列コメント
        EXECUTE format(
            'COMMENT ON COLUMN %I.invoices.ship_to_snapshot IS '
            '''C-6: 発行時点の配送先住所スナップショット（company_addresses から複写）''',
            schema_record.schema_name
        );
        EXECUTE format(
            'COMMENT ON COLUMN %I.invoices.bill_to_snapshot IS '
            '''C-6: 発行時点の請求先住所スナップショット（company_addresses から複写）''',
            schema_record.schema_name
        );
        EXECUTE format(
            'COMMENT ON COLUMN %I.invoices.issue_mode IS '
            '''C-6: 発行モード（tenant_settings.issue_mode から継承）''',
            schema_record.schema_name
        );
        EXECUTE format(
            'COMMENT ON COLUMN %I.invoices.duty_amount IS '
            '''C-6: 関税額（手動入力。NULLの場合は未計算）''',
            schema_record.schema_name
        );
        EXECUTE format(
            'COMMENT ON COLUMN %I.invoices.duty_policy_snapshot IS '
            '''C-6: 発行時点の関税ポリシースナップショット''',
            schema_record.schema_name
        );
        EXECUTE format(
            'COMMENT ON COLUMN %I.invoices.fx_rate_snapshot IS '
            '''C-7: 発行時点の為替レートスナップショット。形式: {"currency":"USD","rate":150.25,"fetched_at":"2026-06-04T10:00:00Z"}''',
            schema_record.schema_name
        );

        -- quote_items: hs_code 列追加
        EXECUTE format(
            'ALTER TABLE %I.quote_items
             ADD COLUMN IF NOT EXISTS hs_code VARCHAR(20)',
            schema_record.schema_name
        );
        EXECUTE format(
            'COMMENT ON COLUMN %I.quote_items.hs_code IS '
            '''C-6: 輸出用 HS コード（Harmonized System）''',
            schema_record.schema_name
        );

        -- invoice_items: hs_code 列追加
        EXECUTE format(
            'ALTER TABLE %I.invoice_items
             ADD COLUMN IF NOT EXISTS hs_code VARCHAR(20)',
            schema_record.schema_name
        );
        EXECUTE format(
            'COMMENT ON COLUMN %I.invoice_items.hs_code IS '
            '''C-6: 輸出用 HS コード（Harmonized System）''',
            schema_record.schema_name
        );
    END LOOP;
END
$$;
