-- ADR-093 海外顧客向け明細改修 / Migration 20260604_030000:
-- quote_items / invoice_items に海外顧客向け明細列を追加する。
--
-- 経緯:
--   見積書・請求書の明細を「海外顧客向け」に改修（ひとしさん指示 2026-06-04）。
--   明細行に英語タイトル(name_en) / 状態(condition) / 形態(unit) を保存し、
--   形態(unit)に応じた重量(weight, 既存列)を public.products から引き込んで表示する。
--
-- 追加列（quote_items / invoice_items 共通）:
--   1. name_en    VARCHAR(255)  -- 英語タイトル（明細のメイン表示。日本語は product_name）
--   2. condition  VARCHAR(50)   -- 商品状態（NM/SP/新品 等）
--   3. unit       VARCHAR(20)   -- 形態（box / case / pack 等）
--   ※ weight NUMERIC(10,3) は既存列のためここでは追加しない。
--
-- 設計:
--   - 全既存テナントスキーマ（^tenant_\d+$）をループして ALTER TABLE ... ADD COLUMN
--     IF NOT EXISTS する DO ブロック（migration 038 の踏襲）。
--   - テーブル未存在のスキーマは CONTINUE でスキップ（migration-test の tenant_001
--     には quote_items/invoice_items が無いため、no-op で緑になる）。
--   - 全列 NULL 許可、DEFAULT なし（既存行への影響なし）。
--
-- 冪等性:
--   - ADD COLUMN IF NOT EXISTS で再実行 no-op。
--
-- 新規テナント用の CREATE TABLE 側（backend/app/services/tenant.py）にも
-- 同 3 列を追加済み。
--
-- 作成日: 2026-06-04

DO $$
DECLARE
    schema_rec RECORD;
    applied_count INTEGER := 0;
    skipped_no_table INTEGER := 0;
BEGIN
    FOR schema_rec IN
        SELECT nspname FROM pg_namespace
        WHERE nspname ~ '^tenant_\d+$'
        ORDER BY nspname
    LOOP
        -- quote_items
        IF EXISTS (
            SELECT 1 FROM pg_tables
            WHERE schemaname = schema_rec.nspname AND tablename = 'quote_items'
        ) THEN
            EXECUTE format('ALTER TABLE %I.quote_items ADD COLUMN IF NOT EXISTS name_en VARCHAR(255)', schema_rec.nspname);
            EXECUTE format('ALTER TABLE %I.quote_items ADD COLUMN IF NOT EXISTS condition VARCHAR(50)', schema_rec.nspname);
            EXECUTE format('ALTER TABLE %I.quote_items ADD COLUMN IF NOT EXISTS unit VARCHAR(20)', schema_rec.nspname);
            applied_count := applied_count + 1;
            RAISE NOTICE 'migration 20260604_030000: %.quote_items に name_en/condition/unit を追加', schema_rec.nspname;
        ELSE
            skipped_no_table := skipped_no_table + 1;
        END IF;

        -- invoice_items
        IF EXISTS (
            SELECT 1 FROM pg_tables
            WHERE schemaname = schema_rec.nspname AND tablename = 'invoice_items'
        ) THEN
            EXECUTE format('ALTER TABLE %I.invoice_items ADD COLUMN IF NOT EXISTS name_en VARCHAR(255)', schema_rec.nspname);
            EXECUTE format('ALTER TABLE %I.invoice_items ADD COLUMN IF NOT EXISTS condition VARCHAR(50)', schema_rec.nspname);
            EXECUTE format('ALTER TABLE %I.invoice_items ADD COLUMN IF NOT EXISTS unit VARCHAR(20)', schema_rec.nspname);
            applied_count := applied_count + 1;
            RAISE NOTICE 'migration 20260604_030000: %.invoice_items に name_en/condition/unit を追加', schema_rec.nspname;
        ELSE
            skipped_no_table := skipped_no_table + 1;
        END IF;
    END LOOP;

    RAISE NOTICE
        'migration 20260604_030000: 完了。適用 % テーブル、未存在スキップ % テーブル',
        applied_count, skipped_no_table;
END $$;

-- =====================================================================
-- Rollback 手順（緊急時のみ手動実行）:
--
-- DO $$
-- DECLARE r RECORD;
-- BEGIN
--     FOR r IN SELECT nspname FROM pg_namespace WHERE nspname ~ '^tenant_\d+$'
--     LOOP
--         IF EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = r.nspname AND tablename = 'quote_items') THEN
--             EXECUTE format('ALTER TABLE %I.quote_items DROP COLUMN IF EXISTS unit', r.nspname);
--             EXECUTE format('ALTER TABLE %I.quote_items DROP COLUMN IF EXISTS condition', r.nspname);
--             EXECUTE format('ALTER TABLE %I.quote_items DROP COLUMN IF EXISTS name_en', r.nspname);
--         END IF;
--         IF EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = r.nspname AND tablename = 'invoice_items') THEN
--             EXECUTE format('ALTER TABLE %I.invoice_items DROP COLUMN IF EXISTS unit', r.nspname);
--             EXECUTE format('ALTER TABLE %I.invoice_items DROP COLUMN IF EXISTS condition', r.nspname);
--             EXECUTE format('ALTER TABLE %I.invoice_items DROP COLUMN IF EXISTS name_en', r.nspname);
--         END IF;
--     END LOOP;
-- END $$;
-- =====================================================================
