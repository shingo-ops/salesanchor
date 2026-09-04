-- ONE PIECE magazine 付録プロモ 5商品の整備（tenant_004 専用・冪等）
--
-- 目的: Vol.21 の MULTI 11行と ST21-014 の NONE 1行を解決する（計12行）
-- 承認: Shingo 2026-09-04
-- バックアップ:
--   tenant_004.tcg_products_bak_20260904              (268)
--   tenant_004.product_search_keywords_bak_20260904   (593)
--   tenant_004.product_exclude_keywords_bak_20260904  (128)
--
-- 設計判断:
--   - 既存キーワードは1本も削除しない（追加のみ）
--   - 検証は担当範囲（PM0269〜PM0271）だけを数える。テーブル全体を数えない
--   - 冪等: ON CONFLICT DO NOTHING

DO $body$
DECLARE
    _schema      TEXT := 'tenant_004';
    v_div_tcg    uuid;
    v_work_op    uuid;
    v_mfr_bandai uuid;
    v_cat_single uuid;
    v_pm0190     uuid;
    v_pm0269     uuid;
    v_pm0270     uuid;
    v_pm0271     uuid;
    v_count      integer;
BEGIN
    -- ガード: tenant_004 が存在しない場合はスキップ（CI 環境対応）
    IF NOT EXISTS (
        SELECT 1 FROM pg_namespace WHERE nspname = _schema
    ) THEN
        RAISE NOTICE 'migration 20260904_160000: schema % does not exist, skipping', _schema;
        RETURN;
    END IF;

    -- 参照マスタの取得
    EXECUTE format($q$SELECT id FROM %I.tcg_major_categories  WHERE code = 'DIV01'$q$,     _schema) INTO v_div_tcg;
    EXECUTE format($q$SELECT id FROM %I.tcg_series             WHERE code = 'IP002'$q$,     _schema) INTO v_work_op;
    EXECUTE format($q$SELECT id FROM %I.tcg_manufacturers      WHERE code = 'MK002'$q$,     _schema) INTO v_mfr_bandai;
    EXECUTE format($q$SELECT id FROM %I.tcg_product_categories WHERE code = 'PC_SINGLE'$q$, _schema) INTO v_cat_single;

    IF v_div_tcg IS NULL OR v_work_op IS NULL OR v_mfr_bandai IS NULL OR v_cat_single IS NULL THEN
        RAISE EXCEPTION '20260904_160000: 参照マスタが見つかりません';
    END IF;

    -- 1. PM0190 を ONE PIECE magazine Vol.20 として確定
    EXECUTE format($q$
        UPDATE %I.tcg_products
           SET japanese_title = 'ONE PIECE magazine Vol.20 付録プロモ',
               english_title  = 'One Piece Magazine Vol.20',
               mark           = 'ST21-014',
               release_date   = DATE '2025-10-03'
         WHERE code = 'PM0190'
    $q$, _schema);

    -- 2. PM0267 のスタブを ONE PIECE magazine Vol.21 として埋める
    EXECUTE format($q$
        UPDATE %I.tcg_products
           SET japanese_title      = 'ONE PIECE magazine Vol.21 特集ヒロインズ 021 付録プロモ',
               english_title       = 'One Piece Magazine Vol.21 Special Feature: Heroines',
               category_class      = 'Single',
               product_category_id = $1
         WHERE code = 'PM0267'
    $q$, _schema) USING v_cat_single;

    -- 3. 新規3商品（Vol.16 / Vol.17 / 別冊 FAN LETTER）
    EXECUTE format($q$
        INSERT INTO %I.tcg_products
            (code, japanese_title, english_title, mark, release_date, category_class,
             division_id, work_id, manufacturer_id, product_category_id, is_active)
        VALUES
            ('PM0269', 'ONE PIECE magazine Vol.16 付録プロモ',
             'One Piece Magazine Vol.16', 'P-028', DATE '2023-03-02', 'Single',
             $1, $2, $3, $4, TRUE),
            ('PM0270', 'ONE PIECE magazine Vol.17 付録プロモ',
             'One Piece Magazine Vol.17', 'P-046', DATE '2023-09-04', 'Single',
             $1, $2, $3, $4, TRUE),
            ('PM0271', 'ONE PIECE magazine 別冊 Focus on ONE PIECE FAN LETTER 付録プロモ',
             NULL, 'P-096', DATE '2025-06-04', 'Single',
             $1, $2, $3, $4, TRUE)
        ON CONFLICT (code) DO NOTHING
    $q$, _schema) USING v_div_tcg, v_work_op, v_mfr_bandai, v_cat_single;

    -- 商品IDの取得
    EXECUTE format($q$SELECT id FROM %I.tcg_products WHERE code = 'PM0190'$q$, _schema) INTO v_pm0190;
    EXECUTE format($q$SELECT id FROM %I.tcg_products WHERE code = 'PM0269'$q$, _schema) INTO v_pm0269;
    EXECUTE format($q$SELECT id FROM %I.tcg_products WHERE code = 'PM0270'$q$, _schema) INTO v_pm0270;
    EXECUTE format($q$SELECT id FROM %I.tcg_products WHERE code = 'PM0271'$q$, _schema) INTO v_pm0271;

    IF v_pm0190 IS NULL OR v_pm0269 IS NULL OR v_pm0270 IS NULL OR v_pm0271 IS NULL THEN
        RAISE EXCEPTION '20260904_160000: 商品IDの取得に失敗しました';
    END IF;

    -- 4. 検索キーワードの追加（既存は削除しない）
    EXECUTE format($q$
        INSERT INTO %I.product_search_keywords (product_id, keyword, position)
        VALUES
            ($1, 'ST21-014',        4),
            ($2, 'P-028',           1),
            ($2, 'magazine Vol.16', 2),
            ($3, 'P-046',           1),
            ($3, 'magazine Vol.17', 2),
            ($4, 'P-096',           1),
            ($4, 'FAN LETTER',      2)
        ON CONFLICT (product_id, keyword) DO NOTHING
    $q$, _schema) USING v_pm0190, v_pm0269, v_pm0270, v_pm0271;

    -- 5. 除外キーワードの追加（PM0190 が Vol.21 を拾わないようにする）
    EXECUTE format($q$
        INSERT INTO %I.product_exclude_keywords (product_id, keyword, position)
        SELECT $1, 'ヒロインズ', COALESCE(MAX(position), 0) + 1
          FROM %I.product_exclude_keywords
         WHERE product_id = $1
        ON CONFLICT DO NOTHING
    $q$, _schema, _schema) USING v_pm0190;

    -- 6. 検証: 担当範囲だけを数える
    EXECUTE format($q$
        SELECT count(*) FROM %I.tcg_products
         WHERE code BETWEEN 'PM0269' AND 'PM0271'
    $q$, _schema) INTO v_count;
    IF v_count != 3 THEN
        RAISE EXCEPTION '20260904_160000: 新規商品が3件ではありません: %', v_count;
    END IF;

    EXECUTE format($q$
        SELECT count(*) FROM %I.tcg_products p
         WHERE p.code BETWEEN 'PM0269' AND 'PM0271'
           AND NOT EXISTS (
               SELECT 1 FROM %I.product_search_keywords k WHERE k.product_id = p.id
           )
    $q$, _schema, _schema) INTO v_count;
    IF v_count != 0 THEN
        RAISE EXCEPTION '20260904_160000: 検索キーワードが空の新規商品があります: %', v_count;
    END IF;

    EXECUTE format($q$
        SELECT count(*) FROM %I.tcg_products
         WHERE code IN ('PM0190', 'PM0267')
           AND japanese_title LIKE 'ONE PIECE magazine%%'
    $q$, _schema) INTO v_count;
    IF v_count != 2 THEN
        RAISE EXCEPTION '20260904_160000: 既存2商品の更新が反映されていません: %', v_count;
    END IF;

    RAISE NOTICE '20260904_160000: magazine promo products ready in schema %', _schema;
END $body$;
