# design: 閲覧ページ 検索欄とプルダウンをお手本の48dpにそろえる（便10＝大きさの便）

> この文書は何か（1行）: PO 指示「検索欄とプルダウンをお手本（メルカリ）と全く同じ UI/UX にする」のうち、
> **高さと文字の大きさだけ**をお手本に合わせる。作り（出し方・現在値の文言）は便11・便12 で直す。

**recon**: docs/handoff/viewer-control-tap-size/recon.md
**土台**: `release/viewer-control-tap-size`（`origin/main` = 77b40a1ae）

## ① 区分：B（見た目の変更。操作の流れは変わらない）

押せる場所と押した結果は変えない。変えるのは**高さ・文字の大きさ・山形の大きさ**だけ。

## ② KGI（PO が実機で○×を判定できる粒度）

PO 決定（2026-10-27・3件とも本会話で受領）:
1. 「お手本と全く同じ UI UX にする」。対象は「**検索欄とプルダウン**」。
2. お手本の「文字 16.3dp」は箱の高さで実体は約13.6dp（recon §1）と示したうえで、文字は「**お手本どおり（13.6px）**」。
3. 表示できる量が減る点（パネル幅83%・行60.7dp）を示したうえで「**完全にお手本通り**」＝便12 で実施。

| # | PO が見て○×を言えること |
|---|---|
| K1 | 検索欄・シリーズ・並び替え・絞り込み・「決定する」が**同じ高さ（48px）にそろった** |
| K2 | 3つの操作ボタンの**文字がお手本と同じ大きさ**に見える |
| K3 | **シリーズ名が読める**（既定の表示で切れていない） |
| K4 | 3つが**1行に並んだまま**で右にはみ出していない |
| K5 | 上部が**お手本（146dp）より低い** |

## ③ KPI（機械で測る値）

| # | 値 | いま | この便の後 |
|---|---|---|---|
| P1 | 操作ボタン3つの高さ | 44px | **48px ちょうど** |
| P2 | 同 文字 | 12px | **13.6px** |
| P3 | 山形の幅 | 24px | **16px** |
| P4 | 上部の検索欄の高さ（スマホ） | 44px | **48px ちょうど**（PC は min-height 36px のまま＝実高 39.6px で不変） |
| P5 | パネル内の候補を絞る検索欄の高さ | 44px | **48px** |
| P6 | 「決定する」の高さ | 44px | **48px** |
| P7 | 一覧の先頭カードの y | 124px | **132px**（お手本146dp 未満） |
| P8 | 360px でシリーズ名が切れている量（既定の表示） | 0px | **0px のまま**（余り8px） |
| P9 | 閲覧ページ JS | 260.8KB | 300KB 以下のまま |

## ④ 設計（How）

### 4-1. 操作ボタン3つ ― 金型に size を1つ足す（`tap`）

必要な組み合わせは **高さ48px・文字13.6px・横の余白12px**。既存の sm/md/lg のどれでもない:

| 既存 | 高さ（スマホ） | 文字 | 横の余白 |
|---|---|---|---|
| sm | 44px | 12px | 12px |
| md | 44px | 14.4px | 20px |
| lg | 48px | 16px | 24px |

**これは大小の段ではなく役割**（お手本の「枠なしの文字ボタンを並べた操作行」）なので、
`xl` のような段の名前ではなく **`tap`** と名付ける。

`frontend/src/components/Button.css` に、**`.comp-btn--lg`（`:46-50`）の直後**へ:

```css
/* お手本（メルカリ）の操作行。48dp の行に、枠なしの文字ボタンを並べる用。
   文字は --font-sm（お手本の実測 13.4dp 相当）・横の余白は sm と同じに詰める */
.comp-btn--tap {
  min-height: var(--comp-btn-height-lg);
  padding: var(--space-1) var(--space-3);
  font-size: var(--font-sm);
}
```

**`@media (max-width: 767px)` の中にも1行足す**（recon §3 の後勝ち。入れないと `.comp-btn` の 44px に負ける）:

```css
  .comp-btn--lg,
  .comp-btn--tap {
    min-height: var(--comp-btn-height-lg);
  }
```

- **新しいトークンは0**（`--comp-btn-height-lg` 48px・`--font-sm` 13.6px・`--space-1`/`--space-3` はすべて既存）。
- `frontend/src/components/buttonAppearance.ts:36` の三項の連鎖に1段足すので、
  **`variant="tab"` のときは付かない**既存の規則を自動で引き継ぐ。
- `.comp-btn--icon-only`（`frontend/src/components/Button.css:134`）はさらに後ろなので、
  アイコンだけのボタンでは従来どおり余白0が勝つ。
- **既定は変わらない**: `size` を渡していない既存の呼び出しは `md` のままでクラスは1つも増えない。
- **`iconOnly` との併用に1規則足す**（独立審査の指摘7）。`@media` の `.comp-btn.comp-btn--icon-only`（0,2,0）が
  44px を当てるので、`.comp-btn--tap`（0,1,0）は負ける。`.comp-btn--lg.comp-btn--icon-only`
  （`frontend/src/components/Button.css:148-152`）と同じ形で `.comp-btn--tap.comp-btn--icon-only` を足し、
  見本では**文字ボタンだけ**を見せる（`tap` は文字ボタン用）。

### 4-2. 山形を 16px にする（これが無いと 360px で切れる）

いまは大きさ指定なしで既定の 24px（`frontend/src/constants/icons-base.tsx:29`）。
13.6px の文字には `frontend/src/constants/iconSizes.ts` の `md`（16px）が釣り合う。
recon §4 の表のとおり、**24px のままだと 360px で8px 足りずシリーズ名が切れる**。

### 4-3. 検索欄 ― 高さの金型に「スマホのときだけ効く段」を足す（`field-h-tap`）

入力部品の高さは3段で最大が 44px（`frontend/src/components/field-size.css:7-9`）＝**48px の段が無い**。
`--comp-input-height-mobile` を 44→48 に変える案は `TextFieldControl` を使う **80ファイル**全部に波及するので採らない。

**PC は 1px も動かさない**（独立審査の指摘1で設計を変更）。理由: PO 決定の対象はスマホのモバイル版で、
PC の閲覧ページでは同じ操作台に **36px の兄弟**が並んでいる
（範囲入力は `frontend/src/components/ContentToolbar.tsx:78`・`:90` が `field-h-md`、
並び替えは `frontend/src/pages/viewer/InventoryView.tsx:543` が `SelectControl size="sm"`、
リセットは同 `:604` が `size="sm"`）＝検索欄だけ 48px にすると**PC に新しい不ぞろいを作る**。
お手本の 48dp は**スマホ（360dp）の操作単位**（`docs/specs/design-system/visual-language/benchmark/mercari-search-filter.md:7-9`）
なので、段もスマホ限定にするのが筋が通る。

- `frontend/src/tokens.css` に **`--field-h-tap: 48px`** を1件追加。**新規トークンは1件**
  （PR 本文の「デザイントークン変更時」4項目が必要。`frontend/scripts/check-new-tokens.js:78-85`）。
  名前は大小の段ではなく**役割**（お手本の操作単位）なので `xl` ではなく `tap`（ボタンの `size="tap"` と同じ考え方）。
- `frontend/src/components/field-size.css` に:

```css
/* お手本（メルカリ）の操作単位 48dp。スマホのときだけ効く段で、PC の高さは
   field-h-sm/md/lg で別に指定する（併記して使う）。
   FormField.css の @media が .comp-field__input / .comp-field__select / .comp-select__control の
   3つに 44px を当てるので、勝たせるために複合セレクタを併記する（幅の field-w-* と同じ型・§AW AW-2b） */
@media (max-width: 767px) {
  .field-h-tap,
  .comp-select__control.field-h-tap,
  .comp-field__select.field-h-tap,
  .comp-field__input.field-h-tap { min-height: var(--field-h-tap, 48px); box-sizing: border-box; }
}
```

