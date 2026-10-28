# design: 在庫表（/inventory）スマホの上部を閲覧ページと同じ作りにする（便1／全4便の1本目）

> この文書は何か（1行）: アプリの在庫表のスマホ表示で、上部の操作のうち3つ（24時間以内・並び替え・
> 詳細フィルタ）が**画面の外にあって指が届かない**。これを**閲覧ページ（/viewer/）とまったく同じ作り**に
> して、全部を画面の中に入れる。
>
> **PO 指示（2026-10-29）**: 「閲覧用のページと全く同じにしてくれ」。
> 進め方は**順番に4便**（①上の段の形＝本便 ②シリーズと並び替えを右から出るパネルに
> ③絞り込みを右から出るパネル＋項目→次の画面に ④検索を押すと開く検索画面に）。
> **在庫表にしかない操作（リセット・カテゴリー除外・列の取捨・形態など）は、機能を減らさず
> 「絞り込み」のパネルの中に残す**（PO 決定）。

**recon**: docs/handoff/inventory-toolbar-mercari/recon.md
**審査**: docs/handoff/inventory-toolbar-mercari/review-opus.md（r1 = REVISE。本書は r1 を取り込んだ版）
**土台**: `release/inventory-toolbar-mercari`（`origin/main` = `5b3162403`）
**前の便**: `docs/handoff/inventory-mobile-responsive/design.md`（便0＝計測 spec・PR #4612）の宿題 **C1**。

## ① 区分：A（見た目と置き場所の変更）

データの読み書き・絞り込みの計算・並び替えの計算は**一切変えない**。変えるのは
**スマホのときに、どの操作をどこに置くか**だけ。**PC は1px も動かさない**。

## ② KGI（PO が実機で○×を判定できる粒度）

PO 決定（2026-10-28・選択肢提示）: **「閲覧ページと同じ形」**＋**「24時間以内はパネルの中」**。

| # | PO が見て○×を言えること |
|---|---|
| K1 | 在庫表をスマホで開くと、**検索欄が横いっぱい**に広がっている |
| K2 | その下の段に**「並び替え」と「詳細フィルタ」が両方見えていて、押せる**（今は画面の外） |
| K3 | **「リセット」と「24時間以内」は上から消えている**。「詳細フィルタ」を押した先にある |
| K4 | 「詳細フィルタ」の文字の横に**効いている絞り込みの数**が出る（既定は 24時間以内 が入りなので **1以上**） |
| K5 | 「詳細フィルタ」を押した先で**24時間以内を切り替えられる**。切り替えると一覧の件数が変わる |
| K6 | 同じ先に**「リセット」**があり、押すと**検索語・カテゴリー・並び替え**が既定に戻る（**仕入元や価格などの詳細フィルタは意図的に残る**＝今までと同じ動き） |
| K7 | **上の操作のところで横に切れているものが無い**（検索欄・並び替え・詳細フィルタ）。※その下の**タブの行（すべて／ポケモン…／その他）の注記が右に切れているのは本便の対象外**で、便2（シリーズのボタン化）で直す |
| K8 | **PC は何も変わらない**（検索欄の幅・詳細フィルタのボタンの見た目を含む） |

## ③ KPI（機械で測る値）

画面幅 360px / 390px の両方で測る。括弧内は 2026-10-28 に本番の実機で測った現在値。

| # | 値 | いま | この便の後 | 出どころ |
|---|---|---|---|---|
| P1 | 上部操作台の子要素の右端の最大値 | **654px**（画面360px） | **画面幅以下**（360/390 とも） | 本番実機の実測 |
| P2 | 画面の外に出ている操作の数 | **3個**（24時間以内・並び替え・詳細フィルタ） | **0個** | 同上 |
| P3 | 検索欄の幅 | 224px | **`.inventory-toolbar` の幅の95%以上** | お手本 §1 の「横いっぱい」 |
| P4 | 「並び替え」「詳細フィルタ」の押せる高さ | **44px**（`@media` が後勝ちで効いている。36px ではない） | **48px以上** | ADR-140 ／ お手本の48dp |
| P5 | 上部操作台（`.inventory-toolbar`）の高さ | 44px（1行・ただし破綻） | **120px以下**（48＋間隔12＋48＋上下の余白。**3行に折り返したら破れる**） | 本便の上限 |
| P6 | 横スクロールの超過（document / `.mobile-content`） | 0 | **0のまま** | 便0 の実測 |
| P7 | PC（幅1280）の検索欄の幅・詳細フィルタの高さと字の大きさ | 現状値 | **同じ値のまま** | PO 決定（PC 不変） |

