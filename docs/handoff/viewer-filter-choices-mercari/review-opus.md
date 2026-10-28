# review-opus: 便13a（絞り込みパネルの寸法）の独立審査と裁定

> この文書は何か（1行）: 設計者とは別の目で変更の粗探しをさせ、出てきた指摘を**設計者が現物で裏を取って**
> 採否を決めた記録。採ったものは design.md に反映済み、採らなかったものは理由をここに残す。

審査日: 2026-10-28 / 対象: 枝 `release/viewer-filter-choices-mercari`（土台 `d10aff603`）の未コミット差分
設計: docs/handoff/viewer-filter-choices-mercari/design.md / 下調べ: docs/handoff/viewer-filter-choices-mercari/recon.md

## 0. 結論

**出荷を止めるべき欠陥が1件**（既存 spec 5本が必ず赤）。ほかに**実機で PO が×を付けうる欠陥が1件**（タップ後に行の色が残る）。
いずれも設計を直して手当てした（design.md 4-7）。審査の指摘のうち**1件は設計者の確認で誤りと判明**したので採らなかった（§2-A2）。

## 1. 採った指摘

| # | 指摘 | 設計者による裏取り | 手当て |
|---|---|---|---|
| D-1 | **既存5本の spec が「パネルの左端 x が 0 になるまで待つ」形で、パネルを狭めると必ず時間切れの赤**。recon §4 の表はこのヘルパーを見落としていた | `grep -n -A3 "viewer-filter-toggle"` と `.toBe(0)` で5本すべて現物確認。`viewer-control-tap-size.spec.ts` だけは `.toBe(0)` が2つあり、**78-86 はシリーズ/並び替え用（全幅のまま）** | design.md 4-7(1)・⑤ C15/C16。待ち方を「**右端が画面の右端に一致するまで**」に変え、共通の置き場へ1か所化。recon §4 にも見落としとして追記 |
| B-3 | `.comp-multiselect__option:hover` はスマホで**タップ後に色が残る**（sticky hover）。お手本 §3-1 の「合図は四角の塗りだけ・行の背景は変えない」＝ KGI K6 を実機で満たさない。K6 を測る検査も無い | `grep -rn "bg-hover\|:hover" frontend/tests-e2e/` → **hover を測っている検査は0本**＝網が無いことを確認。社内に `@media (hover: hover)` の先例あり | design.md 4-7(2)・⑤ C13。`@media (hover: hover)` で囲い、「規則がその中にあること」を静的に測る検査を足す |
| D-3 | C9 の空振り防止が `min-height` しか潰しておらず、**打ち消し幅（bleed）には空振り防止が無い** | 新 spec を通読して確認（C9 は `min-height` 1項目のみ） | ⑤ C9 に「打ち消し幅を 0px に戻すと C5 の2判定が落ちる」を追加 |
| C-1/F-8 | 新 spec が `DRAWER_BODY_PAD_X = 24` と**直書き**で、`Drawer.css` の `--space-6` と二重管理 | `frontend/src/components/Drawer.css:97-101` と `frontend/src/tokens.css:74` の一致を確認 | 実際の `.comp-drawer-body` の計算済み `padding-left` を読む形に変更。根の手当て（金型側にトークンを立てる）は ⑫ J7 に起票 |
| C-2 | `.comp-drawer-body` は `overflow-y:auto` のため **`overflow-x` も `auto` に計算される**。パネルが61px 狭くなるので中身がはみ出しても**内部スクロールになって C10（ページ全体）をすり抜ける** | CSS の overflow 仕様（片軸が非 visible なら他軸の `visible` は `auto` に計算される）と `Drawer.css:97-101` で確認 | ⑤ C14 を追加（root と選択画面の両方で `.comp-drawer-body` の `scrollWidth <= clientWidth`） |
| E-2 | C8 が文字の上しか押していない。**今回新設した左48pxの枠は未検証** | 新 spec を通読して確認 | ⑤ C8 に左の枠を押す判定を追加 |
| A-3 | `comp-multiselect__check` は**過去に別の意味で使われ削除された名前**の再利用 | `docs/specs/design-system/design.md:4234` に「`frontend/src/components/MultiSelect.css` の `.comp-multiselect__check` を削除」の記録を現物で確認 | `comp-multiselect__check-col` に改名 |
| F-2・F-4・F-5 | 設計書と実装の番号・行番号・列挙のずれ | `grep -n` で現物の行番号を確認（`mobileInset` は :792、`freshCheck` は :499、絞り込みの `<Drawer` は :785） | design.md を訂正 |

