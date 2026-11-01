# design: 在庫表（/inventory）スマホの詳細フィルタをパネル＋次の画面に（便3／全4便の3本目）

> この文書は何か（1行）: 在庫表のスマホで「詳細フィルタ」を押したときに出る埋め込みの枠を、閲覧ページと同じ
> 「右から出るパネル → 項目を押すと次の画面で選ぶ」形に作り替える手順書。

**下調べ**: docs/handoff/inventory-filter-subscreen/recon.md（事実と行番号はすべてここ）
**親（全4便の計画）**: docs/handoff/inventory-toolbar-mercari/design.md の ⑫
**直前の便**: docs/handoff/inventory-series-sort-panel/design.md（便2）／
docs/handoff/toolbar-series-name-full-width/design.md（便2.5）
**お手本の設計**: docs/handoff/viewer-filter-subscreen/design.md（閲覧ページ 便2）／
docs/handoff/viewer-filter-choices-mercari/design.md（閲覧ページ 便13a・寸法）

## PO 決定（2026-10-30・本便の前提）

| # | 決めたこと | 本文での扱い |
|---|---|---|
| 1 | **「詳細フィルタ」ボタンの数字（(1) など）は出さない** | 4-8。既存検査 D8 を作り替える |
| 2 | **パネルの幅はお手本と同じ画面の83%**（左に地を残して背景で閉じられる） | 4-3。`Drawer` の `mobileInset` を渡すだけ |
| 3 | **パネルの中の「閉じる」ボタンはスマホでは消す**（✕と背景タップがある） | 4-4 |
| 4 | **在庫表固有の5項目も「押す→次の画面」にする**（1本の便でまとめて） | 4-4・4-5 |
| 5 | **シリーズと列は「隠すものを選ぶ」形にする**（2026-11-01・審査 r1 の H2／M3 を受けた再決定） | 4-4・4-5。行の名前は**「隠すシリーズ」「隠す列」**。既定は選択0件＝「なし」 |
| 6 | **4項目のどれかを選んだら「フィルタを有効化」を自動で入れる**（2026-11-01・審査 r1 の H3 を受けた決定） | 4-5a。選んでも何も起きない状態をなくす |

**決定5 の補足（言葉の向き）**: 「隠すものを選ぶ」形では、行の名前を今のまま「表示する列」にすると
右に出る要約が「表示する列：なし」＝**逆の意味に読めてしまう**。よって行の名前自体を「隠す〜」にする。
PO に示した絵では root の行を「シリーズ／表示する列」と書いていたが、これは誤り（提示時に訂正済み）。

## ① 区分：A（見た目と置き場所の変更）

画面の形だけを変える。API・データ構造・migration・本番 scripts は触らない。
PO GO（`GO #<PR番号>`）を受けてからマージする。

**1つだけ挙動が変わる**: PO 決定6 の自動の有効化（4-5a）。保存される値（`enabled`）が利用者の操作で
入ることがある。保存の形・API・移行は変えない。PC の挙動は変えない。

## ② KGI（PO が実機で○×を判定できる粒度）

幅360のスマホ（本番 app.salesanchor.jp/inventory）で測る。

| # | ○の条件 |
|---|---|
| G1 | 「詳細フィルタ」を押すと**右からパネルが出る**。パネルは画面いっぱいではなく**左に地が残り**、その地を押すと閉じる |
| G2 | パネルの中に**12個**が縦に並ぶ: 24時間以内／注記／提供者＞／コンディション＞／価格の範囲／数量の範囲／フィルタを有効化／**隠すシリーズ＞／隠す列＞**／形態＞／在庫・予約＞／リセット。**「閉じる」ボタンは無い**（✕と背景タップで閉じる） |
| G3 | 「＞」が付いた6つの行を押すと**画面が入れ替わり、左上に「←」が出る**。選び終えて下の「決定する」か「←」を押すと元の画面に戻り、**選んだ名前が行の右**に出る |
| G4 | 6つの行で選んだ内容が一覧に効く。24時間以内・価格・数量・有効化も今までどおり効く＝**機能が1つも減っていない**。**シリーズ・列・形態・在庫予約を選ぶと「フィルタを有効化」が自動で入る**（PO 決定6。今までは有効化を入れない限りこの4項目は効かなかった） |
| G5 | ボタンの文字は**常に「詳細フィルタ」**で、`(1)` のような数字は出ない |
| G6 | パネルを開いても**横スクロールは出ず**、画面の外にはみ出す操作が**0個** |
| G8 | **「隠すシリーズ」「隠す列」の行の右の文字が読める**（既定は「なし」。隠すと隠したものの名前が出る）。候補に出ていないシリーズの隠し設定が**勝手に解除されない** |
| G9 | パネルを**閉じる途中でパネルの中身が空っぽに見えない** |
| G7 | PC（幅1280）は**1pxも変わらない**（今の埋め込み枠のまま・右から出るパネルは出ない） |

## ③ KPI（機械で測る値・CI の画面検査）

