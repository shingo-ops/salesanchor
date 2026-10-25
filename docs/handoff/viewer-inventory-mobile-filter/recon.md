# recon: 閲覧ページの在庫表 — スマホの現在地（実機で測った一次情報）

> この文書は何か（1行）: PO クレーム「スマホだと絞り込みができない。提供者もコンディションも『すべて』の一択になっている」「上部の高さが画面を占有しすぎ」を直す前に、**実機で測った数字と、現物のコードの行**だけを置く場所。

**日付**: 2026-10-25
**ベース**: `origin/main` = `3698f91d8`（`release/viewer-inventory-mobile-filter` worktree）
**PO 報告（原文）**: 「閲覧用の在庫ページだがスマホからの利用ですと、絞り込みができません。『提供者：すべて』『コンディション：すべて』それぞれ『すべて』一択になっているので、改善していただけますと幸いです🙏」「メルカリと同じように選択したらチェックボックスを入れられるようにしたい」「ヘッダーの検索欄や絞り込みプルダウンなどの高さの使用が大きく画面を大きく占有している。サイズ感も使用感もメルカリのスマホアプリをベンチマークして修正してくれ」

**測り方**: 本番の閲覧ページ（`https://app.salesanchor.jp/viewer/`）を実機の Chrome（156.0.8078.47）で開き、
`adb forward tcp:9222 localabstract:chrome_devtools_remote` で開発者向けの口につないで、
`Runtime.evaluate` で `getBoundingClientRect()` と `getComputedStyle()` の値を**直接読んだ**。
画面は 1080x2340px・密度480（`adb shell wm size` / `wm density`）＝ **CSS 幅 360px**。
`innerWidth=360` / `innerHeight=672` / `devicePixelRatio=3` も実測で一致。

## 1. 対象はアプリの在庫表ではなく「閲覧ページ」

| 事実 | 引用 |
|---|---|
| クレームの画面は閲覧ページ。アプリの `/inventory` とは別のコード | `frontend/src/pages/viewer/InventoryView.tsx`（画面本体）／`frontend/src/pages/viewer/main.tsx:2-7`（入口。アプリ本体の CSS と辞書を読まない） |
| PO の文言「提供者」「コンディション」「すべて」は閲覧ページの辞書の語 | `frontend/src/locales/viewer/ja.json:46`・`:47`・`:49` |
| 閲覧ページは ADR-1019。画面はアプリの在庫表と同じ金型で作る決まり | `docs/adr/ADR-1019-inventory-viewer-separate-accounts.md:27` |
| 実機には PWA として入っている（前面は `SameTaskWebApkActivity`・題は「Sales Anchor Viewer」） | 2026-10-25 実測（`dumpsys window` の `mCurrentFocus`） |

## 2. 不具合の再現（実機・本番データ）

絞り込みを開き「提供者: すべて」を押した。

| 測った値 | 結果 |
|---|---|
| 画面の変化 | **無し**。押す前後のスクリーンショットで違う画素は 409 個、位置は `x 109..130 / y 51..79`（端末のステータスバー）だけ |
| 支援技術から見えるチェック欄の数 | **0 件** |
| ボタンの文字 | 「提供者: すべて」のまま |

→ PO の報告「『すべて』一択になっている」と一致する。

## 3. 原因（3つ。すべて実機で測って確定）

選択肢そのものは**ちゃんと出来ている**。`.comp-popover` は実在し、`opacity` は **1**、選択肢は **43 件**あった。
見えない・使えない理由は次の3つ。

### 3-1. 重なり順が逆（本命）

| 測った値 | 実測 | 引用 |
|---|---|---|
| 選択肢の一覧の重なり順 | **50** | `frontend/src/tokens.css:122`（`--z-dropdown: 50`）／`frontend/src/components/Popover.css:16-17` |
| 絞り込みパネルの重なり順 | **301** | `frontend/src/tokens.css:127`（`--z-drawer: 301`）／`frontend/src/components/Drawer.css:33` |
| 絞り込みパネルの大きさ | **x=0 y=0 幅360 高さ672**（画面いっぱい） | `frontend/src/components/Drawer.css:109-112`（767px 以下で `width: 100%`） |
| 絞り込みパネルの背景 | **`rgb(255,255,255)`（不透明）** | `frontend/src/components/Drawer.css:31` |

両方とも `document.body` の直下に出す（`frontend/src/components/Drawer.tsx:117`／`frontend/src/components/Popover.tsx:146-157`）兄弟で、どちらも `position: fixed`。
**50 は 301 の裏**に回り、不透明な白で完全に覆われる。

