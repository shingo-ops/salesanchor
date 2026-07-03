# design-system recon

> この文書は何か(専門用語なしの1行): 理想(design-system)に対して現状がどこにいるかの実測記録。

親: [../../specs/design-system/README.md](../../specs/design-system/README.md)

測定時点: `c736087a0c6855f943455e0d4771779e5371785c`

## KGI① 現在値

### a) プルダウン
```text
      44
frontend/src/components/InventorySearchBar.tsx
frontend/src/components/CompanyContactSelector.tsx
frontend/src/components/PurchaseDetailPanel.tsx
frontend/src/components/ShippingDetailPanel.tsx
frontend/src/components/CommissionPanel.tsx
frontend/src/components/Select.tsx
frontend/src/pages/bots/BotsPage.tsx
frontend/src/pages/schedule/ScheduleSettingsPage.tsx
frontend/src/pages/schedule/SchedulePageImpl.tsx
frontend/src/pages/products/ProductsPage.tsx
frontend/src/pages/products/ProductEditPage.tsx
frontend/src/pages/inbox/InboxMessageThread.tsx
frontend/src/pages/inbox/InboxKartePanel.tsx
frontend/src/pages/inbox/InboxConversationList.tsx
frontend/src/pages/inbox/InboxPage.tsx
frontend/src/pages/inbox/InboxProfileModal.tsx
frontend/src/pages/inbox/ManualRecordSection.tsx
frontend/src/pages/inbox/InboxSettingsModal.tsx
frontend/src/pages/invoice-create/InvoiceCreatePage.tsx
frontend/src/pages/purchase-orders/PurchaseOrdersPage.tsx
frontend/src/pages/purchase-orders/PurchaseOrdersFormModal.tsx
frontend/src/pages/contacts/ContactsPage.tsx
frontend/src/pages/account-settings/PreferencesSection.tsx
frontend/src/pages/admin/TenantProfilePage.tsx
frontend/src/pages/admin/TenantPolicyPage.tsx
frontend/src/pages/goal-setting/GoalSettingPage.tsx
frontend/src/pages/dashboard/DashboardPage.tsx
frontend/src/pages/integrations/FedexEtdSetupGuide.tsx
frontend/src/pages/integrations/PaypalIntegrationPage.tsx
frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx
frontend/src/pages/super-admin/SupplierParseStatsTab.tsx
frontend/src/pages/super-admin/InventoryOffersPage.tsx
frontend/src/pages/super-admin/DexTab.tsx
frontend/src/pages/super-admin/DiscordInboundPage.tsx
frontend/src/pages/super-admin/ParseReviewPage.tsx
frontend/src/pages/super-admin/TcgSeriesTab.tsx
frontend/src/pages/inventory/InventoryPage.tsx
frontend/src/pages/commission-settings/CommissionSettingsPage.tsx
frontend/src/pages/quote-create/QuoteCreatePage.tsx
frontend/src/pages/company-detail/CompanyBasicTab.tsx
frontend/src/pages/company-detail/CompanyConvLogsTab.tsx
frontend/src/pages/orders/OrdersFormModal.tsx
frontend/src/pages/orders/OrdersFilterBar.tsx
frontend/src/pages/companies/CompaniesPage.tsx
---
CompanyContactSelector.stories.tsx
CompanyContactSelector.tsx
Select.stories.tsx
Select.tsx
```

### b) 検索欄
```text
       6
frontend/src/pages/super-admin/InventoryOffersPage.tsx
frontend/src/pages/super-admin/ProductMastersTab.tsx
frontend/src/pages/super-admin/SuppliersAdminTab.tsx
frontend/src/pages/inventory/InventoryPage.tsx
frontend/src/pages/orders/OrdersPage.tsx
frontend/src/pages/orders/OrdersFilterBar.tsx
```

### c) ボタン
```text
       4
frontend/src/topbar.css
frontend/src/pages-layout.css
frontend/src/components/Button.css
frontend/src/components.css
```

### d) アイコン
```text
```

## KGI② 現在値

### a) hex色
```text
     249
 187 frontend/src/index.css
  21 frontend/src/features/schedule/calendars.config.ts
  13 frontend/src/pages/roles/RolesPage.tsx
   6 frontend/src/components/CompanyContactSelector.tsx
   4 frontend/src/components/MergeCompanyModal.tsx
   2 frontend/src/pages/inventory/InventoryPage.tsx
   2 frontend/src/pages/integrations/CarrierCredentialForm.tsx
   2 frontend/src/pages/deals/DealsPage.tsx
   2 frontend/src/contexts/UiPrefsContext.tsx
   1 frontend/src/pages/schedule/schedule-owner.ts
   1 frontend/src/pages/inbox/InboxMessageThread.tsx
   1 frontend/src/pages/dashboard/DashboardPage.tsx
   1 frontend/src/pages/company-detail/CompanyDetailPage.tsx
   1 frontend/src/pages/company-detail/CompanyBasicTab.tsx
   1 frontend/src/pages/companies/CompaniesPage.tsx
```

### b) 文字サイズ直書き
```text
       0
```

### c) 余白直書き
```text
      10
   3 frontend/src/pages/inbox/InboxPage.css
   2 frontend/src/pages/schedule.css
   2 frontend/src/pages/design-preview/sections/CardSection.tsx
   2 frontend/src/components/Card.stories.tsx
   1 frontend/src/pages/dashboard/DashboardPage.css
```

### d) 角丸直書き
```text
       0
```

## KGI④ 現在値