| # | 測る値 | 合格 | 根拠 |
|---|---|---|---|
| P1 | パネルの幅と左端 | 幅 = 画面の83%±1px（360なら298.8）・左端 x = 17%±1px（61.2） | frontend/src/tokens.css:445（`--drawer-panel-w-mobile-inset: 83%`） |
| P2 | root の押せる行の高さ | 44px 以上（`.comp-multiselect__row` は53px） | frontend/src/tokens.css:577 |
| P3 | 次の画面の選択行の高さ | 61px 以上 | frontend/src/tokens.css:174（`--comp-multiselect-check-row-h: 61px`） |
| P4 | 横の超過 | `document` / `.mobile-content` / パネル本体すべて 0 | 便0 からの型 |
| P5 | ボタンの文字 | 「詳細フィルタ」と完全一致（数字を含む形が出ない） | PO 決定1 |
| P6 | PC 不変 | 幅1280で `.content-toolbar` あり・`inventory-filter-panel` が `section`・右から出るパネルは増えない | 便1 D12／便2 E14 と同じ型 |
| P7 | 戻ったときの選択 | 「←」で root に戻っても選んだ値が残る | お手本 A11 |
| P8 | フォーカス | root→次の画面で「←」へ、戻ると押した行へ | お手本 A14 |
| P9 | 閉じているときの注記 | パネルを開いていない間、`inventory-expiry-warning` は0件 | 既存 E1 を壊さないため |
| P10 | 自動の有効化 | 4項目のどれかを選ぶと `inventory-filter-enabled` が入になり、問い合わせに該当の語が乗る | PO 決定6（審査 H3） |
| P11 | 候補の外の保存値 | 候補に無い隠し設定を持った状態で1項目を選んでも、`PATCH` の本文からその値が消えない | 審査 H2 |

## ④ 設計（How）

### 4-1. スマホ専用の部品を**新設**する（ページの行数上限の回避）

`frontend/src/pages/inventory/InventoryPage.tsx` は **723行**で、上限は **800行**
（frontend/scripts/check-page-size.js:19-20）。次の画面の仕組み（6本の選択画面・候補を絞る欄・
フォーカス移動）をページに直接書くと上限に当たる。よって:

- 新設 **`frontend/src/pages/inventory/InventoryFilterDrawer.tsx`**（スマホ専用）。
- 新設 **`frontend/src/pages/inventory/InventoryFilterDrawer.css`**。
- **持つ状態は画面の見せ方だけ**（`view` と `optionQuery`）。絞り込みの値は今までどおり親が持ち、props で受ける
  （`InventoryFilterPanel` と同じ「表示専用」の約束を守る。frontend/src/pages/inventory/InventoryFilterPanel.tsx:1-10）。

```
type FilterView = "root" | "supplier" | "condition" | "category" | "columns" | "unit" | "offerType";
```

`open` が false → true になった回は **必ず `view` を root に戻す**（お手本
frontend/src/pages/viewer/InventoryView.tsx:201-205 と同じ。開き直したら最初の画面から）。

### 4-2. ページ側の差し替えは「スマホか PC か」の1分岐だけ

```
{isMobile
  ? <InventoryFilterDrawer open={showFilterPanel} onClose={…} {...filterPanelProps} />
  : showFilterPanel && <InventoryFilterPanel {...filterPanelProps} />}
```

- **props は1つのオブジェクト（`filterPanelProps`）にまとめてから渡す**。同じ30行の props を2回書くと
  ページが約40行増えて上限に近づくため（4-1）。
- **両方を同時にマウントしない**。同じ目印（`inventory-fresh-check` など）が2枚出ると
  spec が strict mode で曖昧になり落ちる。
- `InventoryFilterPanel` から**スマホ専用の枝を削る**（`showSupplierSelect` と `notice` の props ごと）。
  削る対象は recon.md §1 の表の 1〜6・12（24時間以内・注記・提供者・コンディション・価格・数量・リセット）。
  **PC ではこの枝は一度も走らない**（`showSupplierSelect={isMobile}`）ので PC の見た目は変わらない。
  歯止めは P6（PC 不変）。

### 4-3. `Drawer` への渡し方（共通部品は1文字も触らない）

| 渡すもの | 値 | 効果 |
|---|---|---|
| `mobileInset` | 常に真 | 画面の83%幅・左に地（PO 決定2） |
| `title` | `t("inventory.filterPanel.button")`（＝「詳細フィルタ」） | 題 |
| `onClose` | 親の `setShowFilterPanel(false)` | ✕ と背景タップで閉じる |
| `onEscape` | `view === "root"` なら渡さない／そうでなければ root に戻す | Esc は「1つ戻る」（お手本 A12） |
| `onBack` + `backLabel` | `view !== "root"` のときだけ**1つのオブジェクトにまとめて spread する** | 「←」（frontend/src/components/Drawer.tsx:51-53 の union は `{onBack; backLabel}` か「両方 undefined」のどちらかしか認めない。**別々の props に `cond ? x : undefined` と書くと tsc が赤**＝審査 M5。お手本 frontend/src/pages/viewer/InventoryView.tsx:365 で `const filterDrawerBackProps = …` を作り 同:790 で `{...filterDrawerBackProps}` と渡しているので、同じ形にする） |
| `footer` | `view !== "root"` のときだけ「決定する」 | 押すと root に戻る（選択は残る） |

**中身の描き方（審査 H5 で初版を撤回）**。初版は「中身は `open` のときだけ描く（`{open && …}`）」としていたが、
これは**誤り**。`Drawer` は閉じても中身を DOM に残す作り（frontend/src/components/Drawer.tsx の「DOM は常にマウント」）で、
かつ frontend/src/components/Drawer.css:38-45 が `transform` の `transition` で**スライドアウトする**ため、
`open` で中身ごと消すと**閉じている0.3秒間パネルが空っぽに見える**。お手本もこれを避けており、
frontend/src/pages/viewer/InventoryView.tsx:197-198 に「閉じるときに戻さないのは、スライドアウト中に題と中身が
切り替わって見えるのを避けるため」と明記がある。

よって**中身は常に描く**。既存の E1（閉じている間 `inventory-expiry-warning` が0件＝
frontend/tests-e2e/visual-language/inventory-series-sort-panel.spec.ts:74-77）を守るのは
**注記の1行だけを `open` で出し分ける**ことで足りる（`{open && <p data-testid="inventory-expiry-warning">…}`）。
`view` を root に戻すのも**開く瞬間に行う**（閉じる時ではない。お手本 同:196-205。
閉じた後にタイマーで戻す形は CI で6件赤になった実例が同コメントに記録されている）。

