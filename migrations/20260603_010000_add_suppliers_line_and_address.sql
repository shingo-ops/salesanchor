-- ============================================================================
-- Migration 20260603_010000: ADR-093 — public.suppliers に LINE名 と
--   構造化住所（郵便番号 / 都道府県 / 市町村 / 住所1 / 住所2）を additive 追加。
--
-- 仕入元マスタ改修（中央 admin 画面）で、編集ポップアップから連絡先・住所を
-- 入力できるようにする。既存の単一 address(TEXT) は温存（後方互換）。
--
-- 適用対象: public スキーマ (1 回のみ)
-- 冪等: ADD COLUMN IF NOT EXISTS。全列 NULL 許可でゼロダウンタイム。additive-only。
-- ガード: migration-test の baseline には public.suppliers が無い場合があるため
--         to_regclass で存在チェックしてから ALTER する（無ければ skip）。
-- ============================================================================

DO $$
BEGIN
    IF to_regclass('public.suppliers') IS NULL THEN
        RAISE NOTICE 'public.suppliers not present (migration-test baseline) — skipping';
    ELSE
        ALTER TABLE public.suppliers
            ADD COLUMN IF NOT EXISTS line_name   VARCHAR(255),
            ADD COLUMN IF NOT EXISTS postal_code VARCHAR(20),
            ADD COLUMN IF NOT EXISTS prefecture  VARCHAR(50),
            ADD COLUMN IF NOT EXISTS city        VARCHAR(100),
            ADD COLUMN IF NOT EXISTS address1    VARCHAR(255),
            ADD COLUMN IF NOT EXISTS address2    VARCHAR(255);
    END IF;
END $$;
