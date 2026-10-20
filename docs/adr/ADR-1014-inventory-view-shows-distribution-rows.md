# ADR-1014: 在庫表は LINE 解析の配信行を出す

**Status**: Accepted  
**Date**: 2026-10-13  
**Author**: Hikky-dev  
**PO**: shingo-ops

---

## What（何を）

`/inventory`（在庫表）が表示する行を、`public.inventory` ではなく LINE 解析の「配信行」（`distribution_rows_sql`）に切り替える。

- 配信行（GAS 出力と在庫表）の定義は `backend/app/services/tcg_distribution_svc.py` の `distribution_rows_sql` の1か所だけ。`inventory_offers.py` に配信の WHERE を書かない。配信プレビューの件数は変更前の問い合わせを残している（products を結合しないため）。状態の条件だけ `_condition_filter` を共有する。件数と出力のずれは `test_tcg_condition_review.py` の output_count と len(fetch_output_rows) の比較を CI が止める。
- 同じ投稿・同じ商品・同じ状態（`cr.condition_id` / `cr.basis`）の行は、`merge_same_post`（既定 OFF。2026-10-14 改訂で ON から変更）でまとめて表示する。ユーザー別設定（`/me/inventory-filters`）で切り替える。
- 在庫表の列に備考（`note_ja`）と発送（`ship_ja`）を足す。状態・形態は canonical の値をそのまま出す。
- 行 ID は文字列（`InventoryRow.id: str`）。

## Why（なぜ）

ADR-093 は「`/inventory` は `public.inventory` を表示する」と定めたが、利用者が見たいのは GAS 配信と同じ LINE 解析の結果である。2つの正本があると行数・内容が食い違うため、配信行（GAS 出力と在庫表）の定義を1か所に集める。

## Scope

- 対象: `backend/app/services/tcg_distribution_svc.py`、`backend/app/routers/inventory_offers.py`、`backend/app/routers/me_inventory_filters.py`、`backend/app/schemas/inventory_offers.py`、`frontend/src/pages/inventory/InventoryPage.tsx`、ja/en ロケール。
- `fetch_output_rows` / `fetch_preview_data` の引数・GAS 出力列（14列）は変えない。
- 対象外: migrations、deploy.yml、本番 scripts。

## 置き換える決定

ADR-093「/inventory は public.inventory を表示する」を本 ADR が置き換える（ADR-093 の他の部分は有効）。

## 改訂 2026-10-14（便1: 在庫表と GAS 在庫一覧の揃え）

- まとめ（`merge_same_post`）の既定を OFF にした。保存済みの設定（`user_inventory_filters.filters`）は書き換えない。true を保存済みの人は ON のまま、キーが無い人は OFF になる。
- Sold out の除外を配信行の定義に入れた。`tcg_distribution_svc._sold_out_filter()` の1か所に判定を置き（`ar.` の別名が前提。status の前後の空白と大文字小文字を無視し 'sold out' / 'soldout' を除く）、dist_base と配信プレビューの件数クエリの両方が使う。
- 並び替えの第1キーを英語タイトルにした（GAS 方式）。タイトル列を並べるときは英語タイトルの昇降を切り替える。
- 在庫表に「24時間以内」(`fresh_only`、既定 ON、画面側のみ・保存しない)を足した。窓は `FRESH_WINDOW_HOURS = 24`。

## 改訂 2026-10-18（在庫表の既定の並びを発売日の早い順・商品ごとのまとまりにする）

PO 決定（2026-10-18）。上の 2026-10-14 改訂の「並び替えの第1キーを英語タイトルにした」を本改訂が上書きする（上の行は書き換えない）。ただしタイトル列（`sort=name`）の並びは 2026-10-14 のまま維持する。

- まとまり（商品）の順: 発売日 ASC（空欄は末尾）→ english_title ASC → japanese_title ASC → product_id ASC（在庫表のみ。閲覧ページは product_id を持たないので題名2つまで）。発売日の向きは `sort=release_date` を選んだときだけ `order` に従い、それ以外の並び替えでは常に ASC。
- まとまりの中の順: 既定（`release_date`）は `sort_ord`。それ以外は `{選んだ列} {向き} NULLS LAST → sort_ord`。プルダウンの並び替えはまとまりの中だけで効く（GAS 在庫一覧と同じ仕組み）。
- 既定の向きを asc にした（在庫表 `InventoryPage.tsx`、閲覧ページ `viewerFilter.ts` の `DEFAULT_SORT_DIR`）。並び替えプルダウンの先頭に `release_date:asc`「発売日が早い順」を追加し、既定のとき空表示にならないようにした。
- 実装: `backend/app/routers/inventory_offers.py` の `_build_view_order_by`、`frontend/src/pages/viewer/viewerFilter.ts` の `sortRows`。配信行の定義・GAS 出力14列・API 応答形は変えない。
- 守り: backend の ORDER BY 単体試験と viewerFilter の `sortRows` 試験。

