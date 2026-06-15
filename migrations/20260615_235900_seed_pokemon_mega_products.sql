-- ============================================================================
-- Migration 20260615_235900: ポケモンカードゲーム MEGA シリーズ 商品マスタ投入
--
-- 対象: ポケモンカードゲーム MEGA（2025年8月1日 シリーズ開始）
--   - リンクあり商品 14 件（product_code = 'PKM-<略称>'）
--   - リンクなし商品 11 件（product_code NULL）
--
-- 出典:
--   - 略称(product_code): wiki.pokemonwiki.com 各商品ページの「略称」フィールド
--   - 英語名(name_en): Bulbapedia（公式英語名がない商品は NULL）
--   - 発売日・価格: wiki.pokemonwiki.com 各商品ページ
--
-- 冪等:
--   Phase 1: 既存の短縮名エントリに product_code を付与（重複 INSERT 防止）
--   Phase 2: INSERT ON CONFLICT (product_code) WHERE product_code IS NOT NULL DO UPDATE
--   Phase 3: リンクなし商品は WHERE NOT EXISTS で重複回避
-- ============================================================================

DO $$
BEGIN
    -- 列ガード
    IF to_regclass('public.products') IS NULL
       OR NOT EXISTS (
           SELECT 1 FROM information_schema.columns
           WHERE table_schema = 'public' AND table_name = 'products'
             AND column_name IN ('category', 'tcg_type', 'mark', 'product_code', 'set_type')
       ) THEN
        RAISE NOTICE 'public.products central columns not present (migration-test baseline) -- skipping';
        RETURN;
    END IF;

    -- =========================================================================
    -- Phase 1: 既存の短縮名エントリに product_code を付与
    --          seed_product_marks.sql が参照していた短縮名と公式 略称 を対応付ける。
    --          これにより Phase 2 の INSERT が既存エントリを正規化 UPDATE できる。
    -- =========================================================================
    UPDATE public.products SET product_code = 'PKM-M1L', mark = 'M1L', updated_at = NOW()
    WHERE name IN ('メガブレイブ') AND tenant_id IS NULL AND product_code IS NULL;

    UPDATE public.products SET product_code = 'PKM-M1S', mark = 'M1S', updated_at = NOW()
    WHERE name IN ('メガシンフォニア') AND tenant_id IS NULL AND product_code IS NULL;

    UPDATE public.products SET product_code = 'PKM-MA', mark = 'MA', updated_at = NOW()
    WHERE name IN ('プレミアムトレーナーボックスMEGA') AND tenant_id IS NULL AND product_code IS NULL;

    UPDATE public.products SET product_code = 'PKM-M2', mark = 'M2', updated_at = NOW()
    WHERE name IN ('インフェルノX') AND tenant_id IS NULL AND product_code IS NULL;

    UPDATE public.products SET product_code = 'PKM-M2a', mark = 'M2a', updated_at = NOW()
    WHERE name IN ('MEGAドリームex') AND tenant_id IS NULL AND product_code IS NULL;

    UPDATE public.products SET product_code = 'PKM-MC', mark = 'MC', updated_at = NOW()
    WHERE name IN ('MEGA スタートデッキ100 バトルコレクション') AND tenant_id IS NULL AND product_code IS NULL;

    UPDATE public.products SET product_code = 'PKM-M3', mark = 'M3', updated_at = NOW()
    WHERE name IN ('ムニキスゼロ') AND tenant_id IS NULL AND product_code IS NULL;

    UPDATE public.products SET product_code = 'PKM-M4', mark = 'M4', updated_at = NOW()
    WHERE name IN ('ニンジャスピナー') AND tenant_id IS NULL AND product_code IS NULL;

    -- =========================================================================
    -- Phase 2: リンクあり商品 14 件 — product_code をキーに投入
    --          ON CONFLICT DO UPDATE で既存エントリを正規化（name を正式名称に統一）
    -- =========================================================================
    INSERT INTO public.products
        (product_code, name, name_en, category, tcg_type, mark, product_kind,
         set_type, status, unit_price, release_date, stock_quantity)
    VALUES
        ('PKM-M1L',  '拡張パック メガブレイブ',                          'Mega Brave',                     'ポケモンカードゲーム', 'pokemon', 'M1L',  'TCG', 'booster', 'active',  180,   DATE '2025-08-01', 0),
        ('PKM-M1S',  '拡張パック メガシンフォニア',                        'Mega Symphonia',                 'ポケモンカードゲーム', 'pokemon', 'M1S',  'TCG', 'booster', 'active',  180,   DATE '2025-08-01', 0),
        ('PKM-MA',   'プレミアムトレーナーボックス MEGA',                   'Premium Trainer Box MEGA',       'ポケモンカードゲーム', 'pokemon', 'MA',   'TCG', 'deck',    'active',  6350,  DATE '2025-08-01', 0),
        ('PKM-MBG',  'スターターセットMEGA メガゲンガーex',                 'MEGA Starter Set Mega Gengar ex','ポケモンカードゲーム', 'pokemon', 'MBG',  'TCG', 'deck',    'active',  1800,  DATE '2025-09-05', 0),
        ('PKM-MBD',  'スターターセットMEGA メガディアンシーex',              'MEGA Starter Set Mega Diancie ex','ポケモンカードゲーム','pokemon', 'MBD',  'TCG', 'deck',    'active',  NULL,  DATE '2025-12-19', 0),
        ('PKM-M2',   '拡張パック インフェルノX',                           'Inferno X',                      'ポケモンカードゲーム', 'pokemon', 'M2',   'TCG', 'booster', 'active',  180,   DATE '2025-09-26', 0),
        ('PKM-M2a',  'ハイクラスパック MEGAドリームex',                     NULL,                             'ポケモンカードゲーム', 'pokemon', 'M2a',  'TCG', 'booster', 'active',  550,   DATE '2025-11-28', 0),
        ('PKM-MC',   'スタートデッキ100 バトルコレクション',                 NULL,                             'ポケモンカードゲーム', 'pokemon', 'MC',   'TCG', 'deck',    'active',  891,   DATE '2025-12-19', 0),
        ('PKM-MP1',  'スタートデッキ100 バトルコレクション コロちゃおVer.', NULL,                             'ポケモンカードゲーム', 'pokemon', 'MP1',  'TCG', 'deck',    'active',  NULL,  DATE '2025-12-19', 0),
        ('PKM-M3',   '拡張パック ムニキスゼロ',                            NULL,                             'ポケモンカードゲーム', 'pokemon', 'M3',   'TCG', 'booster', 'active',  180,   DATE '2026-01-23', 0),
        ('PKM-M4',   '拡張パック ニンジャスピナー',                         NULL,                             'ポケモンカードゲーム', 'pokemon', 'M4',   'TCG', 'booster', 'active',  180,   DATE '2026-03-13', 0),
        ('PKM-M5',   '拡張パック アビスアイ',                              NULL,                             'ポケモンカードゲーム', 'pokemon', 'M5',   'TCG', 'booster', 'active',  200,   DATE '2026-05-22', 0),
        ('PKM-M6a',  '拡張パック 30th CELEBRATION',                       '30th Celebration',               'ポケモンカードゲーム', 'pokemon', 'M6a',  'TCG', 'booster', 'active',  360,   DATE '2026-09-16', 0),
        ('PKM-MF',   '30th CELEBRATION プレミアムデッキセット エーフィ・ブラッキー', NULL,                  'ポケモンカードゲーム', 'pokemon', 'MF',   'TCG', 'deck',    'active',  6200,  DATE '2026-09-16', 0)
    ON CONFLICT (product_code) WHERE product_code IS NOT NULL DO UPDATE SET
        name         = EXCLUDED.name,
        name_en      = COALESCE(EXCLUDED.name_en, public.products.name_en),
        mark         = EXCLUDED.mark,
        category     = EXCLUDED.category,
        tcg_type     = EXCLUDED.tcg_type,
        set_type     = EXCLUDED.set_type,
        release_date = COALESCE(EXCLUDED.release_date, public.products.release_date),
        unit_price   = COALESCE(EXCLUDED.unit_price, public.products.unit_price),
        updated_at   = NOW();

    -- =========================================================================
    -- Phase 3: リンクなし商品 11 件（product_code なし）
    --          スペシャルカードセット / 30th CELEBRATION 関連
    --          WHERE NOT EXISTS で同名エントリの重複挿入を防ぐ
    -- =========================================================================
    INSERT INTO public.products
        (name, name_en, category, tcg_type, product_kind,
         set_type, status, unit_price, release_date, stock_quantity)
    SELECT v.name, NULL, 'ポケモンカードゲーム', 'pokemon', 'TCG',
           v.set_type, 'active', v.unit_price, v.release_date, 0
    FROM (VALUES
        ('スペシャルカードセット メガエルレイドex',                               'deck',  1980,   DATE '2026-01-23'),
        ('30th CELEBRATION FUTURISTIC BOX',                                   'deck',  27500,  DATE '2026-09-16'),
        ('30th CELEBRATION カードセット フシギダネ・ヒトカゲ・ゼニガメ',            'deck',  1200,   DATE '2026-10-16'),
        ('30th CELEBRATION カードセット チコリータ・ヒノアラシ・ワニノコ',          'deck',  1200,   DATE '2026-10-16'),
        ('30th CELEBRATION カードセット キモリ・アチャモ・ミズゴロウ',             'deck',  1200,   DATE '2026-10-16'),
        ('30th CELEBRATION カードセット ナエトル・ヒコザル・ポッチャマ',            'deck',  1200,   DATE '2026-10-16'),
        ('30th CELEBRATION カードセット ツタージャ・ポカブ・ミジュマル',            'deck',  1200,   DATE '2026-10-16'),
        ('30th CELEBRATION カードセット ハリマロン・フォッコ・ケロマツ',            'deck',  1200,   DATE '2026-10-16'),
        ('30th CELEBRATION カードセット モクロー・ニャビー・アシマリ',             'deck',  1200,   DATE '2026-10-16'),
        ('30th CELEBRATION カードセット サルノリ・ヒバニー・メッソン',             'deck',  1200,   DATE '2026-10-16'),
        ('30th CELEBRATION カードセット ニャオハ・ホゲータ・クワッス',             'deck',  1200,   DATE '2026-10-16')
    ) AS v(name, set_type, unit_price, release_date)
    WHERE NOT EXISTS (
        SELECT 1 FROM public.products p
        WHERE p.name = v.name AND p.tenant_id IS NULL
    );

END $$;