**3つ併記する理由**: 負ける相手が3つあるため（recon §7）。本便が触る3か所はすべて
`TextFieldControl`（`.comp-field__input`）だが、⑫ G6（アプリの `InventoryToolbar` への横展開）には
`SelectControl` が居る（`frontend/src/pages/inventory/InventoryToolbar.tsx:72`・`:85`）ので、
最初から3本立てで書く（追加費用0。独立審査の指摘8）。

**入力欄の実際の高さは `min-height` だけでは決まらない**（実装中に判明）。
`.comp-field__input`（`frontend/src/components/FormField.css:47-61`）は
`padding: var(--space-2) var(--space-3)`・`border: 1px`・`font-size: var(--font-base)`・
`line-height: var(--line-height-base)` なので中身の高さは 14.4×1.5 ＋ 8×2 ＋ 1×2 = **39.6px**。
したがって `min-height` が 36px（PC）だと実高は **39.6px**、44px（現在のスマホ）や 48px（本便のスマホ）だと
`min-height` が勝つ。**便4 の実測 124px（= 12+44+12+44+12）がこれと整合する**。

呼び出し側は `field-h-md` を**残したまま** `field-h-tap` を足す（**PC は min-height 36px のまま・スマホは 48px**）。
対象は `frontend/src/pages/viewer/InventoryView.tsx:362`（上部）・`:266`（提供者）・`:293`（コンディション）。
メディアクエリの中の複合セレクタ（0,2,0）が `field-h-md`（0,1,0）にも勝つので、スマホでは 48px が出る。

### 4-4. 「決定する」― 既存の lg にするだけ（金型は触らない）

`frontend/src/pages/viewer/InventoryView.tsx:328-339` の `size="md"`（`:331`）を **`size="lg"`** に。
lg はスマホで 48px（`frontend/src/components/Button.css:159-161`）。`fullWidth` は既に付いており、
お手本の 268dp＝パネル 300dp から左右余白 16dp を引いた**パネル内の全幅**と同じ考え方。
横の余白は全幅なので見た目に出ない。**金型の変更は不要**。

### 4-5. 触らないもの（この便の境界）

| 触らない | 理由 |
|---|---|
| 選択肢の行の高さ（44px→60.7dp） | 便12。パネル幅83%と一緒に変えないと一度に見える件数の基準が二度動く |
| 現在値を件数から名前のカンマつなぎへ | 便11（文言の追加を伴う） |
| 選択肢が少ない項目の横並び化 | 便12 |
| 一覧（表）の文字・行 | PO 決定の D2② ＝ 本番で見てから判断。お手本側の実測も未取得 |
| PC（768px 以上）の見た目 | **1px も動かさない**。3つのボタンは `isMobile` の分岐の中だけ（`frontend/src/pages/viewer/InventoryView.tsx:547`）、`field-h-tap` はスマホのメディアクエリの中だけ、「決定する」はスマホのパネルの中だけ |
| アプリの `frontend/src/pages/inventory/InventoryPage.tsx` | 「完成したらアプリの在庫表に横展開」＝便12 の後（⑫ G6） |

## ⑤ Acceptance Criteria

`U` は単体テスト、`B` は画面検査（本物の Chromium・**360px と 390px の両方**）。