## 改訂 2026-10-18（2）（既定の向きを発売日の新しい順に改める）

PO 決定（2026-10-18）「発売日の新しい順にしてほしい、いまは古い順になっている」。上の「改訂 2026-10-18」の既定の向き（asc）を desc に改める（前の改訂節の本文は書き換えない）。

- 既定の向きを desc にした（在庫表 `InventoryPage.tsx` の既定・リセット、閲覧ページ `viewerFilter.ts` の `DEFAULT_SORT_DIR`、API `inventory_offers.py` の `order` 既定）。
- プルダウンの先頭は `release_date:desc`「発売日が新しい順」。旧 `releaseAsc` キーは ja/en とも削除。
- 変えないもの: 同じ発売日の中（english_title → japanese_title → product_id）、同じ商品の中の価値順（ADR-1023）、発売日が空の商品は末尾、`_build_view_order_by` の組み立て。
- 守り: InventoryPage.tablelayout.test.tsx・viewerFilter.test.ts・InventoryView.test.tsx が既定の向き desc を固定する。

## 改訂 2026-10-18（3）（「24時間以内」を配信行の計算の内側で絞る）

PO 決定（2026-10-18）「y」: 在庫表の「24時間以内」ON のとき、絞り込みの選択肢（仕入元・カテゴリ・状態・形態）は24時間以内の在庫にあるものだけに絞ってよい。上の 2026-10-14 改訂の「24時間以内」の実装方法（件数とページ送りに連動させるため外側で絞る）を本改訂が改める（前の節は書き換えない）。

- `fresh_only=true` のときは、配信行の年齢窓（`_age_window`）そのものを `FRESH_WINDOW_HOURS`（24）にする。設定の窓（`max_age_hours`）が24より短いときは短い方、0（絞らない）のときは24。外側の `d.posted_ts >= NOW() - 24h` の条件は無くした（窓の定義は `_age_window` の1か所）。
- 並び・まとめ・件数・ページは変わらない。絞り込みの選択肢だけが、24時間以内の在庫にある値に縮む。`fresh_only=false` の SQL は変更前と同じ。
- 目的: 在庫表の初回表示の待ち時間の短縮（重い配信行の計算が24時間以内の行だけになる）。
- 守り: `backend/tests/test_inventory_distribution_rows.py`（窓が年齢窓に入ることと false 時の SQL 不変）、`backend/tests/test_inventory_distribution_rows_pg.py`（変更前の外側の絞りと total・ページが一致、選択肢は24時間以内の値だけ）。

## 改訂 2026-10-19（価格などで並べても、商品の順番は発売日の新しい順のまま）

PO 決定（2026-10-19）「y」（価格などで並べても、商品の順番は「発売日の新しい順」のまま変えず、中だけを並べる形に直す）。上の「改訂 2026-10-18」の「それ以外の並び替えでは常に ASC」を DESC に改める（前の改訂節の本文は書き換えない）。

- まとまり（商品）の順: `sort=release_date` 以外では 発売日 DESC（空欄は末尾）→ english_title ASC → japanese_title ASC → product_id ASC。既定の並びと同じなので、並べ方を切り替えても商品の位置は動かず、まとまりの中だけが入れ替わる。
- 実装: `backend/app/routers/inventory_offers.py` の `_build_view_order_by`、`frontend/src/pages/viewer/viewerFilter.ts` の `sortRows`。
- GAS 在庫一覧（リポジトリ外 shingo-ops/tcg-client-viewer の index.html）も同じ形に揃える（発売日 DESC → 英語名 → 日本語名）。商品名の見出しは英語名→日本語名を選んだ向きで並べる。
- GAS との既知の差（揃えない）: GAS は product_id を持たない。文字の比べ方（GAS は数字を数として比べ、大文字と小文字を区別しない）。選んだ列の空欄（GAS は常に末尾）。
- 変えないもの: 既定の並び、`sort=release_date` の向き、`sort=name` の並び（在庫表・閲覧ページ）、同じ商品の中の価値順（ADR-1023）。
- 守り: `backend/tests/test_inventory_distribution_rows.py` と `frontend/src/pages/viewer/viewerFilter.test.ts`。

