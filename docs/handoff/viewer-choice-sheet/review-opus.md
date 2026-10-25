# Opus 審査: 「シリーズ」「並び替え」を枠なしボタン＋パネル選択へ（便5）

> この文書は何か（1行）: 実装したものが設計どおりか・検査が空振りしないかを、設計担当（Opus）が現物の行番号で確かめ、見つけた不具合を直した記録。

**日付**: 2026-10-26
**対象**: `release/viewer-choice-sheet`（base `b8a24f592`）
**設計**: `docs/handoff/viewer-choice-sheet/design.md`／**recon**: 同 `recon.md`
**判定**: **APPROVE（指摘3件＝実装2件・設計1件を修正済み）**。手元で測れる検査はすべて緑。寸法・操作の B1〜B13 は CI の Playwright が唯一の一次情報。

## 1. 審査で見つけて直した不具合

### R1（実害あり）: すでに選ばれている行を押してもパネルが閉じなかった

実装は行の選択を `RadioControl` の **`onChange` だけ**で受けていた。
ネイティブの radio は**値が変わったときだけ** `change` を出すため、
「いま選ばれているシリーズ（または並び順）をもう一度押す」操作では**何も起きず、パネルが開いたまま**残る。
お手本（メルカリ）は同じ行を押しても閉じる。PO の K3「1つ選ぶと即反映して閉じる」に反する。

**直し方**: 同じ処理を `onClick` でも呼ぶ（`frontend/src/pages/viewer/InventoryView.tsx` の `choiceRow`）。
`pick()` は同じ値の `setState` なので二重に呼ばれても無害。
**守り手を足した**: 新 spec の **B6b**「すでに選ばれている行を押してもパネルが閉じる」
（`frontend/tests-e2e/visual-language/viewer-choice-sheet.spec.ts`。先に `toBeChecked()` を確かめてから押すので空振りしない）。
design ⑤ の表にも B6b を追記した。

### R2（読み上げ）: ボタンの読み上げ名が「いま選ばれている値」を隠していた

シリーズのボタンは `aria-label={t("viewer.tabSelect")}` ＝「シリーズ」だけを持っていた。
`aria-label` は**中の文字を上書きする**ため、画面には「ポケモン」と出ているのに読み上げは「シリーズ」になる。
並び替えのボタンには `aria-label` が無く、逆に「これが並び替えの操作だ」と分からない。

**直し方**: 両方を `「名前: いまの値」`（例: 「シリーズ: ポケモン」「並び替え: 価格が安い順」）にした。新しい文言キーは増やしていない。

### R3（設計の誤り・CI 1回目の実測で判明）: 「背景クリックでも閉じる」は**スマホでは成立しない**

design ⑤ の当初の B10 に「Esc／✕／背景クリックのどれでも閉じる」と書いたのは**設計の誤り**だった。
`Drawer` 金型はスマホ幅で**全幅**になる（`frontend/src/components/Drawer.css:114-118`）ため、
背景（オーバーレイ）に**押せる場所が物理的に無い**。

**CI の一次情報（PR #4759 の1回目・`画面検査（内部）`）**: `.comp-drawer-overlay` をクリックしようとすると
`comp-drawer-panel--open` の subtree が pointer events を遮り、15秒でタイムアウト → B10 が 6件（2幅×3 project）赤。
**ほかの45件はすべて ✓**（B1〜B9・B11〜B13）で、便3 の spec（A1〜A12・書き換えた A10 を含む）も全件 ✓。
全体では 241 passed / 6 failed。

これは便1・便2 の記録（「スマホは全幅で背景タップもできないため閉じるのに2タップ必要」）と一致する既知の条件で、
**本便が悪化させたものではない**。実装は直さず、**基準の側を実態に合わせて訂正**した:
B10 は「Esc と ✕ で閉じる」＋「パネル幅＝画面幅（＝背景を押す余地が無いことの機械的な根拠）」を測る形にし、
design ⑤ と ⑩ にも明記した。

## 2. 設計との突合（疑っていた点を現物で潰した）

