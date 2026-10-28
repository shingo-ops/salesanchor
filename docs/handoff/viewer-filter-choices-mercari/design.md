# design: 絞り込みパネルの寸法をお手本どおりにする（便13a）

> この文書は何か（1行）: 閲覧ページ（/viewer/）のスマホの絞り込みパネルを、お手本（メルカリ）と同じ
> **「画面いっぱいではなく左に60px残す」「選ぶ一覧の行を大きくして、チェックの印に左48pxを与える」**形にする。
> 選択肢が少ない項目をその場の**横並びボタン**にする話は便13b（別便）。

**recon**: docs/handoff/viewer-filter-choices-mercari/recon.md
**土台**: `release/viewer-filter-choices-mercari`（`origin/main` = `d10aff603`＝便12b #4831 を含む）

本便は `docs/handoff/viewer-filter-row-mercari/design.md` ⑫ の **H1** のうち②③にあたる。
①（少ない選択肢を横並びボタンに）は便13b に分ける。理由は⑫に書く。

## ① 区分：A（見た目の変更）

データの読み書き・絞り込みの計算・画面の行き来は**一切変えない**。変えるのは寸法だけ。
PC は1px も動かさない（4-5）。

## ② KGI（PO が実機で○×を判定できる粒度）

PO 決定（2026-10-27・`docs/handoff/viewer-control-tap-size/design.md` ②に記録済み）:
**「パネル幅83%・行60.7px で表示量が減ることを承知のうえで、完全にお手本通り」**。本便はその履行。

| # | PO が見て○×を言えること |
|---|---|
| K1 | 絞り込みを開くと、**パネルの左に画面の地（暗い幕）が少し見える**。今までは画面いっぱいだった |
| K2 | **その暗い幕を押すとパネルが閉じる**（今までは押す場所が無かった） |
| K3 | 「提供者」に進んだ先の**一覧の行が今より明らかに高い**（指で押しやすい） |
| K4 | その行の**チェックの四角が、行の左のゆったりした枠の中にある**（今は文字のすぐ隣に詰まっている） |
| K5 | 行の**文字が少し大きい**（お手本と同じ大きさ） |
| K6 | 行は**どこを押しても選べる**（今までどおり）。選ぶと**四角の中だけが塗られ、行の色は変わらない** |
| K7 | **シリーズ／並び替えのパネルと検索の画面は今までどおり画面いっぱい**（狭くなっていない） |
| K8 | **PC は何も変わらない** |

## ③ KPI（機械で測る値）

| # | 値 | いま | この便の後 | 出どころ |
|---|---|---|---|---|
| P1 | 絞り込みパネルの幅（画面360px） | 360px（100%） | **約299px（83%）**・左端 x≒61 | お手本 §2 |
| P2 | シリーズ/並び替えパネルの幅 | 360px | **360px のまま** | 本便の境界 |
| P3 | 選択画面のチェック行の高さ | 44px | **61px** | お手本 §3（60.7dp・整数へ丸め） |
| P4 | その行の文字の左端（行の左から） | 32px | **48px** | お手本 §3 |
| P5 | その行の文字の大きさ | 13.6px | **14.4px**（`--font-base`） | お手本 §3（17.7dp ÷ 1.2） |
| P6 | 行の幅 | パネル本文の幅（パネル−48px） | **パネル全幅** | お手本 §3 |
| P7 | スクロールせずに見える行の数（高さ700px） | 8件以上 | **5件以上**（下限を引き下げる） | P3 の帰結 |
| P8 | 閲覧ページ JS | 266.4KB | 300KB 以下のまま | 上限 |

## ④ 設計（How）

### 4-1. パネルの幅 ― `Drawer` に修飾クラスを1つ足す（既定は不変）

`frontend/src/components/Drawer.css:121-124` の `@media (max-width: 767px)` は
`.comp-drawer-panel { width: 100% }` でスマホを全幅にしている。ここを直接変えると **35ファイルの `Drawer`
すべてと、閲覧ページの他の2枚（シリーズ/並び替え・検索）**に波及する（recon §3）。

