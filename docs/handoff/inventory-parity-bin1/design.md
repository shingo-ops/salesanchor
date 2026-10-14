# 在庫表と GAS 在庫一覧の揃え 便1（4項目）設計

- 状態: 設計案（Opus）。PO 決定は 2026-10-14 のチャット（下記 KGI）。
- 現在地: [recon.md](./recon.md)（origin/main 758d84e8d、file:line 付き）。差分の全量: /tmp/CC報告ファイル/app_vs_gas_verify.txt（ローカル。社外秘を含まないが repo には置かない）
- 関連 ADR: ADR-1014（在庫表=配信行。本便で改訂）、ADR-144（UI 金型）、ADR-027（i18n）、ADR-093

## KGI（PO 決定 2026-10-14、要旨）

| # | PO 決定 | 本便 |
|---|---|---|
| 1 | Sold out の行は出さない（アプリも） | ○ |
| 2 | 同じ投稿の行は既定ではまとめない | ○ |
| 3 | 「24時間以内」をアプリにも付ける | ○ |
| 4 | 最初のタブを GAS もアプリと同じ（ポケモン）にする | 保留（下記「保留」） |
| 5 | GAS もアプリと同じ鮮度。目標は1秒以内の表示 | 保留（下記「保留」） |
| 6 | 並び替えは GAS 方式（英語タイトルでまとめてから並べる）をアプリにも採用 | ○ |

列・検索・絞り込みの向き・スマホ・件数・言語・見られる人の違いは便2以降（PO 指示）。

## 変更（変更前 → 変更後）

### 1. Sold out を配信行の定義から除く（SSOT）
- 場所: `backend/app/services/tcg_distribution_svc.py` の `distribution_rows_parts` の dist_base WHERE（recon §1、SVC:319-326）。
- 変更前: Sold out は `ar.exclusion='excluded'` のときだけ除かれる（SVC:322）。status の文字そのものでは除いていない。
- 変更後: WHERE に `AND lower(btrim(COALESCE(ar.status, ''))) NOT IN ('sold out', 'soldout')` を足す。判定は GAS の isSoldOut（GI:962-965。trim と小文字化のあと 'sold out'/'soldout'）と同じ。
- 効き目: 配信行の定義は1か所（ADR-1014）なので、アプリの在庫表と GAS への配信の両方から同時に消える。GAS の画面側の除外（GI:1165-1167）は既に同じ行を隠しているので、GAS の見た目は変わらない。GAS の画面側の除外は今回は残す（GAS は変更しない）。
- 触らないもの: `fetch_preview_data` の件数クエリ（ADR-1014 の方針どおり別の問い合わせで、変更しない）。要確認タブ（dist_base を使わない。tcg_review_sheet_svc.py:106-109）。

### 2. 「まとめ」の既定を OFF にする
- 変更前は true。true の箇所: RT:295 `merge_same_post: bool = Query(default=True)`、`me_inventory_filters.py:51` と `:119`（キーが無い・bool でない値を True にする）、PG:163 `useState(true)`、PG:297、PG:311。
- 変更後: 上の箇所をすべて false にする。i18n の文言で「既定 ON」と書いているところがあれば直す。
- 保存済みの設定（`user_inventory_filters.filters` の JSONB）は触らない。migration もデータの書き換えもしない。
  - true を保存済みの人は ON のまま。キーが無い人は OFF になる。
  - 保存件数は本番 DB で未確認（下記「未確認」）。

### 3. アプリに「24時間以内」を付ける（既定 ON）
- API（RT）:
  - クエリに `fresh_only: bool = Query(default=False)` を足す。
  - 定数 `FRESH_WINDOW_HOURS = 24` を RT に1つだけ置く。
  - true なら、`_build_view_filters` に条件 `d.posted_ts >= NOW() - make_interval(hours => :fresh_hours)` を足す。こうすれば件数とページ送りに連動する（recon §3）。
  - 応答 `InventoryListResponse` に `fresh_window_hours: int`（常に FRESH_WINDOW_HOURS）を足す。
  - 絞り込み候補（facets）は今までどおり絞り込み前の行から作る。
