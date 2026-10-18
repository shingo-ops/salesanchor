# design: 価格などで並べても、商品の順番は「発売日の新しい順」のまま、中だけを並べる

recon: docs/handoff/inventory-sort-block-order/recon.md ／ 関連 ADR: ADR-1014（改訂を足す）・ADR-1023・ADR-1015

## 目的（PO の言葉）
- PO（2026-10-19）「gasの並び替え機能は商品ブロックは崩さずに商品ブロック内で価格がやすいなど並び替える機能になっているが、SAアプリの在庫表はテーブル全体で並び替える仕様になっている、修正できるか？」
- PO 決定（2026-10-19）「y」。問いは「価格などで並べても、商品の順番は『発売日の新しい順』のまま変えず、中だけを並べる形に直してよいですか。y ならアプリも GAS も同じ形に揃えます」。

## 区分
B（ADR-1015）。並び順の式だけを変え、DB・API の形・migrations・deploy.yml・scripts・nginx は触らない。GO は POの委任に基づく Claude Opus 発行（ADR-1003）。GAS 在庫一覧の本番反映は、reference_tcg_client_viewer の手順（直前に clasp pull して差分 0 を確かめる → push → create-version → redeploy）で行う。

## 利用者に見える変化
| 並べ方 | 今 | 変更後 |
|---|---|---|
| 発売日が新しい順（既定） | 発売日の新しい順のまとまり | 変わらない |
| 発売日が古い順 | 発売日の古い順のまとまり | 変わらない |
| 価格が安い順・在庫が多い順・投稿が新しい順・各列の見出し | アプリと閲覧ページは発売日の古い順のまとまり、GAS は英語名の順のまとまり。中だけを並べる | 3つとも、発売日の新しい順（空は末尾）→ 英語名のまとまり。中だけを並べる |
| 商品名の見出し | アプリと閲覧ページは英語名の昇順・降順で切り替わる。GAS は降順が効かない | アプリと閲覧ページは変わらない。GAS も昇順・降順が効くようにする |

## 方式
まとまりの順を、既定の並び（発売日の新しい順）に固定する。これで、どの並べ方を選んでも商品の位置は動かず、中の行だけが入れ替わる。
- 不採用の案「GAS に合わせて英語名の順にする」: 既定の並び（発売日の新しい順）から価格の順に切り替えると、商品の位置ががらりと変わる。PO の承認内容（発売日の新しい順のまま）とも違う。

## 変更前 → 変更後
### 1. `backend/app/routers/inventory_offers.py` の `_build_view_order_by`（:262-277）
- 変更前（:270）: `group_dir = order_dir if sort_col == _SORT_COLUMNS["release_date"] else "ASC"`
- 変更後: `group_dir = order_dir if sort_col == _SORT_COLUMNS["release_date"] else "DESC"`
- docstring の「発売日の向きは release_date を選んだときだけ order_dir」の後に、「ほかの並び替えでは既定と同じ DESC（ADR-1014 改訂 2026-10-19）」と足す。
- そのほかの行は変えない。

### 2. `frontend/src/pages/viewer/viewerFilter.ts` の `sortRows`（:172-193）
- 変更前（:178）: `sortKey === "release_date" ? sortDir : "asc"`
- 変更後: `sortKey === "release_date" ? sortDir : "desc"`
- :166-171 のコメントの「発売日の向きは release_date を選んだときだけ sortDir」の後に、「ほかの並び替えでは desc（既定と同じ）」と足す。

### 3. 試験
- `backend/tests/test_inventory_distribution_rows.py:132`
  - 変更前: 価格 DESC の期待値が `{group_asc}`。
  - 変更後: `{group_desc}`。
  - 価格 ASC の行を 1 つ足し、`{group_desc}, d.price_num ASC NULLS LAST, d.sort_ord ASC` を期待する。
  - 試験名は変えない。
