-- 商品分類マスタ拡張: 小分類→大分類FK / 入数マスタ / 重量マスタ / products FK追加
-- ADR-155: seed なし（値は CSV/アプリ経由で投入）
-- ADR-156: 商品分類ツリー Phase 6
-- 冪等性: 全 DDL は IF NOT EXISTS / DO $$ BEGIN ... END $$ ガード済み

------------------------------------------------------------
-- 1. product_lines に kind_id FK 追加（小分類→大分類）
------------------------------------------------------------
-- CI test-run 用スタブ（単体テスト時にテーブルが存在しない場合の対策）
CREATE TABLE IF NOT EXISTS public.product_kinds (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    name_en VARCHAR(100),
    display_order INTEGER NOT NULL DEFAULT 100,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS public.product_lines (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    name_en VARCHAR(100),
    display_order INTEGER NOT NULL DEFAULT 100,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.product_lines
    ADD COLUMN IF NOT EXISTS kind_id INTEGER REFERENCES public.product_kinds(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_product_lines_kind_id ON public.product_lines (kind_id);

------------------------------------------------------------
-- 2. quantity_units（入数マスタ）
------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.quantity_units (
    id            SERIAL PRIMARY KEY,
    code          VARCHAR(50)  NOT NULL UNIQUE,
    name          VARCHAR(100) NOT NULL,
    name_en       VARCHAR(100),
    value         INTEGER      NOT NULL,
    display_order INTEGER      NOT NULL DEFAULT 100,
    is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_quantity_units_sort ON public.quantity_units (display_order, id);

------------------------------------------------------------
-- 3. weight_classes（重量マスタ）
------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.weight_classes (
    id            SERIAL PRIMARY KEY,
    code          VARCHAR(50)  NOT NULL UNIQUE,
    name          VARCHAR(100) NOT NULL,
    name_en       VARCHAR(100),
    min_grams     INTEGER      NOT NULL DEFAULT 0,
    max_grams     INTEGER,
    display_order INTEGER      NOT NULL DEFAULT 100,
    is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_weight_classes_sort ON public.weight_classes (display_order, id);

------------------------------------------------------------
-- 4. products に FK 追加
------------------------------------------------------------
-- products テーブル スタブ（CI test-run 用）
CREATE TABLE IF NOT EXISTS public.products (
    id SERIAL PRIMARY KEY
);

ALTER TABLE public.products
    ADD COLUMN IF NOT EXISTS quantity_unit_id INTEGER REFERENCES public.quantity_units(id) ON DELETE SET NULL;
ALTER TABLE public.products
    ADD COLUMN IF NOT EXISTS weight_class_id INTEGER REFERENCES public.weight_classes(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_products_quantity_unit_id ON public.products (quantity_unit_id);
CREATE INDEX IF NOT EXISTS idx_products_weight_class_id ON public.products (weight_class_id);

------------------------------------------------------------
-- 5. updated_at トリガ
------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_quantity_units_updated_at') THEN
        CREATE TRIGGER trg_quantity_units_updated_at BEFORE UPDATE ON public.quantity_units FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_weight_classes_updated_at') THEN
        CREATE TRIGGER trg_weight_classes_updated_at BEFORE UPDATE ON public.weight_classes FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
    END IF;
END $$;
