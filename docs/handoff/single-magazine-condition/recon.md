# recon: シングル系にも状態「雑誌付き」を使えるようにする前の現状

一行説明: 本付き・雑誌付きのカードが、本が売り切れても残っているカードと別の行で出るよう、状態の辞書に「シングル系用の雑誌付き」を足せるかを調べた記録。
親: [magazine-promo-condition/recon.md](../magazine-promo-condition/recon.md)（プロモパック系に雑誌付きを足した前例）／ [docs/specs/README.md](../../specs/README.md)

基準: origin/main 570d70c4a。本番の値は reader 鍵（ai_ro）の読み取りで 2026-10-25 に取得。原文・仕入元名の生出力は社外秘の保管場所（CC報告ファイル-keep/shime-auto-check/daily/20261025_1200/state_split/recon/）に置き、ここは件数と仕組みだけを書く。
調べは Sonnet（2026-10-25）。DB・マスタ・コードへの書き込みなし。

## 0. 既存 ADR の検索

- 【事実】ADR-1007（記録 SQL）・ADR-1021（Bulk CN0014）・ADR-1023（状態の価値順）・ADR-1031（群 single / promo_pack）・ADR-1035（状態ごとの単位）・ADR-1036 が関連。「雑誌付き」の語は ADR 本文に無く、`docs/handoff/magazine-promo-condition/` にある。FEATURE-INDEX.md も該当なし。
- 【事実】前例 `docs/handoff/magazine-promo-condition/design.md:5` は「既存の群に1行足すだけなので新 ADR は作らない」と記す。同 `:24` はシングル系の雑誌付き（商品 424591 CHOPPER's）を「群が違う」として明示的に対象外にした。

## 置き場所とtier

- 【事実】`docs/STANDARD-WORKFLOW.md` §1.8: 新テーマは一式、既存テーマの拡張は既存テーマの履歴に追記、軽微は台帳+PR。§2（80-84行付近）: recon は docs/handoff/<仕事名>/recon.md、design は外部事例節と受け入れ基準表（検証方法つき）、PR 本文に `### 標準ワークフロー確認`。§1.7: design の末尾は「## 維持の仕組み」。
- 【事実】`docs/specs/README.md` は仕様書の索引で、仕事別の recon/design は docs/handoff にある。よって置き場所は `docs/handoff/single-magazine-condition/`（本ファイル）。仕様書を新設する場合のみ specs/README.md に追記。
- 【推測】tier は「既存テーマ（雑誌付き）の拡張」で、前例どおり ADR なしの B 類（ADR-1015: Opus 審査 APPROVE で足りる。記録は design.md の審査節）。ただし「別の群へ適用を広げる」は前例（同じ群に1行）より一段広く、ADR 要否は親の判断が要る。【未確認】

## file:line 引用表

| 事実 | 出典 |
|---|---|
| 状態の取り出しは区分→群で絞る。当たりなしはシングル群で Single(R7)、プロモ群で 未開封(R8) | `backend/app/services/gemini_raw_copy_v102_product_first.py:641`, `:649`, `:676` |
| 群の一覧 | `backend/app/services/tcg_analyzer_svc.py:653` |
| 群内で複数当たりなら価値の低い方（value_rank 大）を採る | `backend/app/services/tcg_analyzer_svc.py:861`, `:882` |
| 群ごとの絞り込み | `backend/app/services/line_analysis_v102_svc.py:217` |
| 群内の canonical で condition_id を引く。PSA10 は single(55)と promo_pack(62)に同名で並存＝同名は前例あり | `backend/app/services/line_analysis_v102_svc.py:656` |
| 同じ商品でも (product_id, condition_id) 単位で分かれる＝結合キーは condition_id | `backend/app/services/tcg_analyzer_svc.py:1964` |
| 単位表は canonical をキーにした辞書 | `backend/app/services/gemini_raw_copy_v102_product_first.py:155`, `:379` |
| 状態の語から単位を決め直す・上書きする規則 | `backend/app/services/gemini_raw_copy_v102_product_first.py:745`, `:77` |
| 並び順の順位表も canonical キー（同名は小さい id が勝つ） | `backend/app/services/tcg_result_order.py:11`, `:18` |
| 出力名は canonical（日本語）そのもの | `backend/app/services/tcg_distribution_svc.py:326` |
| バッジは12値の完全一致、未知は灰色 | `frontend/src/features/inventory/conditionBadge.ts` |
| 前例の INSERT（CN0025 雑誌付き・promo_pack・rank4・単位17） | `docs/handoff/magazine-promo-condition/data/02_apply.sql:20` |
| 事前確認は「同じ群に同名なし」 | `docs/handoff/magazine-promo-condition/data/01_precheck.sql:19` |
| CN0026 はテストの仮データ名としてのみ使用（本番 line_conditions に無い） | `backend/tests/test_supply_category.py:34` |
| 言い回しの既存テスト（NJ021 本付き / NJ022 雑誌付き） | `backend/tests/test_tcg_keyword_matching.py:370` |

## 3. 選択肢

【事実】本番の状態は27行。シングル群は PSA10(55) PSA9(56) PSA8(57) PSA7以下(58) Single(59, rank5)。雑誌付き(68)は promo_pack・priority2・REGEX `雑誌[\s　]*(付き|つき)`・単位17(Booklet)・rank4。

