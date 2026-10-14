<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。 -->
# recon — 要確認スライド: 原文と比較表の上端そろえ(A)・「直す」欄のフォーム化(B)

**仕事名**: review-drawer-align-form  
**日付**: 2026-10-14  
**基準**: origin/main 392966440（worktree 作成時点）  
**対象ADR**: ADR-144 / ADR-067 / ADR-027（下の「ADR 検索」参照）  
**担当**: architect（調査のみ。コードは変更していない）

---

## 1. 事実（観測）

### 1-1. ReviewItemDrawer の構造（A の現在地）

- `frontend/src/features/tcg-analysis-review/ReviewItemDrawer.tsx:65` `<Drawer open onClose title size="wide">`。幅は `frontend/src/components/Drawer.css:48-50` `min(var(--drawer-panel-w-wide), 100vw)`、値は `frontend/src/tokens.css:446,448`（1100px）。本文余白は `frontend/src/components/Drawer.css:85-89`（`padding: var(--space-5) var(--space-6)`）。
- `frontend/src/features/tcg-analysis-review/ReviewItemDrawer.tsx:66` `<Stack gap="4">` の中に、Callout(:67)、上段 TwoColumn(:68-74)、下段「直す」section(:75-113)。
- 上段: `frontend/src/features/tcg-analysis-review/ReviewItemDrawer.tsx:68` `<TwoColumn ratio="1:2" gap="3" align="start" className="review-item-top">`。**align="start"** = 左右の高さは独立（引き伸ばしなし）。
  - 左 (:69-72): `<section className="review-item-source">` > `<h3>原文</h3>`(:70) + `<ShadowSourcePane rawText blockRange />`(:71)。
  - 右 (:73): `<ItemComparison readOnly>` = `frontend/src/features/tcg-analysis-review/ItemComparison.tsx:78-81` の `<article className="item-comparison item-comparison--readonly">` > (バッジがあれば) `<div className="item-comparison__badges">`(:79) + `<DataTable density="compact" className="item-comparison__table">`(:80)。
- ShadowSourcePane の DOM: `frontend/src/features/tcg-analysis-review/ShadowSourcePane.tsx:42` `<section className="shadow-source-pane">` > `<div className="shadow-source-legend">`(:43-54、凡例「ブロックの範囲」。ja.json `frontend/src/locales/ja.json:5151`) + `<div className="shadow-source-lines">`(:55-80、行番号つき本文)。
- **見出し「原文」は枠(.shadow-source-pane)の外**（左 section 内、枠の上）。**凡例は枠の内側の最上段**。**バッジは右の article 内で、DataTable の枠の上**。
- 上端・高さ・余白・align を決める宣言（全件）:

| 場所 | 宣言 | 意味 |
|---|---|---|
| `frontend/src/components/TwoColumn.css:6-8` | `.comp-two-column { display: grid }` | 2列グリッド |
| `frontend/src/components/TwoColumn.css:10` | `.comp-two-column--ratio-1-2 { grid-template-columns: 1fr 2fr }` | 幅比 |
| `frontend/src/components/TwoColumn.css:15` | `.comp-two-column--gap-3 { gap: var(--space-3) }` | 列間 |
| `frontend/src/components/TwoColumn.css:18-20` | `--align-start/center/stretch { align-items: … }`（props 型 `frontend/src/components/TwoColumn.tsx:15`） | 縦位置。今は start |
| `frontend/src/features/tcg-analysis-review/review-item-drawer.css:4-6` | `.review-item-source { padding: var(--space-3) }` | 左ラッパの余白(外側) |
| `frontend/src/features/tcg-analysis-review/review-item-drawer.css:8-12` | `@media (max-width:1279px) { .comp-two-column.review-item-top { grid-template-columns: 1fr } }` | 狭い幅は縦積み |
| `frontend/src/features/tcg-analysis-review/item-comparison-readonly.css:3` | `.item-comparison--readonly { padding: var(--space-3) }` | 右ラッパの余白(外側)。枠なし |
| `frontend/src/features/tcg-analysis-review/item-comparison-readonly.css:26-30` | `.review-item-source h3 { font-size: var(--font-xs); margin: 0; color }` | 見出し「原文」。h3 の高さ分だけ左の枠が下がる |
| `frontend/src/features/tcg-analysis-review/item-comparison-readonly.css:33-38` | `.item-comparison__badges { display:flex; flex-wrap; gap: var(--space-1); margin-bottom: var(--space-2) }` | バッジ行。0件なら div ごと出ない(ItemComparison.tsx:79) |
| `frontend/src/features/tcg-analysis-review/shadow-source-pane.css:3-10` | `.shadow-source-pane { display:flex; flex-direction:column; min-width:0; border:1px solid var(--border); border-radius: var(--radius-md); background }` | **左の枠**(高さ指定なし) |
| `frontend/src/features/tcg-analysis-review/shadow-source-pane.css:12-20` | `.shadow-source-legend { padding: var(--space-2) var(--space-3); border-bottom; font-size: var(--font-xs) … }` | 凡例(枠の内側上段) |
| `frontend/src/features/tcg-analysis-review/shadow-source-pane.css:35-41` | `.shadow-source-lines { --shadow-source-max-h: 320px; max-height: var(--shadow-source-max-h); overflow-y:auto; padding: var(--space-2) 0 }` | **左の高さ上限 320px**(本文のみ。凡例は別) |
| `frontend/src/components/DataTable.css:12-18` | `.comp-table { width:100%; overflow-x:auto; border-radius: var(--comp-table-radius); border:1px solid var(--border) }` | **右の枠** |
| `frontend/src/components/DataTable.css:71-74` | `.comp-table--compact .comp-table__th/.td { height: var(--comp-table-row-h-compact) }` | 行高さ。`frontend/src/tokens.css:523` = 32px |

- 観測される構造上の差（コード上の事実。実画面の px 実測は未実施 → §2 未確認）:
  1. 左: 枠の上に h3 がある(枠の上端 = ラッパ padding + h3 高さ)。右: 枠(DataTable)の上にバッジ行 + margin-bottom がある(枠の上端 = ラッパ padding + バッジ行高 + `--space-2`)。バッジが無い件では右の枠はラッパ padding 直下。つまり**左右の枠の上端は件ごとに変わる**。
  2. 左の高さは「凡例 + min(本文高, 320px)」で、右の高さは「バッジ行 + 10行 × 32px + ヘッダ行」。両者を結ぶ宣言はない(align="start")。
  3. TwoColumn のコメント上、色・枠は持たない(`frontend/src/components/TwoColumn.tsx:8`)。枠は左は ShadowSourcePane、右は DataTable が各自持つ。
- 先行の同系統の前例: V102PostEditModal も同じ並び `<TwoColumn ratio="1:2" gap="3" align="start"><ShadowSourcePane/><Stack>DataTable…</Stack></TwoColumn>`（`frontend/src/features/tcg-analysis-review/V102PostEditModal.tsx:227-240`）。
- 呼び出し元: `frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.tsx:211-215`（ReviewItemDrawer の唯一の利用）。ItemComparison の readOnly 利用は `frontend/src/features/tcg-analysis-review/ReviewItemDrawer.tsx:73` と `frontend/src/features/tcg-analysis-review/SupplierDetailView.tsx:116`。ShadowSourcePane の利用は ReviewItemDrawer と V102PostEditModal の2か所＝CSS を変えるとモーダル側にも効く。

### 1-2. 「直す」欄の今の仕組み(B の現在地)

- 下段 `frontend/src/features/tcg-analysis-review/ReviewItemDrawer.tsx:75-113`: `<section className="review-item-fix">` > h3「直す」(`frontend/src/locales/ja.json:3765`) > `<Stack gap="3">` に 3 つ:
  1. `<ConditionReviewPanel item onRefresh />`(:78) — 状態(condition)専用。
  2. 「修正する」`<Button variant="secondary">`(:79-83、ラベルは `frontend/src/locales/ja.json:2471` `superAdmin.supplierQuality.correctPhase3`)。押すと `isProductDrawerOpen=true`(:80) → `<ProductMasterDrawer>`(:116-125)。
  3. 「確認が必要な理由」section(:84-111): 理由ごとに `reviewReasonLabel`、v102 かつ `ackable !== false` かつ未 ack のとき「このままで良い」ボタン(:94-104)、`gap_suspect_code` のとき GapSuspectNote(:105-107)。
