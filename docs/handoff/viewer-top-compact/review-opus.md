# Opus 審査: 閲覧ページ 上部コンパクト化（便3）

> この文書は何か（1行）: 実装したものが設計どおりか・検査が空振りしないかを、設計担当（Opus）が現物とコードの行番号で確かめた記録。

**日付**: 2026-10-25
**対象**: `release/viewer-top-compact`（main 取り込み後）
**設計**: `docs/handoff/viewer-top-compact/design.md`／**recon**: 同 `recon.md`
**判定**: **APPROVE**（手元で測れる検査はすべて緑。寸法 A1〜A12 は CI の Playwright が唯一の一次情報）

## 1. 手元で実際に走らせた検査（数字は実測）

| 検査 | 結果 |
|---|---|
| `cd frontend && npx tsc --noEmit` | 終了 0 |
| `cd frontend && npx vitest run src/pages/viewer/InventoryView.test.tsx` | **32 件すべて pass** |
| `cd frontend && npm run check:all`（関所24本＋lint） | 終了 0（lint は 0 errors / 59 warnings＝**すべて既存ファイル**） |
| pre-commit と同じ関所を変更ファイルだけに: `eslint --max-warnings=0`（`InventoryView.tsx`・`InventoryView.test.tsx`） | 終了 0（**警告0**） |
| 同: `check-css-hardcoded-colors` / `check-css-var-fallbacks` / `check-css-hardcoded-values` / `check-css-fixed-position` / `stylelint`（`viewer.css`） | 5本すべて終了 0 |
| `npx vite build --manifest` → `node scripts/check-viewer-bundle.js`（A15） | **258.0 KB / 上限 300 KB** で PASSED（便2 時点 257.4 KB → **+0.6 KB**） |

## 2. 設計との突合（疑っていた点を現物で潰した）

### 2-1. 「3つが1行に並ぶ・44px 以上」（A2・A3）は偶然に頼っていない — 確認済み

実装は3つの部品に高さを指定していない。CSS の既定値だけを見ると
並び替え 28px（`frontend/src/components/FormField.css:138-142` の `--comp-input-height-sm` = 28px・`frontend/src/tokens.css:486`）、
絞り込み 28px（`frontend/src/components/Button.css:40-44` の `--field-h-sm` = 28px・`frontend/src/tokens.css:164`）、
シリーズ 約39.6px（`FormField.css:49-62` の padding 8×2＋行の高さ 14.4×1.5＋枠線2）で**ばらつく**ため、
`align-items: center`（`frontend/src/pages/viewer/viewer.css:29`）だと y がずれて **A2 が赤になるはず**だった。

実際は赤にならない。**767px 以下の指定が2か所あり、後に書かれているので勝つ**（詳細度は同じ (0,1,0) で後勝ち）:

- `frontend/src/components/Button.css:154-157` → `.comp-btn { min-height: var(--size-icon-btn-lg) }` = **44px**（`frontend/src/tokens.css:163`）
- `frontend/src/components/FormField.css:534-539` → `.comp-select__control { min-height: var(--comp-input-height-mobile) }` = **44px**（`frontend/src/tokens.css:487`）

→ 360px・390px では3つとも**中身より 44px の下限が勝つ＝高さが完全に同じ**になり、y も一致する。
便1 の実機実測（`docs/handoff/viewer-inventory-mobile-filter/recon.md:98-113` の「操作3つ44」）とも一致する。
この2か所は**画面幅で効く指定（`@media (max-width: 767px)`）で、タップ端末かどうかは見ていない**ため、
CI の3つの project（`frontend/playwright.config.ts:63-77`）でも spec が自分で 360/390 に設定する限り同じように効く。

### 2-2. A1 の 192px は**余裕0**（将来の注意点）

68（ヘッダー）＋12（上の余白）＋44（検索欄）＋12（gap）＋44（操作3つ）＋12（下の余白）＝**ちょうど 192**。
`<=192` なので通るが、**1px でも増えたら赤**になる。⑫ D2（48px 行への統一）に進むときは
この基準値も一緒に直す必要がある（48×2＋余白なら 192 を超える）。design ③ に書いてある 192 はこの計算と一致している。

### 2-3. 金型を壊していない

- 絞り込み画面の先頭に足した1行は、`MultiSelect` が自分で出している選択肢（`frontend/src/components/MultiSelect.tsx:96-107`）と
  **タグもクラスも同じ**（`label` ＋ `comp-multiselect__option` ＋ `--inline` ＋ `CheckboxControl`）。
  高さ 44px の下限も同じ指定から来る（`frontend/src/components/MultiSelect.css:40-43`）。**金型のファイルは1行も触っていない**。
- 絞り込みボタンの並び指定は `layoutClassName` で渡している。`Button` は型で `className` を受け取らない設計
  （`frontend/src/components/Button.tsx:38` が `className` を除外）なので、**これが唯一の正しい渡し方**。
- 新しい CSS は3つとも `.viewer-toolbar > …` の**直下の子**に限っている（`frontend/src/pages/viewer/viewer.css:37-48`）。
  検索欄と並び替えの変数は PC（`ContentToolbar`）と共用だが、PC 側の親は `.viewer-toolbar` ではないので**効かない**。

### 2-4. 検査が空振りしない形になっている

- A1〜A4 は `scrollIntoView` を使っていない（便2 の教訓）。
- A7・A9 は「切る前に**オンであることを確定**」→「切る」→「オフであることを確定」の順で、
  何も起きなくても緑になる書き方を避けている。
- A10 の fixture の「アクア」は**実在する選択肢になる**: `seriesTabs()` は空でないシリーズを全部返す
  （`frontend/src/pages/viewer/viewerFilter.ts:213-221`。主な3つ以外も value に出る）。
  また初期のシリーズは「ポケモン」の行が無いので「全て」になる（`frontend/src/pages/viewer/InventoryView.tsx:65`）
  → 60件 → アクアを選んで20件。**件数が必ず変わる**。
- A7 の古い行は mock 側で 48時間前にしている（`frontend/tests-e2e/visual-language/viewer-helpers.ts:43-45`）。
  既定は 0 件なので**既存の spec は1行も変わらない**（後方互換）。

## 3. 残っている穴（正直に書く）

| # | 穴 | 扱い |
|---|---|---|
| R1 | **寸法 A1〜A12 を手元で測れていない**。この端末は Playwright のブラウザが入らず（`~/.cache/ms-playwright` が空）、実機の ADB も未接続 | **CI の Playwright ログが唯一の一次情報**。PR の `visual-language` ジョブの結果を見て判定する（66件＝22×3幅の形になるはず） |
| R2 | 設計 ⑩ の「長いシリーズ名は `…` で切れる」は、`<select>` では**ブラウザが `text-overflow` を適用しない場合がある**。切れ方が `…` ではなく単純な見切れになる可能性 | 見た目だけの話で、A1〜A12 の合否には影響しない。実機確認（K1〜K6）で PO に見てもらう |
| R3 | 「絞り込み (1)」の件数表示は **PO 指示に無い追加**（design 4-3） | 設計どおり**単独で外せる**作りになっている（`InventoryView.tsx` の `filterActiveCount` と辞書1キーを消すだけ） |
| R4 | 24時間の切り替えが1タップ遠くなる | PO 指示による交換（design ⑩）。手がかりは R3 の件数表示で補う |

## 4. 判定

**APPROVE**。設計の意図と実装は一致しており、手元で測れる関所はすべて緑。
残るのは CI の寸法検査（R1）と PO の実機確認（K1〜K6）で、どちらも**赤なら1回の revert で戻せる**（design ⑦）。
