-- ADR-1061 便2-2a: 契約と請求書の public の9表を作る（形だけ。行は入れない）
-- 設計: docs/handoff/viewer-contract-stage/design.md §3-4・RLS :297〜:310
-- RLS: 9表とも ENABLE と FORCE。読むのは全行可、書くのは app.is_operator='true' のときだけ（ADR-1018 Decision 3。先例 20260628_170000_add_app_fx_rates.sql:51〜:63）
-- 冪等: 表と索引は IF NOT EXISTS。CHECK は表を作る文の中に書く（表が在れば文ごと飛ぶ）。方針は DROP POLICY IF EXISTS の後に作る
-- ロールバック: 表は残してコードが使わない（表を消すのは別便・PO GO）

BEGIN;

-- 都道府県（JIS X 0401 の 01〜47）。47行は別の1回だけのデータの変更で入れる（design.md :182）
CREATE TABLE IF NOT EXISTS public.prefectures (
    code CHAR(2) PRIMARY KEY,
    name_ja TEXT NOT NULL,
    name_en TEXT NOT NULL,
    sort_order INTEGER NOT NULL,
    CONSTRAINT ck_prefectures_code CHECK (code ~ '^(0[1-9]|[1-3][0-9]|4[0-7])$'),
    CONSTRAINT ck_prefectures_name_ja CHECK (char_length(btrim(name_ja)) BETWEEN 1 AND 20),
    CONSTRAINT ck_prefectures_name_en CHECK (char_length(btrim(name_en)) BETWEEN 1 AND 40)
);

-- 商材
CREATE TABLE IF NOT EXISTS public.sa_products (
    id BIGSERIAL PRIMARY KEY,
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    seller_tenant_id INTEGER NOT NULL REFERENCES public.tenants(id) ON DELETE RESTRICT,
    default_payment_days INTEGER NOT NULL DEFAULT 3,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_sa_products_code UNIQUE (code),
    CONSTRAINT ck_sa_products_code CHECK (code ~ '^[a-z0-9][a-z0-9_-]{0,49}$'),
    CONSTRAINT ck_sa_products_name CHECK (char_length(btrim(name)) BETWEEN 1 AND 100),
    CONSTRAINT ck_sa_products_default_payment_days CHECK (default_payment_days BETWEEN 1 AND 90)
);

-- プラン
CREATE TABLE IF NOT EXISTS public.sa_plans (
    id BIGSERIAL PRIMARY KEY,
    product_id BIGINT NOT NULL REFERENCES public.sa_products(id) ON DELETE RESTRICT,
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    billing_type TEXT NOT NULL,
    billing_interval TEXT NULL,
    unit_price_jpy BIGINT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_sa_plans_product_code UNIQUE (product_id, code),
    CONSTRAINT ck_sa_plans_code CHECK (code ~ '^[a-z0-9][a-z0-9_-]{0,49}$'),
    CONSTRAINT ck_sa_plans_name CHECK (char_length(btrim(name)) BETWEEN 1 AND 100),
    CONSTRAINT ck_sa_plans_billing_type CHECK (billing_type IN ('one_time', 'subscription')),
    CONSTRAINT ck_sa_plans_billing_interval CHECK (
        (billing_type = 'one_time' AND billing_interval IS NULL)
        OR (billing_type = 'subscription' AND billing_interval IN ('month', 'year'))
    ),
    CONSTRAINT ck_sa_plans_unit_price_jpy CHECK (unit_price_jpy >= 0)
);

-- プランに含む機能（この CHECK が機能の一覧の正本。design.md §3-4）
CREATE TABLE IF NOT EXISTS public.sa_plan_features (
    plan_id BIGINT NOT NULL REFERENCES public.sa_plans(id) ON DELETE CASCADE,
    feature_key TEXT NOT NULL,
    PRIMARY KEY (plan_id, feature_key),
    CONSTRAINT ck_sa_plan_features_feature_key CHECK (feature_key IN ('inventory_view', 'sheet_distribution'))
);

