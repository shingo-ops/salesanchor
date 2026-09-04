-- ポケモン商品マスタ 25商品の新規登録（tenant_004 専用・冪等）
--
-- 内訳: MEGA スターターセットex 4 / 30th CELEBRATION カードセット 9
--       スタートデッキ100 コロちゃおVer. 1 / SVD exスタートデッキ 11
-- 既存への変更: PM0200 に除外キーワード「コロちゃお」「コロチャオ」を追加するのみ
-- 承認: Shingo 2026-09-04
-- バックアップ:
--   tenant_004.tcg_products_bak_20260904b              (271)
--   tenant_004.product_search_keywords_bak_20260904b   (600)
--   tenant_004.product_exclude_keywords_bak_20260904b  (129)
--
-- 設計判断:
--   - 既存キーワードは1本も削除しない（追加のみ）
--   - 単品3種には除外キーワード「種セット」を付け、N種セットを拾わせない
--   - 検証は担当範囲（PM0272〜PM0296）だけを数える

DO $body$
DECLARE
    _schema      TEXT := 'tenant_004';
    v_div        uuid;
    v_work       uuid;
    v_mfr        uuid;
    v_cat        uuid;
    v_count      integer;
    v_pm0200     uuid;
    r            RECORD;
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_namespace WHERE nspname = _schema
    ) THEN
        RAISE NOTICE 'migration 20260905_010000: schema % does not exist, skipping', _schema;
        RETURN;
    END IF;

    EXECUTE format($q$SELECT id FROM %I.tcg_major_categories  WHERE code = 'DIV01'$q$,     _schema) INTO v_div;
    EXECUTE format($q$SELECT id FROM %I.tcg_series             WHERE code = 'IP001'$q$,     _schema) INTO v_work;
    EXECUTE format($q$SELECT id FROM %I.tcg_manufacturers      WHERE code = 'MK001'$q$,     _schema) INTO v_mfr;
    EXECUTE format($q$SELECT id FROM %I.tcg_product_categories WHERE code = 'PC_BOX'$q$,    _schema) INTO v_cat;

    IF v_div IS NULL OR v_work IS NULL OR v_mfr IS NULL OR v_cat IS NULL THEN
        RAISE EXCEPTION '20260905_010000: 参照マスタが見つかりません';
    END IF;

    -- 1. 商品の登録（25件）
    EXECUTE format($q$
        INSERT INTO %I.tcg_products
            (code, japanese_title, english_title, mark, release_date, category_class,
             division_id, work_id, manufacturer_id, product_category_id, is_active)
        VALUES
            ('PM0272','ポケモンカードゲーム MEGA スターターセットex イーブイex','MEGA Starter Set ex Eevee ex','MEE',DATE '2026-07-31','Box',$1,$2,$3,$4,TRUE),
            ('PM0273','ポケモンカードゲーム MEGA スターターセットex ゾロア＆ゾロアークex','MEGA Starter Set ex Zorua & Zoroark ex','MEZ',DATE '2026-07-31','Box',$1,$2,$3,$4,TRUE),
            ('PM0274','ポケモンカードゲーム MEGA スターターセットex ニャオハ＆マスカーニャex','MEGA Starter Set ex Sprigatito & Meowscarada ex','MEM',DATE '2026-07-31','Box',$1,$2,$3,$4,TRUE),
            ('PM0275','ポケモンカードゲーム MEGA スターターセットex 3種セット','MEGA Starter Set ex 3-Deck Set',NULL,DATE '2026-07-31','Box',$1,$2,$3,$4,TRUE),
            ('PM0276','ポケモンカードゲーム MEGA 30th CELEBRATION カードセット フシギダネ・ヒトカゲ・ゼニガメ','30th Celebration Card Set - Bulbasaur, Charmander & Squirtle',NULL,DATE '2026-10-16','Box',$1,$2,$3,$4,TRUE),
            ('PM0277','ポケモンカードゲーム MEGA 30th CELEBRATION カードセット チコリータ・ヒノアラシ・ワニノコ','30th Celebration Card Set - Chikorita, Cyndaquil & Totodile',NULL,DATE '2026-10-16','Box',$1,$2,$3,$4,TRUE),
            ('PM0278','ポケモンカードゲーム MEGA 30th CELEBRATION カードセット キモリ・アチャモ・ミズゴロウ','30th Celebration Card Set - Treecko, Torchic & Mudkip',NULL,DATE '2026-10-16','Box',$1,$2,$3,$4,TRUE),
            ('PM0279','ポケモンカードゲーム MEGA 30th CELEBRATION カードセット ナエトル・ヒコザル・ポッチャマ','30th Celebration Card Set - Turtwig, Chimchar & Piplup',NULL,DATE '2026-10-16','Box',$1,$2,$3,$4,TRUE),
            ('PM0280','ポケモンカードゲーム MEGA 30th CELEBRATION カードセット ツタージャ・ポカブ・ミジュマル','30th Celebration Card Set - Snivy, Tepig & Oshawott',NULL,DATE '2026-10-16','Box',$1,$2,$3,$4,TRUE),
            ('PM0281','ポケモンカードゲーム MEGA 30th CELEBRATION カードセット ハリマロン・フォッコ・ケロマツ','30th Celebration Card Set - Chespin, Fennekin & Froakie',NULL,DATE '2026-10-16','Box',$1,$2,$3,$4,TRUE),
            ('PM0282','ポケモンカードゲーム MEGA 30th CELEBRATION カードセット モクロー・ニャビー・アシマリ','30th Celebration Card Set - Rowlet, Litten & Popplio',NULL,DATE '2026-10-16','Box',$1,$2,$3,$4,TRUE),
            ('PM0283','ポケモンカードゲーム MEGA 30th CELEBRATION カードセット サルノリ・ヒバニー・メッソン','30th Celebration Card Set - Grookey, Scorbunny & Sobble',NULL,DATE '2026-10-16','Box',$1,$2,$3,$4,TRUE),
            ('PM0284','ポケモンカードゲーム MEGA 30th CELEBRATION カードセット ニャオハ・ホゲータ・クワッス','30th Celebration Card Set - Sprigatito, Fuecoco & Quaxly',NULL,DATE '2026-10-16','Box',$1,$2,$3,$4,TRUE),
            ('PM0285','ポケモンカードゲーム MEGA スタートデッキ100 バトルコレクション コロちゃおVer.','Start Deck 100 Battle Collection CoroCiao Version','MP1',DATE '2025-12-19','Box',$1,$2,$3,$4,TRUE),
            ('PM0286','ポケモンカードゲーム スカーレット＆バイオレット exスタートデッキ 草 ジュナイパー','ex Starter Deck Decidueye ex','SVD',DATE '2023-07-07','Box',$1,$2,$3,$4,TRUE),
            ('PM0287','ポケモンカードゲーム スカーレット＆バイオレット exスタートデッキ 炎 ビクティニ','ex Starter Deck Victini ex','SVD',DATE '2023-07-07','Box',$1,$2,$3,$4,TRUE),
            ('PM0288','ポケモンカードゲーム スカーレット＆バイオレット exスタートデッキ 水 ゲッコウガ','ex Starter Deck Greninja ex','SVD',DATE '2023-07-07','Box',$1,$2,$3,$4,TRUE),
            ('PM0289','ポケモンカードゲーム スカーレット＆バイオレット exスタートデッキ 雷 ミライドン','ex Starter Deck Miraidon ex','SVD',DATE '2023-07-07','Box',$1,$2,$3,$4,TRUE),
            ('PM0290','ポケモンカードゲーム スカーレット＆バイオレット exスタートデッキ 超 ピクシー','ex Starter Deck Clefable ex','SVD',DATE '2023-07-07','Box',$1,$2,$3,$4,TRUE),
            ('PM0291','ポケモンカードゲーム スカーレット＆バイオレット exスタートデッキ 闘 コライドン','ex Starter Deck Koraidon ex','SVD',DATE '2023-07-07','Box',$1,$2,$3,$4,TRUE),
            ('PM0292','ポケモンカードゲーム スカーレット＆バイオレット exスタートデッキ 悪 ヘルガー','ex Starter Deck Houndoom ex','SVD',DATE '2023-07-07','Box',$1,$2,$3,$4,TRUE),
            ('PM0293','ポケモンカードゲーム スカーレット＆バイオレット exスタートデッキ 鋼 メルメタル','ex Starter Deck Melmetal ex','SVD',DATE '2023-07-07','Box',$1,$2,$3,$4,TRUE),
            ('PM0294','ポケモンカードゲーム スカーレット＆バイオレット おまかせexスタートデッキ','Random ex Starter Deck','SVD',DATE '2023-07-07','Box',$1,$2,$3,$4,TRUE),
            ('PM0295','ポケモンカードゲーム スカーレット＆バイオレット exスタートデッキ テラスタル カイリュー','ex Starter Deck Terastal Dragonite ex','SVD',DATE '2023-11-24','Box',$1,$2,$3,$4,TRUE),
            ('PM0296','ポケモンカードゲーム スカーレット＆バイオレット exスタートデッキ テラスタル ヨクバリス','ex Starter Deck Terastal Greedent ex','SVD',DATE '2023-11-24','Box',$1,$2,$3,$4,TRUE)
        ON CONFLICT (code) DO NOTHING
    $q$, _schema) USING v_div, v_work, v_mfr, v_cat;

    -- 2. 検索キーワードの登録
    FOR r IN
        SELECT * FROM (VALUES
            ('PM0272','スターターセットex イーブイ',1),
            ('PM0272','イーブイex',2),
            ('PM0273','スターターセットex ゾロア',1),
            ('PM0273','ゾロアークex',2),
            ('PM0274','スターターセットex ニャオハ',1),
            ('PM0274','マスカーニャex',2),
            ('PM0275','スターターセットex 3種セット',1),
            ('PM0275','スターターセットex ３種セット',2),
            ('PM0276','カードセット フシギダネ',1),
            ('PM0277','カードセット チコリータ',1),
            ('PM0278','カードセット キモリ',1),
            ('PM0279','カードセット ナエトル',1),
            ('PM0280','カードセット ツタージャ',1),
            ('PM0281','カードセット ハリマロン',1),
            ('PM0282','カードセット モクロー',1),
            ('PM0283','カードセット サルノリ',1),
            ('PM0284','カードセット ニャオハ',1),
            ('PM0285','コロちゃお',1),
            ('PM0285','コロチャオ',2),
            ('PM0286','exスタートデッキ ジュナイパー',1),
            ('PM0287','exスタートデッキ ビクティニ',1),
            ('PM0288','exスタートデッキ ゲッコウガ',1),
            ('PM0289','exスタートデッキ ミライドン',1),
            ('PM0290','exスタートデッキ ピクシー',1),
            ('PM0291','exスタートデッキ コライドン',1),
            ('PM0292','exスタートデッキ ヘルガー',1),
            ('PM0293','exスタートデッキ メルメタル',1),
            ('PM0294','おまかせexスタートデッキ',1),
            ('PM0295','exスタートデッキ テラスタル カイリュー',1),
            ('PM0296','exスタートデッキ テラスタル ヨクバリス',1)
        ) AS t(code, kw, pos)
    LOOP
        EXECUTE format($q$
            INSERT INTO %I.product_search_keywords (product_id, keyword, position)
            SELECT p.id, $2, $3 FROM %I.tcg_products p WHERE p.code = $1
            ON CONFLICT (product_id, keyword) DO NOTHING
        $q$, _schema, _schema) USING r.code, r.kw, r.pos;
    END LOOP;

    -- 3. 除外キーワードの登録（単品3種に「種セット」）
    FOR r IN
        SELECT * FROM (VALUES
            ('PM0272','種セット'),
            ('PM0273','種セット'),
            ('PM0274','種セット')
        ) AS t(code, kw)
    LOOP
        EXECUTE format($q$
            INSERT INTO %I.product_exclude_keywords (product_id, keyword, position)
            SELECT p.id, $2, COALESCE((SELECT MAX(k.position) FROM %I.product_exclude_keywords k WHERE k.product_id = p.id), 0) + 1
              FROM %I.tcg_products p WHERE p.code = $1
            ON CONFLICT DO NOTHING
        $q$, _schema, _schema, _schema) USING r.code, r.kw;
    END LOOP;

    -- 4. 既存 PM0200 に除外キーワードを追加（コロちゃお版を拾わせない）
    EXECUTE format($q$SELECT id FROM %I.tcg_products WHERE code = 'PM0200'$q$, _schema) INTO v_pm0200;
    IF v_pm0200 IS NULL THEN
        RAISE EXCEPTION '20260905_010000: PM0200 が見つかりません';
    END IF;

    FOR r IN SELECT * FROM (VALUES ('コロちゃお'), ('コロチャオ')) AS t(kw)
    LOOP
        EXECUTE format($q$
            INSERT INTO %I.product_exclude_keywords (product_id, keyword, position)
            SELECT $1, $2, COALESCE((SELECT MAX(k.position) FROM %I.product_exclude_keywords k WHERE k.product_id = $1), 0) + 1
            ON CONFLICT DO NOTHING
        $q$, _schema, _schema) USING v_pm0200, r.kw;
    END LOOP;

    -- 5. 検証: 担当範囲だけを数える
    EXECUTE format($q$
        SELECT count(*) FROM %I.tcg_products WHERE code BETWEEN 'PM0272' AND 'PM0296'
    $q$, _schema) INTO v_count;
    IF v_count != 25 THEN
        RAISE EXCEPTION '20260905_010000: 新規商品が25件ではありません: %', v_count;
    END IF;

    EXECUTE format($q$
        SELECT count(*) FROM %I.tcg_products p
         WHERE p.code BETWEEN 'PM0272' AND 'PM0296'
           AND NOT EXISTS (SELECT 1 FROM %I.product_search_keywords k WHERE k.product_id = p.id)
    $q$, _schema, _schema) INTO v_count;
    IF v_count != 0 THEN
        RAISE EXCEPTION '20260905_010000: 検索キーワードが空の新規商品があります: %', v_count;
    END IF;

    EXECUTE format($q$
        SELECT count(*) FROM %I.product_exclude_keywords k
         JOIN %I.tcg_products p ON p.id = k.product_id
         WHERE p.code = 'PM0200' AND k.keyword IN ('コロちゃお','コロチャオ')
    $q$, _schema, _schema) INTO v_count;
    IF v_count != 2 THEN
        RAISE EXCEPTION '20260905_010000: PM0200 の除外キーワードが2件ではありません: %', v_count;
    END IF;

    RAISE NOTICE '20260905_010000: 25 pokemon products registered in schema %', _schema;
END $body$;