そこで `Drawer` に**任意プロパティ `mobileInset?: boolean`**（既定 `false`）を足し、`true` のときだけ
`comp-drawer-panel--mobile-inset` を付ける。CSS は **`@media` の中の `.comp-drawer-panel` より後ろ**に置く
（どちらも詳細度 0,1,0 なので後勝ち。便10 で `.comp-btn--tap` が同じ理由で `@media` の中にもう1行必要だったのと同型）。

```css
@media (max-width: 767px) {
  .comp-drawer-panel { width: 100%; }
  /* お手本（メルカリ）の絞り込みパネル: 画面の83%。左に地を残して背景を押して閉じられるようにする */
  .comp-drawer-panel--mobile-inset { width: var(--drawer-panel-w-mobile-inset); }
}
```

付けるのは **閲覧ページの絞り込みドロワー1枚だけ**（`frontend/src/pages/viewer/InventoryView.tsx:785` の `<Drawer`・属性は :792）。
他の2枚（:870 シリーズ/並び替え・:881 検索）には渡さない。

**背景を押して閉じられるようになる**: `frontend/src/components/Drawer.tsx:121` のオーバーレイは元から
`onClose` を持っている。全幅だったので押す場所が無かっただけ（`frontend/tests-e2e/visual-language/viewer-choice-sheet.spec.ts:319-325`
の実測コメントがその記録）。狭めると**自動的に押せるようになる**＝K2。お手本も同じ（§2 で左に60dp 空けている）。

### 4-2. 選ぶ一覧の行 ― 印に左48pxの枠を与える

`layout="inline"` のときだけ、印と文字をそれぞれ包む（`frontend/src/components/MultiSelect.tsx:93-107`）。
**`popover` と `row` の DOM は1バイトも変えない**＝PC と他画面は不変。

```tsx
<label className="comp-multiselect__option comp-multiselect__option--inline">
  <span className="comp-multiselect__check"><CheckboxControl ... /></span>
  <span className="comp-multiselect__option-text">{o.label}</span>
</label>
```

```css
.comp-multiselect__option--inline {
  width: 100%;
  min-height: var(--comp-multiselect-check-row-h);   /* 61px */
  gap: 0;
  padding: 0 var(--space-4) 0 0;                      /* 左は印の枠が持つ */
  font-size: var(--font-base);                        /* 14.4px */
}
.comp-multiselect__check {
  flex: 0 0 var(--comp-multiselect-check-col-w);      /* 48px */
  display: flex;
  align-items: center;
  justify-content: center;
}
.comp-multiselect__option-text { min-width: 0; }
```

**行はまるごと押せるまま**（`<label>` が全幅）。**選んだ合図は四角の塗りだけ**で行の背景は変えない
（お手本 §3-1。いまの `:hover` はスマホでは出ないので触らない）。

### 4-3. 行をパネル全幅にする ― 金型は既定0のまま、呼ぶ側が指定する

お手本の行は**パネル全幅**（§3）。いまは `.comp-drawer-body` の左右余白24px の内側にある
（`frontend/src/components/Drawer.css:97-101`）。金型が `Drawer` の余白を知っているのは筋が悪いので、
**打ち消し幅を CSS 変数で受け取り、既定は0** にする。

```css
/* MultiSelect.css — 既定 0px。他の画面は1px も動かない */
.comp-multiselect__list--inline {
  margin-inline: calc(-1 * var(--comp-multiselect-list-bleed, 0px));
}
```
```css
/* viewer.css — 選択画面でだけ、Drawer 本文の左右余白を打ち消す */
.viewer-filter-options { --comp-multiselect-list-bleed: var(--space-6); }
```

変数は継承するので**子孫セレクタを書かずに済む**（便1 の「子孫セレクタは詳細度が上がるので禁止」を守る）。
検索欄と見出しは余白の内側に残る。

