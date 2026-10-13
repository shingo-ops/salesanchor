# recon: 確認スライド上段の比較表（review-compare-table）

調査基準: origin/main d39e25183（#4234 マージ後）。worktree: /Users/tanizawashingo/worktrees/salesanchor/release-review-compare-table
パス表記: 以下 `FE` = frontend/src/features/tcg-analysis-review、`C` = frontend/src/components（いずれもリポジトリ相対）。
preflight: `./scripts/dev/executor-preflight.sh` -> 「PREFLIGHT OK — 作業続行可」（警告2件: 本店が origin/main より2052コミット遅れ／本店に台帳以外の未保存25件。生出力 /tmp/CC報告ファイル/preflight-rct.txt）

## 【事実】

### a. 比較表を描く部品
- frontend/src/features/tcg-analysis-review/ReviewItemDrawer.tsx:68-74 `<TwoColumn ratio="1:2" className="review-item-top">` の左が原文 `<section className="review-item-source">`(:69-72)、右が `<ItemComparison item={item} readOnly={true} onJumpToSourceLine={noJump} />`(:73)。
- 比較表の実体は frontend/src/features/tcg-analysis-review/ItemComparison.tsx の関数 `ItemComparison`(:33-37)。JSX は :36 の1行に全部入っている（改行なし）。readOnly=true のときの構造:
  - 根: `<article className="item-comparison item-comparison--readonly">`
  - 見出し行: `<div className="item-head-grid">` = `<h3>Gemini抽出</h3>` ＋ `<div><h3>システム最終結果</h3><span className="inline-badges">{issueBadges.map(StatusBadge)}</span></div>`
  - 項目行: `<div className="aligned-fields">`、`fieldOrder.map` の各項目で Fragment に2つの div: `<div className="comparison-field"><b>{ラベル}</b><span>{gemini値 || 未解決}</span></div>` と `<div className="comparison-field system-field"><b>{ラベル}</b><FinalSystemValue .../></div>`（ラベルを2回出している）
  - 下段: `<div className="item-extra-grid">` = 左 `<div className="comparison-extra">`(原文位置1行) ＋ 右 `<div className="system-extra">`(作品・商品ID・販売状況の3行、`ComparisonMetadataRow` )
  - readOnly=false のときだけ追加される 手動訂正列・メモ欄(:36 後半)。呼び出し元2か所はどちらも readOnly=true。
- 変更前コード（ItemComparison.tsx:36 の readOnly 部分のみ抜粋）:
```
<article className={readOnly ? 'item-comparison item-comparison--readonly' : 'item-comparison'}>
 <div className="item-head-grid"><h3>{t('tcgAnalysisReview.geminiExtraction')}</h3><div><h3>{t('tcgAnalysisReview.systemFinalResult')}</h3><span className="inline-badges">{issueBadges.map((badge) => <StatusBadge key={badge.id} label={badge.label} tone={badge.tone} />)}</span></div>{!readOnly && ...}</div>
 <div className="aligned-fields">{fieldOrder.map(([key, labelKey], index) => <React.Fragment key={key}>
   <div className="comparison-field"><b>{t(labelKey)}</b><span>{rawValue(item.gemini[key]) || t('tcgAnalysisReview.unresolved')}</span></div>
   <div className="comparison-field system-field"><b>{t(labelKey)}</b><FinalSystemValue item={item} keyName={key} /></div>
   {!readOnly && ...manual-field...}</React.Fragment>)}</div>
 <div className="item-extra-grid">
   <div className="comparison-extra"><ComparisonMetadataRow label={t('tcgAnalysisReview.sourcePosition')} value={line ? <button className="line-jump" type="button" onClick={() => onJumpToSourceLine(line)}>{lineSpan}</button> : (rawValue(lineSpan) || t('tcgAnalysisReview.unresolved'))} /></div>
   <div className="system-extra"><ComparisonMetadataRow label={t("superAdmin.supplierQuality.workName")} value={item.system.work_name || t("common.unresolved")} /><ComparisonMetadataRow label={t('tcgAnalysisReview.productId')} value={item.system.product_id || t("common.unresolved")} badges={productIssueBadges} /><ComparisonMetadataRow label={t('tcgAnalysisReview.saleStatus')} value={item.system.status || t("common.unresolved")} /></div>
   {!readOnly && ...manual-actions...}</div></article>
```
- 補助関数（同ファイル）: `fieldOrder`(:22) 6項目 name/quantity/price/unit/state/memo、`SystemValue`(:27)=`<span>値</span><small>補足</small>`、`FinalSystemValue`(:28)、`ComparisonMetadataRow`(:30)=`<div className="comparison-metadata-row"><b>ラベル</b><span className="comparison-metadata-value">値＋バッジ</span></div>`、`sourceLine`(:31)=span から行番号を正規表現で取る。
- 見出し・項目名・値は :36 の1行に直書きで、ファイルは tsx 全体で37行（改行なしの長い行が多い）。

