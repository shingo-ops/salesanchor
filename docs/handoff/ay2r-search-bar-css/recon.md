# recon: 検索フォームの CSS 整理（AY-2r）

基準: origin/main e0355ceef。実測の生データは docs/handoff/design-system-recon/evidence-20260910/ay2r-before.json・ay2r-after.json。

## 既存 ADR の検索結果
- ADR-027（UI 文字列は t() 経由）: 本便は文字列を触らない。
- ADR-067（デザイントークン強制）: 本便は色・寸法の直値を足さない。
- ADR-144（UI ガバナンス・金型を先確認）: 検索欄は金型 TextField/TextFieldControl を使う。docs/CC_UI_GOVERNANCE.md の範囲内。
- `git grep -i docs/adr/` で `search-bar` の専用 ADR は無し（docs/adr/FEATURE-INDEX.md に該当機能なし）。

## 事実
- /Users/tanizawashingo/worktrees/salesanchor/release-ay2r-search-bar-css/frontend/src/components.css:50-53 `.search-bar, .filter-bar { margin-bottom: var(--space-4) }`。:55 stylelint-disable、:56-65 `.search-bar input, .filter-bar select {…}`、:66 stylelint-enable（変更前）。
- `.filter-bar` を className に使う箇所は 0 件（frontend/src と e2e を git grep。受入は ay2r-acceptance.md）。
- `.search-bar` を使う form は 5 画面: /Users/tanizawashingo/worktrees/salesanchor/release-ay2r-search-bar-css/frontend/src/pages/conditions/ConditionsPage.tsx:394、/Users/tanizawashingo/worktrees/salesanchor/release-ay2r-search-bar-css/frontend/src/pages/product-categories/ProductCategoriesPage.tsx:273、/Users/tanizawashingo/worktrees/salesanchor/release-ay2r-search-bar-css/frontend/src/pages/status-master/StatusMasterPage.tsx:340、/Users/tanizawashingo/worktrees/salesanchor/release-ay2r-search-bar-css/frontend/src/pages/suppliers/SuppliersPage.tsx:158、/Users/tanizawashingo/worktrees/salesanchor/release-ay2r-search-bar-css/frontend/src/pages/units/UnitsPage.tsx:232。各 form は ContentToolbar の left 内（/Users/tanizawashingo/worktrees/salesanchor/release-ay2r-search-bar-css/frontend/src/components/ContentToolbar.tsx:19-20）、中身は `<TextField type="text" size="md" data-testid="<x>-search">` と `<Button type="submit">`。
- `.search-bar input`（詳細度 0,1,1）が金型 `.comp-field__input`（0,1,0）に勝つ。変更前の実測（ay2r-before.json）: radius 4px（金型 6px）、min-width 280px、width 280px。
- 検索欄と検索ボタンの縦中心差は変更前 7.99px（幅375 は 8）。原因は TextField のラッパー `.comp-field` の margin-bottom var(--space-4)=16px（/Users/tanizawashingo/worktrees/salesanchor/release-ay2r-search-bar-css/frontend/src/components/FormField.css:17-22）。
- `.content-toolbar .field-w-sm/md/lg { margin-bottom: 0 }` が既にある（/Users/tanizawashingo/worktrees/salesanchor/release-ay2r-search-bar-css/frontend/src/components/field-size.css:26-28）。TextField の className はラッパー div に付く（/Users/tanizawashingo/worktrees/salesanchor/release-ay2r-search-bar-css/frontend/src/components/TextField.tsx:63-75）。素の `.field-w-md { width: 280px }` は field-size.css:17-19。
- 死にクラス: `search-input` は /Users/tanizawashingo/worktrees/salesanchor/release-ay2r-search-bar-css/frontend/src/pages/contacts/ContactsPage.tsx:287 と /Users/tanizawashingo/worktrees/salesanchor/release-ay2r-search-bar-css/frontend/src/pages/companies/CompaniesPage.tsx:389 に class 文字列のみ（CSS 定義 0 件）。同じ 2 か所の `field-h-md`（min-height 36px）は実高 39.61px より小さく効果なし（docs/specs/design-system/design.md の AY-2p 残件）。
- `--input-select-min-w`（/Users/tanizawashingo/worktrees/salesanchor/release-ay2r-search-bar-css/frontend/src/tokens.css:355）は、`.search-bar input` の削除で参照元が 0 件になる（git grep で tokens.css:355 の定義のみ）。
- docs/specs/design-system/design.md に AY-2q の本番反映記録が無かった。
