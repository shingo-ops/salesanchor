-- ============================================================
-- Migration 20260920_130000: 商品分類マスタ新設
--   - public.product_lines   (小分類: 商品系統)
--   - public.product_formats (細分類: 商品形態)
--   - public.products に FK カラム追加
--
-- ADR-155: migration での値 INSERT 禁止 → seed なし
-- ADR-025: 本番フェーズ移行後の手動 INSERT 禁止
-- ADR-090: products 中央一本化
--
-- 冪等性: 全 DDL は IF NOT EXISTS / DO $$ BEGIN ... END $$ ガード済み
-- ============================================================

-- ============================================================
-- 商品系統マスタ（小分類）
-- パック系 / デッキ系 / BOX・セット系 / 単品系 など
-- ============================================================
CREATE TABLE IF NOT EXISTS public.product_lines (
    id            SERIAL PRIMARY KEY,
    code          VARCHAR(50)  NOT NULL UNIQUE,
    name          VARCHAR(100) NOT NULL,
    name_en       VARCHAR(100),
    display_order INTEGER      NOT NULL DEFAULT 100,
    is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_product_lines_sort
    ON public.product_lines (display_order, id);

-- updated_at 自動更新トリガ
CREATE OR REPLACE FUNCTION public.set_updated_at_product_lines()
RETURNS TRIGGER AS $upd$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$upd$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_product_lines_updated_at ON public.product_lines;
CREATE TRIGGER trg_product_lines_updated_at
    BEFORE UPDATE ON public.product_lines
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at_product_lines();

COMMENT ON TABLE public.product_lines IS
    '商品系統マスタ（小分類）。パック系/デッキ系/BOX・セット系/単品系 など。UI から増減可能。';

-- ============================================================
-- 商品形態マスタ（細分類）
-- 拡張パック / スペシャルBOX / スターターセット など
-- product_lines への FK で小分類に紐付く
-- ============================================================
CREATE TABLE IF NOT EXISTS public.product_formats (
    id            SERIAL PRIMARY KEY,
    code          VARCHAR(50)  NOT NULL UNIQUE,
    name          VARCHAR(100) NOT NULL,
    name_en       VARCHAR(100),
    line_id       INTEGER      REFERENCES public.product_lines(id) ON DELETE SET NULL,
    display_order INTEGER      NOT NULL DEFAULT 100,
    is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_product_formats_sort
    ON public.product_formats (display_order, id);

CREATE INDEX IF NOT EXISTS idx_product_formats_line_id
    ON public.product_formats (line_id);

-- updated_at 自動更新トリガ
CREATE OR REPLACE FUNCTION public.set_updated_at_product_formats()
RETURNS TRIGGER AS $upd$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$upd$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_product_formats_updated_at ON public.product_formats;
CREATE TRIGGER trg_product_formats_updated_at
    BEFORE UPDATE ON public.product_formats
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at_product_formats();

COMMENT ON TABLE public.product_formats IS
    '商品形態マスタ（細分類）。拡張パック/スペシャルBOX/スターターセット など。product_lines FK で小分類に紐付く。';

-- ============================================================
-- products テーブルに FK カラム追加
-- NULLable: 既存データへの影響なし
-- ============================================================
ALTER TABLE public.products
    ADD COLUMN IF NOT EXISTS product_line_id INTEGER
    REFERENCES public.product_lines(id) ON DELETE SET NULL;

ALTER TABLE public.products
    ADD COLUMN IF NOT EXISTS product_format_id INTEGER
    REFERENCES public.product_formats(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_products_product_line_id ON public.products (product_line_id);
CREATE INDEX IF NOT EXISTS idx_products_product_format_id ON public.products (product_format_id);

-- ============================================================
-- Rollback:
--   ALTER TABLE public.products DROP COLUMN IF EXISTS product_format_id;
--   ALTER TABLE public.products DROP COLUMN IF EXISTS product_line_id;
--   DROP TABLE IF EXISTS public.product_formats;
--   DROP TABLE IF EXISTS public.product_lines;
--   DROP FUNCTION IF EXISTS public.set_updated_at_product_formats();
--   DROP FUNCTION IF EXISTS public.set_updated_at_product_lines();
-- ============================================================
