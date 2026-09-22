-- ============================================================
-- Migration: 販売単位・状態マスタ インフラ整備
-- Date: 2026-09-22 (updated after merge with main)
-- Purpose: 連鎖プルダウンの基盤テーブルを構築する
--
--   小分類(product_lines)
--     → 販売可能単位(product_line_available_units → quantity_units)
--       → 使える状態(unit_condition_links → condition_definitions)
--
--   商品ごとの販売情報(product_quantity_units)
--     → 商品 × 販売単位 × 入数
--
-- データ投入方針:
--   全テーブルは構造（列）のみ作成する。
--   値は全てアプリ画面またはCSVから登録する。
--   マイグレーションではINSERTしない。
--
-- 投入予定データ（参考・INSERTはしない）:
--
--   quantity_units（正式販売単位マスタ）:
--     CASE/ケース, BOX/ボックス, PACK/パック,
--     SINGLE/シングル, SUPPLY/サプライ, BULK/バルク
--     value列 = 換算係数（1ケース=12ボックスなら12）
--
--   condition_definitions（正式状態マスタ）:
--     NEW/新品, SEALED/未開封, DAMAGED/傷あり,
--     NO_SHRINK/シュリンクなし, OPENED/開封済み,
--     EMPTY_BOX/空箱, UNSEARCHED/未サーチ, SEARCHED/サーチ済み
--
--   product_line_available_units（小分類→販売可能単位）:
--     ボックス → {ケース, ボックス, パック}
--     プロモ → {パック, シングル}
--     シングル → {シングル}
--     鑑定品 → {シングル}
--     サプライ → {サプライ}
--     バルク → {バルク}
--     ケース → {ケース}
--     パック → {パック}
--
--   unit_condition_links（販売単位→使える状態）:
--     ケース → {新品, 傷あり, 開封済み}
--     ボックス → {未開封, 傷あり, シュリンクなし, 開封済み, 空箱}
--     パック → {未サーチ, サーチ済み}
--     ※シングル・サプライ・バルクは後日拡張
--
-- 既存テーブルとの関係:
--   units / unit_aliases → LINE解析用（本マイグレーションでは変更しない）
--   conditions / condition_aliases → LINE解析用（本マイグレーションでは変更しない）
--   quantity_units → 正式販売単位マスタ（既存テーブル・構造変更のみ）
--   condition_definitions → 正式状態マスタ（既存テーブル・変更なし）
-- ============================================================

BEGIN;

-- ============================================================
-- 1. テーブルコメント追加
--    LINE解析用と正式マスタを区別するため
--    CI環境では対象テーブルが存在しない場合があるため DO ブロックで条件分岐
-- ============================================================
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'units') THEN
    COMMENT ON TABLE public.units IS 'LINE解析用 単位マスタ（正式販売単位はquantity_unitsを使用）';
  END IF;
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'unit_aliases') THEN
    COMMENT ON TABLE public.unit_aliases IS 'LINE解析用 単位エイリアス（unitsの表記ゆれ対応）';
  END IF;
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'conditions') THEN
    COMMENT ON TABLE public.conditions IS 'LINE解析用 状態マスタ（正式状態はcondition_definitionsを使用）';
  END IF;
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'condition_aliases') THEN
    COMMENT ON TABLE public.condition_aliases IS 'LINE解析用 状態エイリアス（conditionsの表記ゆれ対応）';
  END IF;
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'quantity_units') THEN
    COMMENT ON TABLE public.quantity_units IS '正式販売単位マスタ — 値はアプリ/CSVから登録。value列は換算係数（例: 1ケース=12ボックスなら12）';
  END IF;
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'condition_definitions') THEN
    COMMENT ON TABLE public.condition_definitions IS '正式状態マスタ — 値はアプリ/CSVから登録';
  END IF;
END $$;

-- ============================================================
-- 2. quantity_units.value: NOT NULL → NULL許可
--    値はアプリ/CSVから投入するため、初期状態でNULLを許容する
--    CI環境では quantity_units が存在しない場合があるため DO ブロックで条件分岐
-- ============================================================
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'quantity_units' AND column_name = 'value') THEN
    ALTER TABLE public.quantity_units ALTER COLUMN value DROP NOT NULL;
  END IF;
END $$;

