-- viewer-contract-stage 2-2c1: 発行元の会社情報と振込先の表 4 つ、請求書の発行元区分の列、海外用の保存フォルダの列を作る（作るだけ・冪等）
--
-- 設計: docs/handoff/viewer-contract-stage/design.md §3-4（ADR-1061）
-- 中身（各テナントのスキーマ）:
--   tenant_issuer_profiles           発行元の会社情報（国内用・海外用の 2 行まで）
--   tenant_invoice_payment_methods   振込先の一覧（銀行・Wise）
--   tenant_invoice_payment_bank      銀行振込先の詳細
--   tenant_invoice_payment_wise      Wise 振込先の詳細
--   invoices.issuer_region           請求書がどちらの発行元で出たか（domestic / overseas）
-- 中身（public）:
--   tenant_google_drive_config.overseas_folder_id   海外用の保存フォルダの番号
-- ADR-155: 構造変更のみ。値は入れない。
-- GRANT は ALTER DEFAULT PRIVILEGES（20260605_040000）で自動付与される。
-- 新しい会社のスキーマは backend/app/services/tenant.py の _TENANT_TABLES_SQL で同じ形に作る。
-- ロック待ち: run_all_migrations.sh の run_sql が PGOPTIONS で lock_timeout を付ける（既定 1s・ADR-1037）。
--
-- ロールバック（この順・各テナント）:
--   DROP TABLE IF EXISTS <tenant>.tenant_invoice_payment_wise;
--   DROP TABLE IF EXISTS <tenant>.tenant_invoice_payment_bank;
--   DROP TABLE IF EXISTS <tenant>.tenant_invoice_payment_methods;
--   DROP TABLE IF EXISTS <tenant>.tenant_issuer_profiles;
--   ALTER TABLE <tenant>.invoices DROP CONSTRAINT IF EXISTS chk_invoices_issuer_region;
--   ALTER TABLE <tenant>.invoices DROP COLUMN IF EXISTS issuer_region;
--   ALTER TABLE public.tenant_google_drive_config DROP COLUMN IF EXISTS overseas_folder_id;

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
            'CREATE TABLE IF NOT EXISTS %I.tenant_issuer_profiles (
                id SERIAL PRIMARY KEY,
                tenant_id INTEGER NOT NULL DEFAULT %s,
                region VARCHAR(20) NOT NULL,
                company_name VARCHAR(255) NOT NULL,
                email VARCHAR(255),
                website VARCHAR(255),
                country_code CHAR(2) NOT NULL REFERENCES public.countries(code),
                postal_code VARCHAR(10),
                prefecture_code CHAR(2) REFERENCES public.prefectures(code),
                state_region TEXT,
                city TEXT NOT NULL,
                address1 TEXT NOT NULL,
                address2 TEXT,
                phone VARCHAR(16),
                is_invoice_registered BOOLEAN NOT NULL DEFAULT FALSE,
                registration_number VARCHAR(14),
                updated_by_user_id INTEGER,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                CONSTRAINT uq_tenant_issuer_profiles_tenant_region UNIQUE (tenant_id, region),
                CONSTRAINT chk_tenant_issuer_profiles_region CHECK (region IN (''domestic'', ''overseas'')),
                CONSTRAINT chk_tenant_issuer_profiles_company_name CHECK (btrim(company_name) <> ''''),
                CONSTRAINT chk_tenant_issuer_profiles_city CHECK (btrim(city) <> ''''),
                CONSTRAINT chk_tenant_issuer_profiles_address1 CHECK (btrim(address1) <> ''''),
                CONSTRAINT chk_tenant_issuer_profiles_jp_address CHECK (country_code <> ''JP'' OR (postal_code IS NOT NULL AND postal_code ~ ''^[0-9]{7}$'' AND prefecture_code IS NOT NULL AND state_region IS NULL)),
                CONSTRAINT chk_tenant_issuer_profiles_foreign_address CHECK (country_code = ''JP'' OR (prefecture_code IS NULL AND (postal_code IS NULL OR postal_code ~ ''^[0-9A-Za-z -]{1,10}$''))),
                CONSTRAINT chk_tenant_issuer_profiles_phone CHECK (phone IS NULL OR (country_code = ''JP'' AND phone ~ ''^[0-9]{10,11}$'') OR (country_code <> ''JP'' AND phone ~ ''^\+[0-9]{6,15}$'')),
                CONSTRAINT chk_tenant_issuer_profiles_registration CHECK ((is_invoice_registered AND registration_number IS NOT NULL AND registration_number ~ ''^T[0-9]{13}$'') OR (NOT is_invoice_registered AND registration_number IS NULL))
            )',
            r.nspname, tid
        );
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS %I.tenant_invoice_payment_methods (
                id SERIAL PRIMARY KEY,
                tenant_id INTEGER NOT NULL DEFAULT %s,
                region VARCHAR(20) NOT NULL,
                method_type VARCHAR(10) NOT NULL,
                display_name TEXT NOT NULL,
                sort_order INTEGER NOT NULL DEFAULT 0,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                updated_by_user_id INTEGER,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                CONSTRAINT uq_tenant_invoice_payment_methods_id_type UNIQUE (id, tenant_id, method_type),
                CONSTRAINT chk_tenant_invoice_payment_methods_region CHECK (region IN (''domestic'', ''overseas'')),
                CONSTRAINT chk_tenant_invoice_payment_methods_method_type CHECK (method_type IN (''bank'', ''wise'')),
                CONSTRAINT chk_tenant_invoice_payment_methods_display_name CHECK (btrim(display_name) <> '''')
            )',
            r.nspname, tid
        );
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS %I.tenant_invoice_payment_bank (
                payment_method_id INTEGER PRIMARY KEY,
                method_type VARCHAR(10) NOT NULL DEFAULT ''bank'',
                tenant_id INTEGER NOT NULL DEFAULT %s,
                account_holder TEXT NOT NULL,
                bank_name TEXT NOT NULL,
                bank_branch TEXT NOT NULL,
                bank_account_type TEXT NOT NULL,
                bank_account_number TEXT NOT NULL,
                swift_code TEXT,
                bank_address TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                CONSTRAINT chk_tenant_invoice_payment_bank_method_type CHECK (method_type = ''bank''),
                CONSTRAINT chk_tenant_invoice_payment_bank_required CHECK (btrim(account_holder) <> '''' AND btrim(bank_name) <> '''' AND btrim(bank_branch) <> '''' AND btrim(bank_account_type) <> '''' AND btrim(bank_account_number) <> ''''),
                CONSTRAINT fk_tenant_invoice_payment_bank_method FOREIGN KEY (payment_method_id, tenant_id, method_type) REFERENCES %I.tenant_invoice_payment_methods (id, tenant_id, method_type) ON DELETE CASCADE
            )',
            r.nspname, tid, r.nspname
        );
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS %I.tenant_invoice_payment_wise (
                payment_method_id INTEGER PRIMARY KEY,
                method_type VARCHAR(10) NOT NULL DEFAULT ''wise'',
                tenant_id INTEGER NOT NULL DEFAULT %s,
                account_holder TEXT NOT NULL,
                wise_currency CHAR(3) NOT NULL,
                wise_email VARCHAR(255) NOT NULL,
                iban TEXT,
                swift_bic TEXT,
                bank_name TEXT,
                bank_address TEXT,
                note TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                CONSTRAINT chk_tenant_invoice_payment_wise_method_type CHECK (method_type = ''wise''),
                CONSTRAINT chk_tenant_invoice_payment_wise_currency CHECK (wise_currency ~ ''^[A-Z]{3}$''),
                CONSTRAINT chk_tenant_invoice_payment_wise_required CHECK (btrim(account_holder) <> '''' AND btrim(wise_email) <> ''''),
                CONSTRAINT fk_tenant_invoice_payment_wise_method FOREIGN KEY (payment_method_id, tenant_id, method_type) REFERENCES %I.tenant_invoice_payment_methods (id, tenant_id, method_type) ON DELETE CASCADE
            )',
            r.nspname, tid, r.nspname
        );

        EXECUTE format('ALTER TABLE %I.tenant_issuer_profiles ENABLE ROW LEVEL SECURITY', r.nspname);
        EXECUTE format('ALTER TABLE %I.tenant_invoice_payment_methods ENABLE ROW LEVEL SECURITY', r.nspname);
        EXECUTE format('ALTER TABLE %I.tenant_invoice_payment_bank ENABLE ROW LEVEL SECURITY', r.nspname);
        EXECUTE format('ALTER TABLE %I.tenant_invoice_payment_wise ENABLE ROW LEVEL SECURITY', r.nspname);

        IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_issuer_profiles_tenant_isolation' AND schemaname = r.nspname) THEN
            EXECUTE format('CREATE POLICY tenant_issuer_profiles_tenant_isolation ON %I.tenant_issuer_profiles USING (tenant_id = current_setting(''app.tenant_id'', true)::INTEGER)', r.nspname);
        END IF;
        IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_invoice_payment_methods_tenant_isolation' AND schemaname = r.nspname) THEN
            EXECUTE format('CREATE POLICY tenant_invoice_payment_methods_tenant_isolation ON %I.tenant_invoice_payment_methods USING (tenant_id = current_setting(''app.tenant_id'', true)::INTEGER)', r.nspname);
        END IF;
        IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_invoice_payment_bank_tenant_isolation' AND schemaname = r.nspname) THEN
            EXECUTE format('CREATE POLICY tenant_invoice_payment_bank_tenant_isolation ON %I.tenant_invoice_payment_bank USING (tenant_id = current_setting(''app.tenant_id'', true)::INTEGER)', r.nspname);
        END IF;
        IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_invoice_payment_wise_tenant_isolation' AND schemaname = r.nspname) THEN
            EXECUTE format('CREATE POLICY tenant_invoice_payment_wise_tenant_isolation ON %I.tenant_invoice_payment_wise USING (tenant_id = current_setting(''app.tenant_id'', true)::INTEGER)', r.nspname);
        END IF;

        IF to_regclass(format('%I.invoices', r.nspname)) IS NOT NULL THEN
            EXECUTE format('ALTER TABLE %I.invoices ADD COLUMN IF NOT EXISTS issuer_region VARCHAR(20)', r.nspname);
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_invoices_issuer_region' AND conrelid = to_regclass(format('%I.invoices', r.nspname))) THEN
                EXECUTE format('ALTER TABLE %I.invoices ADD CONSTRAINT chk_invoices_issuer_region CHECK (issuer_region IN (''domestic'', ''overseas''))', r.nspname);
            END IF;
            EXECUTE format('COMMENT ON COLUMN %I.invoices.issuer_region IS %L', r.nspname, '請求書を出した発行元の区分（domestic=国内用 / overseas=海外用。NULL は区分を付ける前の請求書）');
        END IF;

        EXECUTE format('COMMENT ON TABLE %I.tenant_issuer_profiles IS %L', r.nspname, '発行元の会社情報。国内用と海外用の 2 行まで（ADR-1061）');
        EXECUTE format('COMMENT ON COLUMN %I.tenant_issuer_profiles.region IS %L', r.nspname, 'domestic=国内用 / overseas=海外用');
        EXECUTE format('COMMENT ON COLUMN %I.tenant_issuer_profiles.country_code IS %L', r.nspname, '国の2文字コード（国マスタの code）');
        EXECUTE format('COMMENT ON COLUMN %I.tenant_issuer_profiles.prefecture_code IS %L', r.nspname, '都道府県の2桁コード（日本のときだけ必須）');
        EXECUTE format('COMMENT ON COLUMN %I.tenant_issuer_profiles.state_region IS %L', r.nspname, '海外の州・地域（日本のときは空）');
        EXECUTE format('COMMENT ON COLUMN %I.tenant_issuer_profiles.registration_number IS %L', r.nspname, '適格請求書の登録番号 T+13桁（登録しているときだけ）');
        EXECUTE format('COMMENT ON TABLE %I.tenant_invoice_payment_methods IS %L', r.nspname, '請求書に載せる振込先の一覧（銀行・Wise）');
        EXECUTE format('COMMENT ON COLUMN %I.tenant_invoice_payment_methods.method_type IS %L', r.nspname, 'bank=銀行振込 / wise=Wise');
        EXECUTE format('COMMENT ON TABLE %I.tenant_invoice_payment_bank IS %L', r.nspname, '銀行振込先の詳細（振込先の一覧 1 行に 1 行）');
        EXECUTE format('COMMENT ON TABLE %I.tenant_invoice_payment_wise IS %L', r.nspname, 'Wise 振込先の詳細（振込先の一覧 1 行に 1 行）');
        EXECUTE format('COMMENT ON COLUMN %I.tenant_invoice_payment_wise.wise_currency IS %L', r.nspname, '受け取る通貨の記号（英大文字3字）');
        RAISE NOTICE 'issuer and payment tables created/verified for schema: %', r.nspname;
    END LOOP;
END $$;

DO $$
BEGIN
    IF to_regclass('public.tenant_google_drive_config') IS NOT NULL THEN
        ALTER TABLE public.tenant_google_drive_config ADD COLUMN IF NOT EXISTS overseas_folder_id TEXT;
        COMMENT ON COLUMN public.tenant_google_drive_config.overseas_folder_id IS '海外用の請求書・見積書を保存する Google ドライブのフォルダの番号（NULL は国内用と同じフォルダ）';
    END IF;
END $$;
