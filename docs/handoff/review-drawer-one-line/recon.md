# 要確認一覧の1行化（作業3）と確認スライドの3列化（作業4）recon — 2026-10-13 Opus

基準: origin/main 47cb55852（`git fetch` 後）。調査の生出力: ~/CC報告ファイル-keep/review-page-20261013/ui-recon-3-4-v2.md（Sonnet 調査・約2040行）。

## ADR 検索
- `git grep -il "DataTable\|Drawer" origin/main -- docs/adr` → ADR-125/138/139/140 のみ（どれも画面固有の利用。部品の仕様を定める ADR なし）。docs/adr/FEATURE-INDEX.md に DataTable/Drawer の項目なし。
- 従う ADR: docs/adr/ADR-144-ui-component-governance.md（金型の新設・拡張は Xxx.tsx＋.css（var() のみ）＋.stories.tsx・PO 許可）、docs/adr/ADR-067-design-token-enforcement.md（色以外のトークンは frontend/src/tokens.css の :root）、docs/adr/ADR-027-ui-internationalization.md（文言は t()・ja/en 同一キー）。
- PO 許可: 2026-10-13「GO #4226 y」の「y」= 金型3件（DataTable の列ごと1行・省略表示／Drawer 幅のトークン化／3列レイアウト）の追加を承認。

## 作業3（表が折れて2行になる）
- frontend/src/components/DataTable.tsx:29-40 `DataTableColumn { key; header; width?; sortable?; renderCell? }`。省略表示の指定なし。
- frontend/src/components/DataTable.tsx:190 width は th の `style={{ width }}` だけ。frontend/src/components/DataTable.tsx:272 td は `<td className="comp-table__td">` で幅・折り返し指定なし。
- frontend/src/components/DataTable.css:46-51 `.comp-table__td { height: var(--comp-table-row-h-default); padding; color; vertical-align: middle }`。white-space 指定なし＝長い文字は折り返す。
- frontend/src/components/DataTable.css:14 表の外枠は `overflow-x: auto`（横にはみ出したら横スクロール）。
- DataTable の利用は 55 ファイル（ui-recon-3-4-v2.md §5）。DataTable の単体試験なし。frontend/src/components/DataTable.stories.tsx あり。
- frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.tsx:111-167 列6本（商品名・仕入先・出どころ・理由・日付・その場で直す）。:24 `INLINE_FIX_COLUMN_WIDTH = "320px"`（直書き）。理由の列は理由を「、」でつなぐ（:130-144）ため長くなる。
- frontend/src/features/tcg-analysis-review/review-row-actions.css:2-8 `.review-row-actions { display:flex; flex-wrap: wrap; … }` → 商品の選択欄と「このままで良い」が折れて2段になる。
- frontend/src/tokens.css:516-518 行の高さ `--comp-table-row-h-default: 44px` 等。:439-440 `--col-width-medium: 200px` `--col-width-wide: 360px`。:188 `--max-width-truncate: 200px`（topbar.css:69 だけが参照）。