| # | 基準 | 測り方 |
|---|---|---|
| U1 | `size="tap"` で `comp-btn--tap` が付く | 単体（**直す前は赤**＝型に無い） |
| U2 | `size` を渡さないと `comp-btn--tap` が付かない（既定不変） | 単体 |
| U3 | `variant="tab"` のときは `size="tap"` でも付かない | 単体（既存規則の継承を固定） |
| U4 | 型検査 `npx tsc --noEmit` が0件（**CI では走らないので手元で必ず実行**。`frontend/package.json` の `check:all` に型検査は無い） | 手元 |
| U5 | `frontend/src/components/Button.test.tsx` の既存（`it` 6本・`it.each` 展開で12ケース）が緑のまま | 手元＋CI |
| B1 | 操作ボタン3つの高さが **48px ちょうど** | 画面検査・2幅（**直す前は赤**＝44px。**等値**にして上限の抜け道を塞ぐ） |
| B2 | 同 文字が **13.6px**（`getComputedStyle` の `font-size`） | 画面検査・2幅（**直す前は赤**＝12px） |
| B3 | 山形2つの幅が **16px** | 画面検査・2幅（**直す前は赤**＝24px） |
| B4 | 上部の検索欄の高さが **48px ちょうど** | 画面検査・2幅（**直す前は赤**＝44px） |
| B4b | **PC 幅（1280px）では上部の検索欄に `field-h-tap` が効かない**（`min-height` が `36px` のまま・実高は 48px 未満） | 画面検査（PC 不変の固定。独立審査の指摘1）。**「36px ちょうど」では赤になる**＝`.comp-field__input`（`frontend/src/components/FormField.css:47-61`）の中身の高さが 文字14.4×1.5 ＋ 余白8×2 ＋ 枠2 = **39.6px** で `min-height: 36px` を上回るため。どちらの規則が勝ったかは `min-height` で測る |
| B5 | パネル内の候補を絞る検索欄の高さが **48px** | 画面検査・2幅（**直す前は赤**＝44px）。**道順**: 絞り込みを開く → `viewer-provider-row` を押して選択画面へ入る → そこで測る |
| B6 | 「決定する」の高さが **48px** | 画面検査・2幅（**直す前は赤**＝44px）。**B5 と同じ道順が必要**＝`viewer-filter-apply` は先頭画面には存在しない（`frontend/src/pages/viewer/InventoryView.tsx:328` が `filterView === "root"` のとき `undefined`） |
| B7a | 既定の表示で**シリーズ名が切れていない**（`viewer-tab-select` 配下の `.viewer-toolbar__label` の `scrollWidth` ≤ `clientWidth` + 1） | 画面検査・2幅（**直す前も緑**＝空振り対策は下記） |
| B7b | 並び替えに最長の項目を選んだ後も、シリーズのラベル枠が **13.6px（1文字分）以上** | 画面検査・2幅（見込みは 21.6px＝約1.6文字。もう1文字長い並び替えが来たら赤になる歯止め。⑩・⑫ G1） |
| B8 | 3つの y が同じ・右端が画面幅以内・ページに横はみ出しが無い | 画面検査・2幅 |
| B9 | 一覧の先頭カードの y が **132px 以内** | 画面検査・2幅（既存3本の `MAX_TOP_Y` を 128→132 に更新。計算値が整数で決定論的なので余白を持たせない） |
| B10 | 閲覧ページ JS が 300KB 以下 | CI（`frontend/scripts/check-viewer-bundle.js`） |
| B11 | **既存 `frontend/tests-e2e/visual-language/viewer-inventory-mobile-filter.spec.ts` の A5・A6・A15 が緑のまま** | CI（**変更しない・確認のみ**。本便で選択画面の検索欄 +4px とフッタ +4px になるため、同 `:26-27` の「一度に見える行が8件以上20件以下」の下限 8 を割らないことを実装直後に確かめる。独立審査の指摘2） |

**B7a が空振りにならないことを、検査の中で証明する（便6〜便9 で3便連続で踏んだため）**:
B7a は直した後も緑なので、それだけでは何も測っていない可能性が残る。
**この端末では Playwright のブラウザが動かない**ので「壊して赤を見る」を手元でできない。
そこで**壊した状態を spec の中で作る**:

| # | 基準 | 測り方 |
|---|---|---|
| B7c | 3つのボタンの文字を 16px に差し替えると、シリーズ名が**切れる**（`scrollWidth` > `clientWidth`） | 画面検査・360px。`page.addStyleTag` で `font-size: 16px !important` を当ててから測る |
| B7d | 山形を 24px に差し替えると、シリーズ名が**切れる** | 画面検査・360px。同じく `.viewer-toolbar__caret { width/height: 24px !important }` |

