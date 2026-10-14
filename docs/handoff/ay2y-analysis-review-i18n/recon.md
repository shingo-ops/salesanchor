# AY-2y recon: 商品マスタ引き出し・原文欄の i18n 化と金型移管

調査基準: origin/main f005b623f（fetch 後）。生出力: /tmp/CC報告ファイル/ssot-ay2y/recon/。

## 既存 ADR の検索（着手前）
- ADR-027（i18n 強制）: docs/adr/ADR-027-ui-internationalization.md。docs/adr/FEATURE-INDEX.md:36 が「i18n / ja.json / en.json」の索引。全 UI 文字列は `t()` 経由、ja/en は同一キー。
- ADR-144（UI ガバナンス）: docs/CC_UI_GOVERNANCE.md。生 input・自作ボタンは金型へ。
- `git grep -il "ProductMasterDrawer\|SourceRawPane" -- docs/adr` は 0 件（この2コンポーネントを名指しする ADR は無い）。

## 現在地（事実）
- 対象は frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx と frontend/src/features/tcg-analysis-review/SourceRawPane.tsx。
- 変更前の eslint 警告は 74 件（local/no-japanese-literal。/tmp/CC報告ファイル/ssot-ay2y/recon/eslint.txt、位置一覧 jp-literals.txt）。pre-commit は `--max-warnings=0`（frontend/package.json の lint-staged）なので、両ファイルを触るには警告 0 が前提になる。
- 日本語直書きは ProductMasterDrawer.tsx:57（検索 placeholder）、:161、:166-168 ほか。
- 生 input・textarea・button は frontend/src/features/tcg-analysis-review/supplier-detail-view.css の `.pmd-head button`・`.pmd-field input, textarea`・`.pmd-actions button`・`.pmd-search-candidate button` で見た目を当てていた（pmd-css.txt）。
- frontend/src/features/tcg-analysis-review/source-raw-pane.css の `.source-search` は `grid-template-columns: auto minmax(130px, 1fr) auto auto auto`（:28-34 付近）。`.source-search input { min-width: 0; }` が :48 付近にあった。
- 既存キーの再利用元は ja.json の reviewItem.wizard.register（22 件）・superAdmin.supplierQuality.productAssign（14 件）ほか（keyprefixes.txt）。再利用は common.close・common.previous・common.next、superAdmin.supplierQuality.productAssign.searchPlaceholder・searching・noResults、reviewIssues.excluded に限った（ja 値の一致を確認済み）。
- 手本: frontend/src/features/tcg-analysis-review/ReviewRegisterProductForm.tsx（同じ登録フォームの金型版）、frontend/src/components/Drawer.tsx:150-158（閉じるボタンの X アイコン）。
- 金型: frontend/src/components/TextField.tsx（TextFieldControl）、frontend/src/components/Textarea.tsx（TextareaControl）、frontend/src/components/Button.tsx。

## 未確認として残るもの
- check-ui-governance は pages/ だけが対象で features/ は見ない（既知の残件）。
