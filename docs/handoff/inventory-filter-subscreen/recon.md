# recon: 在庫表（/inventory）スマホの詳細フィルタをパネル＋次の画面に（便3）

> この文書は何か（1行）: 在庫表のスマホで「詳細フィルタ」を押したときに出る枠を、閲覧ページ（/viewer/）と同じ
> 「右から出るパネル → 項目を押すと次の画面で選ぶ」形に作り替えるための下調べ（事実のみ・推測なし）。

**親（前の便の設計）**: [docs/handoff/inventory-toolbar-mercari/design.md](../inventory-toolbar-mercari/design.md) の ⑫ にある
**便3（③）**が本便。直前の便は
[docs/handoff/inventory-series-sort-panel/design.md](../inventory-series-sort-panel/design.md)（便2）と
[docs/handoff/toolbar-series-name-full-width/design.md](../toolbar-series-name-full-width/design.md)（便2.5）。

## 0. 既存 ADR の検索結果（正本 §2 の必須手順）

`git grep -il -E "絞り込み|フィルタ" docs/adr/` と docs/adr/FEATURE-INDEX.md:18（在庫 → ADR-099／ADR-093／ADR-014）を引いた。
本便に効く ADR は次の5本。**新しい ADR は要らない**（画面の形の変更で、データ構造も API も変えない）。

| ADR | 本便への効き方 |
|---|---|
| docs/adr/ADR-144-ui-component-governance.md | 共通部品（`frontend/src/components/`）の金型を勝手に作らない・変えない。本便は**1ファイルも触らずに作れる**（下の §4） |
| docs/adr/ADR-067-design-token-enforcement.md | 色・寸法は直値禁止。本便で足す CSS は既存トークンと既存変数だけ |
| docs/adr/ADR-027-ui-internationalization.md | 文言は `t("…")` 経由。ja/en 同一キー |
| docs/adr/ADR-1019-inventory-viewer-separate-accounts.md | 閲覧ページ（`frontend/src/pages/viewer/`）は別アプリ。**お手本として読むだけで、1文字も変えない** |
| docs/adr/ADR-140-mobile-nav-bottom-tabs.md | 押せる高さの下限（48dp／44px）の根拠。既存 spec も同じ定数を使う |

## 1. いまの詳細フィルタの作り

**パネルは「右から出る」ものではなく、ページに埋め込まれた枠**。

- `frontend/src/pages/inventory/InventoryPage.tsx:139` — 開閉の状態 `showFilterPanel`
- `frontend/src/pages/inventory/InventoryPage.tsx:585` — ボタンを押すと反転（`onFilterPanelToggle`）
- `frontend/src/pages/inventory/InventoryPage.tsx:590-629` — `{showFilterPanel && <InventoryFilterPanel … />}`。
  **閉じているときは DOM に無い**
- `frontend/src/pages/inventory/InventoryFilterPanel.tsx:113-128` — 中身は `<section className="inventory-filter-panel"
  data-testid="inventory-filter-panel">`。見た目は**直書きの style**（枠線・角丸・`maxWidth: "44rem"`）
- `frontend/src/pages/inventory/InventoryFilterPanel.tsx:1-10` — 冒頭に「状態は親（InventoryPage）が保持し、props 経由で受け取る」と明記（表示専用部品）

### 中に並んでいる項目（上から・実物の行番号）