recon §4 の表のとおり、どちらも 360px で 8px 以上足りなくなる＝**切れるはず**。
B7c・B7d が緑（＝切れることを検出できる）なら、**同じ測り方の B7a は空振りではない**ことが
本物のブラウザの中で保証される。この2件は**「なぜ 13.6px と 16px の山形を選んだか」の根拠**としても残る。

**locator の注意**: B7a・B7b・B7c・B7d はすべて **`viewer-tab-select` の配下**の
`.viewer-toolbar__label` に限る。`.viewer-toolbar__label` は並び替え側にもあり、そちらは
`flex: 0 0 auto` で絶対に切れないので `.first()` 等では常に緑になる（recon §5）。

**B9 の上限を 128→132 にする根拠**:
計算値は 12＋48（検索欄）＋12＋48（ボタン行）＋12 = **132px**（recon §6。便4 の実測 124px と同じ式）。
内訳の全項目が整数で、変動しうる2行は **B1・B4 が「48px ちょうど」の等値で固定**するので
**y は決定論的に 132**＝余白を足す理由が無い（初版の 136 は独立審査の指摘5で「誰も測っていない4px」と判定）。
お手本の上部は 146dp なので**お手本より低いまま**。
**`MAX_TOP_Y = 128` は3本に複製されている**（recon §6）ので**3本同時に更新する**。1本だけ直すと残り2本が赤。
独立審査が3本それぞれの他のテストを読み、**48px 化・13.6px 化で赤になるものは無い**ことを確認済み
（唯一の未検証が B11 の A6）。

**置き場**: `frontend/tests-e2e/visual-language/` の中に viewer-control-tap-size.spec.ts として置く
（`frontend/playwright.config.ts` の `testMatch` が `visual-language/` 配下に限るため、直下に置くと CI で1本も走らない）。
疑似応答は既存の `frontend/tests-e2e/visual-language/viewer-helpers.ts` の `gotoViewer` を使う
（「取得回数で切り替える」形は使わない＝`React.StrictMode` の二重取得で前提が崩れる）。

## ⑥ 触るファイル

| ファイル | 変更 |
|---|---|
| `frontend/src/components/buttonAppearance.ts` | `ButtonSize` に `"tap"` を追加し、クラス付与の三項に1段足す |
| `frontend/src/components/Button.css` | `.comp-btn--lg` の直後に `.comp-btn--tap` を追加＋`@media (max-width: 767px)` に1行追加 |
| `frontend/src/components/Button.test.tsx` | U1〜U3 を追加（既存4件は触らない） |
| `frontend/src/components/Button.stories.tsx` | `tap` の見本を1つ追加 |
| `frontend/src/pages/design-preview/sections/ButtonSection.tsx` | 大きさの並びに `tap` を1つ追加 |
| `frontend/src/tokens.css` | `--field-h-tap: 48px` を1件追加（既存3段の隣） |
| `frontend/src/components/field-size.css` | `@media (max-width: 767px)` の中に `.field-h-tap` の4本立てを追加 |
| `frontend/src/pages/viewer/InventoryView.tsx` | 操作ボタン3つ（`:413`・`:428`・`:554`）を `size="tap"`／山形2つ（`:422`・`:437`）に `size={ICON.md}`／検索欄3か所（`:362`・`:266`・`:293`）に `field-h-tap` を併記／「決定する」（`:331`）を `size="lg"` |
| `frontend/tests-e2e/visual-language/viewer-top-compact.spec.ts` | `MAX_TOP_Y` 128→132（理由をコメントに） |
| `frontend/tests-e2e/visual-language/viewer-choice-sheet.spec.ts` | 同 |
| `frontend/tests-e2e/visual-language/viewer-header-remove.spec.ts` | 同 |
| `frontend/tests-e2e/visual-language/viewer-inventory-mobile-filter.spec.ts` | **変更しない**。A5・A6・A15 が緑のままであることを確認するだけ（B11） |
| frontend/tests-e2e/visual-language/viewer-control-tap-size.spec.ts | 新規（B1〜B9）。この便で作るのでパスの囲みを付けない |
| `docs/handoff/viewer-control-tap-size/recon.md` | 新規 |
| `docs/handoff/viewer-control-tap-size/design.md` | 新規（本書） |

