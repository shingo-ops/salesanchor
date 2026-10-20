# 設計審査: inventory-tabs-attach-table（design.md / recon.md）

- 審査者: Reviewer（Opus）。基準: origin/main 38613d7d7（worktree `release-inventory-tabs-attach-table`）。
- 見たもの: design.md・recon.md と、下に挙げる実物ファイル（file:line はすべてこの worktree で実際に読んだもの）。

## 0. 照合結果（合っていた点）
- Tabs: props は items/activeKey/onChange/variant/size/className のみ（`frontend/src/components/Tabs.tsx:37-44`）。className は role="tablist" の div に付く（:59-69）。underline の線は `.comp-tabs--underline { border-bottom: 1px solid var(--border) }`（`Tabs.css:34-37`）、タブは `margin-bottom:-1px`（`Tabs.css:86-89`。recon の :89-92 は少しずれる）。
- 既存の Tabs 利用で extra/end を渡す箇所は無い（`grep "<Tabs"` の結果: SupplierDetailView:98, InventoryRowDrawer:93/163/208, InventoryView:227, RuleManagementPanel:156, NeedsReviewTabsPanel:204, BuybackByProductPage:249, BuybackPriceHistoryDrawer:109, BuybackProductHistoryDrawer:240, ProductMasterPanel:108, AnalysisDashboardPanel:501, BuybackPricesPage:408, design-preview TabsSection 6か所）。外から `.comp-tabs` の className に複合セレクタを掛けているのは `frontend/src/pages/integrations/CarrierIntegrationPage.css:108-123`（`.carrier-page-tabs.comp-tabs--pill`）だけで、extra/end を渡さない限り className の付き先は変わらないため壊れない。
- トークンはすべて実在: `--comp-tab-h-md`（`frontend/src/tokens.css:535`）、`--comp-tab-px-md`（:539）、`--comp-tab-underline-w`（:542）、`--font-weight-semi`（:31）、`--font-sm`（:15）、`--space-2`（:70）、`--space-5`（:73）、`--accent`（`frontend/src/index.css:33`／dark :237）。GAS 写しにも `--comp-tab-h-md/px-md/underline-w`（`~/CC報告ファイル-keep/inventory-toolbar-two-rows/gas/prod_stage/index.html:32-34`）。
- Select: variant は bare のときだけ受ける（`Select.tsx:54-56`）。value は分割代入されず `...rest` で `<select>` に渡る（`Select.tsx:66-77, 92, 99`）。アプリの「その他」は children 形式（`InventoryPage.tsx:540-552`）、閲覧ページの案は options 形式。どちらも value は rest 経由。
- 閲覧ページ: 絞り込み `r.series !== f.tab`（`viewerFilter.ts:85`）、`TAB_ALL="all"`（:10）、`seriesTabs`（:212-222）、PC Tabs（`InventoryView.tsx:227-236`、size="sm"・count つき）、スマホのセレクト（:215-225）、DataTable（:295）。series は `type_master.name_ja`（`backend/app/services/tcg_distribution_svc.py:331, 364-365`）、アプリの work_code は同じ表の code（`backend/app/routers/products.py:109`）。
- 前例 CSS `frontend/src/pages/buyback-prices/BuybackPricesPage.module.css:40-50` は実在（上角丸 0。上の線は消していない）。
- 既存テスト `InventoryPage.rowdrawer.test.tsx:96` の `expect(screen.queryByRole('tab')).toBeNull()` は実在し、Tabs 化で必ず落ちる（design §6 の対処は妥当）。
- GAS 写しの行番号（index.html:967 `#seriesTabs`、:773-794 CSS、:1243-1275 `buildSeriesTabs`）は実物と一致。

## 1. 指摘

