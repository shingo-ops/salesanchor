-- ハイブリッド型分類: 細分類→大分類FK追加 + 商品→中分類FK追加
-- ADR-156: 商品分類ツリー Phase 7
-- ADR-155: seed なし
-- 冪等性: IF NOT EXISTS ガード済み

------------------------------------------------------------
-- 1. product_formats に kind_id FK 追加（細分類→大分類）
------------------------------------------------------------
-- CI test-run 用スタブ
CREATE TABLE IF NOT EXISTS public.product_kinds (id SERIAL PRIMARY KEY, code VARCHAR(50) NOT NULL UNIQUE, name VARCHAR(100) NOT NULL, name_en VARCHAR(100), display_order INTEGER NOT NULL DEFAULT 100, is_active BOOLEAN NOT NULL DEFAULT TRUE, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW());
CREATE TABLE IF NOT EXISTS public.product_formats (id SERIAL PRIMARY KEY, code VARCHAR(50) NOT NULL UNIQUE, name VARCHAR(100) NOT NULL, name_en VARCHAR(100), line_id INTEGER, display_order INTEGER NOT NULL DEFAULT 100, is_active BOOLEAN NOT NULL DEFAULT TRUE, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW());
CREATE TABLE IF NOT EXISTS public.type_master (id SERIAL PRIMARY KEY, code VARCHAR(50) NOT NULL UNIQUE, name_ja VARCHAR(100) NOT NULL, name_en VARCHAR(100), sort_order INTEGER NOT NULL DEFAULT 100, is_active BOOLEAN NOT NULL DEFAULT TRUE, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW());
CREATE TABLE IF NOT EXISTS public.products (id SERIAL PRIMARY KEY);

ALTER TABLE public.product_formats ADD COLUMN IF NOT EXISTS kind_id INTEGER REFERENCES public.product_kinds(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_product_formats_kind_id ON public.product_formats (kind_id);

------------------------------------------------------------
-- 2. products に type_master_id FK 追加（商品→中分類）
------------------------------------------------------------
ALTER TABLE public.products ADD COLUMN IF NOT EXISTS type_master_id INTEGER REFERENCES public.type_master(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_products_type_master_id ON public.products (type_master_id);
