# 設計: 並び替えプルダウンは「並び替え」見出し＋3択（既定＝発売日の新しい順は選択肢に出さない）

版: 第3版（2026-10-19、Opus。第1版 REVISE 指摘1〜9、第2版 REVISE 指摘1〜2＋任意2点を反映 review-design.md / review-design-v2.md）
recon: /tmp/CC報告ファイル/inventory-sort-3choices/recon/（基準 origin/main 70c3eda3d）

## 1. 目的（PO の言葉）
PO（2026-10-19）「発売日の新しい順がプルダウンに含まれているがこれはプルダウンに含めずにデフォルトの表示設定として発売日の新しい順になっているべきでプルダウンには表示しないほうが使いやすい、デフォルトを並び替えで表示しておき、プルダウンの選択肢は3つにしてほしい」→ Opus 確認「3画面（SAアプリ在庫表・閲覧ページ・GAS）とも同じ形」に PO「y」「SAアプリの在庫表もだよ」。

見え方（指摘3）: 閉じた状態は「並び替え」。開くと先頭に見出し「並び替え」、その下に選べる並び3つ（価格が安い順・在庫が多い順・投稿が新しい）。見出しは「何も選んでいない＝既定（発売日の新しい順）」を表す行で、並びの選択肢としては3つ。見出しを選ぶと既定に戻る。

## 2. 現在地（recon 抜粋、すべて origin/main 70c3eda3d）
- アプリ: frontend/src/pages/inventory/InventoryPage.tsx:467-487 SelectControl（金型 frontend/src/components/Select.tsx）。選択肢 :481-486、SORT_MENU_VALUES :58、既定 :127-128（release_date/desc）、placeholder :472、表示値 :473（4値に無ければ ""）、onChange :474-480 は :476 `if (!field) return;` で "" を捨てる。
- Select.tsx:100-104 `<option value="" disabled={rest.required}>`。2画面とも required を渡さない＝見出しは選択可能。
- 閲覧ページ: frontend/src/pages/viewer/InventoryView.tsx:197-216、onChange :203-209 は :205 `if (!k) return;` で "" を捨てる。既定 frontend/src/pages/viewer/viewerFilter.ts:12-13、:14 コメント「4択」、SORT_MENU_VALUES :15。見出しクリック :229-233。リセットボタン無し。
- backend: backend/app/routers/inventory_offers.py:374-379 既定 release_date desc。変更不要。
- i18n: frontend/src/locales/ja.json・en.json:1563-1568（inventory.sortMenu）、frontend/src/locales/viewer/ja.json・en.json:28-34（viewer.sort）。releaseDesc のコード参照は InventoryPage.tsx:482 と InventoryView.tsx:211 のみ。
- GAS: ~/CC報告ファイル-keep/inventory-sort-cond-block/gas/test_stage/index.html（prod_stage と同一）:840-845 select、:938-939 初期値 sortCol=-1、:1023-1028 change、:1187-1189 初期化（select 初期値 9_desc を読む＝今も開いた直後は発売日の新しい順）、:1396 sortCol>=0 のときだけ並べる、:1670-1686 toggleSort。COL.releaseDate=9（:985）。
- GAS テスト版は現在 @25。Opus が 2026-10-19 に clasp pull した中身（~/CC報告ファイル-keep/inventory-sort-cond-block/gas/pull_v25_1792391192/）は test_stage と diff 0。
- ADR-1014 :40-48（:46「既定のとき空表示にならないようにした」）、:50-55（:55「先頭は release_date:desc」）。

## 3. 方針
既定の並び（発売日の新しい順）はサーバー・各画面の既定値のまま変えず、**プルダウンの選択肢から release_date:desc だけを外す**。未選択（既定）のときは金型の placeholder「並び替え」が表示される（既存の「4値に無ければ ""」の仕組みをそのまま使う）。新しい部品・新しい定義は作らない。
- 見出し（value=""）を選んだら既定（release_date desc）に戻す。
- 文言を3画面でそろえる（4-1・4-2・4-4 に値で指定）。

### 3-1. 見出しクリック後の扱い（指摘1・7、Opus 判断）
- 3画面とも表の見出しクリックで3択以外の並び（例: 商品名順、発売日の古い順）にできる。このときプルダウンは「並び替え」表示になる。これは今も同じ（今も4値以外は "" 表示）で、今回は変えない。
- このとき見出しを選び直しても値が "" のままなので変化しない。既定へ戻すには「3択のどれかを選んでから『並び替え』を選ぶ」「再読み込み」「アプリはリセットボタン」。以前は「発売日が新しい順」を直接選べたので1手増えるが、PO の「プルダウンに含めない」を優先する。ADR-1014 改訂（6）に既知の制限として書く。
- GAS の見出しクリック時の select 表示はアプリ・閲覧ページにそろえ「一致する option が無ければ ''」にする（直前の選択が残ったまま別の並びになるのを防ぐ）。