- 案A（シングル群に同名「雑誌付き」を1行足す。記録SQLのみ、コード変更なし）
  - 【事実】condition_id が 68 と別になるので、同じ商品でカードだけ（Single）と本付き（新id）が別の組に分かれ、本付きだけ完売でもカードの在庫が残る（K1の土台）。PSA10 の同名並存という前例あり。
  - 【事実】注意点1: 単位表は canonical キーなので、新行も 68 の単位 Booklet を引く。名前に「雑誌プロモ付き 1枚」のようなカードがあると単位が冊に上書きされる恐れ。試算では、変わる45行のうち24行は保存済みの単位が Booklet ではない（None）。単位の扱いは決めが要る。
  - 【事実】注意点2: 並び順の順位表も canonical キーで、同名は小さい id(68)の promo_pack 位置が勝つ。シングル群内の並びは別途確認が要る。
  - 【事実】注意点3: コード CN0025 は使用済み。次は CN0026 以降（本番に無い。テストの仮データ名と同じ字面で衝突はしないが、【未確認】Supply との整合）。
- 案B（68 の適用を広げる）
  - 【事実】68 は promo_pack の行。別の群のカードに効かせるにはコード（`backend/app/services/gemini_raw_copy_v102_product_first.py:641` と `backend/app/services/tcg_analyzer_svc.py:653`, `:882` 付近）の変更が要り、言い回しを広げると promo_pack 側の判定も動く。試算では promo 側の「本付き」当たりは0行なので現データでは変化なしだが、K3 を保証する仕組みにならない。
- 結合キー: 【事実】condition_id（名前ではない）。案Aは別idなので分かれる。

## 4. 届け先・画面

- 【事実】出力名は canonical そのもの（tcg_distribution_svc.py:326）。「雑誌付き」は既に出力される名前なので、新しい名前は増えない。
- 【事実】`frontend/src/features/inventory/conditionBadge.ts` は完全一致で未知は灰色。「雑誌付き」は12値に入っていない（2026-10-25 Opus が grep で確認、design.md 対象外の表）。（同ファイル・design.md・conditionBadge.test.ts は3点同時更新の決まり）
- 【事実】在庫一覧 GAS は別リポジトリ（shingo-ops/tcg-client-viewer）。conditionClass が conditionBadge.ts の写しで未知は灰色。【未確認】リポジトリ内には無く、本調査では中身を読んでいない。
- 【事実】状態名の翻訳キーはフロント ja.json/en.json に見つからなかった（未開封は別キー ja.json:1539, 2882, 2894）。line_conditions に英語名列は無い。

## 5. 試算（読み取りのみ。sim_result.txt, sim.py）

基準: origin/main のコードの `_resolve_condition` を手元で呼ぶ。直近90日の v102 行（シングル系 1395 行・プロモパック系 968 行）。
追加する行: シングル群・priority2・REGEX `雑誌(プロモ)?[\s　]*(付き|つき)|本[\s　]*(付き|つき)|付録[\s　]*(付き|つき)`。

- 【事実】再現性: シングル系は今のマスタで再計算した状態が保存値と 1395/1395 一致。プロモパック系は 930/968 一致（不一致38は Error・FLAG_SINGLE など、今回の変更と無関係の古い行。今回の追加でさらに動いた行は0）。
- 【事実】K3: プロモパック系で変わる行 0/968。案Bで68を同じ言い回しに広げても 0/968。
- 【事実】K4: シングル系で変わる行は45/1395、全部 Single→雑誌付き。他の遷移は0。rank を 6 にしても 0 にしても同じ45行。
- 【事実】変わる45行の内訳: CHOPPER's 1 プロモカード(424591) 37行、ONE PIECE学園 10(466058) 8行。当たり語は「雑誌プロモ付き」29行・「本付き」8行・「雑誌付き」8行。現行（is_current）で変わるのは5行。
- 【事実】K1: CHOPPER's は 424591 の全213行中37行が変わり、176行はそのまま Single。現行行14のうち完売1行（雑誌プロモ付き 完売）と在庫3行が雑誌付きに変わり、残り10行は Single のまま。
- 【事実】誤爆探索: 「本付き」に当たった8行はすべて、商品名の直後に「本付き」と続く書き方。「日本付き」等の熟語の一部への当たりは0。
- 【事実】単位: 変わる45行のうち24行は保存済みの単位が空（None）、21行が Booklet。案Aでは単位表が Booklet を引くため、空の24行は冊に変わりうる。
- 【事実】ONE PIECE学園10巻の、雑誌付きと書かれた本の行 (466058) の8行もシングル系で雑誌付きに変わる。これはカードではなく本の商品。
- 【推測】学園10巻を雑誌付きにしてよいかは仕様の判断（K2は CHOPPER's の話）。

## 不明点リスト

| # | 不明点 | 区分 |
|---|---|---|
| 1 | ADR を作るか（別群への広げ方が前例より一段広い） | 【未確認】判断 |
| 2 | 新行の単位（NULL のままか Booklet か）と、単位表が canonical キーである問題の扱い | 【未確認】判断 |
| 3 | 並び順の順位表（同名は id68 が勝つ）がシングル群の表示順に与える影響 | 【未確認】 |
| 4 | 学園10巻 8行を雑誌付きにしてよいか | 【未確認】判断 |
| 5 | conditionBadge.ts に「雑誌付き」の色が入っているか、GAS 側の写し | 【未確認】 |
| 6 | 新行の value_rank（試算は 6/0 とも同結果）。複数当たり行（PSA10 + 雑誌付き）の優先は今データで0行 | 【未確認】 |

## 補足

- 生出力: sim_result.txt, sim_chopper.txt, changed_*.json, rows_*.jsonl, line_conditions_now.tsv（上記保管場所）。
