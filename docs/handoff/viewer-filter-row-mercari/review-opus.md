# 独立審査（Opus）: 便11 絞り込みの項目の行をお手本に合わせる

> この文書は何か（1行）: 便11 の設計と実装（未コミットの作業ツリー）を、設計担当とは別の回で
> **現物のソースだけを根拠に**突き合わせた記録。判定と、直した点を残す。

**審査日**: 2026-10-27
**対象**: docs/handoff/viewer-filter-row-mercari/design.md ＋ 同 recon.md ＋ 実装4ファイル ＋ 新 spec
**土台**: `release/viewer-filter-row-mercari`（審査時に `origin/main` = 0c23808ec へ早送り済み）
**この回の位置づけ**: 設計段階の指摘（design.md 中の「独立審査の指摘1〜8」）は**別の回**で反映済み。
本書は**実装後・PR 前の突き合わせ**（設計どおりに入っているか・新 spec が空振りしないか）。

## 判定

**APPROVE（PR 作成可）**。製品コードの変更は設計と1行ずれなく一致。新 spec が参照する目印・文字列・
型はすべて実装側に実在する。直したのは記録の3か所だけで、製品コードの修正は0件。

## 1. 実装が設計どおりか（diff と design.md の照合）

| design の指示 | 実装 | 判定 |
|---|---|---|
| `--comp-multiselect-row-h: 53px` を MultiSelect 専用の節に新設（4-1） | `frontend/src/tokens.css:561-563`（SubMenu 節の後・Status color 節の前） | 一致 |
| 行の `min-height` を新トークンへ（4-1） | `frontend/src/components/MultiSelect.css:77` | 一致 |
| 左ラベルと右の現在値の `font-size` を `--font-base` へ（4-2） | 同 `:95`・`:107` | 一致 |
| ja の `viewer.filter.all` を「指定しない」（4-3） | `frontend/src/locales/viewer/ja.json:51` | 一致 |
| en を "Unspecified"（4-3） | `frontend/src/locales/viewer/en.json:51` | 一致 |
| メディアクエリは足さない（4-4） | 追加0行 | 一致 |
| 製品コードの変更は上記のみ | `git diff --stat` が4ファイル・CSS 3行＋トークン1件＋辞書2値 | 一致 |

`--size-icon-btn-lg`（44px）は**他に7か所で使われている**（`frontend/src/components/Button.css:157-170` ほか）ので
参照を1つ外しても未使用トークンにはならない。`.comp-multiselect__option--inline`（選択画面の行・
`frontend/src/components/MultiSelect.css:42-44`）は 44px のまま＝便11 の境界（4-4）どおり。

## 2. 新 spec が空振りしないか（目印と文字列の実在確認）

| spec が使うもの | 実装の出どころ | 判定 |
|---|---|---|
| `gotoViewer()` の戻り値 `.providers` | `frontend/tests-e2e/visual-language/viewer-helpers.ts:88-92`（`providers: string[]`） | 実在。型検査も通る |
| `viewer-provider-row` / `viewer-condition-row` | `frontend/src/components/MultiSelect.tsx:115` の `tid("row")` ＋ `frontend/src/pages/viewer/InventoryView.tsx:234`・`:249` の `testId` | 実在 |
| `viewer-provider-options-option-<値>` | 同 `MultiSelect.tsx:103` の `tid(\`option-${o.value}\`)` ＋ `InventoryView.tsx:276` の `testId="viewer-provider-options"`。`CheckboxControl` は `...rest` で `data-testid` を input に渡す（`frontend/src/components/CheckboxControl.tsx:22`・`:44`） | 実在・押せる |
| `drawer-back` | `frontend/src/components/Drawer.tsx:138`（`onBack` があるときだけ描かれる） | 実在 |
| `viewer-provider-filter-button` | `MultiSelect.tsx:175` の `tid("button")` ＋ `InventoryView.tsx:204` の `testId="viewer-provider-filter"` | 実在 |
| 文字列「提供者: 指定しない」 | `MultiSelect.tsx:150-151` の `` `${label}: ${allLabel}` ``（**半角コロン＋半角スペース**）＋辞書 | 一致 |
| `.comp-multiselect__inline-summary` が0件のとき「指定しない」 | `MultiSelect.tsx:142` が `selectedSummary` を無条件に描く。`:82` が0件のとき `allLabel` | 一致 |
| 要約欄が同時に2つ出ないか（曖昧 locator の罠） | `InventoryView.tsx:678-681` が `filterView` で provider / condition / root を**排他**に描く＝`layout="inline"` は常に1つ | 一致 |
| `--font-base` が computed `"14.4px"` | `frontend/src/tokens.css:16` の `0.9rem`。`html`/`:root` に `font-size` 指定は無く既定16px | 一致 |

