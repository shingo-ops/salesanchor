-- =====================================================================
-- 20260908_170000_tcg_keyword_v4_t004.sql
-- キーワード整備 v4（tenant_004）
--
-- 目的:
--   1. 「商品名 型番」で1本にまとめられた網を分解し、商品名単体を追加する
--   2. 実メッセージに現れた別名・略記を網に追加する
--   3. バルク系・AR系の壁を単語に分解し、機能する形にする
--   4. PM0097 の壁を4本に分解する（PM0098 と対称にする）
--   5. PM0137 の網を THE BEST に広げ、壁で別商品を弾く
--
-- 根拠:
--   実メッセージ2ファイル（延べ約98万行）から商品名候補37,865種を抽出。
--   3回以上出現する12,023種で照合を再現し検証した。
--   MULTI→単独 1,356件 / NONE→単独 1,224件 / 悪化5件。
--
-- 注意:
--   - 冪等。再実行しても現状を壊さない。
--   - 検索語は「無ければ足す」。既存は消さない。
--   - 除外語は対象12商品のみ入れ替える。他の商品には触れない。
--   - 検算は今回触った商品コードの範囲だけを数える。
--     テーブル全体の件数一致チェックは書かない。
-- =====================================================================

DO $mig$
DECLARE
    _schema  text := 'tenant_004';
    _n_sk    int;
    _n_ek    int;
    _missing text;
