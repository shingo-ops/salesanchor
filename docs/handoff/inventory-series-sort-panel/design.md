# design: 在庫表（/inventory）スマホの種別・並び替えをパネルに（便2／全4便の2本目）

> この文書は何か（1行）: 在庫表のスマホで、**種別のタブの行**と**並び替えのプルダウン**を、
> 閲覧ページ（/viewer/）と同じ**枠なしの文字ボタン → 押すと右からパネル → 1つ選ぶと即反映して閉じる**
> 形にする。あわせて、右に切れて読めない**注記を詳細フィルタの中へ移す**。

**recon**: docs/handoff/inventory-series-sort-panel/recon.md
**審査**: docs/handoff/inventory-series-sort-panel/review-opus.md（r1 = REVISE。本書は r1 を取り込んだ版）
**土台**: `release/inventory-series-sort-panel`（`origin/main` 起点）
**前の便**: docs/handoff/inventory-toolbar-mercari/design.md（便1・PR #4842）の ⑫ の **便2（②）**。

**PO 指示**: 閲覧用のページと全く同じにしてくれ（2026-10-29）。進め方は順番に4便。
**PO 決定（2026-10-29）**: 注記（LINE の投稿から N 時間以内…）は**詳細フィルタの中に移す**。

## ① 区分：A（見た目と置き場所の変更）

データの読み書き・絞り込みの計算・並び替えの計算・API への問い合わせは**一切変えない**。
変えるのは**スマホのときに、どの操作をどう出すか**だけ。**PC は1px も動かさない**。

## ② KGI（PO が実機で○×を判定できる粒度）

| # | PO が見て○×を言えること |
|---|---|
| K1 | スマホの在庫表に**タブの行（すべて／ポケモン…／その他と注記）が無くなっている** |
| K2 | 代わりに、検索欄の下の段に**いま選ばれている種別の名前（例: ポケモン）が枠なしの文字で出ていて、右に下向きの山形**が付いている |
| K3 | それを押すと**右からパネル**が出て、種別の一覧（すべて＋種別）が並ぶ。**1つ選ぶと即座に一覧が変わってパネルが閉じる** |
| K4 | **すでに選ばれている種別をもう一度押しても閉じる**（固まらない） |
| K5 | 「並び替え」も同じで、**押すと右からパネル**が出て、4つ（既定／価格が安い順／在庫が多い順／投稿が新しい）から選ぶと即反映して閉じる |
| K6 | 並び替えで**「価格が安い順」など既定以外を選ぶと、ボタンの文字がその名前に変わる**。**「既定」を選ぶとボタンの文字は「並び替え」に戻る**（閲覧ページと同じ挙動） |
| K7 | **注記（LINE の投稿から N 時間以内…）が「詳細フィルタ」の中で全文読める**（上では切れていた。**折り返して全部出る**） |
| K8 | 上の操作の段は**4つ**（検索／種別／並び替え／詳細フィルタ）で、**横に切れているものが無い** |
| K9 | **タップした行に色が残らない**（指を離すと元に戻る） |
| K10 | **PC は何も変わらない**（タブの行も並び替えのプルダウンも今までどおり） |

## ③ KPI（機械で測る値）

| # | 値 | いま | この便の後 | 出どころ |
|---|---|---|---|---|
| P1 | 注記の右端 | **561px**（画面360px・本番実機） | **上の領域に存在しない**（詳細フィルタの中へ） | 本番実機の実測 |
| P2 | 種別タブの画面外へのはみ出し | 24px（便1 の CI ログ） | **スマホではタブ自体が無い** | 便1 の CI |
| P3 | 操作台 `.inventory-toolbar` の子の数 | 3 | **4**（検索／種別／並び替え／詳細フィルタ） | 本便 |
| P4 | 操作台の子の右端の最大値 | 267px | **画面幅以下** | 本便 |
| P5 | 操作台の高さ | 108px | **120px以下**（3行に折り返さない） | 便1 の上限を踏襲 |
| P6 | 種別・並び替えのボタンの押せる高さ | 48px（並び替え） | **48px以上**（2つとも） | ADR-140 ／ お手本48dp |
| P7 | パネルの行の押せる高さ | — | **44px以上** | ADR-140 |
| P8 | 横スクロールの超過（document / `.mobile-content`） | 0 | **0のまま** | 便0 の実測 |
| P9 | PC（幅1280）のタブの行と並び替え | 現状 | **変わらない** | PO 決定（PC 不変） |

## ④ 設計（How）