## ④ 設計（How）

### 4-1. スマホ専用の JSX 変数に分ける（**これを最初にやる**）

`frontend/src/pages/inventory/InventoryToolbar.tsx` は `search` / `resetButton` / `freshButton` /
`sortMenu` / `filterButton` を**1つずつ作って、スマホ分岐と PC 分岐の両方が同じものを使っている**。
**ここでクラスや `size` を変えると PC も一緒に変わる**（審査 H2）。

→ **スマホ専用の変数（`searchMobile` / `filterButtonMobile` / `sortMenuMobile`）を別に作る**。
PC 分岐が使う既存の5つは**1文字も触らない**。これが K8 / P7 の担保。

### 4-2. スマホでは共通の操作台（`ContentToolbar`）を使わない＝閲覧ページと同じ作り

閲覧ページのスマホは `ContentToolbar` を**使っていない**。`frontend/src/pages/viewer/InventoryView.tsx` は
`isMobile ? <div className="viewer-toolbar">…</div> : <ContentToolbar …>` の形で、
**スマホ専用の1枚（折り返す flex）**を自前で持っている。`ContentToolbar` を使うのは PC のときだけ。

→ **在庫表も同じにする**。スマホ分岐は `<div className="inventory-toolbar">` を直接描き、
`ContentToolbar` は PC 分岐だけが使う。

**これにより `frontend/src/components/ContentToolbar.tsx` と
`frontend/src/components/ContentToolbar.css` は1文字も変えない**（初版は金型に CSS 変数を足す案だったが、
PO の「閲覧ページと全く同じに」の指示と、共通部品に触らずに済むこの形を採る）。
閲覧ページ・ほかのページへの波及は**構造的にゼロ**になる。

### 4-3. ページ側の CSS を1枚だけ新設する（閲覧ページの規則をそのまま写す）

`frontend/src/pages/inventory/` には今 CSS が1枚も無い。**`frontend/src/pages/inventory/InventoryToolbar.css`**
を新設し、`frontend/src/pages/inventory/InventoryToolbar.tsx` から import する。
中身は `frontend/src/pages/viewer/viewer.css` の `.viewer-toolbar` 系と**同じ規則**にする。

```css
/* 閲覧ページ viewer.css の .viewer-toolbar と同じ（スマホ専用の操作台） */
.inventory-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-3);
  margin: var(--space-3) 0;
}
/* 検索欄は1段目を独り占めする＝次の行に折り返させる（viewer-toolbar__search と同じ） */
.inventory-toolbar > .inventory-toolbar__search { flex: 1 1 100%; }
/* 2段目のボタンは中身なりの幅（viewer-toolbar__fixed と同じ） */
.inventory-toolbar > .inventory-toolbar__fixed { flex: 0 0 auto; }
/* パネルの中の「24時間以内」を押しやすくする（viewer.css の .viewer-fresh-check と同じ） */
.inventory-fresh-check { min-height: var(--size-icon-btn-lg); width: 100%; }
```

**2段になる仕組みも閲覧ページと同じ**: 段を2つ作るのではなく、**1枚の折り返す flex の中で
検索欄だけが `flex: 1 1 100%`（＝1行を独り占め）**なので、残りが自然に次の行へ回る。

### 4-4. スマホの操作台の中身

`.inventory-toolbar` の中に、この順で並べる（閲覧ページ `frontend/src/pages/viewer/InventoryView.tsx` と同じ並べ方）。

| 順 | 中身 | クラス |
|---|---|---|
| 1 | **検索欄**（`TextFieldControl`） | `field-h-md field-h-tap inventory-toolbar__search` |
| 2 | **並び替え**（`SelectControl`・**本便は今の形のまま**） | `field-h-md field-h-tap` |
| 3 | **詳細フィルタ**（枠なしの文字ボタン・数つき） | `layoutClassName="inventory-toolbar__fixed"` |

検索欄が1行を独り占めするので、**2と3が自然に2行目に並ぶ**。