### 4-4. 足すトークン（`frontend/src/tokens.css`）

| トークン | 値 | 根拠 |
|---|---|---|
| `--drawer-panel-w-mobile-inset` | `83%` | お手本 §2（300dp / 360dp） |
| `--comp-multiselect-check-row-h` | `61px` | お手本 §3 の 60.7dp を整数へ。**先例**: `--comp-search-row-h: 69px`（68.7dp・`frontend/src/tokens.css:168`） |
| `--comp-multiselect-check-col-w` | `48px` | お手本 §3（印が行の左48dpを占める） |

**既存で流用できるものが無いことの確認**（recon §5）: 61px は社内に存在しない。48px は `--field-h-tap`
（高さ用途）と `--space-12`（余白用途）があるが、**どちらも「列の幅」ではない**ので部品トークンを立てる
（便11 で `--comp-multiselect-row-h: 53px` を立てたのと同型）。

**83% を選び、`calc(100% - 60px)` を選ばなかった理由**: お手本の実測は360dp の1点だけなので、
「83%」と「左に60dp固定」はこの1点では区別できない（recon §1）。`docs/handoff/viewer-filter-row-mercari/design.md` ⑫ H1 が
**「画面の83%」**と書いているのでそちらを採る。**390px のときは左に66px 残る**（60pxではない）＝⑩に明記する。

### 4-6. 絞り込み root の先頭の1行を金型の class から外す（実装中に見つけた抜け）

`frontend/src/pages/viewer/InventoryView.tsx:499` の「24時間以内のみ」は、`MultiSelect` を使わずに
**金型の class を直接借りて**いる（`<label className="comp-multiselect__option comp-multiselect__option--inline">`）。
4-2 で `--inline` の寸法を変えると、**選択画面ではなく root のこの1行まで一緒に変わる**
（印が行の左端に詰まり、文字が印に接する）。4-5 の「root は触らない」に反するので外す。

**直し方**: 借りるのをやめ、`viewer.css` に**便12b までと同じ値を持つ `.viewer-fresh-check`** を作って移す。
見た目は1px も変えない（`display:flex` / `align-items:center` / `gap: var(--space-2)` /
`min-height: var(--size-icon-btn-lg)` / `padding: var(--space-1) var(--space-2)` / `font-size: var(--font-sm)` /
`color: var(--text-primary)` / `width: 100%` / `cursor: pointer` と `:hover` の `--bg-hover`）。

金型の class を外から借りている箇所は**ここ1つだけ**（`grep -n "comp-multiselect__option" frontend/src` で確認）。

### 4-7. 独立審査で見つかった2件（設計の修正）

**(1) 既存5ファイルの検査が必ず赤になる**。viewer 系の spec は絞り込みドロワーを開くとき
「**パネルの左端 x が 0 になるまで待つ**」ヘルパーを各ファイルに複製して持っている
（`frontend/tests-e2e/visual-language/viewer-inventory-mobile-filter.spec.ts:36-49` ほか4本）。
`mobileInset` で x が 61/66 になるので**この待ちが時間切れになる**。recon §4 の表はこのヘルパーを見落としていた。
**直し方**: 待ち方を「**パネルの右端が画面の右端に一致するまで**」に変える。パネルは `right: 0` の固定配置なので、
スライドが収まれば幅に関係なく右端が一致する＝**全幅のパネルでも狭めたパネルでも同じ判定で成立**する。
複製をやめ、共通の置き場 `frontend/tests-e2e/visual-language/viewer-helpers.ts` に `waitPanelSlidIn` を1つ置く。