| # | 項目 | 部品 | 目印（data-testid） | 出る条件 | 置き場所 |
|---|---|---|---|---|---|
| 1 | 24時間以内 | `Checkbox` | `inventory-fresh-check` | スマホだけ | `frontend/src/pages/inventory/InventoryFilterPanel.tsx:131-144` |
| 2 | 注記（※…） | 親から渡される `notice` | `inventory-expiry-warning` | スマホだけ | `frontend/src/pages/inventory/InventoryFilterPanel.tsx:146`／親は `frontend/src/pages/inventory/InventoryPage.tsx:627` |
| 3 | 提供者 | `MultiSelect`（既定＝浮かぶ） | `inventory-supplier-filter-button` | スマホだけ | `frontend/src/pages/inventory/InventoryFilterPanel.tsx:149-160` |
| 4 | コンディション | `MultiSelect`（既定＝浮かぶ） | `inventory-condition-filter-button` | スマホだけ | `frontend/src/pages/inventory/InventoryFilterPanel.tsx:163-174` |
| 5 | 価格の範囲 | `ContentToolbarRange` | `inventory-price-min` / `-max` | スマホだけ | `frontend/src/pages/inventory/InventoryFilterPanel.tsx:175-185` |
| 6 | 数量の範囲 | `ContentToolbarRange` | `inventory-qty-min` / `-max` | スマホだけ | `frontend/src/pages/inventory/InventoryFilterPanel.tsx:186-196` |
| 7 | フィルタを有効化 | `Checkbox` | `inventory-filter-enabled` | PC とスマホ共通 | `frontend/src/pages/inventory/InventoryFilterPanel.tsx:199-204` |
| 8 | TCGシリーズの表示／非表示 | `Checkbox` を並べる | `inventory-filter-category-<名前>` | PC とスマホ共通 | `frontend/src/pages/inventory/InventoryFilterPanel.tsx:206-229` |
| 9 | 表示する列 | `Checkbox` を並べる | `inventory-filter-col-<列名>` | PC とスマホ共通 | `frontend/src/pages/inventory/InventoryFilterPanel.tsx:231-258` |
| 10 | 形態 | `Checkbox` を並べる | `inventory-unit-<名前>` | PC とスマホ共通 | `frontend/src/pages/inventory/InventoryFilterPanel.tsx:276-292` |
| 11 | 在庫・予約 | `Checkbox` を並べる | `inventory-offertype-<値>` | PC とスマホ共通 | `frontend/src/pages/inventory/InventoryFilterPanel.tsx:293-303` |
| 12 | リセット | `Button` | `inventory-reset-in-panel` | スマホだけ | `frontend/src/pages/inventory/InventoryFilterPanel.tsx:305-312` |
| 13 | 閉じる | `Button` | （目印なし） | PC とスマホ共通 | `frontend/src/pages/inventory/InventoryFilterPanel.tsx:314-318` |

「スマホだけ」の出し分けは props の `showSupplierSelect`（`frontend/src/pages/inventory/InventoryFilterPanel.tsx:26-27`）で、
親が `showSupplierSelect={isMobile}` を渡している（`frontend/src/pages/inventory/InventoryPage.tsx:597`）。

### 項目の「入／切」の向きが2種類ある（写すときの肝）

- **隠す側を覚えている**: カテゴリーと列。`checked={!hiddenCategories.has(c)}`
  （`frontend/src/pages/inventory/InventoryFilterPanel.tsx:222`）／`checked={!hiddenColumns.has(c)}`（`frontend/src/pages/inventory/InventoryFilterPanel.tsx:250`）。
  状態は「隠したもの」の集合（`frontend/src/pages/inventory/InventoryPage.tsx:496-513`）で、サーバにも隠した側が保存される
  （`frontend/src/pages/inventory/InventoryPage.tsx:93-94` の `hidden_categories` / `hidden_columns`・`frontend/src/pages/inventory/InventoryPage.tsx:375` で PATCH）。
- **出す側を覚えている**: 形態と在庫・予約。`checked={showUnits.has(u)}`（`frontend/src/pages/inventory/InventoryFilterPanel.tsx:285`）。
  **空っぽ＝全件**（文言 `inventory.filterPanel.displayConditionsNote`「各項目で未選択なら全件」）。

**ページ番号の戻し方も項目で違う**: カテゴリーは `setPage(1)` する（`frontend/src/pages/inventory/InventoryPage.tsx:504`）が、
**列は `setPage(1)` しない**（`frontend/src/pages/inventory/InventoryPage.tsx:506-513`。列は絞り込みではなく見せ方なので件数が変わらない）。

### 「詳細フィルタ (n)」の n

`frontend/src/pages/inventory/InventoryPage.tsx:486-493` — `freshOnly` ＋ 提供者 ＋ コンディション ＋ 価格 ＋ 数量 の**5つだけ**を数える
（閲覧ページ `frontend/src/pages/viewer/InventoryView.tsx:144-150` の写し）。文字は
`frontend/src/pages/inventory/InventoryToolbar.tsx:234-240` で `buttonWithCount` / `button` を出し分け。

## 2. PC と共用になっている所（壊すと PC が変わる）