## 4. 変更（変更前 → 変更後）
### 4-1. アプリ InventoryPage.tsx
- :58 SORT_MENU_VALUES から "release_date:desc" を削除（残り unit_price:asc・quantity:desc・offered_at:desc）。
- onChange :474-480
  変更前
  ```tsx
  const [field, dir] = e.target.value.split(":");
  if (!field) return;
  setSortField(field);
  setSortDir(dir === "asc" ? "asc" : "desc");
  setPage(1);
  ```
  変更後
  ```tsx
  const [field, dir] = e.target.value.split(":");
  if (!field) {
    setSortField("release_date");
    setSortDir("desc");
  } else {
    setSortField(field);
    setSortDir(dir === "asc" ? "asc" : "desc");
  }
  setPage(1);
  ```
  （既定値の文字列は :127 と :359 と同じ直書き。定数は無い）
- :482 の release_date:desc の行を削除。
- frontend/src/locales/ja.json・en.json の inventory.sortMenu.releaseDesc を両方から削除。他の文言は変えない（ja: 並び替え／価格が安い順／在庫が多い順／投稿が新しい、en: Sort／Price: low to high／Quantity: high to low／Newest posts）。
- 既定値 :127-128・resetAll :355-362・見出しクリック :612-614 は変えない。
### 4-2. 閲覧ページ InventoryView.tsx / viewerFilter.ts
- viewerFilter.ts:15 SORT_MENU_VALUES から "release_date:desc" を削除、:14 コメント「4択」→「3択（既定の発売日の新しい順は見出しで表す）」。
- onChange :203-209 をアプリと同じ形に（"" → setSortKey(DEFAULT_SORT_KEY)・setSortDir(DEFAULT_SORT_DIR)）。
- :211 の release_date:desc の行を削除。
- frontend/src/locales/viewer/ja.json: placeholder「並べ替え」→「並び替え」、postedDesc「投稿が新しい順」→「投稿が新しい」、releaseDesc 削除。
- frontend/src/locales/viewer/en.json: stockDesc "Stock: high to low"→"Quantity: high to low"、releaseDesc 削除（placeholder "Sort"・priceAsc・postedDesc はそのまま）。
### 4-3. 試験
- frontend/src/pages/inventory/InventoryPage.tablelayout.test.tsx:51-69（試験名の「4 options」等の数も実態に合わせて書き換える）: 選択肢4個（先頭 value="" の見出し＋3択）、release_date:desc を含まない、既定で menu.value===""、options[0] は見出し、リセット後も ""。新規1本: unit_price:asc を選ぶ → "" を選ぶ → 最後の /inventory 呼び出しの sort=release_date かつ order=desc、menu.value===""。
- frontend/src/pages/viewer/InventoryView.test.tsx:51-59: 選択肢は見出し＋3択、release_date:desc を含まない、既定で value===""。新規1本: unit_price:asc を選ぶ → "" を選ぶ → 既存試験の作法（captured.props 等）で sortKey="release_date"・sortDir="desc"。
### 4-4. GAS（新しい作業場所 ~/CC報告ファイル-keep/inventory-sort-3choices/gas/）
- 準備: test_stage・prod_stage を ~/CC報告ファイル-keep/inventory-sort-cond-block/gas/ から写す。testpull は pull_v25_1792391192 の写し（.clasp.json 含む）。prodpull は ~/CC報告ファイル-keep/inventory-sort-cond-block/gas/prodpull の写し（Opus が 2026-10-19 に本番を clasp pull した pull_prod_1792391455 と diff 0、本番の公開版は @17 を clasp deployments で確認済み）。台本 deploy_test.sh・deploy_prod.sh も写して G のパスを新しい場所に。
- :840-845 → 先頭に `<option value="" selected>並び替え</option>`、9_desc の行を削除（残り 5_asc 価格が安い順・6_desc 在庫が多い順・0_desc 投稿が新しい）。
- 値の解釈を1つの関数にまとめる:
  ```js
  // ADR-1014 改訂 2026-10-19（6）: 見出し（""）は既定＝発売日の新しい順
  function applySortValue(v) {
    var parts = String(v || '').split('_');
    var col = parseInt(parts[0], 10);
    if (isNaN(col)) { sortCol = COL.releaseDate; sortDir = 'desc'; return; }
    sortCol = col;
    sortDir = parts[1] === 'asc' ? 'asc' : 'desc';
  }
  ```
  change :1023-1028 は `applySortValue(event.target.value); render();`、初期化 :1187-1189 は `applySortValue(document.getElementById('sortSelect').value);`。
