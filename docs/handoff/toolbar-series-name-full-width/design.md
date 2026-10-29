# design: 種別／シリーズの名前が読めるようにする（在庫表と閲覧ページの同時直し）

> この文書は何か（1行）: スマホの上部操作台で、**いま選ばれている種別（閲覧ページではシリーズ）の名前が
> ほとんど表示されない**不具合を直す。種別のボタンに**1行を独り占め**させる。
> **在庫表（/inventory）と閲覧ページ（/viewer/）の両方に同じものを入れる**。

**前の便**: docs/handoff/inventory-series-sort-panel/design.md（便2・PR #4848）の ⑩ で
「上の段の種別のボタンは幅が狭い（約54px）ので、長い種別名は…で切れる。閲覧ページと同じ挙動」と
**承知のうえで通した項目**。本番の実機で見たところ想定より深刻だったため、PO 決定でやり直す。
**閲覧ページ側の宿題 J2（シリーズ名の幅・PO 判断待ち）と同一の問題**で、本便で両方を決着させる。

**PO 指示（2026-10-29）**: 「閲覧用と同じにしてくれ」→ 実測の結果、閲覧ページも同じ欠陥を持つことが
判明したため、**1つの形を決めて両ページに同じものを入れる**ことを提案し、**案2（種別が1行を独り占め）を PO が選択**。
文言は「詳細フィルタ」のまま（閲覧用の「絞り込み」には合わせない）。

## ① 区分：A（見た目と置き場所の変更）

変えるのは **CSS の `flex` の指定1か所 × 2ファイル**だけ。データの読み書き・絞り込み・並び替え・
API への問い合わせ・文言・DOM の構造は**一切変えない**。**PC は1px も動かさない**。

## ② KGI（PO が実機で○×を判定できる粒度）

| # | PO が見て○×を言えること |
|---|---|
| L1 | 在庫表のスマホで、**いま選ばれている種別の名前が最後まで読める**（例「マジック：ザ・ギャザリング」が全部出る） |
| L2 | **並び替えで「価格が安い順」などを選んでも、種別の名前が消えない** |
| L3 | 種別のボタンは**1行を独り占め**していて、その下の行に「並び替え」と「詳細フィルタ (n)」が並ぶ |
| L4 | **並び替えのボタンの文字も切れない** |
| L5 | 閲覧ページ（/viewer/）のスマホでも **L1〜L4 と同じ**になっている（シリーズ名） |
| L6 | 押したときの動き（パネルが右から出て、選ぶと即反映して閉じる）は**今までどおり** |
| L7 | **PC は何も変わらない**（在庫表・閲覧ページとも） |

## ③ KPI（機械で測る値）

本番の実機（幅360・dpr3・`app.salesanchor.jp/inventory`）で Chrome DevTools から直読みした値。
「使える幅」＝ `.inventory-toolbar__label` の `clientWidth`、「必要な幅」＝ 同 `scrollWidth`。

| # | 値 | いま（本番実機） | この便の後 | 出どころ |
|---|---|---|---|---|
| Q1 | 種別の名前に使える幅（ポケモン） | **13px**（必要52px） | **必要な幅以上**（切れない） | 本番実機 |
| Q2 | 同（マジック：ザ・ギャザリング） | **13px**（必要168px） | **必要な幅以上** | 本番実機 |
| Q3 | 同（並び替えが「価格が安い順」のとき） | **0px** | **必要な幅以上** | 本番実機 |
| Q4 | 並び替えの名前に使える幅 | 足りている | **足りたまま** | 本番実機 |
| Q5 | 操作台 `.inventory-toolbar` の高さ | 108px | **168px**（3段） | 本番実機で案2を当てて実測 |
| Q6 | 操作台の子の右端の最大値 | 336px | **画面幅以下のまま** | 本番実機 |
| Q7 | 横スクロールの超過（document / `.mobile-content`） | 0 | **0のまま** | 本番実機 |
| Q8 | PC（幅1280）の見た目 | 現状 | **変わらない** | PO 決定（PC 不変） |

