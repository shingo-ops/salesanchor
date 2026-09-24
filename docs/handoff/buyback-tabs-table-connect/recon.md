# Recon: カテゴリタブのテーブル連結

## 調査対象
- frontend/src/pages/buyback-prices/BuybackPricesPage.tsx:265-304 — ContentToolbar left にタブ配置（pill variant）
- frontend/src/pages/buyback-prices/BuybackByProductPage.tsx — カテゴリタブ配置
- frontend/src/components/Tabs.tsx — variant: "underline" | "pill"、underline は border-bottom: var(--border)
- frontend/src/components/Tabs.css — underline variant: border-bottom 1px solid var(--border)
- frontend/src/components/DataTable.tsx:65 — className prop 受付確認済み（outer div に適用）
- frontend/src/components/DataTable.css — .comp-table: border-radius: var(--comp-table-radius)(8px)
- frontend/src/pages/buyback-prices/BuybackPricesPage.module.css — 既存の CSS modules ファイル

## ADR
- ADR-144: UIガバナンス（Tabs金型使用必須・自作タブ禁止・色直値禁止）
