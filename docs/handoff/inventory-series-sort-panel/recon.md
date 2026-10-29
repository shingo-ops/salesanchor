# recon: 在庫表（/inventory）スマホのシリーズ・並び替えをパネルに（便2）

> この文書は何か（1行）: 在庫表のスマホで、種別のタブの行と並び替えのプルダウンを、
> 閲覧ページ（/viewer/）と同じ「枠なしの文字ボタン → 押すと右からパネル → 1つ選ぶと即反映して閉じる」形に
> するための下調べ。

**前の便**: 便1（PR #4842・上の操作台を閲覧ページと同じ作りに）。設計は
docs/handoff/inventory-toolbar-mercari/design.md。本便はその ⑫ の **便2（②）**。

## 1. いま残っている不具合（本番の実機で実測・2026-10-29）

便1 のあと、上の操作（検索・並び替え・詳細フィルタ）はすべて画面の中に入った。
**残っているのはタブの行**。

| 要素 | 実測（画面360px） |
|---|---|
| 注記（`inventory-expiry-warning`） | x=246・幅315・**右端 561**（201px はみ出し） |
| 種別タブ（`comp-tabs__tab`） | CI 実測で右端が画面を **24px** 超える |

注記は `.comp-tabs-bar__end` の中にあり、この枠は `margin-left: auto; flex-shrink: 0`（`frontend/src/components/Tabs.css`）
なので**縮まないし折り返さない**。

## 2. 写す元（閲覧ページ 便5）の作り

`frontend/src/pages/viewer/InventoryView.tsx`:

- **ボタン2つ**は `Button variant="ghost" size="tap"`。中身は
  `<span class="viewer-toolbar__label">いま選ばれている名前</span>` ＋ `ChevronRight` を
  CSS で90度回した山形。`aria-label` は「名前: 値」の形。
- **パネルは1枚の `Drawer`**。`choicePanel`（`"none" | "series" | "sort"`）という state で
  中身と題を切り替える。**Drawer を2枚持たない**。
- **行は `RadioControl`**。`onChange` と `onClick` の**両方**で「選ぶ→閉じる」を呼ぶ。
  これは「すでに選ばれている行を押しても閉じる」ようにするため（ネイティブ radio の change は
  値が変わったときしか起きない）。
- CSS は `frontend/src/pages/viewer/viewer.css` の `.viewer-toolbar__series`（`flex: 1 1 0`＋…で省略）/
  `__fixed`（`flex: 0 0 auto`）/ `__label` / `__caret` / `.viewer-choice-list` / `.viewer-choice-row`。

**写すときに直す点**: `.viewer-choice-row:hover` は `@media (hover: hover)` で囲まれていない。
スマホでは**タップした行に色が残る**（便13a で同じ問題を `.comp-multiselect__option` で直した）。
在庫表側は最初から囲む。閲覧ページ側は宿題に起票する。

## 3. 在庫表の今の作り

| 対象 | 場所 |
|---|---|
| タブの行 | `frontend/src/pages/inventory/InventoryPage.tsx` の `Tabs`（items＝すべて＋主要3種別／`extra`＝その他のプルダウン／`end`＝注記） |
| 主要3種別の定数 | 同ファイルの `MAIN_TCG_CODES`（`pokemon_booster_box` / `one_piece` / `dragon_ball`） |
| 種別の一覧 | 同ファイルの `tcgTypes`（`/products/tcg-types` から取得。`{ code, name_ja }`） |
| 選ばれている種別 | 同ファイルの `activeTab`（初期値 `pokemon_booster_box`）。API には `work_code` として渡す |
| 並び替え（スマホ） | `frontend/src/pages/inventory/InventoryToolbar.tsx` の `sortMenuMobile`（`SelectControl`・3択） |
| 注記の文言 | `inventory.expiryWarning` ほか3通り（`inventory.distributionOff` / `inventory.windowUnlimited`）を `windowHours` で出し分け |
| 操作台 | `frontend/src/pages/inventory/InventoryToolbar.css` の `.inventory-toolbar`（便1 で新設） |

## 4. 影響しない検査（自分で確かめた）

- `frontend/tests-e2e/visual-language/drawer-inert-closed.spec.ts` は**閲覧ページ（/viewer/）しか開かない**
  （`gotoViewer` のみ）。在庫表に Drawer を1枚増やしても**この検査は赤にならない**。
- `frontend/tests-e2e/visual-language/inventory-mobile-baseline.spec.ts` は測るだけで、
  閉じたドロワーが「はみ出し一覧」に増えても合否には使っていない。

## 5. 在庫表に今ある Drawer

- 設定パネル（`showSettings`）
- 行の詳細パネル（`InventoryRowDrawer`）

本便で**1枚だけ**増える（シリーズと並び替えで共用）。