**(2) タップした行に色が残る（K6 が実機で×になる）**。`.comp-multiselect__option:hover` の
`background: var(--bg-hover)`（`frontend/src/components/MultiSelect.css:44-46`）は、スマホでは
**タップ後に他をタップするまで色が残る**（sticky hover）。お手本 §3-1 は「**選んだ合図は四角の塗りだけ・
行の背景は変えない**」なので、`@media (hover: hover)` で囲う（PC は `hover: hover` なので今までどおり）。
`.viewer-fresh-check:hover` も同じ。社内の先例: `frontend/src/pages/inbox/InboxPage.css` の同型の書き方。

### 4-5. 触らないもの（この便の境界）

- **PC**: `layout="popover"` の DOM・CSS・`Drawer` の既定幅。1行も変えない。
- **絞り込みの最初の画面（root）の行**: 便11 で53px にした `.comp-multiselect__row`。そのまま。
- **シリーズ／並び替えのパネル・検索の画面**: `mobileInset` を付けない＝全幅のまま（K7・P2）。
- **選択肢が少ない項目の横並びボタン**: 便13b。
- **絞り込みの計算・並び順・件数**: 一切触らない。

## ⑤ Acceptance Criteria

新 spec `frontend/tests-e2e/visual-language/viewer-filter-panel-mercari.spec.ts`（360px・390px の2幅）。

| # | 固定すること |
|---|---|
| C1 | 絞り込みパネルの幅が**画面幅の 83%±1px**、左端 x が **画面幅の 17%±1px** |
| C2 | **シリーズ／並び替えのパネルは画面幅ちょうど**（絞り込みだけ狭めたことの裏取り） |
| C3 | 絞り込みが開いている間、**オーバーレイの押せる領域が左に 20px 以上**ある |
| C4 | **オーバーレイを押すと絞り込みパネルが閉じる**（K2） |
| C5 | 選択画面のチェック行の**高さが 61px 以上**・**x が パネルの左端と一致（±1px）**・**幅がパネル幅と一致**。選択画面は必ず縦スクロールするので、ブラウザが場所を取る形のスクロールバーを出すと幅がその分だけ狭くなる。**スクロールバーに左右されない判定を2つ置く**: ①左端の一致（スクロールバーは右に出る）②同じスクロール枠の中にある見出し（本文の余白の内側に残る）との**幅の差がちょうど左右の余白2つ分（48px）** |
| C6 | その行の**文字の左端が 行の左から 48px**（±1px） |
| C7 | その行の**文字の大きさが 14.4px** |
| C8 | 行の**どこを押しても選べる**。文字の上**と、今回新設した左48pxの枠（チェックの外側）**の両方を押して確かめる |
| C9 | **空振り防止**: `addStyleTag` で ①行を44pxに戻すと C5 の高さの判定が落ちる ②打ち消し幅を 0px に戻すと C5 の「左端の一致」と「見出しとの差48px」が落ちる — の2つを同じ検査の中で確かめる |
| C10 | ページの横はみ出しが無い（既存の `expectNoPageOverflow` と同じ作り） |
| C13 | **`.comp-multiselect__option:hover` の規則が `(hover: hover)` の中にある**（4-7(2)。読み込み済みスタイルシートを辿る静的な判定） |
| C14 | **パネルの中で横スクロールが起きていない**（`.comp-drawer-body` の `scrollWidth <= clientWidth`）。root 画面と提供者の選択画面の両方で測る。`.comp-drawer-body` は `overflow-y:auto` のため `overflow-x` も `auto` に計算され、**内部の横はみ出しは C10（ページ全体）では捕まらない** |
| C12 | **root の「24時間以内のみ」の行が変わっていない**: 高さ 44〜52px（61pxになっていない）・文字の左端が行の左から 32px（±1px）。4-6 の歯止め |

既存 spec の更新（**C11 だけは既存ファイル側にある番号**。C1〜C10・C12〜C14 は新 spec 側）:

| # | ファイル | 更新 |
|---|---|---|
| C11 | `frontend/tests-e2e/visual-language/viewer-inventory-mobile-filter.spec.ts:26` | `MIN_VISIBLE_OPTIONS` を **8 → 5**。理由をコメントに残す（44px→61px で見える件数が約28%減る。8 × 44/61 = 5.77 → 5） |
| C15 | `frontend/tests-e2e/visual-language/viewer-helpers.ts` | `waitPanelSlidIn` を新設（4-7(1)） |
| C16 | 上記＋`frontend/tests-e2e/visual-language/viewer-filter-row-mercari.spec.ts`・`frontend/tests-e2e/visual-language/viewer-control-tap-size.spec.ts`・`frontend/tests-e2e/visual-language/viewer-header-remove.spec.ts`・`frontend/tests-e2e/visual-language/viewer-top-compact.spec.ts` の `openFilterDrawer` | 待ち方を `waitPanelSlidIn` に置き換える（**判定の中身は変えない**）。`frontend/tests-e2e/visual-language/viewer-control-tap-size.spec.ts` のシリーズ/並び替え用の待ちは全幅のままなので触らない |

単体テスト `frontend/src/components/MultiSelect.test.tsx` に追加:

| # | 固定すること |
|---|---|
| U1 | `layout="inline"` のとき、各行に `comp-multiselect__check` と `comp-multiselect__option-text` がある |
| U2 | `layout="popover"` のとき、その2つは**出ない**（PC が変わっていないことの歯止め） |

`frontend/src/components/Drawer.test.tsx` に追加:

| # | 固定すること |
|---|---|
| U3 | `mobileInset` を渡さないと `comp-drawer-panel--mobile-inset` が**付かない**（既定不変） |
| U4 | `mobileInset` を渡すと付く |

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| 絞り込みパネルがスマホで画面幅の83%になり、左に地が残る | Playwright: `frontend/tests-e2e/visual-language/viewer-filter-panel-mercari.spec.ts` C1 |
| シリーズ／並び替えのパネルは全幅のまま（絞り込みだけ狭めた） | Playwright: 同 spec C2 |
| 背景（オーバーレイ）に押せる領域があり、押すと閉じる | Playwright: 同 spec C3・C4 |
| 選択画面のチェック行が61px以上で、パネル全幅に広がっている | Playwright: 同 spec C5（空振り防止は C9） |
| その行の文字の左端が行の左から48px | Playwright: 同 spec C6 |
| その行の文字が14.4px | Playwright: 同 spec C7 |
| 行はどこを押しても選べる（文字・左48pxの枠の両方） | Playwright: 同 spec C8 |
| ページにもパネル内部にも横はみ出しが無い | Playwright: 同 spec C10・C14 |
| 絞り込み root の「24時間以内のみ」の行が変わっていない | Playwright: 同 spec C12 |
| タップ後に行の色が残らない（規則が `(hover: hover)` の中にある） | Playwright: 同 spec C13 |
| 選択画面で一度に見える選択肢が5件以上20件以下 | Playwright: `frontend/tests-e2e/visual-language/viewer-inventory-mobile-filter.spec.ts` A5・A6（C11） |
| 既存の viewer 系 spec 5本が赤にならない（待ち方の1か所化） | CI の画面検査が全件緑（C15・C16） |
| `Drawer` の既定が変わっていない（`mobileInset` 未指定で修飾クラスが付かない） | 単体: `frontend/src/components/Drawer.test.tsx` U3・U4 |
| `MultiSelect` の popover（PC）が変わっていない | 単体: `frontend/src/components/MultiSelect.test.tsx` U1・U2 |
| 閲覧ページの配布物が300KB以下 | `node frontend/scripts/check-viewer-bundle.js`（実測 266.8KB） |
| 直値・色・トークン規約に違反していない | `npm run check:all`（終了コード0）・pre-commit の ADR-067 検査 |

## ⑥ 触るファイル

