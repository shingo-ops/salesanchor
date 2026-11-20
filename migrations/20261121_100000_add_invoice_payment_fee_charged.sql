-- invoice-create-portfolio 便E（design-e.md §3-4）: お客様への合計に足した支払い手数料と、その計算の写しを全テナントの invoices に足す。値は書かない。冪等。
--
-- 列（NULL 可・既定値なし）:
--   invoices.payment_fee_charged   NUMERIC(15, 2)  お客様への合計に足した支払い手数料（請求書の通貨）
--   invoices.payment_fee_snapshot  JSONB           手数料の計算に使った設定の行と値の写し
-- 既存の invoices.payment_fee（入金時に PayPal が引いた実額）には触らない。
-- 新しい会社のスキーマは backend/app/services/tenant.py の _TENANT_TABLES_SQL で同じ形に作る。

DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN
        SELECT nspname FROM pg_namespace WHERE nspname ~ '^tenant_[0-9]+$'
    LOOP
        IF to_regclass(format('%I.invoices', r.nspname)) IS NULL THEN
            CONTINUE;
        END IF;

        EXECUTE format('ALTER TABLE %I.invoices ADD COLUMN IF NOT EXISTS payment_fee_charged NUMERIC(15, 2)', r.nspname);
        EXECUTE format('ALTER TABLE %I.invoices ADD COLUMN IF NOT EXISTS payment_fee_snapshot JSONB', r.nspname);
        EXECUTE format('COMMENT ON COLUMN %I.invoices.payment_fee_charged IS %L', r.nspname, 'お客様への合計に足した支払い手数料（請求書の通貨）。入金時の実額は payment_fee');
        EXECUTE format('COMMENT ON COLUMN %I.invoices.payment_fee_snapshot IS %L', r.nspname, '手数料の計算に使った設定の行と値の写し');
        RAISE NOTICE 'invoice payment_fee_charged columns created/verified for schema: %', r.nspname;
    END LOOP;
END $$;