- 「修正する」で開くもの: **モーダルではなく自作の右ドロワー**。`frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:515-531` は `<div className="pmd-backdrop">` + `<aside className="pmd-drawer">`(金型 Drawer/Modal ではない)。CSS は `frontend/src/features/tcg-analysis-review/supplier-detail-view.css:107-135` 付近(`.pmd-drawer`、幅 `--pmd-max-w: 480px`、z-index `--z-modal`)。見出しは日本語直書き 'aria-label="商品マスタメンテナンス"' / '商品マスタ修正' / '閉じる'(:520-523)。
- ProductMasterDrawer の中身は `item.review_issues` で 4 セクションに分岐(`frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:505-512`):
  - `PRODUCT_MASTER_UNREGISTERED` → RegistrationSection(:88-)。項目: 商品種別・作品・メーカー・カテゴリ(SearchSelect、独自部品 :49-)、mark / 日本語名 / 英語名 / 発売日 / 検索キーワード / 除外キーワード(生 `<input>`/`<textarea>` :202-222)。保存: `api.post('/tcg/products', {extraction_item_id, source_message_id, ...values, force})`(:153-)。事前: `GET /tcg/products/registration-form`(:119)、`POST /tcg/products/check-duplicates`(:140)。
  - `PRODUCT_ID_UNRESOLVED` → SearchKeywordSection(:278-)。`GET /tcg/products/search`(:292)、`POST`(:301、保存先パスは未読)。
  - `EXCLUDED` → ExcludedSection(:385-)。
  - それ以外(解決済み) → ProductAssignSection(:401-)。商品検索(生 `<input>` :463)→候補選択→「変更」「確認済みにする」(生 `<button>`)。
  - 同ファイルは生 `<input>`/`<textarea>`/`<button>` を使う(金型未使用)。ReviewItemDrawer 側だけ金型 Button を使う。
- 保存 API(商品の確定): `frontend/src/features/tcg-analysis-review/reviewActions.ts:30-38` `postProductCorrection(item, productUuid)` → `POST /tcg/items/{id}/corrections`、body `{source_message_id, fields:[{field_name:"product_id", system_value: item.system.product_uuid||"", human_value: productUuid}]}`。商品候補: `frontend/src/features/tcg-analysis-review/reviewActions.ts:49-53` `searchProductCandidates` → `GET /tcg/products/search?query=`、`frontend/src/features/tcg-analysis-review/reviewActions.ts:56-59` `searchProductOptions`(value=product_uuid / label=japanese_title)。
- 「このままで良い」: `frontend/src/features/tcg-analysis-review/reviewActions.ts:41-46` `postReviewAck(item, codes)` → `POST /tcg/items/{id}/review-ack` body `{source_message_id, codes}`。呼び出し `frontend/src/features/tcg-analysis-review/ReviewItemDrawer.tsx:47-61`(成功で ackedCodes 追加・Callout「確認済みにしました」・onRefresh)。サーバー側 `backend/app/routers/item_corrections.py:174-200`(`require_super_admin`、codes の検証、保存後 `enqueue_v102_reanalyze`)。
- 状態の確定: `frontend/src/features/tcg-analysis-review/ConditionReviewPanel.tsx:15-92`。`GET /tcg/conditions/review-options`(:37)、`POST /tcg/items/{id}/corrections` に `condition_review:{request_id, expected_review_version, decision:"confirm"|"correct", condition_id}`(:56-60)。部品は金型 `Select`(:81) と `Button`(:84,86)。`condition_review` が無い/対象外なら何も出さない(:43)。
- **バックエンドが受ける「直す」の種類**(`backend/app/routers/item_corrections.py:48-72,123-171`): `fields[].field_name` は任意文字列で受け、v102 の件で検証が入るのは `product_id` のみ(`backend/app/services/v102_human_decisions_svc.py:30` `FIELD_PRODUCT_ID`、`backend/app/routers/item_corrections.py:151-157`)。名前・数量・価格・単位・メモの訂正値をこの画面で保存する専用の API/検証があるかは**未確認**(§2)。
- 既存の編集 UI:
  - ItemComparison の `readOnly=false` 版: `frontend/src/features/tcg-analysis-review/ItemComparison.tsx:84-89`。入力は商品名/数量/価格(生 `<input>` :41)、単位/状態(金型 SelectControl :41)、メモ(金型 TextareaControl :41)。**保存ボタンは `disabled={true}` で固定**(:88)。呼び出し元は `readOnly={false}` を渡す箇所がなく(grep: `ItemComparison` の利用は readOnly 2 か所のみ)、**現在どこからも使われていない死んだ経路**。
  - V102PostEditModal: `frontend/src/features/tcg-analysis-review/V102PostEditModal.tsx:219-243`。金型 Modal(size xl)・DataTable・TextField(size sm)で**行番号(lines)・価格・数量の「書き写し」**を直す。`PUT /tcg/v102/posts/{jobId}/items` body `{source_message_id, items}`(:118-121)。商品の中身(名前・単位・状態・商品ID)は直さない。エラー表示は TextField の `error`(:150,165 付近)。