### 実機で測った3案（なぜ案2なのか）

同じ端末・同じページで、CSS を差し替えて実測した。「全部出る」＝名前が省略記号で詰められていない。

| 形 | 種別の文字 | 並び替えの文字 | 段数・高さ |
|---|---|---|---|
| いまの本番 | 13px ✗ | 全部出る | 2段 108px |
| 文言だけ閲覧用（「絞り込み (1)」）にする | 38px ✗ | 全部出る | 2段 108px |
| 案1 種別も並び替えも縮む側にする（閲覧ページの既存案 J2） | 45px ✗ | 45px ✗ | 2段 108px |
| **案2 種別が1行を独り占め（採用）** | **全部出る（168pxでも）** | **全部出る** | 3段 168px |
| 案3 種別を優先し並び替えが縮む | 全部出る | 32〜38px ✗ | 長い名前だと結局3段 |

**切れないのは案2だけ**。「閲覧用と文言を揃える」だけでは 38px にしかならず、
いちばん短い「ポケモン」（52px）すら入らない。

### いまの幅の内訳（なぜ 13px しか残らないのか）

2段目の内側は **312px**。並び替え **101.7px** ＋ 詳細フィルタ (1) **123.8px** ＋ すき間 **24px** で
**残りは 62.5px**。種別だけ `flex: 1 1 0; min-width: 0` なので**残り物の幅に押し込まれる**。
62.5px から 左右の余白24px・山形16px・すき間8px を引くと、文字に残るのが **13px**。

## ④ 設計（How）

### 4-1. 直すのは CSS の1行 × 2ファイル

**在庫表** `frontend/src/pages/inventory/InventoryToolbar.css`

```css
/* いま */
.inventory-toolbar > .inventory-toolbar__series {
  flex: 1 1 0;      /* ← 残り物の幅しかもらえない */
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
/* これから */
.inventory-toolbar > .inventory-toolbar__series {
  flex: 1 1 100%;             /* ← 検索欄と同じ。1行を独り占めし、残りが次の行へ回る */
  justify-content: flex-start; /* ← 審査 M1。足さないと名前が行の中央に浮く（実機で確認） */
  min-width: 0;
  overflow: hidden;
  white-space: nowrap;
}
```

**`justify-content: flex-start` が要る理由（実機で測った）**: `.comp-btn` は
`justify-content: center`（`frontend/src/components/Button.css`）。ボタンが312pxになると
中身が中央に寄り、名前の左端が **x=142.2** になる（下の行の「並び替え」の文字は x=37）。
`flex-start` を足すと **x=37** で、**下の行のボタンの文字とぴったり同じ左端**に揃う。

**`text-overflow: ellipsis` は `__series` からは落とす**（審査 M6）。ボタンは flex の箱で
直下にテキストが無いため、この指定は**効いていない**。実際に … を出しているのは
`.inventory-toolbar__label` 側の同じ指定で、そちらは残す。

**閲覧ページ** `frontend/src/pages/viewer/viewer.css` の `.viewer-toolbar > .viewer-toolbar__series` も
**同じ値**にする（ADR-1019 の Why「片方だけ直って見え方がずれることを防ぐ」）。

`overflow: hidden` は残す。312px に収まらないほど長い名前（約19文字以上）が将来現れたときに、
はみ出さず … で切るための歯止め（… を出すのは `.inventory-toolbar__label` 側）。

### 4-2. なぜ「1行を独り占め」で3段になるのか

`.inventory-toolbar` は `flex-wrap: wrap` の1枚の箱。`flex-basis: 100%` の子は1行を使い切るので、
**後ろの子は自然に次の行へ回る**（検索欄がすでにこの作りで、便1 から本番で動いている）。
段を2つに分けたり、`@media` を足したりしない。

結果の並び:

