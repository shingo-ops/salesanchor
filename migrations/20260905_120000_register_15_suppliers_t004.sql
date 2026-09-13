-- Migration: 20260905_120000_register_15_suppliers_t004
-- 目的: 仕入元マスタ 15件 (SP0188〜SP0202) を tenant_004 に登録し、
--       LINE チャンネル行 (channel='line', external_id=NULL) も同時作成する
--
-- 冪等性: ON CONFLICT (code) DO NOTHING / ON CONFLICT (channel, external_id) DO NOTHING
-- ※ PostgreSQL は NULL 同士を UNIQUE 重複と見なさないため、
--   external_id=NULL の supplier_channels 行は各仕入元に個別挿入可能
--
-- 禁止: 既存 tcg_suppliers 行の UPDATE/DELETE は行わない

DO $$
DECLARE
    _schema TEXT := 'tenant_004';
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = _schema) THEN
        RAISE NOTICE '20260905_120000: schema % does not exist, skipping', _schema;
        RETURN;
    END IF;

    -- =========================================================
    -- 1. tcg_suppliers: 15件 新規登録（SP0188〜SP0202）
    -- =========================================================

    EXECUTE format($q$
        INSERT INTO %I.tcg_suppliers (code, name, is_active)
        VALUES
            ('SP0188', '大嶋雅人',   TRUE),
            ('SP0189', 'funスタッフ', TRUE),
            ('SP0190', 'シンソク',   TRUE),
            ('SP0191', 'ヨシヤス',   TRUE),
            ('SP0192', '徳武俊太郎', TRUE),
            ('SP0193', 'しらいたつや', TRUE),
            ('SP0194', 'Gスタッフ',  TRUE),
            ('SP0195', 'GL',         TRUE),
            ('SP0196', 'INスタッフ', TRUE),
            ('SP0197', 'Kei',        TRUE),
            ('SP0198', 'とも',       TRUE),
            ('SP0199', 'oyama',      TRUE),
            ('SP0200', 'やまちゃん', TRUE),
            ('SP0201', 'kyosuke',    TRUE),
            ('SP0202', '大知',       TRUE)
        ON CONFLICT (code) DO NOTHING
    $q$, _schema);

    -- =========================================================
    -- 2. supplier_channels: 各仕入元に LINE チャンネル行を1件作成
    --    channel='line', external_id=NULL, is_active=TRUE
    --    supplier_id は code で結合して取得
    -- =========================================================

    EXECUTE format($q$
        INSERT INTO %I.supplier_channels (supplier_id, channel, external_id, is_active)
        SELECT s.id, 'line', NULL, TRUE
        FROM %I.tcg_suppliers s
        WHERE s.code IN (
            'SP0188','SP0189','SP0190','SP0191','SP0192',
            'SP0193','SP0194','SP0195','SP0196','SP0197',
            'SP0198','SP0199','SP0200','SP0201','SP0202'
        )
        AND NOT EXISTS (
            SELECT 1 FROM %I.supplier_channels sc
            WHERE sc.supplier_id = s.id
              AND sc.channel = 'line'
              AND sc.external_id IS NULL
        )
    $q$, _schema, _schema, _schema);

END $$;
