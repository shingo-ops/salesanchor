# review: 在庫表スマホの種別・並び替えをパネルに（便2）独立審査

## r1（Opus・2026-10-29・反証を探す立場）: **REVISE**

実コードを抜き取り検証した結果、初版の設計に**実装前に直せる穴が複数**あった。要点と直し方。

### HIGH

| # | 指摘 | 根拠 | 設計の直し方 |
|---|---|---|---|
| H1 | **既存 spec が消える目印を直接掴んでいる**。便1 で作った spec はスマホ幅で `inventory-sort-menu` を `boundingBox()` で掴む。目印を `inventory-sort-trigger` に変えると**12件（2幅×3 project×2判定）が時間切れで赤**。しかも**写す元の閲覧ページは PC の `select` とスマホのボタンで同じ目印を使い回していて**、そこだけ写していなかった | `frontend/tests-e2e/visual-language/inventory-toolbar-mercari.spec.ts` ／ `frontend/src/pages/viewer/InventoryView.tsx` の2か所 | 4-2: **並び替えの目印は `inventory-sort-menu` のまま据え置く**。E14 で「PC では `select` 要素であること」まで見る |
| H2 | **注記は `white-space: nowrap` を直書きしている**。そのまま詳細フィルタへ移すと、パネルの内側（約286px）より注記（約315px）が広く**約29pxはみ出す**＝ K7（全文読める）と P8（横スクロール0）が同時に壊れる | `frontend/src/pages/inventory/InventoryPage.tsx` の `Tabs` の `end` ／ `frontend/src/pages/inventory/InventoryFilterPanel.tsx` の箱 | 4-4 に `.inventory-notice` を新設し、4-5 で **nowrap を外して折り返す**ことを明記。E10 で幅を測る |
| H3 | **種別の一覧を `tcgTypes` 全件にすると、取得に失敗したとき種別が1つも選べなくなる**（`.catch` で黙って捨てる実装・既存の単体テストも空で mock）。今は `MAIN_TCG_CODES` の3件が定数で必ず出ている | `frontend/src/pages/inventory/InventoryPage.tsx` の取得処理と `MAIN_TCG_CODES` | 4-3: **「すべて」＋ `MAIN_TCG_CODES` ＋ それ以外の `tcgTypes`** で合成する。受け入れ基準に単体テストを追加 |
| H4 | 初期値 `pokemon_booster_box` が `tcgTypes` に無いと、**主操作の文字に英語コードが露出**する | 同上 | ⑩ に明記（今のタブのラベルと同じ規則で、今より悪くはならない）。根本は ⑫ M4 に起票 |
| H5 | **CI の画面検査は1ジョブ・持ち時間10分**で、便1 の時点で655件・7.4分。初版の案は81実行を足す | `.github/workflows/e2e.yml` ／ `frontend/playwright.config.ts` | ⑤: **幅360を基本**にし、E2 と E11 だけ390でも測る。PC は1280で1件 |

### MEDIUM

| # | 指摘 | 設計の直し方 |
|---|---|---|
| M1 | 「既定」を選ぶとボタンの文字は**「並び替え」に戻る**（既定の値は3択に含まれないため）。初版の K6・E8 の文面は実装と不整合 | K6 と E8 を実挙動に合わせて書き直し。E8 は**非既定の行→既定の行**の順で測る |
| M2 | `RadioControl` に `name` を渡す指示が無い（ネイティブのグループ化が効かない）。在庫表に他の radio は無く**衝突はしない** | 4-3 に `name` を明記 |
| M3 | `onClick` 併用が無害なのは**`pick` が同値の `setState` だから**。トグルで書くと事故る | 4-3 に条件として明記 |
| M4 | パネルの `Drawer` を PC にマウントすると `supplier-drawer` と `drawer-close` が PC でも増える | 4-3: **`{isMobile && (...)}` で囲む** |
| M5 | `InventoryToolbar` は「状態は親が持つ表示専用部品」と自分で宣言している。state を中に置くと契約違反 | 4-3: **state も `Drawer` も親のページに置く** |
| M6 | 在庫表の既存辞書はこの概念を**種別**と呼ぶ（全種別／その他）。パネルの題を「シリーズ」にすると KGI 文面と食い違う | 4-6: **「種別」を採用**（`inventory.typeSelect`）。PO に報告し、違和感があれば1語で直せる |
| M7 | `frontend/src/pages/inventory/InventoryPage.tabs.test.tsx` の K5b は「スマホでもタブの行が出る」を断言している。消すと守り手を失う | ⑥: **反転**して「スマホでは出ない」を固定する |
| M8 | CI の mock は種別が**1件だけ**なので E5〜E7 が意味を持たない | ⑥: `frontend/tests-e2e/visual-language/inventory-helpers.ts` の mock を**3件以上**にする |

### LOW（主なもの）

- L1 行の markup と文字を包む要素の規則が無い → 4-3・4-4 に追記。
- L2 `resetAll` のコメントが「発売日の早い順」でコードと逆（実際は新しい順）。本便で同じ語を PO に見せるので ⑫ M3 に起票。
- L3 `tcgTypes` は「カテゴリー列の日本語表示用」とコメントにあるが、実際には**タブでしか使われていない**（H3 の判断材料）。
- L5 守り手に書いた spec の**名前を1文字でも変えると関所が赤**になる。

### r1 で**問題なしと確認された**点（再確認不要）

- `frontend/tests-e2e/visual-language/drawer-inert-closed.spec.ts` は閲覧ページしか開かない＝在庫表に `Drawer` を増やしても赤にならない。
- 在庫表を開く spec に `drawer-close` の参照は**0件**。`supplier-drawer` を見るものは全部 `.comp-drawer-panel--open` で絞ってある。
- `Drawer` は `document.body` に出る（portal）ので、操作台の子の数（P3）には影響しない。
- `frontend/src/pages/inventory/InventoryPage.tablelayout.test.tsx` と `.settings.test.tsx` は PC 扱いなので赤にならない。
- 寸法は実現可能（`comp-btn--tap` は48px・`--size-icon-btn-lg` は44px）。E13 の作り（CSSOM を辿る）の先例も実在。
- 設計書の関所まわりの形式（`| 基準 | 検証方法 |` の表・空セル0件・`守り手:`・フルパス）は通る見込み。
