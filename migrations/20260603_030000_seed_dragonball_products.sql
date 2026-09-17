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
DECLARE
    v_work_id UUID;
    v_schema  TEXT;
BEGIN
    -- migration-test の最小 baseline には public.products の中央カラム
    -- (category / tcg_type / mark / product_kind / release_date) が無いことがある。
    -- それらを追加する additive migration はこの seed より前に本番適用済みのため、
    -- カラムが揃っている時だけ INSERT する（揃っていなければ skip）。
    IF to_regclass('public.products') IS NULL
       OR (
           SELECT COUNT(*) FROM information_schema.columns
           WHERE table_schema = 'public' AND table_name = 'products'
             AND column_name IN ('category', 'tcg_type', 'mark', 'product_kind', 'release_date')
       ) < 5 THEN
        RAISE NOTICE 'public.products central columns not present (migration-test baseline) — skipping seed';
        RETURN;
    END IF;

    -- work_id 動的取得（テナント tcg_series から）
    SELECT nspname INTO v_schema
    FROM pg_namespace n
    JOIN pg_class c ON c.relnamespace = n.oid AND c.relname = 'tcg_series' AND c.relkind = 'r'
    WHERE n.nspname LIKE 'tenant_%'
    ORDER BY n.nspname LIMIT 1;

    IF v_schema IS NOT NULL THEN
        EXECUTE format('SELECT id FROM %I.tcg_series WHERE code = $1', v_schema)
            INTO v_work_id USING 'IP003';
    END IF;

    -- work_id NOT NULL 制約が存在するのにシリーズが見つからない場合はスキップ
    IF v_work_id IS NULL AND EXISTS (
        SELECT 1 FROM pg_attribute
        WHERE attrelid = 'public.products'::regclass
          AND attname = 'work_id' AND attnotnull
    ) THEN
        RAISE NOTICE 'work_id NOT NULL active but Dragon Ball series not found — skipping seed';
        RETURN;
    END IF;

    INSERT INTO public.products
        (product_code, name, name_en, category, tcg_type, mark, product_kind,
         status, unit_price, release_date, stock_quantity, work_id)
    VALUES
        -- Booster Pack (FBxx / SBxx / STxx)
        ('DB-FB01', 'ブースターパック 覚醒の鼓動',          NULL,                 'Dragon Ball', 'dragon_ball', 'FB01', 'TCG', 'active',  220, DATE '2024-02-16', 0, v_work_id),
        ('DB-FB02', 'ブースターパック 烈火の闘気',          NULL,                 'Dragon Ball', 'dragon_ball', 'FB02', 'TCG', 'active',  220, DATE '2024-05-10', 0, v_work_id),
        ('DB-FB03', 'ブースターパック 怒りの咆哮',          NULL,                 'Dragon Ball', 'dragon_ball', 'FB03', 'TCG', 'active',  220, DATE '2024-08-09', 0, v_work_id),
        ('DB-FB04', 'ブースターパック 限界を超えし者',      NULL,                 'Dragon Ball', 'dragon_ball', 'FB04', 'TCG', 'active',  220, DATE '2024-11-08', 0, v_work_id),
        ('DB-FB05', 'ブースターパック 未知なる冒険',        NULL,                 'Dragon Ball', 'dragon_ball', 'FB05', 'TCG', 'active',  220, DATE '2025-02-08', 0, v_work_id),
        ('DB-FB06', 'ブースターパック 迫り来る脅威',        NULL,                 'Dragon Ball', 'dragon_ball', 'FB06', 'TCG', 'active',  220, DATE '2025-04-26', 0, v_work_id),
        ('DB-FB07', 'ブースターパック 神龍への願い',        NULL,                 'Dragon Ball', 'dragon_ball', 'FB07', 'TCG', 'active',  220, DATE '2025-09-13', 0, v_work_id),
        ('DB-FB08', 'ブースターパック 誇り高き戦闘民族',    NULL,                 'Dragon Ball', 'dragon_ball', 'FB08', 'TCG', 'active',  220, DATE '2025-12-13', 0, v_work_id),
        ('DB-FB09', 'ブースターパック DUAL EVOLUTION',      'DUAL EVOLUTION',     'Dragon Ball', 'dragon_ball', 'FB09', 'TCG', 'active',  220, DATE '2026-03-14', 0, v_work_id),
        ('DB-FB10', 'ブースターパック CROSS FORCE',         'CROSS FORCE',        'Dragon Ball', 'dragon_ball', 'FB10', 'TCG', 'active',  220, DATE '2026-06-13', 0, v_work_id),
        ('DB-FB11', 'ブースターパック BRIGHTNESS OF HOPE',  'BRIGHTNESS OF HOPE', 'Dragon Ball', 'dragon_ball', 'FB11', 'TCG', 'active',  240, NULL,             0, v_work_id),
        ('DB-SB01', 'MANGA BOOSTER 01',                     'MANGA BOOSTER 01',   'Dragon Ball', 'dragon_ball', 'SB01', 'TCG', 'active',  330, DATE '2025-06-28', 0, v_work_id),
        ('DB-SB02', 'MANGA BOOSTER 02',                     'MANGA BOOSTER 02',   'Dragon Ball', 'dragon_ball', 'SB02', 'TCG', 'active',  330, DATE '2025-11-08', 0, v_work_id),
        ('DB-ST01', 'STORY BOOSTER 01',                     'STORY BOOSTER 01',   'Dragon Ball', 'dragon_ball', 'ST01', 'TCG', 'active',  330, DATE '2026-08-08', 0, v_work_id),
        -- Starter Deck (FSxx)
        ('DB-FS01', 'スタートデッキ 孫悟空',                NULL,                 'Dragon Ball', 'dragon_ball', 'FS01', 'TCG', 'active',  990, DATE '2024-02-16', 0, v_work_id),
        ('DB-FS02', 'スタートデッキ ベジータ',              NULL,                 'Dragon Ball', 'dragon_ball', 'FS02', 'TCG', 'active',  990, DATE '2024-02-16', 0, v_work_id),
        ('DB-FS03', 'スタートデッキ ブロリー',              NULL,                 'Dragon Ball', 'dragon_ball', 'FS03', 'TCG', 'active',  990, DATE '2024-02-16', 0, v_work_id),
        ('DB-FS04', 'スタートデッキ フリーザ',              NULL,                 'Dragon Ball', 'dragon_ball', 'FS04', 'TCG', 'active',  990, DATE '2024-02-16', 0, v_work_id),
        ('DB-FS05', 'スタートデッキ バーダック',            NULL,                 'Dragon Ball', 'dragon_ball', 'FS05', 'TCG', 'active',  990, DATE '2024-08-09', 0, v_work_id),
        ('DB-FS06', 'スタートデッキ 孫悟空(ミニ)',          NULL,                 'Dragon Ball', 'dragon_ball', 'FS06', 'TCG', 'active',  550, DATE '2024-11-08', 0, v_work_id),
        ('DB-FS07', 'スタートデッキ ベジータ(ミニ)',        NULL,                 'Dragon Ball', 'dragon_ball', 'FS07', 'TCG', 'active',  550, DATE '2024-11-08', 0, v_work_id),
        ('DB-FS08', 'スタートデッキ -ベジータ(ミニ) 超サイヤ人3-', NULL,          'Dragon Ball', 'dragon_ball', 'FS08', 'TCG', 'active',  990, DATE '2025-04-26', 0, v_work_id),
        ('DB-FS09', 'スタートデッキEX シャロット',          NULL,                 'Dragon Ball', 'dragon_ball', 'FS09', 'TCG', 'active', 2640, DATE '2025-06-14', 0, v_work_id),
        ('DB-FS10', 'スタートデッキEX ジブレット',          NULL,                 'Dragon Ball', 'dragon_ball', 'FS10', 'TCG', 'active', 2640, DATE '2025-06-14', 0, v_work_id),
        ('DB-FS11', 'スタートデッキEX 進化の境地',          NULL,                 'Dragon Ball', 'dragon_ball', 'FS11', 'TCG', 'active', 2640, DATE '2026-03-14', 0, v_work_id),
        ('DB-FS12', 'スタートデッキEX 気の躍動',            NULL,                 'Dragon Ball', 'dragon_ball', 'FS12', 'TCG', 'active', 2640, DATE '2026-03-14', 0, v_work_id)
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
        work_id      = COALESCE(EXCLUDED.work_id, products.work_id),
        updated_at   = NOW();
END $$;