## 改訂 2026-10-19（2）（同じ商品のまとまりの中で「最安」「在庫最多」の小さいバッジを付ける）

PO 決定（2026-10-19）「y」（同じ商品のまとまりの中で、最安値の行と在庫が1番多い行に、見づらくならない小さいバッジを付ける）。PO 決定（2026-10-19）「y」（値のある行が1行以下の商品と、全部の行が同じ値の商品には付けない）。前の改訂節の本文は書き換えない。

- 判定の規則（在庫表・閲覧ページ・GAS 在庫一覧で同じ）:
  - 比べる単位は商品のまとまり。比べる行は、利用者が絞り込んだ後・ページで切る前の行。
  - 最安: 価格が空でない行の最小値と等しい行。在庫最多: 数量が空でない行の最大値と等しい行。等しい行が複数あれば全部に付ける。
  - 値のある行が1行以下のとき、値のある行が全部同じ値のときは付けない。
  - 値は画面に出る値と同じく整数に丸めて比べる。まとめモードでは画面に出ている値（数量は合計、単価は最大）で比べる。
- 見た目: 既存の金型 `Badge`（size="sm"、appearance="soft"）を値の右隣・同じ1行に置く。最安は success、在庫最多は info。GAS は既存の `.badge` に小さい版の修飾クラスを足し、既存の色変数の組だけを使う。
- 実装の場所: 在庫表は `backend/app/routers/inventory_offers.py` の `_build_inventory_view_sql`（窓関数で `__badge_cheapest`・`__badge_most_stock` を作り、API の行の `badge_cheapest`・`badge_most_stock` で返す）。閲覧ページは `frontend/src/pages/viewer/viewerFilter.ts` の `markBlockBadges`。GAS 在庫一覧（リポジトリ外 shingo-ops/tcg-client-viewer の index.html）の render()。3か所にある理由は、閲覧ページと GAS がブラウザで絞り込むため（並び順と同じ）。
- 既知の差（揃えない）:
  - まとまりの決め方: 在庫表は product_id（空の行には付けない）。閲覧ページと GAS は product_id を持たないため「発売日・英語名・日本語名が全て同じ」行を1つのまとまりとする。発売日・英語名・日本語名が全て同じ別の商品だけ結果が違いうる。
  - 在庫表は価格が空の行を「¥0」と出す。空の行は比べないので、「¥0」の行にはバッジが付かない。
- 変えないもの: 並び順、件数、ページ、絞り込みの候補、配信行の定義、Badge の金型、tokens.css。
- 守り: `backend/tests/test_inventory_distribution_rows_pg.py`（規則・絞り込み・ページ・列の並び）と `frontend/src/pages/viewer/viewerFilter.test.ts`（閲覧ページの規則）。

## 改訂 2026-10-19（3）（最安・在庫最多をバッジから色の枠に変え、比べる単位にステータスと状態を足す）

PO 決定（2026-10-19）「y」（バッジは見づらく列がずれるので、最安の価格を水色の枠、在庫最多の数量を緑の枠で囲む。ステータスや状態が違う行はそれぞれのまとまりで比べる）。改訂（2）の本文は書き換えず、ここで次の点だけを置き換える。それ以外の規則（空の値、1行以下・全部同じ値は付けない、同じ値は全部、整数に丸める、絞り込み後・ページ前、まとめモードの値）は改訂（2）のまま。