-- 契約（何を売ったかの記録。閲覧者の状態の正本は viewer_accounts.status）
CREATE TABLE IF NOT EXISTS public.sa_contracts (
    id BIGSERIAL PRIMARY KEY,
    plan_id BIGINT NOT NULL REFERENCES public.sa_plans(id) ON DELETE RESTRICT,
    viewer_account_id BIGINT NULL REFERENCES public.viewer_accounts(id) ON DELETE SET NULL,
    tenant_id INTEGER NULL REFERENCES public.tenants(id) ON DELETE SET NULL,
    status TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    activated_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_sa_contracts_status CHECK (status IN ('in_progress', 'active', 'cancelled'))
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_sa_contracts_open_viewer_plan
    ON public.sa_contracts (viewer_account_id, plan_id)
    WHERE status IN ('in_progress', 'active');

-- 税率（行を足すだけ。最初の行は本番反映の後に PO が画面で足す）
CREATE TABLE IF NOT EXISTS public.tax_rates (
    id BIGSERIAL PRIMARY KEY,
    rate_percent NUMERIC(5, 2) NOT NULL,
    effective_from DATE NOT NULL,
    created_by_user_id INTEGER NULL REFERENCES public.users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_tax_rates_effective_from UNIQUE (effective_from),
    CONSTRAINT ck_tax_rates_rate_percent CHECK (rate_percent >= 0 AND rate_percent <= 100)
);

-- 請求書
CREATE TABLE IF NOT EXISTS public.viewer_invoices (
    id BIGSERIAL PRIMARY KEY,
    invoice_number TEXT NOT NULL,
    contract_id BIGINT NULL REFERENCES public.sa_contracts(id) ON DELETE SET NULL,
    viewer_account_id BIGINT NULL REFERENCES public.viewer_accounts(id) ON DELETE SET NULL,
    status TEXT NOT NULL,
    replaces_invoice_id BIGINT NULL REFERENCES public.viewer_invoices(id) ON DELETE SET NULL,
    issued_at TIMESTAMPTZ NOT NULL,
    due_date DATE NOT NULL,
    paid_at DATE NULL,
    paid_confirmed_by_user_id INTEGER NULL REFERENCES public.users(id) ON DELETE SET NULL,
    voided_at TIMESTAMPTZ NULL,
    subtotal_jpy BIGINT NOT NULL,
    discount_total_jpy BIGINT NOT NULL DEFAULT 0,
    taxable_jpy BIGINT NOT NULL,
    tax_rate_percent NUMERIC(5, 2) NOT NULL,
    tax_amount_jpy BIGINT NOT NULL,
    total_jpy BIGINT NOT NULL,
    bill_to_snapshot JSONB NOT NULL,
    issuer_snapshot JSONB NOT NULL,
    mail_to TEXT NULL,
    mail_sent_at TIMESTAMPTZ NULL,
    mail_error TEXT NULL,
    drive_file_id TEXT NULL,
    drive_web_link TEXT NULL,
    drive_saved_at TIMESTAMPTZ NULL,
    drive_error TEXT NULL,
    created_by_user_id INTEGER NULL REFERENCES public.users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_viewer_invoices_invoice_number UNIQUE (invoice_number),
    CONSTRAINT ck_viewer_invoices_status CHECK (status IN ('issued', 'paid', 'voided')),
    CONSTRAINT ck_viewer_invoices_amounts_nonnegative CHECK (
        subtotal_jpy >= 0 AND discount_total_jpy >= 0 AND taxable_jpy >= 0
        AND tax_amount_jpy >= 0 AND total_jpy >= 0
    ),
    CONSTRAINT ck_viewer_invoices_discount_le_subtotal CHECK (discount_total_jpy <= subtotal_jpy),
    CONSTRAINT ck_viewer_invoices_taxable CHECK (taxable_jpy = subtotal_jpy - discount_total_jpy),
    CONSTRAINT ck_viewer_invoices_total CHECK (total_jpy = taxable_jpy + tax_amount_jpy),
    CONSTRAINT ck_viewer_invoices_tax_rate_percent CHECK (tax_rate_percent >= 0 AND tax_rate_percent <= 100)
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_viewer_invoices_issued_contract
    ON public.viewer_invoices (contract_id)
    WHERE status = 'issued';

-- 請求書の番号の年ごとの採番
CREATE TABLE IF NOT EXISTS public.viewer_invoice_number_seq (
    year INTEGER PRIMARY KEY,
    last_number INTEGER NOT NULL,
    CONSTRAINT ck_viewer_invoice_number_seq_year CHECK (year BETWEEN 2000 AND 9999),
    CONSTRAINT ck_viewer_invoice_number_seq_last_number CHECK (last_number >= 0)
);

-- 請求書の明細（ADR-101 の2表に分ける形）
CREATE TABLE IF NOT EXISTS public.viewer_invoice_lines (
    id BIGSERIAL PRIMARY KEY,
    invoice_id BIGINT NOT NULL REFERENCES public.viewer_invoices(id) ON DELETE CASCADE,
    line_type TEXT NOT NULL,
    description TEXT NOT NULL,
    amount_jpy BIGINT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    CONSTRAINT ck_viewer_invoice_lines_line_type CHECK (line_type IN ('item', 'discount')),
    CONSTRAINT ck_viewer_invoice_lines_description CHECK (char_length(btrim(description)) BETWEEN 1 AND 200)
);

COMMENT ON TABLE public.prefectures IS '都道府県（JIS X 0401 の 01〜47）。行は1回だけのデータの変更で入れる。ADR-1061';
COMMENT ON TABLE public.sa_products IS '運営が売る商材。発行元の会社 seller_tenant_id を持つ。ADR-1061';
COMMENT ON TABLE public.sa_plans IS '商材の料金プラン（税抜の円）。ADR-1061';
COMMENT ON TABLE public.sa_plan_features IS 'プランに含む機能。feature_key の CHECK が機能の一覧の正本。ADR-1061';
COMMENT ON TABLE public.sa_contracts IS '何を売ったかの記録。閲覧者の状態の判定には使わない（正本は viewer_accounts.status）。ADR-1061';
COMMENT ON TABLE public.tax_rates IS '消費税率。行を足すだけ。請求書は発行日に有効な行の率を写す。ADR-1061';
COMMENT ON TABLE public.viewer_invoices IS '閲覧者の請求書。金額・宛先・発行元は発行時点の写し。ADR-1061';
COMMENT ON TABLE public.viewer_invoice_number_seq IS '請求書の番号の年ごとの採番（SELECT … FOR UPDATE で進める）。ADR-1061';
COMMENT ON TABLE public.viewer_invoice_lines IS '請求書の明細（item＝品目／discount＝値引き）。ADR-1061';
COMMENT ON COLUMN public.sa_products.default_payment_days IS '既定の支払日数（1〜90。既定 3）';
COMMENT ON COLUMN public.sa_plans.billing_interval IS 'month／year。one_time のときは NULL';
COMMENT ON COLUMN public.sa_contracts.tenant_id IS '将来の導入支援用。今は常に NULL';
COMMENT ON COLUMN public.tax_rates.effective_from IS 'この日から使う（日本時間の日付）。一意';
COMMENT ON COLUMN public.viewer_invoices.taxable_jpy IS '課税対象＝小計−値引き（CHECK で止める）';
COMMENT ON COLUMN public.viewer_invoices.paid_at IS '入金を確かめた日（日付だけ）';

-- RLS（9表とも同じ形）
ALTER TABLE public.prefectures ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.prefectures FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS prefectures_read ON public.prefectures;
CREATE POLICY prefectures_read ON public.prefectures FOR SELECT USING (true);
DROP POLICY IF EXISTS prefectures_write ON public.prefectures;
CREATE POLICY prefectures_write ON public.prefectures FOR ALL
    USING (current_setting('app.is_operator', true) = 'true')
    WITH CHECK (current_setting('app.is_operator', true) = 'true');

ALTER TABLE public.sa_products ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sa_products FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS sa_products_read ON public.sa_products;
CREATE POLICY sa_products_read ON public.sa_products FOR SELECT USING (true);
DROP POLICY IF EXISTS sa_products_write ON public.sa_products;
CREATE POLICY sa_products_write ON public.sa_products FOR ALL
    USING (current_setting('app.is_operator', true) = 'true')
    WITH CHECK (current_setting('app.is_operator', true) = 'true');

ALTER TABLE public.sa_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sa_plans FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS sa_plans_read ON public.sa_plans;
CREATE POLICY sa_plans_read ON public.sa_plans FOR SELECT USING (true);
DROP POLICY IF EXISTS sa_plans_write ON public.sa_plans;
CREATE POLICY sa_plans_write ON public.sa_plans FOR ALL
    USING (current_setting('app.is_operator', true) = 'true')
    WITH CHECK (current_setting('app.is_operator', true) = 'true');

ALTER TABLE public.sa_plan_features ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sa_plan_features FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS sa_plan_features_read ON public.sa_plan_features;
CREATE POLICY sa_plan_features_read ON public.sa_plan_features FOR SELECT USING (true);
DROP POLICY IF EXISTS sa_plan_features_write ON public.sa_plan_features;
CREATE POLICY sa_plan_features_write ON public.sa_plan_features FOR ALL
    USING (current_setting('app.is_operator', true) = 'true')
    WITH CHECK (current_setting('app.is_operator', true) = 'true');

ALTER TABLE public.sa_contracts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sa_contracts FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS sa_contracts_read ON public.sa_contracts;
CREATE POLICY sa_contracts_read ON public.sa_contracts FOR SELECT USING (true);
DROP POLICY IF EXISTS sa_contracts_write ON public.sa_contracts;
CREATE POLICY sa_contracts_write ON public.sa_contracts FOR ALL
    USING (current_setting('app.is_operator', true) = 'true')
    WITH CHECK (current_setting('app.is_operator', true) = 'true');

ALTER TABLE public.tax_rates ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tax_rates FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tax_rates_read ON public.tax_rates;
CREATE POLICY tax_rates_read ON public.tax_rates FOR SELECT USING (true);
DROP POLICY IF EXISTS tax_rates_write ON public.tax_rates;
CREATE POLICY tax_rates_write ON public.tax_rates FOR ALL
    USING (current_setting('app.is_operator', true) = 'true')
    WITH CHECK (current_setting('app.is_operator', true) = 'true');

ALTER TABLE public.viewer_invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.viewer_invoices FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS viewer_invoices_read ON public.viewer_invoices;
CREATE POLICY viewer_invoices_read ON public.viewer_invoices FOR SELECT USING (true);
DROP POLICY IF EXISTS viewer_invoices_write ON public.viewer_invoices;
CREATE POLICY viewer_invoices_write ON public.viewer_invoices FOR ALL
    USING (current_setting('app.is_operator', true) = 'true')
    WITH CHECK (current_setting('app.is_operator', true) = 'true');

ALTER TABLE public.viewer_invoice_number_seq ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.viewer_invoice_number_seq FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS viewer_invoice_number_seq_read ON public.viewer_invoice_number_seq;
CREATE POLICY viewer_invoice_number_seq_read ON public.viewer_invoice_number_seq FOR SELECT USING (true);
DROP POLICY IF EXISTS viewer_invoice_number_seq_write ON public.viewer_invoice_number_seq;
CREATE POLICY viewer_invoice_number_seq_write ON public.viewer_invoice_number_seq FOR ALL
    USING (current_setting('app.is_operator', true) = 'true')
    WITH CHECK (current_setting('app.is_operator', true) = 'true');

ALTER TABLE public.viewer_invoice_lines ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.viewer_invoice_lines FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS viewer_invoice_lines_read ON public.viewer_invoice_lines;
CREATE POLICY viewer_invoice_lines_read ON public.viewer_invoice_lines FOR SELECT USING (true);
DROP POLICY IF EXISTS viewer_invoice_lines_write ON public.viewer_invoice_lines;
CREATE POLICY viewer_invoice_lines_write ON public.viewer_invoice_lines FOR ALL
    USING (current_setting('app.is_operator', true) = 'true')
    WITH CHECK (current_setting('app.is_operator', true) = 'true');

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'salesanchor_app') THEN
        GRANT SELECT, INSERT, UPDATE, DELETE ON public.prefectures, public.sa_products, public.sa_plans,
            public.sa_plan_features, public.sa_contracts, public.tax_rates, public.viewer_invoices,
            public.viewer_invoice_number_seq, public.viewer_invoice_lines TO salesanchor_app;
        GRANT USAGE, SELECT ON SEQUENCE public.sa_products_id_seq, public.sa_plans_id_seq,
            public.sa_contracts_id_seq, public.tax_rates_id_seq, public.viewer_invoices_id_seq,
            public.viewer_invoice_lines_id_seq TO salesanchor_app;
    END IF;
END $$;

COMMIT;
