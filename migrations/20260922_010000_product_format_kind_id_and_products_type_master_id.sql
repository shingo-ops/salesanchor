-- ハイブリッド型分類: 細分類→大分類FK追加 + （商品→中分類FK は ADR-1026 で削除）
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
-- 2. （削除済み）products.type_master_id は ADR-1026 で取り除いた。
--    作品の正本は products.work_id。products は列番号が上限 1600 に達しているため、
--    ここで列を足し直すと毎デプロイ失敗する。この節に ADD を戻さないこと。
------------------------------------------------------------