- 比べる単位: 商品のまとまりを、さらにステータス（行の `status`）と状態（行の `condition`）で分ける。在庫表は `PARTITION BY d.product_id, d.status, d.condition`、閲覧ページは `markBlockBadges` のキーに `status` と `condition` を足す。
- 見た目: Badge は出さない。価格と数量の値は全部の行で同じ入れ物（`inventory-cell__value`、同じ余白）に入れ、最安は水色、在庫最多は緑の枠を内側の影（`box-shadow: inset`）で描く。枠の有無で幅が変わらないので列はずれない。枠の付いた値には `title` で「最安」「在庫最多」を出す。
- 既知の差: 在庫・予約の区分に写らない status（画面ではどれも同じ空欄）も、値ごとに別のまとまりになる。
- 色: `frontend/src/tokens.css` の `--comp-value-frame-cheapest`（水色、ライト・ダークの値を持つ）と `--comp-value-frame-most-stock`（`var(--success)` の別名）。
- 変えないもの: API の項目名 `badge_cheapest`・`badge_most_stock`、辞書キー、並び順・件数・ページ・絞り込みの候補。GAS 在庫一覧は未実装のまま（別便で、この改訂の規則に合わせる）。
- 守り: `backend/tests/test_inventory_distribution_rows_pg.py`（ステータス違い・状態違いの試験を含む）、`frontend/src/pages/viewer/viewerFilter.test.ts`、`frontend/src/features/inventory/inventoryColumns.test.tsx`・`frontend/src/pages/viewer/viewerColumns.cells.test.tsx`（全行が同じ入れ物に入ること）。

## 改訂 2026-10-19（4）（最安・在庫最多の見た目を、線の枠から Badge と同じ塗りの角丸に変える）

PO 決定（2026-10-19）「y」（「バッジと同じ囲み方を想定していた」「スプレッドシートのデータ入力規則のプルダウンみたいに囲って色付けする」。角丸・薄い水色／薄い緑の塗り・数字は濃い色・文字は足さない・列幅は変えない、という理解に同意）。改訂（3）の本文は書き換えず、見た目と色の2点だけをここで置き換える。比べる単位・既知の差・変えないもの・守りは改訂（3）のまま。

- 見た目: 価格と数量の値は全部の行で同じ入れ物（`inventory-cell__value`）に入れ、余白と角は金型 Badge sm と同じトークン（`--space-2px` `--space-2`、`--comp-badge-radius`）にする。最安は薄い水色、在庫最多は薄い緑で塗る。線は描かない。文字の大きさはセルのまま（Badge 部品そのものは 12px になり行の間で数字の大きさが揃わないため使わない）。枠の付いた値の `title` は改訂（3）のまま。
- 色: 最安は `--info-bg`／`--info-text`、在庫最多は `--success-bg`／`--success-text`（Badge soft info／success と同じ組）。改訂（3）の `--comp-value-frame-cheapest`・`--comp-value-frame-most-stock` は削除する（ADR-067 の表からも削除）。

## 改訂 2026-10-19（5）（商品の中は状態のまとまりを固定し、選んだ列はその中だけで並べる）

PO 決定（2026-10-19）「y」（「価格の安い順に並び替えると状態も並び替わってしまう」。商品は発売日の新しい順で固定、商品の中の状態の並びは既定＝価値順（ADR-1023）で固定、価格・数量などの並び替えは「同じ商品・同じ状態」のまとまりの中だけ）。改訂（2026-10-18）・改訂（2026-10-19）の本文は書き換えず、まとまりの中の並びだけをここで置き換える。

- まとまりの中の並び: 状態ブロック番号 ASC → 選んだ列 → 元の順（sort_ord）。状態ブロック番号は「同じ商品・同じ状態の行のうち最小の元の順」。同じ商品の中では sort_ord が 状態の価値順→状態名 の順なので、状態の並びは既定と同じになる。状態の列（condition）を選んだときも商品の中の状態の並びは変わらない。`sort=name`・`sort=release_date` の並びは変えない。
- 実装: アプリは `backend/app/routers/inventory_offers.py` の rows_x に `MIN(x.sort_ord) OVER (PARTITION BY x.product_id, x.condition) AS cond_block` を足し、`_build_view_order_by` で選んだ列の前に `d.cond_block ASC` を置く（cond_block は応答に出さない。API の項目は変えない）。閲覧ページは `frontend/src/pages/viewer/viewerFilter.ts` の `sortRows`、GAS 在庫一覧（リポジトリ外）も同じ形に揃える。
- 既知の差（揃えない）: 閲覧ページと GAS のまとまりのキーには product_id が無い（発売日・英語名・日本語名・状態）。GAS の比較は大文字・小文字を同じとみなすが、状態ブロックの Map のキーでは別になる。
- 変えないもの: 既定の並び、`sort_ord` の式（`tcg_result_order.py`）、印（`__badge_*` の PARTITION）、API の項目・DB。
- 守り: `backend/tests/test_inventory_distribution_rows_pg.py`（S1・S2）、`backend/tests/test_inventory_distribution_rows.py`、`frontend/src/pages/viewer/viewerFilter.test.ts`。

## 改訂 2026-10-19（6）（並び替えプルダウンは見出し「並び替え」＋3択）

