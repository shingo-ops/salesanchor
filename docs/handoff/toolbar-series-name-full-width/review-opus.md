# review (r1): 種別／シリーズの名前が読めるようにする

**判定: REVISE → 取り込みずみ**（本書に挙げた指摘はすべて
docs/handoff/toolbar-series-name-full-width/design.md に反映した）

審査は**反証を探す立場**で行い、指摘の根拠はすべて作業ツリーのファイルを読んで確かめた。
主張は設計担当（Opus）が**1件ずつ自分で再確認**してから取り込んでいる。

## Blocking（3件・すべて事実と確認）

| # | 指摘 | 確認した根拠 | 取り込み |
|---|---|---|---|
| B1 | **初版は `viewer-control-tap-size.spec.ts` を「赤にならない」と誤判定していた**。同ファイルの B8 が `expect(seriesBox.y).toBe(sortBox.y)` を固定しており、シリーズが単独行になると必ず赤（幅360・390の2幅＝6実行） | `frontend/tests-e2e/visual-language/viewer-control-tap-size.spec.ts` の B8 に `expect(seriesBox!.y).toBe(sortBox!.y);` があることを確認 | 設計 ⑤5-3 の表に追加。シリーズは単独行（`not.toBe`）に書き換える |
| B2 | 同ファイルの **B7c・B7d が逆向きに赤**になる。これは「文字を16px／山形を24pxにすると**切れる**」ことを期待する空振り防止の検査。シリーズが1行を独り占めすると使える幅が約262pxになり、既定ラベル「すべて」は**どちらの壊し方でも切れない** | 同ファイルの B7c/B7d が `expect(scrollWidth).toBeGreaterThan(clientWidth)` であることを確認 | 壊し方を **`flex: 1 1 0` に戻す**へ差し替え（設計 ⑤5-2）。閲覧ページ側の空振り防止を**宣言を増やさず**に確保できる |
| B3 | **F2 のために種別の mock を1件足すと既存 spec が赤**。`inventory-series-sort-panel.spec.ts` の E5 が `toHaveCount(4)` を固定。さらに `InventoryPage.tsx` が「主要3種別以外があるとき PC に『その他』のプルダウンを足す」ため **PC の DOM まで変わる** | E5 の `toHaveCount(4)` と `inventory-helpers.ts` の `GET /products/tcg-types` が3件であることを確認 | **mock を一切変えない**方針に変更。F2 を「ラベルの使える幅が240px以上」という直接の判定に置き換えた |

## Major（5件）

| # | 指摘 | 設計担当の確認 | 取り込み |
|---|---|---|---|
| M1 | `.comp-btn` が `justify-content: center` なので、ボタンが312pxになると**名前が行の中央に浮く**。設計書の図は左寄せ | **本番の実機で実測**: 案2 そのままだと名前の左端 **x=142.2**、`justify-content: flex-start` を足すと **x=37**＝下の行のボタンの文字と同じ左端 | `justify-content: flex-start` を 4-1 に追加。F4 で左端の一致も測る |
| M2 | F4（初版）「並び替えのラベルも切れていない」は**永久に緑の空振り**。並び替えは `flex: 0 0 auto` で構造上絶対に縮まない | 既存 spec のヘッダーにも同じ警告が書かれている | 判定を削除 |
| M3 | F7（初版）も空振り。閲覧ページの fixture はシリーズ名が空＝「すべて」3文字で、本便の前後どちらでも緑 | fixture のシリーズが空であることを確認 | F7 を削除し B2 の書き換えに一本化。長い名前の fixture は ⑫ M3 に起票 |
| M4 | 閲覧ページの `MAX_TOP_Y` を192にすると**余裕0px**。在庫表側（+12）と方針が食い違い、1pxの端数で赤になる | 既存の132が `12+(48+12+48)+12` の計算値ちょうどであることを確認。この端末では Playwright が動かず手元で測れない | **204**（192+12）に変更 |
| M5 | **CI の画面検査はすでに789件**（実測）で約8.9分。持ち時間10分（`npm ci` と ブラウザ導入を含む）に対し余裕が小さい。初版の F1〜F8 は27実行の追加 | 前便の審査が置いた基準（655件・7.4分）と整合 | 新規を**5宣言＝15実行**に削減。幅は360のみ。閲覧ページ側は既存の書き換えで0追加 |

## Minor（4件）

| # | 指摘 | 取り込み |
|---|---|---|
| M6 | `.inventory-toolbar__series` 側の `text-overflow: ellipsis` は**効いていない**（ボタンは flex の箱で直下にテキストが無い）。… を出しているのは `.inventory-toolbar__label` 側 | `__series` から `text-overflow` を落とし、説明を訂正 |
| M7 | `frontend/src/components/Button.css` の `:hover` が `@media (hover: hover)` で囲まれていないため、**タップの跡が 62px → 312px に広がる** | ⑩ のトレードオフに明記し、⑫ M2 に別便として起票 |
| M8 | F5 の `page.addStyleTag` は `.inventory-toolbar > .inventory-toolbar__series`（詳細度 0,2,0）に勝つ必要があり `!important` が要る | ⑤5-1 と ⑪ に明記 |
| M9 | 設計書 5-3 の行番号に小さなズレ（A2〜A4 は 102-134、B1〜B3 は 160-196） | 表の行番号を訂正 |

## 審査が「確認済み」とした点（抜粋）

- `.inventory-toolbar__series` / `.viewer-toolbar__series` は**スマホ分岐にしか付かない**＝ PC は変わらない。
  PC での `tab-select` 0件はすでに E14・A12・B13 が固定している。
- `layoutClassName` は `<button>` 自身の `className` に連結されるので `flex` が正しく効く。
- `scrollWidth <= clientWidth` での「切れていない」判定はこの DOM 構造で成立する
  （閲覧ページの B7a が同じ測り方で既に動いている）。
- `.inventory-toolbar` に `padding` が無いので、F4 の「ボタンの幅＝`clientWidth`」が成立する。
- 高さ48pxの判定は壊れない（`align-items: center` で引き伸ばさない）。
- `visual-language/` に画面写真の比較（`toHaveScreenshot`）は0件。

## 残る不確かさ（正直に記録する）

**この端末では Playwright のブラウザが入らない**ため、B1・B2 の「赤になる／逆向きに赤になる」は
DOM・CSS・トークンからの演算による結論で、**ブラウザでの実測ではない**。
**CI の1回目でここが想定どおりかを必ず確認する**。