- 画面（PG）:
  - state `freshOnly` を足し、既定は true にする。保存はしない（GAS と同じく、開き直すと ON に戻る）。
  - 常に `fresh_only` を送る。「フィルタ有効」と関係なく効く（タブ・検索・まとめと同じ扱い。PG:210-213）。
  - ツールバーの検索ボタンの並びに、トグルを1つ足す。部品は既存の金型 `Button` の `variant`＋`aria-pressed` を使う（同じページの前例は PG:472-481 のまとめトグル）。新しい部品・生 input・色の直値は使わない。
  - ラベルは i18n キー `inventory.view.freshOnly`（ja「{{hours}}時間以内」、en「Last {{hours}} h」）。hours は応答の `fresh_window_hours` を使う。応答が来るまではボタンを disabled にし、ラベルの数値はまだ出さない。
  - 切り替えると page=1 に戻す。
  - 「リセット」（resetAll）は今までどおり。freshOnly は戻さない。
- GAS との差（受け入れる）: GAS は閲覧端末の時刻で判定する（GI:1354）。アプリは DB の NOW() で判定する。

### 6. 並び替えを GAS 方式にする
- 場所: RT `_build_inventory_view_sql` の `order_by`（RT:240。RT:253 の ROW_NUMBER も同じ文字列を使う）。
- 変更前: `ORDER BY {sort_col} {dir} NULLS LAST, d.sort_ord ASC`
- 変更後:
  - sort が name 以外のとき: `ORDER BY d.english_title ASC, {sort_col} {dir} NULLS LAST, d.sort_ord ASC`
  - sort が name のとき: `ORDER BY d.english_title {dir}, d.japanese_title {dir} NULLS LAST, d.sort_ord ASC`
    - GAS では、タイトルの見出しを押しても順が変わらない（verify B33）。アプリでは、押すと英語タイトルの昇順と降順が入れ替わるようにする（Opus の設計判断）。
- 英語タイトルが空の行は '' なので、昇順では先頭に来る。これは GAS と同じ（recon §6）。
- 既定（発売日の降順）は変えない。結果は「英語タイトルごとにまとめ、その中で発売日の降順」になり、GAS の既定「新しい順」と同じになる。

### ADR-1014 の改訂
本文に「改訂 2026-10-14（便1）」の節を足し、次の3点を書く。
- まとめの既定 OFF
- Sold out の除外を配信行の定義に入れたこと
- 並び替えの第1キーを英語タイトルにしたこと

あわせて `node scripts/generate-adr-index.js` を実行する。

## 受け入れ条件

| 基準 | 検証方法 |
|---|---|
| status が 'Sold out' / ' sold out ' / 'SoldOut' の行が配信行に出ない。'In Stock' は出る | backend pg テスト（test_inventory_distribution_rows_pg.py に3件を足す）が green |
| distribution_rows_sql の固定テストが新しい SQL に更新されている | test_inventory_distribution_rows.py が green |
| /inventory の merge_same_post を省略すると、まとめない | テスト（API 既定）が green |
| /me/inventory-filters で、キーが無いときは merge_same_post=false を返す | test_me_inventory_filters.py が green |
| fresh_only=true で 24時間を過ぎた行が出ず、total もそれに合う。応答に fresh_window_hours=24 が入る | backend pg テストが green |
| sort=release_date&order=desc の結果が、英語タイトルの昇順で、その中は発売日の降順になる。sort=name&order=desc なら英語タイトルの降順になる | backend pg テストが green |
| 画面: 開いた直後の要求に fresh_only=true と merge_same_post=false が入る。トグルを押すと fresh_only=false で再取得し、page=1 になる | vitest が green |
| ハードコードの文字・色が無い | `node scripts/check-ui-governance.js`、frontend の lint と i18n のチェックが green |
| 本番: デプロイ後に /api/health が 200 | デプロイ後に Sonnet が確認する |

## 弊害とリスク
- true を保存済みの人は、まとめ ON のまま残る。人数は未確認（本番 DB の読み取りが今回できなかった）→ PO に報告する。
- Sold out の除外で、GAS の「在庫集計」シートの行数が減る可能性がある。GAS の画面では元々隠れているので、見た目は変わらない。5000 行の上限には、減る方向にしか効かない。
- 英語タイトル順は、DB の照合順序で決まる。GAS の localeCompare（ja-JP, numeric）とは、数字や記号の並びで違うことがある（未確認）。

## 戻し方
PR を revert する。migration とデータの変更は無いので、コードを戻すだけで元に戻る。

## 維持の仕組み
- 配信行の定義は distribution_rows_parts の1か所だけ。固定テストがあるので、変えると CI が止まる。
- 並び替え・24時間・まとめの既定は、テストで固定する。

## 外部事例
該当なし。社内の2画面を揃える作業で、外部の数値を設計の根拠に使わないため。

