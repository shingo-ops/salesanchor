-- ============================================================================
-- Migration: public.tenant_settings にポリシー列を追加
--
-- 経緯:
--   ADR-106: 標準エンジン + テナント変数の土台。
--   テナントごとに在庫集計フィルタ・見積有効期限・通貨・書類言語・
--   関税ポリシー・発行モードを設定できるようにする。
--
-- 設計:
--   - public.tenant_settings（migration 070 で作成済み）に列を追加。
--   - additive のみ。既存データを一切触らない。
--   - 全列に NOT NULL + DEFAULT を設定し、既存行も安全。
--
-- 冪等性:
--   ADD COLUMN IF NOT EXISTS を使用。
--
-- 関連:
--   migrations/070_add_spreadsheet_phase.sql (tenant_settings 初回作成)
--
-- 作成日: 2026-06-04
-- ============================================================================

-- === 1. ポリシー列の追加 ===
ALTER TABLE public.tenant_settings
    ADD COLUMN IF NOT EXISTS inventory_agg_filter VARCHAR(20) NOT NULL DEFAULT 'none',
    ADD COLUMN IF NOT EXISTS agg_price_threshold_jpy INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS agg_qty_threshold INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS quote_validity_days INTEGER NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS default_currency VARCHAR(10) NOT NULL DEFAULT 'JPY',
    ADD COLUMN IF NOT EXISTS document_language VARCHAR(10) NOT NULL DEFAULT 'en',
    ADD COLUMN IF NOT EXISTS duty_incoterms VARCHAR(10) NOT NULL DEFAULT 'DAP',
    ADD COLUMN IF NOT EXISTS issue_mode VARCHAR(20) NOT NULL DEFAULT 'pdf';

-- === 2. CHECK 制約の追加（冪等: 存在しない場合のみ） ===
DO $check_constraints$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'tenant_settings_inventory_agg_filter_check'
          AND conrelid = 'public.tenant_settings'::regclass
    ) THEN
        ALTER TABLE public.tenant_settings
            ADD CONSTRAINT tenant_settings_inventory_agg_filter_check
            CHECK (inventory_agg_filter IN ('none', 'cheapest', 'balanced'));
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'tenant_settings_duty_incoterms_check'
          AND conrelid = 'public.tenant_settings'::regclass
    ) THEN
        ALTER TABLE public.tenant_settings
            ADD CONSTRAINT tenant_settings_duty_incoterms_check
            CHECK (duty_incoterms IN ('DAP', 'DDU', 'DDP'));
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'tenant_settings_issue_mode_check'
          AND conrelid = 'public.tenant_settings'::regclass
    ) THEN
        ALTER TABLE public.tenant_settings
            ADD CONSTRAINT tenant_settings_issue_mode_check
            CHECK (issue_mode IN ('paypal_auto', 'paypal_manual', 'pdf', 'wise_pdf'));
    END IF;
END $check_constraints$;

-- === 3. COMMENT（列の用途を記録） ===
COMMENT ON COLUMN public.tenant_settings.inventory_agg_filter IS 'ADR-099: 在庫集計フィルタ none/cheapest/balanced';
COMMENT ON COLUMN public.tenant_settings.agg_price_threshold_jpy IS 'ADR-099: 在庫集計 価格閾値 (JPY)';
COMMENT ON COLUMN public.tenant_settings.agg_qty_threshold IS 'ADR-099: 在庫集計 数量閾値';
COMMENT ON COLUMN public.tenant_settings.quote_validity_days IS 'ADR-101: 見積有効期限の既定日数';
COMMENT ON COLUMN public.tenant_settings.default_currency IS 'ADR-101: 既定通貨';
COMMENT ON COLUMN public.tenant_settings.document_language IS 'ADR-101: 書類言語';
COMMENT ON COLUMN public.tenant_settings.duty_incoterms IS 'ADR-101: 関税ポリシー DAP/DDU/DDP';
COMMENT ON COLUMN public.tenant_settings.issue_mode IS 'ADR-101: 発行モード paypal_auto/paypal_manual/pdf/wise_pdf';

-- 送料・報酬の数式は未決定
-- TODO(ADR-103): 送料ポリシー列（キャリア連携後に追加）
-- TODO(ADR-104付録1): 報酬ルール列（後日定義）

-- === 4. 完了ログ ===
DO $log$
DECLARE
    col_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO col_count
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'tenant_settings'
      AND column_name IN (
          'inventory_agg_filter', 'agg_price_threshold_jpy', 'agg_qty_threshold',
          'quote_validity_days', 'default_currency', 'document_language',
          'duty_incoterms', 'issue_mode'
      );
    RAISE NOTICE 'migration 20260604_050000 完了: tenant_settings ポリシー列 % / 8 列存在',
        col_count;
END $log$;