## 作業4（行クリック後のスライド）
- frontend/src/features/tcg-analysis-review/ReviewItemDrawer.tsx:61-99 `<Drawer open onClose title>` の中に `<Stack gap="3">` で Callout・`<ItemComparison readOnly onJumpToSourceLine={noJump}>`・ConditionReviewPanel・「商品を直す」ボタン・理由の一覧を縦に並べる。:31-32 「原文ペインを持たない画面なので、行へのジャンプは何もしない」。
- frontend/src/components/Drawer.tsx:22-30 props は open/onClose/title/children/onOpenFullPage?/footer? のみ（幅の指定なし）。
- frontend/src/components/Drawer.css:30 `width: var(--drawer-panel-width, 480px)`。`git grep -n "drawer-panel-width" origin/main -- frontend/src` → この1行だけ＝変数は未定義で常に 480px。:104-108 767px 以下は width:100%。Drawer の利用は 27 ファイル。frontend/src/components/Drawer.stories.tsx あり。Drawer 単体の試験なし。
- frontend/src/features/tcg-analysis-review/ItemComparison.tsx:36 readOnly のとき `.item-head-grid`（見出し「Gemini抽出」「システム最終結果」）・`.aligned-fields`（項目ごとに `comparison-field`＝Gemini、`comparison-field system-field`＝システム）・`.item-extra-grid` を出す。
- frontend/src/features/tcg-analysis-review/item-comparison-readonly.css:3-9 2列 `minmax(300px,1fr) minmax(320px,1.05fr)` → 最小 632px（間隔 12px 込み）。Drawer 480px に入らない。
- 項目の間隔（ラベル 72px 列・最小高さ・下線・pre-wrap）は frontend/src/features/tcg-analysis-review/supplier-detail-view.css:314-369 にあり、すべて `.supplier-detail-items` の下に限定。Drawer は document.body へポータル（Drawer.tsx:114）なので効かない＝PO の言う「文字の間隔がそろっていない」の原因。
- ItemComparison の利用は2か所とも readOnly: ReviewItemDrawer.tsx:64、SupplierDetailView.tsx:116（`<section className="supplier-detail-items">` :112 の中）。
- 72px の直書き: supplier-detail-view.css:338・:365、source-raw-pane.css:82（`.comparison-metadata-row`・全体に効く）。
- 原文: 一覧 API は `raw_text`（メッセージ本文全体）と `gemini.span`（`L{line_start}-{line_end}`）を返す（backend/app/services/tcg_analysis_review_svc.py:260-279）。`strip_raw_text` は既定 false（backend/app/routers/tcg_analysis_review.py:129）で、NeedsReviewTabsPanel.tsx:83-89 は指定しない＝原文は届いている。行番号は1始まり・`\n` 区切り（backend/app/services/tcg_review_sheet_svc.py:57-65 と frontend/src/features/tcg-analysis-review/sourceRawNavigation.ts:3-5 が同じ数え方）。
- 原文の表示部品: frontend/src/features/tcg-analysis-review/ShadowSourcePane.tsx:18-80（props rawText/blockRange/headingRange・行番号つき・blockRange の先頭へ自動スクロール・高さ上限 320px は shadow-source-pane.css:36）。V102PostEditModal.tsx:229 が `<ShadowSourcePane rawText blockRange />`（headingRange なし）で使用中。凡例は常に「ブロックの範囲」「見出しの範囲」の2つを出す（ShadowSourcePane.tsx:43-50）。
- 2列の金型: frontend/src/components/TwoColumn.tsx:13-37（ratio '1:2'|'1:1'・gap・align・className）。TwoColumn.css:10 `1fr 2fr`。V102PostEditModal.tsx:227 が原文＋右側の2列で使用中（同じ並べ方の前例）。
- 幅のトークン: tokens.css:444-445 `--modal-wide-w: 880px` `--modal-xwide-w: 1100px`。:175 `--drawer-width: 300px` はユーザードロワー用（topbar.css:157・DbViewerPanel.css:16）で流用不可。
- 試験: frontend/src/features/tcg-analysis-review/ReviewItemDrawer.test.tsx:10-12 ItemComparison・ConditionReviewPanel・ProductMasterDrawer をモック。
- 文言: ja.json `shadowAccuracy.source.title`「原文」、`tcgAnalysisReview.geminiExtraction`「Gemini抽出」、`tcgAnalysisReview.systemFinalResult`「システム最終結果」。
- Storybook は `../src/**/*.stories.*` を読む（frontend/.storybook/main.ts:9-12）＝features 配下の story も載る。

## 未確認
- 本番画面での実際の折れ方（PO のスクリーンショットなし）。受入は Storybook の実寸測定で行い、本番は PO の目視で最終確認する。