PO 決定（2026-10-19）「発売日の新しい順はプルダウンに含めずデフォルトの表示設定とし、プルダウンの選択肢は3つにしてほしい」、続けて「y」「SAアプリの在庫表もだよ」（SAアプリの在庫表・閲覧ページ・GAS 在庫一覧の3画面とも同じ形）。

- プルダウンは見出し「並び替え」＋3択（価格が安い順・在庫が多い順・投稿が新しい）。既定（発売日の新しい順）は選択肢に出さず、未選択の見出しで表す。見出しを選ぶと既定（発売日の新しい順）に戻る。
- 上の「改訂 2026-10-18」の「既定のとき空表示にならないようにした」と「先頭は `release_date:desc`」は本改訂で置き換える（前の節の本文は書き換えない）。
- 既知の制限: 表の見出しクリックで3択以外の並び（商品名順・発売日の古い順など）にしたあとは、プルダウンが見出し表示のままになる。既定へ戻すには、3択のどれかを選んでから見出しを選ぶか、再読み込み（アプリはリセットボタン）。
- 文言: 閲覧ページの ja「並べ替え」→「並び替え」、「投稿が新しい順」→「投稿が新しい」、en の閲覧ページ stockDesc を "Quantity: high to low" にしてアプリとそろえた。`releaseDesc` キーは4つの locale から削除。
- 実装: `InventoryPage.tsx`・`InventoryView.tsx`・`viewerFilter.ts` の `SORT_MENU_VALUES` から `release_date:desc` を外し、見出し（空値）の選択で既定の並びに戻す。GAS 在庫一覧（リポジトリ外）は `applySortValue` で同じ解釈にする。サーバーの既定（`inventory_offers.py`）は変えない。
- 守り: `InventoryPage.tablelayout.test.tsx`・`InventoryView.test.tsx` が選択肢の数（見出し＋3択）・既定の見出し表示・見出しで既定に戻ることを固定する。

## 改訂 2026-10-19（7）（GAS 在庫一覧の表を閲覧ページと同じ形にする）

PO 承認（2026-10-19「y」。GAS の表を閲覧ページと同じ形にしてよいか）。改訂（3）で GAS 在庫一覧に未実装と記録した最安・在庫最多の目印（改訂（4）で塗りに変更）と並び順は、本番 GAS 版18で反映した。本改訂はそれに加えて表の見た目を揃える（前の節の本文は書き換えない）。本番 GAS 版17には塗り・並び順の変更はどれも入っていなかった（pull した中身で `applySortValue`・`markBlockFlags`・`cell-value--cheapest` が0件、版18で各1件以上）。

- 内容: GAS 在庫一覧（お客様向け）の表を、閲覧ページ（`frontend/src/pages/viewer/viewerColumns.tsx`）と同じ列順・見出し・文字色・単価の「¥」・提供者の下に投稿時刻・左固定列ステータスにした。
- 正本: `viewerColumns.tsx`・`frontend/src/features/inventory/conditionBadge.ts`・`frontend/src/features/inventory/inventoryColumns.css` と `tokens.css`/`index.css`。正本を変えたら GAS の写しも同じ便で直す。
- GAS で出せないもの（シートに元データが無い）: 予約の補足（`ship_timing`）・「N行分」・行クリックの詳細・ダーク表示。見出しの紺色は PO 試作のため対象外。
- 反映（2026-10-19）: テスト GAS 版27・本番 GAS 版18。本番18には次がまとめて入った: 並び順（発売日の新しい順のまとまり・#4519）、改訂（3）（4）の最安・在庫最多の塗り、改訂（5）状態のまとまり固定、改訂（6）並び替え3択、本改訂（7）の表の見た目。写しの場所: `~/CC報告ファイル-keep/inventory-gas-table-parity/gas/`（`test_stage`・`prod_stage`）。
- 戻し方: 本番は版17、テストは版26へ redeploy。
- 記録: `docs/handoff/inventory-gas-table-parity/`（recon・design・審査）。

## 改訂 2026-10-20（商品名を1行のまま「…」で省き、備考・発送は折り返す）

PO 決定（2026-10-20「1」）。商品名は1行のまま幅の上限を決め、超えた分は「…」にする。マウスを乗せると全文が出る。備考・発送は上限幅で折り返す（前の節の本文は書き換えない）。目的は、PC 幅で長い文字により表が横に広がり、`fitToWidth` が表全体を縮めるのを抑えること。

