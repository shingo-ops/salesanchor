-- 商品マスタ キーワード整備 11項目（tenant_004 専用・冪等）
--
-- 目的: 除外キーワードが自分自身の商品を弾く「自己矛盾」を解消し、
--       類似商品を弾く壁が無い商品に壁を足す。あわせて死に商品1件を無効化する。
--
-- 承認: Shingo 2026-09-07
-- 根拠: CARD-PMG-SELFCONFLICT-01 / CARD-PMG-SIBLING-01 / CARD-PMG-FIX10-01 の実測
--       docs/handoff/tcg-product-master-growth/design.md 1章（検索語=網 / 除外語=壁）
--
-- 実測済みの問題（2026-09-07）:
--   PM0172「THE BEST vol.2」が除外語「THE BEST」で自滅し、
--   原文「PRB-02 THE BEST vol.2」等が NONE になっていた。
--   さらに原文「ONE PIECE CARD THE BEST PRB-02」が PM0137（vol.1）に誤解決していた。
--
-- 設計判断:
--   - 削除は5本のみ。いずれも自分自身の商品名の一部を壁にしていたもの
--   - 検証は担当範囲（対象11商品）だけを数える。テーブル全体を数えない
--   - 冪等: 削除は存在しなくてもエラーにしない。追加は重複チェック付き

DO $body$
DECLARE
    _schema  TEXT := 'tenant_004';
    v_count  integer;
    r        RECORD;
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_namespace WHERE nspname = _schema
    ) THEN
        RAISE NOTICE 'migration 20260907_100000: schema % does not exist, skipping', _schema;
        RETURN;
    END IF;

    -- 0. バックアップ（既に存在する場合は作り直さない）
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables
         WHERE table_schema = _schema AND table_name = 'product_exclude_keywords_bak_20260907'
    ) THEN
        EXECUTE format($q$
            CREATE TABLE %I.product_exclude_keywords_bak_20260907 AS
            SELECT * FROM %I.product_exclude_keywords
        $q$, _schema, _schema);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables
         WHERE table_schema = _schema AND table_name = 'tcg_products_bak_20260907'
    ) THEN
        EXECUTE format($q$
            CREATE TABLE %I.tcg_products_bak_20260907 AS
            SELECT * FROM %I.tcg_products
        $q$, _schema, _schema);
    END IF;

    -- 1. 自己矛盾の除外キーワードを削除（5本）
    FOR r IN
        SELECT * FROM (VALUES
            ('PM0172','THE BEST'),
            ('PM0063','イーブイヒーローズ'),
            ('PM0072','25th Anniversary Collection'),
            ('PM0159','熱風のアリーナ'),
            ('PM0126','バトルアカデミー')
        ) AS t(code, kw)
    LOOP
        EXECUTE format($q$
            DELETE FROM %I.product_exclude_keywords
             WHERE keyword = $2
               AND product_id = (SELECT id FROM %I.tcg_products WHERE code = $1)
        $q$, _schema, _schema) USING r.code, r.kw;
    END LOOP;

    -- 2. 綴り誤りの修正（PM0073 の商品名に合わせる）
    EXECUTE format($q$
        UPDATE %I.product_exclude_keywords
           SET keyword = '25th Aniniversary Golden Box'
         WHERE keyword = '25th Aniniversary Goleden Box'
           AND product_id = (SELECT id FROM %I.tcg_products WHERE code = 'PM0071')
    $q$, _schema, _schema);

    -- 3. 壁の追加（7本・重複しない場合のみ）
    FOR r IN
        SELECT * FROM (VALUES
            ('PM0137','PRB-02',3),
            ('PM0137','PRB02',4),
            ('PM0098','ポケモンセンター',1),
            ('PM0098','ポケセン',2),
            ('PM0098','ジムセット',3),
            ('PM0047','プレシャス',1),
            ('PM0048','プレシャス',1)
        ) AS t(code, kw, pos)
    LOOP
        EXECUTE format($q$
            INSERT INTO %I.product_exclude_keywords (id, product_id, keyword, position)
            SELECT gen_random_uuid(), p.id, $2, $3
              FROM %I.tcg_products p
             WHERE p.code = $1
               AND NOT EXISTS (
                   SELECT 1 FROM %I.product_exclude_keywords e
                    WHERE e.product_id = p.id AND e.keyword = $2
               )
        $q$, _schema, _schema, _schema) USING r.code, r.kw, r.pos;
    END LOOP;

    -- 4. PM0146 の無効化（検索キーワード0件・解決実績0件のため）
    EXECUTE format($q$
        UPDATE %I.tcg_products SET is_active = FALSE WHERE code = 'PM0146'
    $q$, _schema);

    -- 5. 検証: 削除した5本が消えていること
    EXECUTE format($q$
        SELECT count(*) FROM %I.product_exclude_keywords e
          JOIN %I.tcg_products p ON p.id = e.product_id
         WHERE (p.code = 'PM0172' AND e.keyword = 'THE BEST')
            OR (p.code = 'PM0063' AND e.keyword = 'イーブイヒーローズ')
            OR (p.code = 'PM0072' AND e.keyword = '25th Anniversary Collection')
            OR (p.code = 'PM0159' AND e.keyword = '熱風のアリーナ')
            OR (p.code = 'PM0126' AND e.keyword = 'バトルアカデミー')
    $q$, _schema, _schema) INTO v_count;
    IF v_count != 0 THEN
        RAISE EXCEPTION '20260907_100000: 削除対象が残っています: %', v_count;
    END IF;

    -- 6. 検証: 追加した7本が存在すること
    EXECUTE format($q$
        SELECT count(*) FROM %I.product_exclude_keywords e
          JOIN %I.tcg_products p ON p.id = e.product_id
         WHERE (p.code = 'PM0137' AND e.keyword IN ('PRB-02','PRB02'))
            OR (p.code = 'PM0098' AND e.keyword IN ('ポケモンセンター','ポケセン','ジムセット'))
            OR (p.code IN ('PM0047','PM0048') AND e.keyword = 'プレシャス')
    $q$, _schema, _schema) INTO v_count;
    IF v_count != 7 THEN
        RAISE EXCEPTION '20260907_100000: 追加が7本ではありません: %', v_count;
    END IF;

    -- 7. 検証: 綴り修正が反映されていること
    EXECUTE format($q$
        SELECT count(*) FROM %I.product_exclude_keywords e
          JOIN %I.tcg_products p ON p.id = e.product_id
         WHERE p.code = 'PM0071' AND e.keyword = '25th Aniniversary Golden Box'
    $q$, _schema, _schema) INTO v_count;
    IF v_count != 1 THEN
        RAISE EXCEPTION '20260907_100000: PM0071 の綴り修正が1件ではありません: %', v_count;
    END IF;

    -- 8. 検証: PM0146 が無効化されていること
    EXECUTE format($q$
        SELECT count(*) FROM %I.tcg_products WHERE code = 'PM0146' AND is_active = FALSE
    $q$, _schema) INTO v_count;
    IF v_count != 1 THEN
        RAISE EXCEPTION '20260907_100000: PM0146 の無効化が反映されていません: %', v_count;
    END IF;

    RAISE NOTICE '20260907_100000: 完了（削除5・追加7・修正1・無効化1）';
END
$body$;