| 共用しているもの | PC 側 | スマホ側 |
|---|---|---|
| `InventoryFilterPanel` 本体 | `frontend/src/pages/inventory/InventoryPage.tsx:590-629` の同じ呼び出し | 同じ（`showSupplierSelect` だけ違う） |
| `data-testid="inventory-filter-toggle"` | `frontend/src/pages/inventory/InventoryToolbar.tsx:171` | `frontend/src/pages/inventory/InventoryToolbar.tsx:231` |
| `data-testid="inventory-sort-menu"` | `frontend/src/pages/inventory/InventoryToolbar.tsx:160`（`select`） | `frontend/src/pages/inventory/InventoryToolbar.tsx:217`（ボタン） |
| `data-testid="inventory-search"` | `frontend/src/pages/inventory/InventoryToolbar.tsx:131` | `frontend/src/pages/inventory/InventoryToolbar.tsx:187` |
| 項目 7〜11・13 | 出る | 出る |

PC だけに出るもの: `ContentToolbar`（`frontend/src/pages/inventory/InventoryToolbar.tsx:254-315`）・リセット（`:137-141`）・
24時間以内（`:142-155`）・提供者とコンディションの浮かぶ選択（`:285-304`）。

## 3. お手本（閲覧ページ）の作り

- `frontend/src/pages/viewer/InventoryView.tsx:46` — 画面の種類 `FilterView = "root" | "provider" | "condition"`
- `frontend/src/pages/viewer/InventoryView.tsx:94-95` — `filterView` と `optionQuery`（候補を絞る文字）
- `frontend/src/pages/viewer/InventoryView.tsx:189-196` — 次の画面へ／戻る（どちらも `optionQuery` を空に戻す）
- `frontend/src/pages/viewer/InventoryView.tsx:201-205` — パネルを開くときは必ず root に戻す
- `frontend/src/pages/viewer/InventoryView.tsx:271-284` — 押せる1行は `MultiSelect layout="row"` ＋ `onOpen`
- `frontend/src/pages/viewer/InventoryView.tsx:301-355` — 次の画面は「候補を絞る欄（`TextFieldControl`）＋ `MultiSelect layout="inline"`」
- `frontend/src/pages/viewer/InventoryView.tsx:223-240` — 画面が変わったときのフォーカス移動（root→次は「←」へ、戻ったら元の行へ）
- `frontend/src/pages/viewer/InventoryView.tsx:785-867` — 1枚の `Drawer` の中身を `filterView` で入れ替える。
  「←」と下の「決定する」は `filterView !== "root"` のときだけ渡す（`:363-380`）
- `frontend/src/pages/viewer/viewer.css:85-124` — root の縦並び／範囲入力の横並び／24時間以内の行／次の画面の枠

## 4. 共通部品がすでに持っている道具（**本便で `frontend/src/components/` を触らない根拠**）

| 要るもの | すでにある所 |
|---|---|
| 「←」を題の左に出す | `frontend/src/components/Drawer.tsx:49-53,149-160`（`onBack` と `backLabel` は2つセットで必須） |
| Esc だけ「戻る」にする | `frontend/src/components/Drawer.tsx:37,100-111`（`onEscape`。背景と ✕ は常に閉じる） |
| 下に「決定する」を置く | `frontend/src/components/Drawer.tsx:38,195-196`（`footer`） |
| スマホで画面の83%幅にする | `frontend/src/components/Drawer.css:121-131` の `--mobile-inset` ＋ `frontend/src/tokens.css:445`（`--drawer-panel-w-mobile-inset: 83%`） |
| 押せる1行（左に名前・右に今の値・右端に「>」） | `frontend/src/components/MultiSelect.tsx:124-137`（`layout="row"`・目印は `<testId>-row`） |
| その場に並ぶチェックの一覧 | `frontend/src/components/MultiSelect.tsx:139-170`（`layout="inline"`・目印は `<testId>-option-<値>`） |
| 一覧だけパネル全幅に広げる | `frontend/src/components/MultiSelect.css:31` の `--comp-multiselect-list-bleed`（呼ぶ側の CSS で値を渡す） |
| 行の右に出る文字 | `frontend/src/components/MultiSelect.tsx:82`（0件なら `allLabel`、選んだら名前を「, 」で連結） |

## 5. 壊れうる検査の棚卸し

### 画面検査（Playwright・`frontend/tests-e2e/visual-language/`）

