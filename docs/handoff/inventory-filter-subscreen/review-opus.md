# review: 在庫表（/inventory）スマホの詳細フィルタをパネル＋次の画面に（便3）独立審査

## r1（Opus・2026-11-01・反証を探す立場）: **REVISE**

審査対象は `docs/handoff/inventory-filter-subscreen/design.md`（下調べは同ディレクトリの
`docs/handoff/inventory-filter-subscreen/recon.md`）。実コードを抜き取り検証した結果、
**実装前に直せる穴が HIGH 5件・MEDIUM 9件**あった。判定は REVISE。
各指摘の根拠はすべて作業ツリーの現物（ファイル:行と実際の文字列）で確かめ、
演算だけで出した結論は「未確認」と明記した。コードは1文字も変更していない。

---

### HIGH

| # | 指摘 | 現物の根拠 | 設計の直し方 |
|---|---|---|---|
| H1 | **既存の画面検査3本（D6・D7・E10）が赤になる**。design ⑥ は D8 と F5 しか作り替え対象に挙げていない。原因は spec の補助関数が**入れ物の目印**を掴んでいること | `frontend/tests-e2e/visual-language/inventory-toolbar-mercari.spec.ts:87-92` の openFilterPanel() が `const panel = page.getByTestId("inventory-filter-panel"); await expect(panel).toBeVisible();` で待つ。使うのは D6（`:151`）・D7（`:159`）・D8（`:170`）。同じ形の関数が `frontend/tests-e2e/visual-language/inventory-series-sort-panel.spec.ts:62-67` にもあり E10（`:174`）が使う。`inventory-filter-panel` は `frontend/src/pages/inventory/InventoryFilterPanel.tsx:116-117` の `<section>` だけに付いている。design ⑥ でスマホは新部品に差し替わるので**スマホからこの目印が消える** | 新部品の中身を包む要素に **`data-testid="inventory-filter-panel"` を据え置く**（4-4 の「目印は既存の名前を据え置く」を入れ物にも広げる）。そのうえで P6／H12 の PC 判定は今の文面どおり「`inventory-filter-panel` が `section` 要素」で区別がつく。据え置かない場合は ⑥ に D6・D7・E10 の書き換えを明記する |
| H2 | **4-5 の「全件 − 隠した集合」は、保存済みの `hiddenCategories` を黙って消し、サーバにも書き戻す**。便2 の審査 H3（`tcgTypes` 取得失敗で種別が選べない）と同じ型の穴が、カテゴリー側に残っている | 全件の出どころは `frontend/src/pages/inventory/InventoryPage.tsx:180` の `const sortedCategories = useMemo(() => [...categoryFacet].sort(), [categoryFacet]);` → `categoryFacet` は API 応答（同`:263` `if (d.categories) setCategoryFacet(d.categories);`）。サーバ側は `backend/app/routers/inventory_offers.py:460` `categories = sorted({r["category"] for r in facet_rows if r["category"]})` で、`facet_rows` は絞り込み（`where`）を通さない（同`:306-307`・`:454` のコメント「絞り込みなしの配信行から作る」）が、**「24時間以内」の時間の窓の内側で作られる**（同`:403` `age_condition, age_params = _age_window(window_hours)` → `:419` `distribution_rows_parts(... age_condition=age_condition ...)`）。24時間以内は既定 ON（`frontend/src/pages/inventory/InventoryPage.tsx` の `freshOnly` 既定 true）。つまり `sortedCategories` は**保存済み `hiddenCategories` の真部分集合になりうる**。`hiddenCategories = 全件 − next` だと候補に出ていない隠し済みの種別が全部「表示する」に戻り、`frontend/src/pages/inventory/InventoryPage.tsx:93`（`hidden_categories: Array.from(v.hiddenCategories)`）経由で `/me/inventory-filters` に PATCH される（同`:374`）。今の1件ずつの反転（同`:496-504` `toggleHiddenCategory`）は候補に無い値を触らないのでこの事故は起きない。さらに候補が空のとき `selected` が空になり `frontend/src/components/MultiSelect.tsx:82` が `allLabel`＝「すべて」を出す＝**隠しているのに「すべて」と表示する** | カテゴリーは**全件からの引き算をやめ、「候補に出ている値だけ」を差分で反転する**（`hiddenCategories` の既存メンバーのうち候補外の値は必ず残す）。もしくは H2 と M3 をまとめて、`selected` に**隠した集合をそのまま**渡し `allLabel` を「すべて表示」にする。**「列」側には同じ穴は無い**（`hideableColumns` は定数 `HIDEABLE_COLUMNS`＝`frontend/src/pages/inventory/InventoryPage.tsx:106-108` の7件で縮まない） |
| H3 | **TCGシリーズ・表示する列・形態・在庫・予約の4項目は「フィルタを有効化」が入っていないと一覧に1つも効かない**。KGI G4 と受け入れ基準 H8 は実機で×になる | `frontend/src/pages/inventory/InventoryPage.tsx:140` `const [filterEnabled, setFilterEnabled] = useState(false);`（既定 OFF）。同`:239-241` `if (filterEnabled && hiddenCategories.size > 0) { params.set("hide_categories", ...) }`、同`:245-246` `if (filterEnabled && showUnits.size > 0) ...` / `showOfferTypes`、同`:181-184` `const colVisible = useCallback((c: string) => !filterEnabled \|\| !hiddenColumns.has(c), ...)`。CI の mock も `frontend/tests-e2e/visual-language/inventory-helpers.ts:87-92` で `enabled: false`。加えて**「表示する列」は原理的に問い合わせに語が乗らない**（列の取捨は `colVisible` だけ） | ② G4 を「**『フィルタを有効化』を入れた状態で**6つの行が効く」に直す（PO が実機で判定する手順に「まず有効化を入れる」を書く）。⑤ H8 は対象を提供者・コンディション・TCGシリーズ・形態・在庫・予約の5つに限定し、spec では `inventory-filter-enabled` を押してから測る。「表示する列」は別判定（列の数が変わること）にする |
| H4 | **4-9 の F5 の説明が2つ間違っている**。(a)「既定の種別名『すべて』」は事実と違う。(b) 寄生の向きが逆で、放置すると**嘘の緑ではなく赤**になる | (a) CI の mock は `/products/tcg-types` を3件返し（`frontend/tests-e2e/visual-language/inventory-helpers.ts:94-98`）、既定の `activeTab` は `frontend/src/pages/inventory/InventoryPage.tsx:134` の `useState<string>("pokemon_booster_box")` なので既定の種別名は**「ポケモン」**。spec 自身が E4（`frontend/tests-e2e/visual-language/inventory-series-sort-panel.spec.ts:95-102`）に「mock での表示名は『ポケモン』」と書いている。design 4-9 の「すべて」は閲覧ページ B7c の話の写し間違い。(b) F5 は `expect(scrollWidth).toBeGreaterThan(clientWidth)`（同`:320-333`）＝**切れることを期待**する。` (1)` が消えると隣が約24px短くなり種別に使える残り幅が**増える**ので、切れなくなれば F5 は赤 | 文面を訂正する。直し方も簡単にできる: **選び直す必要は無い**。F5 の中で `/products/tcg-types` の `pokemon_booster_box` の `name_ja` を長い名前（「マジック：ザ・ギャザリング」）に差し替えれば**既定のまま**長い名前が出る。種別の**件数**は3件のままなので E5（`:105-113` の `toHaveCount(4)`）は壊れない。ただし `installInventoryMocks` に追加の mock を渡す口が無い（`frontend/tests-e2e/visual-language/inventory-helpers.ts:66-69` の引数は `items`/`rawTexts` だけ）ので、**F5 だけ `installAuthBypass` ＋ `mockApi` を自前で呼ぶ**（`frontend/tests-e2e/utils/api-mock.ts:50` 「同じ key は最後に定義された値で上書きされる」）か、helpers に引数を1つ足すかを 4-9 で決めること |
| H5 | **4-3 の「中身は `open` のときだけ描く」は、閉じるアニメーションの間パネルが空になる**。お手本はこれを意図して避けている | `frontend/src/components/Drawer.css:39-41` `transform: translateX(100%); transition: transform var(--transition-slow);` ＋ `:43-45` `.comp-drawer-panel--open { transform: translateX(0); }`。DOM は常にマウント（`frontend/src/components/Drawer.tsx:131-139`）なので `open` が false になった瞬間に中身を外すと**白いパネルが空のままスライドアウトする**。お手本の `frontend/src/pages/viewer/InventoryView.tsx:196-198` のコメントは「閉じるときに戻さないのは、**スライドアウト中に題と中身が切り替わって見えるのを避けるため**」と明記し、お手本の `Drawer`（同`:785-867`）も便2 の `choicePanel` の `Drawer`（`frontend/src/pages/inventory/InventoryPage.tsx:684-695`）も `{open && …}` で守っていない | 中身は**常に描き**、既存 E1 が見る**注記（`inventory-expiry-warning`）だけ**を `{open && …}` で守る（E1 の判定は `frontend/tests-e2e/visual-language/inventory-series-sort-panel.spec.ts:74-78` の `toHaveCount(0)` 1本だけ）。P9／H16 もそれで満たせる |

