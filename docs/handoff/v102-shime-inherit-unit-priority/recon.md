# recon: 規則12（〆の状態の引き継ぎ）で、〆の件に単位語があればその状態を優先する（便3b）

- 調べた日: 2026-10-11。基準 origin/main 2acc5b7bb（#4136 マージ後）。
- 調査: コードは Sonnet、本番は Opus（SELECT と読み取り専用の使い捨てコンテナのみ）。社外秘の行ごとの記録は手元（`~/CC報告ファイル-keep/session-20261011-shime-ref/`）。

## 0. 既存 ADR の検索
- 前便と同じ（ADR-158 のみ）。前便: `docs/handoff/v102-shime-direct-inherit/`（#4136、規則12）。

## 1. PO の要求
- 2026-10-11 Opus の報告「〆の行に『ボックス』等が書いてあっても状態が語で決まったと扱われず、引き継いでしまう恐れ（未確認）」に対し、PO「状態がある場合は状態を優先　y」。

## 2. 今の作り（事実）
- 状態の決定 `backend/app/services/tcg_analyzer_svc.py:804-904` `resolve_condition_v2`。単位の区分が箱系大→Case、箱系→Sealed box（`R4:単位既定`、:860-866）、パック系→Searched pack（`R5:パック既定`、:871-884）。どれも状態の語ではないので `condition_decided_by_word` は False（`backend/app/services/gemini_raw_copy_v102_soldout_ref.py:33-40`）。
- `R4:単位既定` は、行に箱の単位語があったときと、箱系の商品で単位が見つからず箱系に強制したとき（`backend/app/services/gemini_raw_copy_v102_product_first.py:499-504`）の両方で同じ文字列になる。basis だけでは区別できない。
- 件 dict の `unit_basis`（`backend/app/services/gemini_raw_copy_v102_product_first.py:408,418,449,573`）: 単位語が見つかれば `alias` に語、見つからなければ None。状態から単位を決め直したときは `from_condition` が付く（:567-574）。「件の行の文字に単位語があった」＝ `alias is not None` かつ `from_condition` なし。
- 単位語は、隣が同じ文字種の文字なら採らない（`_edge_blocks`、:330-335）。商品の検索ワードの範囲内の語も除く（:411-416）。例: 「メガドリームカートン 〆」のカートンは採られない。

## 3. 事実の測定
### 3-1. 〆の件の単位語（本番イメージの使い捨てコンテナ、読み取り専用、実コードの `find_unit_product_first`）
- 完売の件 899 件のうち、件の行に単位語あり 298 件、例外 0。
- 測定の限界: 価格の行は「価格の形の最初の行」で代用、役割の付け直し（F1/F3/F5）なし、chosen_product_id は保存済みの商品。
### 3-2. 規則12で引き継ぐ 56 件（#4136 の等価確認）との突き合わせ
- 単位語あり 15 件。
  - 13 件は単位語が BOX（箱系）で、引き継ぐ状態は Sealed box（箱系）＝単位語どおりの状態。v102 では〆の件そのものが Sealed box（`R4:単位既定`）になるので、在庫の Sealed box と同じ組になり、引き継がなくても在庫は外れる（`backend/app/services/tcg_analyzer_svc.py:1847-1852` の組単位）。
  - 2 件は単位語と違う状態を引き継ぐ：「EB-05 BOX 〆」→ FLAG_SINGLE、「〆 15個@11500 完売中」（個＝条件つき）→ FLAG_SINGLE。
- 12f の定義（`from_condition` があれば単位語なし扱い）で数え直すと、56 件のうち 12f が成立するのは 14 件（BOX の 14 件。「EB-05 BOX 〆」を含む）。「〆 15個@11500 完売中」は単位語「個」から状態を決め直している（from_condition = Sealed box）ので 12f は成立せず、今どおり FLAG_SINGLE の在庫（同じ「15個」の行）を引き継ぐ。原文上もその在庫への〆で正しい。
### 3-3. 追加の読み込みの時間
- `_SOLD_ITEMS_SQL` を投稿数が最多の仕入元の直近 40 投稿で EXPLAIN ANALYZE：33.8 ms（本番、読み取りのみ）。抽出タスク全体は 9〜47 秒（デプロイ後のログ5件）。