- 「確認が必要な理由」の仕組み: `item.review_reason_details`(型 `frontend/src/features/tcg-analysis-review/reviewReasonLabel.ts`)を `frontend/src/features/tcg-analysis-review/ReviewItemDrawer.tsx:44,90-110` で列挙。文言 `reviewReasonLabel(t, code)`。出どころ行 `reviewSourceLabel`(:88)。i18n キーは `frontend/src/locales/ja.json:3763-3777`(`reviewItem.*`)。

### 1-3. 金型のフォーム系部品(frontend/src/components/)

- 存在する: TextField / Textarea / Select / AsyncCombobox / CountryCombobox / ChannelTypeCombobox / Button / Callout / Stack / TwoColumn / Card / Modal / Drawer / DataTable / Tabs。共有スタイルは `frontend/src/components/FormField.css`(`.comp-field`、`.comp-field__label` 等。`frontend/src/components/FormField.css:19-40`)。
- **`FormField` という tsx と `FormGrid` は存在しない**(`find frontend/src -iname 'FormGrid*' -o -iname 'FormField.tsx'` 結果なし。FormField.css のみ)。ラベル付き入力は TextField/Select/Textarea の `label` prop で自前で包む(`.comp-field` の flex 縦並び)。
- props:
  - TextField `frontend/src/components/TextField.tsx:21-30,57-103`: label, helperText, error, size(sm|md|lg), fullWidth + 標準 input 属性。`TextFieldControl`(:41)は包みなしの裸 input、variant あり。type は text/email/number/password/tel/url/search/date。
  - Textarea `frontend/src/components/Textarea.tsx:19-28,61-107`: 同じ label/helperText/error/size/fullWidth。`TextareaControl`(:44) textStyle normal|code。
  - Select `frontend/src/components/Select.tsx:21-28,125-170`: options:{value,label,disabled}[]、placeholder、label、helperText、error、size、fullWidth。children モードもあり(`SelectControl`)。
  - AsyncCombobox `frontend/src/components/AsyncCombobox.tsx:25-48`: id, ariaLabel, value(表示文字), placeholder, disabled, loadOptions(query)=>Promise<{value,label}[]>, onSelect(option), minChars(1), debounceMs(300), noResultsText, loadingText, errorText。候補は Portal(body)に描く(表のセルでも切れない、:5-7)。
  - Button `frontend/src/components/Button.tsx:21-33`: variant primary|secondary|ghost|danger|outline|tab, size sm|md|lg, fullWidth, loading, loadingText, iconOnly。
  - Stack `frontend/src/components/Stack.tsx:11-24`: gap '1'..'8'。TwoColumn `frontend/src/components/TwoColumn.tsx:13-26`: ratio '1:2'|'1:1'、gap '2'|'3'|'4'|'6'、align start|center|stretch。Callout `frontend/src/components/Callout.tsx:15-24`: variant warning|info, title, children。
  - `.comp-field` は `margin-bottom: var(--space-4)`(`frontend/src/components/FormField.css:19-24`)。フォームを Stack に入れると余白が二重になる可能性 → 未確認(§2)。
