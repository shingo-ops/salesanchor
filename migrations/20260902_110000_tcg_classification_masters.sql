-- Migration: 20260902_110000_tcg_classification_masters
-- 目的: TCG 分類マスタ 4 テーブルを tenant_004 スキーマに作成し GAS 実データで seed する
--
-- GAS 実測件数（2026-09-02 clasp run で確認）:
--   大分類マスタ (tcg_major_categories)  : 3 行
--   作品マスタ   (tcg_series)             : 11 行
--   メーカーマスタ (tcg_manufacturers)    : 5 行
--   商品区分マスタ (tcg_product_categories): 2 行
--
-- 冪等性: CREATE TABLE IF NOT EXISTS / INSERT … ON CONFLICT DO NOTHING

DO $$
DECLARE
    _schema TEXT := 'tenant_004';
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = _schema) THEN
        RAISE NOTICE '20260902_110000: schema % does not exist, skipping', _schema;
        RETURN;
    END IF;

    -- ----------------------------------------------------------------
    -- 1. tcg_major_categories (大分類マスタ)
    -- ----------------------------------------------------------------
    EXECUTE format($q$
        CREATE TABLE IF NOT EXISTS %I.tcg_major_categories (
            id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            code         VARCHAR(20) NOT NULL UNIQUE,
            display_name TEXT        NOT NULL,
            description  TEXT,
            is_active    BOOLEAN     NOT NULL DEFAULT TRUE,
            created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    $q$, _schema);

    -- ----------------------------------------------------------------
    -- 2. tcg_series (作品マスタ)
    -- ----------------------------------------------------------------
    EXECUTE format($q$
        CREATE TABLE IF NOT EXISTS %I.tcg_series (
            id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            code         VARCHAR(20) NOT NULL UNIQUE,
            display_name TEXT        NOT NULL,
            alt_name     TEXT,
            is_active    BOOLEAN     NOT NULL DEFAULT TRUE,
            created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    $q$, _schema);

    -- ----------------------------------------------------------------
    -- 3. tcg_manufacturers (メーカーマスタ)
    -- ----------------------------------------------------------------
    EXECUTE format($q$
        CREATE TABLE IF NOT EXISTS %I.tcg_manufacturers (
            id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            code         VARCHAR(20) NOT NULL UNIQUE,
            display_name TEXT        NOT NULL,
            alt_name     TEXT,
            is_active    BOOLEAN     NOT NULL DEFAULT TRUE,
            created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    $q$, _schema);

    -- ----------------------------------------------------------------
    -- 4. tcg_product_categories (商品区分マスタ)
    --    kubun_type: '箱系' | 'シングル系' | 'その他'
    --    将来の追加行はこのカラムで区分（PC コードで直接分岐しない）
    -- ----------------------------------------------------------------
    EXECUTE format($q$
        CREATE TABLE IF NOT EXISTS %I.tcg_product_categories (
            id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            code         VARCHAR(20) NOT NULL UNIQUE,
            display_name TEXT        NOT NULL,
            kubun_type   VARCHAR(50) NOT NULL,
            is_active    BOOLEAN     NOT NULL DEFAULT TRUE,
            created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    $q$, _schema);

    -- DEPRECATED: values now managed via app UI/CSV per ADR-155

    RAISE NOTICE '20260902_110000: 4 classification master tables created in schema %', _schema;
END $$;