- 内容: 商品名の日本語の段・英語の段は上限幅（`--comp-inventory-title-max-w` = 360px）で1行のまま末尾を「…」にし、全文を `title` に入れる。備考・発送は `--comp-inventory-text-max-w`（200px）で折り返し、中身がある間は `--comp-inventory-text-min-w`（100px）より細らない。スマホ幅（767px 以下のカード表示）は今のまま。
- 正本: `frontend/src/features/inventory/inventoryColumns.css`・`inventoryColumns.tsx`・`frontend/src/pages/viewer/viewerColumns.tsx`・`frontend/src/tokens.css`（トークン3つは ADR-067 の表に追記）。正本を変えたら GAS の写しも同じ便で直す。
- 反映: アプリ: 本 PR。GAS: テスト版28（本番は本改訂の版で反映）。
- 戻し方: アプリは PR を revert。GAS は本番を版18、テストを版27へ redeploy（反映後の実際の版番号を記録する）。
- 記録: `docs/handoff/inventory-title-ellipsis/`（recon・design・審査）。

## 改訂 2026-10-20（2）（商品名の全文は、切れているときだけ浮くカードで見せる）

PO 決定（2026-10-20「カード版でこの仕様で決定」）。前の改訂の `title` 属性（ブラウザ標準の小さな黄色い帯）をやめ、金型 `HoverCard` で出す（前の節の本文は書き換えない）。

- 内容: パソコン幅（768px 以上）で、日本語・英語どちらかの段が「…」で切れているときだけ、マウスを乗せて150ms後に名前の上へカードを出す。日本語は太字1行、英語は小さく薄く1行。隣の行へ移るとカードは滑って移る。切れていない名前では出ない。クリックでは開閉しない。スマホ幅は折り返しで切れないので出ない。
- 正本: `frontend/src/components/HoverCard.tsx`・`HoverCard.css`・`frontend/src/features/inventory/inventoryColumns.tsx`・`frontend/src/pages/viewer/viewerColumns.tsx`・`frontend/src/tokens.css`（トークン2つ `--ease-pop`・`--comp-hover-card-blur` は ADR-067 の表に追記）。GAS の `:root` にある写しは、正本トークンを変えたとき一緒に直す。
- 反映: アプリ: #4557（2026-10-20 マージ）。GAS: テスト版29・本番版19（2026-10-20 PO 実行。clasp pull で中身が作った物と一致）。
- 戻し方: アプリは PR を revert（前の便の「…」＋ `title` に戻る）。GAS はテストを版28、本番を版18へ redeploy する。
- 記録: `docs/handoff/inventory-name-hover-card/`（recon・design・審査）。

## 改訂 2026-10-20（3）（上部の検索・絞り込み・並び替えを2段に並べる）

PO 決定（2026-10-20「1」。この形で、アプリ・閲覧ページ・在庫一覧の3つをそろえる）。前の節の本文は書き換えない。

- 内容: パソコン幅で、1段目に [検索][価格 最低〜最高][数量 最小〜最大]、2段目に [並び替え][コンディション][提供者]（アプリはその右に詳細フィルタ）、右端に [24時間以内][リセット]。境目はアプリ・閲覧ページが 768px、GAS は今の 1280px（GAS はリセットの位置に「更新」）。スマホ幅は3画面とも今のまま。
- アプリの価格・数量・状態（コンディション）は「フィルタを有効化」に関係なく常に効く（ADR-093 の表示条件のうち、この3つだけ有効化スイッチから外す）。保存先は今の `/me/inventory-filters` の同じ項目。形態・在庫/予約・シリーズ除外は今どおり有効化スイッチ付き。
- 閲覧ページにアプリと同じ動きのリセット（検索語・並び）を足す。
- 正本: 金型 `frontend/src/components/ContentToolbar.tsx`（2段目の枠と範囲入力。規格は `docs/specs/design-system/component-ssot/page-header-v2/design.md` §2.5）、`frontend/src/pages/inventory/InventoryToolbar.tsx`、`frontend/src/pages/viewer/InventoryView.tsx`。GAS の grid は写し。
- 反映: アプリ: 本 PR。GAS: 反映後に版番号を追記する。
- 戻し方: アプリは PR を revert。GAS はテストを版29、本番を版19へ redeploy する。
- 記録: `docs/handoff/inventory-toolbar-two-rows/`（recon・design・審査）。
