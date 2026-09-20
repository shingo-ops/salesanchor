-- ============================================================================
-- Migration 20260920_070000: tcg_product_categories に tenant_id 列を追加
--
-- 背景:
--   tcg_product_categories テーブルに tenant_id 列を追加し、
--   共用マスタ（tenant_id IS NULL）とテナント固有マスタの両対応とする。
--
-- 変更内容:
--   1. public.tcg_product_categories に tenant_id 列を追加（ADD COLUMN IF NOT EXISTS）
--   2. インデックス追加（冪等）
--
-- 冪等性: ADD COLUMN IF NOT EXISTS
--
-- 作成日: 2026-09-20
-- ============================================================================

DO $step1$
BEGIN
    IF to_regclass('public.tcg_product_categories') IS NULL THEN
        RAISE EXCEPTION 'public.tcg_product_categories が存在しません。migration を中断します。';
    END IF;

    ALTER TABLE public.tcg_product_categories ADD COLUMN IF NOT EXISTS tenant_id INTEGER;

    RAISE NOTICE 'step1: public.tcg_product_categories tenant_id 列の確認/追加 完了';
END $step1$;

CREATE INDEX IF NOT EXISTS idx_tcg_product_categories_tenant_id ON public.tcg_product_categories (tenant_id);