```
┌──────────────────────────┐
│ 商品名・型番で検索            │  ← flex: 1 1 100%
└──────────────────────────┘
 マジック：ザ・ギャザリング ⌄        ← flex: 1 1 100% ＋ justify-content: flex-start
 並び替え ⌄      詳細フィルタ (1)   ← flex: 0 0 auto
```

文字の左端は3段とも同じ（実機で x=37）。

### 4-3. 触らないもの（境界）

- `frontend/src/components/` 配下すべて（金型は不変）
- JSX（`InventoryToolbar.tsx` / `InventoryView.tsx`）・文言（`ja.json` / `en.json`）・`data-testid`
- 絞り込みと並び替えの計算・API への問い合わせ・パネルの開閉の作り
- PC 分岐（`ContentToolbar` 側）

## ⑤ Acceptance Criteria（検査で測る）

**CI の持ち時間の予算**（審査 M5）: 画面検査は**1ジョブ・10分**で、`npm ci` と Playwright の導入を含む。
いまの収集件数は **789件**（`npx playwright test --list` を3つの project で数えた実測）。
便1 の時点が655件・7.4分だったので、789件はおよそ **8.9分**。**足せるのは20実行程度**。
本便は**新規5宣言（×3 project ＝ 15実行）に抑え、閲覧ページ側は既存の検査の書き換えで賄う**。

### 5-1. 新設する判定（在庫表・5宣言／すべて幅360のみ）

**既存の検査では永久に捕まらない**。便0・便2 の検査（画面外に出ていないか／段の高さ／横スクロール）は、
文字が 13px に潰れていた状態でも**全部緑**だった。`scrollWidth > clientWidth` を直接見る判定を新設する。
追加先は `frontend/tests-e2e/visual-language/inventory-series-sort-panel.spec.ts`。

| # | 測ること |
|---|---|
| F1 | `inventory-tab-select` の中の `.inventory-toolbar__label` が**切れていない**（`scrollWidth <= clientWidth`） |
| F2 | 同じラベルの**使える幅が 240px 以上**（将来また押し潰されたら赤。**mock は変えない**＝審査 B3） |
| F3 | **並び替えに「価格が安い順」を選んだ状態**でも F1 が成り立つ（本番実機で 0px になった状態の再現） |
| F4 | 種別のボタンが**1行を独り占め**している（`inventory-tab-select` の y が `inventory-sort-menu` の y と**異なる**／ボタンの幅が `.inventory-toolbar` の `clientWidth` と等しい）。あわせて**ラベルの左端が「並び替え」のラベルの左端と同じ**（審査 M1 の中央寄せの退行を捕まえる） |
| F5 | **空振り防止**: `page.addStyleTag` で `.inventory-toolbar > .inventory-toolbar__series { flex: 1 1 0 !important; }` を当てると F1 が**赤になる**ことを同じブラウザで確かめる（`!important` が要る＝審査 M8。先例 `frontend/tests-e2e/visual-language/viewer-control-tap-size.spec.ts` の B7c） |

**測る対象は `inventory-tab-select` の配下に限定する**。`.inventory-toolbar__label` は並び替え側にもあり、
そちらは `flex: 0 0 auto` で**構造上絶対に切れない**ので、`.first()` で取ると常に緑の空振りになる。
**並び替え側のラベルを測る判定は置かない**（審査 M2）。

### 5-2. 閲覧ページ側は「既存の検査の書き換え」で賄う（新規0宣言）

`frontend/tests-e2e/visual-language/viewer-control-tap-size.spec.ts` の **B7c・B7d** は
「壊した状態を作って**切れることを検出できる**」ことを示す検査だが、
**シリーズが1行を独り占めすると使える幅が約262pxになり、文字を16pxにしても山形を24pxにしても切れない**
＝ `expect(scrollWidth).toBeGreaterThan(clientWidth)` が**逆向きに赤になる**（審査 B2）。