### 指摘1【重大度: 高】アプリのスマホ表示が変わるのに「スマホは変えない」と書いている
- 根拠: アプリのタブ行は isMobile で分けておらず、PC・スマホ共通で描画している（`frontend/src/pages/inventory/InventoryPage.tsx:527-568`。isMobile は :575 の onRowClick にだけ使う）。これを Tabs 金型に置き換える（design §3-5）と、スマホのタブも生ボタン＋`.tabs`（`frontend/src/company-forms.css:40-77`）から Tabs underline/md に変わる。さらに DataTable はスマホで `mobileCards`（:589）によりカード表示になるので、attachedTop をスマホでどう扱うかも決まっていない。
- 一方 design §2 見出し「PC 幅だけ。スマホは変えない」、§4「スマホの表示（アプリ・閲覧ページ・GAS とも）」、K5 は閲覧ページだけを見ている。設計と実装結果が食い違う。
- 修正案: どちらかに決めて書く。推奨は (a)「アプリはスマホも Tabs 金型になる（見た目が変わる）。PO 報告に書く」とし、§2/§4 を直し、K に「アプリ スマホ幅でタブ行が出る・注記が画面幅からはみ出さない（横スクロールが出ない）」を足す。あわせて「DataTable は cardMode のとき attachedTop を無視する」を §3-2 に明記。(b) スマホだけ旧描画を残す案は生ボタンと ui-allow が残るので ADR-144 上おすすめしない。

### 指摘2【重大度: 中】表の外枠を描く要素の記述が実物と違う（frame は枠を描かない）
- 根拠: 外枠（border・角丸）は `.comp-table` だけが持つ（`frontend/src/components/DataTable.css:12-18`）。`.comp-table-frame` は `width:100%` のみ（`DataTable.css:196-198`）。fitToWidth/stickyHeader のときも `.comp-table` クラスはスクロール箱 `wrapperCls`（`DataTable.tsx:214-219`）に付き、frame > fit card > scroll box の中に入る（`DataTable.tsx:471-483`）。カード表示では frame に className が付くが枠は各カード（`DataTable.css:298-301` 付近 `.comp-table__card`）。
- design §3-2 は「fitToWidth のときは外枠を描いている `.comp-table-frame` も…両方に効かせる」と書いており、実装者が frame にもクラスを付けると無意味なクラスが増え、カード表示の className 扱いとも混ざる。
- 修正案: 「`comp-table--attached-top` は `wrapperCls`（`DataTable.tsx:214-219`）にだけ足す。cardMode では付けない」と確定させる。

### 指摘3【重大度: 中】タブ行の下線の重なり方（縦位置）が決まっておらず、K1 では検出できない
- 根拠: タブボタンは `margin-bottom:-1px` で親の下線に重ねる作り（`Tabs.css:86-89`）。design §3-1 は線を外側 `.comp-tabs-bar` に移し内側の線を消す（`.comp-tabs-bar--underline > .comp-tabs--underline { border-bottom:none }`）うえ `align-items:center` にする。内側の `.comp-tabs` は `overflow-x:auto`（`Tabs.css:20-27`）なので縦方向もはみ出しが切られ、選択中の青い下線が外側の線と重ならない（1px 上に浮く／切れる）、また高さ 36px の Select と縦がずれる恐れがある。
- K1 は「タブ行の下端と表の上端の差が 1px 以内」だけで、選択中の下線が外側の線に重なっているかは見ていない。
- 修正案: §3-1 に「`.comp-tabs-bar` は `align-items: flex-end`（または stretch）、Select variant="tab" も `margin-bottom:-1px`、内側 `.comp-tabs` に `min-width:0`」のように縦位置の決めを書く。K1 に「選択中タブ（ボタンと『その他』選択中の両方）の下端 = タブ行の下端 ±1px」を足す。