### b. 各行の値の出どころ
- props 型: ItemComparison.tsx:18 `AnalysisReviewItem = { extraction_item_id; source_message_id; provider; raw_text; gemini: Record<string,string>; system: Record<string,string>; review_issues?: string[]; condition_review?; review_reason_details? }`。Drawer 側の型は ReviewItemDrawer.tsx:24 `ReviewDrawerItem = AnalysisReviewItem & { is_v102?; gap_suspect? }`。gemini/system はキー固定の型ではなく `Record<string,string>`。
- 値を作るのはバックエンド backend/app/services/tcg_analysis_review_svc.py:272-296（API の items[] の各要素）:
  - `gemini` キー: name(raw_product_name) / quantity(raw_quantity) / price(raw_price) / unit(raw_unit) / state(raw_state) / memo(raw_memo) / span(`L{line_start}-{line_end}`、line_start が None なら空文字) (:272-280)
  - `system` キー: work_id / work_name / product_id(=product_code) / product_title / product_uuid / pid_resolved / pid_basis / unit(=unit_canonical) / unit_resolved("YES"/"NO") / condition(=condition_canonical) / status / note(=note_ja) / exclusion (:281-295)
- 行ごとの表示（ItemComparison.tsx）:
  | 項目 | Gemini 列 | システム列 |
  |---|---|---|
  | 商品名 name | `item.gemini.name` 空なら「未解決」(:36) | `FinalSystemValue`(:28): `item.gemini.name` 空なら「未解決」。補足は gemini.name が有れば「Gemini抽出値を採用」、無ければ「未解決」 |
  | 数量 quantity | `item.gemini.quantity` | name と同じ分岐（gemini.quantity を表示。補足も同じ） |
  | 単価 price | `item.gemini.price` | 同上（gemini.price） |
  | 単位 unit | `item.gemini.unit` | `system.unit` 空なら「未解決」。補足は `system.unit && system.unit_resolved==='YES'` なら「System確定」、他は「未解決」 |
  | 状態 state | `item.gemini.state` | `system.condition` 空なら「未解決」。補足は condition が有れば「System確定」、無ければ「未解決」 |
  | メモ memo | `item.gemini.memo` | `system.note` が有れば 値＋補足「System確定」、無ければ「なし」（補足なし） |
  | 原文位置 | `item.gemini.span`（:36 下段 `comparison-extra`）。数字が取れれば `<button class="line-jump">` で表示、取れなければ span 文字列、空なら「未解決」 | 行なし（Gemini 側の下段にある） |
  | 作品 | **Gemini 側に対応する値なし** | `item.system.work_name \|\| 未解決`（common.unresolved） |
  | 商品ID | **Gemini 側に対応する値なし** | `item.system.product_id \|\| 未解決` ＋ `productIssueBadges`（商品マスタ未登録バッジ） |
  | 販売状況 | **Gemini 側に対応する値なし** | `item.system.status \|\| 未解決` |