→ **壊し方を「`flex` を `1 1 0` に戻す」に差し替える**。これで閲覧ページ側にも
F5 と同じ空振り防止が手に入り、**宣言を1本も増やさずに済む**。
既存の **B7a**（シリーズ名が切れていないこと・`viewer-control-tap-size.spec.ts`）が
そのまま閲覧ページ側の F1 相当になる。

### 5-3. 段が増えることで**必ず赤になる既存の検査**（本便で同時に直す）

実際にファイルを読んで確認した一覧。**判定の中身ではなく前提（2段であること）が変わるため赤になる**。

| ファイル:行 | 判定 | いま | 本便での更新 |
|---|---|---|---|
| `frontend/tests-e2e/visual-language/inventory-series-sort-panel.spec.ts:29` | `MAX_TOOLBAR_HEIGHT` | 120 | **180**（実機実測168＋余裕12。便1 が108に対し120を置いたのと同じ取り方） |
| 同 `:258`（E11） | 題「3行に折り返していないこと」 | — | **「4行に折り返していないこと」**に改める |
| `frontend/tests-e2e/visual-language/inventory-toolbar-mercari.spec.ts:40` | `MAX_TOOLBAR_HEIGHT` | 120 | **180** |
| 同 `:195`（D10） | 同上 | — | 同上 |
| `frontend/tests-e2e/visual-language/viewer-top-compact.spec.ts:35` | `MAX_TOP_Y` | 132 | **204**（下の計算） |
| 同 `:96`（A1） | 先頭カードの y | — | 定数の更新で足りる |
| 同 `:102-134`（A2・A3・A4、y の比較は `:121-122`） | **「シリーズ・並び替え・絞り込みが1行に並び」** | — | **シリーズは単独の行**（`not.toBe`）・並び替えと絞り込みは同じ行、に書き換える。題も直す |
| `frontend/tests-e2e/visual-language/viewer-choice-sheet.spec.ts:31` | `MAX_TOP_Y` | 132 | **204** |
| 同 `:334`（B11） | 先頭カードの y | — | 定数の更新で足りる |
| 同 `:160-196`（B1・B2・B3、y の比較は `:185-186`） | **「3つのボタンが枠なしで1行に並び」** | — | 同上の書き換え |
| `frontend/tests-e2e/visual-language/viewer-header-remove.spec.ts:26` | `MAX_TOP_Y` | 132 | **204** |
| 同 `:63`（C1） | 題「128px以内」 | — | 題の数値を直す |
| **`frontend/tests-e2e/visual-language/viewer-control-tap-size.spec.ts:197-198`（B8）** | **`seriesBox.y === sortBox.y`** | — | **審査 B1。設計の初版はこのファイルを「安全」と誤判定していた**。シリーズは単独行に書き換える（幅360・390の2幅で走るので6実行） |
| 同 `:216-240`（B7c・B7d） | 「切れること」を期待 | — | **審査 B2。上の 5-2 のとおり壊し方を差し替える** |

**高さの上限の決め方**（審査 M4 で検算）: `--space-3: 12px`・`--comp-btn-height-lg: 48px`。
- 在庫表: いま 48+12+48 = **108**（実機実測と一致）→ 上限120（余裕+12）。本便 48+12+48+12+48 = **168**（実機実測と一致）→ 上限 **180**（余裕+12）。
- 閲覧ページ: いまの132 は `margin 12 +(48+12+48)+ margin 12` の**計算値ちょうどで余裕0**。
  1段増えて 12+168+12 = 192。**在庫表と同じ+12の余裕を取って 204** にする
  （この端末では Playwright が動かず手元で測れないため、1px の端数で赤にしない）。

