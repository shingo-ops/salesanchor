# page-title recon（D1便・gate用証跡）

> この文書は何か（専門用語なしの1行）: ページ題名の現状実測の証跡。正本は docs/specs/design-system/component-ssot/page-title/design.md §1。
親: docs/specs/design-system/component-ssot/page-title/README.md
実測SHA: origin/main 29c8decb58b2c9db255ab93b9e228ebe058970be

- 金型の実体: frontend/src/components/PageLayout.tsx:26 の h2.text-page-title（t(navKey)）。利用63ページ。
- タイトル文字列SSOT: frontend/src/hooks/usePageTitle.ts:15
- 見た目定義: frontend/src/pages-layout.css:149 の .text-page-title
- 生h1/h2の代表例: frontend/src/pages/company-detail/CompanyDetailPage.tsx:150 / frontend/src/pages/super-admin/ParseReviewPage.tsx:382
- 既存ADR検索: git grep -i "page.title" docs/adr/ 済み・該当なし（本便は既存部品の口の追加のみ）
