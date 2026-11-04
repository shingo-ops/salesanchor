-- viewer-customer-sheet 便2: 請求先（本契約のお客さんが自分で書く7項目）の置き場と、鍵の用途 billing_form の追加
-- RLS は付けない: 名簿 viewer_accounts と同じ public の全体共通の表
-- 冪等（表は IF NOT EXISTS・CHECK は pg_constraint を見て足す・用途の CHECK は付け替え）
-- ロールバック: 表は残してコードが使わない（削除は別便・PO GO）

BEGIN;

CREATE TABLE IF NOT EXISTS public.viewer_billing_profiles (
    viewer_account_id BIGINT PRIMARY KEY REFERENCES public.viewer_accounts(id) ON DELETE CASCADE,
    party_type TEXT NOT NULL,
    bill_to_name TEXT NOT NULL,
    contact_name TEXT NULL,
    postal_code TEXT NOT NULL,
    address TEXT NOT NULL,
    phone TEXT NOT NULL,
    invoice_email TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_viewer_billing_profiles_party_type') THEN
        ALTER TABLE public.viewer_billing_profiles ADD CONSTRAINT ck_viewer_billing_profiles_party_type
            CHECK (party_type IN ('company', 'individual'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_viewer_billing_profiles_bill_to_name') THEN
        ALTER TABLE public.viewer_billing_profiles ADD CONSTRAINT ck_viewer_billing_profiles_bill_to_name
            CHECK (char_length(bill_to_name) BETWEEN 1 AND 100 AND char_length(btrim(bill_to_name)) >= 1);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_viewer_billing_profiles_contact_name') THEN
        ALTER TABLE public.viewer_billing_profiles ADD CONSTRAINT ck_viewer_billing_profiles_contact_name
            CHECK ((contact_name IS NULL OR char_length(contact_name) BETWEEN 1 AND 50)
                   AND (party_type <> 'company' OR contact_name IS NOT NULL));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_viewer_billing_profiles_postal_code') THEN
        ALTER TABLE public.viewer_billing_profiles ADD CONSTRAINT ck_viewer_billing_profiles_postal_code
            CHECK (postal_code ~ '^[0-9]{7}$');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_viewer_billing_profiles_address') THEN
        ALTER TABLE public.viewer_billing_profiles ADD CONSTRAINT ck_viewer_billing_profiles_address
            CHECK (char_length(address) BETWEEN 1 AND 200 AND char_length(btrim(address)) >= 1);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_viewer_billing_profiles_phone') THEN
        ALTER TABLE public.viewer_billing_profiles ADD CONSTRAINT ck_viewer_billing_profiles_phone
            CHECK (phone ~ '^[0-9]{10,11}$');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_viewer_billing_profiles_invoice_email') THEN
        ALTER TABLE public.viewer_billing_profiles ADD CONSTRAINT ck_viewer_billing_profiles_invoice_email
            CHECK (invoice_email IS NULL OR (char_length(invoice_email) BETWEEN 3 AND 254 AND position('@' in invoice_email) > 0));
    END IF;
END $$;

COMMENT ON TABLE public.viewer_billing_profiles IS '本契約の閲覧者が自分で書く請求先（1人1行）。AI の読み取りには出さない。ADR-1019';
COMMENT ON COLUMN public.viewer_billing_profiles.viewer_account_id IS '閲覧者 viewer_accounts.id（名簿の行が消えるとこの行も消える）';
COMMENT ON COLUMN public.viewer_billing_profiles.party_type IS 'company＝会社／individual＝個人';
COMMENT ON COLUMN public.viewer_billing_profiles.bill_to_name IS '請求書の宛名（1〜100文字）';
COMMENT ON COLUMN public.viewer_billing_profiles.contact_name IS '担当者名（1〜50文字）。会社のときは必須';
COMMENT ON COLUMN public.viewer_billing_profiles.postal_code IS '郵便番号（ハイフンなしの数字7桁）';
COMMENT ON COLUMN public.viewer_billing_profiles.address IS '住所（1〜200文字）';
COMMENT ON COLUMN public.viewer_billing_profiles.phone IS '電話番号（ハイフンなしの数字10〜11桁）';
COMMENT ON COLUMN public.viewer_billing_profiles.invoice_email IS '請求書の送り先メール（任意）。名簿のメールとは別';
COMMENT ON COLUMN public.viewer_billing_profiles.created_at IS '最初に保存した時刻';
COMMENT ON COLUMN public.viewer_billing_profiles.updated_at IS '最後に保存した時刻';

-- 鍵の用途に billing_form を足す（CHECK の付け替え）
ALTER TABLE public.viewer_login_tokens DROP CONSTRAINT IF EXISTS ck_viewer_login_tokens_purpose;
ALTER TABLE public.viewer_login_tokens ADD CONSTRAINT ck_viewer_login_tokens_purpose
    CHECK (purpose IN ('signup_code', 'password_reset', 'billing_form'));
COMMENT ON COLUMN public.viewer_login_tokens.purpose IS 'signup_code＝申込コード／password_reset＝パスワード再発行／billing_form＝請求先フォーム';

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'salesanchor_app') THEN
        GRANT SELECT, INSERT, UPDATE, DELETE ON public.viewer_billing_profiles TO salesanchor_app;
    END IF;
END $$;

COMMIT;