### 指摘4【重大度: 中】「その他」選択直後はフォーカスが残り、選択中の下線が消える書き方になっている
- 根拠: 既存の `.comp-select__control:focus { border-color: var(--accent); box-shadow: var(--focus-ring-shadow) }`（`frontend/src/components/FormField.css` の「3. フォーカス状態」節、`:focus` 規則）が (0,2,0) で効く。プルダウンで選んだ直後は select にフォーカスが残るため、design §3-3 の「focus: 枠や影は出さず」を `border-color: transparent` で書くと、同時に付く `comp-select--tab-active` の `border-bottom-color: var(--accent)` を消してしまう（詳細度・記述順次第）。stylelint の no-descending-specificity（`Tabs.css:12-17` の注記と同じ縛り）もある。
- 修正案: §3-3 に規則の順と詳細度を明記する。例: `.comp-select__control.comp-select--tab:focus { box-shadow:none; border-top-color/left/right: transparent }`（下線色は触らない）→ その後に `.comp-select__control.comp-select--tab-active`（下線 accent）を置く、など。右余白の「standard と同じだけ足す」も、`calc(var(--comp-tab-px-md) + var(--space-5))` なのか `var(--space-5)` なのかを書く（standard の右余白は `var(--space-5)` のみ、`FormField.css` Select 専用節）。上下の余白 0（基底は `padding: var(--space-2) var(--space-3)`）も明記。

### 指摘5【重大度: 中】MAIN_SERIES の日本語リテラルが ESLint（ADR-027 規則）に掛かり、コミットが止まる
- 根拠: `frontend/scripts/eslint-rules/no-japanese-literal.cjs` が TS の文字列リテラルの日本語を検出する（Literal 節）。`frontend/package.json:56` の lint-staged は `eslint --max-warnings=0` なので warn でも止まる。design §3-6 の `export const MAIN_SERIES = ["ポケモン", "ワンピース", "ドラゴンボール"]` はこれに該当する。テストファイル（K3/K4 の「ホロライブ」等）も同じ。
- 前例: DB 値の照合キーとして無効化している `frontend/src/constants/icons.tsx:167`（`/* eslint-disable local/no-japanese-literal -- DB 定義のカテゴリキー… */`）、テストは `frontend/src/features/tcg-analysis-review/ProductMasterDrawer.test.tsx:1`。
- 修正案: §3-6 に「MAIN_SERIES の行に `// eslint-disable-next-line local/no-japanese-literal -- type_master.name_ja と照合する DB 値（表示文言ではない）` を付ける。テストは先頭に前例と同じ disable を付ける」と書く。ADR-027 上、表示文言ではなく DB 値との照合である理由を一文残す。

### 指摘6【重大度: 低】行番号・件数の小さなずれ
- 根拠（実物）: DataTable の開始は `InventoryPage.tsx:570`（design は :572）。「その他」option の配列は :548（design は :549）。注記の p は :555-567（design は :556-570）。`SelectVariant` の型は `Select.tsx:18`（design の :55-56 は `SelectControlVariantProps`）。Tabs の既存利用は design-preview を含めて 19 か所（design・§4 は「27 か所」）。recon の `Tabs.css:89-92` は実物 :86-89。
- 修正案: 数字を直す。件数は「extra/end を渡す既存箇所は 0」と書けば足りる。

### 指摘7【重大度: 低】「同じ配列の直書き4か所」の4か所目は同じ配列ではない
- 根拠: `InventoryPage.tsx:542` は `["pokemon_booster_box","one_piece","dragon_ball","all"]` で "all" を含む。また `as const` の読取専用タプルに対する `.includes(tt.code)`（string）は TypeScript の型エラーになる。
- 修正案: 「:542 は `activeTab === "all" || (MAIN_TCG_CODES as readonly string[]).includes(activeTab)` に置き換える。includes は `readonly string[]` に広げて使う」と書く。

### 指摘8【重大度: 低】「全て→すべて」の変更はスマホの表示も変える
- 根拠: `viewer.tabAll` はスマホのセレクトでも使う（`InventoryView.tsx:222`）。GAS もスマホ用セレクトの先頭が「全て」（写し `index.html:1269`）。design §3-6/§3-7 で変えると「スマホは変えない」（§4）と食い違う。
- 修正案: 「文言のそろえはスマホにも及ぶ（意図どおり）」と §4 に例外として書く。