- ガバナンス(`docs/CC_UI_GOVERNANCE.md:7-17,19-27,31-44`): 実装前に `components/` の金型を確認 → あれば必ず使う → 無ければ実装せず止めて報告(PO 許可後に金型を登録)。生 `<select>` と生 `<input type=text/search/省略>` は CI が赤。例外は `ui-allow: <理由> (#<番号>)`(両方必須)。**フォームの組み方(ラベル配置・グリッド・必須表示など)を直接定める記述は無い**(=金型の使用義務のみ)。ADR-144 本文も「金型を使う・無ければ PO 許可で新設」(`docs/adr/ADR-144-ui-component-governance.md:31-64`)。
- 先行の同系統設計: `docs/handoff/review-inline-edit/design.md`(行の中で商品を AsyncCombobox で選び postProductCorrection で保存。**「件を開いた画面の作り直し・ProductMasterDrawer の手作りの部品の置き換えは別の課題」と明記**: 同 design.md 対象外の節)。

### 1-4. 関係する試験・story

- `frontend/src/features/tcg-analysis-review/ReviewItemDrawer.test.tsx:10-12` で ItemComparison / ConditionReviewPanel / ProductMasterDrawer を**モック**。関係するもの: `:55-88` "layout"（原文表示とブロック範囲 `[data-range="block"]`、wide クラス `comp-drawer-panel--wide`、見出し "Fix"）、`:33-53` gap suspect、(ack の試験は本ファイルには無い → 未確認 §2)。CSS の位置関係を検証する試験は無い(jsdom)。
- `frontend/src/features/tcg-analysis-review/ShadowSourcePane.test.tsx`（凡例 `.shadow-source-legend*`、行番号 `.shadow-source-line-no`、`data-range`）。`frontend/src/features/tcg-analysis-review/ItemComparison.test.tsx:64-99`（readOnly: 10 行・バッジコンテナ・jump・title）。`frontend/src/features/tcg-analysis-review/reviewActions.test.ts`、`frontend/src/features/tcg-analysis-review/ConditionReviewPanel.test.tsx`、`frontend/src/features/tcg-analysis-review/V102PostsTab.test.tsx`。
- story: `frontend/src/features/tcg-analysis-review/ReviewItemDrawer.stories.tsx:36-42`（Default 1 本のみ。`condition_review: null`、`ProductMasterDrawer` は実物）。`frontend/src/features/tcg-analysis-review/ItemComparison.stories.tsx`（Default / LongName / Unresolved / NoMemo / WithMemoNote / ProductMasterUnregistered / Width640 / Width960、readOnly: true）。
- ReviewItemDrawer の ja/en キー: `frontend/src/locales/ja.json:3763-3777`、`frontend/src/locales/en.json`（同一キー必須: ADR-027）。

### 1-5. ADR 検索(結果)

