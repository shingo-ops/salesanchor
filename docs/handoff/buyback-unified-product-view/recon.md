# Recon: 買取相場 統一商品マスタ表示

## 調査対象
- frontend/src/pages/buyback-prices/BuybackPricesPage.tsx:44 — viewMode 初期値 "shop"
- frontend/src/pages/buyback-prices/BuybackPricesPage.tsx:265-304 — ContentToolbar left（検索とプルダウンの配置）
- frontend/src/components/TextField.tsx:1-75 — className prop 受付確認（InputHTMLAttributes 継承）
- frontend/src/components/ContentToolbar.css:2 — flex, nowrap, gap: var(--space-3)
- backend/app/routers/buyback_prices.py:74 — BuybackPriceItem に product_name_ja, match_status あり

## ADR
- ADR-027: i18n 強制
- ADR-144: UIガバナンス