### 指摘9【重大度: 低】「その他」の英訳がアプリと違う
- 根拠: アプリは `inventory.filter.otherTypes` = en "Other"（`frontend/src/locales/en.json:1500`）。design §3-6 は viewer `tabOther` の en を "Others"。
- 修正案: "Other" にそろえる（PO 依頼「同じ仕様に」）。

### 指摘10【重大度: 低】§9 の「ESLint/検査の自作タブ禁止」の所在
- 根拠: 自作タブの検出は ESLint ではなく `scripts/check-ui-governance.js:13, 273`（CI `.github/workflows/ui-governance-gate.yml:39`、変更ファイルの増減で見る）。
- 修正案: §9 の守り手を「`scripts/check-ui-governance.js`（ui-governance-gate）」と正しく書く。

### 指摘11【重大度: 低】既定の選択タブの違いを PO 報告に入れる
- 根拠: アプリの既定はポケモン（`InventoryPage.tsx:126`）、閲覧ページは TAB_ALL（`InventoryView.tsx:54`）。design §4 で「変えない」としたが、PO 依頼は「同じ仕様に」。
- 修正案: §6 のリスク表に「既定タブはアプリ=ポケモン、閲覧/GAS=すべてのまま」を足し、PO 報告に載せる（決めは PO）。

## 2. PO 依頼との対応・範囲
- 「タブを表に連結」→ §3-1/3-2/3-5（ただし指摘2・3を直す前提）。「その他を透明・プルダウンは残す」→ §3-3。「閲覧ページと GAS も同じ仕様」→ §3-6/3-7。範囲外の変更（API・DB・migration・deploy.yml）は無い（§4）。
- ADR-144: 生ボタンのタブを Tabs 金型へ戻し ui-allow を外すので整合。ただし金型（Tabs/DataTable/Select）に props を足すので、`docs/CC_UI_GOVERNANCE.md` の「金型作法: Xxx.tsx + Xxx.css + Xxx.stories.tsx」に沿って Storybook 追加（§3-4）があるのは良い。
- ADR-1019 項8: 閲覧ページは同じ金型で作るので整合。
- ADR-027: 指摘5 以外は t() 経由（tabAll/tabOther）で整合。
- デザイントークン: 使う名前はすべて実在（§0）。

## 3. 受入条件の判定可能性
- K1: 数値基準あり。ただし選択中の下線の重なりを見ていない（指摘3）。
- K2: 数値（rgba(0,0,0,0)・background-image≠none）で判定可。フォーカス中の選択中も見ること（指摘4）。
- K3/K4: vitest で判定可（DataTable はモック `InventoryView.test.tsx:7-12` が `data-testid="dt"` を描くので「直前の兄弟」は判定できる）。
- K5: 閲覧ページのみ。アプリのスマホが抜けている（指摘1）。
- K6/K8/K9: 判定可。
- K7: 「写しと差 0」は判定可。5つのタブは PO 目視のみなので、pull した index.html に MAIN_SERIES 3語と「その他」選択欄があることを grep で確かめる手順を足すとよい（低）。

## 4. 結論
指摘1（アプリのスマホが変わるのに変えないと書いている）は設計と結果が食い違うため直してから実装に渡す。指摘2〜5 は Sonnet が迷う／CI・コミットで止まる箇所なので、同時に design.md に書き足すこと。指摘6〜11 は文言の修正で足りる。

VERDICT: REVISE

---

# 2回目（改訂後の design.md を再審査）