### 4-4. root（最初の画面）の中身

上から順に。**「押す→次の画面」にするのは「＞」の6つ**。

| # | 項目 | 形 | 目印 |
|---|---|---|---|
| 1 | 24時間以内 | その場のチェック（今のまま） | `inventory-fresh-check` |
| 2 | 注記（※…） | 文（今のまま・折り返す） | `inventory-expiry-warning` |
| 3 | 提供者 | **行＞** | `inventory-supplier-filter-row` |
| 4 | コンディション | **行＞** | `inventory-condition-filter-row` |
| 5 | 価格の範囲 | その場の入力2つ（今のまま） | `inventory-price-min` / `-max` |
| 6 | 数量の範囲 | その場の入力2つ（今のまま） | `inventory-qty-min` / `-max` |
| 7 | フィルタを有効化 | **その場のチェック**（下の割り切り。PO 決定6 で自動でも入る＝4-5a） | `inventory-filter-enabled` |
| 8 | **隠すシリーズ**（PO 決定5） | **行＞** | `inventory-category-filter-row` |
| 9 | **隠す列**（PO 決定5） | **行＞** | `inventory-columns-filter-row` |
| 10 | 形態 | **行＞** | `inventory-unit-filter-row` |
| 11 | 在庫・予約 | **行＞** | `inventory-offertype-filter-row` |
| 12 | リセット | ボタン（今のまま） | `inventory-reset-in-panel` |
| — | （参考）リセットが戻すもの | 検索語・カテゴリー・並び替え・ページ**だけ**。**詳細フィルタの値は1つも戻さない**（frontend/src/pages/inventory/InventoryPage.tsx:386-392 の「意図的に保持」。審査 M8）。パネルの中で絞り込みの行の下にリセットが並ぶため、PO に明示する | — |
| — | 閉じる | **置かない**（PO 決定3） | — |

**1件だけ割り切り（PO に明示する）**: 項目7「フィルタを有効化」は**入／切の2択**なので、
次の画面にすると**入切のたびに2タップ増える**。お手本も真偽の項目（24時間以内）は
その場のチェックのままにしている（frontend/src/pages/viewer/viewer.css:99-115 の `.viewer-fresh-check`）。
よって**7だけはその場のチェック行**とし、残りの4項目（8〜11）は指示どおり次の画面にする。
PO が「7も次の画面に」と判断した場合は、同じ `MultiSelect layout="row"` の形で後から足せる（約10行）。

目印は**既存の名前を据え置く**（1・2・5・6・12）。新しく付ける6つの行の目印は
`MultiSelect` が自動で付ける `<testId>-row` 形式（frontend/src/components/MultiSelect.tsx:124-137）に従う。

### 4-5. 「隠す側／出す側」の向きを合わせる（**設定を壊さない肝**／審査 H2・PO 決定5）

`MultiSelect` は「選んだものの配列」を扱うが、在庫表の状態は項目ごとに向きが違う（recon.md §1）。

**初版の「全件 − 隠した集合」を渡す案は撤回する（審査 H2）**。理由は実害が出るため:
候補の一覧 `sortedCategories` は **API の結果から作られる facet**
（frontend/src/pages/inventory/InventoryPage.tsx:180 が `categoryFacet` を並べ替えるだけ・
`categoryFacet` の代入は 同:263 の `if (d.categories) setCategoryFacet(d.categories)`）。
いま候補に出ていないシリーズ（＝その時の結果に1行も無いシリーズ）を利用者が過去に隠していた場合、
「全件 − 隠した集合」→「`hiddenCategories` = 全件 − next」と計算すると**その隠し設定が消え**、
さらに 同:375 の `PATCH /me/inventory-filters` が**消えた状態をサーバに保存してしまう**（保存は自動・250ms）。
いまの画面はシリーズごとに1つずつ入切する作り（frontend/src/pages/inventory/InventoryFilterPanel.tsx:215 の
`sortedCategories.map` ＋ `checked={!hiddenCategories.has(c)}`）なので、この事故は起きていない。

**PO 決定5 の形（隠すものを選ぶ）で、かつ候補の外を必ず保つ**:

| 項目 | いまの状態 | `selected` に渡す値 | `onChange(next)` でやること |
|---|---|---|---|
| 隠すシリーズ | 隠した集合 `hiddenCategories` | **`候補 ∩ hiddenCategories`**（＝候補に出ているうち隠しているもの） | `hiddenCategories = (hiddenCategories − 候補) ∪ next`／`setPage(1)`／4-5a |
| 隠す列 | 隠した集合 `hiddenColumns` | **`HIDEABLE_COLUMNS ∩ hiddenColumns`** | `hiddenColumns = (hiddenColumns − HIDEABLE_COLUMNS) ∪ next`／**`setPage(1)` しない**（列は件数を変えない。frontend/src/pages/inventory/InventoryPage.tsx:505-512 の今の挙動に合わせる）／4-5a |
| 形態 | 出す集合 `showUnits` | `Array.from(showUnits)` | `setShowUnits(new Set(next))`／`setPage(1)`／4-5a |
| 在庫・予約 | 出す集合 `showOfferTypes` | `Array.from(showOfferTypes)` | `setShowOfferTypes(new Set(next))`／`setPage(1)`／4-5a |
| 提供者 | 出す配列 | そのまま | 今の `onSupplierChange`（frontend/src/pages/inventory/InventoryPage.tsx:478-481） |
| コンディション | 出す集合 | `Array.from(showConditions)` | 今の `onConditionChange`（同:482-485） |

