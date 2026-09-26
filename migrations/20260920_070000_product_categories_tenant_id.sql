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
DECLARE
    _schema TEXT := 'public';
    _table  TEXT := 'tcg_product' || '_categories';
BEGIN
    IF to_regclass(_schema || '.' || _table) IS NULL THEN
        RAISE EXCEPTION 'テーブル %.% が存在しません。migration を中断します。', _schema, _table;
    END IF;

    EXECUTE format('ALTER TABLE %I.%I ADD COLUMN IF NOT EXISTS tenant_id INTEGER', _schema, _table);

    RAISE NOTICE 'step1: %.% tenant_id 列の確認/追加 完了', _schema, _table;
END $step1$;

DO $step2$
DECLARE
    _schema TEXT := 'public';
    _table  TEXT := 'tcg_product' || '_categories';
BEGIN
    EXECUTE format(
        'CREATE INDEX IF NOT EXISTS idx_tcg_product_categories_tenant_id ON %I.%I (tenant_id)',
        _schema, _table
    );
END $step2$;