| ファイル | 変更 |
|---|---|
| `frontend/src/tokens.css` | トークン3件追加（4-4） |
| `frontend/src/components/Drawer.tsx` | 任意プロパティ `mobileInset` を追加（既定 false） |
| `frontend/src/components/Drawer.css` | `@media` の中に修飾クラス1規則を追加 |
| `frontend/src/components/Drawer.test.tsx` | U3・U4 |
| `frontend/src/components/MultiSelect.tsx` | `layout="inline"` のときだけ印と文字を包む |
| `frontend/src/components/MultiSelect.css` | `--inline` の寸法・`__check`・`__option-text`・一覧の打ち消し幅（既定0） |
| `frontend/src/components/MultiSelect.test.tsx` | U1・U2 |
| `frontend/src/pages/viewer/InventoryView.tsx` | 絞り込みドロワーに `mobileInset` を渡す（1行）／「24時間以内のみ」の class を `.viewer-fresh-check` に差し替え（4-6） |
| `frontend/src/pages/viewer/viewer.css` | `.viewer-filter-options` に打ち消し幅を指定（1行）／`.viewer-fresh-check` を追加（4-6） |
| `frontend/tests-e2e/visual-language/viewer-filter-panel-mercari.spec.ts` | 新規（C1〜C10） |
| `frontend/tests-e2e/visual-language/viewer-inventory-mobile-filter.spec.ts` | C11（定数1行＋コメント）／待ち方を共通化（C16） |
| `frontend/tests-e2e/visual-language/viewer-helpers.ts` | `waitPanelSlidIn` を新設（C15） |
| `frontend/tests-e2e/visual-language/viewer-filter-row-mercari.spec.ts` | 待ち方を共通化（C16） |
| `frontend/tests-e2e/visual-language/viewer-control-tap-size.spec.ts` | 同上（絞り込み用の1か所だけ） |
| `frontend/tests-e2e/visual-language/viewer-header-remove.spec.ts` | 同上 |
| `frontend/tests-e2e/visual-language/viewer-top-compact.spec.ts` | 同上 |
| `docs/handoff/viewer-filter-choices-mercari/recon.md` | 新規 |
| `docs/handoff/viewer-filter-choices-mercari/design.md` | 新規（本書） |
| `docs/handoff/viewer-filter-choices-mercari/review-opus.md` | 新規（独立審査の記録） |

## ⑦ 戻し方

1コミットなので `git revert` 1回。`Drawer` も `MultiSelect` も**任意の追加だけ**なので、
戻しても他の35ファイルに影響しない。

## ⑧ 削除するファイル

無し。

## ⑨ 外部・過去事例の参照と我々への応用

- **お手本（一次情報）**: `docs/specs/design-system/visual-language/benchmark/mercari-search-filter.md` §2・§3。
  実機の構造データの `bounds` から機械集計したもの。本便は新たな実機計測を必要としない
  （端末の ADB は `offline` で使えない。使える数字が既にリポジトリにあることを確認済み＝recon §1）。
- **社内の先例**:
  - 修飾クラスで `Drawer` の幅を変える: `frontend/src/components/Drawer.css:48-50` の `--wide`。
  - `@media` の中にもう1行置かないと負ける: 便10 の `.comp-btn--tap`（`docs/handoff/viewer-control-tap-size/design.md` 4-3）。
  - お手本の dp を整数のトークンへ丸める: 便12a の `--comp-search-row-h: 69px`。
  - 「印に48pxの枠を与えて文字の左端をそろえる」: 便12a の `.viewer-recent-row`
    （`frontend/src/pages/viewer/viewer.css:218-235`）。本便は同じ考え方を金型側で行う。
- **WCAG 2.5.5（Target Size）**: 行は44px以上を維持（61px）。

## ⑩ 弊害・トレードオフ

- **一度に見える選択肢が減る**（8件以上 → 5件以上）。PO が承知のうえで決めた変更（②）。
- **パネルが狭くなるぶん、長い提供者名の切れる位置が早くなる**（幅が約61px 減る）。
- **「83%」は390pxの端末では左に66px 残る**（お手本の実測点は360pxの1点のみ。4-4）。
  左を60px 固定にしたい場合は `--drawer-panel-w-mobile-inset` を `calc(100% - 60px)` に差し替えるだけで済む形にしてある。