-- ============================================================
-- 3. product_line_available_units（小分類 → 販売可能単位）
--    用途: 小分類を選ぶと、販売単位のプルダウンが絞り込まれる
--    例: ボックス商品 → ケース/ボックス/パック が選べる
--    データはアプリ/CSVから登録
--    CI環境では product_lines / quantity_units が存在しない場合があるため
--    DO ブロックで条件分岐
-- ============================================================
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'product_lines')
     AND EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'quantity_units')
  THEN
    CREATE TABLE IF NOT EXISTS public.product_line_available_units (
        id               SERIAL PRIMARY KEY,
        product_line_id  INTEGER NOT NULL REFERENCES public.product_lines(id),
        quantity_unit_id INTEGER NOT NULL REFERENCES public.quantity_units(id),
        created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
        UNIQUE (product_line_id, quantity_unit_id)
    );
    EXECUTE 'COMMENT ON TABLE public.product_line_available_units IS ''小分類→販売可能単位の紐づけ（連鎖プルダウン第1段）''';
    EXECUTE 'CREATE INDEX IF NOT EXISTS idx_plau_product_line_id ON public.product_line_available_units (product_line_id)';
    EXECUTE 'CREATE INDEX IF NOT EXISTS idx_plau_quantity_unit_id ON public.product_line_available_units (quantity_unit_id)';
  END IF;
END $$;

-- ============================================================
-- 4. unit_condition_links（販売単位 → 使える状態）
--    用途: 販売単位を選ぶと、状態のプルダウンが絞り込まれる
--    例: ボックス → 未開封/傷あり/シュリンクなし/開封済み/空箱
--    データはアプリ/CSVから登録
--    CI環境では quantity_units / condition_definitions が存在しない場合があるため
--    DO ブロックで条件分岐
-- ============================================================
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'quantity_units')
     AND EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'condition_definitions')
  THEN
    CREATE TABLE IF NOT EXISTS public.unit_condition_links (
        id               SERIAL PRIMARY KEY,
        quantity_unit_id INTEGER NOT NULL REFERENCES public.quantity_units(id),
        condition_def_id INTEGER NOT NULL REFERENCES public.condition_definitions(id),
        created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
        UNIQUE (quantity_unit_id, condition_def_id)
    );
    EXECUTE 'COMMENT ON TABLE public.unit_condition_links IS ''販売単位→使える状態の紐づけ（連鎖プルダウン第2段）''';
    EXECUTE 'CREATE INDEX IF NOT EXISTS idx_ucl_quantity_unit_id ON public.unit_condition_links (quantity_unit_id)';
    EXECUTE 'CREATE INDEX IF NOT EXISTS idx_ucl_condition_def_id ON public.unit_condition_links (condition_def_id)';
  END IF;
END $$;

-- ============================================================
-- 5. product_quantity_units（商品 × 販売単位 × 入数）
--    用途: 商品ごとに「何の単位で、入数いくつで売るか」を記録
--    例: ポケモン151 + ケース + 入数12
--    データはアプリ/CSVから登録
--    CI環境では products / quantity_units が存在しない場合があるため
--    DO ブロックで条件分岐
-- ============================================================
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'products')
     AND EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'quantity_units')
  THEN
    CREATE TABLE IF NOT EXISTS public.product_quantity_units (
        id               SERIAL PRIMARY KEY,
        product_id       INTEGER NOT NULL REFERENCES public.products(id),
        quantity_unit_id INTEGER NOT NULL REFERENCES public.quantity_units(id),
        value            INTEGER,  -- 入数（換算係数）。NULLはアプリ/CSV投入待ち
        created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
        UNIQUE (product_id, quantity_unit_id)
    );
    EXECUTE 'COMMENT ON TABLE public.product_quantity_units IS ''商品ごとの販売単位と入数（連鎖プルダウン実データ）''';
    EXECUTE 'COMMENT ON COLUMN public.product_quantity_units.value IS ''入数（換算係数）。例: 1ケース=12ボックスなら12''';
    EXECUTE 'CREATE INDEX IF NOT EXISTS idx_pqu_product_id ON public.product_quantity_units (product_id)';
    EXECUTE 'CREATE INDEX IF NOT EXISTS idx_pqu_quantity_unit_id ON public.product_quantity_units (quantity_unit_id)';
  END IF;
END $$;

COMMIT;
