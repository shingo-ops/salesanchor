-- ============================================================================
-- Migration 20260603_030000: ドラゴンボール フュージョンワールド 商品マスタ投入
--
-- 公式サイト (dbs-cardgame.com/fw/jp/products) の Booster Pack / Starter Deck を
-- 中央カタログ public.products に投入する（ADR-090: tenant_id=NULL）。
--
-- 冪等: product_code（'DB-<型番>'）の partial UNIQUE で ON CONFLICT DO UPDATE。
--       再実行・本番再適用しても重複せず、値が更新される。
-- category='Dragon Ball' / tcg_type='dragon_ball'（既存規約・migration 085/20260602_020000）。
-- 在庫数は中央カタログのため 0（在庫は仕入元オファーで管理）。
-- additive-only（INSERT のみ）。
-- ============================================================================

DO $$
BEGIN
    IF to_regclass('public.products') IS NULL THEN
        RAISE NOTICE 'public.products not present (migration-test baseline) — skipping';
        RETURN;
    END IF;

    INSERT INTO public.products
        (product_code, name, name_en, category, tcg_type, mark, product_kind,
         status, unit_price, release_date, stock_quantity)
    VALUES
        -- Booster Pack (FBxx / SBxx / STxx)
        ('DB-FB01', 'ブースターパック 覚醒の鼓動',          NULL,                 'Dragon Ball', 'dragon_ball', 'FB01', 'TCG', 'active',  220, DATE '2024-02-16', 0),
        ('DB-FB02', 'ブースターパック 烈火の闘気',          NULL,                 'Dragon Ball', 'dragon_ball', 'FB02', 'TCG', 'active',  220, DATE '2024-05-10', 0),
        ('DB-FB03', 'ブースターパック 怒りの咆哮',          NULL,                 'Dragon Ball', 'dragon_ball', 'FB03', 'TCG', 'active',  220, DATE '2024-08-09', 0),
        ('DB-FB04', 'ブースターパック 限界を超えし者',      NULL,                 'Dragon Ball', 'dragon_ball', 'FB04', 'TCG', 'active',  220, DATE '2024-11-08', 0),
        ('DB-FB05', 'ブースターパック 未知なる冒険',        NULL,                 'Dragon Ball', 'dragon_ball', 'FB05', 'TCG', 'active',  220, DATE '2025-02-08', 0),
        ('DB-FB06', 'ブースターパック 迫り来る脅威',        NULL,                 'Dragon Ball', 'dragon_ball', 'FB06', 'TCG', 'active',  220, DATE '2025-04-26', 0),
        ('DB-FB07', 'ブースターパック 神龍への願い',        NULL,                 'Dragon Ball', 'dragon_ball', 'FB07', 'TCG', 'active',  220, DATE '2025-09-13', 0),
        ('DB-FB08', 'ブースターパック 誇り高き戦闘民族',    NULL,                 'Dragon Ball', 'dragon_ball', 'FB08', 'TCG', 'active',  220, DATE '2025-12-13', 0),
        ('DB-FB09', 'ブースターパック DUAL EVOLUTION',      'DUAL EVOLUTION',     'Dragon Ball', 'dragon_ball', 'FB09', 'TCG', 'active',  220, DATE '2026-03-14', 0),
        ('DB-FB10', 'ブースターパック CROSS FORCE',         'CROSS FORCE',        'Dragon Ball', 'dragon_ball', 'FB10', 'TCG', 'active',  220, DATE '2026-06-13', 0),
        ('DB-FB11', 'ブースターパック BRIGHTNESS OF HOPE',  'BRIGHTNESS OF HOPE', 'Dragon Ball', 'dragon_ball', 'FB11', 'TCG', 'active',  240, NULL,             0),
        ('DB-SB01', 'MANGA BOOSTER 01',                     'MANGA BOOSTER 01',   'Dragon Ball', 'dragon_ball', 'SB01', 'TCG', 'active',  330, DATE '2025-06-28', 0),
        ('DB-SB02', 'MANGA BOOSTER 02',                     'MANGA BOOSTER 02',   'Dragon Ball', 'dragon_ball', 'SB02', 'TCG', 'active',  330, DATE '2025-11-08', 0),
        ('DB-ST01', 'STORY BOOSTER 01',                     'STORY BOOSTER 01',   'Dragon Ball', 'dragon_ball', 'ST01', 'TCG', 'active',  330, DATE '2026-08-08', 0),
        -- Starter Deck (FSxx)
        ('DB-FS01', 'スタートデッキ 孫悟空',                NULL,                 'Dragon Ball', 'dragon_ball', 'FS01', 'TCG', 'active',  990, DATE '2024-02-16', 0),
        ('DB-FS02', 'スタートデッキ ベジータ',              NULL,                 'Dragon Ball', 'dragon_ball', 'FS02', 'TCG', 'active',  990, DATE '2024-02-16', 0),
        ('DB-FS03', 'スタートデッキ ブロリー',              NULL,                 'Dragon Ball', 'dragon_ball', 'FS03', 'TCG', 'active',  990, DATE '2024-02-16', 0),
        ('DB-FS04', 'スタートデッキ フリーザ',              NULL,                 'Dragon Ball', 'dragon_ball', 'FS04', 'TCG', 'active',  990, DATE '2024-02-16', 0),
        ('DB-FS05', 'スタートデッキ バーダック',            NULL,                 'Dragon Ball', 'dragon_ball', 'FS05', 'TCG', 'active',  990, DATE '2024-08-09', 0),
        ('DB-FS06', 'スタートデッキ 孫悟空(ミニ)',          NULL,                 'Dragon Ball', 'dragon_ball', 'FS06', 'TCG', 'active',  550, DATE '2024-11-08', 0),
        ('DB-FS07', 'スタートデッキ ベジータ(ミニ)',        NULL,                 'Dragon Ball', 'dragon_ball', 'FS07', 'TCG', 'active',  550, DATE '2024-11-08', 0),
        ('DB-FS08', 'スタートデッキ -ベジータ(ミニ) 超サイヤ人3-', NULL,          'Dragon Ball', 'dragon_ball', 'FS08', 'TCG', 'active',  990, DATE '2025-04-26', 0),
        ('DB-FS09', 'スタートデッキEX シャロット',          NULL,                 'Dragon Ball', 'dragon_ball', 'FS09', 'TCG', 'active', 2640, DATE '2025-06-14', 0),
        ('DB-FS10', 'スタートデッキEX ジブレット',          NULL,                 'Dragon Ball', 'dragon_ball', 'FS10', 'TCG', 'active', 2640, DATE '2025-06-14', 0),
        ('DB-FS11', 'スタートデッキEX 進化の境地',          NULL,                 'Dragon Ball', 'dragon_ball', 'FS11', 'TCG', 'active', 2640, DATE '2026-03-14', 0),
        ('DB-FS12', 'スタートデッキEX 気の躍動',            NULL,                 'Dragon Ball', 'dragon_ball', 'FS12', 'TCG', 'active', 2640, DATE '2026-03-14', 0)
    ON CONFLICT (product_code) WHERE product_code IS NOT NULL DO UPDATE SET
        name         = EXCLUDED.name,
        name_en      = EXCLUDED.name_en,
        category     = EXCLUDED.category,
        tcg_type     = EXCLUDED.tcg_type,
        mark         = EXCLUDED.mark,
        product_kind = EXCLUDED.product_kind,
        status       = EXCLUDED.status,
        unit_price   = EXCLUDED.unit_price,
        release_date = EXCLUDED.release_date,
        updated_at   = NOW();
END $$;