`field-h-tap` は `@media (max-width: 767px)` の中にだけある（`frontend/src/components/field-size.css`）。
**CI の3つの project のうち 768px ではそもそもスマホ分岐が描かれない**
（`frontend/src/hooks/useIsMobile.ts` の境目は 767px）ので矛盾しない（審査 M2）。
**新 spec は必ず `page.setViewportSize` で 360 / 390 を明示する**（project 既定の幅に頼らない）。

**詳細フィルタのボタン**:

| | いま（スマホ） | この便の後（スマホ） |
|---|---|---|
| `variant` | `filterEnabled ? "primary" : "secondary"` | **常に `"ghost"`**（枠なしの文字ボタン。閲覧ページと同じ） |
| `size` | `"sm"` | **`"tap"`**（48px・`--font-sm`） |
| `layoutClassName` | `"field-h-md"` | **`"inventory-toolbar__fixed"`**（`.field-h-md` は外す。`.comp-btn--tap` と同じ詳細度で順序依存になるため。審査 L3） |
| 文字 | 「詳細フィルタ」 | **数が1以上なら「詳細フィルタ (n)」** |

**並び替えを「枠なしの文字ボタン＋右から出るパネル」にするのは便2**（PO 決定の4便の②）。
本便の時点でも**画面の中に入り、押せる**（P1/P2 を満たす）。

**幅の見積り（画面360px）**: 本文の左右余白を除いた内側は約288px。2行目は
並び替え 108px ＋ 間隔 `--space-3` 12px ＋ 詳細フィルタ 約130px（`--font-sm` 13.6px ＋ 左右 `--space-3` ＋「 (1)」）
＝ **約250px ≤ 288px**。余裕は約38px しかないので、**P5（高さ）を spec で必ず測る**
（溢れると右にはみ出さず**黙って3行に折り返す**＝`flex-wrap: wrap` のため。審査 M1）。

### 4-5. 「詳細フィルタ」に効いている数を出す（閲覧ページと同じ数え方）

24時間以内をパネルの中へ移すと、**既定で絞り込みが効いていることが上から見えなくなる**。
閲覧ページは同じ問題を「絞り込み (1)」の形で解いている（`frontend/src/pages/viewer/InventoryView.tsx`）。
**数え方をそのまま写す**（独自の定義を作らない）:

```
(24時間以内が入 ? 1 : 0)
+ (仕入元を1件以上選んでいる ? 1 : 0)
+ (コンディションを1件以上選んでいる ? 1 : 0)
+ (価格の下限か上限に入力がある ? 1 : 0)
+ (数量の下限か上限に入力がある ? 1 : 0)
```

5つとも `frontend/src/pages/inventory/InventoryPage.tsx` に状態がそろっていることを確認済み
（`freshOnly` / `selectedSupplierIds` / `showConditions` / `priceMin`・`priceMax` / `qtyMin`・`qtyMax`）。

辞書に `inventory.filterPanel.buttonWithCount` を**ja/en 1キーずつ追加**する
（閲覧ページの `viewer.filter.buttonWithCount` と同じ形。0件のときは今までどおり数を出さない）。

**この数は「カテゴリーの除外」「列の取捨」「形態」「有効化スイッチ」を数えない**
（閲覧ページに無い項目のため）。**過少申告になる**ことは承知のうえで、
PO が既に使っている閲覧ページと同じ意味にそろえることを優先する（審査 M5）。

### 4-6. 「リセット」と「24時間以内」をパネルの中へ（スマホだけ）

`frontend/src/pages/inventory/InventoryFilterPanel.tsx` は**すでにスマホ専用の中身を持っている**
（`showSupplierSelect` が真のときだけ仕入元・コンディション・価格・数量を出す）。同じ仕組みに乗せる。
**新しく足す2つは必ず `showSupplierSelect` で囲む**（囲まないと PC でパネルを開いたとき
同じ操作が2つになり、spec が strict mode 違反で落ちる。審査 L2）。

- **24時間以内**: パネルの**先頭**にチェックとして置く（閲覧ページ 便3 と同じ位置）。
  **`data-testid` は `inventory-fresh-check`**（上部の `inventory-fresh-toggle` とは**別の名前**にする。
  同じ名前を使い回すと「どちらを見ているか」が曖昧になる。閲覧ページ 便2 の教訓・審査 L1）。