- gemini のキーに work/product_id/status 相当は無い（tcg_analysis_review_svc.py:272-280）。よって作品・商品ID・販売状況はシステム側のみに値がある（事実）。
- 単価ラベルの ja は「単価」（`tcgAnalysisReview.fieldLabels.price`）。

### c. 補足の出どころと i18n キー
- 補足は `SystemValue` の `<small>`(ItemComparison.tsx:27) に出る。条件は上表のとおり(:28)。
- キーと文言（frontend/src/locales/ja.json / en.json で実測）:
  - `tcgAnalysisReview.geminiExtracted` = ja「Gemini抽出値を採用」/ en「Using Gemini extracted value」
  - `tcgAnalysisReview.systemConfirmed` = ja「System確定」/ en「System confirmed」
  - `tcgAnalysisReview.unresolved` = ja「未解決」/ en「Unresolved」
  - `tcgAnalysisReview.none` = ja「なし」/ en「None」
  - `common.unresolved` = ja「未解決」/ en「Unresolved」（下段3行と原文位置以外の空値用に `tcgAnalysisReview.unresolved` と別キーが両方使われている）
- 補足の `<small>` のスタイル: item-comparison-readonly.css:72-78（`display:block`、`--text-secondary`、`--font-2xs`、`margin-top: --space-1`）。

### d. バッジ
- 描画: ItemComparison.tsx:35 `issueBadges = reviewIssueBadges(item.review_issues||[])` を :36 の「システム最終結果」見出しの下 `.inline-badges` に `StatusBadge` で並べる。商品ID 行には別途 `productIssueBadges = productMetadataIssueBadges(...)`（商品マスタ未登録のみ）。
- 部品: frontend/src/features/tcg-analysis-review/components/StatusBadge.tsx:4-7（`.tcg-status-badge--{warning|danger|success}`）、CSS components/status-badge.css:7-17。
- 出どころ: frontend/src/features/tcg-analysis-review/reviewIssues.ts
  - :6 `CONDITION_REVIEW_REQUIRED` のラベルは `conditionReview.needsReview`（ja「要確認」）、visible:true
  - :9 `EXCLUDED` のラベルは `reviewIssues.excluded`（ja「除外対象」）
  - :16 `needsReviewBadge`（id 'NEEDS_REVIEW'）のラベルも `conditionReview.needsReview`（ja「要確認」）
  - :20-27 `reviewIssueBadges` は「個別バッジ（visible のもの）」を並べたあと、`hasNeedsReview(issues)`（:15 の `['PRODUCT_ID_UNRESOLVED','UNIT_UNRESOLVED','EXCLUDED','CONDITION_REVIEW_REQUIRED']` のどれか含む、:18）かつ `hasOnlyPidDerivedReview` でない場合に `needsReviewBadge` を末尾に足す。
  - 例: issues に `CONDITION_REVIEW_REQUIRED` と `EXCLUDED` があると -> 個別バッジ「要確認」「除外対象」＋ まとめバッジ「要確認」の3つ（報告された「要確認・除外対象・要確認」と同じ並び）。ID が別（CONDITION_REVIEW_REQUIRED と NEEDS_REVIEW）で文言キーが同じ（conditionReview.needsReview）であるため。コード上で理由が分かる。
- issues の生成: backend/app/services/tcg_analysis_review_svc.py:299-308 `("CONDITION_REVIEW_REQUIRED" if row.needs_review) + _compute_issues(...)`。つまり CONDITION_REVIEW_REQUIRED が先頭に来る。
- reviewIssues.ts:29-32 のコメント: PRODUCT_ID_UNRESOLVED と PRODUCT_MASTER_UNREGISTERED は backend が同じ条件で両方出すため、アイテム表示では後者のみ（ID未解決は visible:false）。
- ReviewItemDrawer 下段(:90-110)の理由リストは別の仕組み（`review_reason_details`、reviewReasonLabel.ts）で、バッジとは別系統。

