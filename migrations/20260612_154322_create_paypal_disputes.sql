-- Migration: 各テナントに paypal_disputes テーブルを作成（ADR-101 改訂(2) Inc4 Step A）
--
-- 目的: PayPal のケース(dispute)を webhook で受信して保存・請求書/受注に紐づけ表示する基盤。
--   本 migration はスキーマのみ（自社列・payload 前提に依存しない）。受信ハンドラは follow-up。
--
-- 影響: {tenant_NNN}.paypal_disputes（新規）。全テナントに冪等作成。破壊操作なし。

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
        -- invoices が無いテナント（後発・未整備）はスキップ（FK 整合ガード）
        IF to_regclass(format('%I.invoices', schema_record.schema_name)) IS NULL THEN
            RAISE NOTICE 'skip (no invoices): %', schema_record.schema_name;
            CONTINUE;
        END IF;

        EXECUTE format($f$
            CREATE TABLE IF NOT EXISTS %I.paypal_disputes (
                id           SERIAL PRIMARY KEY,
                dispute_id   TEXT NOT NULL UNIQUE,
                invoice_id   INTEGER REFERENCES %I.invoices(id) ON DELETE SET NULL,
                pp_status    TEXT,
                reason       TEXT,
                amount       NUMERIC(15,2),
                currency     TEXT,
                raw          JSONB,
                created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        $f$, schema_record.schema_name, schema_record.schema_name);

        EXECUTE format(
            'CREATE INDEX IF NOT EXISTS idx_paypal_disputes_invoice ON %I.paypal_disputes(invoice_id)',
            schema_record.schema_name
        );
    END LOOP;
END
$$;