- `git grep -il -E "ReviewItemDrawer|ShadowSourcePane|ProductMasterDrawer|review-ack|要確認の商品|needs-review" -- docs/adr` → ヒット 0 件(docs/handoff 配下に前例の recon/design が多数)。`docs/adr/FEATURE-INDEX.md`（61 行）に drawer / review / form / 要確認の項目は無い(i18n=ADR-027 のみ該当)。
- 従う ADR:
  - `docs/adr/ADR-144-ui-component-governance.md` — 金型使用義務。生 input/select 禁止・新設は PO 許可・ui-allow 書式。
  - `docs/adr/ADR-067-design-token-enforcement.md` — 色・余白は var() のトークン。コンポーネント固有トークンは先頭で宣言(shadow-source-pane.css:36 の前例)。
  - `docs/adr/ADR-027-ui-internationalization.md` — 全 UI 文字列 t()・ja/en 同一キー。
  - ADR-137 は `docs/adr/` に同番号が 3 ファイル(fedex-etd / nginx / v-company-stats)。**「Adaptive Shell」の ADR 本体ファイルは無く**、`docs/adr/ADR-140-mobile-nav-bottom-tabs.md:9` の関連欄に名前が出るのみ(本体の所在は未確認 §2)。
  - 関連する過去の作業記録: `docs/handoff/review-drawer-one-line/recon.md`・`docs/handoff/review-drawer-one-line/design.md`（この Drawer を 3 列→TwoColumn 化した作業）、`docs/handoff/review-compare-table/design.md`、`docs/handoff/review-inline-edit/design.md`、`docs/handoff/parity03-product-master-drawer-fe/design.md`。

---

## 2. 未確認(推測で埋めていない)

| # | 未確認 | 解消方法 | 状態 |
|---|---|---|---|
| 1 | 実画面の左右の枠の上端・高さが何 px ずれているか(コード上の差は §1-1 のとおり。実測なし) | Storybook(ReviewItemDrawer Default)か本番を Playwright で開き getBoundingClientRect | 未確認 |
| 2 | 右の表の合計高さ(10行×32px+ヘッダ+バッジ)と左の高さ(320px+凡例)のどちらが大きいか。件によって逆転するか | 同上(バッジ有無・原文行数を変えて) | 未確認 |
| 3 | 「直す」に入力させたい項目(名前/数量/価格/単位/状態/メモ のどれを、どの API で保存するか)。POST /corrections が名前などの field_name を v102 件でどう扱うか(`backend/app/services/item_corrections_svc.py` 全体は未読) | PO に項目を確認 → item_corrections_svc.py と v102 の再解析が読む field_name を読む | 未確認 |
| 4 | ProductMasterDrawer の SearchKeywordSection/ExcludedSection の保存先 API(`frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:301` 付近、`:385-`)の詳細 | 該当行を読む | 未確認 |
| 5 | `.comp-field` の `margin-bottom: var(--space-4)`(FormField.css:19-24)を Stack 内に並べたときの余白の二重化の見た目 | Storybook で確認 | 未確認 |
| 6 | 「Adaptive Shell」(ADR-137 と呼ばれている)の本体ドキュメントの場所と、Drawer 内レイアウトへの制約の有無 | `git grep -il "Adaptive Shell"` で追加調査 | 未確認 |
| 7 | ReviewItemDrawer の「このままで良い」の試験の有無 | ReviewRowActions.test.tsx / reviewActions.test.ts を読む | 未確認 |
| 8 | e2e(tests-e2e)に「修正する」「原文」等の UI 文字へ依存する試験があるか(frontend/CLAUDE.md の決まり) | `git grep` で tests-e2e を検索 | 未確認 |

**未解決ゼロ確認**: 解決していない(上表 8 件。設計前に #1・#3 は必須で解消が必要)。

---

## 3. 補足

- B の設計上の分岐(判断材料。結論は設計側): (a) ItemComparison の readOnly=false 版(死んだ経路・保存 disabled 固定・生 input あり)を復活させるか、(b) 金型(TextField/Select/Textarea/AsyncCombobox)で「直す」欄を新規に組むか。`docs/handoff/review-inline-edit/design.md` は ProductMasterDrawer の置き換えを別課題としている。
- 金型にフォーム用のグリッド/行部品が無いため、2 列などのラベル付きグリッドが必要なら ADR-144 に従い「PO 許可 → 金型新設」か、TwoColumn / Stack の組み合わせで足りるかの判断が要る。
- ShadowSourcePane と shadow-source-pane.css は V102PostEditModal と共用。変更範囲に含めるなら両画面で確認が必要。