### e. ItemComparison の利用箇所（全走査）
`grep -rn "ItemComparison\|item-comparison" frontend/src` の結果:
- 描画している呼び出し元は2か所のみ（どちらも `readOnly={true}`）:
  1. frontend/src/features/tcg-analysis-review/ReviewItemDrawer.tsx:73（`onJumpToSourceLine={noJump}`）。`noJump = () => undefined`(:36)。
  2. frontend/src/features/tcg-analysis-review/SupplierDetailView.tsx:116 `<ItemComparison item={item} readOnly={true} onJumpToSourceLine={jumpToLine} />`（`<section className="supplier-detail-items">` :112 内の `.supplier-detail-item-row` ごと、その下に ConditionReviewPanel と「商品を直す」ボタン）。ここは行番号ジャンプが実際に動く（SourceRawPane と連動）。
- 型 import のみ: ConditionReviewPanel.tsx:6、ProductMasterDrawer.tsx:20、ConditionReviewPanel.test.tsx:6（`AnalysisReviewItem` 型）。型の置き場所が ItemComparison.tsx。
- **V102PostEditModal.tsx は ItemComparison を使っていない**（grep 0件）。使っているのは DataTable（V102PostEditModal.tsx:10, :138, :231）。
- readOnly=false の呼び出しはリポジトリ内に存在しない（grep 結果、描画箇所は上記2つのみ）。manual 列・メモ欄のコードは未使用経路。
- 影響: ItemComparison.tsx/ item-comparison-readonly.css を変えると、ReviewItemDrawer と SupplierDetailView（仕入先詳細）の2画面に同時に効く。SupplierDetailView 側の幅は supplier-detail-view.css（.supplier-detail-items :57, .supplier-detail-item-row :66）で決まる。ストーリー: ReviewItemDrawer.stories.tsx のみ（ItemComparison 単体・SupplierDetailView のストーリーは無い）。
- ストーリー ReviewItemDrawer.stories.tsx:15-25 の item には gemini の span `L12-15`、system の work_name/product_id/status を持つ値が入っている。

### f. 使える既存の金型（frontend/src/components）
- DataTable（C/DataTable.tsx）: `columns: DataTableColumn<T>[]`（key/header/width/ellipsis/sortable/renderCell）、`data`、`rowKey`、`density`('compact'|'default'|'relaxed')、`emptyState`、`className`、`onRowClick`、`selectable`、ページ送り、`rowClassName`。外側は `<div class="comp-table" role="region" aria-label="data table">`(DataTable.tsx:174)。常に `<thead>` のヘッダー行を出す。CSS: DataTable.css（`.comp-table`、`__table` に `min-width: var(--comp-table-min-width)`、`__th`/`__td` は `height: var(--comp-table-row-h-default)`・`padding: 0 var(--comp-table-cell-px)`・`vertical-align: middle`、compact/relaxed で高さ違い、`__row:hover`）。story: C/DataTable.stories.tsx（Default / WithSort / WithSelection / DensityCompact / DensityRelaxed / Ellipsis / EmptyState、title 'Components/DataTable'）。
  - 同 feature での使用例: V102PostEditModal.tsx:138,231（`density="compact"`）、V102PostsTab.tsx、ReviewCsvPreviewTable.tsx 他。