**赤にならないと確認したもの**（審査が1件ずつ根拠を確認）: `viewer-filter-panel-mercari.spec.ts`／
`viewer-inventory-mobile-filter.spec.ts`／`inventory-mobile-baseline.spec.ts`（`console.log` が主体）／
`popover-mold.spec.ts`／`horizontal-overflow.spec.ts`／`inventory-table-layout.spec.ts`／
`inventory-raw-text-mobile.spec.ts`／`drawer-inert-closed.spec.ts`／`viewer-focus-trap.spec.ts`／
単体テスト（jsdom は寸法を持たない）。`visual-language/` に画面写真の比較（`toHaveScreenshot`）は**0件**。

## ⑥ 触るファイル

| ファイル | 変更 |
|---|---|
| `frontend/src/pages/inventory/InventoryToolbar.css` | `.inventory-toolbar__series` を `flex: 1 1 100%` ＋ `justify-content: flex-start` に。`text-overflow` を落とす |
| `frontend/src/pages/viewer/viewer.css` | `.viewer-toolbar__series` に同じ変更 |
| `frontend/tests-e2e/visual-language/inventory-series-sort-panel.spec.ts` | `MAX_TOOLBAR_HEIGHT` を180へ・E11 の題・**F1〜F5 を追加** |
| `frontend/tests-e2e/visual-language/inventory-toolbar-mercari.spec.ts` | `MAX_TOOLBAR_HEIGHT` を180へ・D10 の題 |
| `frontend/tests-e2e/visual-language/viewer-top-compact.spec.ts` | `MAX_TOP_Y` を204へ・A2〜A4 を新しい段の形に |
| `frontend/tests-e2e/visual-language/viewer-choice-sheet.spec.ts` | `MAX_TOP_Y` を204へ・B1〜B3 を新しい段の形に |
| `frontend/tests-e2e/visual-language/viewer-header-remove.spec.ts` | `MAX_TOP_Y` を204へ・C1 の題 |
| `frontend/tests-e2e/visual-language/viewer-control-tap-size.spec.ts` | **B8 を新しい段の形に**・**B7c/B7d の壊し方を `flex: 1 1 0` に差し替え** |
| `docs/handoff/toolbar-series-name-full-width/design.md` ／ 同 `review-opus.md` | 本書類 |

**mock（`inventory-helpers.ts` / `viewer-helpers.ts`）は1行も変えない**。
種別を1件足すと `inventory-series-sort-panel.spec.ts:107` の `toHaveCount(4)` が赤になり、
`InventoryPage.tsx` が PC に「その他」のプルダウンを増やすので **PC の DOM まで変わる**（審査 B3）。

## ⑦ 戻し方

PR をそのまま revert すれば元に戻る。新しいトークンも新しい文言も足さない。

## ⑨ 外部・過去事例の参照と我々への応用

| 参照 | 我々への応用 |
|---|---|
| **便1（PR #4842）の検索欄** | `flex: 1 1 100%` で1行を独り占めする形が本番で動いている。同じ手を種別にも使う＝新しい仕掛けを作らない |
| **便2（PR #4848）の ⑩** | 「長い種別名は…で切れる」を承知で通した。**実機で見たら想定（約54px）より狭い13pxだった**＝机上の見積もりでは足りず、実機で測って初めて判る |
| **閲覧ページの宿題 J2** | 「並び替えも縮む側にして両方を途中で切る」案が残っていた。**実機で測ったら両方切れる**ので不採用にできた |
| **ADR-1019 の Why**「片方だけ直って見え方がずれることを防げる」 | だから在庫表と閲覧ページを**同じ PR で同時に**直す |
| **便13a の「既存検査が前提にしている段取りも数える」教訓** | 高さの上限を固定している既存 spec（`MAX_TOP_Y` など）は、段が増えると**判定の中身と関係なく赤になる**。先に洗い出して同時に更新する |

## ⑩ 弊害・トレードオフ

- **操作台が1段ぶん高くなる**（在庫表で 108px → 168px）。一覧の先頭カードがその分だけ下がり、
  **1画面に見えるカードが減る**。PO は実測値（108→168）を見たうえで案2を選択（2026-10-29）。