**選択が ← で保たれるか**（spec は「決定する」ではなく `drawer-back` で戻る）:
選択肢を押した瞬間に `MultiSelect.tsx:84-86` の `toggle` → `onChange` で
`InventoryView.tsx:75-76` の `useState` に入る。`backToFilterRoot()` は `filterView` だけを戻す
（同 `:153-156`）。`viewer-filter-apply`（同 `:329-336`）も中身は `backToFilterRoot()` だけなので
**←と「決定する」は結果が同じ**。既存 spec も A2・A7 で ← を使っている。

## 3. 既存の歯止めへの波及（行が2本で計18px 伸びる）

| 既存の検査 | 何を見ているか | 18px 増の影響 |
|---|---|---|
| `viewer-inventory-mobile-filter.spec.ts:112-125`（A1） | 数量の下限欄の下端 ≤ 画面高700px | 設計の積算427.4→445.4px。赤にならない |
| 同 `:145-153`（A4） | コンディションの行が画面内 | 同上 |
| `viewer-top-compact.spec.ts:155`（A6） | 24時間の行が**提供者の行より上**（y の前後関係のみ） | 高さに依存しない。無影響 |
| `viewer-control-tap-size.spec.ts:138`・`:150` | 行を押して選択画面へ入るだけ | 無影響 |
| `InventoryView.test.tsx`（jsdom・多数） | testid の有無・文字列に「Acme」等の名前が入ること | jsdom は CSS を計算しない。文言「すべて」を assert している行は**0件**（確認済み） |
| `MultiSelect.test.tsx:123` | 自前の `allLabel="All"` を渡す | 辞書に依存しない。無影響 |

**「すべて」を期待している既存の検査は、閲覧ページ側には1本も無い**（`grep` で確認。
`tcg-product-import.spec.ts:115` の「すべて」はタブの別辞書＝別画面）。

## 4. 本書で直した点（記録のみ・製品コードは0件）

1. design.md ⑥ の表が en を **"Not specified"** と書いていた（4-3 の本文と実装は "Unspecified"）。
   → ⑥ を "Unspecified" に直した。**社内の既存訳に3つ目の表記を作らない**という 4-3 の根拠と食い違っていた。
2. design.md ⑤ の「道順」が「選んで**「決定する」で戻る**」と書いていたが、spec は ← で戻る。
   → 実装の根拠（←と「決定する」が同じ結果になる理由）を添えて ← に直した。
3. design.md の「土台」が着手時の `origin/main`（f7bb004b7）のままだった。
   → PR 前に 0c23808ec へ早送りした事実を追記した。

## 5. 残した懸念（PR 本文にも書く）

- **B1 の「53px ちょうど」は min-height が勝つことに依存する**。中身の固有高さは 40.04px
  （design 4-1 の検算を再計算して一致）なので余裕 12.96px あるが、将来 `--font-base` を
  16px 以上に上げると固有高さが 25.6+17=42.6px になり、なお 53px 以内。**行が増える**（2段になる）
  変更が入ったときだけ 53px が破れる＝そのときは検査が赤で教える。
- **アプリの在庫表は「すべて」のまま**（別キー）。製品内で文言が2通りになる既知の不一致で、
  横展開（design ⑫ H3）で解消する。PO が K5 を見るときの前提。
- **同じドロワーの中で文字の大きさが混ざる**（項目の行 14.4px／選択画面の行 13.6px）。便12 でそろえる。

## 関連
- 設計: docs/handoff/viewer-filter-row-mercari/design.md
- 調査: docs/handoff/viewer-filter-row-mercari/recon.md
- 前便の審査: docs/handoff/viewer-control-tap-size/review-opus.md