| 検査 | 置き場所 | 本便での扱い |
|---|---|---|
| D6（パネルの中に24時間以内とリセットがある） | `frontend/tests-e2e/visual-language/inventory-toolbar-mercari.spec.ts` | 目印を据え置けばそのまま通る |
| D7（パネルの24時間以内が44px以上） | 同上 | 据え置き |
| **D8（ボタンの文字に数が出る・切ると減る）** | 同上 | **数字をやめる決定のため作り替えが必要** |
| D9（スマホに `ContentToolbar` が無い） | 同上 | 影響なし |
| D11（横の超過が0） | 同上 | パネルが `Drawer` になるので再確認が必要 |
| D12（PC 不変） | 同上 | **これが PC の歯止め** |
| **E1（上段に `inventory-expiry-warning` が0件）** | `frontend/tests-e2e/visual-language/inventory-series-sort-panel.spec.ts` | 注記はパネルの中にある。`Drawer` は**閉じても中身を DOM に残す**ため、中身を開いている間だけ描かないと**この検査が赤になる** |
| E10（注記がパネルの中・折り返す） | 同上 | 据え置き |
| E13（行のホバー規則が `@media (hover: hover)` の中） | 同上 | 本便で使う `.comp-multiselect__row:hover` は**囲めていない**（`frontend/src/components/MultiSelect.css:117-120`）＝宿題 |
| E14（PC 不変） | 同上 | PC の歯止め |
| **F5（空振り防止・いまは隣のボタンの文言の長さに寄生）** | `frontend/tests-e2e/visual-language/inventory-series-sort-panel.spec.ts:320-333` | 判定は `.inventory-toolbar__label` の `scrollWidth > clientWidth` のみ。**「詳細フィルタ」から ` (1)` が消えると隣が約24px短くなり、嘘の緑になりうる**＝本便で直す宿題 |

`openPanel()`（同 spec:34-36）は `[data-testid="supplier-drawer"].comp-drawer-panel--open` で
「開いている方だけ」に絞っている。**在庫表には設定・行の詳細と同じ目印の `Drawer` が複数ある**ため、
本便で4枚目が増えてもこの絞り方なら曖昧にならない。

### 単体テスト（`frontend/src/pages/inventory/`）

| 検査 | 置き場所 | 本便での扱い |
|---|---|---|
| K1〜K4（PC の操作台と API） | `frontend/src/pages/inventory/InventoryPage.toolbar.test.tsx:68-125` | PC は不変＝通るはず（回帰の歯止め） |
| **K6（スマホの操作台とパネルの中身）** | 同 `:127-153` | `inventory-condition-filter-button`（浮かぶボタン）が**行に変わるので赤になる**＝書き換え必須 |
| K7・K8（種別・並び替えのパネル） | 同 `:155-193` | 影響なし（別の `Drawer`） |
| `openPanel()` の見方 | 同 `:55` | `Drawer` は閉じても中身を残すので `--open` で見る。**本便の単体テストも同じ型で書く** |

## 6. 変える前に知っておく制約

- **ページの行数上限**: `frontend/scripts/check-page-size.js:19-20` が *Page.tsx を**800行**に制限。
  `frontend/src/pages/inventory/InventoryPage.tsx` は現在 **723行**＝残り77行。
  次の画面の仕組みをページに直接書くと上限に当たる。
- **CSS の命名の関所**は `mc-*` / `crm-*` の再定義だけを禁止（`frontend/scripts/check-css-class-naming.js:23-35`）。
  `inventory-*` の新しい CSS ファイルを足すのは禁止されていない。
- **浮かぶ選択（Popover）は画面端に合わせて寄せる作りに直っている**
  （`frontend/src/components/Popover.tsx:73-80`）し、一覧の最小幅も画面幅で抑えている
  （`frontend/src/components/MultiSelect.css:15`）。**つまり「いま浮かぶ選択が画面外に出る」不具合は無い**。
  本便の目的は不具合直しではなく**お手本と同じ形にそろえること**。

## 7. まだ測っていないこと（設計で埋める）

- 本番の実機で、いまのパネルの高さ・項目の押せる高さ・行の文字の切れは測っていない
  （閉じた枠の中なので便2.5 の実測対象外）。**便3 の合否は新しい spec（CI の画面検査）と実機で測る**。