### 4-1. スマホでは `Tabs` を描かない

`frontend/src/pages/inventory/InventoryPage.tsx` の `Tabs` の呼び出しを `!isMobile` で囲む。
**PC はまったく同じ DOM のまま**。

| タブの行が持っていた役割 | 行き先 |
|---|---|
| 主要3種別＋すべての切り替え | **種別のボタン＋パネル**（4-2・4-3） |
| `extra` の「その他」プルダウン | 同じパネルの中に**全種別を並べる**ので不要 |
| `end` の注記 | **詳細フィルタのパネルの中へ**（4-5・PO 決定） |

### 4-2. 操作台に「種別」のボタンを足し、「並び替え」を文字ボタンに替える

スマホ分岐（便1 で作った `.inventory-toolbar`）の中身を**4つ**にする。

| 順 | 中身 | `data-testid` | クラス |
|---|---|---|---|
| 1 | 検索欄（便1 のまま） | `inventory-search` | `inventory-toolbar__search` |
| 2 | **種別**（新規・枠なしの文字ボタン） | **`inventory-tab-select`** | `inventory-toolbar__series` |
| 3 | **並び替え**（`SelectControl` → 枠なしの文字ボタン） | **`inventory-sort-menu`（今と同じ名前のまま）** | `inventory-toolbar__fixed` |
| 4 | 詳細フィルタ（便1 のまま） | `inventory-filter-toggle` | `inventory-toolbar__fixed` |

**並び替えの `data-testid` は `inventory-sort-menu` のまま変えない**（審査 H1）。
便1 で作った `frontend/tests-e2e/visual-language/inventory-toolbar-mercari.spec.ts` が
スマホ幅でこの名前を直接掴んでいるので、名前を変えると**12件赤になる**。
**写す元の閲覧ページも PC の `select` とスマホのボタンで同じ `viewer-sort-menu` を使い回している**
（`frontend/src/pages/viewer/InventoryView.tsx` の2か所）。同じやり方にそろえる。

ボタンの作りは閲覧ページの `seriesTrigger` / `sortTrigger` をそのまま写す:
`Button variant="ghost" size="tap"` ＋ `<span class="inventory-toolbar__label">いま選ばれている名前</span>`
＋ `ChevronRight` を CSS で90度回した山形。`aria-label` は「名前: 値」の形。

- **種別のボタンの文字**: `activeTab === "all"` なら `t("common.all")`、それ以外は
  **4-3 の合成した一覧**から引いた表示名（見つからなければ code をそのまま＝今のタブのラベルと同じ規則）。
- **並び替えのボタンの文字**: いまの `sortField:sortDir` が3択のどれかなら**その名前**、
  そうでなければ `t("inventory.sortMenu.placeholder")`（＝並び替え）。閲覧ページと同じ出し分け。
  **つまり「既定」を選ぶと文字は「並び替え」に戻る**（審査 M1。K6 はこれに合わせてある）。
- **`sortMenuMobile`（`SelectControl`）は削除**する。PC 分岐の `sortMenu` はそのまま残す。

### 4-3. パネルは1枚の `Drawer`。**親のページ（`frontend/src/pages/inventory/InventoryPage.tsx`）が持つ**

`frontend/src/pages/inventory/InventoryToolbar.tsx` は冒頭に
「状態は親が持ち props で受け取る」**表示専用部品**と明記されている（審査 M5）。だから:

- **state も `Drawer` も `frontend/src/pages/inventory/InventoryPage.tsx` に置く**。
  `type InventoryChoicePanel = "none" | "series" | "sort"`。
- `InventoryToolbar` には `onOpenChoice: (p: "series" | "sort") => void` と、
  ボタンに出す文字（`currentTypeLabel` / `currentSortLabel`）を props で渡すだけ。
- **`Drawer` は `{isMobile && (...)}` で囲む**（審査 M4。PC にマウントすると
  `supplier-drawer` と `drawer-close` が PC でも1枚増える）。
- 題は `choicePanel === "sort"` なら `t("inventory.sortMenu.placeholder")`、
  そうでなければ `t("inventory.typeSelect")`。

**種別の選択肢の作り方（審査 H3 の修正）**:
`tcgTypes` は `/products/tcg-types` から取るが、**失敗しても黙って捨てる実装**で、
空配列になり得る（既存の単体テストも空で mock している）。`tcgTypes` 全件だけにすると
**取得できなかったときに種別が1つも選べなくなる**＝機能の退行。そこで:

```
選択肢 = 「すべて」
       ＋ MAIN_TCG_CODES（定数3件）を先頭に
       ＋ tcgTypes のうち MAIN_TCG_CODES に無いもの
（表示名は tcgTypes から引き、無ければ code をそのまま）
```

これで**今まで選べたものは必ず選べる**（今のタブと同じ保証）。

**行の作り（K4 の肝）**: `RadioControl` を使い、**`onChange` と `onClick` の両方**で
「選ぶ→閉じる」を呼ぶ。ネイティブ radio の `change` は**値が変わったときしか起きない**ので、
`onClick` が無いと**すでに選ばれている行を押しても閉じない**（閲覧ページ 便5 の審査で見つかった欠陥）。
**`pick` は同じ値を入れ直す `setState` なので、二重に呼ばれても害がない**ことが前提（審査 M3）。
トグル（反転）で書いてはいけない。
`RadioControl` には **`name` を必ず渡す**（`inventory-type-choice` / `inventory-sort-choice`。審査 M2）。

- 種別の行: `data-testid` は `inventory-type-option-<code>`（「すべて」は `inventory-type-option-all`）。
- 並び替えの行: 先頭に「既定」、続けて3択。`data-testid` は `inventory-sort-option-<value>`。
  既定の値は `release_date:desc`。
- 行の markup は閲覧ページと同じ `<label>` で包み、文字は `<span class="inventory-choice-row__label">`（審査 L1）。

**選んだときの処理は今あるものをそのまま呼ぶ**: 種別は `setActiveTab` ＋ `setPage(1)`、
並び替えは今の `onSortMenuChange` と同じ処理。

### 4-4. CSS（`frontend/src/pages/inventory/InventoryToolbar.css` に足す）

閲覧ページ `frontend/src/pages/viewer/viewer.css` の規則を写す。

```css
.inventory-toolbar > .inventory-toolbar__series {
  flex: 1 1 0;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.inventory-toolbar__label { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.inventory-toolbar__caret { transform: rotate(90deg); flex-shrink: 0; }
.inventory-choice-list { display: flex; flex-direction: column; }
.inventory-choice-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  width: 100%;
  min-height: var(--size-icon-btn-lg);
  padding: var(--space-1) var(--space-2);
  font-size: var(--font-sm);
  color: var(--text-primary);
  cursor: pointer;
}
.inventory-choice-row__label { min-width: 0; }
/* タップした行に色を残さない（便13a の教訓。写す元は囲めていない＝⑫ M1 に起票） */
@media (hover: hover) {
  .inventory-choice-row:hover { background: var(--bg-hover); }
}
/* 詳細フィルタの中に移した注記は折り返す（審査 H2） */
.inventory-notice { margin: 0; font-size: var(--font-xs); color: var(--text-secondary); }
```

### 4-5. 注記を詳細フィルタの中へ（PO 決定）

文言の組み立て（`windowHours` による3通りの出し分け）は**1文字も変えない**。
それを `frontend/src/pages/inventory/InventoryFilterPanel.tsx` に**任意 props `notice`** として渡し、
**`showSupplierSelect` が真のときだけ**、便1 で先頭に置いた「24時間以内」の**すぐ下**に出す。

**`white-space: nowrap` を必ず外す**（審査 H2）。今の注記は `Tabs` の `end` の中で
`whiteSpace: "nowrap"` を直書きしている。詳細フィルタの中は内側が約286pxしかなく、
注記は約315px あるので、**nowrap のまま移すと横に29pxはみ出して P8（横スクロール0）が壊れる**。
移した先では 4-4 の `.inventory-notice` を当て、**折り返して全文出す**（K7）。

`data-testid` は `inventory-expiry-warning` のまま（PC 側と同じ名前。PC は `Tabs` の `end`、
スマホは詳細フィルタの中で、**同時には出ない**ので二重にならない）。

### 4-6. 辞書

**在庫表はこの概念を「種別」と呼ぶ**（既存の `inventory.filter.allTypes`＝全種別・
`inventory.filter.otherTypes`＝その他）。閲覧ページの語は「シリーズ」だが、
**在庫表ではページの既存の言葉にそろえる**（審査 M6。PO に報告して違和感があれば1語で直せる）。

- `inventory.typeSelect` を ja/en 1キーずつ追加（ja「種別」／en「Type」）
- `inventory.sortMenu.default` を ja/en 1キーずつ追加（ja「発売日が新しい順（既定）」／en は閲覧ページの `viewer.sort.default` の en に合わせる）