| # | 疑い | 結果 |
|---|---|---|
| 1 | 枠なしボタンが本当に「枠なし」か | `.comp-btn` の枠は `border: 1px solid transparent`（`frontend/src/components/Button.css:2-18`）、`ghost` は `background: transparent`（同 `:68-72`）。**どちらも透明**なので B1 の `rgba(0, 0, 0, 0)` 判定が成立する |
| 2 | 3つが1行に収まるか | 縮まない2つ（並び替え・絞り込み）の自然幅 ＋ `gap` が 328px に収まり、シリーズは `flex: 1 1 0; min-width: 0`（`frontend/src/pages/viewer/viewer.css:40-46`）で縮む。**ボタンから件数を外した**ので文字も短い。44px は 767px 以下の `.comp-btn`（`frontend/src/components/Button.css:154-157`）で確保 |
| 3 | 金型を触っていないか | `git diff --stat` の変更は**閲覧ページの4ファイルと検査2本と書類だけ**。`frontend/src/components/` は0ファイル |
| 4 | PC が変わっていないか | `sortMenu`（`<select>`）は PC の `ContentToolbar` にそのまま残り、スマホは別変数 `sortTrigger`。B13 で `tagName === "SELECT"` を固定 |
| 5 | 便2 の状態機械を壊していないか | `drawerOpen`・`filterView`・`handleFilterEscape`・`filterDrawerTitle/BackProps/Footer` は差分0。パネルは**別の `Drawer` インスタンス**として追加 |
| 6 | 「既定に戻す」操作が消えていないか | 並び替えパネルの先頭に `viewer-sort-option-default` があり、`DEFAULT_SORT_KEY`/`DEFAULT_SORT_DIR`（`frontend/src/pages/viewer/viewerFilter.ts:11-13`）に戻す。B9 が4行と戻りを測る |
| 7 | 検査が空振りしないか | 開く前に `openPanel().count() === 0`、選ぶ前に `toBeChecked()`／件数の前後比較、`scrollIntoView` 不使用。B9 は**同じまとまりの2行**を用意して並びの効果が実際に見える fixture にしている（`sortRows` はまとまりの中でしか選んだ列を見ない。`frontend/src/pages/viewer/viewerFilter.ts:168-181`） |
| 8 | 題の読み取りが実在のクラスか | `comp-drawer-title`（`frontend/src/components/Drawer.tsx:168`）・`comp-drawer-overlay`（同 `:138`）はどちらも実在 |

## 3. 手元で実際に走らせた検査（数字は実測）

| 検査 | 結果 |
|---|---|
| `npx tsc --noEmit` | 終了 0 |
| `npx vitest run src/pages/viewer/InventoryView.test.tsx` | **34 件すべて pass** |
| `npm run check:all`（関所25本＋lint） | 終了 0（lint は 0 errors / 59 warnings＝**すべて既存ファイル**） |
| `npx eslint --max-warnings=0 src/pages/viewer/InventoryView.tsx` | 終了 0（**警告0**） |
| CSS の関所4本 ＋ `stylelint`（`viewer.css`） | すべて終了 0 |
| `npx vite build --manifest` ＋ `node scripts/check-viewer-bundle.js` | **260.0 KB / 上限 300 KB** PASSED（便3 の258.0KB から **+2.0KB**。アイコンは足していない） |
| `npx playwright test --list --project=vl-mobile-390 …viewer-choice-sheet.spec.ts` | **17 件収集**（8件 × 2幅 ＋ PC 1件）→ CI の3 project で 51 件走る見込み |

## 4. 残っている穴（正直に書く）

| # | 穴 | 扱い |
|---|---|---|
| S1 | **寸法・操作（B1〜B13）を手元で測れていない**。この端末は Playwright のブラウザが入らず、実機の ADB も未接続 | **CI の `visual-language` が唯一の一次情報**。PR の結果で判定する |
| S2 | **閉じた `Drawer` の中身が Tab で辿れる・読み上げに乗る**（`frontend/src/components/Drawer.css:37-40` は `translateX(100%)` だけで `visibility`/`inert` を使わない）。パネルを1つ増やしたため、閉じているとき余分な行が Tab 経路に入る | **金型側の話で便2 の C8 と同根**。直すと35ファイルに効くため本便では触らず、design ⑫ **D5** に起票 |
| S3 | ボタンの文字が 12px（`size="sm"`）。お手本は 16.3dp | design ⑩ に明記した既知の交換。48px・16px への底上げは ⑫ D2（上部192px の基準も同時に直す必要がある） |
| S4 | シリーズが多い（43件想定）とパネルが縦に長い。候補を絞る検索欄は付けていない | ⑫ D1。PO の使用感で判断 |
| S5 | 同じ `data-testid="supplier-drawer"` の要素が2つになる（どちらも DOM 常在） | 既存 spec も同じ状況を前提に `.comp-drawer-panel--open` で絞る作法（`frontend/tests-e2e/visual-language/inventory-mobile-baseline.spec.ts:144`・`frontend/tests-e2e/visual-language/viewer-inventory-mobile-filter.spec.ts:31`）。新 spec も同じ作法＋B4 で「開いているパネルは常に1つ」を固定した |

## 5. 判定

**APPROVE**。R1・R2 を直した上で、設計の意図と実装は一致。手元で測れる関所はすべて緑。
残るのは CI の寸法・操作検査（S1）と PO の実機確認（K1〜K7）で、どちらも赤なら revert 1回で戻せる（design ⑦）。