- DescriptionList / KeyValue / 汎用 Table 系の金型: `ls frontend/src/components | grep -i "descri\|keyvalue\|table"` の結果は DataTable のみ。DescriptionList・KeyValue という名前のファイルは無い。`<dl>` を使う components もヒット無し。
- 他に関係しうる金型: TwoColumn（C/TwoColumn.tsx、ratio '1:2'|'1:1'、gap、align）、Stack、Card、Badge（C/Badge.tsx）、Callout、Drawer（size 'wide' = `--drawer-panel-w-wide` 1100px、Drawer.tsx:30-31）。
- feature ローカル部品: FE/components/DataList.tsx（button 行のリスト、`role="list"`）、FE/components/StatusBadge.tsx。DataList は行が `<button>` でクリック選択用。
- ADR-144（docs/adr/ADR-144-ui-component-governance.md）: pages/ の UI は components/ の金型を使う。金型が無い場合は PO 許可を得て新設（:59-64）。
- tokens: `--comparison-label-col-w: 72px;` は frontend/src/tokens.css:450 に定義済み（項目ラベル列幅）。

### g. item-comparison-readonly.css の全セレクタ（frontend/src/features/tcg-analysis-review/item-comparison-readonly.css、89行）
| 行 | セレクタ | 宣言/トークン |
|---|---|---|
| :3 | `.item-comparison--readonly` | `padding: var(--space-3)` |
| :6-12 | `.item-comparison--readonly .item-head-grid`, `.aligned-fields`, `.item-extra-grid` | `display:grid; grid-template-columns: minmax(300px,1fr) minmax(320px,1.05fr); column-gap: var(--space-3)`（直前に stylelint-disable no-descending-specificity コメント） |
| :15-19 | `.comparison-metadata-row` | grid `var(--comparison-label-col-w) minmax(0,1fr)`、`gap: var(--space-2)` |
| :21-24 | `.comparison-metadata-row b` | `color: var(--text-secondary); font-weight: 500` |
| :26-32 | `.comparison-metadata-value` | flex、`min-width:0`、`gap: var(--space-1)`、`align-items:flex-start`、`flex-wrap: wrap` |
| :39-44 | `.review-item-source h3`, `.item-comparison--readonly .item-head-grid h3` | `font-size: var(--font-xs); margin:0; color: var(--text-secondary)` |
| :46-51 | `.item-comparison--readonly .inline-badges` | inline-flex、`gap: var(--space-1)`、wrap、`margin-top: var(--space-1)` |
| :53 | `.item-comparison--readonly .aligned-fields` | `align-items: stretch` |
| :56-64 | `.item-comparison--readonly .comparison-field` | grid `var(--comparison-label-col-w) minmax(0,1fr)`、`gap: var(--space-2)`、`min-height: var(--space-10)`、`padding: var(--space-2) 0`、`border-bottom: 1px solid var(--border)`、`white-space: pre-wrap` |
| :66-70 | `.comparison-field b`, `.comparison-extra b` | `color: var(--text-secondary); font-weight: 500` |
| :72-78 | `.comparison-field small`, `.comparison-extra small` | `display:block; color: var(--text-secondary); font-size: var(--font-2xs); margin-top: var(--space-1)` |
| :81 | `.item-extra-grid` | `padding-top: var(--space-2)` |
| :83-87 | `.item-comparison--readonly .comparison-extra` | grid `var(--comparison-label-col-w) minmax(0,1fr)`、`gap: var(--space-2)` |
| :89 | `.item-comparison--readonly .system-extra` | `display:grid; gap: var(--space-2)` |
- 使用トークン: --space-1/2/3/10、--text-secondary、--border、--font-xs、--font-2xs、--comparison-label-col-w。
- 折れの要因に関するコード上の事実: `.comparison-field` に `white-space: pre-wrap`(:63)。ラベル列は 72px 固定、値列は `minmax(0,1fr)`。2列の最小幅は 300px+320px。`.comparison-metadata-row` / `.comparison-extra` の値列も 72px ラベル列の残り。`.line-jump` は frontend/src/features/tcg-analysis-review/source-raw-pane.css:69-77（`border:0; background:transparent; color: var(--accent); padding:0; text-decoration: underline; font: inherit; text-align:left`）。
- ReviewItemDrawer 側 CSS: frontend/src/features/tcg-analysis-review/review-item-drawer.css:4-6 `.review-item-source { padding: var(--space-3) }`、:8-12 `@media (max-width:1279px) { .comp-two-column.review-item-top { grid-template-columns: 1fr } }`。TwoColumn は ratio "1:2"、Drawer は wide(1100px)。
- 他ファイルが ItemComparison の class を参照: supplier-detail-view.css は `.supplier-detail-item-row` 等（比較表の class 自体は review-drawer-one-line の design.md:113 で item-comparison-readonly.css へ移動済み）。