- **背景を押すと閉じるようになる**。今まで出来なかった操作が増える＝**誤って閉じる**可能性がある。
  お手本と同じ挙動であり、選んだ内容は閉じても残る（絞り込みは即時反映のため）。
- **タップ後の行の色を消す**（4-7(2)）。PC は `hover: hover` なので今までどおりだが、**タッチ対応のPCでは行のホバー色が出なくなる**画面が出る可能性がある（`layout="inline"` の実使用は閲覧ページだけなので実害は無い）。
- **`MultiSelect` の inline の DOM が2要素増える**。`popover` / `row` は不変なので波及しない。
- **金型の class を外から借りていた1か所が表に出た**（4-6）。借りたままだと金型を直すたびに巻き添えになるので、
  本便で viewer 側の class に移す。見た目は1px も変えないが、**他に同じ借り方をしている箇所が将来増えると同じ事故が起きる**。

## ⑪ 維持の仕組み

- C1〜C10 の新 spec が**2幅 × 既存の project 数**で回る。
- **C9 が空振り防止**（行を44pxに戻すと落ちることを本物の Chromium の中で示す）。便10 の B7c・B7d と同じ型。
- U2・U3 が「PC と他の `Drawer` が変わっていないこと」の歯止め。
守り手: `frontend/tests-e2e/visual-language/viewer-filter-panel-mercari.spec.ts` ・
`frontend/src/components/MultiSelect.test.tsx` ・ `frontend/src/components/Drawer.test.tsx`

- **C12 が「root は変わっていないこと」の歯止め**（4-6 の抜けは既存の検査では1本も赤にならなかった＝網が無かった）。

## ⑫ 継続（この便の後）

| # | 内容 |
|---|---|
| J1 | **便13b＝選択肢が少ない項目（2〜6件）をその場の横並びボタンに**（お手本 §2-2。48px・間隔8px・折り返す）。**本便と分けた理由**: 横並びの選べるボタンは社内に金型が無く（recon §5）、新しい部品の形・`aria-pressed` の扱い・何件から次の画面に進ませるかの境目（6件）を決める必要がある。寸法だけの本便と混ぜると、CI が赤になったときにどちらが原因か切り分けられない |
| J2 | **H2＝シリーズ名の幅の優先順**（便10 からの持ち越し・**PO 判断待ち**）。並び替えに最長の項目を選ぶと360pxで約19px 足りない |
| J3 | **H3＝アプリの在庫表（`frontend/src/pages/inventory/InventoryPage.tsx`）への横展開**。閲覧ページが仕上がってから |
| J4 | 便6〜便8 の持ち越し: C-up・C-out・C-sb・C-perf・C-tap／E1・E2・E3・E5・E6・E7／F5・F6・F7・F8 |
| J6 | **`frontend/tests-e2e/visual-language/viewer-choice-sheet.spec.ts`:129-138 の `waitPanelSlidIn` だけ複製が残る**（シリーズ/並び替えは全幅のままなので今回は触らない）。次にこのパネルの幅を変えるときは共通の置き場へ寄せる |
| J7 | **`.comp-drawer-body` の左右余白と打ち消し幅の一致は、検査では「実際の計算済み padding を読む」ことで守っているが、トークンそのものを共有してはいない**。金型側に「本文の余白」を表すトークンを立てるのが本筋 |
| J5 | 便12b の積み残し: 候補の一覧に見出しも読み上げ用のラベルも無い／候補が0件のときの表示はお手本未確認 |

## 対象 ADR

ADR-1019（閲覧ページは別アプリ）／ADR-067（値は CSS 変数参照のみ）／ADR-140（タップ領域44px以上）／ADR-144（金型の増やし方）
