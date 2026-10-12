# recon: 状態の語で決まった状態の単位を優先する／分類「セット系」（便SU）

基準 origin/main（2026-10-11）。本番は読み取りのみ。生出力（手元・社外秘）: /tmp/CC報告ファイル/unit-residual5/（round1〜round6）、/tmp/CC報告ファイル/v102-unit-state-set/。

## 既存 ADR
- ADR-158（docs/adr/ADR-158-product-level-supersession.md、現行行の決め方）、ADR-157（docs/adr/ADR-157-buyback-price-logger.md、買取価格）、ADR-1007（docs/adr/ADR-1007-migration-structure-only-run-once.md、値は data SQL）。docs/adr を 単位・分類・kubun・セット で git grep → 状態から単位を決める・分類セット系の ADR は無し。

## 単位・状態の決まり方（v102、origin/main）
- 単位の別名: backend/app/services/gemini_raw_copy_v102_product_first.py:422-449 find_unit_product_first（件の行の別名。見つからなければ None）。
- 状態: backend/app/services/gemini_raw_copy_v102_product_first.py:496-505 _resolve_condition。商品が箱系かつ単位区分が BOX_RECHECK_UNIT_KUBUNS（空・不明・条件つき・複合・数量専用、同:58-60）なら箱系でやり直し、語が無ければ backend/app/services/tcg_analyzer_svc.py:860-866 の R4 で Sealed box（basis R4:単位既定）。語で決まると R1〜R3。
- 単位の置き換え: backend/app/services/gemini_raw_copy_v102_product_first.py:569-573。単位が無い、または箱系かつ「条件つき」のときだけ状態の単位（line_conditions.unit_id、同:110-115）にする。basis は見ていない。
- 商品の分類: backend/app/services/tcg_analyzer_svc.py:157-175 load_product_kubun_type_map（products.product_category_id → tcg_product_categories.kubun_type）。表は2行（1 PC_BOX 箱系、2 PC_SINGLE シングル系）、id は identity、kubun_type は自由文字列（migrations/20260902_110000_tcg_classification_masters.sql:65,73）。管理画面 API backend/app/routers/super_admin_product_categories.py:134。
- 便BB の対象: backend/app/services/v102_buyback_unit_svc.py:133-137 is_candidate（分類を見ていない）。件の product_category は backend/app/services/gemini_raw_copy_v101.py:943 で件に写される。

## 観測した誤り（本番 v102 現行行 1,090 件、2026-10-11 読み取り）
- 30th CELEBRATION 22,000円（よこ）: 件の行「ペリ無し統一箱・パック右上…斜め切り取り」の「パック」を単位に採り Pack。状態は Opened box（R3:ペリ無）で正しい。正解 Opened box／Box。「統一箱」の「箱」は境界判定（gemini_raw_copy_v102_product_first.py:330-341）で採られない。
- 状態の単位と単位が違う件 22件（unit-residual5/round2/q2b.out）: R1〜R3 で決まった状態 13件（上の1件＋「2個@80,000円（検品のため開封済み）」「10個@58,000円 検品のため開封済み」の個 12件、いずれも商品未特定・配信外）、R4 の 440301 Set 8件、SOLDOUT_INHERIT 1件。
- 個 12件の原文: 同じ投稿内で同じ商品が「10BOX@59,800円(検品のため一度開封済み)」と書かれ、商品は箱の商品（プレシャスコレクターボックス・クラシック）。
- 440301「MEGA 30th CELEBRATION カードセット（9種セット）」: 公式（pokemoncenter-online.com 9900000008291、10,800円・2026-10-16）に実在する9種一括の商品。原文は全件「カードセット(9種セット)」「Nセット@価格」。商品の分類は箱系。単位 Set の kubun は「複合」（line_units id 13・UN0005）。
- 「セット」の単位の現行行 84件: 商品未特定 72、440301 8、他4（207・208 シングル系、420530 分類なし、465998 シングル系）。箱系は 440301 だけ。

## 読み手への影響
- unit_basis に from_condition・reason state_word、または from_category セット系 が増える（JSON の追加キー）。condition_basis は変えない。
- 分類 セット系 の行が無ければ（本番投入前）コードの動きは「状態の語による単位優先」以外は不変。