### 3-2. 一覧が画面より広い

| 測った値 | 実測 | 引用 |
|---|---|---|
| 一覧の最小幅 | **400px** | `frontend/src/components/MultiSelect.css:10` → `frontend/src/tokens.css:447` |
| 画面の幅 | **360px** | 実測（`innerWidth`） |
| 一覧の実際の位置 | **x = -29、幅 418** ＝ 左に29pxはみ出し、右は 389px で**両側とも画面外** | `frontend/src/components/Popover.tsx:63-68`（画面端で折り返す処理が無い） |
| 横スクロールで追えるか | 追えない（`position: fixed`。`document.scrollWidth` は 360 でページ側にはみ出しが出ない） | `frontend/src/components/Popover.css:16` |

### 3-3. 画面を下げてから開くと、一覧がさらに下へずれる（審査で判明・実機で確認）

`frontend/src/components/Popover.tsx:66` は `top` に `window.scrollY` を足すが、
基準の `triggerRect` は `getBoundingClientRect()`（同 `:100`）＝**すでに画面基準**で、
置き場の `.comp-popover` は `position: fixed`（`frontend/src/components/Popover.css:16`）。**スクロール量の二重加算**になっている。

| スクロール量 | 押したボタンの位置（画面基準） | 一覧が置かれた位置 | 正しい位置 |
|---|---|---|---|
| 0 | y=100・高さ44 | **y=150** | 150 ✓ |
| 400 | y=100・高さ44（パネルは固定なので動かない） | **y=550** | 150 ✗ |

画面の高さは 672px。400px 下げた状態では一覧の大半が**画面の下**に出る。
**この欠陥はパソコン側（`frontend/src/pages/viewer/InventoryView.tsx:275-281`）とアプリ側 `/inventory` にも残っている。**

### 3-4. そのほか（同時に測れた欠陥）

| 測った値 | 実測 | 引用 |
|---|---|---|
| 選択肢1行の高さ | **30px**（タップ目標 44px に未達） | `frontend/src/components/MultiSelect.css:20-28`／基準は `frontend/src/tokens.css:163`（WCAG 2.5.5） |
| 一覧の表示できる高さ | **200px** | `frontend/src/components/MultiSelect.css:16` → `frontend/src/tokens.css:346` |
| 一覧の中身の高さ | **1279px**（43件） | 実測（`scrollHeight`） |
| → 一度に見える件数 | 200 ÷ 30 ＝ **約6.6 件 / 43 件**。残りは入れ子のスクロールでしか出せない | — |

## 4. 上部に使っている高さ（便2の根拠・実機実測）

| 帯 | 画面上の y（CSS px） | 高さ | 中身 |
|---|---|---|---|
| ページの開始 | 93 | — | ブラウザのバーの下 |
| ヘッダー | 93 → 161 | **68** | 「在庫一覧」(30) ／「最終更新 11:41」(20) ／言語の選択 (44) |
| 種類の選択 | 161 → 217 | **56** | 「ポケモン (679)」部品44＋余白12 |
| 検索欄 | 217 → 273 | **56** | 幅280・高さ44 |
| 操作3つ | 273 → 329 | **56** | 24時間以内(85x44) ／ 並び替え(108x44) ／ 絞り込み(73x44) |
| **一覧の開始** | **329** | — | — |

→ **ページが一覧より上に使っている高さ＝ 329 − 93 ＝ 236px**。

### 4-1. 236px の内訳（DevTools の `getComputedStyle` で確認。便2 の直し所）

ページ座標（ブラウザのバーより下を 0 とする）で測り直した値。`uiautomator` 側の実測と一致した。

| 範囲 | 高さ | 正体 |
|---|---|---|
| 0 → 68 | **68** | `.viewer-header`（`frontend/src/pages/viewer/viewer.css:7-13` の `padding: var(--space-3) var(--space-4)` ＋ `gap: var(--space-3)`）。中身は 題28 ／ 最終更新22 ／ 言語44 |
| 68 → 112 | 44 | 種類の選択（`min-height: 44px`・枠線1） |
| 112 → 124 | **12** | `.viewer-toolbar` の `margin-top`（`frontend/src/pages/viewer/viewer.css:31` の `margin: var(--space-3) 0`） |
| 124 → 168 | 44 | 検索欄（幅280・`min-height: 44px`・枠線1） |
| 168 → 180 | **12** | `.viewer-toolbar` の `gap`（同 `:30`）。**360px 幅では操作台が2行に折り返している**（操作台の高さは 100 ＝ 44+12+44） |
| 180 → 224 | 44 | 24時間以内84 ／ 並び替え108 ／ 絞り込み72（すべて `min-height: 44px`・枠線1） |
| 224 → 236 | **12** | `.viewer-toolbar` の `margin-bottom` |

