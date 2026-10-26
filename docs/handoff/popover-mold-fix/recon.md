# recon: 選択肢パネルの土台（Popover 金型）の2欠陥

> この文書は何か（1行）: 浮かぶ選択肢パネルが「スクロールするとずれる」「画面の端で外に出る」の2点について、現物のコードと影響範囲を記録したもの。

**日付**: 2026-10-26
**由来**: 便2（PR #4740）の審査で C2 として起票。便3・便4・便5 でも持ち越し（`docs/handoff/viewer-filter-subscreen/design.md:312`、`docs/handoff/viewer-top-compact/design.md:171`、`docs/handoff/viewer-choice-sheet/design.md:218`）
**読んだ版**: `origin/main` = `03cb7cae5`

## 1. 欠陥(a) スクロール分の二重足し算

`frontend/src/components/Popover.tsx:38-70` の `calcPosition` が、`top`/`left` に `window.scrollY`/`window.scrollX` を足している。

- 基準にしている `triggerRect` は `getBoundingClientRect()`（同 `:100`）＝**すでに画面基準**。
- パネルは `position: fixed`（`frontend/src/components/Popover.css:16`）＝**画面基準で置かれる**。
- よって足した分だけ素でずれる。4つの `placement`（top/bottom/left/right）すべてに入っている（`:50,51,55,56,60,61,66,67`）。
- 便1 の実測: 400px スクロールした状態で開くと一覧が 400px 下へ（y=150 → 550）。

## 2. 欠陥(b) 画面の端で外に出る

- `calcPosition` は計算結果をそのまま使い、**画面内へ収める処理が無い**（`Popover.tsx:38-70`）。
- `Popover.css` にも `max-width` が無い（`frontend/src/components/Popover.css:14-31`）。
- 中身側の最小幅: `.comp-multiselect__menu--popover { min-width: var(--dropdown-min-width) }`（`frontend/src/components/MultiSelect.css:12-14`）、`--dropdown-min-width: 400px`（`frontend/src/tokens.css:447`）。
- 便1 の実測: 画面 360px に対し **x=-29・幅418**（左右とも画面外）。

## 3. 開いている間にスクロール・リサイズしても測り直さない

位置計算の `useEffect` の依存は `[isOpen, placement]` だけ（`Popover.tsx:98-107`）。`resize`・`scroll` の購読が無いので、開いたまま画面を動かすとパネルが置き去りになる。

## 4. 影響範囲（全数確認）

`<Popover` を書いているのは3ファイルだけ。

| 使っている所 | 何に出るか |
|---|---|
| `frontend/src/components/MultiSelect.tsx:174` | `layout="popover"`（既定）の「ボタン＋浮かぶ一覧」 |
| `frontend/src/components/Popover.stories.tsx:31,42,63` | Storybook（CI の画面検査では走らない） |

`MultiSelect` を `layout="popover"`（既定）で使っている画面:

| 画面 | 場所 | testid |
|---|---|---|
| アプリ側 在庫表の操作台 | `frontend/src/pages/inventory/InventoryToolbar.tsx:158,168` | `inventory-condition-filter-button`・`inventory-supplier-filter-button` |
| アプリ側 在庫表のフィルタパネル | `frontend/src/pages/inventory/InventoryFilterPanel.tsx:119,134` | `inventory-supplier-filter-button`・`inventory-condition-filter-button`（PC のフィルタパネル内） |
| 閲覧ページ | `frontend/src/pages/viewer/InventoryView.tsx:10` | **`layout="inline"`/`"row"` のみ＝Popover を使わない**（便1・便2 で切替済み） |

**似て非なるもの（今回は触らない）**

- `frontend/src/components/ContextMenu.tsx:78-95` — 画面内へ収める計算を**すでに持っている**（画面端との最低間隔8px、`--space-3` をトークンから読む先例あり `:67-72`）。今回の直しはこの考え方に揃える。
- `frontend/src/pages/schedule/SchedulePageImpl.tsx:119-141` — 予定表が持つ独自計算。`clamp` 済みで `scrollY` も足していない。

## 5. 既存の自動検査

| ある/ない | 中身 |
|---|---|
| `Popover.test.tsx` | **無い**（単体テストが1本も無い） |
| `frontend/src/components/MultiSelect.test.tsx:80-87` | A20＝`layout` 既定が popover であること（位置は測っていない） |
| `frontend/tests-e2e/visual-language/viewer-inventory-mobile-filter.spec.ts` | A15＝ドロワーが開いている間 `.comp-popover` が 0 件（位置は測っていない） |
| 位置の検査 | **無い**（スクロール・画面端のどちらも固定されていない） |

## 6. 作法

- `scripts/check-process-artifacts.js:115-128` の DANGEROUS_PATTERNS に `components/Popover` は**入っていない**（`frontend/src/pages-layout.css` は入っている）。ただし `frontend/src/` は real-code かつ user-impacting なので通常の関所は全部かかる。
- `frontend/AGENTS.md:34-37`（ADR-144）: 共通部品は金型を先に確認。例外は `ui-allow` コメント。
- ADR-067: CSS は直値禁止＝トークン参照のみ。
- この端末では Playwright の chromium が動かない（`salesanchor-ci-blind-spots` 参照）ため、**画面検査の一次情報は CI ログだけ**。単体テスト（vitest）は手元で走る。
