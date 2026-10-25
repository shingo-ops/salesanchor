# recon: 閲覧ページ「シリーズ・並び替え」をパネル選択へ（便5）の現在地

> この文書は何か（1行）: PO 指示「シリーズと並び替えのプルダウンがでかすぎて見づらい、メルカリみたいに」を実装する前の、現在地の一次情報。

**日付**: 2026-10-25
**親（あるべき姿）**: `docs/specs/design-system/visual-language/README.md`
**対象**: 閲覧ページ `frontend/src/pages/viewer/`（**アプリ本体の `frontend/src/pages/inventory/` とは別コード**。正本は ADR-1019）
**前便**: 便3 `docs/handoff/viewer-top-compact/design.md`（PR #4752・本番反映済み）／便2 `docs/handoff/viewer-filter-subscreen/design.md`（PR #4740）
**worktree / commit**: `/root/worktrees/salesanchor/release-viewer-choice-sheet` / `b8a24f592`
**ADR 検索**: `git grep -i "金型" docs/adr/` ＋ `docs/adr/FEATURE-INDEX.md` → ADR-144（UI 金型ガバナンス）・ADR-1019（閲覧ページ）・ADR-140（タップ領域44px）・ADR-067（トークン参照のみ）・ADR-027（文言は t() 経由）・ADR-1014（並びの既定）が該当。新規 ADR は不要（既存の枠内）。

## 1. PO 指示（原文・2026-10-25）

> ポケモンなどの絞り込みと並び替えの絞り込み機能のプルダウンがでかすぎて見づらい、修正できる？メルカリみたいに

**PO 判断（同日・選択肢を提示して受領）**: **「両方（メルカリの形へ）」**
＝①押す前のボタンは**枠なしの文字だけ**にする ②押した後は**OS 標準のプルダウンをやめ、自分たちのパネルで選ぶ**。

| PO の言葉 | 実物 | 根拠 |
|---|---|---|
| ポケモンなどの絞り込み | 「シリーズ」の選択（スマホのみ・`SelectControl`＝ネイティブ `<select>`） | `frontend/src/pages/viewer/InventoryView.tsx:430`（`data-testid="viewer-tab-select"`） |
| 並び替えの絞り込み機能 | 「並び替え」の選択（スマホ・PC 共用の変数） | `frontend/src/pages/viewer/InventoryView.tsx:366`（`sortMenu`・`data-testid="viewer-sort-menu"`） |
| プルダウン | ネイティブ `<select>` を押したときに OS が出す一覧（シリーズは最大43件） | `frontend/src/components/Select.tsx:92-108`（`<select>` を返す） |
| メルカリみたいに | 枠線なしのボタン → パネルで選ぶ | `docs/specs/design-system/visual-language/benchmark/mercari-search-filter.md:41`・`:43` |

## 2. いまの実装（スマホの操作台）

| 要素 | 行 | 部品 | 要点 |
|---|---|---|---|
| 検索欄 | `frontend/src/pages/viewer/InventoryView.tsx:333-345` | `TextFieldControl` | `viewer-toolbar__search`（1行独占） |
| シリーズ | `frontend/src/pages/viewer/InventoryView.tsx:429-440` | `SelectControl`（既定 size=md・`appearance="bare"`） | 選択肢は「すべて (件数)」＋ `seriesTabs()` の全件。**ボタンの文字に件数が入る**ため長い |
| 並び替え | `frontend/src/pages/viewer/InventoryView.tsx:366-390` | `SelectControl size="sm"` | **スマホ（`:441`）と PC（`:486`）で同じ変数を使い回している** |
| 絞り込み | `frontend/src/pages/viewer/InventoryView.tsx:442-453` | `Button variant="secondary" size="sm"` | 便3 で件数表示を追加 |

**並び替えの隠れた4つ目**: `placeholder`（`frontend/src/pages/viewer/InventoryView.tsx:371`）の空欄を選ぶと
`DEFAULT_SORT_KEY`/`DEFAULT_SORT_DIR` に戻る（`frontend/src/pages/viewer/InventoryView.tsx:374-383`）。
既定は発売日の新しい順（`frontend/src/pages/viewer/viewerFilter.ts:11-13`・ADR-1014）。
3択は `frontend/src/pages/viewer/viewerFilter.ts:15`（`SORT_MENU_VALUES`）。
→ **パネルにするなら「既定」を含めた4行**にしないと、いまできる操作（既定に戻す）が消える。

## 3. 使える金型（**新設は不要**）

| 要るもの | 既にあるか | 根拠 |
|---|---|---|
| 枠も背景もない文字だけのボタン | **ある**＝`variant="ghost"`。`.comp-btn` の枠は `1px solid transparent`、ghost は `background: transparent` | `frontend/src/components/Button.css:2-18`・`:68-72`／variant 一覧は `frontend/src/components/Button.tsx:7` |
| 1つだけ選ぶ入力 | **ある**＝`RadioControl`（ネイティブ radio 1つ・`div`/`label` を増やさない） | `frontend/src/components/RadioControl.tsx:1-15`・CSS は `frontend/src/components/RadioControl.css:2` |
| 右から入れ替わるパネル | **ある**＝`Drawer`（便2 で `onBack`/`backLabel`/`onEscape` を追加済み） | `frontend/src/components/Drawer.tsx:25-36` |
| 下から出るシート | ある（`Sheet`・受信箱で使用中）が、閲覧ページは便2 で**右から**を PO 承認済みなので使わない | `frontend/src/components/Sheet.tsx:1-20`／使用箇所 `frontend/src/pages/inbox/InboxPage.tsx` |
| **1つだけ選ぶパネルの金型** | **無い**。`MultiSelect` は複数選択専用（`selected: string[]` を `toggle` する） | `frontend/src/components/MultiSelect.tsx:96-107`（選択肢の行）・`:110-121`（`layout="row"`） |
| 下向きの山形アイコン | **無い**（`ChevronRight` と `ArrowLeft` だけ） | `frontend/src/constants/icons-base.tsx:8`・`:53`・`:55` |