---

### MEDIUM

| # | 指摘 | 現物の根拠 | 設計の直し方 |
|---|---|---|---|
| M1 | **新しい `MultiSelect` に渡す必須 props の文言が辞書に無い。「新キー3つ」では足りない** | `frontend/src/components/MultiSelect.tsx:46-51` — `clearLabel` / `allLabel` / `countLabel` は**省略不可**。既存にあるのは `inventory.supplierFilter.{clear,all,count}` と `inventory.conditionFilter.{clear,all,count}` だけ。TCGシリーズ・表示する列・形態・在庫・予約の4項目には1つも無い（`frontend/src/locales/ja.json` の `inventory.filterPanel` は `button`/`buttonWithCount`/`enable`/`categories`/`columns`/`columnsNote`/`displayConditions`/`displayConditionsNote` の8キーだけ） | 4-8 に不足分を書く。最小は**共有の1組**（`inventory.filterPanel.clear` / `.count`。全件は既存の `common.all`＝「すべて」を使う）で4項目を使い回す＝ja/en 各2キー追加。ADR-027 のとおり ja/en 同一キー |
| M2 | **H4（`common.close` の文字が無い）はそのままでは成り立たない**。✕ ボタンの読み上げ名がちょうど「閉じる」 | `frontend/src/components/Drawer.tsx:176-185` の ✕ が `aria-label={t("common.close")}`・`data-testid="drawer-close"`。`frontend/src/locales/ja.json` の `common.close` は「閉じる」。`getByRole("button", { name: "閉じる" })` / `getByLabelText` で測ると必ず1件見つかる | H4 を「**見える文字**として『閉じる』のボタンが無い」に書き直す（例: `panel.locator("button", { hasText: 閉じる })` が0件、または `getByRole("button", {name})` が `drawer-close` の1件だけ） |
| M3 | **「隠す側」の2行は、既定（何も隠していない）で行の右に全件の名前が並ぶ。「すべて」にならない** | `frontend/src/components/MultiSelect.tsx:82` `const selectedSummary = selected.length === 0 ? allLabel : selected.map(resolveLabel).join(", ");`。4-5 の変換後、既定は `selected` が全件なので「表示する列」の行の右は「型番, 状態, 数量, 単価, 仕入元, 備考, 発送」（`frontend/src/pages/inventory/InventoryPage.tsx:106-108` ＋ `inventory.col.*`）。画面外には出ない（`frontend/src/components/MultiSelect.css:129-138` が `flex:1; min-width:0; overflow:hidden; text-overflow:ellipsis`）が、`.comp-multiselect__row-label` は `flex-shrink: 0`（同`:122-127`）。幅360→パネル298.8px、`.comp-drawer-body` の左右 `var(--space-6)`＝24px（`frontend/src/tokens.css:79`）で内側250.8px。「TCGシリーズの表示／非表示」は `--font-base` 14.4px（同`:16`）で**約185px**、＋`gap: var(--space-2)`×2＝16px ＋山形18px ＝ 約219px。値に残るのは**約30px＝「…」だけ**（**机上の演算・未実測**）。②G3 の「選んだ名前が行の右に出る」がこの2行では成立しない | H2 の直し方と同じ向きにそろえる＝隠す側は `selected` に**隠した集合**を渡し `allLabel` を「すべて表示」にする（0件＝何も隠していない）。行の名前も短くする（「TCGシリーズ」） |
| M4 | **候補が0件のとき「該当なし」の文言が消える＝機能が減る** | `frontend/src/components/MultiSelect.tsx:93-94` — `options` が空で `emptyLabel` 未指定なら**何も描かない**（金型のコメント`:15-18`「アプリ側の既存呼び出し元が emptyLabel を渡していないため、ここで origin/main と同じ『空なら何も出ない』に保つ」）。今は `frontend/src/pages/inventory/InventoryFilterPanel.tsx:212-213`（カテゴリー）と `:274-275`（形態）が `t("inventory.noResults")` を出している。design 4-6 は `emptyLabel` に触れていない | 4-6 に「次の画面の `MultiSelect` には `emptyLabel={t("inventory.noResults")}` を渡す」と明記 |
| M5 | **`onBack` / `backLabel` は「2つ一緒に渡す」だけでは型が通らない** | `frontend/src/components/Drawer.tsx:51-53` の union は `{ onBack: () => void; backLabel: string } \| { onBack?: undefined; backLabel?: undefined }`。`onBack={cond ? fn : undefined}` と `backLabel={cond ? s : undefined}` を**別々に書くと**どちらの枝にも当てはまらず tsc が赤。お手本は1つのオブジェクトを spread している（`frontend/src/pages/viewer/InventoryView.tsx:365` の `const filterDrawerBackProps = ...` → 同`:790` の `{...filterDrawerBackProps}`） | 4-3 に「お手本と同じく1オブジェクトを作って spread する」と書く。`footer` は `footer?: ReactNode`（同`:38`）なので単独で `undefined` 可＝この問題は無い |
| M6 | **画面検査の実行数の見積りが設計書に1行も無い**。過去2便の審査はどちらもここで設計を削らせている | `frontend/playwright.config.ts:55-77` — 「visual-language/*.spec.ts」は `vl-mobile-390` / `vl-tablet-768` / `vl-desktop-1280` の**3 project**で走る（`chromium` は `testIgnore` で除外）。持ち時間は `.github/workflows/e2e.yml:151-158` の `visual-language-run` ジョブで **15分**（`playwright` ジョブは同`:252` の `if: false` で停止中）。手元で数えた現在の数は **807件／20ファイル**（`npx playwright test --project=vl-mobile-390 --project=vl-tablet-768 --project=vl-desktop-1280 --list`）。design ⑤ の H1〜H16 は16宣言＝**48実行（+6%）**。便2 の審査 H5 は81実行の案を削らせ、便2.5 の審査 M5 は「5宣言＝15実行」まで落とさせている（当時の持ち時間は10分） | ③ か ⑤ に実行数の見積りを1行書く。宣言を束ねれば半分になる（H3+H4、H5+H6+H7、H10+H11、H13+H14 を各1宣言に）＝**8宣言＝24実行**。何分増えるかは**未確認**（この端末では Playwright のブラウザが入らない） |
| M7 | **4-6 の「列は固定11件」は誤り。7件** | `frontend/src/pages/inventory/InventoryPage.tsx:106-108` `const HIDEABLE_COLUMNS = ["mark", "condition", "quantity", "unitPrice", "supplier", "note", "ship"];` | 「固定7件」に訂正（結論＝10件を超えないので絞る欄は出ない、は変わらない） |
| M8 | **便2 の宿題が台帳から落ちている** | `docs/handoff/inventory-series-sort-panel/design.md:315` の ⑫ M3「`resetAll` のコメントが『発売日の早い順』でコードと逆（実際は新しい順）」は未修正（`frontend/src/pages/inventory/InventoryPage.tsx:385-393`：コメント「既定（発売日の早い順）」／`setSortDir("desc")`）。design ⑫ は便2 の M1（hover）は引き継いだが M3 は消えている | ⑫ に戻す。あわせて 4-4 項目12「リセット」に、`resetAll` が**詳細フィルタの値を1つも戻さない**（同`:386-392` は `searchQ`/`debouncedQ`/`category`/`sortField`/`sortDir`/`page` だけ。意図的）ことを明記する — パネルの中でリセットが絞り込みの行の下に並ぶので PO が誤解しうる |
| M9 | **`displayConditionsNote` は形態と在庫・予約を「まとめて」説明している注記**。4-6 の「その項目の次の画面の中に出す」だと2画面に同じ文が重複する | `frontend/src/pages/inventory/InventoryFilterPanel.tsx:263-268` — 「表示条件」の見出しと注記が1つで、その下に形態（`:270-287`）と在庫・予約（`:289-302`）が入る。文言は `frontend/src/locales/ja.json` の `inventory.filterPanel.displayConditionsNote`「選択した条件に一致する行だけを表示します（各項目で未選択なら全件）。」 | どちらの画面に出すか（または2画面に出すか／文を分けるか）を 4-6 で決める。「表示条件」の見出し自体がスマホから消える（グループの括りが無くなる）ことも ⑩ に書く |

---

### LOW

| # | 指摘 | 現物の根拠 / 取るべき対応 |
|---|---|---|
| L1 | **recon.md の裸のファイル名の引用4件で関所が赤になる**（design.md 本体ではなく下調べ側） | 手元で実測: `LOCAL_PRECHECK=1 MOCK_PR_BODY=… CHANGED_FILES=… node scripts/check-process-artifacts.js` が 「InventoryFilterPanel.tsx」「InventoryPage.tsx」「InventoryToolbar.tsx」「*Page.tsx」を「ファイルが存在しません」で落とす。原因は `docs/handoff/inventory-filter-subscreen/recon.md:40-85` と `:147` の「`InventoryFilterPanel.tsx:131-144`」「`*Page.tsx`」のようにバッククォートで囲んだ裸のファイル名（ディレクトリなし）（`scripts/check-process-artifacts.js:1351-1360` のバッククォート正規表現が拡張子付きパスを拾い、`:1381-1389` で `existsSync` する）。→ **recon.md をフルパスに直す**（`frontend/src/pages/inventory/InventoryFilterPanel.tsx:131-144`）。「*Page.tsx」はバッククォートを外す |
| L2 | **design.md 本体の関所検査は通る（実測）** | `scripts/check-process-artifacts.js` の `validateDesignDoc`（`:1392-1440`）が見るのは「`\| 基準 \|` の表」「表の2列目が空の行が無い」「recon.md への相互参照」「宣言した ADR が本文に在る」「`## 外部・過去事例` 欄が非空」の5点で、design.md はすべて満たす。`## ⑪ 維持の仕組み` の `守り手:` 行もある（`:1443-1478`）。守り手の spec が未作成なので今は落ちるが**警告モード**（実行結果: `⚠️ 維持の仕組み欄チェック（警告モード・将来failへ引き上げ予定）`）＝同じ PR で spec を作れば消える。design.md 側にも裸のファイル名の引用が5件あるが、**設計doc は citation 検査の対象外**なので赤にならない |
| L3 | 行番号のズレ（いずれも ±1行） | 4-5 の `477-480`→実 `478-481`（`onSupplierChange`）、`481-484`→`482-485`（`onConditionChange`）、`486-493`→`487-493`（`filterActiveCount`）、`506-513`→`505-512`（`toggleHiddenColumn`）。4-8 の `234-240`→出し分けの実体は `236-239`。4-1 の「723行」、4-5 の `93-94`（`hidden_categories`/`hidden_columns`）、P1/P2/P3 のトークン行（`frontend/src/tokens.css:445`／`:577`／`:174`）は**正しい** |
| L4 | `frontend/src/pages/inventory/InventoryPage.tsx` の行数上限は余裕あり | 現在 723行／上限 800行（`frontend/scripts/check-page-size.js:19-20` の `REGULAR_LIMIT = 800`）。手元で `node scripts/check-page-size.js` → `✅ ページサイズチェック PASSED`。今の `<InventoryFilterPanel …/>` の呼び出しは `:590-629` の40行で、`filterPanelProps` 化してもほぼ同数。差し引き +20行前後の見込み（**未確認**）。ただし 4-1 の「props を1つにまとめる」は**行を減らす策ではなく、2回書いて+40行になるのを防ぐ策**なので文面を正確にするとよい |
| L5 | `buttonWithCount` を残す判断は正しい | `frontend/package.json` の `check:all` に**未使用の辞書キーを見る検査は無い**（`check:i18n-missing-keys` は ja/en の欠落だけ）。4-8 の「辞書のキーは消さない」で問題なし |
| L6 | `.comp-multiselect__row:hover` を足しても既存 E13 は赤にならない | E13（`frontend/tests-e2e/visual-language/inventory-series-sort-panel.spec.ts:196-241`）は `const target = ".inventory-choice-row:hover";` を**名指し**で探す。`.comp-multiselect__row:hover`（`frontend/src/components/MultiSelect.css:118-120`・`@media (hover: hover)` の外）は検査されない。⑩ の宿題扱い＋⑫ M1 で妥当 |

---

### r1 で「問題なしと確認された」点（再確認不要）

1. **PC は一緒に変わらない（審査の仮説1は反証された）**。便2 で PC とスマホの JSX 変数はすでに分かれている:
   PC の `filterButton`（`frontend/src/pages/inventory/InventoryToolbar.tsx:168-178`）は本文が
   `{t("inventory.filterPanel.button")}` だけで**数字を出していない**。数字の出し分けはスマホ専用の
   `filterButtonMobile`（同`:225-240`。`:236-238` の `p.filterActiveCount > 0 ? …buttonWithCount… : …button…`）
   にしか無い。同ファイル`:180-181` のコメントも「PC 分岐が使う search / resetButton / freshButton /
   sortMenu / filterButton は1文字も触らない」と宣言している。よって PO 決定1 はスマホの話で、
   KPI P6（PC 不変）と矛盾しない。`filterActiveCount` props の削除も PC に影響しない。
2. **赤になる単体テストは K6 だけ**＝design ⑥ のとおり。`frontend/src/pages/inventory/InventoryPage.toolbar.test.tsx:143`
   が `findByTestId('inventory-filter-panel')` を掴む（H1 の直し方（a）を採ればこれも赤にならない）。
   K1〜K4（`:69-124`）は PC 扱い。K7・K8（`:151-188`）は別の `Drawer` で、`openPanel()`（同`:54`
   `document.querySelector('.comp-drawer-panel--open')`）が**開いている1枚だけ**に絞るので4枚目が増えても壊れない。
   `frontend/src/pages/inventory/InventoryPage.singlefetch.test.tsx` は `stubMatchMedia` を呼ばず PC 扱い＝
   `inventory-supplier-filter-button`（同`:127`）は PC 操作台のもので赤にならない。
3. **`supplier-drawer` が2枚同時に `--open` になる瞬間は無い**。既存 spec は全部 `.comp-drawer-panel--open` で
   絞ってある（`frontend/tests-e2e/visual-language/inventory-series-sort-panel.spec.ts:34-36`）。PC には
   新しい `Drawer` を出さない（4-2 の `isMobile ?` 分岐）ので H12 の「`supplier-drawer` の枚数が今と同じ」も成立する。
   PC の `InventoryFilterPanel` とスマホの新部品が同時に DOM にある瞬間も無い（同じ三項演算子の両枝）。
4. `frontend/tests-e2e/visual-language/drawer-inert-closed.spec.ts` は `gotoViewer` しか呼ばない（`:112`・`:131`・`:164`）
   ＝在庫表に `Drawer` を増やしても赤にならない（便2 の審査と同じ結論）。
5. **「空っぽ＝全件」が壊れるのはカテゴリーと列だけ**。形態・在庫・予約は出す側のまま（`showUnits` /
   `showOfferTypes`）で `Array.from()` の素通し＝意味は反転しない。`unitFacet` が取得失敗で空になっても
   「選べない」だけで**保存値は消えない**（反転の計算に全件を使わないため）。
6. **トークンと金型の道具はすべて実在**: `frontend/src/tokens.css:445`（`--drawer-panel-w-mobile-inset: 83%`）・
   `:174`（`--comp-multiselect-check-row-h: 61px`）・`:175`（`--comp-multiselect-check-col-w: 48px`）・
   `:577`（`--comp-multiselect-row-h: 53px`）。`mobileInset` は `frontend/src/components/Drawer.css:129-131` が
   当てる。一覧の全幅化も呼び出し側から渡せる（`frontend/src/components/MultiSelect.css:30-32` の
   `--comp-multiselect-list-bleed`）。**`frontend/src/components/` を1ファイルも触らずに作れる**という
   4-10／ADR-144 の主張は成立する。
7. **新設ファイルは金型の関所の対象外**。`frontend/scripts/check-stories-count.js:17,25-27` は
   `src/components/` 配下だけ、`frontend/scripts/check-mobile-responsive-structure2.js:26-29` は
   `src/components/Drawer.css` と `Modal.css` だけ。手元で `check:page-size`・`check:content-toolbar`・
   `check:page-folder` を実行し3本とも PASS（ベースライン）。`ContentToolbarRange` をパネルの中で使う形は
   今の `frontend/src/pages/inventory/InventoryFilterPanel.tsx:174-195` で既に CI を通っている。
8. **候補一覧がサーバ側の絞り込みで消えることは無い**（`backend/app/routers/inventory_offers.py:454` の
   コメントと `:306-307` の `rows_x`／`rows_f` の分離）。H2 は「絞り込み」ではなく**時間の窓とデータ量**の側の話。

---

### 残る不確かさ（正直に記録する）

**この端末では Playwright のブラウザが入らない**ため、H1（D6・D7・E10 が赤）・H4（F5 の向き）・
H5（スライドアウトの見え方）・M3（行の寸法と「…」）は **DOM・CSS・トークンからの演算による結論で、
ブラウザでの実測ではない**。便2.5 の審査では同じやり方で **両方向に外した実例**がある
（`docs/handoff/toolbar-series-name-full-width/review-opus.md` の「CI 1回目の結果」: B1 は当たり・B7c は外れ）。
**CI の1回目でここが想定どおりかを必ず確認する**。

M6 の「何分増えるか」も未測。測ったのは件数（807）・project 数（3）・持ち時間（15分）だけ。

---

## r2（Opus・2026-11-01・実装に対する独立審査）: **APPROVE**（HIGH 2件を直したうえで）

審査の対象は実装後の `git diff origin/main...HEAD`（PR #4983）。CI は process-artifacts gate
（PR 本文の GO記録が未記入）以外すべて緑で、画面検査（内部）は **756 passed / 78 skipped / 失敗0**（13.6分）。
新設の27実行（9宣言×3 project）はすべて1回目で緑、D6・D7・E10・F5 も緑。

**製品コードの不具合は0件**。r1 の HIGH 5件・MEDIUM 9件はすべて現物で塞がれていることを確認した
（H1＝目印の据え置き `frontend/src/pages/inventory/InventoryFilterDrawer.tsx:476`／H2＝向きの合成
`frontend/src/pages/inventory/InventoryPage.tsx:513-527`＋単体 K9・K11／H3＝自動有効化 同`:508-510`／
H4＝F5 の自前 fixture 化／H5＝中身を常に描き注記だけ `{open && …}`）。

### HIGH（マージ前に直した・2件）

| # | 指摘 | 自分で取った裏（一次情報） | 直し |
|---|---|---|---|
| H-1 | J3 の「在庫・予約」の回は**行まるごと**を `toContainText("在庫")` で見ており、**右の値が更新されていなくても緑**になる | `frontend/src/locales/ja.json` の実値: `inventory.col.offerType` = 「在庫・予約」（行の左ラベル）・`inventory.offerType.in_stock` = 「在庫」（値）。左ラベルだけで "在庫" を含む | 6ケースすべて値の要素 `.comp-multiselect__row-value` を `toHaveText` で完全一致。J8 と同じ locator |
| H-2 | 便3 でドロワーを**常時マウント**にしたため、既存 D6・D7・E10 の `openFilterPanel()` が `toBeVisible()` だけで「開いた」を判定できなくなった（開かなくても緑になる） | `frontend/src/components/Drawer.css:38-45` の閉状態は `transform: translateX(100%)` と `transition` **だけ**。同ファイルを `visibility|display:|opacity|pointer-events` で走査しても `display: flex` の4件しか無く、**閉状態を可視判定から外す規則が存在しない**。画面外に平行移動した要素は bounding box を持つので可視扱い | 3本の `openFilterPanel()` に「本便のパネルだけが持つ `mobileInset` の外枠が `--open` で1件」を足した。既存の D6・D7・E10 の判定そのものは変えていない |

### 併せて直した（追加実行0・既存宣言の中で強くした）

- **M-4**: 形態・在庫予約の**自動有効化**を検査していなかった（J4 の `toBeChecked()` はシリーズの回だけ・
  K10 はシリーズ・K11 は列）。J4 の中で、形態と在庫予約それぞれの前に有効化を一度切ってから選び直す形にした。
- **M-2**: J8 の「行の右の文字が読める」が幅>0・文字数>0 だったため**「…」1文字でも通る**
  （`frontend/src/components/MultiSelect.css:129-138` の `overflow:hidden; text-overflow:ellipsis`）。
  `scrollWidth <= clientWidth`（切れていない）で測る形に替えた。
- 実行数は3ファイルとも据え置き（自分で測った `npx playwright test --list`:
  inventory-filter-subscreen **27**・inventory-toolbar-mercari **69**・inventory-series-sort-panel **63**）。

### 宿題に回した指摘（次便・この便では直さない）

| # | 内容 | 理由 |
|---|---|---|
| M-3 | J6 はパネル**本体**のはみ出しを測っていない（直接の子の右端だけ）。`.comp-drawer-panel` は `overflow: hidden`（`frontend/src/components/Drawer.css:36`）なので深い階層のはみ出しは黙って切られる | 測り方を足すと本当の赤を引く可能性があり、直しが CSS の設計変更に及ぶ。便4 で独立して扱う |
| M-5 | 「24時間以内」などで候補が縮むと、隠しているのに行の右が「なし」と出る（保存値は保持されるので設定は壊れない）。候補は絞り込みでは縮まないが時間の窓では縮む（`backend/app/routers/inventory_offers.py:403` の `age_condition`） | PC も一覧に出ない点は同じ（PC は無言・スマホは「なし」と断言する差）。文言の設計が必要 |
| L-7 | `.comp-multiselect__row:hover` が `@media (hover: hover)` の外（`frontend/src/components/MultiSelect.css:118-120`）＝既知の宿題。便3 で row をスマホで使い始めたため「実際に起きる便」になった | 共通部品の変更（4-10 の境界の外） |
| L-2 | `frontend/src/pages/inventory/InventoryPage.toolbar.test.tsx` の K11 のコメントが `colVisible` の根拠を `:276` と書いているが実体は `:182-184` | 行番号のズレのみ |
| L-1 | `inventory.filterPanel.buttonWithCount`（ja/en）が参照0になった | `check:all` に未使用キー検査は無い。残しても害がない |

### 設計書に書き足したこと（審査 M-1）

自動有効化（PO 決定6）は**4項目の共通スイッチ**を入れるので、利用者が形態だけを選んでも、保存済みの
隠しシリーズ・隠し列・在庫予約が**同時に効き始める**。design.md ⑩ にこの波及を追記した
（コードは PO 決定6 に忠実なので、直すのは設計書の側）。

### 残る不確かさ（r2）

- 実機（本番・Android 幅360）での見え方は未確認: G9（閉じる途中にパネルが空に見えないか）・
  指を離しても `:hover` の色が残らないか（L-7）・行の右が「…」だけになる場面が実在するか。
- H-2 の「閉じたパネルで `toBeVisible()` が真になる」は **CSS の実測（可視性を変える規則が0件）からの帰結**で、
  ブラウザでの実測ではない。CI の緑は「開いた状態で測った結果」なのでこの反証にはならない。
- M-1 の波及が本番の利用者に起きるか（「有効化が切なのに隠し設定が保存されている」利用者の実在）は
  本番データを見ていないため不明。