## 2. 採らなかった指摘

### A-2「金型の既定の見た目が変わり、Drawer の外で使うとチェックが容器の左端に密着する」→ **誤り**

審査は `.comp-multiselect__option--inline { padding: 0 var(--space-4) 0 0 }`（左 padding 0）だけを見て
「密着する」と判断しているが、**左の余白はチェックの枠が持っている**。
`.comp-multiselect__check-col` は `flex: 0 0 48px` ＋ `justify-content: center` で、
中のチェック（`--size-checkbox: 16px`）は**枠の中央＝左から16px の位置**に置かれる。
したがって Drawer の中でも外でも見え方は同じで、密着しない。**打ち消し幅（bleed）だけが Drawer 前提**であり、
それは既に「呼ぶ側が指定・金型の既定は0px」に分離してある（design.md 4-3）。

### D-5「`SCROLLBAR_ALLOWANCE = 20` は判定を甘くするだけ」→ **残す**

審査の言うとおり、この緩い判定だけなら打ち消し幅が4pxでも緑になる。ただし**厳密な判定は
「見出しとの幅の差＝左右の余白2つ分」が担っており**、そこに空振り防止（D-3 の手当て）も付けた。
緩い方は「スクロールバーが場所を取る環境でも落ちない」ための保険として残す。
なお「headless Chromium はスクロールバーが場所を取らない」という審査の推定は、
`viewer-choice-sheet.spec.ts:328` が**全幅パネルの厳密一致を要求していて、直近の便（#4831）の CI 記録では
画面検査が全件緑**であることが傍証だが（この緑は記録であって本審査で測り直したものではない）、
それは**文書（document）側の話**で、`.comp-drawer-body` という**要素の内部スクロール**を直接示してはいない。
断定できないので、どちらでも成立する形を保つ。

### D-6「C1 の x の判定が待ちの条件と重複」/ D-2「C2 は直す前でも緑」→ **残す**

どちらも回帰の歯止めとして意味がある（C2 は「絞り込みだけ狭めた」ことの裏取り）。重複は害ではない。

### D-9「`MIN_VISIBLE_OPTIONS = 5` は未検証」→ **CI で実測する**

この端末では Playwright のブラウザが動かないため、手元で測る道が無い。CI の画面検査が唯一の一次情報。
下限5は「8 × 44/61 = 5.77 → 5」という算数から置いた値で、**CI が緑なら実測で裏が取れる**。

## 3. 審査が確認して「問題なし」と結論した点（設計者も追認）

- 新しいクラス名5種と `mobileInset`・`--comp-multiselect-list-bleed` を**リポジトリ全体に grep して、
  閲覧ページ・金型・spec・docs 以外の利用者はゼロ**。`layout="inline"` の利用者も閲覧ページ2か所と見本帳1か所のみ。
- `@media` の中の `.comp-drawer-panel--mobile-inset` は同一詳細度・後勝ちで `width:100%` に勝つ。
  `--wide` は `@media` の外なので併用時も狭める側が勝つ。
- `no-descending-specificity` は違反しない（`npx stylelint "src/**/*.css"` を実行して確認）。
- 負の margin はちょうど padding box の端に一致するため、横スクロールは出ない（ただし余裕0＝C14 で網を張る）。
- strict mode violation は無い（`.comp-drawer-panel--open` で絞っており、オーバーレイは開いている1枚だけ）。
- `CheckboxControl` は素の `<input>` 1個なので、`<span>` を2枚足しても `<label>` の関連付け・読み上げは変わらない。

## 4. この審査で確立した型（次便へ）

**「CI が赤になる検査」を数えるときは、判定の中身だけでなく『前提を作る段取り（開き方・待ち方）』も数える。**
今回は5本の spec が同じヘルパーを複製して持っており、判定を1つも変えていないのに全部赤になるところだった。
**同じ名前の関数が複数の spec に複製されていたら、それは変更の影響範囲**。
