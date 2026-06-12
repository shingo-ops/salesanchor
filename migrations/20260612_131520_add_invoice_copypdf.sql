-- Migration: invoices に「PayPal 請求書の写しPDF」関連列を追加（全テナント）
--
-- 目的 (ADR-101 改訂(2) / Inc1):
--   PayPal 正規請求書（Invoicing）の送信成功時に、原本と同一内容の写しPDFを自動生成・DB保存し、
--   発行者ビュー（invoicer_view_url）をアプリからワンクリックで開けるようにする。
--
-- 影響テーブル: {tenant_NNN}.invoices
-- 適用対象: 全テナント（pg_namespace 走査で冪等適用）
-- 冪等・安全: ADD COLUMN IF NOT EXISTS（nullable 追加のみ・既存データ不変・破壊操作なし）
--   ※ paypal_copy_pdf(BYTEA) は通常クエリ(_INVOICE_COLUMNS)に含めず、専用 endpoint で個別取得する。

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
        -- 対象テナントに invoices が無ければスキップ（後発テナントの不整合ガード）
        IF to_regclass(format('%I.invoices', schema_record.schema_name)) IS NULL THEN
            RAISE NOTICE 'skip (no invoices): %', schema_record.schema_name;
            CONTINUE;
        END IF;

        RAISE NOTICE 'Processing schema: %', schema_record.schema_name;

        EXECUTE format(
            'ALTER TABLE %I.invoices
             ADD COLUMN IF NOT EXISTS paypal_invoicer_view_url TEXT,
             ADD COLUMN IF NOT EXISTS paypal_copy_pdf          BYTEA,
             ADD COLUMN IF NOT EXISTS paypal_copy_pdf_at       TIMESTAMPTZ',
            schema_record.schema_name
        );

        EXECUTE format(
            'COMMENT ON COLUMN %I.invoices.paypal_invoicer_view_url IS '
            '''ADR-101改訂(2): PayPal 請求書の発行者ビュー URL（原本ワンクリック導線）''',
            schema_record.schema_name
        );
        EXECUTE format(
            'COMMENT ON COLUMN %I.invoices.paypal_copy_pdf IS '
            '''ADR-101改訂(2): 送信時に自動生成した写しPDF（reportlab・原本リンク+QR入り）。_INVOICE_COLUMNS には載せない''',
            schema_record.schema_name
        );
        EXECUTE format(
            'COMMENT ON COLUMN %I.invoices.paypal_copy_pdf_at IS '
            '''ADR-101改訂(2): 写しPDF を生成・保存した日時''',
            schema_record.schema_name
        );
    END LOOP;
END
$$;