**既存行を削るファイル**（書き換えを含む）: `frontend/src/components/buttonAppearance.ts`・
`frontend/src/components/Button.css`・`frontend/src/pages/viewer/InventoryView.tsx`・
`frontend/tests-e2e/visual-language/viewer-top-compact.spec.ts`・
`frontend/tests-e2e/visual-language/viewer-choice-sheet.spec.ts`・
`frontend/tests-e2e/visual-language/viewer-header-remove.spec.ts`。

## ⑦ 戻し方

1コミットなので `git revert` 1回。金型側は**追加だけ**（新しい size の値・新しい高さの段）なので、
戻しても既存の呼び出し側に影響は出ない。

## ⑧ 削除するファイル

無し。

## ⑨ 外部・過去事例の参照と我々への応用

- **お手本（一次情報）**: `docs/specs/design-system/visual-language/benchmark/mercari-search-filter.md`。
  要点1「**48dp で全部そろえている**」（検索欄・札・並び替え・絞り込み・パネルの帯・確定ボタンがすべて48dp）が
  この便の根拠そのもの。文字は同書の幅の実測から 13.4dp と逆算した（recon §1）。
- **WCAG 2.5.5（Target Size）**: 下限44px。48px は上回る方向なので ADR-140 から外れない。
- **社内の過去事例（効いたもの）**: ①便2・便5 の「金型は任意の口だけ足して既定不変」。②幅の金型が
  `.comp-field__input.field-w-*` の複合セレクタでスマホ規則に勝たせた前例（`frontend/src/components/field-size.css:14-22`）。
  **高さの4段目はこの2つの型をそのまま使う**ので新しい発明が無い。
- **社内の過去事例（避けるもの）**: 便3 で「sm は28pxだから並ばない」と誤診した原因は `@media` の後勝ちの
  見落とし。本便は recon §3 で先に押さえ、新しい size を `@media` の中にも入れる設計にした。
- **自己審査で潰した誤り（2026-10-27・独立審査 BLOCK）**: 初版は①ボタンの枠線2px と②絞り込みの既定表示
  「絞り込み **(1)**」を数え落として横幅を約30px 甘く見積もり、③既存検査が折り返しを捕まえると誤記していた。
  3件とも現物で確認して訂正済み（recon §4・§5）。

## ⑩ 弊害・トレードオフ

- **`field-h-tap` は「幅に依らない3段」という入力部品の金型の文法から外れる**（スマホのときだけ効く段）。
  そのぶん PC は1px も動かないという利点を取った（独立審査の指摘1）。**併記して使う**運用を
  `frontend/src/components/field-size.css` のコメントに残す。
- **シリーズ名の余裕が 12px→8px に減る**（recon §4 の訂正版。初版は「38px→8px」と3倍ずれていた＝
  **現状でも余裕はもともと薄い**）。既定の表示では切れないが、
  **並び替えに最長の項目「在庫が多い順」を選ぶと 360px で約19px 足りず、シリーズ名が山形だけに近くなる**
  （いまでも約12px 足りないので新しい不具合ではないが悪化する。実測見込みのラベル枠は 21.6px＝約1.6文字＋「…」）。B7b で下限を1文字分に固定し、
  **直し（縮む順の見直し）は ⑫ G1 に起票**する。直す案は「並び替えも縮む側にして両方を途中で切る」
  （`frontend/src/pages/viewer/viewer.css` の `flex` を2行変える）で、どれを優先して読ませるかの PO 判断が要る。