- 閲覧ページでも同じだけ高くなる。**便4 で 128→132 と詰めた上端の値を、本便で引き上げ直す**ことになる。
- 幅の広い端末（390px 以上）でも**常に3段**になる。幅に応じて2段に戻す仕掛けは入れない
  （`@media` を増やすと「段を2つ作らない」という便1 の方針に反し、端末ごとに形が変わって検証が増える）。
- 312px を超える名前（約19文字以上）が将来現れたら、やはり … で切れる（`.inventory-toolbar__label` 側の歯止め）。
- **押したときの灰色の跡が行いっぱい（312px）に広がる**（審査 M7）。`.comp-btn` の `:hover` は
  `@media (hover: hover)` で囲まれていないため、スマホでタップした後に色が残る。
  いままでも同じ不具合だったが**幅が62px→312pxになるので目立つ**。本便の範囲外として ⑫ に起票する。

## ⑪ 維持の仕組み

守り手: `frontend/tests-e2e/visual-language/inventory-series-sort-panel.spec.ts`（F1〜F5）と
`frontend/tests-e2e/visual-language/viewer-control-tap-size.spec.ts`（B7a＝切れていないこと／
B7c・B7d＝空振り防止）。CI の画面検査で毎回走る。

- **`scrollWidth > clientWidth` で測る**。「画面外に出ていないか」「段の高さ」だけでは
  **この不具合は永久に捕まらない**（便0・便2 の検査は全部緑のまま 13px になっていた）。
- 測る対象を **`inventory-tab-select` / `viewer-tab-select` の配下に限定する**。
  `.inventory-toolbar__label` は並び替え側にもあり、そちらは切れないので
  **`.first()` で取ると常に緑の空振りになる**（閲覧ページ便10 の教訓）。
- 空振り防止: CSS を元の `flex: 1 1 0` に戻した状態を spec の中で作り、**判定が赤になること**を確かめる
  （在庫表 F5・閲覧ページ B7c/B7d）。`!important` を付けないと `.inventory-toolbar > .inventory-toolbar__series`
  （詳細度 0,2,0）に負ける。
- F4 で**ラベルの左端が揃っていること**も測る＝ `justify-content: flex-start` を誰かが外したら赤になる。

## ⑫ 継続（この便の後）

| # | 内容 |
|---|---|
| **便3（③）** | 在庫表の詳細フィルタを右から出るパネルにし、中を「項目を押す→次の画面で選ぶ」形に |
| **便4（④）** | 在庫表の検索を「押すと検索画面が開く」形に |
| M1 | 閲覧ページの `.viewer-choice-row:hover` が `@media (hover: hover)` で囲まれていない（便2 で起票ずみ） |
| M2 | **`frontend/src/components/Button.css` の `:hover` が `@media (hover: hover)` で囲まれていない**（審査 M7）。スマホでタップした跡が残る。金型なので影響範囲が広く、単独の便で扱う |
| M3 | 閲覧ページの fixture（`viewer-helpers.ts`）のシリーズ名が空または5文字で、**長い名前での検証ができない**（審査 M3）。長い名前の fixture を足す便 |

## 対象 ADR

- **ADR-144**（UI 共通部品の遵守ガバナンス）: 金型の新設も変更もなし。`frontend/src/components/` は0ファイル。
- **ADR-067**（デザイントークン強制）: 色・寸法の直値は足さない。`flex` の数値と `100%` はトークン対象外
  （`.inventory-toolbar__search` / `.viewer-toolbar__search` の先例と同じ）。
- **ADR-140**（タップ領域の下限 44px）: ボタンの高さ48pxは変えない。
- **ADR-1019**（閲覧ページはアプリと別コード）: 本便は**例外的に両方を触る**。
  同 ADR の Why「画面をアプリの在庫表と同じ部品で作れば、片方だけ直って見え方がずれることを防げる」
  （PO 決定 Q14）に沿った、**ずれを作らないための同時変更**。共有部品は作らない。
