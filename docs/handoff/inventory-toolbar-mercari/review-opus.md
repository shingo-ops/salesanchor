# review: 在庫表スマホの上部操作台（便1）独立審査

## r1（Opus・2026-10-29・反証を探す立場）: **REVISE**

実コードを抜き取り検証した結果、初版の設計の主張のうち5件が実コードと食い違っていた。
**主要な指摘と、設計の直し方**を下にまとめる（全文の要点）。

### HIGH

| # | 指摘 | 根拠 | 設計の直し方 |
|---|---|---|---|
| H1 | **`field-w-lg` では検索欄は全幅にならない**。`TextFieldControl` は裸の `<input>` を返すので `.comp-field` の `width:100%` に乗れず、親の `.content-toolbar__left` は伸びない（flex item の既定 `0 1 auto`）ため、`width:100%` が中身なりの幅で解決される。閲覧ページはこれを避けて `flex: 1 1 100%` を別クラスで足している | `frontend/src/components/TextField.tsx` ／ `frontend/src/components/ContentToolbar.css` ／ `frontend/src/pages/viewer/viewer.css` | 4-2・4-3 を新設。金型に `--content-toolbar-left-flex`（既定値つき）を足し、ページ側 CSS で検索欄に `flex: 1 1 100%` を与える |
| H2 | **`search` と `filterButton` は PC 分岐と共用の JSX 変数**。クラスや `size` を変えると **PC も変わる**。初版の「PC 分岐はクラスを変えないので二重に安全」は誤り。さらに初版の D9 は「並び」しか見ないので PC の劣化を検出できない | `frontend/src/pages/inventory/InventoryToolbar.tsx` | 4-1 を新設（スマホ専用の JSX 変数に分ける）。D12 で PC の検索欄の幅・詳細フィルタの `min-height`・`font-size` を固定 |
| H3 | **既存の単体テストが必ず赤**。スマホで `.content-toolbar--two-rows` が無いこと、5つの並びを固定している | `frontend/src/pages/inventory/InventoryPage.toolbar.test.tsx` | ⑥と受け入れ基準に追加（K6 を新しい形に更新する） |
| H4 | **`onReset` は絞り込みを戻さない**（検索語・カテゴリー・並び替え・ページだけ。詳細フィルタは意図的に保持とコメントに明記）。初版の K6「絞り込みが元に戻る」は × になる | `frontend/src/pages/inventory/InventoryPage.tsx` | K6 の文を実装に合わせて修正 |
| H5 | **関所が落ちる**: 設計書に裸の設計書ファイル名（フルパスでない引用）があり、検査9（バッククォート内の `.md` をルートから解決）で ❌ | `scripts/dev/validate-pr-body.sh` | フルパスに修正（全件確認済み） |

### MEDIUM

| # | 指摘 | 設計の直し方 |
|---|---|---|
| M1 | 2段目が入らなくても**右に溢れず3行に折り返す**（`.content-toolbar__left` が two-rows で `flex-wrap: wrap`）＝「右端≤画面幅」の判定は空振りになりうる。高さの判定が無い | **D10（高さ112px以下）を追加**。4-4 に幅の見積り（余裕約26px）を明記 |
| M2 | 768px ではそもそもスマホ分岐が描かれない（境目767px）ので `field-h-tap` の media は問題にならない。本当のリスクは **spec が project 既定の viewport に依存すること** | 4-4 と ⑤ に「spec 側で 360/390 を明示」と明記 |
| M3 | **今すでに高さは44px**（`@media` が後勝ち）。初版の「いま36px」は実測と矛盾し、D3 が空振りになる | P4 を「44px → **48px以上**」に修正。D3（高さ）と D4（画面内）を分離 |
| M4 | 移した「24時間以内」は `Checkbox` の素の大きさ（約15px）で **ADR-140 違反**。閲覧ページは専用 CSS を足している | 4-3 に `.inventory-fresh-check` を追加。**D7** で44px以上を測る |
| M5 | ボタンの `variant` は `filterEnabled`（別物）に連動するので「(1) と出ているのに枠なし灰」が起きる。また数は在庫表の絞り込み全部を数えない＝**過少申告** | `variant` を**常に ghost** に統一。過少申告は⑩に明記し、定義の見直しを⑫ L3 に起票 |
| M6 | 便0 の計測 spec が `.content-toolbar__left` を**単数**取得しているため、2段になると1段目しか測らず**黙って壊れる**（赤にはならない） | ⑥と受け入れ基準に「全件取得に直す」を追加 |

### LOW

| # | 指摘 | 設計の直し方 |
|---|---|---|
| L1 | 閲覧ページは移した先の `data-testid` を**別名**にしている（便2の教訓） | 4-6 で `inventory-fresh-check` ／ `inventory-reset-in-panel` に分けた |
| L2 | 新 props を `showSupplierSelect` で囲まないと PC でパネルを開いたとき操作が2つになり strict mode 違反 | 4-6 に明記 |
| L3 | `size="tap"` にするなら `layoutClassName="field-h-md"` は外すべき（同じ詳細度で順序依存） | 4-4 の表に明記 |
| L4 | `.content-toolbar .field-w-lg { margin-bottom: 0 }` は two-rows でも当たるが、`TextFieldControl` は `.comp-field` を作らないので**打ち消す相手がいない**（無害・無意味） | 設計から `field-w-lg` の利用自体を外した |
| L5 | K4 の「既定は (1)」は CI の mock でのみ保証。実アカウントは保存値で2以上になりうる | K4 を「**1以上**」に修正 |
| L6 | 辞書の置き場（`inventory.filterPanel` に1キーずつ）は整合的 | そのまま |

## r1 で**問題なしと確認された**点（再確認不要）

- 受け入れ基準の表ヘッダ `| 基準 | 検証方法 |` は関所の正規表現に合致し、空セルは0件。
- `docs/handoff/inventory-toolbar-mercari/recon.md` のバッククォート引用は全件実在。
- 数え方に使う5つの状態は `frontend/src/pages/inventory/InventoryPage.tsx` に**すべて存在する**。
- `.css` は関所のパス検査の対象拡張子外。
- e2e 側で `inventory-fresh-toggle` / `inventory-reset-sort` を参照している spec は**0件**。
