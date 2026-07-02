-- Migration 20260628_170000: public.app_fx_rates テーブル新設
-- 目的: USD/JPY 為替レート SSOT。Celery Beat が1日2回自動取得・UPSERT する。
--
-- 設計:
--   - 全テナント共通の公開情報（テナントスキーマではなく public に配置）
--   - currency VARCHAR(3) PRIMARY KEY — 現在は "USD" のみ、将来他通貨も追加可
--   - RLS: 読み取りは全ロール許可（為替は公開情報）
--          書き込みは app.is_operator='true' のみ（Celery ワーカー = operator コンテキスト）
--
-- ロールバック / DOWN:
--   DROP TABLE IF EXISTS public.app_fx_rates CASCADE;
--   DROP FUNCTION IF EXISTS public.app_fx_rates_touch_updated_at();
--
-- 冪等: CREATE TABLE IF NOT EXISTS / CREATE OR REPLACE FUNCTION /
--       DROP POLICY IF EXISTS / DROP TRIGGER IF EXISTS

-- === 1. テーブル作成 ===
CREATE TABLE IF NOT EXISTS public.app_fx_rates (
    currency   VARCHAR(3)    PRIMARY KEY,
    rate_jpy   NUMERIC(12,4) NOT NULL,
    fetched_at TIMESTAMPTZ   NOT NULL,
    updated_at TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  public.app_fx_rates            IS '為替レート SSOT（1日2回 Celery Beat が自動更新）';
COMMENT ON COLUMN public.app_fx_rates.currency   IS '通貨コード (ISO 4217): USD / EUR 等';
COMMENT ON COLUMN public.app_fx_rates.rate_jpy   IS '1外貨 = rate_jpy 円（JPY 建て）';
COMMENT ON COLUMN public.app_fx_rates.fetched_at IS '外部API (open.er-api.com) から取得した時刻（UTC）';
COMMENT ON COLUMN public.app_fx_rates.updated_at IS '行最終更新日時（トリガー自動更新）';

-- === 2. updated_at 自動更新トリガー ===
CREATE OR REPLACE FUNCTION public.app_fx_rates_touch_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_app_fx_rates_touch_updated_at ON public.app_fx_rates;
CREATE TRIGGER trg_app_fx_rates_touch_updated_at
    BEFORE UPDATE ON public.app_fx_rates
    FOR EACH ROW EXECUTE FUNCTION public.app_fx_rates_touch_updated_at();

-- === 3. RLS 有効化 ===
ALTER TABLE public.app_fx_rates ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.app_fx_rates FORCE ROW LEVEL SECURITY;

-- 読み取り: 全ロール許可（為替は公開情報・テナント分離不要）
DROP POLICY IF EXISTS app_fx_rates_read ON public.app_fx_rates;
CREATE POLICY app_fx_rates_read
    ON public.app_fx_rates
    FOR SELECT
    USING (true);

-- 書き込み (INSERT / UPDATE / DELETE): operator のみ
-- app.is_operator='true' は Celery ワーカーの set_tenant_context_sync が付与する
DROP POLICY IF EXISTS app_fx_rates_write ON public.app_fx_rates;
CREATE POLICY app_fx_rates_write
    ON public.app_fx_rates
    FOR ALL
    USING (current_setting('app.is_operator', true) = 'true')
    WITH CHECK (current_setting('app.is_operator', true) = 'true');