## 1回目の指摘への対応
| 指摘 | 判定 | 根拠（改訂後 design.md の行） |
|---|---|---|
| 1 アプリのスマホ | 対応済み | §2 見出し（:12）、3-5「スマホでもこのタブ行を出す」（:68）、`attachedTop={!isMobile}`（:69）、§4（:96）、§6（:115）、K5b（:127） |
| 2 外枠の要素 | 対応済み | 3-2 `wrapperCls` にだけ・カード表示では付けない（:42）。実物 `DataTable.tsx:214-219`・`DataTable.css:12-18, 196-198` と一致 |
| 3 縦位置 | 対応済み | 3-1 `align-items:flex-end`・bar 内のタブ `margin-bottom:0`・`min-width:0`（:33-39）。K1 ②③（:122） |
| 4 フォーカスと選択中 | 対応済み | 3-3 の順 1〜5、focus は border-bottom に触らない、選択中は (0,3,0)（:46-53）。右余白 `var(--space-5)`・上下 0 を明記（:48） |
| 5 日本語リテラル | 対応済み | 3-6 eslint-disable/enable の範囲指定とテストも同様（:75）。前例 `frontend/src/constants/icons.tsx:167` と同じ形 |
| 6 行番号・件数 | 対応済み | `Select.tsx:18`（:45）、:570（:69）、:555-567（:66）、19 か所（:23, :99） |
| 7 配列と型 | 対応済み | `readonly string[]`・"all" を含む2か所の書き方（:62） |
| 8 「すべて」のスマホ波及 | 対応済み | :84、:90、§4 例外（:96） |
| 9 Other | 対応済み | :84 |
| 10 守り手 | 対応済み | §9（:138）`scripts/check-ui-governance.js` |
| 11 既定タブ | 対応済み | §6（:114） |
| K7 grep | 対応済み | :129。GAS 土台の確定（:89）は作業場所 `~/CC報告ファイル-keep/inventory-tabs-attach-table/gas/` に stage・prod_stage・pull_test・pull_prod・verify_test_v30・verify_prod_v20 があることを ls で確認（差 0 の中身そのものは今回再実行していない＝未確認） |

## 新しい指摘（実装時に入れること。設計の作り直しは不要）
### 指摘12【重大度: 低】スマホでは「その他」が他のタブより高くなる
- 根拠: `frontend/src/components/FormField.css:494-500` の `@media (max-width: 767px) { .comp-select__control { min-height: var(--comp-input-height-mobile) } }`。3-3 の tab の種類は `height` だけを決めていて `min-height` を消していないので、アプリのスマホ（改訂で金型の見た目になる）で「その他」だけが高くなり、タブ行が膨らむ。既存の種類 karte/header/tabbar はどれも `min-height: 0`（`FormField.css:201, 222, 240`）。
- 修正案: 3-3 の 1 に `min-height: 0` を足す（実装者が 3-3 の 1 に1行足すだけ）。K5b で、スマホ幅でも「その他」の高さがタブと同じになることを見るとよい。

### 指摘13【重大度: 低】GAS のスマホで新しいタブ行を隠す指定
- 根拠: 今の GAS は `<768px` で `.series-tabs{display:none}`（写し `index.html` の CSS 節 :781-782 付近）でタブ行を隠している。3-7 で comp-tabs-bar 相当の外側の箱を足すと、その箱（下線つき）がスマホで残るおそれがある。
- 修正案: 「外側の箱にも今の `.series-tabs` と同じスマホでの非表示を掛ける」を 3-7 の実装メモにする。K7 の PO 目視にスマホ幅を含める。

### 指摘14【重大度: 低・未確認】stylelint の no-descending-specificity
- 3-1 の `.comp-tabs-bar--underline .comp-tabs--underline .comp-tabs__tab`（0,3,0）は、`Tabs.css:111-113` の hover（0,4,0）より後に置くと stylelint に止められる可能性がある（今回は実行して確かめていない）。K6 の `check:stylelint`（`frontend/package.json` の check:all に含まれる）で検出されるので、止められたら `Tabs.css` 内で hover 規則より前へ動かす。

## 結論（2回目）
1回目の指摘 1〜11 はすべて design.md に反映済み。新しい指摘 12〜14 は低で、実装時に1行足す・置き場所を動かす程度。CI と受入条件（K5b・K6・K7）で検出できるので、設計の差し戻しは不要。

VERDICT: APPROVE