- `backend/tests/test_inventory_distribution_rows_pg.py:298-316`: 新旧どちらも同じ `_build_view_order_by` から作って比べるので、期待値の変更は要らない（審査で確認済み）。`:313` のコメント「改訂 2026-10-18」に「・2026-10-19」を足す。
- `backend/tests/test_inventory_distribution_rows_pg.py:545-546`（`test_bin1_sort_groups_by_release_date_then_title`）: CI（run 39167855790）で失敗して見つかった。価格の降順の期待値が、まとまりの順を発売日の古い順とする前提のまま残っていた。
  - 変更前: `["Beta", "Alpha", "Alpha"]  # まとまりの順は不変`
  - 変更後: `["Alpha", "Alpha", "Beta"]  # まとまりの順は既定と同じ発売日の新しい順（ADR-1014 改訂 2026-10-19）`
  - 同じ試験のほかの行（release_date の asc・desc、name の asc・desc）は変えない。
- `frontend/src/pages/viewer/viewerFilter.test.ts:75-77`
  - 変更前: 価格の安い順で `[3, 1, 0, 2]`。
  - 変更後: `[0, 3, 1, 2]`（発売日の新しい商品B → 商品A の 100・900 → 空の C）。
  - 試験名を「price asc keeps the default group order (release date newest first) and sorts only inside a group」に直す。
- `frontend/src/pages/viewer/InventoryView.test.tsx:51-58` と `frontend/src/pages/inventory/InventoryPage.tablelayout.test.tsx:56-62` は、プルダウンの値と API の引数だけを見ている。並びの結果は固定していないので変更不要（審査で grep 済み）。

### 4. `docs/adr/ADR-1014-inventory-view-shows-distribution-rows.md` に「改訂 2026-10-19」を足す（Opus が書く）
- ほかの並び替えでのまとまりの順を、発売日 ASC から DESC（既定と同じ）に改める。
- GAS 在庫一覧も同じ形に揃える。
- 前の改訂節は書き換えない。

### 5. GAS 在庫一覧 index.html（リポジトリの外。テスト 1Tb → 本番 1hc の順）
土台は、別のディレクトリへ直前に clasp pull した実体にする。~/tcg-viewer-1tb-head の行番号は目安で、pull した実体で探し直す。
- 並び替えの関数（:1387-1432）を、次の順に比べる形にする。
  1. sortCol が COL.englishTitle（商品名の見出し）のとき
     - English Title を sortDir で比べる。
     - 同じなら Japanese Title を sortDir で比べる。
     - 同じなら 0 を返す。
  2. それ以外のとき
     - (a) 発売日で比べる（空は常に末尾）。向きは、sortCol が COL.releaseDate なら sortDir、それ以外は 'desc'。
     - (b) English Title の昇順で比べる（今の :1404-1412 のまま）。
     - (b2) Japanese Title の昇順で比べる（新しく足す。COL.japaneseTitle :972。比べ方は (b) と同じ localeCompare）。
     - (c) sortCol が COL.releaseDate でなければ、選んだ列で比べる（今の :1414-1431 のまま）。
- コメントに「アプリの在庫表と同じ（ADR-1014 改訂 2026-10-19）」と書く。
- 文言・色・CSS は変えない。
- 既知の差（今回は揃えない。どれも今からある差で、PO の決定（商品の順番）の範囲外）:
  - GAS の14列には product_id が無い。発売日・英語名・日本語名が全て同じ別商品は、GAS では1つのまとまりとして並ぶ。
  - 文字の比べ方: GAS は `localeCompare('ja-JP', {numeric:true, sensitivity:'base'})` で比べる（数字を数として比べ、大文字と小文字を区別しない）。アプリと閲覧ページは数字を文字として比べる（'item 10' と 'item 2' の順が違う）。
  - 選んだ列の空欄: GAS は常に末尾に置く。アプリの状態・種別・仕入元・投稿日時は、昇順のとき空欄が先頭に来る。

## 触らない範囲
- 配信行の定義・SQL の行条件・API の応答形・sort_ord（ADR-1023）。
- 在庫表の画面（`frontend/src/pages/inventory/InventoryPage.tsx`）。並べ方はサーバーが決めるので、画面の変更は要らない。
- 文言・色・部品（デザイントークン・金型の変更なし）。
- DB・migrations・deploy.yml・scripts・nginx。