ほかは既存キーを使う: `common.all` ／ `inventory.sortMenu.placeholder` ／ `.priceAsc` ／ `.stockDesc` ／ `.postedDesc`。

### 4-7. 触らないもの（境界）

- `frontend/src/components/` 配下すべて（`Tabs` も `Drawer` も `Button` も金型は不変）
- 閲覧ページ `frontend/src/pages/viewer/` 一式（ADR-1019）
- `resetAll` の中身・API への問い合わせ・絞り込みと並び替えの計算・注記の文言の組み立て
- PC 分岐（`Tabs` の呼び出し・`sortMenu`・`search`・`filterButton`）

## ⑤ Acceptance Criteria（新しい spec で測る）

新 spec `frontend/tests-e2e/visual-language/inventory-series-sort-panel.spec.ts`。

**走らせる幅を絞る**（審査 H5）: CI の画面検査は**1ジョブ・持ち時間10分**で、便1 の時点で
655件・7.4分まで来ている。本 spec は**幅360を基本**にし、**E2 と E11 だけ390でも**測る。
PC の判定（E14）は1280。便1 の spec が既に390の寸法を見ているので二重に測らない。

| # | 測ること | 幅 |
|---|---|---|
| E1 | スマホでタブの行（`[role=tablist]`）が**無い**／`inventory-expiry-warning` が**詳細フィルタの外に無い** | 360 |
| E2 | `.inventory-toolbar` の子が**4つ**で、全部の右端が画面幅以下 | 360・390 |
| E3 | `inventory-tab-select` と `inventory-sort-menu` の**高さが48px以上**で、両方 viewport の中にある | 360 |
| E4 | `inventory-tab-select` の文字が**いま選ばれている種別の名前**（CI の mock の表示名と一致） | 360 |
| E5 | `inventory-tab-select` を押すと**パネルが開き**、行が「すべて」＋種別の数だけ並ぶ（**mock の種別は3件以上**にする） | 360 |
| E6 | その行のうち**いま選ばれていないもの**を押すと**パネルが閉じ**、`inventory-tab-select` の文字が**その名前に変わる** | 360 |
| E7 | **すでに選ばれている行をもう一度押してもパネルが閉じる**（K4） | 360 |
| E8 | `inventory-sort-menu` を押すとパネルが開き、行が**4つ**。**「価格が安い順」を押すと閉じ、ボタンの文字がその名前に変わる**。続けて**「既定」を押すと文字が「並び替え」に戻る** | 360 |
| E9 | パネルの行の**押せる高さが44px以上** | 360 |
| E10 | 「詳細フィルタ」を開くと、その中に `inventory-expiry-warning` が**あり、幅がパネルの内側に収まっている**（折り返している） | 360 |
| E11 | `.inventory-toolbar` の**高さが120px以下** | 360・390 |
| E12 | document と `.mobile-content` の**横の超過が0** | 360 |
| E13 | 行のホバーの規則が `@media (hover: hover)` の中にある（CSSOM を辿って静的に測る。先例 `frontend/tests-e2e/visual-language/viewer-filter-panel-mercari.spec.ts`） | 360 |
| E14 | **PC（幅1280）が変わっていない**: タブの行が**ある**／`inventory-sort-menu` が **`select` 要素**／`inventory-tab-select` が**無い**／注記が `.comp-tabs-bar__end` の中に**ある** | 1280 |
| E15 | 空振り防止: 行の `onClick` を外すと E7 が赤になることを、手元の単体テスト（`frontend/src/pages/inventory/InventoryToolbar.test.tsx`）で1回確かめて記録する | 単体 |

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| スマホでタブの行が消え、注記が上から消える | Playwright: `frontend/tests-e2e/visual-language/inventory-series-sort-panel.spec.ts` E1 |
| 操作が4つとも画面の中に入る | Playwright: 同 spec E2・E3 |
| 種別がパネルで選べて即反映して閉じる | Playwright: 同 spec E5・E6 |
| すでに選ばれている行を押しても閉じる | Playwright: 同 spec E7／単体: `frontend/src/pages/inventory/InventoryToolbar.test.tsx`（E15） |
| 並び替えがパネルで選べ、文字が正しく戻る | Playwright: 同 spec E8 |
| パネルの行が44px以上 | Playwright: 同 spec E9 |
| 注記が詳細フィルタの中で折り返して全文読める | Playwright: 同 spec E10 |
| 3行に折り返さない／横スクロールが出ない | Playwright: 同 spec E11・E12 |
| タップした行に色が残らない | Playwright: 同 spec E13 |
| PC が変わっていない | Playwright: 同 spec E14 |
| 種別マスタが取れなくても今まで選べた種別が選べる | 単体: `frontend/src/pages/inventory/InventoryToolbar.test.tsx`（`tcgTypes` を空で描いて `MAIN_TCG_CODES` の3件が出ること） |
| 便1 の spec が赤にならない（`inventory-sort-menu` を残したこと） | CI の画面検査で `frontend/tests-e2e/visual-language/inventory-toolbar-mercari.spec.ts` が全件緑 |
| 既存の在庫表 spec が赤にならない | CI の画面検査が全件緑 |
| 既存の単体テストを新しい形に合わせて更新してある | 単体: `frontend/src/pages/inventory/InventoryPage.toolbar.test.tsx`・`frontend/src/pages/inventory/InventoryPage.tabs.test.tsx` |
| 共通部品に1文字も触っていない | `git diff --stat` に `frontend/src/components/` が出てこないこと |
| 直値・色・トークン規約に違反していない | `npm run check:all`（終了コード0）・pre-commit の ADR-067 検査 |
| 型が通る | `cd frontend && npx tsc --noEmit`（終了コード0） |
| 辞書の ja/en のキー数が一致する | `npm run check:all` の i18n 検査（ADR-027） |