- **`(いまの集合 − 候補) ∪ next` の形を必ず使う**。候補の外にある保存値をそのまま持ち越すための式で、
  これが H2 の歯止め。列は定数7件（同:106-108 の `HIDEABLE_COLUMNS`）なので候補の外は通常できないが、
  **同じ式で書く**（将来列が増減したときに事故らせない）。
- 既定（何も隠していない）は `selected` が**0件**＝`MultiSelect` が `allLabel` を出す
  （frontend/src/components/MultiSelect.tsx:82）。`allLabel` は「**なし**」にする（4-8）。
  初版の案（表示する側を渡す）だと既定で全件の名前が行の右に並び、幅が足りず「…」しか読めなかった（審査 M3）。
- **サーバへの保存形は触らない**。隠した側を送る形（同:93-94）のまま。
- 変換は**親（`InventoryPage`）側に小さな関数として置く**（表示部品に業務の向きを持たせない）。
- 「空っぽ＝全件」の意味（形態・在庫・予約）は変わらない。

### 4-5a. 4項目を選んだら「フィルタを有効化」を自動で入れる（PO 決定6／審査 H3）

**現状の事実**: シリーズ・列・形態・在庫予約の4項目は、`filterEnabled` が切のとき**一覧に1つも効かない**。
- frontend/src/pages/inventory/InventoryPage.tsx:239-241 `if (filterEnabled && hiddenCategories.size > 0) params.set("hide_categories", …)`
- 同:245-246 `if (filterEnabled && showUnits.size > 0) …` / `if (filterEnabled && showOfferTypes.size > 0) …`
- 同:181-184 `colVisible = (c) => !filterEnabled || !hiddenColumns.has(c)`
- `filterEnabled` の初期値は切（同:140 `useState(false)`）。提供者とコンディションは有効化に関係なく常に効く（同:243-244 のコメント）。

**やること**: 上の4項目の `onChange` で**値が空でなくなる向きの変更があったときに `setFilterEnabled(true)` を呼ぶ**。
- 「空にする向き」（選択を全部外す）では**触らない**。入れっぱなしにしても害はないが、
  利用者が自分で切ったつもりの状態を勝手に入れ直さないため。
- `filterEnabled` は保存対象（同:382 の依存配列）なので、**自動で入れた値もサーバに保存される**。これは意図どおり
  （次に開いたときも選んだ絞り込みが効く）。⑩ に弊害として書く。
- **PC も同じ関数を通る場合がある**: PC の `InventoryFilterPanel` は別の `onChange` を使っているため、
  本便で足す自動有効化は**スマホの新部品から呼ばれる経路だけ**に置く。PC の挙動は変えない（KPI P6）。

### 4-6. 次の画面（6本）の中身

```
<div className="inventory-filter-options">
  {候補が多い項目だけ} <TextFieldControl … data-testid="inventory-filter-option-search" />
  <MultiSelect layout="inline" … />
</div>
```

- **候補を絞る欄を出すのは「提供者」「コンディション」の2つ**（お手本と同じ。
  frontend/src/pages/viewer/InventoryView.tsx:301-355）。
  残り4つ（隠すシリーズ・隠す列・形態・在庫・予約）は、**候補が10件を超えるときだけ**出す。
  列は**定数7件**（frontend/src/pages/inventory/InventoryPage.tsx:106-108 の `HIDEABLE_COLUMNS`。
  審査 M7＝初版の「11件」は誤り）・形態と在庫・予約は数件なので通常は出ない。シリーズが増えたときに自動で出る。
- 絞り込んでも**選択済みの名前が化けない**よう、`allOptions` に全件を渡す
  （frontend/src/components/MultiSelect.tsx:38-40・お手本 A9）。
- **候補が0件のときは `emptyLabel={t("inventory.noResults")}` を渡す**（審査 M4）。
  `MultiSelect` は `options` が空で `emptyLabel` 未指定なら**何も描かない**
  （frontend/src/components/MultiSelect.tsx:93-94）。いまは
  frontend/src/pages/inventory/InventoryFilterPanel.tsx:212-213（シリーズ）と 同:274-275（形態）が
  「該当なし」を出しているので、渡さないと**機能が減る**。
- 注記の置き場所（審査 M9）:
  - `inventory.filterPanel.columnsNote` → **「隠す列」の次の画面の中**。
  - `inventory.filterPanel.displayConditionsNote` は**形態と在庫・予約をまとめて**説明する1文
    （frontend/src/pages/inventory/InventoryFilterPanel.tsx:263-268）。スマホでは「表示条件」という
    括りの見出しが無くなるため、**形態と在庫・予約の両方の画面に同じ文を出す**（各画面が単独で意味を持つように）。
    文を分けたり書き換えたりはしない（文言の変更は本便の範囲外）。
- 「隠す〜」の2画面には、**選んだものが隠れる向き**であることを画面の題で示す（4-8 の `hideCategories` /
  `hideColumns`）。チェックの意味が PC 版と逆になることは ⑩ に弊害として記す。
- 一覧だけパネル全幅にする（`--comp-multiselect-list-bleed`）。4-8 の CSS で指定。

### 4-7. フォーカスの移動（お手本の写し）

`view` が変わったら: root→次の画面は `[data-testid="drawer-back"]` へ、
次の画面→root は**押した行**へ戻す（frontend/src/pages/viewer/InventoryView.tsx:223-240 と同じ形）。
開いた直後は `Drawer` 側の初期フォーカスに任せる。

### 4-8. 文言（ADR-027: ja/en 同一キー）

