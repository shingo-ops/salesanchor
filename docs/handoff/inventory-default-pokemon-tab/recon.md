# recon: 在庫表を最初からポケモンで開き、表示を早くする

基準: `origin/main` 7d8b5f732（2026-10-21 fetch 後の worktree）。調査は Sonnet（読み取りのみ）、要点の照合は Opus が実物を読んで行った。
生出力: `/tmp/CC報告ファイル/default-pokemon-recon/`、`/tmp/CC報告ファイル/default-pokemon-measure/`（series_count.txt・api.txt・assetsizes.txt・gas_timing*.txt）、`/tmp/CC報告ファイル/default-pokemon-measure2/`（m.js・raw.jsonl・out.txt）。
GAS ソースの基準: `/Users/tanizawashingo/CC報告ファイル-keep/inventory-tabs-attach-table/gas/verify_prod_after/`（本番 版21 を反映直後に pull したもの）と `verify_test_after/`（テスト 版31）。両者の index.html は同一（`cmp` 一致）。

## PO の依頼（原文、2026-10-21）
- 「ポケモンをデフォルトにして裏で全件読み取る」
- 「読み込みはタブ順にその他に統合されていないデータを優先的に読み込んでページが1秒でも早く表示されるようにしたい」

## 既存 ADR・設計
- ADR-1019 項8: 閲覧ページはアプリ在庫表と同じ金型。既定タブの決めは無い。
- ADR-1030: タブは中分類（type_master）で絞る。
- `docs/handoff/inventory-tabs-attach-table/design.md`: タブを「すべて／ポケモン／ワンピース／ドラゴンボール／その他▼」に揃えた（#4578、GAS テスト版31・本番版21）。既定タブには触れていない。
- `docs/handoff/gas-viewer-fresh-fast/design.md`: 閲覧ページの絞り込み規則 D4（手元の行に対する純関数）。

## A. アプリ在庫表（変更不要）
- 既定タブは既にポケモン: `frontend/src/pages/inventory/InventoryPage.tsx:131` `useState<string>("pokemon_booster_box")`。
- 読み込みはタブごとのサーバー絞り込み・50件: `load()` `:74-126` が `GET /inventory?page&per_page=50&...&work_code=<タブ>`（`:88`）。タブ切替で再取得（`:126`, `:539`）。
- 既定を前提にしたテスト: `frontend/src/pages/inventory/InventoryPage.tabs.test.tsx:81`。
- → 依頼の「ポケモンを先に」は既に満たしている（開いているタブの50件だけを読む）。

## B. 閲覧ページ /viewer
- 既定タブ「すべて」: `frontend/src/pages/viewer/InventoryView.tsx:56` `useState(TAB_ALL)`、`TAB_ALL="all"`（`frontend/src/pages/viewer/viewerFilter.ts:10`）。
- 主な3つの定義: `frontend/src/pages/viewer/viewerFilter.ts:227` `MAIN_SERIES = ["ポケモン","ワンピース","ドラゴンボール"]`（type_master.name_ja と照合。GAS index.html の MAIN_SERIES と相互参照コメントあり）。
- 読み込み: `GET /api/v1/viewer/inventory` 1回で全行。サーバーは Redis の作り置き JSON を丸ごと返す（`backend/app/routers/viewer.py:234-245`、作り置き `backend/app/tasks/viewer_inventory_cache.py:72-116`）。絞り込み・並べ替えは手元（`frontend/src/pages/viewer/InventoryView.tsx:96-98`）、表に渡すのは50件の slice（`:100-102`）。タブ切替で通信は起きない。
- スマホのセレクト: `frontend/src/pages/viewer/InventoryView.tsx:219-228`、value={tab}、選択肢は「すべて」＋件数順の全シリーズ（`seriesTabs` `frontend/src/pages/viewer/viewerFilter.ts:213-224`）。
- PC のタブ: `frontend/src/pages/viewer/InventoryView.tsx:288-` Tabs 金型、activeKey は tab が TAB_ALL か MAIN_SERIES のときその値。
- 既定=すべて を明示的に確かめるテストは無い（grep で該当なし）。`frontend/src/pages/viewer/InventoryView.test.tsx` 全体が暗黙に全件表示を前提にしているかは未確認 → 実装時に vitest で確認する。
- 表示時間: 【未測定】。閲覧 API はログインが必要（未ログインは 401、0.07〜0.15秒・30B、measure/api.txt）。計測用アカウントは無い（id=23 は 10/20 削除済み）。応答の大きさは件数×項目からの見積もりで約1.4〜2.4MB（非圧縮）【推測】。

