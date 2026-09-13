-- 既存商品5件の名称・型番の訂正（tenant_004 専用・冪等）
--
-- 公式サイトと突き合わせて判明した誤りを直す。
-- 変更するのは japanese_title 4件と mark 1件のみ。
-- キーワード・除外キーワード・発売日・英語名は一切変更しない。
--
-- 承認: Shingo 2026-09-05
-- バックアップ: tenant_004.tcg_products_bak_20260905 (296)
--
-- 出典:
--   PM0056 公式商品一覧 pokemon-card.com/products/
--   PM0182 PM0186 PM0189 公式ニュース pokemon-card.com/info/005053.html
--   PM0200 公式商品ページURL pokemon-card.com/ex/mc/ ほか4サイト一致

DO $body$
DECLARE
    _schema  TEXT := 'tenant_004';
    v_count  integer;
    r        RECORD;
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_namespace WHERE nspname = _schema
    ) THEN
        RAISE NOTICE 'migration 20260905_020000: schema % does not exist, skipping', _schema;
        RETURN;
    END IF;

    -- 1. 商品名の訂正（4件）
    FOR r IN
        SELECT * FROM (VALUES
            ('PM0056','スペシャルBOX ポケモンセンターカナザワオープン記念'),
            ('PM0182','スペシャルBOX ポケモンセンタートウホク'),
            ('PM0186','スペシャルBOX ポケモンセンターヒロシマ'),
            ('PM0189','スペシャルBOX ポケモンセンターフクオカ')
        ) AS t(code, title)
    LOOP
        EXECUTE format($q$
            UPDATE %I.tcg_products SET japanese_title = $2 WHERE code = $1
        $q$, _schema) USING r.code, r.title;
    END LOOP;

    -- 2. 型番の訂正（1件）
    EXECUTE format($q$
        UPDATE %I.tcg_products SET mark = 'MC' WHERE code = 'PM0200'
    $q$, _schema);

    -- 3. 検証: 訂正後の値が入っていること
    EXECUTE format($q$
        SELECT count(*) FROM %I.tcg_products
         WHERE code IN ('PM0056','PM0182','PM0186','PM0189')
           AND japanese_title LIKE 'スペシャルBOX ポケモンセンター%%'
    $q$, _schema) INTO v_count;
    IF v_count != 4 THEN
        RAISE EXCEPTION '20260905_020000: 商品名の訂正が4件ではありません: %', v_count;
    END IF;

    EXECUTE format($q$
        SELECT count(*) FROM %I.tcg_products WHERE code = 'PM0200' AND mark = 'MC'
    $q$, _schema) INTO v_count;
    IF v_count != 1 THEN
        RAISE EXCEPTION '20260905_020000: PM0200 の型番が MC ではありません: %', v_count;
    END IF;

    -- 4. 検証: 誤った値が残っていないこと
    EXECUTE format($q$
        SELECT count(*) FROM %I.tcg_products WHERE japanese_title LIKE 'スペシャリティボックス%%'
    $q$, _schema) INTO v_count;
    IF v_count != 0 THEN
        RAISE EXCEPTION '20260905_020000: スペシャリティボックス が残っています: %', v_count;
    END IF;

    -- 5. 検証: キーワードの本数が変わっていないこと
    EXECUTE format($q$
        SELECT count(*) FROM %I.product_search_keywords k
         JOIN %I.tcg_products p ON p.id = k.product_id
         WHERE p.code IN ('PM0056','PM0182','PM0186','PM0189','PM0200')
    $q$, _schema, _schema) INTO v_count;
    RAISE NOTICE '20260905_020000: keywords for 5 products = %', v_count;

    RAISE NOTICE '20260905_020000: fixed 4 titles and 1 mark in schema %', _schema;
END $body$;