→ **`ChevronRight` を CSS で90度回して使えば、アイコンを足さずに下向きにできる**（閲覧ページは JS 300KB 上限・便3 実測258.0KB）。

**ADR-144**: 金型の**新設**は「実装を止めて PO 許可 → 部品本体・CSS・見本（stories）の3点セット」が必要（`docs/adr/ADR-144-ui-component-governance.md:60-65`）。
本便は**既存金型の組み合わせだけで作れるため、新設も既定変更も不要**。

## 4. 便2 で作った副画面の仕組み（使い回す）

| 仕組み | 行 | 中身 |
|---|---|---|
| 画面の状態 | `frontend/src/pages/viewer/InventoryView.tsx:41`・`:79` | `type FilterView = "root" \| "provider" \| "condition"` |
| 開く・戻る | 同 `:139-146` | `openFilterSubview` / `backToFilterRoot`（候補を絞る欄を毎回空へ） |
| 開くときに初期化 | 同 `:150-155` | **時間に依存する後片付けは罠**（便2 の教訓） |
| Esc だけ一段戻す | 同 `:160-166` | `handleFilterEscape`。✕・背景クリックは `onClose`（＝閉じる） |
| 題・←・下のボタン | 同 `:307-330` | `filterDrawerTitle` / `filterDrawerBackProps` / `filterDrawerFooter`（「決定する」） |
| ドロワー本体 | 同 `:559-571` | `filterView` で中身を差し替え |

## 5. 形を変えると書き換えが要る検査（grep の結果）

| ファイル:行 | 何を測っているか | 影響 |
|---|---|---|
| `frontend/tests-e2e/visual-language/viewer-top-compact.spec.ts:104-106` | シリーズ・並び替え・絞り込みの箱の位置と高さ（A2・A3・A4） | **testId が同じなら測り方はそのまま使える** |
| `frontend/tests-e2e/visual-language/viewer-top-compact.spec.ts:201` | `selectOption(OTHER_SERIES)` でシリーズを選び件数が変わる（A10） | **書き換え必須**（ネイティブ `<select>` 前提） |
| `frontend/tests-e2e/visual-language/viewer-top-compact.spec.ts:220` | PC に `viewer-tab-select` が無い（A12） | そのまま |
| `frontend/src/pages/viewer/InventoryView.test.tsx:59`・`:69`・`:115` | 並び替えの選択肢と `fireEvent.change`（PC 前提の経路あり） | PC は不変。スマホ経路のものは書き換え |
| `frontend/src/pages/viewer/InventoryView.test.tsx:193`・`:226` | `viewer-tab-select` の値・選択肢 | **書き換え必須** |
| `frontend/tests-e2e/visual-language/viewer-inventory-mobile-filter.spec.ts:35` | 絞り込みドロワーを開く（便2 の A1〜A18） | 触らない＝壊してはいけない |

## 6. お手本の実測（メルカリ）

`docs/specs/design-system/visual-language/benchmark/mercari-search-filter.md:41`:
3行目は `status_check_box`「販売中のみ」98.7x48dp ／ `sort_menu`「おすすめ順」90.7x48dp ／ `filter`「絞り込み」77.3x48dp。
同 `:43`「3行目の『おすすめ順』『絞り込み』は**枠線のない、絵文字＋文字だけのボタン**。箱で囲っていないため、同じ 48dp の中に文字 16.3dp がゆったり入る」。
同 `:30`「**『パネルの上にさらに小さなパネルを浮かせる』形は存在しない**」。

## 7. 幅の計算（1行に収まるか）

360px 幅で中身に使えるのは **328px**（`frontend/src/pages/viewer/viewer.css:23-25` の `padding: 0 var(--space-4)`）。
`Button size="sm"` は左右の余白が `var(--space-3)`×2＝24px・文字 `--font-xs`＝12px（`frontend/src/components/Button.css:40-44`・`frontend/src/tokens.css:14`・`:71`）。
高さは 767px 以下で **44px** になる（`frontend/src/components/Button.css:154-157`）。

- 縮まない2つ（並び替え・絞り込み）の自然幅の見込み: 約96px ＋ 約112px ＝ 208px、`gap` 12px×2＝24px → **232px**
- シリーズに残るのは **328 − 232 ＝ 約96px**（`flex: 1 1 0; min-width: 0` で縮む・はみ出しは `…`）
→ **ボタンの文字から件数を外す**（「ポケモン (43)」→「ポケモン」）ことが前提。件数はパネルの各行に出す。

## 8. この端末の制約

実機の ADB は未接続・この端末では Playwright のブラウザが動かない（`~/.cache/ms-playwright` が空）。
**寸法の一次情報は CI の Playwright ログだけ**。本番反映後の確認は、配布 JS の SHA256 を手元ビルドと突き合わせる方法が使える（便3 で実施・一致）。