## C. シート版（GAS 在庫一覧）
- 既定タブ「すべて」: `verify_prod_after/index.html:1000` `var activeSeries = ''`。宣言は MAIN_SERIES（`:1003`）より前。
- 選んでいたシリーズの行が無くなったら「すべて」に戻す: `index.html` buildSeriesTabs 内 `if (activeSeries && !counts[activeSeries]) activeSeries = '';`。
- 読み込み: `loadData`（`:1207`）が `google.script.run.getInventoryData()` を1回。GAS の Code.js 55〜97行目 は在庫集計シートを `getDataRange().getValues()` で全行読み、許可14列を返す（引数なし）。
- 受信後（`onDataLoaded` `:1219-1252`）: Sold out 除外（`:1232-1234`）→ 全行の検索用文字列 SEARCH_TEXTS（`:1237-1239`）→ buildSeriesTabs → buildFilterOptions → applySortValue → render。
- render（`:1428-`）: 全行 filter（`:1441-1470`。シリーズ絞りは `:1452`、SEARCH_TEXTS は検索語があるときだけ使う `:1448-1450`）→ sort → 絞った後の全行を innerHTML（ページ分割なし）。
- 更新ボタン（`:918` `loadData(true)`）は activeSeries を保ったまま再取得する。

### C の時間の内訳（本番 版21、匿名 Chrome、3回、measure2/out.txt）
| 区間 | 平均（秒） |
|---|---|
| 外枠と iframe の HTML 読み込み完了 | 2.67 |
| サーバー呼び出しの送信開始 | 3.00 |
| サーバーの応答待ち（TTFB） | 1.85 |
| 応答の受信完了 | 4.88 |
| 応答受信 → 表のデータ行が出るまで（画面側の処理） | 1.21（うち onDataLoaded〜render 終了 1.04） |
| 表のデータ行が出た時刻 | **6.09** |
- 応答は gzip 後 約32.6KB（展開 333,610B）、本文の受信は 19〜24ms。→ 通信量は時間の主因ではない。
- 応答の行数 1,197（約2日分）、Sold out 除外後に表示 834行（24時間絞り込み後）。
- ばらつき: 前回の測定では平均8.2秒、修正前スクリプトの回では 4.5〜22秒。原因は【未測定】。

## D. シリーズ別の件数（本番、読み取り鍵、measure/series_count.txt）
- 配信条件（`backend/app/services/tcg_distribution_svc.py:365-375`）相当での件数。全期間 3,490 行、直近24時間 886 行。
- ポケモン 2,315（約66%）／ワンピース 730／ドラゴンボール 126／その他のシリーズ合計 約319。
- condition_review 結合を別名の列で代用しているため完全一致の保証は無い【未測定】。

## E. 「その他」判定の正本
- 3か所で別々に定義: アプリ `frontend/src/pages/inventory/InventoryPage.tsx:59` MAIN_TCG_CODES（code）、閲覧 `frontend/src/pages/viewer/viewerFilter.ts:227` MAIN_SERIES（name_ja）、GAS `index.html:1003` MAIN_SERIES（name_ja）。共通ファイルは無い（GAS は別の配信系のため共有できない）。今回はこの定義を増やさず、既定タブは各所の MAIN_SERIES[0]（アプリは既存の定数）を使う。

## F. 分かったこと（設計への入力）
1. GAS の時間の大半（外枠 2.67秒＋応答待ち 1.85秒）は Google 側。通信量は 33KB で 20ms。サーバー呼び出しを「ポケモン」「その他」に分けても、シートは毎回全行読むので応答待ちは減らず、呼び出しが1回増える。
2. GAS の画面側の処理 1.04秒は、表に描く行数と検索用文字列の作成に比例する。ポケモンで開けば描く行が約3分の2になり、検索用文字列を表示の後に回せば最初の表示から外せる。
3. 閲覧ページは表に描くのが常に50件。時間の主因は応答の大きさと JSON の読み込みと見られるが【未測定】（ログインが必要）。
