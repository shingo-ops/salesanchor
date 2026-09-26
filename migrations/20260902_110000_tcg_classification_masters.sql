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

    -- ================================================================
    -- Seed data（GAS 実データ 2026-09-02 確認分）
    -- ================================================================

    -- tcg_major_categories: 3 行
    EXECUTE format($q$
        INSERT INTO %I.tcg_major_categories (code, display_name, description) VALUES
            ('DIV01', 'TCG',    'トレーディングカード'),
            ('DIV02', 'Figure', 'フィギュア'),
            ('DIV03', 'Goods',  'グッズ・雑貨')
        ON CONFLICT (code) DO NOTHING
    $q$, _schema);

    -- tcg_series: 11 行
    EXECUTE format($q$
        INSERT INTO %I.tcg_series (code, display_name, alt_name) VALUES
            ('IP001', 'Pokemon',       'ポケモン'),
            ('IP002', 'One Piece',     'ワンピース'),
            ('IP003', 'Dragon Ball',   'ドラゴンボール'),
            ('IP004', 'Yu-Gi-Oh',      '遊戯王'),
            ('IP005', 'Union Arena',   'ユニオンアリーナ'),
            ('IP006', 'GUNDAM',        'ガンダム'),
            ('IP007', 'Weiss Schwarz', 'Weiss Shwarz'),
            ('IP008', 'Digimon',       'デジモン'),
            ('IP009', 'hololive',      'ホロライブ'),
            ('IP010', 'LORCANA',       'ロルカナ'),
            ('IP011', 'Xross Stars',   'クロススターズ')
        ON CONFLICT (code) DO NOTHING
    $q$, _schema);

    -- tcg_manufacturers: 5 行
    EXECUTE format($q$
        INSERT INTO %I.tcg_manufacturers (code, display_name, alt_name) VALUES
            ('MK001', 'The Pokemon Company', 'ポケモン'),
            ('MK002', 'Bandai',              'バンダイ'),
            ('MK003', 'Takara Tomy',         'タカラトミー'),
            ('MK004', 'Bushiroad',           'ブシロード'),
            ('MK005', 'Konami',              'コナミ')
        ON CONFLICT (code) DO NOTHING
    $q$, _schema);

    -- tcg_product_categories: 2 行（GAS 実データ）
    EXECUTE format($q$
        INSERT INTO %I.tcg_product_categories (code, display_name, kubun_type) VALUES
            ('PC_BOX',    'Box',    '箱系'),
            ('PC_SINGLE', 'Single', 'シングル系')
        ON CONFLICT (code) DO NOTHING
    $q$, _schema);

    RAISE NOTICE '20260902_110000: 4 classification master tables created and seeded in schema %', _schema;
END $$;
