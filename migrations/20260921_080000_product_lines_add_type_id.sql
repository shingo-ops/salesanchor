-- ============================================================================
-- Migration 20260921_030000: product_lines に type_id FK 追加（中分類への紐付け）
--
-- ADR-156: 商品分類ツリー Phase 1
--   小分類 (product_lines) を中分類 (type_master) に紐付ける FK カラムを追加。
--   NULLable: 既存データへの影響なし。
--
-- 依存: 20260920_130000_create_product_classification.sql (product_lines)
--        20260921_020000_rename_tcg_type_master_to_type_master.sql (type_master)
--
-- ADR-155 準拠: seed なし
-- 冪等性: ADD COLUMN IF NOT EXISTS / CREATE INDEX IF NOT EXISTS
-- ============================================================================

-- 依存テーブルの存在保証（CI test-run 用: product_lines は PR #3613 が先行する本番では作成済み）
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

ALTER TABLE public.product_lines ADD COLUMN IF NOT EXISTS type_id INTEGER REFERENCES public.type_master(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_product_lines_type_id ON public.product_lines (type_id);

-- ============================================================================
-- Rollback:
--   DROP INDEX IF EXISTS idx_product_lines_type_id;
--   ALTER TABLE public.product_lines DROP COLUMN IF EXISTS type_id;
-- ============================================================================