**初版の「新キー3つ」では足りない（審査 M1）**。`MultiSelect` は `clearLabel` / `allLabel` / `countLabel` を
**省略できない**（frontend/src/components/MultiSelect.tsx:46-51）。既存で揃っているのは
`inventory.supplierFilter.{clear,all,count}` と `inventory.conditionFilter.{clear,all,count}` の2組だけで、
残り4項目（隠すシリーズ・隠す列・形態・在庫予約）には1つも無い。

| キー | ja | 使う所 |
|---|---|---|
| `inventory.filterPanel.back` | 戻る | 「←」の読み上げ名 |
| `inventory.filterPanel.apply` | 決定する | 下のボタン |
| `inventory.filterPanel.searchOptions` | 絞り込む | 候補を絞る欄のプレースホルダ |
| `inventory.filterPanel.hideCategories` | 隠すシリーズ | 行の名前・次の画面の題（PO 決定5） |
| `inventory.filterPanel.hideColumns` | 隠す列 | 行の名前・次の画面の題（PO 決定5） |
| `inventory.filterPanel.hideNote` | 選んだものを一覧から隠します | 「隠す〜」2画面の説明 |
| `inventory.filterPanel.clear` | 選択を消す | `MultiSelect` の `clearLabel`（4項目で使い回す） |
| `inventory.filterPanel.noneSelected` | なし | `MultiSelect` の `allLabel`（**隠す側の2項目だけ**。0件＝何も隠していない） |
| `inventory.filterPanel.count` | {{count}}件選択中 | `MultiSelect` の `countLabel`（4項目で使い回す） |

- 形態・在庫予約の `allLabel` は**既存の `common.all`（「すべて」）**を使う（0件＝全件の意味。4-5）。
- 「形態」「在庫・予約」の行の名前は既存の `inventory.col.unit` / `inventory.filterPanel.displayConditions`
  などを使い、**新しいキーを作らない**。
- ja と en の両方に同じキーを足す（ADR-027）。`check:i18n-missing-keys` が歯止め。

**数字をやめる（PO 決定1）**: `frontend/src/pages/inventory/InventoryToolbar.tsx:236-239` の出し分けを消し、
常に `t("inventory.filterPanel.button")` にする。**これはスマホ専用の `filterButtonMobile` だけの話**で、
PC の `filterButton`（同:168-178）は**元から数字を出していない**ため PC は1pxも変わらない（審査 r1 の確認1）。**辞書のキー `buttonWithCount` は消さない**
（PC・他ページからの参照が無いことを確認してから消す判断は別便。残っていても害はない）。
`filterActiveCount` の計算（frontend/src/pages/inventory/InventoryPage.tsx:487-493）と props も
**使われなくなるので消す**（未使用変数は lint が赤にする）。

### 4-9. 既存検査への手当て（審査 H1・H4 を受けて全面改訂）

#### (1) 目印 `inventory-filter-panel` は**新しいパネルに引き継ぐ**（審査 H1 の対処）

初版は「赤になるのは D8 と F5 だけ」としていたが**誤り**。スマホの画面検査2本が、入れ物の目印
`inventory-filter-panel` を `toBeVisible()` で待つ共通関数を持っている:

- frontend/tests-e2e/visual-language/inventory-toolbar-mercari.spec.ts:87-92 の `openFilterPanel()`
  → これを使う **D6**（同:151）・**D7**（同:159）・**D8**（同:177）
- frontend/tests-e2e/visual-language/inventory-series-sort-panel.spec.ts:62-67 の `openFilterPanel()`
  → これを使う **E10**（同:174）
- 単体テスト frontend/src/pages/inventory/InventoryPage.toolbar.test.tsx:143 の `findByTestId('inventory-filter-panel')`

この目印は今 frontend/src/pages/inventory/InventoryFilterPanel.tsx:116-117 にあり、本便でこの部品は
**PC 専用**になる。よって**新しい `InventoryFilterDrawer` の中身の入れ物に同じ目印を付け直す**
（`data-testid="inventory-filter-panel"`）。こうすると D6・D7・E10・単体 K6 は**作り替え不要で緑のまま**通る:

| 検査 | 期待していること | 新しい形で満たせるか |
|---|---|---|
| D6 | パネルの中に `inventory-fresh-check` と `inventory-reset-in-panel` がある | ○（4-4 の項目1・12をそのまま root に置く） |
| D7 | `inventory-fresh-check` の**先祖の `<label>`** の高さが44px以上 | ○（`<label>` で包む形を崩さない。崩すと xpath が外れる） |
| D8 | 文字に数が入る／切ると減る | **×＝作り替える**（下の(2)） |
| E10 | パネルの中に `inventory-expiry-warning` があり、幅がパネルの内側 | ○（4-4 の項目2） |
| K6 | パネルの中に5つの目印と注記がある | **×＝これも誤り（下の訂正）** |

**PC とスマホで同じ目印が同時に出ることはない**（4-2 の `isMobile ?` が同じ三項演算子の両枝なので、
DOM に載るのは常にどちらか一方）。

**訂正（実装便で判明）**: 上の表の「K6 は○（作り替え不要）」は誤りだった。実測
（`cd frontend && npx vitest run --config vitest.unit.config.ts --project unit src/pages/inventory`）は
**1 failed / 40 passed**。落ちたのは frontend/src/pages/inventory/InventoryPage.toolbar.test.tsx の
K6、元の135行目 `expect(screen.queryByTestId('inventory-price-min')).toBeNull()`。

理由は2つ、どちらも4-3で決めた「Drawer は閉じても中身を DOM に残す」作りそのものから来ている:

