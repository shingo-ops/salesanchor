-- 細分類→中分類 多対多中間テーブル + エイリアス
-- ADR-156: 商品分類ツリー Phase 8
-- ADR-155: seed なし
-- 冪等性: IF NOT EXISTS ガード済み

------------------------------------------------------------
-- 1. 中間テーブル作成
------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.type_master (id SERIAL PRIMARY KEY, code VARCHAR(50) NOT NULL UNIQUE, name_ja VARCHAR(100) NOT NULL, name_en VARCHAR(100), sort_order INTEGER NOT NULL DEFAULT 100, is_active BOOLEAN NOT NULL DEFAULT TRUE, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW());
CREATE TABLE IF NOT EXISTS public.product_formats (id SERIAL PRIMARY KEY, code VARCHAR(50) NOT NULL UNIQUE, name VARCHAR(100) NOT NULL, name_en VARCHAR(100), line_id INTEGER, display_order INTEGER NOT NULL DEFAULT 100, is_active BOOLEAN NOT NULL DEFAULT TRUE, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW());

CREATE TABLE IF NOT EXISTS public.product_format_game_links (
    format_id     INTEGER NOT NULL REFERENCES public.product_formats(id) ON DELETE CASCADE,
    type_master_id INTEGER NOT NULL REFERENCES public.type_master(id) ON DELETE CASCADE,
    alias         VARCHAR(100),
    PRIMARY KEY (format_id, type_master_id)
);

CREATE INDEX IF NOT EXISTS idx_pfgl_format_id ON public.product_format_game_links (format_id);
CREATE INDEX IF NOT EXISTS idx_pfgl_type_master_id ON public.product_format_game_links (type_master_id);
