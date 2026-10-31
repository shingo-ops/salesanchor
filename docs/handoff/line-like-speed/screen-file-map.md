# 135 画面とファイルの対応表（段 0b）

作り方: リポジトリの根で `python3 docs/handoff/line-like-speed/screen-map.py`（読むだけ）。下の表はその出力をそのまま貼ったもの（2026-11-01 Claude Opus・基準 origin/main 1896879cb）。
読むもの: 毎朝の記録の画面の一覧 `tests/prod-check/page-speed-targets.ts`（135 行）× `frontend/src/App.tsx` のルート（入れ子をたどる）→ 画面のファイル。`?section=` の画面は `frontend/src/pages/super-admin/AnalysisRulesPage.tsx` の分岐で描かれる部品のファイルも書く。行き先が別の画面（redirect）は行き先のファイルも書く。ほかの画面は、そのファイルが読み込む別の *Page.tsx（親の中で中身を描く部品）を書く。

## 結果
- 135 行すべてにファイルがある（ファイルが無い行 0）。design.md §3-4 の段 0 の合格線「対応表の 135 行すべてにファイルがある」に合う。
- ファイルの列に出る画面のファイルは 87 本。
- `frontend/src/pages/buyback-prices/BuybackByProductPage.tsx` はルートを持たないが、表の 19 行目（/buyback-prices）の右の列に出る。BuybackPricesPage.tsx:34 で読み、:44 で最初の表示が product、:392-393 で product の時に中身を描く。つまり /buyback-prices を開いた時に最初に描かれる中身。→ 段 3 で /buyback-prices を直す時は、このファイルも相手にする。
  - u1-count.py はこのファイルを N_nofetch_in_file に分ける。ただし実物は BuybackByProductPage.tsx:61-62 で、`api` と `.get` が別の行に分かれてデータを取っている（u1-count.py の正規表現は 1 行の `api.get` だけを数える）。段 3 の前に、このファイルを数え方の取りこぼしとして扱う。
- `frontend/src/pages/badges/BadgesPage.tsx`・`frontend/src/pages/buddy/BuddyPage.tsx` の 2 本は、ルートからも分岐からも画面のファイルからも読まれない（試験 FormActionButtonMigration.test.tsx:6・:8 だけが読む・recon §4 U1）。表に出ない → 段 3 で直す相手にしない。
- 右の列には、ほかに CarrierSetupGuidePage.tsx:14 → ComingSoonPage.tsx（carrier 3 行）と、AnalysisRulesPage.tsx:42 → SupplierExtractionRulesPage.tsx（64 行目）が出る。後者は section=extraction-rules の部品と同じファイル。
- `?section=import`（65 行目）は、ページの分岐に当たる枝が無い。そのため直接開くと、中身の場所に部品が描かれない（横のメニューで押した時だけ `/super-admin/tcg-line-import` へ移る・AnalysisRulesPage.tsx:109-111）。段 1〜3 で直す部品は無い。
- `?section=accuracy-management` の部品は、別ファイルではなく同じファイルの中にある（AnalysisRulesPage.tsx:60）。
- U1 の列は u1-count.py の分け方で、画面のファイルについてだけ書く（`?section=` の部品は *Page.tsx ではないので数えない）。`?section=` の 25 行と行き先が別の画面 3 行の「N_nofetch_in_file」は、取ってくるのが中の部品や行き先だという意味。段 3 で `?section=` を直す時は、右の列の部品のファイルを相手にする。

## u1-count.py の流し直し（段 0b）
基準 origin/main 1896879cb で流した結果: `# total 96 A_clear=62 C_noindicator=3 N_nofetch_in_file=24 X_other_indicator=7`。recon §4 U1 の数（中身を消す 62・このファイルで取らない 24・ほかの印 7・印なし 3）と同じ。

