---
branch: release/buyback-product-matching
status: IN_PROGRESS
started: 2026-09-24
theme: 買取商品の自社マスタ自動紐付け（ADR-157 Phase 3）
---

## KGI
- 買取商品460件のうち検索ワード登録済み商品が自社マスタに自動紐付けされる（目標: 318件以上）
- 複数候補は管理画面で人間が選択できる
- 紐付け済み商品は一覧画面に自社商品コード・名称が表示される

## 変更ファイル
- migrations/20260924_100000_buyback_product_matching.sql（新規）
- backend/app/services/buyback_scraper/product_matcher.py（新規）
- backend/app/routers/buyback_prices.py（変更）
- backend/app/tasks/buyback_scraper.py（変更）
- frontend/src/pages/buyback-prices/BuybackPendingReviewModal.tsx（新規）
- frontend/src/pages/buyback-prices/BuybackPricesPage.tsx（変更）
- frontend/src/pages/buyback-prices/buybackTypes.ts（変更）
- frontend/src/locales/ja.json（変更）
- frontend/src/locales/en.json（変更）
- scripts/run_all_migrations.sh（変更）
