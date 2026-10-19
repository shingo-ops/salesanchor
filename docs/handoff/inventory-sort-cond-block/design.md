# 設計: 並び替えは「商品 → 状態」のまとまりの中だけ（在庫表・閲覧ページ・GAS 在庫一覧）

版: 第2版（2026-10-19、Opus。第1版の審査 REVISE 指摘1〜6を反映 /tmp/CC報告ファイル/inventory-sort-cond-block/review-design.md）

## 1. 目的（PO の言葉）
PO（2026-10-19）「価格の安い順に並び替えると状態も並び替わってしまう、商品は発売日順で固定、状態も並びは固定で商品ブロック、状態ブロック内で並び替えしてほしい」→ Opus の確認文（商品は発売日の新しい順で固定、商品の中の状態の並びは今の既定＝価値順で固定、価格・数量などの並び替えは「同じ商品・同じ状態」のまとまりの中だけ。アプリ在庫表・閲覧ページ・GAS に適用）に PO「y」。

## 2. 現在地（recon。基準 origin/main 837245a2d、生出力 /tmp/CC報告ファイル/inventory-sort-cond-block/）
- アプリ: backend/app/routers/inventory_offers.py:264-279 `_build_view_order_by`。価格の安い順は `ORDER BY 発売日 DESC NULLS LAST, english_title, japanese_title, product_id, d.price_num ASC NULLS LAST, d.sort_ord ASC`（:279）。状態の価値順は sort_ord（backend/app/services/tcg_distribution_svc.py:348、順の式は backend/app/services/tcg_result_order.py:36-42 = 発売日→商品→状態の価値順→状態名→価格）の中にしかなく、選んだ列より後ろ。＝原因。
- 閲覧ページ: frontend/src/pages/viewer/viewerFilter.ts:172-193 `sortRows`。発売日→英語名→日本語名→選んだ列→idx（サーバーの順＝sort_ord）。同じ原因。
- GAS: ~/CC報告ファイル-keep/inventory-block-pill-gas/gas/test_stage/index.html:1393-1453（prod_stage と同一）。発売日→英語名→日本語名→選んだ列→0（安定ソートでシートの順が残る）。同じ原因。シートに状態の順位の列は無い（14列）。
- ADR: ADR-1014 :40-48・:70-76（商品のまとまり）・:98-104（印の単位＝商品・ステータス・状態）。ADR-1023 :65-73（value_rank を並び順の正本に使う。状態の中は価格の安い順）。前便の設計 docs/handoff/inventory-sort-block-order/design.md。

## 3. 方針（なぜこの方法か）
状態の順の正本は sort_ord（ADR-1023 の価値順がサーバーで1か所にだけ入っている）。新しい順位の列や表は作らず（SSOT 遵守・データを分散しない）、**「同じ商品・同じ状態の行のうち、いちばん小さい元の順」＝状態ブロック番号** を各画面でその場で求め、商品キーと選んだ列の間に挟む。
- sort_ord の式は 商品→状態の価値順→状態名 の順なので、同じ商品の中で状態ブロック番号の小さい順＝今の既定の状態の並び（価値順）になる。
- 却下案: (a) value_rank を API・シートに新しい列として出す → 列の追加（GAS 14列固定 ADR-1014 :47）と順位の写しが増える。(b) 状態名の文字順 → 価値順と違う。

## 4. 変更（変更前 → 変更後）
### 4-1. アプリ（backend/app/routers/inventory_offers.py）
- rows_x（:299 `ctes.append(f"rows_x AS (SELECT x.*, tm.code AS work_code, pp.category AS category FROM rows_main x {join})")`）に1列足す:
  `MIN(x.sort_ord) OVER (PARTITION BY x.product_id, x.condition) AS cond_block`
  rows_nx・rows_f・rows_pg は rows_x 由来なので3枝（total/page/facet）の列数は揃ったまま。rows_xp（merge 時の絞り込み候補用）には足さない（出力列に出ないため）。実装者は UNION の列数・型が一致することを PG 試験で確認する。