### a) ストーリー数
```text
      37
frontend/src/components/FedExRateModal.tsx
frontend/src/components/InventorySearchBar.tsx
frontend/src/components/OrderFinancialPanel.tsx
frontend/src/components/InventoryPicker.tsx
frontend/src/components/CommissionPanel.tsx
frontend/src/pages/commissions/CommissionsPage.tsx
frontend/src/pages/bots/BotsPage.tsx
frontend/src/pages/inbox/InboxKartePanel.tsx
frontend/src/pages/inbox/inbox.types.ts
frontend/src/pages/invoice-create/InvoiceCreatePage.tsx
frontend/src/pages/purchase-orders/PurchaseOrdersPage.tsx
frontend/src/pages/purchase-orders/PurchaseOrdersFormModal.tsx
frontend/src/pages/sales/SalesPage.tsx
frontend/src/pages/invoices/InvoicesPage.tsx
frontend/src/pages/quotes/QuotesPage.tsx
frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx
frontend/src/pages/staff-reports/StaffReportsPage.tsx
frontend/src/pages/deals/DealsPage.tsx
frontend/src/pages/buddy/BuddyPage.tsx
frontend/src/pages/archives/ArchivesPage.tsx
frontend/src/pages/goal-setting/GoalSettingPage.tsx
frontend/src/pages/dashboard/FunnelReasonsPage.tsx
frontend/src/pages/dashboard/PriorityProspectsSection.tsx
frontend/src/pages/dashboard/FunnelRevenuePage.tsx
frontend/src/pages/dashboard/FunnelLeadsPage.tsx
frontend/src/pages/dashboard/FunnelSection.tsx
frontend/src/pages/dashboard/DashboardPage.tsx
frontend/src/pages/dashboard/WeeklyAdvisorSection.tsx
frontend/src/pages/super-admin/FxRatePage.tsx
frontend/src/pages/super-admin/SupplierParseStatsTab.tsx
frontend/src/pages/super-admin/InventoryOffersPage.tsx
frontend/src/pages/super-admin/DiscordInboundPage.tsx
frontend/src/pages/super-admin/ParseReviewPage.tsx
frontend/src/pages/inventory/InventoryPage.tsx
frontend/src/pages/inventory/OwnInventoryPage.tsx
frontend/src/pages/teams/TeamsPage.tsx
frontend/src/pages/commission-settings/CommissionSettingsPage.tsx
frontend/src/pages/quote-create/QuoteCreatePage.tsx
frontend/src/pages/company-detail/CompanyBasicTab.tsx
frontend/src/pages/company-detail/CompanyConvLogsTab.tsx
frontend/src/pages/quote-detail/QuoteDetailPage.tsx
frontend/src/pages/orders/useOrdersState.ts
frontend/src/pages/orders/OrdersTable.tsx
frontend/src/pages/erp/ERPPage.tsx
frontend/src/pages/channels/ChannelsPage.tsx
```

### b) Storybook設定
```text
      45
frontend/src/components/FedExRateModal.tsx
frontend/src/components/InventorySearchBar.tsx
frontend/src/components/OrderFinancialPanel.tsx
frontend/src/components/InventoryPicker.tsx
frontend/src/components/CommissionPanel.tsx
frontend/src/pages/commissions/CommissionsPage.tsx
frontend/src/pages/bots/BotsPage.tsx
frontend/src/pages/inbox/InboxKartePanel.tsx
frontend/src/pages/inbox/inbox.types.ts
frontend/src/pages/invoice-create/InvoiceCreatePage.tsx
frontend/src/pages/purchase-orders/PurchaseOrdersPage.tsx
frontend/src/pages/purchase-orders/PurchaseOrdersFormModal.tsx
frontend/src/pages/sales/SalesPage.tsx
frontend/src/pages/invoices/InvoicesPage.tsx
frontend/src/pages/quotes/QuotesPage.tsx
frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx
frontend/src/pages/staff-reports/StaffReportsPage.tsx
frontend/src/pages/deals/DealsPage.tsx
frontend/src/pages/buddy/BuddyPage.tsx
frontend/src/pages/archives/ArchivesPage.tsx
frontend/src/pages/goal-setting/GoalSettingPage.tsx
frontend/src/pages/dashboard/FunnelReasonsPage.tsx
frontend/src/pages/dashboard/PriorityProspectsSection.tsx
frontend/src/pages/dashboard/FunnelRevenuePage.tsx
frontend/src/pages/dashboard/FunnelLeadsPage.tsx
frontend/src/pages/dashboard/FunnelSection.tsx
frontend/src/pages/dashboard/DashboardPage.tsx
frontend/src/pages/dashboard/WeeklyAdvisorSection.tsx
frontend/src/pages/super-admin/FxRatePage.tsx
frontend/src/pages/super-admin/SupplierParseStatsTab.tsx
frontend/src/pages/super-admin/InventoryOffersPage.tsx
frontend/src/pages/super-admin/DiscordInboundPage.tsx
frontend/src/pages/super-admin/ParseReviewPage.tsx
frontend/src/pages/inventory/InventoryPage.tsx
frontend/src/pages/inventory/OwnInventoryPage.tsx
frontend/src/pages/teams/TeamsPage.tsx
frontend/src/pages/commission-settings/CommissionSettingsPage.tsx
frontend/src/pages/quote-create/QuoteCreatePage.tsx
frontend/src/pages/company-detail/CompanyBasicTab.tsx
frontend/src/pages/company-detail/CompanyConvLogsTab.tsx
frontend/src/pages/quote-detail/QuoteDetailPage.tsx
frontend/src/pages/orders/useOrdersState.ts
frontend/src/pages/orders/OrdersTable.tsx
frontend/src/pages/erp/ERPPage.tsx
frontend/src/pages/channels/ChannelsPage.tsx
```

### c) Storybook設定の有無
```text
      37
main.ts
preview.tsx
```

## KGI⑤ 現在値

```text
design-token-audit.yml
```

## KGI③

未測定。コード変更を伴うため移行計画便で実施する。