## ⑥ 触るファイル

| ファイル | 変更 |
|---|---|
| `frontend/src/pages/inventory/InventoryToolbar.tsx` | 種別・並び替えの文字ボタンを作る。`sortMenuMobile`（`SelectControl`）を外す。選択肢の行を作る関数を持つ |
| `frontend/src/pages/inventory/InventoryToolbar.css` | 4-4 の規則を追加 |
| `frontend/src/pages/inventory/InventoryPage.tsx` | `Tabs` を `!isMobile` で囲む。`choicePanel` の state と `Drawer`（`isMobile` のときだけ）を持つ。種別の選択肢を合成する。注記を `InventoryFilterPanel` に渡す |
| `frontend/src/pages/inventory/InventoryFilterPanel.tsx` | 任意 props `notice` を受け、スマホのときだけ「24時間以内」の下に出す |
| `frontend/src/locales/ja.json` / `frontend/src/locales/en.json` | `inventory.typeSelect` と `inventory.sortMenu.default` を1キーずつ追加 |
| `frontend/src/pages/inventory/InventoryToolbar.test.tsx` | **新規**（E15・種別マスタが空でも3件出ること） |
| `frontend/src/pages/inventory/InventoryPage.toolbar.test.tsx` | 新しい形に更新（スマホの操作台の子が4つ・`inventory-sort-menu` が `select` でなくなる） |
| `frontend/src/pages/inventory/InventoryPage.tabs.test.tsx` | **K5b を反転**（スマホでは `[role=tablist]` が**無い**ことを固定する。消さずに守り手を残す。審査 M7） |
| `frontend/tests-e2e/visual-language/inventory-helpers.ts` | `/products/tcg-types` の mock を**3件以上**にする（E5〜E7 が意味を持つように。審査 M8）。既存 spec が赤にならないことを確認する |
| `frontend/tests-e2e/visual-language/inventory-series-sort-panel.spec.ts` | **新規**（E1〜E14） |
| `docs/handoff/inventory-series-sort-panel/recon.md` ／ `docs/handoff/inventory-series-sort-panel/design.md` ／ `docs/handoff/inventory-series-sort-panel/review-opus.md` | 本書類 |

## ⑦ 戻し方

PR をそのまま revert すれば元に戻る。新しいトークンは足さない。辞書の追加キーは使われなくなるだけ。

## ⑧ 削除するファイル

なし（`sortMenuMobile` の削除はファイル内の変更）。

## ⑨ 外部・過去事例の参照と我々への応用

| 参照 | 我々への応用 |
|---|---|
| **お手本（メルカリ）の実測**（`docs/specs/design-system/visual-language/benchmark/mercari-search-filter.md` §0・§4） | 選択肢は「その場に全部出す」か「次の画面に進む」の2通りだけ。浮かせない。→ OS 標準のプルダウンをやめ、右から出るパネルにする |
| **閲覧ページ 便5（PR #4759）** | 同じ形を本番で動かしている。ボタン・パネル・行の作りを写す。**testid を PC と使い回す作法も写す**（審査 H1） |
| **閲覧ページ 便5 の審査で見つかった欠陥** | ネイティブ radio の `change` は値が変わらないと起きない＝すでに選ばれている行を押しても閉じない。`onClick` でも同じ処理を呼ぶ → E7・E15 |
| **便13a の sticky hover** | スマホでタップした行に色が残る。`@media (hover: hover)` で囲む → E13。写す元は囲めていないので ⑫ M1 に起票 |
| **便1 の PC 不変の肝** | スマホと PC で JSX 変数を共用すると PC も変わる → 本便もスマホ専用の変数だけを触る・`Drawer` は `isMobile` で囲む |
| **便13a の「既存検査が前提にしている段取りも数える」教訓** | 便1 の spec が `inventory-sort-menu` を直接掴んでいた。**判定の中身ではなく目印の名前**で赤になる → 名前を据え置く |