- `_build_view_order_by` の :279 を
  変更前 `return f"ORDER BY {group}, {sort_col} {order_dir} NULLS LAST, d.sort_ord ASC"`
  変更後 `return f"ORDER BY {group}, d.cond_block ASC, {sort_col} {order_dir} NULLS LAST, d.sort_ord ASC"`
  name（:270-271）と release_date（:277-278）の枝は変えない（すでに状態は sort_ord の順）。
- cond_block は応答に出ない（`_project_inventory_rows` :153-185 が InventoryRow の項目を1つずつ指定して作るため。審査で確認）。API の項目・openapi.json は変えない。
- `_build_view_order_by` の docstring を新しい順に、`_build_inventory_view_sql` の docstring の列の説明（:290）に cond_block を足す。
### 4-1b. 試験（backend/tests）
- test_inventory_distribution_rows_pg.py `_old_three_statements` の `rows_sql`（:318-322）の SELECT に、本番と同じ `, MIN(x.sort_ord) OVER (PARTITION BY x.product_id, x.condition) AS cond_block` を足す（方式 (a)。旧側にも同じ列を持たせ、:379-381・:423-438 の `new == old` をそのまま成り立たせる）。facets は DISTINCT 5列なので影響なし。
- 同ファイルに S1・S2 の試験を新設。
- `_no_sort_ord` に cond_block を追加（CI で判明、Opus 承認。cond_block は MIN(sort_ord) なので sort_ord と同じ理由で窓の内外で番号が変わる）。
- test_inventory_distribution_rows.py: 変わるのは `_VIEW_SQL_BEFORE`（:117-120、長さと SHA256。既定の並びでも rows_x が変わるため）と期待文字列 :134-135 だけ。`_GOLDEN`（:124-129）と :132-133・:136-137・:142 は変わらない。これら以外が変わったら止めて Opus に報告。
### 4-2. 閲覧ページ（frontend/src/pages/viewer/viewerFilter.ts sortRows）
- else 枝で sortKey !== "release_date" のとき、並べる前に `release_date + "\u0000" + english_title + "\u0000" + japanese_title + "\u0000" + condition` をキーに渡された rows の最小 idx を Map で求め、日本語名のキーの次・選んだ列の前に「状態ブロック番号の昇順」のキーを足す。name・release_date の枝は変えない。
### 4-3. GAS（test_stage/index.html と prod_stage/index.html、同一の変更）
- sort の前に、filtered の位置（シートの順を保ったまま）で同じキー（発売日・英語名・日本語名・状態）の最小位置を求める。比較関数の (b2) 日本語名の後、(c) の前（発売日の列のときは入れない）に状態ブロック番号の昇順を足す。比較関数で位置を引けるよう、sort 前に行→元の位置を持たせる（配列を変更しない方法。例: 行ごとの索引の配列を並べ替えてから行に戻す）。
- 塗り（前便）・並び（前便）はそのまま。deploy_test.sh の期待版を 24 に更新、deploy_prod.sh は 17 のまま。
- 本番 GAS への出し方: 本番は版17（並び替えの前便・塗り・本便のどれも未反映）。テスト版24→25 に本便を載せ、PO がテスト版で3つ（商品ブロック内の並び・塗り・状態ブロック）を目視してから、本番へ3つを一度に出す（PO の ! 実行）。本番に出す直前に `clasp deployments` で本番の版が17のままか確かめ、違えば止める。
### 4-4. 文書
- ADR-1014 に「改訂 2026-10-19（5）: 商品の中は状態のまとまり（価値順・ADR-1023）を固定し、選んだ列はその中だけで並べる。状態の列を選んだときは商品の中の状態の並びは変わらない」を追記。既知の差（:75・:91 と同じ書き方）として「閲覧ページと GAS のまとまりのキーには product_id が無い（発売日・英語名・日本語名・状態）」「GAS の比較は大文字・小文字を同じとみなすが、状態ブロックの Map のキーでは別になる」を書く。docs/adr/README.md 再生成。
- docs/handoff/inventory-sort-cond-block/recon.md・design.md（本書）。

