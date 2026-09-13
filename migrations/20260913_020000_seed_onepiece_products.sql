-- ============================================================================
-- Migration 20260913_020000: ONE PIECE カードゲーム商品マスタ 168 件を中央カタログへ投入
--
-- ADR-090: public 中央カタログ（tenant_id=NULL）。在庫数は 0。
-- Dragon Ball v2 seed (20260913_010000) と同一形式。
-- v2: search_keywords をv2精度改善（汎用語削除・型番+タイトル固有語のみ）
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

    INSERT INTO public.products
        (product_code, name, name_en, category, tcg_type, mark, product_kind,
         set_type, status, unit_price, release_date, stock_quantity,
         packs_per_box, boxes_per_case, search_keywords, exclude_keywords)
    VALUES
    -- ====================================================================
    -- ブースターパック (OP-01 to OP-17)
    -- ====================================================================
    ('OP-OP01', 'ブースターパック ROMANCE DAWN', 'ROMANCE DAWN',
     'ONE PIECE', 'one_piece', 'OP-01', 'TCG', 'booster', 'active', 220, DATE '2022-07-22', 0, 24, 12,
     'OP-01,OP01,ROMANCE DAWN,ロマンスドーン',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,スタートデッキ,デッキ'),

    ('OP-OP02', 'ブースターパック 頂上決戦', 'PARAMOUNT WAR',
     'ONE PIECE', 'one_piece', 'OP-02', 'TCG', 'booster', 'active', 220, DATE '2022-11-04', 0, 24, 12,
     'OP-02,OP02,PARAMOUNT WAR,頂上決戦',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,スタートデッキ,デッキ'),

    ('OP-OP03', 'ブースターパック 強大な敵', 'PILLARS OF STRENGTH',
     'ONE PIECE', 'one_piece', 'OP-03', 'TCG', 'booster', 'active', 220, DATE '2023-02-11', 0, 24, 12,
     'OP-03,OP03,PILLARS OF STRENGTH,強大な敵',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,スタートデッキ,デッキ'),

    ('OP-OP04', 'ブースターパック 謀略の王国', 'KINGDOMS OF INTRIGUE',
     'ONE PIECE', 'one_piece', 'OP-04', 'TCG', 'booster', 'active', 220, DATE '2023-05-27', 0, 24, 12,
     'KINGDOMS OF INTRIGUE,OP-04,OP04,謀略の王国',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,スタートデッキ,デッキ'),

    ('OP-OP05', 'ブースターパック 新時代の主役', 'AWAKENING OF THE NEW ERA',
     'ONE PIECE', 'one_piece', 'OP-05', 'TCG', 'booster', 'active', 220, DATE '2023-08-26', 0, 24, 12,
     'AWAKENING OF THE NEW ERA,OP-05,OP05,新時代の主役',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,スタートデッキ,デッキ'),

    ('OP-OP06', 'ブースターパック 双璧の覇者', 'WINGS OF THE CAPTAIN',
     'ONE PIECE', 'one_piece', 'OP-06', 'TCG', 'booster', 'active', 220, DATE '2023-11-25', 0, 24, 12,
     'OP-06,OP06,WINGS OF THE CAPTAIN,双璧の覇者',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,スタートデッキ,デッキ'),

    ('OP-OP07', 'ブースターパック 500年後の未来', '500 YEARS IN THE FUTURE',
     'ONE PIECE', 'one_piece', 'OP-07', 'TCG', 'booster', 'active', 220, DATE '2024-02-24', 0, 24, 12,
     '500 YEARS IN THE FUTURE,500年後の未来,OP-07,OP07',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,スタートデッキ,デッキ'),

    ('OP-OP08', 'ブースターパック 二つの伝説', 'TWO LEGENDS',
     'ONE PIECE', 'one_piece', 'OP-08', 'TCG', 'booster', 'active', 220, DATE '2024-05-25', 0, 24, 12,
     'OP-08,OP08,TWO LEGENDS,二つの伝説',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,スタートデッキ,デッキ'),

    ('OP-OP09', 'ブースターパック 新皇帝', 'EMPERORS IN THE NEW WORLD',
     'ONE PIECE', 'one_piece', 'OP-09', 'TCG', 'booster', 'active', 220, DATE '2024-08-31', 0, 24, 12,
     'EMPERORS IN THE NEW WORLD,OP-09,OP09,新皇帝',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,スタートデッキ,デッキ'),

    ('OP-OP10', 'ブースターパック 王族の血統', 'ROYAL BLOOD',
     'ONE PIECE', 'one_piece', 'OP-10', 'TCG', 'booster', 'active', 220, DATE '2024-11-30', 0, 24, 12,
     'OP-10,OP10,ROYAL BLOOD,王族の血統',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,スタートデッキ,デッキ'),

    ('OP-OP11', 'ブースターパック 疾風迅雷', 'A FIST OF DIVINE SPEED',
     'ONE PIECE', 'one_piece', 'OP-11', 'TCG', 'booster', 'active', 220, DATE '2025-03-01', 0, 24, 12,
     'A FIST OF DIVINE SPEED,OP-11,OP11,疾風迅雷,神速の拳',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,スタートデッキ,デッキ'),

    ('OP-OP12', 'ブースターパック 師弟の絆', 'LEGACY OF THE MASTER',
     'ONE PIECE', 'one_piece', 'OP-12', 'TCG', 'booster', 'active', 220, DATE '2025-05-31', 0, 24, 12,
     'LEGACY OF THE MASTER,OP-12,OP12,師弟の絆',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,スタートデッキ,デッキ'),

    ('OP-OP13', 'ブースターパック 受け継がれる意志', 'CARRYING ON HIS WILL',
     'ONE PIECE', 'one_piece', 'OP-13', 'TCG', 'booster', 'active', 220, DATE '2025-08-23', 0, 24, 12,
     'CARRYING ON HIS WILL,OP-13,OP13,受け継がれる意志',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,スタートデッキ,デッキ'),

    ('OP-OP14', 'ブースターパック 蒼海の七傑', 'THE AZURE SEA''S SEVEN',
     'ONE PIECE', 'one_piece', 'OP-14', 'TCG', 'booster', 'active', 220, DATE '2025-11-22', 0, 24, 12,
     'OP-14,OP14,THE AZURE SEA,one_piece,蒼海の七傑',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,スタートデッキ,デッキ'),

    ('OP-OP15', 'ブースターパック 神の島の冒険', 'ADVENTURE ON KAMI''S ISLAND',
     'ONE PIECE', 'one_piece', 'OP-15', 'TCG', 'booster', 'active', 220, DATE '2026-02-28', 0, 24, 12,
     'ADVENTURE ON KAMI,OP-15,OP15,one_piece,神の島の冒険',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,スタートデッキ,デッキ'),

    ('OP-OP16', 'ブースターパック 決戦の刻', 'THE TIME OF BATTLE',
     'ONE PIECE', 'one_piece', 'OP-16', 'TCG', 'booster', 'active', 220, DATE '2026-05-30', 0, 24, 12,
     'OP-16,OP16,THE TIME OF BATTLE,決戦の刻',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,スタートデッキ,デッキ'),

    ('OP-OP17', 'ブースターパック 世界最強の戦士', 'THE WORLD''S STRONGEST WARRIORS',
     'ONE PIECE', 'one_piece', 'OP-17', 'TCG', 'booster', 'active', 220, DATE '2026-08-22', 0, 24, 12,
     'OP-17,OP17,世界最強の戦士,THE WORLD''S STRONGEST,one_piece,世界最強の戦士',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,スタートデッキ,デッキ'),

    -- ====================================================================
    -- エクストラブースター (EB-01 to EB-05)
    -- ====================================================================
    ('OP-EB01', 'エクストラブースター メモリアルコレクション', 'MEMORIAL COLLECTION',
     'ONE PIECE', 'one_piece', 'EB-01', 'TCG', 'booster', 'active', 220, DATE '2024-01-27', 0, 24, 12,
     'EB-01,EB01,MEMORIAL COLLECTION,メモリアルコレクション',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,スタートデッキ,デッキ'),

    ('OP-EB02', 'エクストラブースター アニメ25thコレクション', 'Anime 25th Collection',
     'ONE PIECE', 'one_piece', 'EB-02', 'TCG', 'booster', 'active', 220, DATE '2025-01-25', 0, 24, 12,
     '25th,Anime 25th Collection,EB-02,EB02,アニメ25thコレクション',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,スタートデッキ,デッキ,25周年エディション'),

    ('OP-EB03', 'エクストラブースター ONE PIECE Heroines Edition', 'ONE PIECE HEROINES EDITION',
     'ONE PIECE', 'one_piece', 'EB-03', 'TCG', 'booster', 'active', 220, DATE '2025-10-25', 0, 24, 12,
     'EB-03,EB03,Heroines Edition,ONE PIECE Heroines Edition,ヒロインズ,ヒロインズエディション',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,スタートデッキ,デッキ,vol.2'),

    ('OP-EB04', 'エクストラブースター EGGHEAD CRISIS', 'EGGHEAD CRISIS',
     'ONE PIECE', 'one_piece', 'EB-04', 'TCG', 'booster', 'active', 220, DATE '2026-01-31', 0, 24, 12,
     'EB-04,EB04,EGGHEAD CRISIS,エッグヘッド,エッグヘッドクライシス',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,スタートデッキ,デッキ'),

    ('OP-EB05', 'エクストラブースター ONE PIECE Heroines Edition vol.2', 'ONE PIECE HEROINES EDITION vol.2',
     'ONE PIECE', 'one_piece', 'EB-05', 'TCG', 'booster', 'active', 220, NULL, 0, 24, 12,
     'EB-05,EB05,Heroines Edition vol.2,ONE PIECE Heroines Edition vol.2,ヒロインズ vol.2,ヒロインズエディション vol.2',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,スタートデッキ,デッキ'),

    -- ====================================================================
    -- プレミアムブースター (PRB-01 to PRB-02)
    -- ====================================================================
    ('OP-PRB01', 'プレミアムブースター ONE PIECE CARD THE BEST', 'ONE PIECE CARD THE BEST',
     'ONE PIECE', 'one_piece', 'PRB-01', 'TCG', 'booster', 'active', 220, DATE '2024-07-27', 0, 24, 12,
     'CARD THE BEST,ONE PIECE CARD THE BEST,PRB-01,PRB01,THE BEST,ザベスト',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,スタートデッキ,デッキ,vol.2'),

    ('OP-PRB02', 'プレミアムブースター THE BEST vol.2', 'ONE PIECE CARD THE BEST vol.2',
     'ONE PIECE', 'one_piece', 'PRB-02', 'TCG', 'booster', 'active', 220, DATE '2025-07-26', 0, 24, 12,
     'PRB-02,PRB02,THE BEST vol.2,ザベスト vol.2',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,スタートデッキ,デッキ'),

    -- ====================================================================
    -- スタートデッキ (ST-01 to ST-20)
    -- ====================================================================
    ('OP-ST01', 'スタートデッキ 麦わらの一味', 'Straw Hat Crew',
     'ONE PIECE', 'one_piece', 'ST-01', 'TCG', 'deck', 'active', 550, DATE '2022-07-08', 0, NULL, NULL,
     'ST-01,ST01,Straw Hat Crew,麦わらの一味',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン'),

    ('OP-ST02', 'スタートデッキ 最悪の世代', 'Worst Generation',
     'ONE PIECE', 'one_piece', 'ST-02', 'TCG', 'deck', 'active', 550, DATE '2022-07-08', 0, NULL, NULL,
     'ST-02,ST02,Worst Generation,最悪の世代',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン'),

    ('OP-ST03', 'スタートデッキ 王下七武海', 'The Seven Warlords of the Sea',
     'ONE PIECE', 'one_piece', 'ST-03', 'TCG', 'deck', 'active', 550, DATE '2022-07-08', 0, NULL, NULL,
     'ST-03,ST03,Seven Warlords,王下七武海',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン'),

    ('OP-ST04', 'スタートデッキ 百獣海賊団', 'Animal Kingdom Pirates',
     'ONE PIECE', 'one_piece', 'ST-04', 'TCG', 'deck', 'active', 550, DATE '2022-07-08', 0, NULL, NULL,
     'Animal Kingdom Pirates,ST-04,ST04,百獣海賊団',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン'),

    ('OP-ST05', 'スタートデッキ ONE PIECE FILM edition', 'ONE PIECE FILM edition',
     'ONE PIECE', 'one_piece', 'ST-05', 'TCG', 'deck', 'active', 550, DATE '2022-08-06', 0, NULL, NULL,
     'FILM edition,ONE PIECE FILM,ONE PIECE FILM edition,ST-05,ST05,フィルムエディション',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン'),

    ('OP-ST06', 'スタートデッキ 海軍', 'Absolute Justice',
     'ONE PIECE', 'one_piece', 'ST-06', 'TCG', 'deck', 'active', 550, DATE '2022-09-30', 0, NULL, NULL,
     'Absolute Justice,ST-06,ST06,海軍',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン'),

    ('OP-ST07', 'スタートデッキ ビッグ・マム海賊団', 'Big Mom Pirates',
     'ONE PIECE', 'one_piece', 'ST-07', 'TCG', 'deck', 'active', 550, DATE '2023-01-21', 0, NULL, NULL,
     'Big Mom Pirates,ST-07,ST07,ビッグマム,ビッグ・マム海賊団',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン'),

    ('OP-ST08', 'スタートデッキ Side モンキー・D・ルフィ', 'Monkey D. Luffy',
     'ONE PIECE', 'one_piece', 'ST-08', 'TCG', 'deck', 'active', 550, DATE '2023-03-25', 0, NULL, NULL,
     'Monkey D. Luffy,ST-08,ST08,Side モンキー・D・ルフィ,Side ルフィ,モンキー・D・ルフィ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン'),

    ('OP-ST09', 'スタートデッキ Side ヤマト', 'Yamato',
     'ONE PIECE', 'one_piece', 'ST-09', 'TCG', 'deck', 'active', 550, DATE '2023-03-25', 0, NULL, NULL,
     'ST-09,ST09,Side ヤマト,Yamato,ヤマト',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン'),

    ('OP-ST10', 'アルティメットデッキ 三船長 集結', 'The Three Captains',
     'ONE PIECE', 'one_piece', 'ST-10', 'TCG', 'deck', 'active', 1650, DATE '2023-07-29', 0, NULL, NULL,
     'ST-10,ST10,The Three Captains,アルティメット,アルティメットデッキ,アルティメットデッキ 三船長 集結,三船長',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン'),

    ('OP-ST11', 'スタートデッキ Side ウタ', 'Uta',
     'ONE PIECE', 'one_piece', 'ST-11', 'TCG', 'deck', 'active', 550, DATE '2023-10-07', 0, NULL, NULL,
     'ST-11,ST11,Side ウタ,Uta,ウタ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン'),

    ('OP-ST12', 'スタートデッキ ゾロ&サンジ', 'Zoro and Sanji',
     'ONE PIECE', 'one_piece', 'ST-12', 'TCG', 'deck', 'active', 990, DATE '2023-10-28', 0, NULL, NULL,
     'ST-12,ST12,Zoro and Sanji,サンジ,ゾロ,ゾロ&サンジ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン'),

    ('OP-ST13', 'アルティメットデッキ 3兄弟の絆', 'The Three Brothers',
     'ONE PIECE', 'one_piece', 'ST-13', 'TCG', 'deck', 'active', 3300, DATE '2023-12-23', 0, NULL, NULL,
     '3兄弟,3兄弟の絆,ST-13,ST13,The Three Brothers,アルティメット,アルティメットデッキ,アルティメットデッキ 3兄弟の絆',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン'),

    ('OP-ST14', 'スタートデッキ 3D2Y', '3D2Y',
     'ONE PIECE', 'one_piece', 'ST-14', 'TCG', 'deck', 'active', 550, DATE '2024-04-27', 0, NULL, NULL,
     '3D2Y,ST-14,ST14',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン'),

    ('OP-ST15', 'スタートデッキ 赤 エドワード・ニューゲート', 'Red Edward.Newgate',
     'ONE PIECE', 'one_piece', 'ST-15', 'TCG', 'deck', 'active', 550, DATE '2024-07-13', 0, NULL, NULL,
     'Red Edward Newgate,ST-15,ST15,ニューゲート,白ひげ,赤 エドワード・ニューゲート',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン'),

    ('OP-ST16', 'スタートデッキ 緑 ウタ', 'Green Uta',
     'ONE PIECE', 'one_piece', 'ST-16', 'TCG', 'deck', 'active', 550, DATE '2024-07-13', 0, NULL, NULL,
     'Green Uta,ST-16,ST16,緑 ウタ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン'),

    ('OP-ST17', 'スタートデッキ 青 ドンキホーテ・ドフラミンゴ', 'Blue Donquixote Doflamingo',
     'ONE PIECE', 'one_piece', 'ST-17', 'TCG', 'deck', 'active', 550, DATE '2024-07-13', 0, NULL, NULL,
     'Blue Donquixote Doflamingo,ST-17,ST17,ドフラミンゴ,青 ドフラミンゴ,青 ドンキホーテ・ドフラミンゴ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン'),

    ('OP-ST18', 'スタートデッキ 紫 モンキー・D・ルフィ', 'Purple Monkey.D.Luffy',
     'ONE PIECE', 'one_piece', 'ST-18', 'TCG', 'deck', 'active', 550, DATE '2024-07-13', 0, NULL, NULL,
     'Purple Monkey D Luffy,ST-18,ST18,紫 モンキー・D・ルフィ,紫 ルフィ,紫ルフィ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン'),

    ('OP-ST19', 'スタートデッキ 黒 スモーカー', 'Black Smoker',
     'ONE PIECE', 'one_piece', 'ST-19', 'TCG', 'deck', 'active', 550, DATE '2024-07-13', 0, NULL, NULL,
     'Black Smoker,ST-19,ST19,スモーカー,黒 スモーカー',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン'),

    ('OP-ST20', 'スタートデッキ 黄 シャーロット・カタクリ', 'Yellow Charlotte Katakuri',
     'ONE PIECE', 'one_piece', 'ST-20', 'TCG', 'deck', 'active', 550, DATE '2024-07-13', 0, NULL, NULL,
     'ST-20,ST20,Yellow Charlotte Katakuri,カタクリ,黄 カタクリ,黄 シャーロット・カタクリ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン'),

    ('OP-ST21', 'スタートデッキEX ギア5', 'GEAR5',
     'ONE PIECE', 'one_piece', 'ST-21', 'TCG', 'deck', 'active', 1650, DATE '2024-12-21', 0, NULL, NULL,
     'GEAR5,ST-21,ST21,ギア5,ギアフィフス,スタートデッキEX,スタートデッキEX ギア5',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン'),

    ('OP-ST22', 'スタートデッキ エース&ニューゲート', 'Ace & Newgate',
     'ONE PIECE', 'one_piece', 'ST-22', 'TCG', 'deck', 'active', 990, DATE '2025-04-26', 0, NULL, NULL,
     'Ace & Newgate,ST-22,ST22,エース,エース&ニューゲート,ニューゲート',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン'),

    ('OP-ST23', 'スタートデッキ 赤 シャンクス', 'Red Shanks',
     'ONE PIECE', 'one_piece', 'ST-23', 'TCG', 'deck', 'active', 550, DATE '2025-06-28', 0, NULL, NULL,
     'Red Shanks,ST-23,ST23,シャンクス,赤 シャンクス',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン'),

    ('OP-ST24', 'スタートデッキ 緑 ジュエリー・ボニー', 'Green Jewelry Bonney',
     'ONE PIECE', 'one_piece', 'ST-24', 'TCG', 'deck', 'active', 550, DATE '2025-06-28', 0, NULL, NULL,
     'Green Jewelry Bonney,ST-24,ST24,ボニー,緑 ジュエリー・ボニー',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン'),

    ('OP-ST25', 'スタートデッキ 青 バギー', 'Blue Buggy',
     'ONE PIECE', 'one_piece', 'ST-25', 'TCG', 'deck', 'active', 550, DATE '2025-06-28', 0, NULL, NULL,
     'Blue Buggy,ST-25,ST25,バギー,青 バギー',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン'),

    ('OP-ST26', 'スタートデッキ 紫黒 モンキー・D・ルフィ', 'Purple/Black Monkey.D.Luffy',
     'ONE PIECE', 'one_piece', 'ST-26', 'TCG', 'deck', 'active', 550, DATE '2025-06-28', 0, NULL, NULL,
     'Purple Black Monkey D Luffy,ST-26,ST26,紫黒 モンキー・D・ルフィ,紫黒 ルフィ,紫黒ルフィ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン'),

    ('OP-ST27', 'スタートデッキ 黒 マーシャル・D・ティーチ', 'Black Marshall.D.Teach',
     'ONE PIECE', 'one_piece', 'ST-27', 'TCG', 'deck', 'active', 550, DATE '2025-06-28', 0, NULL, NULL,
     'Black Marshall D Teach,ST-27,ST27,ティーチ,黒 ティーチ,黒 マーシャル・D・ティーチ,黒ひげ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン'),

    ('OP-ST28', 'スタートデッキ 緑黄 ヤマト', 'Green/Yellow Yamato',
     'ONE PIECE', 'one_piece', 'ST-28', 'TCG', 'deck', 'active', 550, DATE '2025-06-28', 0, NULL, NULL,
     'Green Yellow Yamato,ST-28,ST28,緑黄 ヤマト',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン'),

    ('OP-ST29', 'スタートデッキ EGGHEAD', 'Egghead',
     'ONE PIECE', 'one_piece', 'ST-29', 'TCG', 'deck', 'active', 990, DATE '2025-12-20', 0, NULL, NULL,
     'EGGHEAD,ST-29,ST29,エッグヘッド',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン'),

    ('OP-ST30', 'スタートデッキEX ルフィ&エース', 'Luffy & Ace',
     'ONE PIECE', 'one_piece', 'ST-30', 'TCG', 'deck', 'active', 1650, DATE '2026-04-11', 0, NULL, NULL,
     'Luffy & Ace,ST-30,ST30,スタートデッキEX,スタートデッキEX ルフィ&エース,ルフィ&エース',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン'),

    ('OP-ST31', 'スタートデッキ 赤 モンキー・D・ルフィ', 'Red Monkey.D.Luffy',
     'ONE PIECE', 'one_piece', 'ST-31', 'TCG', 'deck', 'active', 550, DATE '2026-07-11', 0, NULL, NULL,
     'Red Monkey D Luffy,ST-31,ST31,赤 モンキー・D・ルフィ,赤ルフィ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン'),

    ('OP-ST32', 'スタートデッキ 緑 ロロノア・ゾロ', 'Green Roronoa Zoro',
     'ONE PIECE', 'one_piece', 'ST-32', 'TCG', 'deck', 'active', 550, DATE '2026-07-11', 0, NULL, NULL,
     'Green Roronoa Zoro,ST-32,ST32,緑 ロロノア・ゾロ,緑ゾロ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン'),

    ('OP-ST33', 'スタートデッキ 青 クザン', 'Blue Kuzan',
     'ONE PIECE', 'one_piece', 'ST-33', 'TCG', 'deck', 'active', 550, DATE '2026-07-11', 0, NULL, NULL,
     'Blue Kuzan,ST-33,ST33,クザン,青 クザン',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン'),

    ('OP-ST34', 'スタートデッキ 紫 シャーロット・カタクリ', 'Purple Charlotte Katakuri',
     'ONE PIECE', 'one_piece', 'ST-34', 'TCG', 'deck', 'active', 550, DATE '2026-07-11', 0, NULL, NULL,
     'Purple Charlotte Katakuri,ST-34,ST34,紫 カタクリ,紫 シャーロット・カタクリ,紫カタクリ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン'),

    ('OP-ST35', 'スタートデッキ 赤黒 サボ', 'Red/Black Sabo',
     'ONE PIECE', 'one_piece', 'ST-35', 'TCG', 'deck', 'active', 550, DATE '2026-07-11', 0, NULL, NULL,
     'Red Black Sabo,ST-35,ST35,サボ,赤黒 サボ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン'),

    ('OP-ST36', 'スタートデッキ 黄 ユースタス・キッド', 'Yellow Eustass Captain Kid',
     'ONE PIECE', 'one_piece', 'ST-36', 'TCG', 'deck', 'active', 550, DATE '2026-07-11', 0, NULL, NULL,
     'ST-36,ST36,Yellow Eustass Captain Kid,キッド,黄 キッド,黄 ユースタス・キッド',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン'),

    -- Set Sail Deck
    ('OP-SD01', 'Set Sail Deck Set', 'Set Sail Deck Set',
     'ONE PIECE', 'one_piece', 'SD-01', 'TCG', 'deck', 'active', NULL, DATE '2026-09-18', 0, NULL, NULL,
     'SD-01,SD01,Set Sail Deck,Set Sail Deck Set,セットセイル',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン'),

    -- ====================================================================
    -- ダブルパックセット (DP-01 to DP-12)
    -- ====================================================================
    ('OP-DP01', 'ダブルパックセット vol.1', 'Double Pack Set Vol.1',
     'ONE PIECE', 'one_piece', 'DP-01', 'TCG', 'special', 'active', NULL, DATE '2023-09-22', 0, NULL, NULL,
     'DP-01,DP01,vol.1',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-DP02', 'ダブルパックセット vol.2', 'Double Pack Set Vol.2',
     'ONE PIECE', 'one_piece', 'DP-02', 'TCG', 'special', 'active', NULL, DATE '2023-12-08', 0, NULL, NULL,
     'DP-02,DP02,vol.2',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-DP03', 'ダブルパックセット vol.3', 'Double Pack Set Vol.3',
     'ONE PIECE', 'one_piece', 'DP-03', 'TCG', 'special', 'active', NULL, DATE '2024-03-15', 0, NULL, NULL,
     'DP-03,DP03,vol.3',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-DP04', 'ダブルパックセット vol.4', 'Double Pack Set Vol.4',
     'ONE PIECE', 'one_piece', 'DP-04', 'TCG', 'special', 'active', NULL, DATE '2024-06-28', 0, NULL, NULL,
     'DP-04,DP04,vol.4',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-DP05', 'ダブルパックセット vol.5', 'Double Pack Set Vol.5',
     'ONE PIECE', 'one_piece', 'DP-05', 'TCG', 'special', 'active', NULL, DATE '2024-09-13', 0, NULL, NULL,
     'DP-05,DP05,vol.5',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-DP06', 'ダブルパックセット vol.6', 'Double Pack Set Vol.6',
     'ONE PIECE', 'one_piece', 'DP-06', 'TCG', 'special', 'active', NULL, DATE '2024-12-13', 0, NULL, NULL,
     'DP-06,DP06,vol.6',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-DP07', 'ダブルパックセット vol.7', 'Double Pack Set Vol.7',
     'ONE PIECE', 'one_piece', 'DP-07', 'TCG', 'special', 'active', NULL, DATE '2025-06-06', 0, NULL, NULL,
     'DP-07,DP07,vol.7',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-DP08', 'ダブルパックセット vol.8', 'Double Pack Set Vol.8',
     'ONE PIECE', 'one_piece', 'DP-08', 'TCG', 'special', 'active', NULL, DATE '2025-08-22', 0, NULL, NULL,
     'DP-08,DP08,vol.8',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-DP09', 'ダブルパックセット vol.9', 'Double Pack Set Vol.9',
     'ONE PIECE', 'one_piece', 'DP-09', 'TCG', 'special', 'active', NULL, DATE '2026-01-16', 0, NULL, NULL,
     'DP-09,DP09,vol.9',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-DP10', 'ダブルパックセット vol.10', 'Double Pack Set Vol.10',
     'ONE PIECE', 'one_piece', 'DP-10', 'TCG', 'special', 'active', NULL, DATE '2026-04-03', 0, NULL, NULL,
     'DP-10,DP10,vol.10',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-DP11', 'ダブルパックセット vol.11', 'Double Pack Set Vol.11',
     'ONE PIECE', 'one_piece', 'DP-11', 'TCG', 'special', 'active', NULL, DATE '2026-06-12', 0, NULL, NULL,
     'DP-11,DP11,vol.11',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-DP12', 'ダブルパックセット vol.12', 'Double Pack Set Vol.12',
     'ONE PIECE', 'one_piece', 'DP-12', 'TCG', 'special', 'active', NULL, DATE '2026-08-28', 0, NULL, NULL,
     'DP-12,DP12,vol.12',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    -- ====================================================================
    -- スペシャルセット各種 (20件)
    -- ====================================================================
    ('OP-DF01', 'デビルフルーツコレクション vol.1', 'Devil Fruits Collection Vol.1',
     'ONE PIECE', 'one_piece', 'DF-01', 'TCG', 'special', 'active', NULL, DATE '2023-11-03', 0, NULL, NULL,
     'DF-01,DF01,Devil Fruits Collection,vol.1,デビルフルーツコレクション',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-DF02', 'デビルフルーツコレクション vol.2', 'Devil Fruits Collection Vol.2',
     'ONE PIECE', 'one_piece', 'DF-02', 'TCG', 'special', 'active', NULL, DATE '2024-11-08', 0, NULL, NULL,
     'DF-02,DF02,Devil Fruits Collection,vol.2,デビルフルーツコレクション',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-DF03', 'デビルフルーツコレクション vol.3', 'Devil Fruits Collection Vol.3',
     'ONE PIECE', 'one_piece', 'DF-03', 'TCG', 'special', 'active', NULL, DATE '2025-11-14', 0, NULL, NULL,
     'DF-03,DF03,Devil Fruits Collection,vol.3,デビルフルーツコレクション',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-TS01', 'ティンパックセット vol.1', 'Tin Pack Set Vol.1',
     'ONE PIECE', 'one_piece', 'TS-01', 'TCG', 'special', 'active', NULL, DATE '2025-04-18', 0, NULL, NULL,
     'TS-01,TS01,Tin Pack Set,vol.1,ティンパックセット',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-TS02', 'ティンパックセット vol.2', 'Tin Pack Set Vol.2',
     'ONE PIECE', 'one_piece', 'TS-02', 'TCG', 'special', 'active', NULL, DATE '2026-01-30', 0, NULL, NULL,
     'TS-02,TS02,Tin Pack Set,vol.2,ティンパックセット',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-GC01', 'ギフトコレクション2023', 'GIFT COLLECTION 2023',
     'ONE PIECE', 'one_piece', 'GC-01', 'TCG', 'special', 'active', NULL, DATE '2023-10-27', 0, NULL, NULL,
     'GC-01,GC01,GIFT COLLECTION,ギフトコレクション,ギフトコレクション2023',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-SDS01', 'スペシャルドン!!セット vol.1 ルフィ', 'Special DON!! Set Vol.1 -Luffy-',
     'ONE PIECE', 'one_piece', 'SDS-01', 'TCG', 'special', 'active', NULL, NULL, 0, NULL, NULL,
     'SDS-01,SDS01,Special DON!! Set,vol.1 ルフィ,スペシャルドン!!セット,ルフィ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-SDS02', 'スペシャルドン!!セット vol.2 エース', 'Special DON!! Set Vol.2 -Ace-',
     'ONE PIECE', 'one_piece', 'SDS-02', 'TCG', 'special', 'active', NULL, NULL, 0, NULL, NULL,
     'SDS-02,SDS02,Special DON!! Set,vol.2 エース,エース,スペシャルドン!!セット',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-SDS03', 'スペシャルドン!!セット vol.3 サボ', 'Special DON!! Set Vol.3 -Sabo-',
     'ONE PIECE', 'one_piece', 'SDS-03', 'TCG', 'special', 'active', NULL, NULL, 0, NULL, NULL,
     'SDS-03,SDS03,Special DON!! Set,vol.3 サボ,サボ,スペシャルドン!!セット',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-1ANNY', 'ONE PIECEカードゲーム 1st ANNIVERSARY SET', '1st Anniversary Set',
     'ONE PIECE', 'one_piece', '1ANNY', 'TCG', 'special', 'active', NULL, NULL, 0, NULL, NULL,
     '1ANNY,1st ANNIVERSARY SET,1周年,ONE PIECEカードゲーム 1st ANNIVERSARY SET',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-2ANNY', 'ONE PIECEカードゲーム 2nd ANNIVERSARY SET', '2nd Anniversary Set',
     'ONE PIECE', 'one_piece', '2ANNY', 'TCG', 'special', 'active', NULL, NULL, 0, NULL, NULL,
     '2ANNY,2nd ANNIVERSARY SET,2周年,ONE PIECEカードゲーム 2nd ANNIVERSARY SET',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-3ANNY', 'ONE PIECEカードゲーム 3rd ANNIVERSARY SET', '3rd Anniversary Set',
     'ONE PIECE', 'one_piece', '3ANNY', 'TCG', 'special', 'active', NULL, NULL, 0, NULL, NULL,
     '3ANNY,3rd ANNIVERSARY SET,3周年,ONE PIECEカードゲーム 3rd ANNIVERSARY SET',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-HERO-SS', 'ONE PIECE Heroines Special Set', 'ONE PIECE Heroines Special Set',
     'ONE PIECE', 'one_piece', 'HERO-SS', 'TCG', 'special', 'active', NULL, NULL, 0, NULL, NULL,
     'HERO-SS,HEROSS,Heroines Special Set,ONE PIECE Heroines Special Set,ヒロインズ,ヒロインズスペシャルセット',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-PCC-UTA', 'プレミアムカードコレクション -ウタ-', 'Premium Card Collection -Uta-',
     'ONE PIECE', 'one_piece', 'PCC-UTA', 'TCG', 'special', 'active', NULL, DATE '2023-10-07', 0, NULL, NULL,
     '-ウタ-,PCC-UTA,PCCUTA,Uta,ウタ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-PCC-LA1', 'プレミアムカードコレクション -Live Action Edition-', 'Premium Card Collection -Live Action Edition-',
     'ONE PIECE', 'one_piece', 'PCC-LA1', 'TCG', 'special', 'active', NULL, NULL, 0, NULL, NULL,
     '-Live Action Edition-,Live Action Edition,PCC-LA1,PCCLA-1,PCCLA1,ライブアクション',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-PCC-LA2-BW', 'プレミアムカードコレクション -Live Action Edition vol.2 バロックワークス-', 'Premium Card Collection -Live Action Edition vol.2 Baroque Works-',
     'ONE PIECE', 'one_piece', 'PCC-LA2-BW', 'TCG', 'special', 'active', NULL, NULL, 0, NULL, NULL,
     '-Live Action Edition vol.2 バロックワークス-,Baroque Works,Live Action Edition vol.2,PCC-LA2-BW,PCCLA-2BW,PCCLA2BW,バロックワークス',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-PCC-LA2-SH', 'プレミアムカードコレクション -Live Action Edition vol.2 麦わらの一味-', 'Premium Card Collection -Live Action Edition vol.2 Straw Hat Crew-',
     'ONE PIECE', 'one_piece', 'PCC-LA2-SH', 'TCG', 'special', 'active', NULL, NULL, 0, NULL, NULL,
     '-Live Action Edition vol.2 麦わらの一味-,Live Action Edition vol.2,PCC-LA2-SH,PCCLA-2SH,PCCLA2SH,Straw Hat Crew,麦わらの一味',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-PCC-FR', 'プレミアムカードコレクション -FILM RED Edition-', 'Premium Card Collection -FILM RED Edition-',
     'ONE PIECE', 'one_piece', 'PCC-FR', 'TCG', 'special', 'active', NULL, NULL, 0, NULL, NULL,
     '-FILM RED Edition-,FILM RED Edition,PCC-FR,PCCFR,フィルムレッド',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-PCC-25', 'プレミアムカードコレクション 25周年エディション', 'Premium Card Collection -25th Edition-',
     'ONE PIECE', 'one_piece', 'PCC-25', 'TCG', 'special', 'active', NULL, NULL, 0, NULL, NULL,
     '25th Edition,25周年,25周年エディション,PCC-25,PCC25',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-PCC-KUMA', 'プレミアムカードコレクション -熊本県スペシャル-', 'Premium Card Collection -Kumamoto Special-',
     'ONE PIECE', 'one_piece', 'PCC-KUMA', 'TCG', 'special', 'active', NULL, DATE '2026-02-22', 0, NULL, NULL,
     '-熊本県スペシャル-,Kumamoto Special,PCC-KUMA,PCCKUMA,熊本県スペシャル',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    -- ====================================================================
    -- チャンピオンシップセット (9件)
    -- ====================================================================
    ('OP-CS22-LUFFY', 'チャンピオンシップセット2022 モンキー・D・ルフィ', 'Championship Set 2022 Monkey D. Luffy',
     'ONE PIECE', 'one_piece', 'CS22-LF', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'CS-22LF,CS22-LF,CS22LF,Championship Set,チャンピオンシップセット,チャンピオンシップセット2022 モンキー・D・ルフィ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-CS22-YAMATO', 'チャンピオンシップセット2022 ヤマト', 'Championship Set 2022 Yamato',
     'ONE PIECE', 'one_piece', 'CS22-YM', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'CS-22YM,CS22-YM,CS22YM,Championship Set,チャンピオンシップセット,チャンピオンシップセット2022 ヤマト',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-CS22-LAW', 'チャンピオンシップセット2022 トラファルガー・ロー', 'Championship Set 2022 Trafalgar Law',
     'ONE PIECE', 'one_piece', 'CS22-LW', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'CS-22LW,CS22-LW,CS22LW,Championship Set,チャンピオンシップセット,チャンピオンシップセット2022 トラファルガー・ロー',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-CS22-SHANKS', 'チャンピオンシップセット2022 シャンクス', 'Championship Set 2022 Shanks',
     'ONE PIECE', 'one_piece', 'CS22-SK', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'CS-22SK,CS22-SK,CS22SK,Championship Set,チャンピオンシップセット,チャンピオンシップセット2022 シャンクス',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-CS22-KID', 'チャンピオンシップセット2022 ユースタス・キッド', 'Championship Set 2022 Eustass Kid',
     'ONE PIECE', 'one_piece', 'CS22-KD', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'CS-22KD,CS22-KD,CS22KD,Championship Set,チャンピオンシップセット,チャンピオンシップセット2022 ユースタス・キッド',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-CS22-NAMI', 'チャンピオンシップセット2022 ナミ', 'Championship Set 2022 Nami',
     'ONE PIECE', 'one_piece', 'CS22-NM', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'CS-22NM,CS22-NM,CS22NM,Championship Set,チャンピオンシップセット,チャンピオンシップセット2022 ナミ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-CS22-ACE', 'チャンピオンシップセット2022 ポートガス・D・エース', 'Championship Set 2022 Portgas D. Ace',
     'ONE PIECE', 'one_piece', 'CS22-AC', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'CS-22AC,CS22-AC,CS22AC,Championship Set,チャンピオンシップセット,チャンピオンシップセット2022 ポートガス・D・エース',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-CS23', 'チャンピオンシップセット2023', 'Championship Set 2023',
     'ONE PIECE', 'one_piece', 'CS23', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'CS-23,CS23,Championship Set,チャンピオンシップセット,チャンピオンシップセット2023',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-CS23-YK', 'チャンピオンシップセット2023（旧四皇）', 'Special Set -Former Four Emperors-',
     'ONE PIECE', 'one_piece', 'CS23-YK', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'CS-23YK,CS23-YK,CS23YK,Former Four Emperors,チャンピオンシップセット,チャンピオンシップセット2023（旧四皇）,旧四皇',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    -- ファミリー/学習デッキ (2件)
    ('OP-FAMILY', 'ファミリーデッキセット', 'Family Deck Set',
     'ONE PIECE', 'one_piece', 'FAMILY', 'TCG', 'deck', 'active', NULL, DATE '2023-04-29', 0, NULL, NULL,
     'FAMILY,Family Deck Set,ファミリーデッキセット',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン'),

    ('OP-LEARN', 'いっしょに学ぼうデッキセット', 'Learn Together Deck Set',
     'ONE PIECE', 'one_piece', 'LEARN', 'TCG', 'deck', 'active', NULL, NULL, 0, NULL, NULL,
     'LEARN,Learn Together Deck Set,いっしょに学ぼうデッキセット',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ブースターパック,BOX,カートン'),

    -- ====================================================================
    -- ベストセレクション (7件)
    -- ====================================================================
    ('OP-BS01', 'プレミアムカードコレクション -ベストセレクション vol.1-', 'Premium Card Collection -Best Selection-',
     'ONE PIECE', 'one_piece', 'BS-01', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     '-ベストセレクション vol.1-,BS-01,BS01,Best Selection,ベストセレクション',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-BS02', 'プレミアムカードコレクション -ベストセレクション vol.2-', 'Premium Card Collection -Best Selection Vol.2-',
     'ONE PIECE', 'one_piece', 'BS-02', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     '-ベストセレクション vol.2-,BS-02,BS02,Best Selection,ベストセレクション',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-BS03', 'プレミアムカードコレクション -ベストセレクション vol.3-', 'Premium Card Collection -Best Selection Vol.3-',
     'ONE PIECE', 'one_piece', 'BS-03', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     '-ベストセレクション vol.3-,BS-03,BS03,Best Selection,ベストセレクション',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-BS04', 'プレミアムカードコレクション -ベストセレクション vol.4-', 'Premium Card Collection -Best Selection Vol.4-',
     'ONE PIECE', 'one_piece', 'BS-04', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     '-ベストセレクション vol.4-,BS-04,BS04,Best Selection,ベストセレクション',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-BS05', 'プレミアムカードコレクション -ベストセレクション vol.5-', 'Premium Card Collection -Best Selection Vol.5-',
     'ONE PIECE', 'one_piece', 'BS-05', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     '-ベストセレクション vol.5-,BS-05,BS05,Best Selection,ベストセレクション',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-BS06', 'プレミアムカードコレクション -ベストセレクション vol.6-', 'Premium Card Collection -Best Selection Vol.6-',
     'ONE PIECE', 'one_piece', 'BS-06', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     '-ベストセレクション vol.6-,BS-06,BS06,Best Selection,ベストセレクション',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-BS07', 'プレミアムカードコレクション -ベストセレクション vol.7-', 'Premium Card Collection -Best Selection Vol.7-',
     'ONE PIECE', 'one_piece', 'BS-07', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     '-ベストセレクション vol.7-,BS-07,BS07,Best Selection,ベストセレクション',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    -- ====================================================================
    -- PCC追加 (6件)
    -- ====================================================================
    ('OP-PCC-6A1', 'プレミアムカードコレクション -6 assort vol.1-', 'Premium Card Collection -6 assort vol.1-',
     'ONE PIECE', 'one_piece', 'PCC-6A1', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     '-6 assort vol.1-,6 assort vol.1,PCC-6A1,PCC6A1',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-PCC-6A2', 'プレミアムカードコレクション -6 assort vol.2-', 'Premium Card Collection -6 assort vol.2-',
     'ONE PIECE', 'one_piece', 'PCC-6A2', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     '-6 assort vol.2-,6 assort vol.2,PCC-6A2,PCC6A2',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-PCC-LEAD', 'プレミアムカードコレクション -リーダーコレクション-', 'Premium Card Collection -Leader Collection-',
     'ONE PIECE', 'one_piece', 'PCC-LEAD', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     '-リーダーコレクション-,Leader Collection,PCC-LEAD,PCCLEAD,リーダーコレクション',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-PCC-DAY25', 'プレミアムカードコレクション -ONE PIECE DAY''25-', 'Premium Card Collection -ONE PIECE DAY''25-',
     'ONE PIECE', 'one_piece', 'PCC-DAY25', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     '-ONE PIECE DAY,ONE PIECE,ONE PIECE DAY,PCC-DAY25',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-PCC-29', 'プレミアムカードコレクション -29thアニバーサリー-', 'Premium Card Collection -29th Anniversary Edition-',
     'ONE PIECE', 'one_piece', 'PCC-29', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     '-29thアニバーサリー-,29th Anniversary,29thアニバーサリー,PCC-29,PCC29',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-PCC-ACE', 'プレミアムカードコレクション -Ace & Sabo & Luffy-', 'Premium Card Collection -Ace & Sabo & Luffy-',
     'ONE PIECE', 'one_piece', 'PCC-ACE', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     '-Ace & Sabo & Luffy-,Ace & Sabo & Luffy,PCC-ACE,PCCACE,エース,サボ,ルフィ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    -- ====================================================================
    -- プロモーションパック (11件)
    -- ====================================================================
    ('OP-PP2201', 'プロモーションパック 2022 Vol.1', 'Promotion Pack 2022 Vol.1',
     'ONE PIECE', 'one_piece', 'PP22-01', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     '2022 Vol.1,PP-2201,PP22-01,PP2201,Promotion Pack,プロモーションパック',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-PP2202', 'プロモーションパック 2022 Vol.2', 'Promotion Pack 2022 Vol.2',
     'ONE PIECE', 'one_piece', 'PP22-02', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     '2022 Vol.2,PP-2202,PP22-02,PP2202,Promotion Pack,プロモーションパック',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-PP03', 'プロモーションパック Vol.3', 'Promotion Pack Vol.3',
     'ONE PIECE', 'one_piece', 'PP-03', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'PP-03,PP03,Promotion Pack,Vol.3,プロモーションパック',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-PP04', 'プロモーションパック Vol.4', 'Promotion Pack Vol.4',
     'ONE PIECE', 'one_piece', 'PP-04', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'PP-04,PP04,Promotion Pack,Vol.4,プロモーションパック',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-PP05', 'プロモーションパック Vol.5', 'Promotion Pack Vol.5',
     'ONE PIECE', 'one_piece', 'PP-05', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'PP-05,PP05,Promotion Pack,Vol.5,プロモーションパック',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-PP06', 'プロモーションパック Vol.6', 'Promotion Pack Vol.6',
     'ONE PIECE', 'one_piece', 'PP-06', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'PP-06,PP06,Promotion Pack,Vol.6,プロモーションパック',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-PP07', 'プロモーションパック Vol.7', 'Promotion Pack Vol.7',
     'ONE PIECE', 'one_piece', 'PP-07', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'PP-07,PP07,Promotion Pack,Vol.7,プロモーションパック',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-PP08', 'プロモーションパック Vol.8', 'Promotion Pack Vol.8',
     'ONE PIECE', 'one_piece', 'PP-08', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'PP-08,PP08,Promotion Pack,Vol.8,プロモーションパック',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-PP09', 'プロモーションパック Vol.9', 'Promotion Pack Vol.9',
     'ONE PIECE', 'one_piece', 'PP-09', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'PP-09,PP09,Promotion Pack,Vol.9,プロモーションパック',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-PPEX02', 'プロモーションパック EX Vol.2', 'Promotion Pack EX Vol.2',
     'ONE PIECE', 'one_piece', 'PPEX-02', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'EX Vol.2,PPEX-02,PPEX02,Promotion Pack EX,プロモーションパック',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-PPEX04', 'プロモーションパック EX Vol.4', 'Promotion Pack EX Vol.4',
     'ONE PIECE', 'one_piece', 'PPEX-04', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'EX Vol.4,PPEX-04,PPEX04,Promotion Pack EX,プロモーションパック',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    -- ====================================================================
    -- スタンダードバトルパック (17件: SBP-01 to SBP-17)
    -- ====================================================================
    ('OP-SBP01', 'スタンダードバトルパック Vol.1', 'Standard Battle Pack Vol.1',
     'ONE PIECE', 'one_piece', 'SBP-01', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'SBP-01,SBP01,Vol.1',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-SBP02', 'スタンダードバトルパック Vol.2', 'Standard Battle Pack Vol.2',
     'ONE PIECE', 'one_piece', 'SBP-02', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'SBP-02,SBP02,Vol.2',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-SBP03', 'スタンダードバトルパック Vol.3', 'Standard Battle Pack Vol.3',
     'ONE PIECE', 'one_piece', 'SBP-03', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'SBP-03,SBP03,Vol.3',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-SBP04', 'スタンダードバトルパック Vol.4', 'Standard Battle Pack Vol.4',
     'ONE PIECE', 'one_piece', 'SBP-04', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'SBP-04,SBP04,Vol.4',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-SBP05', 'スタンダードバトルパック Vol.5', 'Standard Battle Pack Vol.5',
     'ONE PIECE', 'one_piece', 'SBP-05', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'SBP-05,SBP05,Vol.5',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-SBP06', 'スタンダードバトルパック Vol.6', 'Standard Battle Pack Vol.6',
     'ONE PIECE', 'one_piece', 'SBP-06', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'SBP-06,SBP06,Vol.6',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-SBP07', 'スタンダードバトルパック Vol.7', 'Standard Battle Pack Vol.7',
     'ONE PIECE', 'one_piece', 'SBP-07', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'SBP-07,SBP07,Vol.7',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-SBP08', 'スタンダードバトルパック Vol.8', 'Standard Battle Pack Vol.8',
     'ONE PIECE', 'one_piece', 'SBP-08', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'SBP-08,SBP08,Vol.8',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-SBP09', 'スタンダードバトルパック Vol.9', 'Standard Battle Pack Vol.9',
     'ONE PIECE', 'one_piece', 'SBP-09', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'SBP-09,SBP09,Vol.9',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-SBP10', 'スタンダードバトルパック Vol.10', 'Standard Battle Pack Vol.10',
     'ONE PIECE', 'one_piece', 'SBP-10', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'SBP-10,SBP10,Vol.10',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-SBP11', 'スタンダードバトルパック Vol.11', 'Standard Battle Pack Vol.11',
     'ONE PIECE', 'one_piece', 'SBP-11', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'SBP-11,SBP11,Vol.11',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-SBP12', 'スタンダードバトルパック Vol.12', 'Standard Battle Pack Vol.12',
     'ONE PIECE', 'one_piece', 'SBP-12', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'SBP-12,SBP12,Vol.12',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-SBP13', 'スタンダードバトルパック Vol.13', 'Standard Battle Pack Vol.13',
     'ONE PIECE', 'one_piece', 'SBP-13', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'SBP-13,SBP13,Vol.13',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-SBP14', 'スタンダードバトルパック Vol.14', 'Standard Battle Pack Vol.14',
     'ONE PIECE', 'one_piece', 'SBP-14', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'SBP-14,SBP14,Vol.14',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-SBP15', 'スタンダードバトルパック Vol.15', 'Standard Battle Pack Vol.15',
     'ONE PIECE', 'one_piece', 'SBP-15', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'SBP-15,SBP15,Vol.15',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-SBP16', 'スタンダードバトルパック Vol.16', 'Standard Battle Pack Vol.16',
     'ONE PIECE', 'one_piece', 'SBP-16', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'SBP-16,SBP16,Vol.16',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-SBP17', 'スタンダードバトルパック Vol.17', 'Standard Battle Pack Vol.17',
     'ONE PIECE', 'one_piece', 'SBP-17', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'SBP-17,SBP17,Vol.17',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    -- ====================================================================
    -- 雑誌付録プロモ (6件)
    -- ====================================================================
    ('OP-VJ', 'Vジャンプ付録カード', 'V Jump Appendix Card',
     'ONE PIECE', 'one_piece', 'VJ', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'V Jump,VJ,Vジャンプ,Vジャンプ付録カード,付録カード',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-WSJ', '週刊少年ジャンプ付録カード', 'Weekly Shonen Jump Appendix Card',
     'ONE PIECE', 'one_piece', 'WSJ', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'WSJ,Weekly Shonen Jump,付録カード,週刊少年ジャンプ,週刊少年ジャンプ付録カード',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-SJ', '最強ジャンプ付録カード', 'Saikyo Jump Appendix Card',
     'ONE PIECE', 'one_piece', 'SJ', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'SJ,Saikyo Jump,付録カード,最強ジャンプ,最強ジャンプ付録カード',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-PCS1', 'プロモーションカードセット(1)', 'Promotion Card Set (1)',
     'ONE PIECE', 'one_piece', 'PCS-01', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'PCS-01,PCS01,Promotion Card Set,プロモーションカードセット,プロモーションカードセット(1)',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-PCS2', 'プロモーションカードセット(2)', 'Promotion Card Set (2)',
     'ONE PIECE', 'one_piece', 'PCS-02', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'PCS-02,PCS02,Promotion Card Set,プロモーションカードセット,プロモーションカードセット(2)',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-PCS25', 'プロモーションカードセット 2025', 'Promotion Card Set 2025',
     'ONE PIECE', 'one_piece', 'PCS-25', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     '2025,PCS-25,PCS25,Promotion Card Set,プロモーションカードセット,プロモーションカードセット 2025',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    -- ====================================================================
    -- 映画/コラボ (2件)
    -- ====================================================================
    ('OP-FILMRED', 'ONE PIECE FILM RED 入場者特典カード', 'ONE PIECE FILM RED Theater Bonus Card',
     'ONE PIECE', 'one_piece', 'FILMRED', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'FILM RED,FILMRED,ONE PIECE FILM RED 入場者特典カード,Theater Bonus Card,フィルムレッド,入場者特典カード',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-7ELEVEN', 'セブンイレブンキャンペーン特典カード', 'Seven-Eleven Campaign Card',
     'ONE PIECE', 'one_piece', '7ELEVEN', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     '7-ELEVEN,7ELEVEN,Campaign Card,キャンペーン特典カード,セブンイレブン,セブンイレブンキャンペーン特典カード',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    -- ====================================================================
    -- イラストレーションボックス (9件: IB-01 to IB-08 + IB-EX)
    -- ====================================================================
    ('OP-IB01', 'イラストレーションボックス Vol.1', 'Illustration Box Vol.1',
     'ONE PIECE', 'one_piece', 'IB-01', 'TCG', 'special', 'active', NULL, NULL, 0, NULL, NULL,
     'IB-01,IB01,Illustration Box,イラストレーションボックス,イラストレーションボックス Vol.1',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-IB02', 'イラストレーションボックス Vol.2', 'Illustration Box Vol.2',
     'ONE PIECE', 'one_piece', 'IB-02', 'TCG', 'special', 'active', NULL, NULL, 0, NULL, NULL,
     'IB-02,IB02,Illustration Box,イラストレーションボックス,イラストレーションボックス Vol.2',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-IB03', 'イラストレーションボックス Vol.3', 'Illustration Box Vol.3',
     'ONE PIECE', 'one_piece', 'IB-03', 'TCG', 'special', 'active', NULL, NULL, 0, NULL, NULL,
     'IB-03,IB03,Illustration Box,イラストレーションボックス,イラストレーションボックス Vol.3',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-IB04', 'イラストレーションボックス Vol.4', 'Illustration Box Vol.4',
     'ONE PIECE', 'one_piece', 'IB-04', 'TCG', 'special', 'active', NULL, NULL, 0, NULL, NULL,
     'IB-04,IB04,Illustration Box,イラストレーションボックス,イラストレーションボックス Vol.4',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-IB05', 'イラストレーションボックス Vol.5', 'Illustration Box Vol.5',
     'ONE PIECE', 'one_piece', 'IB-05', 'TCG', 'special', 'active', NULL, NULL, 0, NULL, NULL,
     'IB-05,IB05,Illustration Box,イラストレーションボックス,イラストレーションボックス Vol.5',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-IB06', 'イラストレーションボックス Vol.6', 'Illustration Box Vol.6',
     'ONE PIECE', 'one_piece', 'IB-06', 'TCG', 'special', 'active', NULL, NULL, 0, NULL, NULL,
     'IB-06,IB06,Illustration Box,イラストレーションボックス,イラストレーションボックス Vol.6',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-IB07', 'イラストレーションボックス Vol.7', 'Illustration Box Vol.7',
     'ONE PIECE', 'one_piece', 'IB-07', 'TCG', 'special', 'active', NULL, NULL, 0, NULL, NULL,
     'IB-07,IB07,Illustration Box,イラストレーションボックス,イラストレーションボックス Vol.7',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-IB08', 'イラストレーションボックス Vol.8', 'Illustration Box Vol.8',
     'ONE PIECE', 'one_piece', 'IB-08', 'TCG', 'special', 'active', NULL, NULL, 0, NULL, NULL,
     'IB-08,IB08,Illustration Box,イラストレーションボックス,イラストレーションボックス Vol.8',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-IBEX', 'イラストレーションボックス EX', 'Illustration Box EX',
     'ONE PIECE', 'one_piece', 'IB-EX', 'TCG', 'special', 'active', NULL, NULL, 0, NULL, NULL,
     'IB-EX,IBEX,Illustration Box EX,イラストレーションボックス EX',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    -- ====================================================================
    -- その他限定 (5件) + リーダーカードフィギュア (1件)
    -- ====================================================================
    ('OP-UTA-COL', 'ウタコレクション', 'UTA Collection',
     'ONE PIECE', 'one_piece', 'UTA-COL', 'TCG', 'special', 'active', NULL, NULL, 0, NULL, NULL,
     'UTA Collection,UTA-COL,UTACOL,ウタ,ウタコレクション',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-TREASURE', 'トレジャーブースターズセット', 'Treasure Boosters Set',
     'ONE PIECE', 'one_piece', 'TREASURE', 'TCG', 'special', 'active', NULL, NULL, 0, NULL, NULL,
     'TREASURE,Treasure Boosters Set,トレジャーブースターズセット',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-SGS', 'スペシャルグッズセット -Ace/Sabo/Luffy-', 'Special Goods Set -Ace/Sabo/Luffy-',
     'ONE PIECE', 'one_piece', 'SGS', 'TCG', 'special', 'active', NULL, NULL, 0, NULL, NULL,
     'Ace,Luffy,SGS,Sabo,Special Goods Set,エース,サボ,スペシャルグッズセット,スペシャルグッズセット -Ace/Sabo/Luffy-,ルフィ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-DONCARD', 'ストレージボックス×ドン!!カードセット', 'Storage Box & DON!! Card Set',
     'ONE PIECE', 'one_piece', 'DONCARD', 'TCG', 'special', 'active', NULL, NULL, 0, NULL, NULL,
     'DON!! Card Set,DONCARD,Storage Box,ストレージボックス,ストレージボックス×ドン!!カードセット,ドン!!カードセット',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-PCC-MERA', 'プレミアムカードコレクション -メラメラの実争奪戦Edition-', 'Premium Card Collection -Flame-Flame Fruit Coliseum Edition-',
     'ONE PIECE', 'one_piece', 'PCC-MERA', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     '-メラメラの実争奪戦Edition-,Flame-Flame Fruit,PCC-MERA,PCCMERA,メラメラの実',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    ('OP-LCF', 'リーダーカードフィギュア 応募者全員サービス', 'Leader Card Figure',
     'ONE PIECE', 'one_piece', 'LCF', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'LCF,Leader Card Figure,リーダーカードフィギュア,リーダーカードフィギュア 応募者全員サービス,応募者全員サービス',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ')

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
        updated_at = NOW();
END $$;