BEGIN
    -- 対象商品が全て存在するか先に確認する
    EXECUTE format($f$
        SELECT string_agg(c, ', ')
        FROM (VALUES
            ('PM0002'),('PM0003'),('PM0004'),('PM0005'),('PM0006'),
            ('PM0007'),('PM0008'),('PM0009'),('PM0010'),('PM0011'),
            ('PM0047'),('PM0059'),('PM0072'),('PM0082'),('PM0085'),
            ('PM0094'),('PM0097'),('PM0103'),('PM0104'),('PM0118'),
            ('PM0127'),('PM0134'),('PM0137'),('PM0141'),('PM0143'),
            ('PM0153'),('PM0157'),('PM0160'),('PM0172'),('PM0179'),
            ('PM0180'),('PM0181'),('PM0196'),('PM0207'),('PM0211'),
            ('PM0222'),('PM0223'),('PM0224'),('PM0256'),('PM0257'),
            ('PM0266'),('PM0268')
        ) AS t(c)
        WHERE NOT EXISTS (SELECT 1 FROM %I.tcg_products p WHERE p.code = t.c)
    $f$, _schema) INTO _missing;

    IF _missing IS NOT NULL THEN
        RAISE EXCEPTION '20260908_170000: 対象商品が見つかりません: %', _missing;
    END IF;

    -- -----------------------------------------------------------------
    -- 1) 検索語（網）を追加する。無ければ足す。既存は消さない。
    -- -----------------------------------------------------------------
    EXECUTE format($f$
        INSERT INTO %I.product_search_keywords (product_id, keyword, position)
        SELECT p.id,
               v.kw,
               COALESCE((SELECT MAX(k2.position)
                         FROM %I.product_search_keywords k2
                         WHERE k2.product_id = p.id), 0)
                 + (ROW_NUMBER() OVER (PARTITION BY p.id ORDER BY v.kw)) * 10
        FROM (VALUES
            ('PM0072','25thプロモパック'),
            ('PM0072','25th アニバーサリー プロモパック'),
            ('PM0082','ROMANCE DAWN'),
            ('PM0085','頂上決戦'),
            ('PM0094','強大な敵'),
            ('PM0103','謀略の王国'),
            ('PM0118','新時代の主役'),
            ('PM0127','双璧の覇者'),
            ('PM0134','500年後の未来'),
            ('PM0137','THE BEST'),
            ('PM0137','ワンピース THE BEST'),
            ('PM0141','新たなる皇帝'),
            ('PM0143','二つの伝説'),
            ('PM0153','Anime25th collection'),
            ('PM0157','神速の拳'),
            ('PM0160','王族の血統'),
            ('PM0172','THE BEST vol.2'),
            ('PM0172','CARD THE BEST vol.2'),
            ('PM0179','ONE PIECE DAY25'),
            ('PM0180','師弟の絆'),
            ('PM0181','受け継がれる意思'),
            ('PM0196','蒼海の七傑'),
            ('PM0207','神の島の冒険'),
            ('PM0211','俺だけレベルアップ'),
            ('PM0222','決戦の刻'),
            ('PM0223','遊戯王 HEROES'),
            ('PM0223','デュエルモンスターズ LIMIT OVER HEROES'),
            ('PM0224','遊戯王 RIVALS'),
            ('PM0224','デュエルモンスターズ LIMIT OVER RIVALS'),
            ('PM0256','QUARTER CENTURY CHRONICLE side UNITY'),
            ('PM0257','QUARTER CENTURY CHRONICLE side PRIDE'),
            ('PM0266','世界最強の戦士'),
            ('PM0268','四皇トレジャーパック'),
            ('PM0268','4周年トレジャーパック')
        ) AS v(code, kw)
        JOIN %I.tcg_products p ON p.code = v.code
        WHERE NOT EXISTS (
            SELECT 1 FROM %I.product_search_keywords k
            WHERE k.product_id = p.id AND k.keyword = v.kw
        )
    $f$, _schema, _schema, _schema, _schema);

    GET DIAGNOSTICS _n_sk = ROW_COUNT;
    RAISE NOTICE '20260908_170000: 検索語を % 本追加しました（既存は据え置き）', _n_sk;

    -- -----------------------------------------------------------------
    -- 2) 除外語（壁）を入れ替える。対象12商品のみ。
    --    単語に分解した形にするため、いったん空にしてから入れ直す。
    -- -----------------------------------------------------------------
    EXECUTE format($f$
        DELETE FROM %I.product_exclude_keywords k
        USING %I.tcg_products p
        WHERE k.product_id = p.id
          AND p.code IN ('PM0002','PM0003','PM0004','PM0005','PM0006',
                         'PM0007','PM0008','PM0009','PM0010','PM0011',
                         'PM0097','PM0137')
    $f$, _schema, _schema);

    EXECUTE format($f$
        INSERT INTO %I.product_exclude_keywords (product_id, keyword, position)
        SELECT p.id,
               v.kw,
               (ROW_NUMBER() OVER (PARTITION BY p.id ORDER BY v.ord)) * 10
        FROM (VALUES
            ('PM0002','RRR',1),('PM0002','SR',2),('PM0002','SAR',3),
            ('PM0002','CHR',4),('PM0002','Sバルク',5),

            ('PM0003','SR',1),('PM0003','SAR',2),('PM0003','CHR',3),
            ('PM0003','Sバルク',4),

            ('PM0004','RR',1),('PM0004','RRR',2),('PM0004','SR',3),
            ('PM0004','SAR',4),('PM0004','CHR',5),

            ('PM0005','RR',1),('PM0005','RRR',2),('PM0005','SAR',3),
            ('PM0005','CHR',4),('PM0005','Sバルク',5),

            ('PM0006','RR',1),('PM0006','RRR',2),('PM0006','SR',3),
            ('PM0006','CHR',4),('PM0006','Sバルク',5),

            ('PM0007','ダブりあり',1),('PM0007','被りあり',2),('PM0007','2枚',3),

            ('PM0008','ダブりなし',1),('PM0008','被りなし',2),('PM0008','2枚',3),

            ('PM0009','ダブりなし',1),('PM0009','ダブりあり',2),
            ('PM0009','被りなし',3),('PM0009','被りあり',4),

            ('PM0010','ダブりあり',1),('PM0010','被りあり',2),('PM0010','CHR',3),

            ('PM0011','ダブりなし',1),('PM0011','被りなし',2),('PM0011','CHR',3),

            ('PM0097','&クレイバースト',1),('PM0097','ポケモンセンター',2),
            ('PM0097','ポケセン',3),('PM0097','ジムセット',4),

            ('PM0137','OF XY',1),('PM0137','ストレージ',2),('PM0137','vol.2',3),
            ('PM0137','PRB-02',4),('PM0137','PRB02',5)
        ) AS v(code, kw, ord)
        JOIN %I.tcg_products p ON p.code = v.code
    $f$, _schema, _schema);

    -- -----------------------------------------------------------------
    -- 3) 除外語を追加する（既存を残したまま足す）
    -- -----------------------------------------------------------------
    EXECUTE format($f$
        INSERT INTO %I.product_exclude_keywords (product_id, keyword, position)
        SELECT p.id,
               v.kw,
               COALESCE((SELECT MAX(k2.position)
                         FROM %I.product_exclude_keywords k2
                         WHERE k2.product_id = p.id), 0)
                 + (ROW_NUMBER() OVER (PARTITION BY p.id ORDER BY v.kw)) * 10
        FROM (VALUES
            ('PM0047','シールド'),
            ('PM0059','覇者'),
            ('PM0104','収集啦'),
            ('PM0104','礼盒'),
            ('PM0127','ファイター')
        ) AS v(code, kw)
        JOIN %I.tcg_products p ON p.code = v.code
        WHERE NOT EXISTS (
            SELECT 1 FROM %I.product_exclude_keywords k
            WHERE k.product_id = p.id AND k.keyword = v.kw
        )
    $f$, _schema, _schema, _schema, _schema);

    -- -----------------------------------------------------------------
    -- 4) 検算（今回触った商品の範囲だけを数える）
    -- -----------------------------------------------------------------
    EXECUTE format($f$
        SELECT count(*) FROM %I.product_search_keywords k
        JOIN %I.tcg_products p ON p.id = k.product_id
        WHERE p.code IN ('PM0072','PM0082','PM0085','PM0094','PM0103',
                         'PM0118','PM0127','PM0134','PM0137','PM0141',
                         'PM0143','PM0153','PM0157','PM0160','PM0172',
                         'PM0179','PM0180','PM0181','PM0196','PM0207',
                         'PM0211','PM0222','PM0223','PM0224','PM0256',
                         'PM0257','PM0266','PM0268')
    $f$, _schema, _schema) INTO _n_sk;

    EXECUTE format($f$
        SELECT count(*) FROM %I.product_exclude_keywords k
        JOIN %I.tcg_products p ON p.id = k.product_id
        WHERE p.code IN ('PM0002','PM0003','PM0004','PM0005','PM0006',
                         'PM0007','PM0008','PM0009','PM0010','PM0011',
                         'PM0047','PM0059','PM0097','PM0104','PM0127',
                         'PM0137')
    $f$, _schema, _schema) INTO _n_ek;

    -- 期待値（初回適用時）:
    --   対象28商品の検索語 = 既存76本 + 追加34本 = 110本
    --   対象16商品の除外語 = 入替50本 + 追加5本 + PM0047/PM0104の既存8本 = 63本
    -- 2回目以降は同じ値になる（冪等）。
    RAISE NOTICE '20260908_170000: 検算 — 対象商品の検索語 % 本 / 除外語 % 本', _n_sk, _n_ek;
    RAISE NOTICE '20260908_170000: 完了';
END
$mig$;