## 表
| # | 画面の道すじ | 種類 | App.tsx の行 | ファイル | U1 | 中で描かれる部品・行き先 |
|---|---|---|---|---|---|---|
| 1 | `/management-center/integrations/fedex/setup-guide` | carrier | App.tsx:168 | frontend/src/pages/integrations/CarrierSetupGuidePage.tsx | N_nofetch_in_file | CarrierSetupGuidePage.tsx:14 で読む → frontend/src/pages/coming-soon/ComingSoonPage.tsx |
| 2 | `/management-center/integrations/dhl/setup-guide` | carrier | App.tsx:168 | frontend/src/pages/integrations/CarrierSetupGuidePage.tsx | N_nofetch_in_file | CarrierSetupGuidePage.tsx:14 で読む → frontend/src/pages/coming-soon/ComingSoonPage.tsx |
| 3 | `/management-center/integrations/ups/setup-guide` | carrier | App.tsx:168 | frontend/src/pages/integrations/CarrierSetupGuidePage.tsx | N_nofetch_in_file | CarrierSetupGuidePage.tsx:14 で読む → frontend/src/pages/coming-soon/ComingSoonPage.tsx |
| 4 | `/` | 固定 | App.tsx:177 | frontend/src/pages/dashboard/DashboardPage.tsx | A_clear |  |
| 5 | `/dashboard/follow-ups` | 固定 | App.tsx:178 | frontend/src/pages/dashboard/FollowUpsPage.tsx | A_clear |  |
| 6 | `/dashboard/leads` | 固定 | App.tsx:179 | frontend/src/pages/dashboard/FunnelLeadsPage.tsx | A_clear |  |
| 7 | `/dashboard/revenue` | 固定 | App.tsx:180 | frontend/src/pages/dashboard/FunnelRevenuePage.tsx | N_nofetch_in_file |  |
| 8 | `/dashboard/reasons` | 固定 | App.tsx:181 | frontend/src/pages/dashboard/FunnelReasonsPage.tsx | A_clear |  |
| 9 | `/goals/settings` | 固定 | App.tsx:182 | frontend/src/pages/goal-setting/GoalSettingPage.tsx | X_other_indicator |  |
| 10 | `/crm/leads/:id/edit` | needs-id | App.tsx:186 | frontend/src/pages/leads/LeadEditPage.tsx | A_clear |  |
| 11 | `/contacts/:id/edit` | needs-id | App.tsx:191 | frontend/src/pages/contacts/ContactEditPage.tsx | A_clear |  |
| 12 | `/lead-chat` | 固定 | App.tsx:195 | frontend/src/pages/inbox/InboxPage.tsx | N_nofetch_in_file |  |
| 13 | `/crm` | redirect | App.tsx:198 | frontend/src/pages/crm/CustomerHubPage.tsx | N_nofetch_in_file | 行き先 /crm/leads → frontend/src/pages/leads/LeadsPage.tsx |
| 14 | `/crm/leads` | 固定 | App.tsx:201 | frontend/src/pages/leads/LeadsPage.tsx | A_clear |  |
| 15 | `/crm/companies` | 固定 | App.tsx:202 | frontend/src/pages/companies/CompaniesPage.tsx | A_clear |  |
| 16 | `/crm/companies/:id` | needs-id | App.tsx:204 | frontend/src/pages/company-detail/CompanyDetailPage.tsx | A_clear |  |
| 17 | `/crm/contacts` | 固定 | App.tsx:205 | frontend/src/pages/contacts/ContactsPage.tsx | A_clear |  |
| 18 | `/crm/archive` | 固定 | App.tsx:206 | frontend/src/pages/archives/ArchivesPage.tsx | A_clear |  |
| 19 | `/buyback-prices` | 固定 | App.tsx:210 | frontend/src/pages/buyback-prices/BuybackPricesPage.tsx | N_nofetch_in_file | BuybackPricesPage.tsx:34 で読む → frontend/src/pages/buyback-prices/BuybackByProductPage.tsx |
| 20 | `/inventory` | 固定 | App.tsx:213 | frontend/src/pages/inventory/InventoryPage.tsx | X_other_indicator |  |
| 21 | `/own-inventory` | 固定 | App.tsx:215 | frontend/src/pages/inventory/OwnInventoryPage.tsx | A_clear |  |
| 22 | `/admin/products/new` | 固定 | App.tsx:217 | frontend/src/pages/products/ProductEditPage.tsx | N_nofetch_in_file |  |
| 23 | `/admin/products/:id/edit` | needs-id | App.tsx:218 | frontend/src/pages/products/ProductEditPage.tsx | N_nofetch_in_file |  |
| 24 | `/admin/products` | 固定 | App.tsx:219 | frontend/src/pages/products/ProductsPage.tsx | A_clear |  |
| 25 | `/quotes/new` | 固定 | App.tsx:222 | frontend/src/pages/quote-create/QuoteCreatePage.tsx | N_nofetch_in_file |  |
| 26 | `/quotes/:id` | needs-id | App.tsx:223 | frontend/src/pages/quote-detail/QuoteDetailPage.tsx | A_clear |  |
| 27 | `/quotes` | 固定 | App.tsx:224 | frontend/src/pages/quotes/QuotesPage.tsx | A_clear |  |
| 28 | `/invoices/new` | 固定 | App.tsx:225 | frontend/src/pages/invoice-create/InvoiceCreatePage.tsx | A_clear |  |
| 29 | `/invoices/:id` | needs-id | App.tsx:226 | frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx | A_clear |  |
| 30 | `/invoices` | 固定 | App.tsx:227 | frontend/src/pages/invoices/InvoicesPage.tsx | A_clear |  |
| 31 | `/reports` | 固定 | App.tsx:230 | frontend/src/pages/staff-reports/StaffReportsPage.tsx | A_clear |  |
| 32 | `/faq` | 固定 | App.tsx:233 | frontend/src/pages/coming-soon/ComingSoonPage.tsx | N_nofetch_in_file |  |
| 33 | `/orders` | 固定 | App.tsx:244 | frontend/src/pages/orders/OrdersPage.tsx | A_clear |  |
| 34 | `/sales` | 固定 | App.tsx:246 | frontend/src/pages/sales/SalesPage.tsx | A_clear |  |
| 35 | `/commissions` | 固定 | App.tsx:247 | frontend/src/pages/commissions/CommissionsPage.tsx | A_clear |  |
| 36 | `/commission-settings` | 固定 | App.tsx:249 | frontend/src/pages/commission-settings/CommissionSettingsPage.tsx | A_clear |  |
| 37 | `/staff` | 固定 | App.tsx:253 | frontend/src/pages/staff/StaffPage.tsx | A_clear |  |
| 38 | `/staff/:id/edit` | needs-id | App.tsx:254 | frontend/src/pages/staff/StaffEditPage.tsx | A_clear |  |
| 39 | `/bots` | 固定 | App.tsx:255 | frontend/src/pages/bots/BotsPage.tsx | A_clear |  |
| 40 | `/bots/:id/edit` | needs-id | App.tsx:256 | frontend/src/pages/bots/BotEditPage.tsx | A_clear |  |
| 41 | `/teams` | 固定 | App.tsx:257 | frontend/src/pages/teams/TeamsPage.tsx | A_clear |  |
| 42 | `/teams/:id/edit` | needs-id | App.tsx:258 | frontend/src/pages/teams/TeamEditPage.tsx | A_clear |  |
| 43 | `/roles` | 固定 | App.tsx:259 | frontend/src/pages/roles/RolesPage.tsx | A_clear |  |
| 44 | `/data` | 固定 | App.tsx:260 | frontend/src/pages/erp/ERPPage.tsx | A_clear |  |
| 45 | `/suppliers` | 固定 | App.tsx:261 | frontend/src/pages/suppliers/SuppliersPage.tsx | A_clear |  |
| 46 | `/suppliers/import` | 固定 | App.tsx:262 | frontend/src/pages/suppliers/SupplierImportPage.tsx | A_clear |  |
| 47 | `/management-center/units/import` | 固定 | App.tsx:263 | frontend/src/pages/units/UnitImportPage.tsx | A_clear |  |
| 48 | `/management-center/conditions/import` | 固定 | App.tsx:264 | frontend/src/pages/conditions/ConditionImportPage.tsx | A_clear |  |
| 49 | `/management-center/status-master/import` | 固定 | App.tsx:265 | frontend/src/pages/status-master/StatusMasterImportPage.tsx | A_clear |  |
| 50 | `/management-center/note-master/import` | 固定 | App.tsx:266 | frontend/src/pages/note-master/NoteMasterImportPage.tsx | A_clear |  |
| 51 | `/management-center/product-categories/import` | 固定 | App.tsx:267 | frontend/src/pages/product-categories/ProductCategoriesImportPage.tsx | A_clear |  |
| 52 | `/suppliers/:id/edit` | needs-id | App.tsx:268 | frontend/src/pages/suppliers/SupplierEditPage.tsx | A_clear |  |
| 53 | `/shifts` | 固定 | App.tsx:269 | frontend/src/pages/shifts/ShiftsPage.tsx | A_clear |  |
| 54 | `/schedule` | 固定 | App.tsx:270 | frontend/src/pages/schedule/SchedulePage.tsx | N_nofetch_in_file |  |
| 55 | `/schedule/settings` | 固定 | App.tsx:271 | frontend/src/pages/schedule/ScheduleSettingsPage.tsx | A_clear |  |
| 56 | `/channels` | 固定 | App.tsx:274 | frontend/src/pages/channels/ChannelsPage.tsx | A_clear |  |
| 57 | `/settings` | 固定 | App.tsx:282 | frontend/src/pages/notifications/NotificationsPage.tsx | A_clear |  |
| 58 | `/account/settings` | 固定 | App.tsx:284 | frontend/src/pages/account-settings/AccountSettingsPage.tsx | N_nofetch_in_file |  |
| 59 | `/templates` | 固定 | App.tsx:287 | frontend/src/pages/coming-soon/ComingSoonPage.tsx | N_nofetch_in_file |  |
| 60 | `/super-admin/tcg-product-master/import` | 固定 | App.tsx:299 | frontend/src/pages/super-admin/TcgProductImportPage.tsx | A_clear |  |
| 61 | `/super-admin/fx-rate` | 固定 | App.tsx:301 | frontend/src/pages/super-admin/FxRatePage.tsx | X_other_indicator |  |
| 62 | `/super-admin/tcg-distribution` | 固定 | App.tsx:306 | frontend/src/pages/super-admin/TcgDistributionPage.tsx | N_nofetch_in_file |  |
| 63 | `/super-admin/tcg-line-import` | 固定 | App.tsx:311 | frontend/src/pages/super-admin/TcgLineImportPage.tsx | X_other_indicator |  |
| 64 | `/super-admin/analysis-rules` | 固定 | App.tsx:316 | frontend/src/pages/super-admin/AnalysisRulesPage.tsx | N_nofetch_in_file | AnalysisRulesPage.tsx:42 で読む → frontend/src/pages/super-admin/SupplierExtractionRulesPage.tsx |
| 65 | `/super-admin/analysis-rules?section=import` | section | App.tsx:316 | frontend/src/pages/super-admin/AnalysisRulesPage.tsx | N_nofetch_in_file | 分岐なし（中身の場所に部品が描かれない） |
| 66 | `/super-admin/analysis-rules?section=accuracy-management` | section | App.tsx:316 | frontend/src/pages/super-admin/AnalysisRulesPage.tsx | N_nofetch_in_file | AnalysisRulesPage.tsx:164 → frontend/src/pages/super-admin/AnalysisRulesPage.tsx:60 |
| 67 | `/super-admin/analysis-rules?section=needs-review` | section | App.tsx:316 | frontend/src/pages/super-admin/AnalysisRulesPage.tsx | N_nofetch_in_file | AnalysisRulesPage.tsx:165 → frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.tsx |
| 68 | `/super-admin/analysis-rules?section=error-log` | section | App.tsx:316 | frontend/src/pages/super-admin/AnalysisRulesPage.tsx | N_nofetch_in_file | AnalysisRulesPage.tsx:166 → frontend/src/pages/super-admin/components/ExtractionErrorLogPanel.tsx |
| 69 | `/super-admin/analysis-rules?section=sold-out-results` | section | App.tsx:316 | frontend/src/pages/super-admin/AnalysisRulesPage.tsx | N_nofetch_in_file | AnalysisRulesPage.tsx:167 → frontend/src/pages/super-admin/components/SoldOutResultsPanel.tsx |
| 70 | `/super-admin/analysis-rules?section=rule-management` | section | App.tsx:316 | frontend/src/pages/super-admin/AnalysisRulesPage.tsx | N_nofetch_in_file | AnalysisRulesPage.tsx:186 → frontend/src/pages/super-admin/components/RuleManagementPanel.tsx |
| 71 | `/super-admin/analysis-rules?section=extraction-rules` | section | App.tsx:316 | frontend/src/pages/super-admin/AnalysisRulesPage.tsx | N_nofetch_in_file | AnalysisRulesPage.tsx:187 → frontend/src/pages/super-admin/SupplierExtractionRulesPage.tsx |
| 72 | `/super-admin/analysis-rules?section=knowledge-aliases` | section | App.tsx:316 | frontend/src/pages/super-admin/AnalysisRulesPage.tsx | N_nofetch_in_file | AnalysisRulesPage.tsx:188 → frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx |
| 73 | `/super-admin/analysis-rules?section=product-master` | section | App.tsx:316 | frontend/src/pages/super-admin/AnalysisRulesPage.tsx | N_nofetch_in_file | AnalysisRulesPage.tsx:168 → frontend/src/pages/super-admin/components/ProductMasterPanel.tsx |
| 74 | `/super-admin/analysis-rules?section=product-categories-master` | section | App.tsx:316 | frontend/src/pages/super-admin/AnalysisRulesPage.tsx | N_nofetch_in_file | AnalysisRulesPage.tsx:169 → frontend/src/pages/super-admin/components/ProductCategoriesMasterPanel.tsx |
| 75 | `/super-admin/analysis-rules?section=product-kinds-master` | section | App.tsx:316 | frontend/src/pages/super-admin/AnalysisRulesPage.tsx | N_nofetch_in_file | AnalysisRulesPage.tsx:170 → frontend/src/pages/super-admin/components/ProductKindsMasterPanel.tsx |
| 76 | `/super-admin/analysis-rules?section=type-master` | section | App.tsx:316 | frontend/src/pages/super-admin/AnalysisRulesPage.tsx | N_nofetch_in_file | AnalysisRulesPage.tsx:171 → frontend/src/pages/super-admin/components/TypeMasterPanel.tsx |
| 77 | `/super-admin/analysis-rules?section=supplier-master` | section | App.tsx:316 | frontend/src/pages/super-admin/AnalysisRulesPage.tsx | N_nofetch_in_file | AnalysisRulesPage.tsx:172 → frontend/src/pages/super-admin/components/SupplierMasterPanel.tsx |
| 78 | `/super-admin/analysis-rules?section=conditions-master` | section | App.tsx:316 | frontend/src/pages/super-admin/AnalysisRulesPage.tsx | N_nofetch_in_file | AnalysisRulesPage.tsx:173 → frontend/src/pages/super-admin/components/ConditionsMasterPanel.tsx |
| 79 | `/super-admin/analysis-rules?section=unit-master` | section | App.tsx:316 | frontend/src/pages/super-admin/AnalysisRulesPage.tsx | N_nofetch_in_file | AnalysisRulesPage.tsx:174 → frontend/src/pages/super-admin/components/UnitMasterPanel.tsx・frontend/src/pages/super-admin/components/UnitIgnorePhrasesPanel.tsx |
| 80 | `/super-admin/analysis-rules?section=note-master` | section | App.tsx:316 | frontend/src/pages/super-admin/AnalysisRulesPage.tsx | N_nofetch_in_file | AnalysisRulesPage.tsx:180 → frontend/src/pages/super-admin/components/NoteMasterPanel.tsx |
| 81 | `/super-admin/analysis-rules?section=product-lines-master` | section | App.tsx:316 | frontend/src/pages/super-admin/AnalysisRulesPage.tsx | N_nofetch_in_file | AnalysisRulesPage.tsx:181 → frontend/src/pages/super-admin/components/ProductLinesMasterPanel.tsx |
| 82 | `/super-admin/analysis-rules?section=product-formats-master` | section | App.tsx:316 | frontend/src/pages/super-admin/AnalysisRulesPage.tsx | N_nofetch_in_file | AnalysisRulesPage.tsx:182 → frontend/src/pages/super-admin/components/ProductFormatsMasterPanel.tsx |
| 83 | `/super-admin/analysis-rules?section=quantity-units-master` | section | App.tsx:316 | frontend/src/pages/super-admin/AnalysisRulesPage.tsx | N_nofetch_in_file | AnalysisRulesPage.tsx:183 → frontend/src/pages/super-admin/components/QuantityUnitsMasterPanel.tsx |
| 84 | `/super-admin/analysis-rules?section=condition-defs-master` | section | App.tsx:316 | frontend/src/pages/super-admin/AnalysisRulesPage.tsx | N_nofetch_in_file | AnalysisRulesPage.tsx:184 → frontend/src/pages/super-admin/components/ConditionDefsMasterPanel.tsx |
| 85 | `/super-admin/analysis-rules?section=weight-classes-master` | section | App.tsx:316 | frontend/src/pages/super-admin/AnalysisRulesPage.tsx | N_nofetch_in_file | AnalysisRulesPage.tsx:185 → frontend/src/pages/super-admin/components/WeightClassesMasterPanel.tsx |
| 86 | `/super-admin/analysis-rules?section=prompt-config` | section | App.tsx:316 | frontend/src/pages/super-admin/AnalysisRulesPage.tsx | N_nofetch_in_file | AnalysisRulesPage.tsx:189 → frontend/src/pages/super-admin/ExtractionPromptConfigTab.tsx |
| 87 | `/super-admin/analysis-rules?section=pipeline-map` | section | App.tsx:316 | frontend/src/pages/super-admin/AnalysisRulesPage.tsx | N_nofetch_in_file | AnalysisRulesPage.tsx:190 → frontend/src/pages/super-admin/components/PipelineMapPanel.tsx |
| 88 | `/super-admin/analysis-rules?section=line-workflow-guide` | section | App.tsx:316 | frontend/src/pages/super-admin/AnalysisRulesPage.tsx | N_nofetch_in_file | AnalysisRulesPage.tsx:191 → frontend/src/pages/super-admin/components/LineWorkflowGuidePanel.tsx |
| 89 | `/super-admin/analysis-rules?section=db-viewer` | section | App.tsx:316 | frontend/src/pages/super-admin/AnalysisRulesPage.tsx | N_nofetch_in_file | AnalysisRulesPage.tsx:194 → frontend/src/pages/super-admin/components/DbViewerPanel.tsx |
| 90 | `/super-admin/supplier-extraction-rules` | 固定 | App.tsx:320 | frontend/src/pages/super-admin/SupplierExtractionRulesPage.tsx | A_clear |  |
| 91 | `/super-admin/masters/suppliers/import` | 固定 | App.tsx:324 | frontend/src/pages/super-admin/SupplierImportPage.tsx | A_clear |  |
| 92 | `/super-admin/masters/units/import` | 固定 | App.tsx:328 | frontend/src/pages/super-admin/UnitImportPage.tsx | A_clear |  |
| 93 | `/super-admin/masters/conditions/import` | 固定 | App.tsx:332 | frontend/src/pages/super-admin/ConditionImportPage.tsx | A_clear |  |
| 94 | `/super-admin/masters/status-master/import` | 固定 | App.tsx:336 | frontend/src/pages/super-admin/StatusMasterImportPage.tsx | A_clear |  |
| 95 | `/super-admin/masters/note-master/import` | 固定 | App.tsx:340 | frontend/src/pages/super-admin/NoteMasterImportPage.tsx | A_clear |  |
| 96 | `/super-admin/masters/product-categories/import` | 固定 | App.tsx:344 | frontend/src/pages/super-admin/ProductCategoriesImportPage.tsx | A_clear |  |
| 97 | `/super-admin/viewers` | 固定 | App.tsx:348 | frontend/src/pages/super-admin/ViewerAccountsPage.tsx | X_other_indicator |  |
| 98 | `/super-admin/viewer-templates` | 固定 | App.tsx:349 | frontend/src/pages/super-admin/ViewerTemplatesPage.tsx | X_other_indicator |  |
| 99 | `/admin` | redirect | App.tsx:351 | frontend/src/pages/admin/AdminHubPage.tsx | N_nofetch_in_file | 行き先 /admin/tenant-profile → frontend/src/pages/admin/TenantProfilePage.tsx |
| 100 | `/admin/tenant-profile` | 固定 | App.tsx:354 | frontend/src/pages/admin/TenantProfilePage.tsx | A_clear |  |
| 101 | `/admin/tenant-policy` | 固定 | App.tsx:356 | frontend/src/pages/admin/TenantPolicyPage.tsx | A_clear |  |
| 102 | `/admin/discord-config` | 固定 | App.tsx:358 | frontend/src/pages/admin/DiscordConfigPage.tsx | X_other_indicator |  |
| 103 | `/admin/discord-announce` | 固定 | App.tsx:360 | frontend/src/pages/admin/DiscordAnnouncePage.tsx | N_nofetch_in_file |  |
| 104 | `/admin/inventory-visibility` | 固定 | App.tsx:362 | frontend/src/pages/admin/InventoryVisibilityPage.tsx | A_clear |  |
| 105 | `/admin/channel-masters` | 固定 | App.tsx:364 | frontend/src/pages/admin/ChannelMastersPage.tsx | A_clear |  |
| 106 | `/design-system` | 固定 | App.tsx:369 | frontend/src/pages/design-system/DesignSystemPage.tsx | N_nofetch_in_file |  |
| 107 | `/design-preview` | 固定 | App.tsx:372 | frontend/src/pages/design-preview/DesignPreviewPage.tsx | N_nofetch_in_file |  |
| 108 | `/management-center` | redirect | App.tsx:375 | frontend/src/pages/management-center/ManagementCenterPage.tsx | N_nofetch_in_file | 行き先 /management-center/staff → frontend/src/pages/staff/StaffPage.tsx |
| 109 | `/management-center/teams` | 固定 | App.tsx:377 | frontend/src/pages/teams/TeamsPage.tsx | A_clear |  |
| 110 | `/management-center/staff` | 固定 | App.tsx:378 | frontend/src/pages/staff/StaffPage.tsx | A_clear |  |
| 111 | `/management-center/shifts` | 固定 | App.tsx:379 | frontend/src/pages/shifts/ShiftsPage.tsx | A_clear |  |
| 112 | `/management-center/roles` | 固定 | App.tsx:380 | frontend/src/pages/roles/RolesPage.tsx | A_clear |  |
| 113 | `/management-center/inventory-visibility` | 固定 | App.tsx:381 | frontend/src/pages/admin/InventoryVisibilityPage.tsx | A_clear |  |
| 114 | `/management-center/commission` | 固定 | App.tsx:382 | frontend/src/pages/commission-settings/CommissionSettingsPage.tsx | A_clear |  |
| 115 | `/management-center/tenant-profile` | 固定 | App.tsx:383 | frontend/src/pages/admin/TenantProfilePage.tsx | A_clear |  |
| 116 | `/management-center/tenant-policy` | 固定 | App.tsx:385 | frontend/src/pages/admin/TenantPolicyPage.tsx | A_clear |  |
| 117 | `/management-center/discord-config` | 固定 | App.tsx:386 | frontend/src/pages/admin/DiscordConfigPage.tsx | X_other_indicator |  |
| 118 | `/management-center/discord-announce` | 固定 | App.tsx:387 | frontend/src/pages/admin/DiscordAnnouncePage.tsx | N_nofetch_in_file |  |
| 119 | `/management-center/channel-masters` | 固定 | App.tsx:388 | frontend/src/pages/admin/ChannelMastersPage.tsx | A_clear |  |
| 120 | `/management-center/channels` | 固定 | App.tsx:389 | frontend/src/pages/channels/ChannelsPage.tsx | A_clear |  |
| 121 | `/management-center/bots` | 固定 | App.tsx:390 | frontend/src/pages/bots/BotsPage.tsx | A_clear |  |
| 122 | `/management-center/suppliers` | 固定 | App.tsx:391 | frontend/src/pages/suppliers/SuppliersPage.tsx | A_clear |  |
| 123 | `/management-center/status-master` | 固定 | App.tsx:392 | frontend/src/pages/status-master/StatusMasterPage.tsx | A_clear |  |
| 124 | `/management-center/conditions` | 固定 | App.tsx:393 | frontend/src/pages/conditions/ConditionsPage.tsx | A_clear |  |
| 125 | `/management-center/product-categories` | 固定 | App.tsx:394 | frontend/src/pages/product-categories/ProductCategoriesPage.tsx | A_clear |  |
| 126 | `/management-center/units` | 固定 | App.tsx:395 | frontend/src/pages/units/UnitsPage.tsx | A_clear |  |
| 127 | `/management-center/note-master` | 固定 | App.tsx:396 | frontend/src/pages/note-master/NoteMasterPage.tsx | A_clear |  |
| 128 | `/management-center/data` | 固定 | App.tsx:397 | frontend/src/pages/erp/ERPPage.tsx | A_clear |  |
| 129 | `/management-center/integrations/google-drive` | 固定 | App.tsx:399 | frontend/src/pages/integrations/GoogleDriveIntegrationPage.tsx | C_noindicator |  |
| 130 | `/management-center/integrations/fedex` | 固定 | App.tsx:400 | frontend/src/pages/integrations/CarrierIntegrationPage.tsx | C_noindicator |  |
| 131 | `/management-center/integrations/dhl` | 固定 | App.tsx:401 | frontend/src/pages/integrations/CarrierIntegrationPage.tsx | C_noindicator |  |
| 132 | `/management-center/integrations/ups` | 固定 | App.tsx:402 | frontend/src/pages/integrations/CarrierIntegrationPage.tsx | C_noindicator |  |
| 133 | `/management-center/integrations/paypal` | 固定 | App.tsx:403 | frontend/src/pages/integrations/PaypalIntegrationPage.tsx | N_nofetch_in_file |  |
| 134 | `/management-center/notifications` | 固定 | App.tsx:404 | frontend/src/pages/notifications/NotificationsPage.tsx | A_clear |  |
| 135 | `/management-center/reports` | 固定 | App.tsx:405 | frontend/src/pages/staff-reports/StaffReportsPage.tsx | A_clear |  |