1. スマホでは `InventoryFilterDrawer` を**開く前から常にマウントする**（4-1・4-3）。中身も
   「常に描く」（4-3）ため、パネルを開く前から `inventory-price-min` 等が DOM 上に存在する。
   よって「上の操作台に出ていない」ことを `toBeNull()`（DOM に無い）で確かめることはできない。
   「開く前は閉じている」（`.comp-drawer-panel--open` が無い）ことと、「上の操作台
   （`.inventory-toolbar`）の中には無い」こと（`toolbar.contains(...)` が `false`）の2つに
   分けて確かめる形に作り替えた。
2. コンディションは `MultiSelect layout="row"` になり、目印が `-button` から `-row`
   （`inventory-condition-filter-row`）に変わった（frontend/src/components/MultiSelect.tsx:21の
   コメント「button は inline/row では出さない」）。元の K6 は
   `inventory-condition-filter-button` を待っていたため、これも作り替えが必要だった。

直した K6 とその理由コメントは frontend/src/pages/inventory/InventoryPage.toolbar.test.tsx にある。
合わせて K9（候補の外の保存値が消えないこと・審査 H2）・K10（隠すシリーズを選ぶと有効化が自動で
入ること・PO 決定6）を同ファイルに追加し、`npx vitest run --config vitest.unit.config.ts --project unit
src/pages/inventory` は 0 failed（9 test files・43 tests）になっている。

#### (2) D8 を作り替える（PO 決定1）

**「文字が『詳細フィルタ』と完全一致し、数字を含まない」**に差し替える
（frontend/tests-e2e/visual-language/inventory-toolbar-mercari.spec.ts:170-182 が現物）。

#### (3) F5 の寄生をやめる（便2.5 からの宿題・審査 H4）

現物（frontend/tests-e2e/visual-language/inventory-series-sort-panel.spec.ts:320-333）は
`flex: 1 1 0` に戻したうえで `scrollWidth > clientWidth` を期待する＝**「切れること」を確かめる**検査。
初版の説明は2点まちがっていた:

- CI の既定の種別名は「すべて」ではなく**「ポケモン」**（同:95-99 の E4 が mock の表示名を明記）。
- 本便で ` (1)` が消えると残り幅が**増える**ので、合否が動く向きは「嘘の緑」とは限らない。

**この便では「どちらに転ぶか」を予測しない**。設計の初版は「嘘の緑になりうる」、独立審査 r1 は「赤になる」と
**逆の予測**を立てたが、どちらも DOM と CSS からの演算で、この端末では Playwright のブラウザが入らないため
実測できない（docs/handoff/toolbar-series-name-full-width/review-opus.md に、同じやり方の予測が
**両方向に外れた実例**がある）。

よって**予測に依存しない形に作り替える**: 閲覧ページ B7c と同じく、**spec の中で長い種別名
（14文字・「マジック：ザ・ギャザリング」相当）の選択肢を自前の mock で用意し、それを選んでから `flex` を壊す**。
残り幅がどれだけ増えても 168px の名前は収まらないので、**隣の文言の長さに合否が左右されなくなる**。
共有の frontend/tests-e2e/visual-language/inventory-helpers.ts は**変更しない**（他の spec に影響するため）。

**CI の1回目で必ず確認すること**（審査 r1 が「残る不確かさ」として挙げた4点）: D6・D7・E10 が緑か／
作り替えた F5 が緑か／スライドアウト中にパネルが空にならないか／「隠す〜」の行の右の文字が読めるか。

### 4-10. 触らないもの（境界）

- `frontend/src/components/` 配下すべて（`Drawer`・`MultiSelect`・`Checkbox`・`Button` の金型）。
- 閲覧ページ `frontend/src/pages/viewer/` 一式（ADR-1019。読むだけ）。
- API への問い合わせ・`/me/inventory-filters` の保存形・`resetAll` の中身・注記の文言の組み立て。
- PC の分岐（`ContentToolbar`・PC の浮かぶ選択・`Tabs`）。
- 種別・並び替えのパネル（便2 の `Drawer`）。

## ⑤ 受け入れ基準

新 spec は `frontend/tests-e2e/visual-language/inventory-filter-subscreen.spec.ts`。
**宣言は9本にまとめる**（審査 M6）。`visual-language/*.spec.ts` は `vl-mobile-390` / `vl-tablet-768` /
`vl-desktop-1280` の**3 project で走る**（frontend/playwright.config.ts:55-77）ので
**9宣言＝27実行**。現在の収集は807件・持ち時間は15分（.github/workflows/e2e.yml の `visual-language-run`）＝**+3.3%**。
初版の16宣言（48実行）から半分に削った。過去2便の審査はどちらも実行数で設計を削らせている。

