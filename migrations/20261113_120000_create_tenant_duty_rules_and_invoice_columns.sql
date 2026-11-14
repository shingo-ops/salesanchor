-- invoice-create-portfolio 便A: 関税の額の表 2 つと、請求書の 5 列を作る（作るだけ・冪等）
--
-- 設計: docs/handoff/invoice-create-portfolio/design.md §3-3（関税）・§3-5（請求書の列）
-- 中身（各テナントのスキーマ）:
--   tenant_duty_rules              関税の決まり（行き先の国・送料の会社・有効期間・根拠の URL。DDP のときに使う）
--   tenant_duty_rule_components    関税の決まりの中身（関税・手数料などの率と下限・上限）
--   invoices.payment_method_id         請求書で案内した振込先の版の番号（外部キーなし。版は消えない。ADR-1079）
--   invoices.tax_rate_percent          使った消費税の率
--   invoices.shipping_carrier          送料の会社
--   invoices.shipping_service          送料のサービス名
--   invoices.shipping_snapshot         送料の元の額・元の通貨・換算の率・出どころ
-- 関税の条件（DAP・DDU・DDP）の正本は tenant_settings.duty_incoterms だけ。この表には条件の列を持たない。
-- ADR-155: 構造変更のみ。値は入れない。
-- GRANT は ALTER DEFAULT PRIVILEGES（20260605_040000）で自動付与される。
-- 新しい会社のスキーマは backend/app/services/tenant.py の _TENANT_TABLES_SQL で同じ形に作る。
-- ロック待ち: run_all_migrations.sh の run_sql が PGOPTIONS で lock_timeout を付ける（既定 1s・ADR-1037）。
--
-- ロールバック（この順・各テナント）:
--   DROP TABLE IF EXISTS <tenant>.tenant_duty_rule_components;
--   DROP TABLE IF EXISTS <tenant>.tenant_duty_rules;
--   ALTER TABLE <tenant>.invoices DROP COLUMN IF EXISTS payment_method_id, DROP COLUMN IF EXISTS tax_rate_percent,
--     DROP COLUMN IF EXISTS shipping_carrier,
--     DROP COLUMN IF EXISTS shipping_service, DROP COLUMN IF EXISTS shipping_snapshot;

DO $$
DECLARE
    r RECORD;
    tid INT;