## ⑩ 弊害・トレードオフ

- **種別の切り替えが1タップ増える**。いまはタブ自体が画面からはみ出して確実には押せないので実質は改善。
- **パネルの行に件数を出さない**。閲覧ページは「ポケモン (874)」のように件数を出すが、在庫表は
  一覧をページ単位でサーバから取るため**種別ごとの件数を手元に持っていない**（⑫ M2）。
- **種別マスタ（`/products/tcg-types`）が取れないとき**、選択肢は「すべて」＋主要3種別だけになり、
  **表示名が英語のコードのまま**出る（今のタブのラベルと同じ規則。審査 H4）。
  今より悪くはならないが、主操作の文字になるぶん目立つ。
- **スマホで種別の一覧が縦に長くなる可能性**がある。パネルは縦スクロールする。
- 上の段の**種別のボタンは幅が狭い**（約54px）ので、長い種別名は…で切れる。閲覧ページと同じ挙動。
- **スマホとPCで同じ `data-testid` を使い回す**（`inventory-sort-menu`）。要素の種類（`select` かボタンか）が
  幅で変わるので、検査は**要素の種類まで見る**必要がある（E14 で固定）。

## ⑪ 維持の仕組み

守り手: `frontend/tests-e2e/visual-language/inventory-series-sort-panel.spec.ts`（E1〜E14・CI の画面検査で毎回走る）

- E14（PC 不変）で、以後の便で PC を壊したらすぐ赤になる。
- E7 は単体テスト（`frontend/src/pages/inventory/InventoryToolbar.test.tsx`）でも二重に守る。
- E13 で sticky hover の退行を静的に捕まえる。
- `frontend/src/pages/inventory/InventoryPage.tabs.test.tsx` の K5b を反転させ、
  「スマホにタブの行が復活したら赤」にする。

## ⑫ 継続（この便の後）

| # | 内容 |
|---|---|
| **便3（③）** | 詳細フィルタを右から出るパネルにし、中を「項目を押す→次の画面で選ぶ」形に。在庫表にしかない操作はこのパネルの中に残す（PO 決定） |
| **便4（④）** | 検索を「押すと検索画面が開く」形に（履歴と候補） |
| M1 | **閲覧ページの `.viewer-choice-row:hover` が `@media (hover: hover)` で囲まれていない**（スマホでタップした行に色が残る）。閲覧ページ側の便として起票 |
| M2 | パネルの行に**種別ごとの件数**を出す（サーバ側の対応が要る） |
| M3 | **`frontend/src/pages/inventory/InventoryPage.tsx` の `resetAll` のコメントが「発売日の早い順」でコードと逆**（実際は新しい順）。本便で同じ語を PO に見せるので、どちらが正かを確かめて直す（審査 L2） |
| M4 | **`tcgTypes` の取得失敗を黙って捨てている**（再試行なし）。種別が英語コードで出る原因。別便で扱う |
| M5 | 便1 の L3（効いている数の定義）・便0 の C2/C3/C4/C5・原文パネルのタブ44px |

## 対象 ADR

- **ADR-144**（UI 共通部品の遵守ガバナンス）: 金型の新設も変更もなし。`Button` / `Drawer` / `RadioControl` の
  既存の組み合わせだけ。閲覧ページ 便5 と同型。
- **ADR-067**（デザイントークン強制）: 色・寸法は直値を書かない。flex の数値と `100%`・`rotate(90deg)` は
  トークン対象外（閲覧ページの先例と同じ）。
- **ADR-140**（タップ領域の下限 44px）: ボタンは48px、パネルの行は44px以上（P6・P7）。
- **ADR-027**（i18n 強制）: 追加は ja/en 各2キー。キー数は一致させる。
- **ADR-1019**（閲覧ページはアプリと別コード）: 本便は `frontend/src/pages/viewer/` に触らない。