| 基準 | 検証方法 |
|---|---|
| G1 パネルが右から出て、左に地が残り、地を押すと閉じる | J1（幅＝画面の83%±1px・左端＝17%±1px・地を押すと `--open` が消える） |
| G2 root に12個が並び、見える「閉じる」ボタンが無い | J2（12個の目印がすべて root に在る・並び順も確認／**見える文字**として「閉じる」のボタンが0件。✕ の読み上げ名は `common.close`＝「閉じる」で必ず1件あるため、`drawer-close` を除いて数える＝審査 M2） |
| G3 行を押すと次の画面・「←」で戻る・行の右に名前が出る | J3（6行それぞれで「←」が出る／「決定する」で root に戻る／戻った行の右の文字が選んだ名前） |
| G4 機能が減っていない（6項目すべて一覧に効く）／G8 後半・P10・P11 | J4（各項目を選ぶと `/inventory?` の問い合わせに該当の語が乗る＋`inventory-filter-enabled` が自動で入る）＋単体テスト `frontend/src/pages/inventory/InventoryPage.toolbar.test.tsx` の **K9**（向きの合わせ方＝`(いまの集合 − 候補) ∪ next` で候補の外の保存値が残ること。**ここが H2 の歯止め**） |
| G5 ボタンに数字が出ない | J5（文字が「詳細フィルタ」と完全一致）＋作り替えた D8 |
| G6 横スクロール0・はみ出し0 | J6（`document`・`.mobile-content`・パネル本体の超過が0／パネル内の子の右端がパネル幅以内） |
| G7 PC 不変 | J7（幅1280で `.content-toolbar` あり・`inventory-filter-panel` が `section`・`supplier-drawer` の枚数が今と同じ）＋既存 D12・E14 |
| P2 root の行が44px以上／P3 次の画面の行が61px以上／G8 前半 | J8（行の高さ2種＋「隠す〜」の行の右の文字の幅が0でない） |
| P8 フォーカスが「←」→元の行へ移る／P9 閉じている間は注記が0件 | J9 |
| G9 閉じる途中で中身が空にならない | **検査を作らない**（スライドアウト中の見え方は実機の目で見る。4-3 の「中身は常に描く」が作りの歯止め）。CI の1回目と実機で確認する |
| 既存の画面検査が緑のまま（D6・D7・E10） | 目印 `inventory-filter-panel` を新パネルに引き継ぐ（4-9 (1)）。**作り替えない**＝CI で緑であることが合否 |
| F5 が隣の文言に寄生しない | 自前 fixture で長い種別名（168px 相当）を選んでから壊す形に直す（4-9 (3)）。**この端末では Playwright のブラウザが入らないため手元で赤を確かめられない**＝CI の1回目で緑を確認し、寄生していないことは「隣の文言に触れていないコード」で示す |
| 既存の作りを壊していない | `npm run check:all`／`npx tsc --noEmit`／`npm run test`（単体）／CI 必須15本 |

## ⑥ 触るファイル

| ファイル | 変更 |
|---|---|
| frontend/src/pages/inventory/InventoryFilterDrawer.tsx | **新設**（スマホのパネル＋6本の次の画面） |
| frontend/src/pages/inventory/InventoryFilterDrawer.css | **新設**（root の縦並び・次の画面の枠・一覧の全幅化） |
| frontend/src/pages/inventory/InventoryPage.tsx | props を1つにまとめる／スマホは新部品・PC は今の枠／向きの変換関数／`filterActiveCount` を削除 |
| frontend/src/pages/inventory/InventoryFilterPanel.tsx | スマホ専用の枝（recon.md §1 の 1〜6・12）と props を削除 |
| frontend/src/pages/inventory/InventoryToolbar.tsx | 「詳細フィルタ」の文字を数字なしに固定・`filterActiveCount` props を削除 |
| frontend/src/locales/ja.json / en.json | 新キー**9つ**（4-8。審査 M1 で3つ→9つ） |
| frontend/tests-e2e/visual-language/inventory-filter-subscreen.spec.ts | **新設**（J1〜J9＝9宣言・27実行） |
| frontend/tests-e2e/visual-language/inventory-toolbar-mercari.spec.ts | D8 を作り替え |
| frontend/tests-e2e/visual-language/inventory-series-sort-panel.spec.ts | F5 の寄生をやめる |
| frontend/src/pages/inventory/InventoryPage.toolbar.test.tsx | **K6 は作り替えが必要だった**（4-9 (1) の訂正を参照。`toBeNull` 系の期待とコンディションの目印が実態と食い違っていた）。**K9・K10 を追加**（候補の外の保存値が残ること／隠すシリーズを選ぶと有効化が自動で入ること） |

## ⑦ 戻し方

PR をそのまま revert すれば元に戻る。**新しいトークンも金型の変更も無い**ので、
戻しても他の画面に影響しない。辞書の追加キーは使われなくなるだけ。

## ⑧ 削除するファイル

なし（ファイル単位の削除は無い。行の削除は `InventoryFilterPanel.tsx`・`InventoryToolbar.tsx`・
`InventoryPage.tsx` にある）。

## ⑨ 外部・過去事例の参照と我々への応用

| 参照 | 我々への応用 |
|---|---|
| お手本（メルカリ）の絞り込みの実測（docs/specs/design-system/visual-language/benchmark/mercari-search-filter.md） | パネルは画面いっぱいにせず左に地を残す・項目は押すと次の画面・選択行は約61dp → P1・P3 にそのまま採用 |
| 閲覧ページ 便2（docs/handoff/viewer-filter-subscreen/design.md） | `Drawer` に「←」と Esc の戻る、`MultiSelect` に `layout="row"` を足した便。**その道具を使うだけで済む**（recon.md §4） |
| 閲覧ページ 便13a（docs/handoff/viewer-filter-choices-mercari/design.md） | 選択行61px・印の列48px・パネル83%の数値の出どころ。**同じトークンを使う**＝新しい寸法を作らない |
| 在庫表 便2 の教訓（docs/handoff/inventory-series-sort-panel/design.md） | `Drawer` は閉じても中身を残す→開閉の判定は `--open` で見る（4-3・単体テストの書き方） |
| 在庫表 便2.5 の教訓（docs/handoff/toolbar-series-name-full-width/design.md） | 「壊すと切れる」検査は隣の文言の長さに寄生する→F5 を自前 fixture に直す（4-9） |

## ⑩ 弊害・トレードオフ

- **上から「絞り込みが効いているか」が分からなくなる**（PO 決定1）。既定で24時間以内が入っているため、
  いまは常に `(1)` 以上が見えていた。効き目はパネルを開けば行の右の文字で分かる。
- **項目ごとに1タップ増える**（その場のチェック群 → 行を押して次の画面）。代わりに root が短くなり、
  スクロールせずに全項目が見える。
- **在庫表の中でパネルの幅が2種類になる**。種別・並び替え（便2）は全幅、詳細フィルタは83%。
  お手本が同じ使い分けをしているため、お手本に合わせる側を採る。