- **リセット**: パネルの**末尾（「閉じる」の直前）**に `Button variant="secondary"` として置く。
  **`data-testid` は `inventory-reset-in-panel`**。
  **動きは今までと同じ**＝`resetAll`（`frontend/src/pages/inventory/InventoryPage.tsx`）は
  検索語・カテゴリー・並び替え・ページだけを戻し、**詳細フィルタの設定は意図的に残す**。
  K6 の文はこれに合わせてある（審査 H4）。
- 状態は親が持ったままで、**props を渡す先を増やすだけ**。
  `freshOnly` / `onFreshToggle` / `freshWindowHours` / `onReset` を `InventoryFilterPanel` の props に足す。

### 4-7. 触らないもの（境界）

- `frontend/src/components/ContentToolbar.tsx`（TSX は変更なし。CSS だけ1行）
- `frontend/src/components/Button.tsx` / `frontend/src/components/field-size.css`（金型）
- 閲覧ページ `frontend/src/pages/viewer/` 一式（ADR-1019・別コード）
- 絞り込みの計算・並び替えの計算・API・`resetAll` の中身

## ⑤ Acceptance Criteria（新しい spec で測る）

新 spec `frontend/tests-e2e/visual-language/inventory-toolbar-mercari.spec.ts`。
**幅は spec 側で 360 と 390 を明示**する（`frontend/tests-e2e/visual-language/inventory-helpers.ts` の
`gotoInventory` が `setViewportSize` を持つ）。PC の判定だけ 1280 で測る。

| # | 測ること |
|---|---|
| D1 | `.inventory-toolbar` の**すべての**子要素の右端が画面幅以下（360・390 とも） |
| D2 | 検索欄の幅が `.inventory-toolbar` の幅の**95%以上**（＝1行を独り占めしている） |
| D3 | 「並び替え」「詳細フィルタ」の**高さが48px以上** |
| D4 | 「並び替え」「詳細フィルタ」が**両方 viewport の中にある**（`boundingBox` が画面内） |
| D5 | 上部操作台に `inventory-reset-sort` と `inventory-fresh-toggle` が**無い**（スマホ） |
| D6 | 「詳細フィルタ」を押すと `inventory-filter-panel` が開き、その中に `inventory-fresh-check` と `inventory-reset-in-panel` が**ある** |
| D7 | `inventory-fresh-check` の**押せる高さが44px以上**（ADR-140。審査 M4） |
| D8 | 「詳細フィルタ」のボタンの文字に**数が入っている**（既定 `(1)`）。`inventory-fresh-check` を切ると**数が減る** |
| D9 | スマホでは `.content-toolbar` が**描かれず**、`.inventory-toolbar` が**1枚だけ**ある（閲覧ページと同じ作りであることの担保） |
| D10 | `.inventory-toolbar` の**高さが120px以下**（3行に折り返していないことの担保。P5） |
| D11 | document と `.mobile-content` の**横の超過が0** |
| D12 | **PC（幅1280）が変わっていない**: 子要素の並びに加えて、**検索欄の幅**と**詳細フィルタの `min-height` と `font-size`** を直す前の値で固定する（審査 H2） |
| D13 | 空振り防止: この端末では Playwright のブラウザが動かない（便0 の記録）ため、**直す前の本番実機の実測値**（recon の表＝右端654px・画面360px・`inventory-fresh-toggle` と `inventory-reset-sort` が上部に存在）を根拠に、D1・D4・D5 が**直す前なら必ず赤になる条件**であることを PR 本文に明記する |

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| スマホで上部の操作が1つも画面の外に出ない | Playwright: `frontend/tests-e2e/visual-language/inventory-toolbar-mercari.spec.ts` D1・D4 |
| 検索欄が横いっぱいになる | Playwright: 同 spec D2 |
| 2段目の2つが48px以上で押しやすい | Playwright: 同 spec D3 |
| 「リセット」「24時間以内」が上から消え、詳細フィルタの中にある | Playwright: 同 spec D5・D6 |
| パネルの中の「24時間以内」が44px以上 | Playwright: 同 spec D7 |
| 「詳細フィルタ」に効いている絞り込みの数が出る | Playwright: 同 spec D8 |
| スマホでは共通の操作台を使わず、閲覧ページと同じ1枚になっている／3行に折り返していない | Playwright: 同 spec D9・D10 |
| 横スクロールが出ない | Playwright: 同 spec D11 |
| PC の検索欄と詳細フィルタが1pxも変わっていない | Playwright: 同 spec D12 |
| 既存の単体テストを新しい形に合わせて更新してある | 単体: `frontend/src/pages/inventory/InventoryPage.toolbar.test.tsx`（K6 を2段・新しい並びに更新） |
| 共通の操作台の金型に1文字も触っていない | `git diff --stat` に `frontend/src/components/ContentToolbar.tsx` と `frontend/src/components/ContentToolbar.css` が**出てこない**こと／単体 `frontend/src/components/ContentToolbar.test.tsx` が緑のまま |
| 便0 の恒久計測が新しい形でも成立する | `frontend/tests-e2e/visual-language/inventory-mobile-baseline.spec.ts` が `.inventory-toolbar` を測り、CI ログの `childCount` が0に落ちていないこと |
| 既存の在庫表 spec が赤にならない | CI の画面検査が全件緑 |
| 直値・色・トークン規約に違反していない | `npm run check:all`（終了コード0）・pre-commit の ADR-067 検査 |
| 型が通る | `cd frontend && npm run generate:api-types && npx tsc --noEmit`（終了コード0） |
| 辞書の ja/en のキー数が一致する | `npm run check:all` の i18n 検査（ADR-027） |