## 保留（PO 判断が要るもの）
- **4 GAS の最初のタブ**: GAS のタブは `products.work_id → type_master.name_ja`、アプリは `products.tcg_type`（recon §4）。ポケモンに当たる Series の値と、2つの結び方が一致するかは、本番 DB を見ないと決められない。type_master には seed が無い。本番 DB の読み取りは、今回、自動の安全判定（Remote Shell Writes）で止まった。
- **5 GAS の鮮度と1秒**:
  - 実測（/tmp/CC報告ファイル/gas_load_timing.txt）では、本番 GAS は開いてから表が出るまで 10.6〜16.8 秒（中央値 14.3 秒、565 行）。「更新」は 1.9〜2.5 秒かかった。これはシートを読み直すだけの時間。
  - DB を直接読むには、GAS から API を呼ぶ新しい入口と、その認証（新しい secret）が要る。前例は無い（recon §5）。secret の追加は、PO の確認が要る操作にあたる。
  - GAS の画面の初期表示そのものが1秒を超えているので、1秒の目標には別の作り方が要る可能性がある。どの部分に時間がかかっているかの内訳は、まだ測っていない。

## 未確認
- 本番の max_age_hours。24 以下なら「24時間以内」は効き目が無い。
- Sold out で、exclusion が 'excluded' でないのに配信行に入っている行の件数。
- merge_same_post を保存している人数の内訳。
- tcg_type と work_id の対応。

## 審査（Fable、1回目）を受けた改訂（2026-10-14）
審査の結果は REVISE（/tmp/CC報告ファイル/bin1_design_review.txt）。指摘7件をすべて取り込み、下のとおり設計を確定する。上の本文と食い違う場合は、この節を優先する。

1. **Sold out の判定は共有関数にする。**
   - SVC に `_sold_out_filter() -> str` を新しく作る（`_condition_filter` と同じ方式）。中身は `lower(btrim(COALESCE(ar.status, ''))) NOT IN ('sold out', 'soldout')`。
   - この関数を、dist_base の WHERE（SVC:319-326）と、配信プレビューの件数クエリの WHERE（SVC:417-437）の両方で使う。プレビューの件数と配信の行数がずれないようにするため。
   - test_tcg_condition_review.py の「件数＝出力行数」の比較に、Sold out の seed を入れた1件を足す。
   - 配信プレビューの実行ボタン（DistributionPreview.tsx:125）は、件数を見るだけなので変更しない。
2. **固定テストの基準を書き換える。**
   - test_inventory_distribution_rows_pg.py:231 `_old_three_statements` の基準 ORDER BY を、新しい ORDER BY に更新する。
   - 英語タイトルが空の行が昇順で先頭に来ることを確かめる pg テストを1件足す。
3. **`_build_view_filters` の引数 `fresh_only` は既定値 `False` にする。** 既存テストの呼び出し（:267-271、:291-295）は変えない。
4. **`FRESH_WINDOW_HOURS = 24` は SVC（tcg_distribution_svc.py）に置く。**
   - schema の `InventoryListResponse` に `fresh_window_hours: int` を足す。
   - RT は応答を返すすべての箇所で、この値を入れる。max_age_hours が None で早く返す箇所（RT:316）も含む。
5. **vitest の更新対象は次の4つ。**
   - CommerceNavigationButtonMigration.test.tsx:47-48、62（URL の完全一致。fresh_only=true と merge_same_post=false が入る）
   - InventoryPage.settings.test.tsx:39-42
   - InventoryPage.singlefetch.test.tsx:79
   - InventoryPage.noechopatch.test.tsx:40-89
6. **期間の注記（inventory.expiryWarning、PG:607-613）で出す時間を変える。**
   - 出す時間は、freshOnly が ON なら「fresh_window_hours」と「window_hours（0 より大きいとき）」の小さい方、OFF なら今までどおり window_hours。
   - window_hours が 0（無制限）で freshOnly が ON のときは、fresh_window_hours を出す。
   - 文言のキーは既存のものを使う（新しいキーは freshOnly のラベル1つだけ）。
7. **細かい点。**
   - `load` の依存配列（PG:249）に freshOnly を足す。
   - 「既定 ON」と書いてあるのはコメント3か所だけで、i18n の文言には無い。直すのは PG:162、me_inventory_filters.py:50、ADR-1014:15。
   - 弊害を1つ足す。トグルが ON のとき primary 色になるので、ツールバーの primary が増える（Button.tsx:12「primary は1画面1個」）。「フィルタ」のトグル（PG:511-520）という既存の前例と同じ扱いにする。