- **`.comp-multiselect__row:hover` が `@media (hover: hover)` で囲まれていない**
  （frontend/src/components/MultiSelect.css:117-120）。スマホで指を離しても色が残る恐れ。
  本便は金型を触らない方針なので**宿題として起票**し、別便（金型の便）で直す。
  なお次の画面の行（`.comp-multiselect__option`）は囲まれている（同:46-50）。
- **`InventoryFilterPanel` からスマホの枝を削るので、PC 専用部品になる**。将来 PC でも同じ形にするときは
  新部品の側を伸ばす。**ただし目印 `inventory-filter-panel` は新しいスマホのパネルにも付ける**（4-9 (1)）。
- **チェックの意味が PC 版と逆になる**（PO 決定5）。スマホは「隠すものを選ぶ」、PC は「表示するものにチェック」。
  行と画面の題を「隠す〜」にし、説明文（`hideNote`）を添えることで取り違えを防ぐ。
  なお**保存される値は同じ**（どちらも「隠した集合」を送る）ので、PC とスマホを行き来しても設定は壊れない。
- **「表示条件」という括りの見出しがスマホから消える**（形態と在庫・予約が独立した2行になる）。
  まとめて説明していた注記は両方の画面に出す（4-6・審査 M9）。
- **自動で入る「フィルタを有効化」はサーバに保存される**（PO 決定6）。次に開いたときも入ったままになる。
  利用者が自分で切ったときは勝手に入れ直さない（4-5a）。
- **自動で入る「有効化」は4項目の共通スイッチなので、1項目を選ぶと保存済みの他3項目も同時に効き始める**
  （審査 r2 の M-1）。例: 有効化を切ったまま隠し列を5つ保存している利用者がスマホで形態を1つ選ぶと、
  その瞬間に列が5本消え、保存済みの隠しシリーズも効いて行が減る。本人は形態しか触っていない。
  根拠: `filterEnabled` は `InventoryPage.tsx:240`・`:246`・`:247`（問い合わせ）と `:182-184`（列）の
  共通の条件。PO 決定6 を実装に忠実に書いた結果であり、コード側は変えない。
- **上から「絞り込みが効いているか」が分からなくなる**ことと合わせ、効き目の確認はパネルを開く操作が必要になる。

## ⑪ 維持の仕組み

守り手: frontend/tests-e2e/visual-language/inventory-filter-subscreen.spec.ts

- 対象: パネルの幅と位置（83%/17%）・root の12項目と並び・次の画面への出入り・選択が残ること・
  行の高さ（44px/61px）・横はみ出し0・**PC 不変**・ボタンに数字が出ないこと。
- 置き場所は `visual-language/` 配下にする（`frontend/tests-e2e/` 直下に置くと CI で1本も走らない。
  docs/handoff/inventory-mobile-responsive/design.md の C5）。
- 併せて既存の守り手（inventory-toolbar-mercari.spec.ts の D1〜D12・inventory-series-sort-panel.spec.ts の
  E1〜E14・F1〜F5）を**緑に保つ**ことが本便の条件。

## ⑫ 継続（この便の後）

| # | 内容 |
|---|---|
| 便4（④） | 検索を「押すと検索画面が開く」形に（閲覧ページ 便12a・便12b と同じ） |
| M1 | `.comp-multiselect__row:hover` を `@media (hover: hover)` で囲む（金型の便・⑩） |
| M2 | 「フィルタを有効化」を次の画面にするか（4-4 の割り切り・PO 判断） |
| M3 | 辞書の `inventory.filterPanel.buttonWithCount` の後片付け（参照0になったら消す） |
| M4 | 便0 からの持ち越し: C2（カードのラベル/値の幅配分）・C3（詳細パネルの折り返し）・C5（`tests-e2e/` 直下の spec が走らない） |
| M6 | **便2 からの持ち越し（審査 M8 で台帳に戻した）**: `resetAll` のコメントが「既定（発売日の早い順）」なのにコードは `setSortDir("desc")`＝新しい順で**逆**（frontend/src/pages/inventory/InventoryPage.tsx:385-393） |
| M7 | 便2.5 からの持ち越し: B7c の後片付けが再試行しない／F2 は山形が消えると緑になる／F3 が ja 文言「価格が安い順」に直結／`MAX_TOP_Y` の余裕が 0→12px に緩んだ |
| M5 | 原文パネルのタブが 68x36px で44pxに足りない（便0 の実測） |

L3（「詳細フィルタ (n)」の数え方）は **PO 決定1（数字をやめる）で決着**＝宿題から外す。

## 対象 ADR

- **docs/adr/ADR-144-ui-component-governance.md**: 金型の新設も変更もなし。`frontend/src/components/` は
  **1ファイルも触らない**（recon.md §4 の道具がすべて既にある）。スマホ専用の画面をページ側に持つのは
  閲覧ページに先例がある。
- **docs/adr/ADR-067-design-token-enforcement.md**: 新しい寸法・色を作らない。83%・61px・48px はすべて
  既存トークン（frontend/src/tokens.css:445・174・175）。
- **docs/adr/ADR-027-ui-internationalization.md**: 追加文言は ja/en 同一キーで9つ（4-8。初版の「3つ」は審査 M1 で9つに増えた）。
- **docs/adr/ADR-1019-inventory-viewer-separate-accounts.md**: 閲覧ページは別アプリ。お手本として読むだけ。
- **docs/adr/ADR-140-mobile-nav-bottom-tabs.md**: 押せる高さの下限（44px/48dp）の根拠。
- **docs/adr/ADR-093-inventory-table-product-master-redesign.md**: 詳細フィルタ自体の由来（`InventoryFilterPanel` の冒頭コメント）。
