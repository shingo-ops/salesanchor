-- ============================================================================
-- Migration 20260913_030000: マスタ未登録商品 17件の追加
--
-- 目的:
--   Gemini抽出で取引実績がありながら商品マスタに未登録だった商品を追加。
--   検索ワード(search_keywords)は型番+タイトル+固有識別子のみ（Phase 1方針準拠）。
--   除外ワード(exclude_keywords)で類似商品との誤マッチを防止。
--
-- 対象:
--   Dragon Ball フュージョンワールド 新弾 7件 (FB-09〜12, FS-11〜12, STORY BOOSTER 01)
--   ONE PIECE プロモ・付録系 9件 (DAY'24, Nike, ROUND1, P-159, CHOPPER's, ナツコミ, EMOTION, Guide, VJ10月号)
--   ドラゴンボールスーパーダイバーズ 1件 (PO判断で登録)
--
-- 出典: 公式サイト + 通販サイト + ニュース記事
--   詳細: /tmp/CC報告ファイル/unregistered_products_master_v2.txt
--
-- ADR-090: public 中央カタログ（tenant_id=NULL）。在庫数は 0。
-- 冪等: ON CONFLICT(product_code) WHERE product_code IS NOT NULL DO UPDATE。
-- ============================================================================

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
        RAISE NOTICE 'public.products required columns not present — skipping seed';
        RETURN;
    END IF;

    INSERT INTO public.products
        (product_code, name, name_en, category, tcg_type, mark, product_kind,
         set_type, status, unit_price, release_date, stock_quantity,
         packs_per_box, boxes_per_case, search_keywords, exclude_keywords)
    VALUES

    -- ====================================================================
    -- Dragon Ball フュージョンワールド — ブースターパック新弾 (FB-09 〜 FB-12)
    -- ====================================================================
    -- キーワード設計:
    --   search: 型番(ハイフン有無) + 英語タイトル（日本語サブタイトルなし）
    --   exclude: 競合TCG + ONE PIECE + 別DBゲーム(ダイバーズ) + アクセサリ類

    ('DB-FB09', 'ブースターパック DUAL EVOLUTION', 'Booster Pack -DUAL EVOLUTION-',
     'Dragon Ball', 'dragon_ball', 'FB09', 'TCG', 'booster', 'active', 220, DATE '2026-03-14', 0, 24, 12,
     'FB-09,FB09,DUAL EVOLUTION',
     'スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ワンピース,ワンピースカード,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ヒーローズ,SDBH,ダイバーズ,超カードゲーム,ガンダム'),

    ('DB-FB10', 'ブースターパック CROSS FORCE', 'Booster Pack -CROSS FORCE-',
     'Dragon Ball', 'dragon_ball', 'FB10', 'TCG', 'booster', 'active', 220, DATE '2026-06-13', 0, 24, 12,
     'FB-10,FB10,CROSS FORCE',
     'スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ワンピース,ワンピースカード,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ヒーローズ,SDBH,ダイバーズ,超カードゲーム,ガンダム'),

    ('DB-FB11', 'ブースターパック BRIGHTNESS OF HOPE', 'Booster Pack -BRIGHTNESS OF HOPE-',
     'Dragon Ball', 'dragon_ball', 'FB11', 'TCG', 'booster', 'active', 220, DATE '2026-09-12', 0, 24, 12,
     'FB-11,FB11,BRIGHTNESS OF HOPE',
     'スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ワンピース,ワンピースカード,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ヒーローズ,SDBH,ダイバーズ,超カードゲーム,ガンダム'),

    ('DB-FB12', 'ブースターパック REACH THE GOD', 'Booster Pack -REACH THE GOD-',
     'Dragon Ball', 'dragon_ball', 'FB12', 'TCG', 'booster', 'active', 220, DATE '2026-12-12', 0, 24, 12,
     'FB-12,FB12,REACH THE GOD',
     'スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ワンピース,ワンピースカード,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ヒーローズ,SDBH,ダイバーズ,超カードゲーム,ガンダム'),

    -- ====================================================================
    -- Dragon Ball フュージョンワールド — スタートデッキEX (FS-11, FS-12)
    -- ====================================================================

    ('DB-FS11', 'スタートデッキEX 進化の境地', 'Starter Deck EX -Evolution Mastery-',
     'Dragon Ball', 'dragon_ball', 'FS11', 'TCG', 'special', 'active', NULL, DATE '2026-03-14', 0, NULL, NULL,
     'FS-11,FS11,進化の境地',
     'スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ワンピース,ワンピースカード,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ヒーローズ,SDBH,ダイバーズ,超カードゲーム,ガンダム'),

    ('DB-FS12', 'スタートデッキEX 気の躍動', 'Starter Deck EX -Ki Surge-',
     'Dragon Ball', 'dragon_ball', 'FS12', 'TCG', 'special', 'active', NULL, DATE '2026-03-14', 0, NULL, NULL,
     'FS-12,FS12,気の躍動',
     'スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ワンピース,ワンピースカード,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ヒーローズ,SDBH,ダイバーズ,超カードゲーム,ガンダム'),

    -- ====================================================================
    -- Dragon Ball フュージョンワールド — STORY BOOSTER (FW-ST01)
    -- ====================================================================
    -- 注意: ONE PIECEのST-01と型番が似るが、product_codeがDB-接頭辞で分離。
    --       work_id制約(match_pid_with_work)でゲーム系列が分離されるため誤マッチなし。
    --       search_keywordsに"STORY BOOSTER"を入れて区別。

    ('DB-STBR01', 'STORY BOOSTER 01', 'STORY BOOSTER 01',
     'Dragon Ball', 'dragon_ball', 'STBR01', 'TCG', 'booster', 'active', NULL, DATE '2026-08-08', 0, NULL, NULL,
     'STBR01,STBR-01,STORY BOOSTER 01,STORY BOOSTER,ストーリーブースター',
     'スリーブ,プレイマット,カードケース,シングル,中古,オリパ,ワンピース,ワンピースカード,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ヒーローズ,SDBH,ダイバーズ,超カードゲーム,ガンダム,ST-01,ST01'),

    -- ====================================================================
    -- ドラゴンボールスーパーダイバーズ（別ゲーム・PO判断で登録）
    -- ====================================================================
    -- FWとは別ゲーム（アーケード筐体）。tcg_type は dragon_ball だが
    -- search_keywords に「ダイバーズ」「DIVERS」があり、FW商品は exclude に
    -- 「ダイバーズ」を持つため誤マッチしない。逆にダイバーズ側も FW固有語を除外。

    ('DB-DIVERS', 'ドラゴンボールスーパーダイバーズ', 'Dragon Ball Super Divers',
     'Dragon Ball', 'dragon_ball', 'DIVERS', 'TCG', 'special', 'active', NULL, DATE '2024-11-07', 0, NULL, NULL,
     'ダイバーズ,スーパーダイバーズ,DIVERS,超カードゲーム,アドバンスパック',
     'フュージョンワールド,FW,DBFW,FB,FS,ブースターパック,スタートデッキ,ワンピース,ワンピースカード,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ヒーローズ,SDBH,ガンダム,スリーブ,プレイマット'),

    -- ====================================================================
    -- ONE PIECE — プレミアムカードコレクション DAY'24
    -- ====================================================================
    -- 既存 DAY'25(OP-PCC-DAY25) と区別: search に "DAY24","DAY'24" を入れ、
    -- exclude に "DAY25","DAY'25" を入れて相互に誤マッチ防止。

    ('OP-PCC-DAY24', 'プレミアムカードコレクション -ONE PIECE DAY''24-', 'Premium Card Collection -ONE PIECE DAY''24-',
     'ONE PIECE', 'one_piece', 'PCC-DAY24', 'TCG', 'promo', 'active', NULL, NULL, 0, NULL, NULL,
     'PCC-DAY24,DAY24,DAY''24,OP07-109',
     'DAY25,DAY26,DAY''25,DAY''26,ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    -- ====================================================================
    -- ONE PIECE — プレミアムカードコレクション Nikeコラボエディション
    -- ====================================================================
    -- 固有識別子: Nike, ナイキ, P-099。他PCC商品と誤マッチしない。

    ('OP-PCC-NIKE', 'プレミアムカードコレクション -Nikeコラボエディション-', 'Premium Card Collection -Nike Collaboration Edition-',
     'ONE PIECE', 'one_piece', 'PCC-NIKE', 'TCG', 'promo', 'active', NULL, DATE '2026-09-04', 0, NULL, NULL,
     'PCC-NIKE,Nike,ナイキ,P-099,P099,Nikeコラボ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    -- ====================================================================
    -- ONE PIECE — ROUND1 プロモーションパック
    -- ====================================================================
    -- 収録カードは既存セットのカード番号(OP16-095等)だが、
    -- search_keywords にはセット型番を入れない（元セットと誤マッチするため）。
    -- 「ROUND1」「ラウンドワン」のみで特定。

    ('OP-PP-R1', 'ONE PIECEカードゲーム -ROUND1 プロモーションパック-', 'ONE PIECE Card Game -ROUND1 Promotion Pack-',
     'ONE PIECE', 'one_piece', 'PP-R1', 'TCG', 'promo', 'active', NULL, DATE '2026-07-18', 0, NULL, NULL,
     'ROUND1,ラウンドワン,ROUND ONE',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    -- ====================================================================
    -- ONE PIECE — 肉ルフィ P-159（週刊少年ジャンプ33号付録）
    -- ====================================================================
    -- 通称「肉ルフィ」がメッセージでの呼称。P-159 でも特定可能。
    -- OP-WSJ（ジャンプ付録カード全般）とは別商品として登録。

    ('OP-P159', 'モンキー・D・ルフィ P-159 肉ルフィ', 'Monkey D. Luffy P-159',
     'ONE PIECE', 'one_piece', 'P-159', 'TCG', 'promo', 'active', NULL, DATE '2026-07-13', 0, NULL, NULL,
     'P-159,P159,肉ルフィ',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    -- ====================================================================
    -- ONE PIECE — CHOPPER's 1（コミック付録プロモカード）
    -- ====================================================================
    -- カード番号 EB02-003 は EB-02 セットのカードだが、コミック付録として別商品。
    -- search に EB02-003 を入れず、CHOPPER's 固有名で特定。
    -- EB02-003 を入れると EB-02(アニメ25thコレクション)と誤マッチする。

    ('OP-CHP01', 'ONE PIECE CHOPPER''s 1 プロモカード', 'ONE PIECE CHOPPER''s 1 Promo Card',
     'ONE PIECE', 'one_piece', 'CHP01', 'TCG', 'promo', 'active', NULL, DATE '2026-04-23', 0, NULL, NULL,
     'CHOPPER''s,チョッパーズ,CHP01',
     'EB-02,EB02,アニメ25th,ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    -- ====================================================================
    -- ONE PIECE — ナツコミ 2026 メタキラカード
    -- ====================================================================

    ('OP-NATSU26', 'ナツコミ 2026 メタキラカード ワンピース ルフィ', 'Natsucomi 2026 Metallic Card One Piece Luffy',
     'ONE PIECE', 'one_piece', 'NATSU26', 'TCG', 'promo', 'active', NULL, DATE '2026-07-01', 0, NULL, NULL,
     'ナツコミ,NATSU,メタキラ,メタキラカード',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    -- ====================================================================
    -- ONE PIECE — EMOTION プロモカード P-041
    -- ====================================================================

    ('OP-P041', 'モンキー・D・ルフィ P-041 EMOTION', 'Monkey D. Luffy P-041 EMOTION',
     'ONE PIECE', 'one_piece', 'P-041', 'TCG', 'promo', 'active', NULL, DATE '2024-08-12', 0, NULL, NULL,
     'P-041,P041,EMOTION,エモーション',
     'ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    -- ====================================================================
    -- ONE PIECE — 2nd ANNIVERSARY COMPLETE GUIDE（書籍＋プロモ）
    -- ====================================================================
    -- 既存 OP-2ANNY (2nd Anniversary SET) と区別。
    -- search に "COMPLETE GUIDE","コンプリートガイド" を入れて SET と分離。
    -- exclude に "2nd ANNIVERSARY SET","2ANNY" を入れて誤マッチ防止。

    ('OP-2ANNY-GD', '2nd ANNIVERSARY COMPLETE GUIDE', 'ONE PIECE CARD GAME 2nd ANNIVERSARY COMPLETE GUIDE',
     'ONE PIECE', 'one_piece', '2ANNY-GD', 'TCG', 'promo', 'active', NULL, DATE '2024-07-04', 0, NULL, NULL,
     'COMPLETE GUIDE,コンプリートガイド,2nd ANNIVERSARY GUIDE,OP05-067,OP06-101',
     '2nd ANNIVERSARY SET,2ANNY,ドラゴンボール,ポケモン,ポケモンカード,遊戯王,デュエマ,ヴァイス,バトスピ,ガンダム,デジモン,ホロライブ,ロルカナ,ユニオンアリーナ,SDBH,ヒーローズ,スリーブ,プレイマット,カードケース,シングル,中古,オリパ'),

    -- ====================================================================
    -- ONE PIECE — Vジャンプ 2026年10月号 麦わらの一味3人の最強セット
    -- ====================================================================
    -- 既存 OP-VJ (Vジャンプ付録カード全般) と区別。
    -- P-110 はこの商品固有のプロモ番号。
    -- OP16-053, OP09-105 は既存セットのカード番号のため search に入れない。

    ('OP-VJ2610', 'Vジャンプ 2026年10月号 麦わらの一味3人の最強セット', 'V-Jump Oct 2026 Straw Hat Trio Set',
     'ONE PIECE', 'one_piece', 'VJ2610', 'TCG', 'promo', 'active', NULL, DATE '2026-08-21', 0, NULL, NULL,
     'VJ2610,P-110,P110,最強セット,麦わらの一味3人',
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