## 5. 触らない範囲
sort_ord の式（tcg_result_order.py）、印（__badge_* の PARTITION）、API の項目・辞書・DB・migrations・deploy.yml・scripts・nginx、並びメニューの選択肢、name と release_date の並び。

## 6. 受入条件
| 基準 | 検証方法 |
|---|---|
| S1 アプリ: 価格の安い順で、同じ商品の中の状態の順が既定（発売日の新しい順）と同じ | PG 試験: 同じ商品に状態2つ（価値順 A<B、A の価格が B より高い）を入れ、unit_price asc で A の行が B の行より前、各状態の中は価格の昇順 |
| S2 アプリ: 数量・投稿日時・種別でも同じ | PG 試験で quantity desc を1本 |
| S3 アプリ: name・release_date の並びは変更前と同じ | 既存の試験が通る（pg の新旧同一は 4-1b の旧側修正込み）。更新するのは 4-1b に挙げた `_VIEW_SQL_BEFORE` と :134-135 だけ |
| S4 閲覧ページ: S1 と同じ | viewerFilter.test.ts に同じ形のケース（idx で状態の順 A<B、価格は A が高い）を足し、unit_price asc で A が先 |
| S5 GAS: 閲覧ページと同じ順 | 入力 /tmp/CC報告ファイル/inventory-block-pill-gas/fresh24/sheet.csv（無ければ ~/CC報告ファイル-keep/inventory-sort-cond-block/ に写しを取ってから使う）。新しい GAS ステージの並び処理を取り出したものと、新しい viewerFilter.sortRows（行の順を idx とする）を手元の node で、並び4種（価格安い順・在庫多い順・投稿新しい順・新しい順）× 全行で比べ、順の差 0。ほかに乱数1000ケース（題名は小文字英字のみ・数字なしで作る）。実データで差が出たら、差の全行が ADR-1014:75 の既知の差（文字の比べ方・空欄の扱い）かを分類して報告し、それ以外の差が 0 なら合格。加えて「同じ商品の中の状態の出現順」が新しい順と同じこと（差 0）を全商品で確かめる |
| S6 本番: 在庫表で「価格が安い順」を選ぶと、商品の中で状態の並びが「新しい順」のときと同じ | Deploy 後、reader 鍵の SELECT で同じ SQL を本番の行に流し、商品ごとの状態の出現順が既定と一致（差 0）。PO 目視 |
| S7 CI 必須チェックが全緑 | gh pr checks |

## 7. リスクと戻し方
- 窓関数を1つ足すので在庫表の応答が遅くなる恐れ → 本番 reader で変更前後の実行時間を測り、中央値の増加が 100ms 以内であること（超えたら停止して相談）。
- 戻し方: PR の revert。GAS は clasp の前の版へ redeploy（deploy スクリプトの記録した版番号）。

## 外部・過去事例の参照と我々への応用
- 外部事例: 該当なし。画面内の並び順の規則で、外部の数値で成否が決まる性質ではない。
- 過去事例（自社）: 前便 docs/handoff/inventory-sort-block-order/design.md（商品の順を固定、#4505 系）。同じ2か所＋GAS を同じ形で直し、試験で固定した。
- 応用: 今回も在庫表・閲覧ページ・GAS の3か所を同じ規則で直す。

## 維持の仕組み
- 守り手: backend/tests/test_inventory_distribution_rows_pg.py（S1・S2。CI の pytest）、backend/tests/test_inventory_distribution_rows.py（ORDER BY の式を固定）、frontend/src/pages/viewer/viewerFilter.test.ts（S4）。
- 正本: ADR-1014 改訂（5）。区分は ADR-1015 の A。
ADR-1014 改訂（5）を正本にし、アプリ・閲覧ページの試験（S1〜S4）で守る。GAS はリポジトリ外のため、アプリと同じ規則であることをステージのコメントに ADR 番号で残す。
審査: 第1版 REVISE（review-design.md）→ 第2版 APPROVE 条件付き（review-design-v2.md）→ 条件のS5の1文を反映済み