- **金型に size の値が1つ増える**（`tap`）。大小の段ではなく役割名なので、段の順序の意味は壊れない。`ButtonSize` を `Record` で網羅している箇所は0件なので型が壊れる場所も無い。
  誤用の歯止めは U2・U3 と、外観見本・Storybook に「お手本の操作行用」と書くこと。
- **新規トークン1件**（`--field-h-tap`）。PR 本文のチェックリスト4項目が必要。

## ⑪ 維持の仕組み

守り手:
- 新設する画面検査 viewer-control-tap-size.spec.ts（`frontend/tests-e2e/visual-language/` 配下。
  CI の画面検査で毎 PR・2幅×3 project）— 高さ5か所・文字・山形・切れ・1行・上限を機械で固定する。
- `frontend/src/components/Button.test.tsx`（`npm run test:unit` と pre-commit）— `tap` の既定不変と tab 除外。
- `frontend/src/pages/design-preview/sections/ButtonSection.tsx`（外観見本）— 新しい size が見本に無い状態を作らない。
- `frontend/scripts/check-new-tokens.js`（CI）— トークン追加の理由を PR 本文に残させる。独立審査が `frontend/scripts/` を全部読み、**本便で引っかかる関所はこれだけ**と確認済み。

## ⑫ 継続（この便の後）

| # | 内容 |
|---|---|
| G1 | **シリーズ名の幅の優先順**（⑩）。並び替えに最長の項目を選ぶと 360px で約19px 足りない（現状でも約12px 足りない）。案は「並び替えも縮む側にして両方を途中で切る」（`frontend/src/pages/viewer/viewer.css` の `flex` を2行）。**どれを優先して読ませるかの PO 判断が必要** |
| G2 | **便11＝現在値の出し方**。複数選択（提供者・コンディション）の現在値を件数「3件」から**選んだ名前のカンマつなぎ**へ、未選択は「**指定しない**」へ。文言追加を伴う（ADR-027） |
| G3 | **便12＝選択肢の出し方をお手本の2通りに**。①少ない項目（2〜6件）はその場に横並びボタン（48dp・間隔8dp・折り返す）②チェックボックス一覧の行を 60.7dp・印が行の左48dp を占める形へ ③**パネル幅を画面の83%（左に60dp残す）へ**。PO 決定「完全にお手本通り」。既存検査の「一度に8〜20件見える」の基準も同時に更新する |
| G4 | **お手本の一覧（商品カード）側は未実測**。D2② に進むなら撮影・実測が先（実機の ADB は現在未接続） |
| G5 | 便6〜便8 の持ち越し: **C-up**・**C-out**・**C-sb**・**C-perf**・**C-tap**／**E1**（初期フォーカス・復帰の共通化。複製は3金型と下調べ済み）・**E2**・**E3**・**E5**・**E6**（調査済み・未コミットの作業ツリーに残置）・**E7**／**F5**・**F6**・**F7**・**F8** |
| G6 | **アプリの在庫表への横展開**（`frontend/src/pages/inventory/InventoryPage.tsx` と `InventoryToolbar`）。PO 指示「完成したらアプリの在庫表に横展開」。本便の `tap` と `field-h-tap` はそのまま使える（`field-h-tap` は `SelectControl` にも効く形で書く） |

## 対象 ADR

- **ADR-144**（UI 共通部品の遵守ガバナンス）: 既存金型に**値を1つ足すだけ**で金型新設ではない（§4 の対象外）。
- **ADR-067**（デザイントークン強制）: 追加する CSS の値はすべて既存トークンの参照。新規トークンは
  `--field-h-tap` の1件（大小の段ではなく役割名）。
- **ADR-140**（タップ領域の下限 44px）: 44→48px は下限を上回る方向。
- **ADR-027**（i18n 強制）: 本便は文言を1つも追加・変更しない（便11 で追加する）。
- **ADR-1019**（閲覧ページはアプリと別コード）: 本便はアプリ側に触らない。
