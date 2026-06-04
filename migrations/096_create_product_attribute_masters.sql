-- ============================================================================
-- Migration 096: public.product_attribute_masters 新設 + 既定値 seed + backfill
--
-- 「各種マスタ」(商品マスタ画面の 2nd タブ) で、商品の選択肢系マスタを UI から
-- 追加 / 編集 / 削除できるようにするための汎用マスタ表。
--   対象 attribute: product_kind(商品種類) / set_type(セット種別) /
--     rarity(レアリティ) / language(言語) / unit(単位) /
--     hs_code(HSコード) / item(品目) / material(素材)
--   ※ TCGシリーズは既存 public.tcg_type_master / tcg_series_master で管理するため対象外。
--
-- 冪等性:
--   - CREATE TABLE / INDEX IF NOT EXISTS
--   - 固定 seed は ON CONFLICT (attribute, label_ja) DO NOTHING
--   - products 由来の backfill は to_regclass + information_schema 列ガード
--     （migration-test の単体ベースラインでは public.products / 各列が無いことがある）
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.product_attribute_masters (
    id          SERIAL PRIMARY KEY,
    attribute   VARCHAR(40)  NOT NULL,   -- product_kind / set_type / rarity / language / unit / hs_code / item / material
    code        VARCHAR(100),            -- 任意のマシン値 (language の ja/en など)。未使用なら NULL
    label_ja    VARCHAR(255) NOT NULL,   -- 表示名 (日本語)
    label_en    VARCHAR(255),            -- 表示名 (英語)
    sort_order  INTEGER      NOT NULL DEFAULT 100,
    is_active   BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE (attribute, label_ja)
);

CREATE INDEX IF NOT EXISTS idx_product_attr_masters_attr
    ON public.product_attribute_masters (attribute, sort_order, id);

-- updated_at トリガ（migration 085 と同パターン）
CREATE OR REPLACE FUNCTION public.set_updated_at_product_attribute_masters()
RETURNS TRIGGER AS $upd$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$upd$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_set_updated_at_product_attribute_masters
    ON public.product_attribute_masters;
CREATE TRIGGER trigger_set_updated_at_product_attribute_masters
    BEFORE UPDATE ON public.product_attribute_masters
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at_product_attribute_masters();

COMMENT ON TABLE public.product_attribute_masters IS
    '各種マスタ: 商品の選択肢系マスタ (商品種類/セット種別/レアリティ/言語/単位/HSコード/品目/素材) を UI から増減する。';

-- === 固定 seed（既定の選択肢） ===
INSERT INTO public.product_attribute_masters (attribute, code, label_ja, label_en, sort_order) VALUES
    -- 商品種類
    ('product_kind', 'tcg',          'TCG',            'TCG',            10),
    ('product_kind', 'sealed',       'BOX・パック',     'Sealed product', 20),
    ('product_kind', 'single',       'シングルカード',  'Single card',    30),
    ('product_kind', 'accessory',    'アクセサリー',    'Accessory',      40),
    ('product_kind', 'supply',       'サプライ',        'Supply',         50),
    -- セット種別
    ('set_type', 'booster_pack',  'ブースターパック', 'Booster pack',   10),
    ('set_type', 'booster_box',   'ブースターBOX',    'Booster box',    20),
    ('set_type', 'starter_deck',  'スターターデッキ', 'Starter deck',   30),
    ('set_type', 'structure_deck','構築済みデッキ',   'Structure deck', 40),
    ('set_type', 'box',           'BOX',             'Box',            50),
    ('set_type', 'case',          'カートン',         'Case',           60),
    -- レアリティ
    ('rarity', NULL, 'C',   'C',   10),
    ('rarity', NULL, 'U',   'U',   20),
    ('rarity', NULL, 'R',   'R',   30),
    ('rarity', NULL, 'RR',  'RR',  40),
    ('rarity', NULL, 'RRR', 'RRR', 50),
    ('rarity', NULL, 'SR',  'SR',  60),
    ('rarity', NULL, 'SAR', 'SAR', 70),
    ('rarity', NULL, 'UR',  'UR',  80),
    ('rarity', NULL, 'HR',  'HR',  90),
    ('rarity', NULL, 'SEC', 'SEC', 100),
    -- 言語
    ('language', 'ja',    '日本語',     'Japanese',              10),
    ('language', 'en',    '英語',       'English',               20),
    ('language', 'ko',    '韓国語',     'Korean',                30),
    ('language', 'zh-TW', '中国語(繁体)', 'Chinese (Traditional)', 40),
    ('language', 'zh-CN', '中国語(簡体)', 'Chinese (Simplified)',  50),
    -- 単位 (inventory.unit の CHECK 値と一致: piece/pack/box/case/set)
    ('unit', 'piece', 'piece', 'piece', 10),
    ('unit', 'pack',  'pack',  'pack',  20),
    ('unit', 'box',   'box',   'box',   30),
    ('unit', 'case',  'case',  'case',  40),
    ('unit', 'set',   'set',   'set',   50),
    -- HSコード（TCG 既定）
    ('hs_code', NULL, '9504400000', '9504400000', 10),
    -- 品目（発送ラベル既定）
    ('item', NULL, 'Playing card', 'Playing card', 10),
    -- 素材（発送ラベル既定）
    ('material', NULL, 'Paper', 'Paper', 10)
ON CONFLICT (attribute, label_ja) DO NOTHING;

-- === backfill: 既存 public.products の実値を選択肢として取り込む ===
-- 列ガード付き。products 由来の値は label_ja=label_en=実値、code=NULL、末尾並び。
DO $$
DECLARE
    has_table  BOOLEAN;
    has_col    BOOLEAN;
    col_attr   TEXT;
    src_col    TEXT;
    pairs      TEXT[][] := ARRAY[
        ARRAY['category', 'product_kind'],
        ARRAY['rarity',   'rarity'],
        ARRAY['language', 'language'],
        ARRAY['material', 'material'],
        ARRAY['hs_code',  'hs_code']
    ];
    i INTEGER;
BEGIN
    SELECT to_regclass('public.products') IS NOT NULL INTO has_table;
    IF NOT has_table THEN
        RAISE NOTICE 'public.products not present; skipping backfill';
        RETURN;
    END IF;

    FOR i IN 1 .. array_length(pairs, 1) LOOP
        src_col  := pairs[i][1];
        col_attr := pairs[i][2];
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'products'
              AND column_name = src_col
        ) INTO has_col;
        IF has_col THEN
            EXECUTE format($q$
                INSERT INTO public.product_attribute_masters
                    (attribute, code, label_ja, label_en, sort_order)
                SELECT DISTINCT %L, NULL, TRIM(p.%I), TRIM(p.%I), 500
                FROM public.products p
                WHERE p.%I IS NOT NULL AND TRIM(p.%I) <> ''
                ON CONFLICT (attribute, label_ja) DO NOTHING
            $q$, col_attr, src_col, src_col, src_col, src_col);
            RAISE NOTICE 'backfilled % from products.%', col_attr, src_col;
        END IF;
    END LOOP;
END $$;

-- ============================================================================
-- Rollback:
--   DROP TRIGGER IF EXISTS trigger_set_updated_at_product_attribute_masters
--     ON public.product_attribute_masters;
--   DROP FUNCTION IF EXISTS public.set_updated_at_product_attribute_masters();
--   DROP TABLE IF EXISTS public.product_attribute_masters;
-- ============================================================================
