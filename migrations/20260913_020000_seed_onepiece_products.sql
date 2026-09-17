-- ============================================================================
-- Migration 20260913_020000: ONE PIECE カードゲーム商品マスタ 168 件を中央カタログへ投入
--
-- ADR-090: public 中央カタログ（tenant_id=NULL）。在庫数は 0。
-- Dragon Ball v2 seed (20260913_010000) と同一形式。
-- 冪等: ON CONFLICT(product_code) WHERE product_code IS NOT NULL DO UPDATE。
-- ============================================================================

DO $$
BEGIN
    IF to_regclass('public.tcg_type_master') IS NULL THEN
        RAISE NOTICE 'public.tcg_type_master not present -- skipping';
        RETURN;
    END IF;
    INSERT INTO public.tcg_type_master (id, code, name_ja, name_en, sort_order) VALUES
        ((SELECT COALESCE(MAX(id),0)+1 FROM public.tcg_type_master),
         'one_piece', 'ワンピースカードゲーム', 'ONE PIECE CARD GAME', 300)
    ON CONFLICT (code) DO NOTHING;
END $$;

DO $$
DECLARE
    v_work_id UUID;
    v_schema  TEXT;
BEGIN
    IF to_regclass('public.products') IS NULL
       OR (
           SELECT COUNT(*) FROM information_schema.columns
           WHERE table_schema = 'public' AND table_name = 'products'
             AND column_name IN ('category', 'tcg_type', 'mark', 'product_kind',
                                 'release_date', 'set_type', 'search_keywords',
                                 'exclude_keywords', 'boxes_per_case', 'packs_per_box')
       ) < 10 THEN
        RAISE NOTICE 'public.products required columns not present — skipping seed v2';
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
            INTO v_work_id USING 'IP002';
    END IF;

    -- work_id NOT NULL 制約が存在するのにシリーズが見つからない場合はスキップ
    IF v_work_id IS NULL AND EXISTS (
        SELECT 1 FROM pg_attribute
        WHERE attrelid = 'public.products'::regclass
          AND attname = 'work_id' AND attnotnull
    ) THEN
        RAISE NOTICE 'work_id NOT NULL active but ONE PIECE series not found — skipping seed';
        RETURN;
    END IF;

    INSERT INTO public.products
        (product_code, name, name_en, category, tcg_type, mark, product_kind,
         set_type, status, unit_price, release_date, stock_quantity,
         packs_per_box, boxes_per_case, search_keywords, exclude_keywords, work_id)
    VALUES
    -- ====================================================================
    -- ブースターパック (OP-01 to OP-17)
    -- ====================================================================
    ('OP-OP01', 'ブースターパック ROMANCE DAWN', 'ROMANCE DAWN',
     'ONE PIECE', 'one_piece', 'OP-01', 'TCG', 'booster', 'active', 220, DATE '2022-07-22', 0, 24, 12,
     'OP-01,OP01,ROMANCE DAWN,ロマンスドーン',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,スタートデッキ,デッキ', v_work_id),

    ('OP-OP02', 'ブースターパック 頂上決戦', 'PARAMOUNT WAR',
     'ONE PIECE', 'one_piece', 'OP-02', 'TCG', 'booster', 'active', 220, DATE '2022-11-04', 0, 24, 12,
     'OP-02,OP02,頂上決戦,PARAMOUNT WAR',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,スタートデッキ,デッキ', v_work_id),

    ('OP-OP03', 'ブースターパック 強大な敵', 'PILLARS OF STRENGTH',
     'ONE PIECE', 'one_piece', 'OP-03', 'TCG', 'booster', 'active', 220, DATE '2023-02-11', 0, 24, 12,
     'OP-03,OP03,強大な敵,PILLARS OF STRENGTH',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,スタートデッキ,デッキ', v_work_id),

    ('OP-OP04', 'ブースターパック 謀略の王国', 'KINGDOMS OF INTRIGUE',
     'ONE PIECE', 'one_piece', 'OP-04', 'TCG', 'booster', 'active', 220, DATE '2023-05-27', 0, 24, 12,
     'OP-04,OP04,謀略の王国,KINGDOMS OF INTRIGUE',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,スタートデッキ,デッキ', v_work_id),

    ('OP-OP05', 'ブースターパック 新時代の主役', 'AWAKENING OF THE NEW ERA',
     'ONE PIECE', 'one_piece', 'OP-05', 'TCG', 'booster', 'active', 220, DATE '2023-08-26', 0, 24, 12,
     'OP-05,OP05,新時代の主役,AWAKENING OF THE NEW ERA',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,スタートデッキ,デッキ', v_work_id),

    ('OP-OP06', 'ブースターパック 双璧の覇者', 'WINGS OF THE CAPTAIN',
     'ONE PIECE', 'one_piece', 'OP-06', 'TCG', 'booster', 'active', 220, DATE '2023-11-25', 0, 24, 12,
     'OP-06,OP06,双璧の覇者,WINGS OF THE CAPTAIN',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,スタートデッキ,デッキ', v_work_id),

    ('OP-OP07', 'ブースターパック 500年後の未来', '500 YEARS IN THE FUTURE',
     'ONE PIECE', 'one_piece', 'OP-07', 'TCG', 'booster', 'active', 220, DATE '2024-02-24', 0, 24, 12,
     'OP-07,OP07,500年後の未来,500 YEARS IN THE FUTURE',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,スタートデッキ,デッキ', v_work_id),

    ('OP-OP08', 'ブースターパック 二つの伝説', 'TWO LEGENDS',
     'ONE PIECE', 'one_piece', 'OP-08', 'TCG', 'booster', 'active', 220, DATE '2024-05-25', 0, 24, 12,
     'OP-08,OP08,二つの伝説,TWO LEGENDS',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,スタートデッキ,デッキ', v_work_id),

    ('OP-OP09', 'ブースターパック 新皇帝', 'EMPERORS IN THE NEW WORLD',
     'ONE PIECE', 'one_piece', 'OP-09', 'TCG', 'booster', 'active', 220, DATE '2024-08-31', 0, 24, 12,
     'OP-09,OP09,新皇帝,EMPERORS IN THE NEW WORLD',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,スタートデッキ,デッキ', v_work_id),

    ('OP-OP10', 'ブースターパック 王族の血統', 'ROYAL BLOOD',
     'ONE PIECE', 'one_piece', 'OP-10', 'TCG', 'booster', 'active', 220, DATE '2024-11-30', 0, 24, 12,
     'OP-10,OP10,王族の血統,ROYAL BLOOD',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,スタートデッキ,デッキ', v_work_id),

    ('OP-OP11', 'ブースターパック 疾風迅雷', 'A FIST OF DIVINE SPEED',
     'ONE PIECE', 'one_piece', 'OP-11', 'TCG', 'booster', 'active', 220, DATE '2025-03-01', 0, 24, 12,
     'OP-11,OP11,疾風迅雷,神速の拳,A FIST OF DIVINE SPEED',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,スタートデッキ,デッキ', v_work_id),

    ('OP-OP12', 'ブースターパック 師弟の絆', 'LEGACY OF THE MASTER',
     'ONE PIECE', 'one_piece', 'OP-12', 'TCG', 'booster', 'active', 220, DATE '2025-05-31', 0, 24, 12,
     'OP-12,OP12,師弟の絆,LEGACY OF THE MASTER',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,スタートデッキ,デッキ', v_work_id),

    ('OP-OP13', 'ブースターパック 受け継がれる意志', 'CARRYING ON HIS WILL',
     'ONE PIECE', 'one_piece', 'OP-13', 'TCG', 'booster', 'active', 220, DATE '2025-08-23', 0, 24, 12,
     'OP-13,OP13,受け継がれる意志,CARRYING ON HIS WILL',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,スタートデッキ,デッキ', v_work_id),

    ('OP-OP14', 'ブースターパック 蒼海の七傑', 'THE AZURE SEA''S SEVEN',
     'ONE PIECE', 'one_piece', 'OP-14', 'TCG', 'booster', 'active', 220, DATE '2025-11-22', 0, 24, 12,
     'OP-14,OP14,蒼海の七傑,THE AZURE SEA',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,スタートデッキ,デッキ', v_work_id),

    ('OP-OP15', 'ブースターパック 神の島の冒険', 'ADVENTURE ON KAMI''S ISLAND',
     'ONE PIECE', 'one_piece', 'OP-15', 'TCG', 'booster', 'active', 220, DATE '2026-02-28', 0, 24, 12,
     'OP-15,OP15,神の島の冒険,ADVENTURE ON KAMI',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,スタートデッキ,デッキ', v_work_id),

    ('OP-OP16', 'ブースターパック 決戦の刻', 'THE TIME OF BATTLE',
     'ONE PIECE', 'one_piece', 'OP-16', 'TCG', 'booster', 'active', 220, DATE '2026-05-30', 0, 24, 12,
     'OP-16,OP16,決戦の刻,THE TIME OF BATTLE',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,スタートデッキ,デッキ', v_work_id),

    ('OP-OP17', 'ブースターパック 世界最強の戦士', 'THE WORLD''S STRONGEST WARRIORS',
     'ONE PIECE', 'one_piece', 'OP-17', 'TCG', 'booster', 'active', 220, DATE '2026-08-22', 0, 24, 12,
     'OP-17,OP17,世界最強の戦士,THE WORLD''S STRONGEST',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,スタートデッキ,デッキ', v_work_id),

    -- ====================================================================
    -- エクストラブースター (EB-01 to EB-05)
    -- ====================================================================
    ('OP-EB01', 'エクストラブースター メモリアルコレクション', 'MEMORIAL COLLECTION',
     'ONE PIECE', 'one_piece', 'EB-01', 'TCG', 'booster', 'active', 220, DATE '2024-01-27', 0, 24, 12,
     'EB-01,EB01,メモリアルコレクション,MEMORIAL COLLECTION,エクストラブースター',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,スタートデッキ,デッキ', v_work_id),

    ('OP-EB02', 'エクストラブースター アニメ25thコレクション', 'Anime 25th Collection',
     'ONE PIECE', 'one_piece', 'EB-02', 'TCG', 'booster', 'active', 220, DATE '2025-01-25', 0, 24, 12,
     'EB-02,EB02,アニメ25thコレクション,Anime 25th Collection,25th,エクストラブースター',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,スタートデッキ,デッキ,25周年エディション', v_work_id),

    ('OP-EB03', 'エクストラブースター ONE PIECE Heroines Edition', 'ONE PIECE HEROINES EDITION',
     'ONE PIECE', 'one_piece', 'EB-03', 'TCG', 'booster', 'active', 220, DATE '2025-10-25', 0, 24, 12,
     'EB-03,EB03,Heroines Edition,ヒロインズエディション,ヒロインズ,エクストラブースター',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,スタートデッキ,デッキ,vol.2', v_work_id),

    ('OP-EB04', 'エクストラブースター EGGHEAD CRISIS', 'EGGHEAD CRISIS',
     'ONE PIECE', 'one_piece', 'EB-04', 'TCG', 'booster', 'active', 220, DATE '2026-01-31', 0, 24, 12,
     'EB-04,EB04,EGGHEAD CRISIS,エッグヘッドクライシス,エッグヘッド,エクストラブースター',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,スタートデッキ,デッキ', v_work_id),

    ('OP-EB05', 'エクストラブースター ONE PIECE Heroines Edition vol.2', 'ONE PIECE HEROINES EDITION vol.2',
     'ONE PIECE', 'one_piece', 'EB-05', 'TCG', 'booster', 'active', 220, NULL, 0, 24, 12,
     'EB-05,EB05,Heroines Edition vol.2,ヒロインズエディション vol.2,ヒロインズ vol.2,エクストラブースター',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,スタートデッキ,デッキ', v_work_id),

    -- ====================================================================
    -- プレミアムブースター (PRB-01 to PRB-02)
    -- ====================================================================
    ('OP-PRB01', 'プレミアムブースター ONE PIECE CARD THE BEST', 'ONE PIECE CARD THE BEST',
     'ONE PIECE', 'one_piece', 'PRB-01', 'TCG', 'booster', 'active', 220, DATE '2024-07-27', 0, 24, 12,
     'PRB-01,PRB01,THE BEST,ザベスト,プレミアムブースター,CARD THE BEST',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,スタートデッキ,デッキ,vol.2', v_work_id),

    ('OP-PRB02', 'プレミアムブースター THE BEST vol.2', 'ONE PIECE CARD THE BEST vol.2',
     'ONE PIECE', 'one_piece', 'PRB-02', 'TCG', 'booster', 'active', 220, DATE '2025-07-26', 0, 24, 12,
     'PRB-02,PRB02,THE BEST vol.2,ザベスト vol.2,プレミアムブースター',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,スタートデッキ,デッキ', v_work_id),

    -- ====================================================================
    -- スタートデッキ (ST-01 to ST-20)
    -- ====================================================================
    ('OP-ST01', 'スタートデッキ 麦わらの一味', 'Straw Hat Crew',
     'ONE PIECE', 'one_piece', 'ST-01', 'TCG', 'deck', 'active', 550, DATE '2022-07-08', 0, NULL, NULL,
     'ST-01,ST01,麦わらの一味,Straw Hat Crew,デッキ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン', v_work_id),

    ('OP-ST02', 'スタートデッキ 最悪の世代', 'Worst Generation',
     'ONE PIECE', 'one_piece', 'ST-02', 'TCG', 'deck', 'active', 550, DATE '2022-07-08', 0, NULL, NULL,
     'ST-02,ST02,最悪の世代,Worst Generation,デッキ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン', v_work_id),

    ('OP-ST03', 'スタートデッキ 王下七武海', 'The Seven Warlords of the Sea',
     'ONE PIECE', 'one_piece', 'ST-03', 'TCG', 'deck', 'active', 550, DATE '2022-07-08', 0, NULL, NULL,
     'ST-03,ST03,王下七武海,Seven Warlords,デッキ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン', v_work_id),

    ('OP-ST04', 'スタートデッキ 百獣海賊団', 'Animal Kingdom Pirates',
     'ONE PIECE', 'one_piece', 'ST-04', 'TCG', 'deck', 'active', 550, DATE '2022-07-08', 0, NULL, NULL,
     'ST-04,ST04,百獣海賊団,Animal Kingdom Pirates,デッキ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン', v_work_id),

    ('OP-ST05', 'スタートデッキ ONE PIECE FILM edition', 'ONE PIECE FILM edition',
     'ONE PIECE', 'one_piece', 'ST-05', 'TCG', 'deck', 'active', 550, DATE '2022-08-06', 0, NULL, NULL,
     'ST-05,ST05,FILM edition,フィルムエディション,ONE PIECE FILM,デッキ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン', v_work_id),

    ('OP-ST06', 'スタートデッキ 海軍', 'Absolute Justice',
     'ONE PIECE', 'one_piece', 'ST-06', 'TCG', 'deck', 'active', 550, DATE '2022-09-30', 0, NULL, NULL,
     'ST-06,ST06,海軍,Absolute Justice,デッキ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン', v_work_id),

    ('OP-ST07', 'スタートデッキ ビッグ・マム海賊団', 'Big Mom Pirates',
     'ONE PIECE', 'one_piece', 'ST-07', 'TCG', 'deck', 'active', 550, DATE '2023-01-21', 0, NULL, NULL,
     'ST-07,ST07,ビッグ・マム海賊団,Big Mom Pirates,ビッグマム,デッキ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン', v_work_id),

    ('OP-ST08', 'スタートデッキ Side モンキー・D・ルフィ', 'Monkey D. Luffy',
     'ONE PIECE', 'one_piece', 'ST-08', 'TCG', 'deck', 'active', 550, DATE '2023-03-25', 0, NULL, NULL,
     'ST-08,ST08,Side ルフィ,Monkey D. Luffy,モンキー・D・ルフィ,デッキ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン', v_work_id),

    ('OP-ST09', 'スタートデッキ Side ヤマト', 'Yamato',
     'ONE PIECE', 'one_piece', 'ST-09', 'TCG', 'deck', 'active', 550, DATE '2023-03-25', 0, NULL, NULL,
     'ST-09,ST09,Side ヤマト,Yamato,ヤマト,デッキ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン', v_work_id),

    ('OP-ST10', 'アルティメットデッキ 三船長 集結', 'The Three Captains',
     'ONE PIECE', 'one_piece', 'ST-10', 'TCG', 'deck', 'active', 1650, DATE '2023-07-29', 0, NULL, NULL,
     'ST-10,ST10,アルティメットデッキ,三船長,The Three Captains,アルティメット,デッキ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン', v_work_id),

    ('OP-ST11', 'スタートデッキ Side ウタ', 'Uta',
     'ONE PIECE', 'one_piece', 'ST-11', 'TCG', 'deck', 'active', 550, DATE '2023-10-07', 0, NULL, NULL,
     'ST-11,ST11,Side ウタ,Uta,ウタ,デッキ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン', v_work_id),

    ('OP-ST12', 'スタートデッキ ゾロ&サンジ', 'Zoro and Sanji',
     'ONE PIECE', 'one_piece', 'ST-12', 'TCG', 'deck', 'active', 990, DATE '2023-10-28', 0, NULL, NULL,
     'ST-12,ST12,ゾロ&サンジ,Zoro and Sanji,ゾロ,サンジ,デッキ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン', v_work_id),

    ('OP-ST13', 'アルティメットデッキ 3兄弟の絆', 'The Three Brothers',
     'ONE PIECE', 'one_piece', 'ST-13', 'TCG', 'deck', 'active', 3300, DATE '2023-12-23', 0, NULL, NULL,
     'ST-13,ST13,アルティメットデッキ,3兄弟の絆,The Three Brothers,3兄弟,アルティメット,デッキ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン', v_work_id),

    ('OP-ST14', 'スタートデッキ 3D2Y', '3D2Y',
     'ONE PIECE', 'one_piece', 'ST-14', 'TCG', 'deck', 'active', 550, DATE '2024-04-27', 0, NULL, NULL,
     'ST-14,ST14,3D2Y,デッキ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン', v_work_id),

    ('OP-ST15', 'スタートデッキ 赤 エドワード・ニューゲート', 'Red Edward.Newgate',
     'ONE PIECE', 'one_piece', 'ST-15', 'TCG', 'deck', 'active', 550, DATE '2024-07-13', 0, NULL, NULL,
     'ST-15,ST15,赤 エドワード・ニューゲート,Red Edward Newgate,ニューゲート,白ひげ,デッキ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン', v_work_id),

    ('OP-ST16', 'スタートデッキ 緑 ウタ', 'Green Uta',
     'ONE PIECE', 'one_piece', 'ST-16', 'TCG', 'deck', 'active', 550, DATE '2024-07-13', 0, NULL, NULL,
     'ST-16,ST16,緑 ウタ,Green Uta,デッキ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン', v_work_id),

    ('OP-ST17', 'スタートデッキ 青 ドンキホーテ・ドフラミンゴ', 'Blue Donquixote Doflamingo',
     'ONE PIECE', 'one_piece', 'ST-17', 'TCG', 'deck', 'active', 550, DATE '2024-07-13', 0, NULL, NULL,
     'ST-17,ST17,青 ドフラミンゴ,Blue Donquixote Doflamingo,ドフラミンゴ,デッキ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン', v_work_id),

    ('OP-ST18', 'スタートデッキ 紫 モンキー・D・ルフィ', 'Purple Monkey.D.Luffy',
     'ONE PIECE', 'one_piece', 'ST-18', 'TCG', 'deck', 'active', 550, DATE '2024-07-13', 0, NULL, NULL,
     'ST-18,ST18,紫 ルフィ,Purple Monkey D Luffy,紫ルフィ,デッキ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン', v_work_id),

    ('OP-ST19', 'スタートデッキ 黒 スモーカー', 'Black Smoker',
     'ONE PIECE', 'one_piece', 'ST-19', 'TCG', 'deck', 'active', 550, DATE '2024-07-13', 0, NULL, NULL,
     'ST-19,ST19,黒 スモーカー,Black Smoker,スモーカー,デッキ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン', v_work_id),

    ('OP-ST20', 'スタートデッキ 黄 シャーロット・カタクリ', 'Yellow Charlotte Katakuri',
     'ONE PIECE', 'one_piece', 'ST-20', 'TCG', 'deck', 'active', 550, DATE '2024-07-13', 0, NULL, NULL,
     'ST-20,ST20,黄 カタクリ,Yellow Charlotte Katakuri,カタクリ,デッキ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン', v_work_id),

    ('OP-ST21', 'スタートデッキEX ギア5', 'GEAR5',
     'ONE PIECE', 'one_piece', 'ST-21', 'TCG', 'deck', 'active', 1650, DATE '2024-12-21', 0, NULL, NULL,
     'ST-21,ST21,ギア5,GEAR5,ギアフィフス,スタートデッキEX,デッキ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン', v_work_id),

    ('OP-ST22', 'スタートデッキ エース&ニューゲート', 'Ace & Newgate',
     'ONE PIECE', 'one_piece', 'ST-22', 'TCG', 'deck', 'active', 990, DATE '2025-04-26', 0, NULL, NULL,
     'ST-22,ST22,エース&ニューゲート,Ace & Newgate,エース,ニューゲート,デッキ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン', v_work_id),

    ('OP-ST23', 'スタートデッキ 赤 シャンクス', 'Red Shanks',
     'ONE PIECE', 'one_piece', 'ST-23', 'TCG', 'deck', 'active', 550, DATE '2025-06-28', 0, NULL, NULL,
     'ST-23,ST23,赤 シャンクス,Red Shanks,シャンクス,デッキ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン', v_work_id),

    ('OP-ST24', 'スタートデッキ 緑 ジュエリー・ボニー', 'Green Jewelry Bonney',
     'ONE PIECE', 'one_piece', 'ST-24', 'TCG', 'deck', 'active', 550, DATE '2025-06-28', 0, NULL, NULL,
     'ST-24,ST24,緑 ジュエリー・ボニー,Green Jewelry Bonney,ボニー,デッキ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン', v_work_id),

    ('OP-ST25', 'スタートデッキ 青 バギー', 'Blue Buggy',
     'ONE PIECE', 'one_piece', 'ST-25', 'TCG', 'deck', 'active', 550, DATE '2025-06-28', 0, NULL, NULL,
     'ST-25,ST25,青 バギー,Blue Buggy,バギー,デッキ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン', v_work_id),

    ('OP-ST26', 'スタートデッキ 紫黒 モンキー・D・ルフィ', 'Purple/Black Monkey.D.Luffy',
     'ONE PIECE', 'one_piece', 'ST-26', 'TCG', 'deck', 'active', 550, DATE '2025-06-28', 0, NULL, NULL,
     'ST-26,ST26,紫黒 ルフィ,Purple Black Monkey D Luffy,紫黒ルフィ,デッキ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン', v_work_id),

    ('OP-ST27', 'スタートデッキ 黒 マーシャル・D・ティーチ', 'Black Marshall.D.Teach',
     'ONE PIECE', 'one_piece', 'ST-27', 'TCG', 'deck', 'active', 550, DATE '2025-06-28', 0, NULL, NULL,
     'ST-27,ST27,黒 ティーチ,Black Marshall D Teach,ティーチ,黒ひげ,デッキ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン', v_work_id),

    ('OP-ST28', 'スタートデッキ 緑黄 ヤマト', 'Green/Yellow Yamato',
     'ONE PIECE', 'one_piece', 'ST-28', 'TCG', 'deck', 'active', 550, DATE '2025-06-28', 0, NULL, NULL,
     'ST-28,ST28,緑黄 ヤマト,Green Yellow Yamato,デッキ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン', v_work_id),

    ('OP-ST29', 'スタートデッキ EGGHEAD', 'Egghead',
     'ONE PIECE', 'one_piece', 'ST-29', 'TCG', 'deck', 'active', 990, DATE '2025-12-20', 0, NULL, NULL,
     'ST-29,ST29,EGGHEAD,エッグヘッド,デッキ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン', v_work_id),

    ('OP-ST30', 'スタートデッキEX ルフィ&エース', 'Luffy & Ace',
     'ONE PIECE', 'one_piece', 'ST-30', 'TCG', 'deck', 'active', 1650, DATE '2026-04-11', 0, NULL, NULL,
     'ST-30,ST30,ルフィ&エース,Luffy & Ace,スタートデッキEX,デッキ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン', v_work_id),

    ('OP-ST31', 'スタートデッキ 赤 モンキー・D・ルフィ', 'Red Monkey.D.Luffy',
     'ONE PIECE', 'one_piece', 'ST-31', 'TCG', 'deck', 'active', 550, DATE '2026-07-11', 0, NULL, NULL,
     'ST-31,ST31,赤 モンキー・D・ルフィ,Red Monkey D Luffy,赤ルフィ,デッキ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン', v_work_id),

    ('OP-ST32', 'スタートデッキ 緑 ロロノア・ゾロ', 'Green Roronoa Zoro',
     'ONE PIECE', 'one_piece', 'ST-32', 'TCG', 'deck', 'active', 550, DATE '2026-07-11', 0, NULL, NULL,
     'ST-32,ST32,緑 ロロノア・ゾロ,Green Roronoa Zoro,緑ゾロ,デッキ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン', v_work_id),

    ('OP-ST33', 'スタートデッキ 青 クザン', 'Blue Kuzan',
     'ONE PIECE', 'one_piece', 'ST-33', 'TCG', 'deck', 'active', 550, DATE '2026-07-11', 0, NULL, NULL,
     'ST-33,ST33,青 クザン,Blue Kuzan,クザン,デッキ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン', v_work_id),

    ('OP-ST34', 'スタートデッキ 紫 シャーロット・カタクリ', 'Purple Charlotte Katakuri',
     'ONE PIECE', 'one_piece', 'ST-34', 'TCG', 'deck', 'active', 550, DATE '2026-07-11', 0, NULL, NULL,
     'ST-34,ST34,紫 カタクリ,Purple Charlotte Katakuri,紫カタクリ,デッキ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン', v_work_id),

    ('OP-ST35', 'スタートデッキ 赤黒 サボ', 'Red/Black Sabo',
     'ONE PIECE', 'one_piece', 'ST-35', 'TCG', 'deck', 'active', 550, DATE '2026-07-11', 0, NULL, NULL,
     'ST-35,ST35,赤黒 サボ,Red Black Sabo,サボ,デッキ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン', v_work_id),

    ('OP-ST36', 'スタートデッキ 黄 ユースタス・キッド', 'Yellow Eustass Captain Kid',
     'ONE PIECE', 'one_piece', 'ST-36', 'TCG', 'deck', 'active', 550, DATE '2026-07-11', 0, NULL, NULL,
     'ST-36,ST36,黄 キッド,Yellow Eustass Captain Kid,キッド,デッキ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン', v_work_id),

    -- Set Sail Deck
    ('OP-SD01', 'Set Sail Deck Set', 'Set Sail Deck Set',
     'ONE PIECE', 'one_piece', 'SD-01', 'TCG', 'deck', 'active', NULL, DATE '2026-09-18', 0, NULL, NULL,
     'SD-01,SD01,Set Sail Deck,セットセイル,デッキ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン', v_work_id),

    -- ====================================================================
    -- ダブルパックセット (DP-01 to DP-12)
    -- ====================================================================
    ('OP-DP01', 'ダブルパックセット vol.1', 'Double Pack Set Vol.1',
     'ONE PIECE', 'one_piece', 'DP-01', 'TCG', 'special', 'active', NULL, DATE '2023-09-22', 0, NULL, NULL,
     'DP-01,DP01,ダブルパックセット,Double Pack Set',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-DP02', 'ダブルパックセット vol.2', 'Double Pack Set Vol.2',
     'ONE PIECE', 'one_piece', 'DP-02', 'TCG', 'special', 'active', NULL, DATE '2023-12-08', 0, NULL, NULL,
     'DP-02,DP02,ダブルパックセット,Double Pack Set',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-DP03', 'ダブルパックセット vol.3', 'Double Pack Set Vol.3',
     'ONE PIECE', 'one_piece', 'DP-03', 'TCG', 'special', 'active', NULL, DATE '2024-03-15', 0, NULL, NULL,
     'DP-03,DP03,ダブルパックセット,Double Pack Set',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-DP04', 'ダブルパックセット vol.4', 'Double Pack Set Vol.4',
     'ONE PIECE', 'one_piece', 'DP-04', 'TCG', 'special', 'active', NULL, DATE '2024-06-28', 0, NULL, NULL,
     'DP-04,DP04,ダブルパックセット,Double Pack Set',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-DP05', 'ダブルパックセット vol.5', 'Double Pack Set Vol.5',
     'ONE PIECE', 'one_piece', 'DP-05', 'TCG', 'special', 'active', NULL, DATE '2024-09-13', 0, NULL, NULL,
     'DP-05,DP05,ダブルパックセット,Double Pack Set',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-DP06', 'ダブルパックセット vol.6', 'Double Pack Set Vol.6',
     'ONE PIECE', 'one_piece', 'DP-06', 'TCG', 'special', 'active', NULL, DATE '2024-12-13', 0, NULL, NULL,
     'DP-06,DP06,ダブルパックセット,Double Pack Set',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-DP07', 'ダブルパックセット vol.7', 'Double Pack Set Vol.7',
     'ONE PIECE', 'one_piece', 'DP-07', 'TCG', 'special', 'active', NULL, DATE '2025-06-06', 0, NULL, NULL,
     'DP-07,DP07,ダブルパックセット,Double Pack Set',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-DP08', 'ダブルパックセット vol.8', 'Double Pack Set Vol.8',
     'ONE PIECE', 'one_piece', 'DP-08', 'TCG', 'special', 'active', NULL, DATE '2025-08-22', 0, NULL, NULL,
     'DP-08,DP08,ダブルパックセット,Double Pack Set',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-DP09', 'ダブルパックセット vol.9', 'Double Pack Set Vol.9',
     'ONE PIECE', 'one_piece', 'DP-09', 'TCG', 'special', 'active', NULL, DATE '2026-01-16', 0, NULL, NULL,
     'DP-09,DP09,ダブルパックセット,Double Pack Set',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-DP10', 'ダブルパックセット vol.10', 'Double Pack Set Vol.10',
     'ONE PIECE', 'one_piece', 'DP-10', 'TCG', 'special', 'active', NULL, DATE '2026-04-03', 0, NULL, NULL,
     'DP-10,DP10,ダブルパックセット,Double Pack Set',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-DP11', 'ダブルパックセット vol.11', 'Double Pack Set Vol.11',
     'ONE PIECE', 'one_piece', 'DP-11', 'TCG', 'special', 'active', NULL, DATE '2026-06-12', 0, NULL, NULL,
     'DP-11,DP11,ダブルパックセット,Double Pack Set',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-DP12', 'ダブルパックセット vol.12', 'Double Pack Set Vol.12',
     'ONE PIECE', 'one_piece', 'DP-12', 'TCG', 'special', 'active', NULL, DATE '2026-08-28', 0, NULL, NULL,
     'DP-12,DP12,ダブルパックセット,Double Pack Set',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    -- ====================================================================
    -- スペシャルセット各種 (20件)
    -- ====================================================================
    ('OP-DF01', 'デビルフルーツコレクション vol.1', 'Devil Fruits Collection Vol.1',
     'ONE PIECE', 'one_piece', 'DF-01', 'TCG', 'special', 'active', NULL, DATE '2023-11-03', 0, NULL, NULL,
     'DF-01,DF01,デビルフルーツコレクション,Devil Fruits Collection',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-DF02', 'デビルフルーツコレクション vol.2', 'Devil Fruits Collection Vol.2',
     'ONE PIECE', 'one_piece', 'DF-02', 'TCG', 'special', 'active', NULL, DATE '2024-11-08', 0, NULL, NULL,
     'DF-02,DF02,デビルフルーツコレクション,Devil Fruits Collection',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-DF03', 'デビルフルーツコレクション vol.3', 'Devil Fruits Collection Vol.3',
     'ONE PIECE', 'one_piece', 'DF-03', 'TCG', 'special', 'active', NULL, DATE '2025-11-14', 0, NULL, NULL,
     'DF-03,DF03,デビルフルーツコレクション,Devil Fruits Collection',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-TS01', 'ティンパックセット vol.1', 'Tin Pack Set Vol.1',
     'ONE PIECE', 'one_piece', 'TS-01', 'TCG', 'special', 'active', NULL, DATE '2025-04-18', 0, NULL, NULL,
     'TS-01,TS01,ティンパックセット,Tin Pack Set',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-TS02', 'ティンパックセット vol.2', 'Tin Pack Set Vol.2',
     'ONE PIECE', 'one_piece', 'TS-02', 'TCG', 'special', 'active', NULL, DATE '2026-01-30', 0, NULL, NULL,
     'TS-02,TS02,ティンパックセット,Tin Pack Set',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-GC01', 'ギフトコレクション2023', 'GIFT COLLECTION 2023',
     'ONE PIECE', 'one_piece', 'GC-01', 'TCG', 'special', 'active', NULL, DATE '2023-10-27', 0, NULL, NULL,
     'GC-01,GC01,ギフトコレクション,GIFT COLLECTION',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-SDS01', 'スペシャルドン!!セット vol.1 ルフィ', 'Special DON!! Set Vol.1 -Luffy-',
     'ONE PIECE', 'one_piece', 'SDS-01', 'TCG', 'special', 'active', NULL, NULL, 0, NULL, NULL,
     'SDS-01,SDS01,スペシャルドン!!セット,Special DON!! Set,ルフィ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-SDS02', 'スペシャルドン!!セット vol.2 エース', 'Special DON!! Set Vol.2 -Ace-',
     'ONE PIECE', 'one_piece', 'SDS-02', 'TCG', 'special', 'active', NULL, NULL, 0, NULL, NULL,
     'SDS-02,SDS02,スペシャルドン!!セット,Special DON!! Set,エース',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-SDS03', 'スペシャルドン!!セット vol.3 サボ', 'Special DON!! Set Vol.3 -Sabo-',
     'ONE PIECE', 'one_piece', 'SDS-03', 'TCG', 'special', 'active', NULL, NULL, 0, NULL, NULL,
     'SDS-03,SDS03,スペシャルドン!!セット,Special DON!! Set,サボ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-1ANNY', 'ONE PIECEカードゲーム 1st ANNIVERSARY SET', '1st Anniversary Set',
     'ONE PIECE', 'one_piece', '1ANNY', 'TCG', 'special', 'active', NULL, NULL, 0, NULL, NULL,
     '1ANNY,1st ANNIVERSARY SET,1周年,アニバーサリー',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-2ANNY', 'ONE PIECEカードゲーム 2nd ANNIVERSARY SET', '2nd Anniversary Set',
     'ONE PIECE', 'one_piece', '2ANNY', 'TCG', 'special', 'active', NULL, NULL, 0, NULL, NULL,
     '2ANNY,2nd ANNIVERSARY SET,2周年,アニバーサリー',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-3ANNY', 'ONE PIECEカードゲーム 3rd ANNIVERSARY SET', '3rd Anniversary Set',
     'ONE PIECE', 'one_piece', '3ANNY', 'TCG', 'special', 'active', NULL, NULL, 0, NULL, NULL,
     '3ANNY,3rd ANNIVERSARY SET,3周年,アニバーサリー',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-HERO-SS', 'ONE PIECE Heroines Special Set', 'ONE PIECE Heroines Special Set',
     'ONE PIECE', 'one_piece', 'HERO-SS', 'TCG', 'special', 'active', NULL, NULL, 0, NULL, NULL,
     'HERO-SS,Heroines Special Set,ヒロインズスペシャルセット,ヒロインズ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-PCC-UTA', 'プレミアムカードコレクション -ウタ-', 'Premium Card Collection -Uta-',
     'ONE PIECE', 'one_piece', 'PCC-UTA', 'TCG', 'special', 'active', NULL, DATE '2023-10-07', 0, NULL, NULL,
     'PCC-UTA,プレミアムカードコレクション,Premium Card Collection,ウタ,Uta',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-PCC-LA1', 'プレミアムカードコレクション -Live Action Edition-', 'Premium Card Collection -Live Action Edition-',
     'ONE PIECE', 'one_piece', 'PCC-LA1', 'TCG', 'special', 'active', NULL, NULL, 0, NULL, NULL,
     'PCC-LA1,プレミアムカードコレクション,Premium Card Collection,Live Action Edition,ライブアクション',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-PCC-LA2-BW', 'プレミアムカードコレクション -Live Action Edition vol.2 バロックワークス-', 'Premium Card Collection -Live Action Edition vol.2 Baroque Works-',
     'ONE PIECE', 'one_piece', 'PCC-LA2-BW', 'TCG', 'special', 'active', NULL, NULL, 0, NULL, NULL,
     'PCC-LA2-BW,プレミアムカードコレクション,Premium Card Collection,Live Action Edition vol.2,バロックワークス,Baroque Works',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-PCC-LA2-SH', 'プレミアムカードコレクション -Live Action Edition vol.2 麦わらの一味-', 'Premium Card Collection -Live Action Edition vol.2 Straw Hat Crew-',
     'ONE PIECE', 'one_piece', 'PCC-LA2-SH', 'TCG', 'special', 'active', NULL, NULL, 0, NULL, NULL,
     'PCC-LA2-SH,プレミアムカードコレクション,Premium Card Collection,Live Action Edition vol.2,麦わらの一味,Straw Hat Crew',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-PCC-FR', 'プレミアムカードコレクション -FILM RED Edition-', 'Premium Card Collection -FILM RED Edition-',
     'ONE PIECE', 'one_piece', 'PCC-FR', 'TCG', 'special', 'active', NULL, NULL, 0, NULL, NULL,
     'PCC-FR,プレミアムカードコレクション,Premium Card Collection,FILM RED Edition,フィルムレッド',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-PCC-25', 'プレミアムカードコレクション 25周年エディション', 'Premium Card Collection -25th Edition-',
     'ONE PIECE', 'one_piece', 'PCC-25', 'TCG', 'special', 'active', NULL, NULL, 0, NULL, NULL,
     'PCC-25,プレミアムカードコレクション,Premium Card Collection,25周年,25th Edition',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-PCC-KUMA', 'プレミアムカードコレクション -熊本県スペシャル-', 'Premium Card Collection -Kumamoto Special-',
     'ONE PIECE', 'one_piece', 'PCC-KUMA', 'TCG', 'special', 'active', NULL, DATE '2026-02-22', 0, NULL, NULL,
     'PCC-KUMA,プレミアムカードコレクション,Premium Card Collection,熊本県スペシャル,Kumamoto Special',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    -- ====================================================================
    -- チャンピオンシップセット (9件)
    -- ====================================================================
    ('OP-CS22-LUFFY', 'チャンピオンシップセット2022 モンキー・D・ルフィ', 'Championship Set 2022 Monkey D. Luffy',
     'ONE PIECE', 'one_piece', 'CS22-LF', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'CS22-LF,CS22LF,チャンピオンシップセット,Championship Set',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-CS22-YAMATO', 'チャンピオンシップセット2022 ヤマト', 'Championship Set 2022 Yamato',
     'ONE PIECE', 'one_piece', 'CS22-YM', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'CS22-YM,CS22YM,チャンピオンシップセット,Championship Set',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-CS22-LAW', 'チャンピオンシップセット2022 トラファルガー・ロー', 'Championship Set 2022 Trafalgar Law',
     'ONE PIECE', 'one_piece', 'CS22-LW', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'CS22-LW,CS22LW,チャンピオンシップセット,Championship Set',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-CS22-SHANKS', 'チャンピオンシップセット2022 シャンクス', 'Championship Set 2022 Shanks',
     'ONE PIECE', 'one_piece', 'CS22-SK', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'CS22-SK,CS22SK,チャンピオンシップセット,Championship Set',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-CS22-KID', 'チャンピオンシップセット2022 ユースタス・キッド', 'Championship Set 2022 Eustass Kid',
     'ONE PIECE', 'one_piece', 'CS22-KD', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'CS22-KD,CS22KD,チャンピオンシップセット,Championship Set',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-CS22-NAMI', 'チャンピオンシップセット2022 ナミ', 'Championship Set 2022 Nami',
     'ONE PIECE', 'one_piece', 'CS22-NM', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'CS22-NM,CS22NM,チャンピオンシップセット,Championship Set',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-CS22-ACE', 'チャンピオンシップセット2022 ポートガス・D・エース', 'Championship Set 2022 Portgas D. Ace',
     'ONE PIECE', 'one_piece', 'CS22-AC', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'CS22-AC,CS22AC,チャンピオンシップセット,Championship Set',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-CS23', 'チャンピオンシップセット2023', 'Championship Set 2023',
     'ONE PIECE', 'one_piece', 'CS23', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'CS23,チャンピオンシップセット,Championship Set',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-CS23-YK', 'チャンピオンシップセット2023（旧四皇）', 'Special Set -Former Four Emperors-',
     'ONE PIECE', 'one_piece', 'CS23-YK', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'CS23-YK,CS23YK,チャンピオンシップセット,旧四皇,Former Four Emperors',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    -- ファミリー/学習デッキ (2件)
    ('OP-FAMILY', 'ファミリーデッキセット', 'Family Deck Set',
     'ONE PIECE', 'one_piece', 'FAMILY', 'TCG', 'deck', 'active', NULL, DATE '2023-04-29', 0, NULL, NULL,
     'FAMILY,ファミリーデッキセット,Family Deck Set,デッキ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン', v_work_id),

    ('OP-LEARN', 'いっしょに学ぼうデッキセット', 'Learn Together Deck Set',
     'ONE PIECE', 'one_piece', 'LEARN', 'TCG', 'deck', 'active', NULL, NULL, 0, NULL, NULL,
     'LEARN,いっしょに学ぼうデッキセット,Learn Together Deck Set,デッキ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン', v_work_id),

    -- ====================================================================
    -- ベストセレクション (7件)
    -- ====================================================================
    ('OP-BS01', 'プレミアムカードコレクション -ベストセレクション vol.1-', 'Premium Card Collection -Best Selection-',
     'ONE PIECE', 'one_piece', 'BS-01', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'BS-01,BS01,プレミアムカードコレクション,Premium Card Collection,ベストセレクション,Best Selection',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-BS02', 'プレミアムカードコレクション -ベストセレクション vol.2-', 'Premium Card Collection -Best Selection Vol.2-',
     'ONE PIECE', 'one_piece', 'BS-02', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'BS-02,BS02,プレミアムカードコレクション,Premium Card Collection,ベストセレクション,Best Selection',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-BS03', 'プレミアムカードコレクション -ベストセレクション vol.3-', 'Premium Card Collection -Best Selection Vol.3-',
     'ONE PIECE', 'one_piece', 'BS-03', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'BS-03,BS03,プレミアムカードコレクション,Premium Card Collection,ベストセレクション,Best Selection',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-BS04', 'プレミアムカードコレクション -ベストセレクション vol.4-', 'Premium Card Collection -Best Selection Vol.4-',
     'ONE PIECE', 'one_piece', 'BS-04', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'BS-04,BS04,プレミアムカードコレクション,Premium Card Collection,ベストセレクション,Best Selection',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-BS05', 'プレミアムカードコレクション -ベストセレクション vol.5-', 'Premium Card Collection -Best Selection Vol.5-',
     'ONE PIECE', 'one_piece', 'BS-05', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'BS-05,BS05,プレミアムカードコレクション,Premium Card Collection,ベストセレクション,Best Selection',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-BS06', 'プレミアムカードコレクション -ベストセレクション vol.6-', 'Premium Card Collection -Best Selection Vol.6-',
     'ONE PIECE', 'one_piece', 'BS-06', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'BS-06,BS06,プレミアムカードコレクション,Premium Card Collection,ベストセレクション,Best Selection',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-BS07', 'プレミアムカードコレクション -ベストセレクション vol.7-', 'Premium Card Collection -Best Selection Vol.7-',
     'ONE PIECE', 'one_piece', 'BS-07', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'BS-07,BS07,プレミアムカードコレクション,Premium Card Collection,ベストセレクション,Best Selection',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    -- ====================================================================
    -- PCC追加 (6件)
    -- ====================================================================
    ('OP-PCC-6A1', 'プレミアムカードコレクション -6 assort vol.1-', 'Premium Card Collection -6 assort vol.1-',
     'ONE PIECE', 'one_piece', 'PCC-6A1', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'PCC-6A1,プレミアムカードコレクション,Premium Card Collection,6 assort vol.1',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-PCC-6A2', 'プレミアムカードコレクション -6 assort vol.2-', 'Premium Card Collection -6 assort vol.2-',
     'ONE PIECE', 'one_piece', 'PCC-6A2', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'PCC-6A2,プレミアムカードコレクション,Premium Card Collection,6 assort vol.2',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-PCC-LEAD', 'プレミアムカードコレクション -リーダーコレクション-', 'Premium Card Collection -Leader Collection-',
     'ONE PIECE', 'one_piece', 'PCC-LEAD', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'PCC-LEAD,プレミアムカードコレクション,Premium Card Collection,リーダーコレクション,Leader Collection',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-PCC-DAY25', 'プレミアムカードコレクション -ONE PIECE DAY''25-', 'Premium Card Collection -ONE PIECE DAY''25-',
     'ONE PIECE', 'one_piece', 'PCC-DAY25', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'PCC-DAY25,プレミアムカードコレクション,Premium Card Collection,ONE PIECE DAY',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-PCC-29', 'プレミアムカードコレクション -29thアニバーサリー-', 'Premium Card Collection -29th Anniversary Edition-',
     'ONE PIECE', 'one_piece', 'PCC-29', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'PCC-29,プレミアムカードコレクション,Premium Card Collection,29thアニバーサリー,29th Anniversary',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-PCC-ACE', 'プレミアムカードコレクション -Ace & Sabo & Luffy-', 'Premium Card Collection -Ace & Sabo & Luffy-',
     'ONE PIECE', 'one_piece', 'PCC-ACE', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'PCC-ACE,プレミアムカードコレクション,Premium Card Collection,Ace & Sabo & Luffy,エース,サボ,ルフィ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    -- ====================================================================
    -- プロモーションパック (11件)
    -- ====================================================================
    ('OP-PP2201', 'プロモーションパック 2022 Vol.1', 'Promotion Pack 2022 Vol.1',
     'ONE PIECE', 'one_piece', 'PP22-01', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'PP22-01,PP2201,プロモーションパック,Promotion Pack',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-PP2202', 'プロモーションパック 2022 Vol.2', 'Promotion Pack 2022 Vol.2',
     'ONE PIECE', 'one_piece', 'PP22-02', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'PP22-02,PP2202,プロモーションパック,Promotion Pack',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-PP03', 'プロモーションパック Vol.3', 'Promotion Pack Vol.3',
     'ONE PIECE', 'one_piece', 'PP-03', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'PP-03,PP03,プロモーションパック,Promotion Pack',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-PP04', 'プロモーションパック Vol.4', 'Promotion Pack Vol.4',
     'ONE PIECE', 'one_piece', 'PP-04', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'PP-04,PP04,プロモーションパック,Promotion Pack',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-PP05', 'プロモーションパック Vol.5', 'Promotion Pack Vol.5',
     'ONE PIECE', 'one_piece', 'PP-05', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'PP-05,PP05,プロモーションパック,Promotion Pack',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-PP06', 'プロモーションパック Vol.6', 'Promotion Pack Vol.6',
     'ONE PIECE', 'one_piece', 'PP-06', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'PP-06,PP06,プロモーションパック,Promotion Pack',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-PP07', 'プロモーションパック Vol.7', 'Promotion Pack Vol.7',
     'ONE PIECE', 'one_piece', 'PP-07', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'PP-07,PP07,プロモーションパック,Promotion Pack',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-PP08', 'プロモーションパック Vol.8', 'Promotion Pack Vol.8',
     'ONE PIECE', 'one_piece', 'PP-08', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'PP-08,PP08,プロモーションパック,Promotion Pack',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-PP09', 'プロモーションパック Vol.9', 'Promotion Pack Vol.9',
     'ONE PIECE', 'one_piece', 'PP-09', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'PP-09,PP09,プロモーションパック,Promotion Pack',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-PPEX02', 'プロモーションパック EX Vol.2', 'Promotion Pack EX Vol.2',
     'ONE PIECE', 'one_piece', 'PPEX-02', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'PPEX-02,PPEX02,プロモーションパック,Promotion Pack EX',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-PPEX04', 'プロモーションパック EX Vol.4', 'Promotion Pack EX Vol.4',
     'ONE PIECE', 'one_piece', 'PPEX-04', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'PPEX-04,PPEX04,プロモーションパック,Promotion Pack EX',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    -- ====================================================================
    -- スタンダードバトルパック (17件: SBP-01 to SBP-17)
    -- ====================================================================
    ('OP-SBP01', 'スタンダードバトルパック Vol.1', 'Standard Battle Pack Vol.1',
     'ONE PIECE', 'one_piece', 'SBP-01', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'SBP-01,SBP01,スタンダードバトルパック,Standard Battle Pack',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-SBP02', 'スタンダードバトルパック Vol.2', 'Standard Battle Pack Vol.2',
     'ONE PIECE', 'one_piece', 'SBP-02', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'SBP-02,SBP02,スタンダードバトルパック,Standard Battle Pack',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-SBP03', 'スタンダードバトルパック Vol.3', 'Standard Battle Pack Vol.3',
     'ONE PIECE', 'one_piece', 'SBP-03', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'SBP-03,SBP03,スタンダードバトルパック,Standard Battle Pack',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-SBP04', 'スタンダードバトルパック Vol.4', 'Standard Battle Pack Vol.4',
     'ONE PIECE', 'one_piece', 'SBP-04', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'SBP-04,SBP04,スタンダードバトルパック,Standard Battle Pack',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-SBP05', 'スタンダードバトルパック Vol.5', 'Standard Battle Pack Vol.5',
     'ONE PIECE', 'one_piece', 'SBP-05', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'SBP-05,SBP05,スタンダードバトルパック,Standard Battle Pack',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-SBP06', 'スタンダードバトルパック Vol.6', 'Standard Battle Pack Vol.6',
     'ONE PIECE', 'one_piece', 'SBP-06', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'SBP-06,SBP06,スタンダードバトルパック,Standard Battle Pack',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-SBP07', 'スタンダードバトルパック Vol.7', 'Standard Battle Pack Vol.7',
     'ONE PIECE', 'one_piece', 'SBP-07', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'SBP-07,SBP07,スタンダードバトルパック,Standard Battle Pack',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-SBP08', 'スタンダードバトルパック Vol.8', 'Standard Battle Pack Vol.8',
     'ONE PIECE', 'one_piece', 'SBP-08', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'SBP-08,SBP08,スタンダードバトルパック,Standard Battle Pack',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-SBP09', 'スタンダードバトルパック Vol.9', 'Standard Battle Pack Vol.9',
     'ONE PIECE', 'one_piece', 'SBP-09', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'SBP-09,SBP09,スタンダードバトルパック,Standard Battle Pack',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-SBP10', 'スタンダードバトルパック Vol.10', 'Standard Battle Pack Vol.10',
     'ONE PIECE', 'one_piece', 'SBP-10', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'SBP-10,SBP10,スタンダードバトルパック,Standard Battle Pack',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-SBP11', 'スタンダードバトルパック Vol.11', 'Standard Battle Pack Vol.11',
     'ONE PIECE', 'one_piece', 'SBP-11', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'SBP-11,SBP11,スタンダードバトルパック,Standard Battle Pack',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-SBP12', 'スタンダードバトルパック Vol.12', 'Standard Battle Pack Vol.12',
     'ONE PIECE', 'one_piece', 'SBP-12', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'SBP-12,SBP12,スタンダードバトルパック,Standard Battle Pack',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-SBP13', 'スタンダードバトルパック Vol.13', 'Standard Battle Pack Vol.13',
     'ONE PIECE', 'one_piece', 'SBP-13', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'SBP-13,SBP13,スタンダードバトルパック,Standard Battle Pack',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-SBP14', 'スタンダードバトルパック Vol.14', 'Standard Battle Pack Vol.14',
     'ONE PIECE', 'one_piece', 'SBP-14', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'SBP-14,SBP14,スタンダードバトルパック,Standard Battle Pack',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-SBP15', 'スタンダードバトルパック Vol.15', 'Standard Battle Pack Vol.15',
     'ONE PIECE', 'one_piece', 'SBP-15', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'SBP-15,SBP15,スタンダードバトルパック,Standard Battle Pack',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-SBP16', 'スタンダードバトルパック Vol.16', 'Standard Battle Pack Vol.16',
     'ONE PIECE', 'one_piece', 'SBP-16', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'SBP-16,SBP16,スタンダードバトルパック,Standard Battle Pack',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-SBP17', 'スタンダードバトルパック Vol.17', 'Standard Battle Pack Vol.17',
     'ONE PIECE', 'one_piece', 'SBP-17', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'SBP-17,SBP17,スタンダードバトルパック,Standard Battle Pack',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    -- ====================================================================
    -- 雑誌付録プロモ (6件)
    -- ====================================================================
    ('OP-VJ', 'Vジャンプ付録カード', 'V Jump Appendix Card',
     'ONE PIECE', 'one_piece', 'VJ', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'VJ,Vジャンプ,V Jump,付録カード',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-WSJ', '週刊少年ジャンプ付録カード', 'Weekly Shonen Jump Appendix Card',
     'ONE PIECE', 'one_piece', 'WSJ', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'WSJ,週刊少年ジャンプ,Weekly Shonen Jump,付録カード',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-SJ', '最強ジャンプ付録カード', 'Saikyo Jump Appendix Card',
     'ONE PIECE', 'one_piece', 'SJ', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'SJ,最強ジャンプ,Saikyo Jump,付録カード',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-PCS1', 'プロモーションカードセット(1)', 'Promotion Card Set (1)',
     'ONE PIECE', 'one_piece', 'PCS-01', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'PCS-01,PCS01,プロモーションカードセット,Promotion Card Set',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-PCS2', 'プロモーションカードセット(2)', 'Promotion Card Set (2)',
     'ONE PIECE', 'one_piece', 'PCS-02', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'PCS-02,PCS02,プロモーションカードセット,Promotion Card Set',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-PCS25', 'プロモーションカードセット 2025', 'Promotion Card Set 2025',
     'ONE PIECE', 'one_piece', 'PCS-25', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'PCS-25,PCS25,プロモーションカードセット,Promotion Card Set,2025',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    -- ====================================================================
    -- 映画/コラボ (2件)
    -- ====================================================================
    ('OP-FILMRED', 'ONE PIECE FILM RED 入場者特典カード', 'ONE PIECE FILM RED Theater Bonus Card',
     'ONE PIECE', 'one_piece', 'FILMRED', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'FILMRED,FILM RED,フィルムレッド,入場者特典カード,Theater Bonus Card',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-7ELEVEN', 'セブンイレブンキャンペーン特典カード', 'Seven-Eleven Campaign Card',
     'ONE PIECE', 'one_piece', '7ELEVEN', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     '7ELEVEN,セブンイレブン,7-ELEVEN,キャンペーン特典カード,Campaign Card',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    -- ====================================================================
    -- イラストレーションボックス (9件: IB-01 to IB-08 + IB-EX)
    -- ====================================================================
    ('OP-IB01', 'イラストレーションボックス Vol.1', 'Illustration Box Vol.1',
     'ONE PIECE', 'one_piece', 'IB-01', 'TCG', 'special', 'active', NULL, NULL, 0, NULL, NULL,
     'IB-01,IB01,イラストレーションボックス,Illustration Box',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-IB02', 'イラストレーションボックス Vol.2', 'Illustration Box Vol.2',
     'ONE PIECE', 'one_piece', 'IB-02', 'TCG', 'special', 'active', NULL, NULL, 0, NULL, NULL,
     'IB-02,IB02,イラストレーションボックス,Illustration Box',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-IB03', 'イラストレーションボックス Vol.3', 'Illustration Box Vol.3',
     'ONE PIECE', 'one_piece', 'IB-03', 'TCG', 'special', 'active', NULL, NULL, 0, NULL, NULL,
     'IB-03,IB03,イラストレーションボックス,Illustration Box',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-IB04', 'イラストレーションボックス Vol.4', 'Illustration Box Vol.4',
     'ONE PIECE', 'one_piece', 'IB-04', 'TCG', 'special', 'active', NULL, NULL, 0, NULL, NULL,
     'IB-04,IB04,イラストレーションボックス,Illustration Box',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-IB05', 'イラストレーションボックス Vol.5', 'Illustration Box Vol.5',
     'ONE PIECE', 'one_piece', 'IB-05', 'TCG', 'special', 'active', NULL, NULL, 0, NULL, NULL,
     'IB-05,IB05,イラストレーションボックス,Illustration Box',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-IB06', 'イラストレーションボックス Vol.6', 'Illustration Box Vol.6',
     'ONE PIECE', 'one_piece', 'IB-06', 'TCG', 'special', 'active', NULL, NULL, 0, NULL, NULL,
     'IB-06,IB06,イラストレーションボックス,Illustration Box',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-IB07', 'イラストレーションボックス Vol.7', 'Illustration Box Vol.7',
     'ONE PIECE', 'one_piece', 'IB-07', 'TCG', 'special', 'active', NULL, NULL, 0, NULL, NULL,
     'IB-07,IB07,イラストレーションボックス,Illustration Box',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-IB08', 'イラストレーションボックス Vol.8', 'Illustration Box Vol.8',
     'ONE PIECE', 'one_piece', 'IB-08', 'TCG', 'special', 'active', NULL, NULL, 0, NULL, NULL,
     'IB-08,IB08,イラストレーションボックス,Illustration Box',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-IBEX', 'イラストレーションボックス EX', 'Illustration Box EX',
     'ONE PIECE', 'one_piece', 'IB-EX', 'TCG', 'special', 'active', NULL, NULL, 0, NULL, NULL,
     'IB-EX,IBEX,イラストレーションボックス EX,Illustration Box EX',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    -- ====================================================================
    -- その他限定 (5件) + リーダーカードフィギュア (1件)
    -- ====================================================================
    ('OP-UTA-COL', 'ウタコレクション', 'UTA Collection',
     'ONE PIECE', 'one_piece', 'UTA-COL', 'TCG', 'special', 'active', NULL, NULL, 0, NULL, NULL,
     'UTA-COL,ウタコレクション,UTA Collection,ウタ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-TREASURE', 'トレジャーブースターズセット', 'Treasure Boosters Set',
     'ONE PIECE', 'one_piece', 'TREASURE', 'TCG', 'special', 'active', NULL, NULL, 0, NULL, NULL,
     'TREASURE,トレジャーブースターズセット,Treasure Boosters Set',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-SGS', 'スペシャルグッズセット -Ace/Sabo/Luffy-', 'Special Goods Set -Ace/Sabo/Luffy-',
     'ONE PIECE', 'one_piece', 'SGS', 'TCG', 'special', 'active', NULL, NULL, 0, NULL, NULL,
     'SGS,スペシャルグッズセット,Special Goods Set,Ace,Sabo,Luffy,エース,サボ,ルフィ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-DONCARD', 'ストレージボックス×ドン!!カードセット', 'Storage Box & DON!! Card Set',
     'ONE PIECE', 'one_piece', 'DONCARD', 'TCG', 'special', 'active', NULL, NULL, 0, NULL, NULL,
     'DONCARD,ストレージボックス,ドン!!カードセット,Storage Box,DON!! Card Set',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-PCC-MERA', 'プレミアムカードコレクション -メラメラの実争奪戦Edition-', 'Premium Card Collection -Flame-Flame Fruit Coliseum Edition-',
     'ONE PIECE', 'one_piece', 'PCC-MERA', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'PCC-MERA,プレミアムカードコレクション,Premium Card Collection,メラメラの実,Flame-Flame Fruit',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id),

    ('OP-LCF', 'リーダーカードフィギュア 応募者全員サービス', 'Leader Card Figure',
     'ONE PIECE', 'one_piece', 'LCF', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'LCF,リーダーカードフィギュア,Leader Card Figure,応募者全員サービス',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ', v_work_id)

    ON CONFLICT (product_code) WHERE product_code IS NOT NULL DO UPDATE SET
        name = EXCLUDED.name,
        name_en = EXCLUDED.name_en,
        category = EXCLUDED.category,
        tcg_type = EXCLUDED.tcg_type,
        mark = EXCLUDED.mark,
        product_kind = EXCLUDED.product_kind,
        set_type = EXCLUDED.set_type,
        status = EXCLUDED.status,
        unit_price = EXCLUDED.unit_price,
        release_date = EXCLUDED.release_date,
        packs_per_box = EXCLUDED.packs_per_box,
        boxes_per_case = EXCLUDED.boxes_per_case,
        search_keywords = EXCLUDED.search_keywords,
        exclude_keywords = EXCLUDED.exclude_keywords,
        work_id = COALESCE(EXCLUDED.work_id, products.work_id),
        updated_at = NOW();
END $$;