### h. ADR 検索
- `git grep -il "comparison\|比較" docs/adr/` のヒット23件（ADR-015, 034, 035, 036, 047, 053, 056, 064, 068, 072, 077, 086, 107, 109, 119, 125, 133, 144, 153, 154, 1001, 1004, 1011）。中身を grep した範囲で ItemComparison・Gemini/システム比較表の設計を定めた ADR は未確認（ADR-144 と ADR-154 の該当行は無関係な文脈の「比較」=件数比較・値の比較）。
- docs/adr/FEATURE-INDEX.md に comparison/比較/review/要確認の語を含む行は 0件（grep 結果）。
- 関係する ADR: ADR-144（金型使用・金型が無いときは PO 許可で新設、docs/adr/ADR-144-ui-component-governance.md:31, 59-64）、ADR-027（i18n）。
- 関連 handoff（既存の設計記録）: docs/handoff/review-drawer-one-line/recon.md:21-34、design.md:10-11（KGI-3: Gemini とシステムの同じ項目が同じ高さの行に並ぶ・ラベル列 72px）、:89, :113。

### i. 既存の試験・ストーリーで DOM 構造に依存する箇所
- frontend/src/features/tcg-analysis-review/ReviewItemDrawer.test.tsx:10 `vi.mock("./ItemComparison", () => ({ ItemComparison: () => null }))`。ItemComparison はこの試験で空に差し替えられており、比較表の DOM に依存する箇所は無い。同ファイルが見るのは: ギャップ表示(:37-38)、原文ペイン `[data-range="block"]`(:67)、`data-testid="supplier-drawer"` の class `comp-drawer-panel--wide`(:80)、見出し「Fix」(:86)。
- ItemComparison 専用の試験ファイルは無い（調査時点の `ls` で ItemComparison の試験ファイルは無かった。本作業で frontend/src/features/tcg-analysis-review/ItemComparison.test.tsx を新設）。`grep -rln "comparison-field\|aligned-fields\|item-head-grid" frontend/src` の結果はコンポーネント・CSS 以外に試験ヒット無し（frontend/src/**/*.test.* でヒットなし）。
- ConditionReviewPanel.test.tsx:6 は `AnalysisReviewItem` 型の import のみ。
- 他: frontend の src 外（e2e 等）の ItemComparison 参照は未確認（grep が完了していない）。
- ストーリー: ReviewItemDrawer.stories.tsx（Default 1本、title 'Features/ReviewItemDrawer'）。
- i18n の ja/en キー同一性チェックや grep セルフチェックが CI 側にあることは frontend/CLAUDE.md の記述（未読）による。ここでは未確認。

## 【未確認】
- 実画面で各行の折れが起きる具体的な幅（コードからは要因候補の CSS を列挙しただけ。ブラウザ実測は未実施）。
- SupplierDetailView 上で比較表が置かれる実際の列幅（supplier-detail-view.css の該当ルールは行番号のみ確認、中身は未精読）。
- ja.json/en.json の i18n キー検査・stylelint・ui-governance のうち、今回変更に引っかかる CI チェックの一覧（frontend/CLAUDE.md、docs/ai-agents/executor-checklist.md は今回未読）。
- ADR 23件のうち ItemComparison/比較表に直接言及する本文が有るかは、grep ヒット語の文脈確認を ADR-144/154 以外は未実施。
- `_compute_issues`（tcg_analysis_review_svc.py）の全分岐。EXCLUDED が付く条件は未確認。