## 受入条件
| 基準 | 検証方法 |
|---|---|
| S1 価格・在庫・投稿・各列で並べたときのまとまりの順が、発売日 DESC NULLS LAST → 英語名 → 日本語名 → product_id になる | pytest `backend/tests/test_inventory_distribution_rows.py` |
| S2 閲覧ページで価格の安い順にすると `[0, 3, 1, 2]` になる。既定・発売日 asc/desc・商品名の試験は変わらず通る | vitest `frontend/src/pages/viewer/viewerFilter.test.ts` と、閲覧ページの試験全体 |
| S3 CI の必須チェックが全て緑 | gh pr checks |
| S4 ①反映: 変更を含むコミットが、Deploy が成功したコミットの祖先である（`git merge-base --is-ancestor` と `gh run view` で確かめる）。②結果: 本番の在庫表 API で、sort=unit_price&order=asc の 1 ページ目のまとまりの順が、既定（sort=release_date&order=desc）の 1 ページ目のまとまりの順の先頭と一致する | reader 鍵では API を呼べないので、本番 DB を SELECT で読み、同じ ORDER BY を当てた結果で照合する（`backend/app/services/tcg_distribution_svc.py` の配信行を使う式は実装役が SELECT だけで組む）。組めなければ「未観測・保留」と書き、S1 と S2 で判定する |
| S5 GAS のテスト版で、価格が安い順にしても商品の順番が既定（新しい順）と同じで、各商品の中だけが価格の順になる。英語名が同じで日本語名が違う商品は混ざらない。商品名の見出しの降順が効く | テスト版を clasp pull し直して、差分が意図した変更だけかを確かめる。Playwright で画面を見る（使えないときはその事実を書き、コードの差分で判定する） |
| S6 GAS の本番版でも S5 と同じ | 本番を clasp pull して確かめる（新しい版番号と diff） |

## 維持の仕組み
- 守り手: backend/tests/test_inventory_distribution_rows.py（まとまりの順の式を固定する。CI の pytest で毎回走る）。閲覧ページは frontend/src/pages/viewer/viewerFilter.test.ts で同じ順を固定する。
- まとまりの順は `_build_view_order_by` と `sortRows` の2か所にあり、どちらも試験で固定している。閲覧ページの冒頭の注記には、「アプリの在庫表と同じ結果にする」とある。
- GAS はリポジトリの外にあり、CI の守りは無い。そこで ADR-1014 の改訂に「GAS も同じ形」と書き、次に変えるときに照合できるようにする。
- 戻し方: PR を revert する。GAS は前の版に redeploy する（テスト版23・本番版17）。

## 外部・過去事例の参照と我々への応用
- 外部事例: 該当なし。理由は、PO が決めた並び方を自社の3か所に揃えるだけで、外部の数値を根拠にする判断が無いため。
- 過去事例（自社）: ADR-1014 改訂 2026-10-18（2）で、既定の向きを発売日の新しい順に改めた（#4505）。そのときも、在庫表（サーバー）と閲覧ページ（ブラウザ）の2か所を同じ式で直し、試験で固定した。
- 応用: 今回も同じ2か所を同じ形で直す。GAS はリポジトリの外にあるので、ADR の改訂に既知の差まで書き、次に照合できるようにする。

## 審査記録
- 1回目（2026-10-19、reviewer・opus）: REVISE（軽微）。アプリの式と試験の設計は PO 決定どおりで、期待値 [0,3,1,2] は手計算で正しいと確認された。指摘は次の4点で、全て反映した。
  - ① viewerFilter.ts の行番号 :180 を :178 に直す。
  - ② GAS に日本語名の比べを足し、既知の差を明記する。
  - ③ ADR の改訂節を末尾へ移す。
  - ④ pg 試験と InventoryView 系の試験を変更不要と確定し、S4 に反映の観測を足す。
- 判定（Opus）: 指摘は全て文書内で解消しており、事業判断が要る点は無い。実装へ進める。