## ⑥ 触るファイル

| ファイル | 変更 |
|---|---|
| `frontend/src/pages/inventory/InventoryToolbar.tsx` | スマホ専用の JSX 変数を新設し、**スマホ分岐から `ContentToolbar` を外して `.inventory-toolbar` を直接描く**。PC 分岐は不変 |
| `frontend/src/pages/inventory/InventoryToolbar.css` | **新規**（閲覧ページ `frontend/src/pages/viewer/viewer.css` と同じ4規則） |
| `frontend/src/pages/inventory/InventoryFilterPanel.tsx` | スマホのとき先頭に24時間以内、末尾にリセット（props 追加・`showSupplierSelect` で囲む） |
| `frontend/src/pages/inventory/InventoryPage.tsx` | `InventoryFilterPanel` に props を渡す。効いている数の計算を足す |
| `frontend/src/locales/ja.json` / `frontend/src/locales/en.json` | `inventory.filterPanel.buttonWithCount` を1キーずつ追加 |
| `frontend/src/pages/inventory/InventoryPage.toolbar.test.tsx` | K6 を新しい形（`.inventory-toolbar`・リセットと24時間以内はパネル）に更新 |
| `frontend/tests-e2e/visual-language/inventory-mobile-baseline.spec.ts` | スマホでは `.content-toolbar__left` が無くなるので、**`.inventory-toolbar` も測れるように**直す（ログの接頭辞は変えない） |
| `frontend/tests-e2e/visual-language/inventory-toolbar-mercari.spec.ts` | **新規**（D1〜D13） |
| `docs/handoff/inventory-toolbar-mercari/recon.md` ／ `docs/handoff/inventory-toolbar-mercari/design.md` | 本書類 |

## ⑦ 戻し方

PR をそのまま revert すれば元に戻る。新設したトークンは無く、金型の追加行は既定値つきの変数1つだけ。
辞書の追加キーは使われなくなるだけで害はない。

## ⑧ 削除するファイル

なし。

## ⑨ 外部・過去事例の参照と我々への応用

| 参照 | 我々への応用 |
|---|---|
| **お手本（メルカリ）の実測**（`docs/specs/design-system/visual-language/benchmark/mercari-search-filter.md` §1・§4） | 上部は48dp の行で、検索欄は横いっぱい。操作は枠で囲わない。→ 検索欄を全幅、詳細フィルタを枠なしに |
| **閲覧ページ 便3（PR #4752）** | 「24時間以内」を絞り込みパネルの先頭へ移して上部を1行短くした。→ 同じ移し方をそのまま採用 |
| **閲覧ページ 便5（PR #4759）** | シリーズ・並び替え・絞り込みを枠なしの文字ボタンにした。→ 詳細フィルタに適用（並び替えは便2） |
| **閲覧ページの「絞り込み (n)」**（`frontend/src/pages/viewer/InventoryView.tsx`） | パネルの中に隠した絞り込みが効いていることを数で見せる。→ 数え方をそのまま写す |
| **閲覧ページ 便13a の「変数で受ける」型** | 金型に `var(--…, 既定値)` を置き、呼ぶ側が値を渡す。子孫セレクタが要らない。→ `--content-toolbar-left-flex` に適用 |
| **便13a の分割の教訓** | 寸法の便と形の便を混ぜると CI の赤の切り分けができない。→ 並び替えのパネルは便2へ |

