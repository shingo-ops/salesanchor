> この文書は何か（専門用語なしの1行）: 便0aで測った部品台帳の未実測欄の生の測定結果。

親リンク: [../../specs/design-system/migration.md](../../specs/design-system/migration.md)

## 測定前提
`git rev-parse origin/main`

```text
204798341c75d10c217c6941523f5fa75fb1cbe3
```

## 測定結果
### a) ページ骨格・素の<h1>残存
```text
6
frontend/src/pages/schedule/SchedulePageImpl.tsx
frontend/src/pages/register/RegisterPage.tsx
frontend/src/pages/register/RegisterChangeBillingPage.tsx
frontend/src/pages/register/RegisterAddressPage.tsx
frontend/src/pages/company-detail/CompanyDetailPage.tsx
frontend/src/pages/login/LoginPage.tsx
```

### b) 骨格CSS系統数（.page-header と .page-layout-header の別々の定義本数）
```text
25:.page-header {
32:.page-header h2 {
62:.page-layout-header {
82:.page-layout-header-right {
```

### c) カード独自CSS
```text
0
```

### d) 素の<table>（DataTable未使用）
```text
28
frontend/src/pages/invoice-create/InvoiceCreatePage.tsx
frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx
frontend/src/pages/quote-create/QuoteCreatePage.tsx
frontend/src/pages/quote-detail/QuoteDetailPage.tsx
frontend/src/pages/products/ProductsPage.tsx
frontend/src/pages/purchase-orders/PurchaseOrdersFormModal.tsx
frontend/src/pages/inventory/InventoryPage.tsx
frontend/src/pages/admin/InventoryVisibilityPage.tsx
frontend/src/pages/admin/ChannelMastersPage.tsx
frontend/src/pages/company-detail/CompanyContactsTab.tsx
frontend/src/pages/company-detail/CompanyAddressesTab.tsx
frontend/src/pages/commission-settings/CommissionSettingsPage.tsx
frontend/src/pages/staff-reports/StaffReportsPage.tsx
frontend/src/pages/buddy/BuddyPage.tsx
frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx
frontend/src/pages/super-admin/FxRatePage.tsx
frontend/src/pages/super-admin/InventoryOffersPage.tsx
frontend/src/pages/super-admin/DexTab.tsx
frontend/src/pages/super-admin/LLMBudgetTab.tsx
frontend/src/pages/super-admin/DiscordInboundPage.tsx
frontend/src/pages/super-admin/ProductMastersTab.tsx
frontend/src/pages/super-admin/ParseReviewPage.tsx
frontend/src/pages/super-admin/SuppliersAdminTab.tsx
frontend/src/pages/super-admin/TcgSeriesTab.tsx
frontend/src/pages/design-preview/sections/ModalSection.tsx
frontend/src/pages/design-preview/sections/TokenSection.tsx
frontend/src/pages/design-system/DesignSystemPage.tsx
frontend/src/pages/login/LoginPage.tsx
```

### e) 独自badge
```text
0
```

### f) 空状態の独自実装
```text
4
frontend/src/pages/inbox/InboxMessageThread.tsx
frontend/src/pages/super-admin/FxRatePage.tsx
frontend/src/pages/super-admin/DiscordInboundPage.tsx
frontend/src/pages/design-preview/sections/EmptyStateSection.tsx
```