BEGIN
    FOR r IN
        SELECT nspname FROM pg_namespace
        WHERE nspname ~ '^tenant_[0-9]+$'
        ORDER BY nspname
    LOOP
        tid := regexp_replace(r.nspname, '\D', '', 'g')::INT;

        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS %I.tenant_duty_rules (
                id SERIAL PRIMARY KEY,
                tenant_id INTEGER NOT NULL DEFAULT %s,
                destination_country_code CHAR(2) NOT NULL,
                carrier VARCHAR(50),
                label TEXT NOT NULL,
                effective_from DATE NOT NULL,
                effective_to DATE,
                source_url TEXT NOT NULL,
                note TEXT,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                CONSTRAINT chk_tenant_duty_rules_country CHECK (destination_country_code ~ ''^[A-Z]{2}$''),
                CONSTRAINT chk_tenant_duty_rules_carrier CHECK (carrier IS NULL OR (carrier = lower(btrim(carrier)) AND carrier <> '''')),
                CONSTRAINT chk_tenant_duty_rules_label CHECK (btrim(label) <> ''''),
                CONSTRAINT chk_tenant_duty_rules_source_url CHECK (btrim(source_url) <> ''''),
                CONSTRAINT chk_tenant_duty_rules_period CHECK (effective_to IS NULL OR effective_to >= effective_from)
            )',
            r.nspname, tid
        );
        EXECUTE format(
            'CREATE INDEX IF NOT EXISTS idx_tenant_duty_rules_country_carrier ON %I.tenant_duty_rules (destination_country_code, carrier)',
            r.nspname
        );
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS %I.tenant_duty_rule_components (
                id SERIAL PRIMARY KEY,
                rule_id INTEGER NOT NULL REFERENCES %I.tenant_duty_rules(id) ON DELETE CASCADE,
                tenant_id INTEGER NOT NULL DEFAULT %s,
                sort_order INTEGER NOT NULL DEFAULT 0,
                label TEXT NOT NULL,
                base VARCHAR(30) NOT NULL,
                rate_pct NUMERIC(8, 4) NOT NULL,
                min_amount NUMERIC(14, 2),
                max_amount NUMERIC(14, 2),
                amount_currency CHAR(3),
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                CONSTRAINT chk_tenant_duty_rule_components_label CHECK (btrim(label) <> ''''),
                CONSTRAINT chk_tenant_duty_rule_components_base CHECK (base IN (''subtotal'', ''subtotal_shipping'', ''subtotal_shipping_prior'')),
                CONSTRAINT chk_tenant_duty_rule_components_rate CHECK (rate_pct >= 0),
                CONSTRAINT chk_tenant_duty_rule_components_amounts CHECK ((min_amount IS NULL OR min_amount >= 0) AND (max_amount IS NULL OR max_amount >= 0) AND (min_amount IS NULL OR max_amount IS NULL OR min_amount <= max_amount)),
                CONSTRAINT chk_tenant_duty_rule_components_currency CHECK (amount_currency IS NULL OR amount_currency ~ ''^[A-Z]{3}$''),
                CONSTRAINT chk_tenant_duty_rule_components_currency_required CHECK ((min_amount IS NULL AND max_amount IS NULL) OR amount_currency IS NOT NULL)
            )',
            r.nspname, r.nspname, tid
        );
        EXECUTE format(
            'CREATE INDEX IF NOT EXISTS idx_tenant_duty_rule_components_rule_id ON %I.tenant_duty_rule_components (rule_id)',
            r.nspname
        );

        EXECUTE format('ALTER TABLE %I.tenant_duty_rules ENABLE ROW LEVEL SECURITY', r.nspname);
        EXECUTE format('ALTER TABLE %I.tenant_duty_rule_components ENABLE ROW LEVEL SECURITY', r.nspname);

        IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_duty_rules_tenant_isolation' AND schemaname = r.nspname) THEN
            EXECUTE format('CREATE POLICY tenant_duty_rules_tenant_isolation ON %I.tenant_duty_rules USING (tenant_id = current_setting(''app.tenant_id'', true)::INTEGER)', r.nspname);
        END IF;
        IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_duty_rule_components_tenant_isolation' AND schemaname = r.nspname) THEN
            EXECUTE format('CREATE POLICY tenant_duty_rule_components_tenant_isolation ON %I.tenant_duty_rule_components USING (tenant_id = current_setting(''app.tenant_id'', true)::INTEGER)', r.nspname);
        END IF;

        IF to_regclass(format('%I.invoices', r.nspname)) IS NOT NULL THEN
            EXECUTE format('ALTER TABLE %I.invoices ADD COLUMN IF NOT EXISTS payment_method_id INTEGER', r.nspname);
            EXECUTE format('ALTER TABLE %I.invoices ADD COLUMN IF NOT EXISTS tax_rate_percent NUMERIC(5, 2)', r.nspname);
            EXECUTE format('ALTER TABLE %I.invoices ADD COLUMN IF NOT EXISTS shipping_carrier VARCHAR(50)', r.nspname);
            EXECUTE format('ALTER TABLE %I.invoices ADD COLUMN IF NOT EXISTS shipping_service VARCHAR(100)', r.nspname);
            EXECUTE format('ALTER TABLE %I.invoices ADD COLUMN IF NOT EXISTS shipping_snapshot JSONB', r.nspname);
            EXECUTE format('COMMENT ON COLUMN %I.invoices.payment_method_id IS %L', r.nspname, '請求書で案内した振込先の版の番号（振込先の一覧の id。版は消えない。外部キーは張らない。PayPal は NULL）');
            EXECUTE format('COMMENT ON COLUMN %I.invoices.tax_rate_percent IS %L', r.nspname, '計算に使った消費税の率（パーセント。日本宛のときだけ）');
            EXECUTE format('COMMENT ON COLUMN %I.invoices.shipping_snapshot IS %L', r.nspname, '送料の元の額・元の通貨・換算の率・出どころ（calculate / quote / none）');
        END IF;

        EXECUTE format('COMMENT ON TABLE %I.tenant_duty_rules IS %L', r.nspname, '関税の決まり。関税の条件が DDP のときに、行き先の国と送料の会社ごとに請求する額の決まり');
        EXECUTE format('COMMENT ON COLUMN %I.tenant_duty_rules.carrier IS %L', r.nspname, '送料の会社（小文字・前後の空白なし）。NULL はどの会社でも');
        EXECUTE format('COMMENT ON COLUMN %I.tenant_duty_rules.source_url IS %L', r.nspname, '額の根拠の URL（空は不可）');
        EXECUTE format('COMMENT ON TABLE %I.tenant_duty_rule_components IS %L', r.nspname, '関税の決まりの中身（関税・手数料など）。sort_order の順に計算する');
        EXECUTE format('COMMENT ON COLUMN %I.tenant_duty_rule_components.base IS %L', r.nspname, 'subtotal=小計 / subtotal_shipping=小計+送料 / subtotal_shipping_prior=小計+送料+前の中身の合計');
        EXECUTE format('COMMENT ON COLUMN %I.tenant_duty_rule_components.amount_currency IS %L', r.nspname, '下限・上限の通貨（英大文字3字。下限か上限があるときは必須）');
        RAISE NOTICE 'duty rule tables and invoice columns created/verified for schema: %', r.nspname;
    END LOOP;
END $$;