## ⑩ 弊害・トレードオフ

- **上部が1段ぶん高くなる**（44px → 約104〜112px）。一覧に使える高さがそのぶん減る。
  PO 決定（閲覧ページと同じ形）を承知のうえでの採用。
- **24時間以内の切り替えが1タップ増える**（上部 → パネルの中）。数の表示（K4）で「効いている」ことは分かる。
- **「詳細フィルタ」の有効化スイッチの入切が上から見えなくなる**（今は青い塗りで分かる）。
  閲覧ページと同じ「枠なし＋数」にそろえるための割り切り。スイッチ自体はパネルの中で見える。
- **数は過少申告**（4-5 の最後）。
- **2段目の余裕が約26px しかない**。文言が伸びる変更を入れるときは D10 が先に赤になる。
- **並び替えだけ枠が残る**（便2 で解消）。閲覧ページと完全に同じ見た目になるのは便2 の後。

## ⑪ 維持の仕組み

- D1〜D13 を CI の画面検査に常設する（`visual-language/` 配下に置く。直下に置くと1本も走らない）。
- D12（PC 不変）を入れることで、以後の便で PC を壊したらすぐ赤になる。
- D10（高さ112px以下）で、文言が伸びて3行になる退行を捕まえる。

## ⑫ 継続（この便の後）

PO 決定（2026-10-29）の**4便**のうち、本便は①。

| # | 内容 |
|---|---|
| **便2（②）** | **シリーズ（今のタブ行）と並び替えを、枠なしの文字ボタン＋右から出るパネルに**（閲覧ページ 便5 と同じ）。タブ行の注記が右に切れている問題もここで消える |
| **便3（③）** | **詳細フィルタを右から出るパネルに**し、中を「項目を押す→次の画面で選ぶ」形に（閲覧ページ 便2・便11・便13a と同じ）。今の浮かぶプルダウンはここで無くなる。**在庫表にしかない操作（カテゴリー除外・列の取捨・形態・有効化スイッチ・リセット）はこのパネルの中に残す**（PO 決定） |
| **便4（④）** | **検索を「押すと検索画面が開く」形に**（履歴と候補。閲覧ページ 便12a・便12b と同じ） |
| L3 | **効いている数の定義を在庫表に合わせる**（カテゴリー除外・列の取捨・形態・有効化スイッチを数えるか。PO 判断。便3 と一緒に見直すのが自然） |
| L4 | 便0 からの持ち越し **C2**（カードのラベル/値の幅配分）・**C3**（詳細パネルの折り返し）・**C4**（はみ出し0の恒久検査）・**C5**（`tests-e2e/` 直下の spec が走らない） |
| L5 | 原文パネルのタブが 68x36px で**44pxに足りない**（便0 の実測） |

## 対象 ADR

- **ADR-144**（UI 共通部品の遵守ガバナンス）: 金型の新設も変更もなし。**共通部品には1文字も触らない**。
  スマホ専用の操作台をページ側に持つのは、閲覧ページ（`frontend/src/pages/viewer/viewer.css` の
  `.viewer-toolbar`）に先例がある。
- **ADR-067**（デザイントークン強制）: 色・寸法は直値を書かない。flex の数値と `100%` は
  トークン対象外なので直書き可（閲覧ページ `frontend/src/pages/viewer/viewer.css` の先例と同じ）。
- **ADR-140**（タップ領域の下限 44px）: 2段目の2つは48px、パネルの24時間以内は44px以上（D3・D7）。
- **ADR-027**（i18n 強制）: 追加は ja/en 各1キー。キー数は一致させる。
- **ADR-093**（在庫表の詳細フィルタ）: パネルの役割は変えず、置くものを増やすだけ。
- **ADR-1019**（閲覧ページはアプリと別コード）: 本便は `frontend/src/pages/viewer/` に触らない。