→ 削れるのは **ヘッダー 68** と **行間の余白 12×3 = 36** の計 **104**。
3行 × 48 ＝ 144 に収めれば、お手本の 146 とほぼ同じになる（今より **92px** 短い）。

**便2 で PO に決めてもらう点**: ヘッダーを無くすと「最終更新」と「言語の選択」の置き場が要る。
題「在庫一覧」は、この端末では PWA のタイトルバーが既に「Sales Anchor Viewer」を出しており二重。

## 5. お手本（メルカリ）との差

メルカリの実測は `docs/specs/design-system/visual-language/benchmark/mercari-search-filter.md`。

| 観点 | メルカリ | 閲覧ページ | 差 |
|---|---|---|---|
| 一覧より上に使う高さ | **146px**（48 × 3行） | **236px** | **+90px（1.6倍）** |
| 行数 | 3 | **4**（ヘッダーが余分） | +1 |
| 1行の高さ | 48（余白は行に含む） | 56〜68（部品44＋余白12） | +8〜20 |
| 操作部品の見た目 | 枠線なしの絵＋文字 | 枠つきの入力部品 | — |
| 絞り込みの選択肢の出し方 | 浮かせない（その場／次の画面） | **浮かせる**（`Popover`） | 原因3-1 |
| 選択肢1行の高さ | 60.7〜68.7・行まるごと押せる | **30**・文字とチェック欄だけ | −30.7〜38.7 |
| 選択肢の一覧の幅 | パネル全幅（300） | **400**（画面 360 より広い） | +40 |
| 選択肢の打ち切り | 画面の高さまで使う | **200px で打ち切り**（中身1279） | — |
| 選んだ結果の見せ方 | 選んだ名前をカンマでつなぐ | 件数（`countLabel`） | — |

## 6. なぜ今まで検査で捕まらなかったか

| 事実 | 引用 |
|---|---|
| CI で実際に走る Playwright は3幅検査だけで、対象は `frontend/tests-e2e/visual-language/` 配下に限定 | `frontend/playwright.config.ts:64`・`:69`・`:74`／`.github/workflows/e2e.yml:247`（`playwright` ジョブは `if: false`） |
| その `frontend/tests-e2e/visual-language/` に**閲覧ページの spec は1本も無い** | ディレクトリの中身は `frontend/tests-e2e/visual-language/inbox-baseline.spec.ts`・`inbox-helpers.ts`・`inbox-single-column.spec.ts`・`inventory-helpers.ts`・`inventory-mobile-baseline.spec.ts`・`inventory-raw-text-mobile.spec.ts` の6本のみ |
| 単体テストはスマホ版も試すが、確かめているのは絞り込みボタンが在るかだけ。パネルを開いて選択肢を操作するテストが無い | `frontend/src/pages/viewer/InventoryView.test.tsx:124-142` |
| 単体テストの土台（jsdom）には重なり順も描画も無いため、3-1〜3-4 は**原理的に検出できない** | 同上 |
| ページ全体の横はみ出し検査でも捕まらない | 実測 `document.scrollWidth` = 360（はみ出し 0） |

## 7. 未確認・破棄したもの（推測で埋めない）

- **便2（上部の高さ）の直し方は未設計**。§4 の実測は取れたが、どの行をどう減らすかは便2の設計で決める。
- 破棄した引用1件: 下請け調査がアプリ側 `frontend/src/pages/inventory/InventoryFilterPanel.tsx:118-143` を「クレームの箇所」として報告したが、**そこは `/inventory`（社内アプリ）であり閲覧ページではない**。アプリ側の絞り込みパネルは `Drawer` ではなく画面に直接置く `<section>`（`frontend/src/pages/inventory/InventoryPage.tsx:486`・`frontend/src/pages/inventory/InventoryFilterPanel.tsx:103-116`）なので §3-1 は起きない。§3-2・§3-3・§3-4 はアプリ側にも当てはまる（別便の宿題）。
- 審査で訂正した引用: `frontend/src/components/Drawer.css:30`→**`:31`**（不透明な背景）、`:105-112`→**`:109-112`**（スマホで全幅）。