- 初期値 :938-939（sortCol=-1・sortDir='asc'）は触らない。`var COL` は :975 で :938 より後に実行されるため、:938 で COL を使うと TypeError になる。初期化 :1187-1189 の applySortValue が必ず上書きする。現行も初期化で sortCol=9 desc なので、開いた直後の並びは同一（T4 で差0確認）。
- toggleSort :1680-1683: 一致する option があればその値、無ければ `selectEl.value = ''`。
- deploy_test.sh: 期待版 25、create-version「並び替えを見出し＋3択に(ADR-1014改訂10-19(6))」、戻し方コメント「版25へ redeploy」。deploy_prod.sh: 期待版 17、create-version「並び順＋塗り＋状態のまとまり固定＋並び替え3択(ADR-1014改訂10-19)」、戻し方コメント「版17へ redeploy」。
- clasp はPOの ! 実行のみ。Sonnet は clasp を実行しない。
### 4-5. 文書
- ADR-1014 に「改訂 2026-10-19（6）: プルダウンは見出し『並び替え』＋3択（価格が安い順・在庫が多い順・投稿が新しい）。既定（発売日の新しい順）は選択肢に出さず、未選択の見出しで表す。見出しを選ぶと既定に戻る。:46『既定のとき空表示にならないようにした』と :55『先頭は release_date:desc』は本改訂で置き換え。既知の制限: 表の見出しクリックで3択以外の並びにしたあとはプルダウンが見出し表示のまま。既定へは3択のどれかを選んでから見出しを選ぶか再読み込み（アプリはリセットボタン）」を追記。node scripts/generate-adr-index.js。
- docs/handoff/inventory-sort-3choices/recon.md・design.md。

## 5. 触らない範囲
backend・API・DB・migrations・deploy.yml・scripts、並びの規則（商品→状態のまとまり）、見出しクリックの並べ替えそのもの、金型 Select.tsx、塗り・印、SORT_MENU_VALUES の二重定義（既存）。

## 6. 受入条件
| 基準 | 検証方法 |
|---|---|
| T1 アプリ: 見出し「並び替え」＋3択、既定で見出し表示、表は発売日の新しい順 | vitest（4-3）。本番配信 JS に `inventory-sort-menu` があり releaseDesc の文言（発売日が新しい順）が無いこと |
| T2 アプリ: 別の並び→見出しで既定に戻る | vitest（4-3 新規、最後の呼び出しが sort=release_date&order=desc） |
| T3 閲覧ページ: T1・T2 と同じ、ja 文言が「並び替え」「投稿が新しい」 | vitest |
| T4 GAS: 見出し＋3択、開いた直後の並びが変更前（9_desc）と同じ、3択も変更前と同じ | 手元 node で新旧の並び処理を ~/CC報告ファイル-keep/inventory-sort-cond-block/ の sheet.csv 写しに流し、変更前 9_desc と変更後 "" の順が全行一致（差0）、5_asc・6_desc・0_desc も新旧で全行一致 |
| T5 i18n: ja/en キー一致、ハードコードなし | 既存 CI |
| T6 CI 必須チェック全緑 | gh pr checks |
| T7 PO 目視 | 閉じた状態で「並び替え」／開くと先頭「並び替え」＋3択／開いた直後の表は発売日の新しい順／価格が安い順→並び替え で元の順に戻る（GAS テスト版とアプリ）。4つとも○で合格 |

## 7. リスクと戻し方
- 見出しクリック後の戻し方が1手増える（3-1、既知の制限として ADR に記載）。
- 戻し方: PR の revert。GAS はテスト版25・本番版17へ redeploy。

## 8. 外部・過去事例の参照と我々への応用
不要: 画面のプルダウン文言・選択肢の整理で、外部の数値で成否が決まる性質ではない。

## 9. 維持の仕組み
守り手: frontend/src/pages/inventory/InventoryPage.tablelayout.test.tsx、frontend/src/pages/viewer/InventoryView.test.tsx（CI の vitest）
ADR-1014 改訂（6）を正本とし、vitest（4-3）で選択肢の数・既定の見出し表示・見出しで既定に戻ることを守る。GAS はステージのコメントに ADR 番号を残す。
審査: 第1版 REVISE（review-design.md）→ 第2版 REVISE（review-design-v2.md）→ 第3版
