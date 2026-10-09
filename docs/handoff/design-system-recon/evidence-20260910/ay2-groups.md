# ay2-groups

base HEAD 08f59418c772fab0bed6137e818d5e87de5c91f2（origin/main, worktree release-frontend-textfield-ay2a）。text-like page-side input 360 件。

手法: ax2-applied と同一（postcss + JSX 祖先連鎖の静的解決、ay2-applied.cjs / ay2-css.cjs）。追加: type属性セレクタ・:not(attr/class/state) は input 自身の属性値で静的評価。

シグネチャ = 「祖先まで一致が確定し、かつ読み込まれる規則（file:line selector）」の整列集合 + inline style（リテラルのみ）。祖先が静的に確定できなかった規則（unconfirmed）はシグネチャに含めず、メンバーごとの件数を別掲。

グループ数: 47

## グループ一覧（件数順）

| ID | 件数 | type内訳 | 主selector(シグネチャ全文) | inline style | 主な領域 | unconfirmedを持つ件数 |
|---|---|---|---|---|---|---|
| G01 | 136 | omitted:67 number:23 text:20 email:12 password:5 date:3 dynamic:2 time:2 tel:1 url:1 | `components.css:19 .form-group input`<br>`components.css:30 .form-group input:focus` | なし | pages/staff:21 components:15 pages/leads:15 pages/admin:11 | 14 |
| G02 | 61 | text:38 omitted:12 email:5 number:3 datetime-local:1 dynamic:1 tel:1 | (規則なし = UA既定のみ) | なし | pages/register:41 pages/super-admin:11 pages/admin:3 components/master-list-editor:2 | 15 |
| G03 | 32 | omitted:29 email:2 number:1 | `company-forms.css:100 .form-grid > .form-row input:not([type="checkbox"]):not([type="radio"])`<br>`company-forms.css:113 .form-grid > .form-row input:focus`<br>`company-forms.css:147 .modal-content-wide .form-row input:not([type="checkbox"]):not([type="radio"])`<br>`company-forms.css:163 .modal-content-wide .form-row input:focus` | なし | pages/companies:24 pages/contacts:8 | 0 |
| G04 | 22 | text:11 number:6 email:2 tel:2 date:1 | `pages/inbox/InboxPage.css:1160 .right-panel-field`<br>`pages/inbox/InboxPage.css:1168 .right-panel-field::placeholder`<br>`pages/inbox/InboxPage.css:1169 .right-panel-field:focus` | なし | pages/inbox:22 | 0 |
| G05 | 16 | omitted:15 number:1 | `company-forms.css:100 .form-grid > .form-row input:not([type="checkbox"]):not([type="radio"])`<br>`company-forms.css:113 .form-grid > .form-row input:focus` | なし | pages/company-detail:16 | 0 |
| G06 | 14 | number:7 omitted:5 date:1 url:1 | `company-forms.css:238 .product-edit-form .form-group input:not([type="checkbox"]):not([type="radio"])`<br>`components.css:19 .form-group input`<br>`components.css:30 .form-group input:focus` | なし | pages/products:14 | 0 |
| G07 | 7 | omitted:6 date:1 | `features/tcg-analysis-review/supplier-detail-view.css:244 .pmd-field input` | なし | features/tcg-analysis-review:7 | 1 |
| G08 | 6 | date:2 omitted:2 time:2 | `pages/schedule.css:813 .schedule-input`<br>`pages/schedule.css:822 .schedule-input`<br>`pages/schedule.css:827 .schedule-input:focus` | なし | pages/schedule:6 | 0 |
| G09 | 6 | omitted:4 number:2 | (規則なし = UA既定のみ) | 6件 `style{width:var(--input-width-weight)}` | pages/invoice-create:3 pages/quote-create:3 | 0 |
| G10 | 4 | tel:4 | (規則なし = UA既定のみ) | 4件 `style{flex:1}` | pages/register:4 | 0 |
| G11 | 3 | email:2 password:1 | `components.css:19 .form-group input`<br>`components.css:30 .form-group input:focus`<br>`pages-layout.css:246 .login-card .form-group input`<br>`pages-layout.css:255 .login-card .form-group input:focus` | なし | pages/login:3 | 0 |
| G12 | 3 | search:2 text:1 | `components/field-size.css:15 .field-w-md`<br>`components/field-size.css:22 .content-toolbar .field-w-md`<br>`components/field-size.css:8 .field-h-md` | なし | pages/companies:1 pages/inventory:1 pages/orders:1 | 0 |
| G13 | 3 | text:3 | `features/tcg-distribution/distribution.css:322 .dist-input`<br>`features/tcg-distribution/distribution.css:334 .dist-input:focus`<br>`features/tcg-distribution/distribution.css:340 .dist-input--error ?conditional-class` | なし | features/tcg-distribution:3 | 3 |
| G14 | 2 | text:2 | `components.css:50 .search-bar input`<br>`components/field-size.css:13 .field-w-sm`<br>`components/field-size.css:22 .content-toolbar .field-w-sm`<br>`components/field-size.css:8 .field-h-md` | なし | components/master-list-editor:1 pages/products:1 | 1 |
| G15 | 2 | date:2 | `pages/dashboard/WeeklyAdvisorSection.css:205 .db-weekly-composer-input`<br>`pages/dashboard/WeeklyAdvisorSection.css:216 .db-weekly-composer-input:focus` | なし | pages/dashboard:2 | 2 |
| G16 | 2 | text:2 | (規則なし = UA既定のみ) | 2件 `style{background:var(--bg-primary);border-radius:4px;border:1px solid var(--border-color);color:var(--text-primary);font-size:0.85rem;min-width:200px;padding:0.4rem 0.6rem}` | pages/super-admin:2 | 0 |
| G17 | 2 | text:2 | (規則なし = UA既定のみ) | 2件 `style{border-radius:4px;border:1px solid var(--border);font-size:13px;padding:6px 8px;width:80px}` | components:2 | 0 |
| G18 | 2 | omitted:2 | (規則なし = UA既定のみ) | 2件 `style{color:var(--text-secondary);font-size:var(--font-sm);margin-top:var(--space-1);min-width:var(--input-width-product-name);width:100%}` | pages/invoice-create:1 pages/quote-create:1 | 0 |
| G19 | 2 | omitted:2 | (規則なし = UA既定のみ) | 2件 `style{font-weight:var(--font-weight-semi);min-width:var(--input-width-product-name);width:100%}` | pages/invoice-create:1 pages/quote-create:1 | 0 |
| G20 | 2 | number:2 | (規則なし = UA既定のみ) | 2件 `style{margin-left:var(--space-2);width:var(--input-width-month)}` | pages/commission-settings:1 pages/commissions:1 | 0 |
| G21 | 2 | number:2 | (規則なし = UA既定のみ) | 2件 `style{margin-left:var(--space-2);width:var(--input-width-year)}` | pages/commission-settings:1 pages/commissions:1 | 0 |
| G22 | 2 | omitted:2 | (規則なし = UA既定のみ) | 2件 `style{max-width:100%;width:SEARCH_WIDTH}` | pages/super-admin:2 | 0 |
| G23 | 2 | number:2 | (規則なし = UA既定のみ) | 2件 `style{width:6rem}` | pages/inventory:2 | 0 |
| G24 | 2 | number:2 | (規則なし = UA既定のみ) | 2件 `style{width:7rem}` | pages/inventory:2 | 0 |
| G25 | 2 | number:2 | (規則なし = UA既定のみ) | 2件 `style{width:var(--input-width-qty)}` | pages/invoice-create:1 pages/quote-create:1 | 0 |
| G26 | 2 | number:2 | (規則なし = UA既定のみ) | 2件 `style{width:var(--input-width-year)}` | pages/invoice-create:1 pages/quote-create:1 | 0 |
| G27 | 1 | text:1 | `company-forms.css:147 .modal-content-wide .form-row input:not([type="checkbox"]):not([type="radio"])`<br>`company-forms.css:163 .modal-content-wide .form-row input:focus` | なし | components:1 | 0 |
| G28 | 1 | text:1 | `components.css:19 .form-group input`<br>`components.css:30 .form-group input:focus` | 1件 `style{min-width:var(--min-width-input-sm);padding:var(--space-6px) var(--space-2);width:100%}` | components:1 | 0 |
| G29 | 1 | omitted:1 | `components.css:19 .form-group input`<br>`components.css:30 .form-group input:focus` | 1件 `style{min-width:var(--min-width-input-sm)}` | pages/purchase-orders:1 | 0 |
| G30 | 1 | number:1 | `components.css:19 .form-group input`<br>`components.css:30 .form-group input:focus` | 1件 `style{width:var(--input-width-qty)}` | pages/purchase-orders:1 | 0 |
| G31 | 1 | number:1 | `components.css:19 .form-group input`<br>`components.css:30 .form-group input:focus` | 1件 `style{width:var(--input-width-year)}` | pages/purchase-orders:1 | 0 |
| G32 | 1 | text:1 | `components.css:67 .search-input-field`<br>`components.css:77 .search-input-field::placeholder`<br>`components.css:80 .search-input-field:focus`<br>`pages/inbox/InboxPage.css:116 .inbox-search-input` | なし | pages/inbox:1 | 0 |
| G33 | 1 | text:1 | `components/field-size.css:13 .field-w-sm`<br>`components/field-size.css:22 .content-toolbar .field-w-sm`<br>`components/field-size.css:8 .field-h-md` | なし | pages/contacts:1 | 0 |
| G34 | 1 | omitted:1 | `features/tcg-analysis-review/source-raw-pane.css:48 .source-search input` | なし | features/tcg-analysis-review:1 | 1 |
| G35 | 1 | number:1 | `pages/goal-setting/GoalSettingPage.css:119 .gs-advisor__monthly-input`<br>`pages/goal-setting/GoalSettingPage.css:510 .gs-input`<br>`pages/goal-setting/GoalSettingPage.css:522 .gs-input:focus` | なし | pages/goal-setting:1 | 0 |
| G36 | 1 | number:1 | `pages/goal-setting/GoalSettingPage.css:277 .gs-advisor__metric-input`<br>`pages/goal-setting/GoalSettingPage.css:281 .gs-advisor__metric-input:focus-visible`<br>`pages/goal-setting/GoalSettingPage.css:510 .gs-input`<br>`pages/goal-setting/GoalSettingPage.css:522 .gs-input:focus` | なし | pages/goal-setting:1 | 0 |
| G37 | 1 | number:1 | `pages/goal-setting/GoalSettingPage.css:510 .gs-input`<br>`pages/goal-setting/GoalSettingPage.css:522 .gs-input:focus`<br>`pages/goal-setting/GoalSettingPage.css:527 .gs-input.gs-input-saved ?conditional-class` | なし | pages/goal-setting:1 | 0 |
| G38 | 1 | date:1 | `pages/inbox/InboxPage.css:1160 .right-panel-field`<br>`pages/inbox/InboxPage.css:1168 .right-panel-field::placeholder`<br>`pages/inbox/InboxPage.css:1169 .right-panel-field:focus`<br>`pages/inbox/InboxPage.css:1339 input[type="date"].karte-field-empty:not(:focus)::-webkit-datetime-edit ?conditional-class` | なし | pages/inbox:1 | 0 |
| G39 | 1 | text:1 | `pages/inbox/InboxPage.css:1160 .right-panel-field`<br>`pages/inbox/InboxPage.css:1168 .right-panel-field::placeholder`<br>`pages/inbox/InboxPage.css:1169 .right-panel-field:focus`<br>`pages/inbox/InboxPage.css:1630 .sales-form-other-input` | なし | pages/inbox:1 | 0 |
| G40 | 1 | number:1 | `pages/super-admin/components/AnalysisDashboardPanel.css:75 .analysis-dashboard-window-input` | なし | pages/super-admin:1 | 0 |
| G41 | 1 | text:1 | (規則なし = UA既定のみ) | 1件 `style{background:var(--bg-primary);border-radius:4px;border:1px solid var(--border-color);box-sizing:border-box;color:var(--text-primary);font-size:0.85rem;margin-bottom:0.5rem;padding:0.4rem 0.6rem;width:100%}` | features/tcg-import-review:1 | 0 |
| G42 | 1 | number:1 | (規則なし = UA既定のみ) | 1件 `style{background:var(--bg-primary);border-radius:4px;border:1px solid var(--border-color);color:var(--text-primary);font-size:0.85rem;padding:0.4rem 0.6rem;width:80px}` | pages/super-admin:1 | 0 |
| G43 | 1 | number:1 | (規則なし = UA既定のみ) | 1件 `style{border-radius:4px;border:1px solid var(--border);font-size:13px;padding:6px 8px;width:100px}` | components:1 | 0 |
| G44 | 1 | text:1 | (規則なし = UA既定のみ) | 1件 `style{border-radius:4px;border:1px solid var(--border);font-size:13px;padding:6px 8px;width:160px}` | components:1 | 0 |
| G45 | 1 | omitted:1 | (規則なし = UA既定のみ) | 1件 `style{border-radius:var(--radius-sm);border:1px solid var(--border);flex:1;font-size:var(--font-sm);padding:var(--space-2)}` | pages/invoice-detail:1 | 0 |
| G46 | 1 | omitted:1 | (規則なし = UA既定のみ) | 1件 `style{border-radius:var(--radius-sm);border:1px solid var(--border);padding:var(--space-2);width:100%}` | pages/invoice-detail:1 | 0 |
| G47 | 1 | text:1 | (規則なし = UA既定のみ) | 1件 `style{flex:1;min-width:var(--min-width-input-sm);padding:var(--space-6px) var(--space-2)}` | components:1 | 0 |

## 領域(ディレクトリ)別 input 件数

| 領域 | 件数 | 所属グループ(件数) |
|---|---|---|
| pages/register | 45 | G02(41) G10(4) |
| pages/companies | 28 | G01(3) G03(24) G12(1) |
| pages/inbox | 26 | G02(1) G04(22) G32(1) G38(1) G39(1) |
| components | 22 | G01(15) G17(2) G27(1) G28(1) G43(1) G44(1) G47(1) |
| pages/staff | 21 | G01(21) |
| pages/super-admin | 21 | G01(4) G02(11) G16(2) G22(2) G40(1) G42(1) |
| pages/contacts | 20 | G01(11) G03(8) G33(1) |
| pages/company-detail | 16 | G05(16) |
| pages/leads | 15 | G01(15) |
| pages/products | 15 | G06(14) G14(1) |
| pages/admin | 14 | G01(11) G02(3) |
| pages/account-settings | 10 | G01(10) |
| pages/invoice-create | 10 | G01(3) G09(3) G18(1) G19(1) G25(1) G26(1) |
| pages/quote-create | 10 | G01(3) G09(3) G18(1) G19(1) G25(1) G26(1) |
| features/tcg-analysis-review | 9 | G02(1) G07(7) G34(1) |
| pages/integrations | 9 | G01(9) |
| pages/bots | 7 | G01(7) |
| pages/inventory | 6 | G02(1) G12(1) G23(2) G24(2) |
| pages/schedule | 6 | G08(6) |
| pages/badges | 4 | G01(4) |
| pages/shifts | 4 | G01(4) |
| pages/suppliers | 4 | G01(4) |
| components/master-list-editor | 3 | G02(2) G14(1) |
| features/tcg-distribution | 3 | G13(3) |
| pages/commission-settings | 3 | G02(1) G20(1) G21(1) |
| pages/goal-setting | 3 | G35(1) G36(1) G37(1) |
| pages/login | 3 | G11(3) |
| pages/orders | 3 | G01(2) G12(1) |
| pages/purchase-orders | 3 | G29(1) G30(1) G31(1) |
| pages/teams | 3 | G01(3) |
| pages/buddy | 2 | G01(2) |
| pages/commissions | 2 | G20(1) G21(1) |
| pages/dashboard | 2 | G15(2) |
| pages/invoice-detail | 2 | G45(1) G46(1) |
| pages/notifications | 2 | G01(2) |
| pages/roles | 2 | G01(2) |
| features/tcg-import-review | 1 | G41(1) |
| pages/staff-reports | 1 | G01(1) |

## グループ詳細

### G01（136 件）

- type: {"omitted":67,"number":23,"text":20,"email":12,"password":5,"date":3,"dynamic":2,"time":2,"tel":1,"url":1}
- 適用規則:
  - `components.css:19 .form-group input`
  - `components.css:30 .form-group input:focus`
- 静的className: `input`
- inline style: 0件 
- disabled属性あり: 13件 / unconfirmedを持つ: 14件
- 領域: pages/staff:21, components:15, pages/leads:15, pages/admin:11, pages/contacts:11, pages/account-settings:10, pages/integrations:9, pages/bots:7, pages/badges:4, pages/shifts:4, pages/super-admin:4, pages/suppliers:4, pages/companies:3, pages/invoice-create:3, pages/quote-create:3, pages/teams:3, pages/buddy:2, pages/notifications:2, pages/orders:2, pages/roles:2, pages/staff-reports:1
- ファイル:
  - pages/staff/StaffEditPage.tsx : 9
  - pages/staff/StaffPage.tsx : 8
  - components/ShippingDetailPanel.tsx : 7
  - pages/account-settings/ProfileSection.tsx : 7
  - pages/contacts/ContactEditPage.tsx : 7
  - pages/leads/LeadsPage.tsx : 7
  - pages/admin/TenantProfilePage.tsx : 6
  - components/PurchaseDetailPanel.tsx : 5
  - pages/admin/TenantPolicyPage.tsx : 5
  - pages/leads/LeadEditPage.tsx : 5
  - pages/badges/BadgesPage.tsx : 4
  - pages/bots/BotsPage.tsx : 4
  - pages/contacts/ContactFormFields.tsx : 4
  - pages/shifts/ShiftsPage.tsx : 4
  - pages/staff/StaffFormFields.tsx : 4
  - pages/super-admin/KnowledgeAliasesTab.tsx : 4
  - pages/suppliers/SupplierFormFields.tsx : 4
  - pages/account-settings/SecuritySection.tsx : 3
  - pages/bots/BotFormFields.tsx : 3
  - pages/companies/CompanyFormFields.tsx : 3
  - pages/integrations/CarrierCredentialForm.tsx : 3
  - pages/integrations/FedexLabelValidationTab.tsx : 3
  - pages/invoice-create/InvoiceCreatePage.tsx : 3
  - pages/leads/LeadFormFields.tsx : 3
  - pages/quote-create/QuoteCreatePage.tsx : 3
  - pages/buddy/BuddyPage.tsx : 2
  - pages/integrations/PaypalIntegrationPage.tsx : 2
  - pages/notifications/NotificationsPage.tsx : 2
  - pages/orders/OrdersFormModal.tsx : 2
  - pages/roles/RolesPage.tsx : 2
  - pages/teams/TeamFormFields.tsx : 2
  - components/ChannelTypeCombobox.tsx : 1
  - components/CountryCombobox.tsx : 1
  - components/OrderFinancialPanel.tsx : 1
  - pages/integrations/GoogleDriveIntegrationPage.tsx : 1
  - pages/staff-reports/StaffReportsPage.tsx : 1
  - pages/teams/TeamsPage.tsx : 1
- メンバー(file:line):
  - frontend/src/components/ChannelTypeCombobox.tsx:91 [text] className="input"
  - frontend/src/components/CountryCombobox.tsx:90 [text] className="input"
  - frontend/src/components/OrderFinancialPanel.tsx:223 [number]
  - frontend/src/components/PurchaseDetailPanel.tsx:328 [text]
  - frontend/src/components/PurchaseDetailPanel.tsx:338 [date]
  - frontend/src/components/PurchaseDetailPanel.tsx:361 [dynamic]
  - frontend/src/components/PurchaseDetailPanel.tsx:385 [number]
  - frontend/src/components/PurchaseDetailPanel.tsx:412 [text]
  - frontend/src/components/ShippingDetailPanel.tsx:401 [dynamic]
  - frontend/src/components/ShippingDetailPanel.tsx:425 [text]
  - frontend/src/components/ShippingDetailPanel.tsx:449 [number]
  - frontend/src/components/ShippingDetailPanel.tsx:476 [text]
  - frontend/src/components/ShippingDetailPanel.tsx:487 [number]
  - frontend/src/components/ShippingDetailPanel.tsx:529 [text]
  - frontend/src/components/ShippingDetailPanel.tsx:539 [date]
  - frontend/src/pages/account-settings/ProfileSection.tsx:163 [tel]
  - frontend/src/pages/account-settings/ProfileSection.tsx:169 [omitted]
  - frontend/src/pages/account-settings/ProfileSection.tsx:173 [omitted]
  - frontend/src/pages/account-settings/ProfileSection.tsx:180 [omitted]
  - frontend/src/pages/account-settings/ProfileSection.tsx:184 [omitted]
  - frontend/src/pages/account-settings/ProfileSection.tsx:191 [omitted]
  - frontend/src/pages/account-settings/ProfileSection.tsx:195 [omitted]
  - frontend/src/pages/account-settings/SecuritySection.tsx:67 [password]
  - frontend/src/pages/account-settings/SecuritySection.tsx:79 [password]
  - frontend/src/pages/account-settings/SecuritySection.tsx:91 [password]
  - frontend/src/pages/admin/TenantPolicyPage.tsx:192 [number]
  - frontend/src/pages/admin/TenantPolicyPage.tsx:207 [number]
  - frontend/src/pages/admin/TenantPolicyPage.tsx:222 [number]
  - frontend/src/pages/admin/TenantPolicyPage.tsx:238 [text]
  - frontend/src/pages/admin/TenantPolicyPage.tsx:253 [text]
  - frontend/src/pages/admin/TenantProfilePage.tsx:145 [text]
  - frontend/src/pages/admin/TenantProfilePage.tsx:158 [text]
  - frontend/src/pages/admin/TenantProfilePage.tsx:183 [text]
  - frontend/src/pages/admin/TenantProfilePage.tsx:196 [email]
  - frontend/src/pages/admin/TenantProfilePage.tsx:209 [text]
  - frontend/src/pages/admin/TenantProfilePage.tsx:222 [text]
  - frontend/src/pages/badges/BadgesPage.tsx:61 [omitted]
  - frontend/src/pages/badges/BadgesPage.tsx:62 [omitted]
  - frontend/src/pages/badges/BadgesPage.tsx:64 [omitted]
  - frontend/src/pages/badges/BadgesPage.tsx:66 [number]
  - frontend/src/pages/bots/BotFormFields.tsx:54 [omitted]
  - frontend/src/pages/bots/BotFormFields.tsx:83 [omitted]
  - frontend/src/pages/bots/BotFormFields.tsx:90 [email]
  - frontend/src/pages/bots/BotsPage.tsx:228 [omitted]
  - frontend/src/pages/bots/BotsPage.tsx:231 [omitted]
  - frontend/src/pages/bots/BotsPage.tsx:255 [omitted]
  - frontend/src/pages/bots/BotsPage.tsx:258 [email]
  - frontend/src/pages/buddy/BuddyPage.tsx:65 [number]
  - frontend/src/pages/buddy/BuddyPage.tsx:66 [number]
  - frontend/src/pages/companies/CompanyFormFields.tsx:37 [omitted]
  - frontend/src/pages/companies/CompanyFormFields.tsx:51 [omitted]
  - frontend/src/pages/companies/CompanyFormFields.tsx:58 [omitted]
  - frontend/src/pages/contacts/ContactEditPage.tsx:154 [omitted]
  - frontend/src/pages/contacts/ContactEditPage.tsx:157 [omitted]
  - frontend/src/pages/contacts/ContactEditPage.tsx:160 [omitted]
  - frontend/src/pages/contacts/ContactEditPage.tsx:163 [omitted]
  - frontend/src/pages/contacts/ContactEditPage.tsx:166 [omitted]
  - frontend/src/pages/contacts/ContactEditPage.tsx:175 [email]
  - frontend/src/pages/contacts/ContactEditPage.tsx:178 [omitted]
  - frontend/src/pages/contacts/ContactFormFields.tsx:56 [omitted]
  - frontend/src/pages/contacts/ContactFormFields.tsx:63 [omitted]
  - frontend/src/pages/contacts/ContactFormFields.tsx:70 [email]
  - frontend/src/pages/contacts/ContactFormFields.tsx:78 [omitted]
  - frontend/src/pages/integrations/CarrierCredentialForm.tsx:95 [text]
  - frontend/src/pages/integrations/CarrierCredentialForm.tsx:106 [password]
  - frontend/src/pages/integrations/CarrierCredentialForm.tsx:121 [text]
  - frontend/src/pages/integrations/FedexLabelValidationTab.tsx:334 [text]
  - frontend/src/pages/integrations/FedexLabelValidationTab.tsx:345 [text]
  - frontend/src/pages/integrations/FedexLabelValidationTab.tsx:356 [text]
  - frontend/src/pages/integrations/GoogleDriveIntegrationPage.tsx:162 [url]
  - frontend/src/pages/integrations/PaypalIntegrationPage.tsx:144 [text]
  - frontend/src/pages/integrations/PaypalIntegrationPage.tsx:154 [password]
  - frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:317 [omitted]
  - frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:419 [number]
  - frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:423 [number]
  - frontend/src/pages/leads/LeadEditPage.tsx:172 [omitted]
  - frontend/src/pages/leads/LeadEditPage.tsx:175 [omitted]
  - frontend/src/pages/leads/LeadEditPage.tsx:178 [email]
  - frontend/src/pages/leads/LeadEditPage.tsx:181 [omitted]
  - frontend/src/pages/leads/LeadEditPage.tsx:277 [number]
  - frontend/src/pages/leads/LeadFormFields.tsx:110 [omitted]
  - frontend/src/pages/leads/LeadFormFields.tsx:118 [email]
  - frontend/src/pages/leads/LeadFormFields.tsx:126 [omitted]
  - frontend/src/pages/leads/LeadsPage.tsx:330 [omitted]
  - frontend/src/pages/leads/LeadsPage.tsx:333 [omitted]
  - frontend/src/pages/leads/LeadsPage.tsx:336 [email]
  - frontend/src/pages/leads/LeadsPage.tsx:339 [omitted]
  - frontend/src/pages/leads/LeadsPage.tsx:427 [number]
  - frontend/src/pages/leads/LeadsPage.tsx:465 [omitted]
  - frontend/src/pages/leads/LeadsPage.tsx:468 [number]
  - frontend/src/pages/notifications/NotificationsPage.tsx:63 [omitted]
  - frontend/src/pages/notifications/NotificationsPage.tsx:64 [omitted]
  - frontend/src/pages/orders/OrdersFormModal.tsx:72 [omitted]
  - frontend/src/pages/orders/OrdersFormModal.tsx:80 [number]
  - frontend/src/pages/quote-create/QuoteCreatePage.tsx:165 [omitted]
  - frontend/src/pages/quote-create/QuoteCreatePage.tsx:268 [number]
  - frontend/src/pages/quote-create/QuoteCreatePage.tsx:273 [number]
  - frontend/src/pages/roles/RolesPage.tsx:494 [omitted]
  - frontend/src/pages/roles/RolesPage.tsx:556 [number]
  - frontend/src/pages/shifts/ShiftsPage.tsx:63 [number]
  - frontend/src/pages/shifts/ShiftsPage.tsx:64 [date]
  - frontend/src/pages/shifts/ShiftsPage.tsx:65 [time]
  - frontend/src/pages/shifts/ShiftsPage.tsx:66 [time]
  - frontend/src/pages/staff-reports/StaffReportsPage.tsx:90 [omitted]
  - frontend/src/pages/staff/StaffEditPage.tsx:161 [omitted]
  - frontend/src/pages/staff/StaffEditPage.tsx:164 [omitted]
  - frontend/src/pages/staff/StaffEditPage.tsx:167 [omitted]
  - frontend/src/pages/staff/StaffEditPage.tsx:170 [omitted]
  - frontend/src/pages/staff/StaffEditPage.tsx:173 [omitted]
  - frontend/src/pages/staff/StaffEditPage.tsx:176 [omitted]
  - frontend/src/pages/staff/StaffEditPage.tsx:179 [email]
  - frontend/src/pages/staff/StaffEditPage.tsx:182 [omitted]
  - frontend/src/pages/staff/StaffEditPage.tsx:203 [omitted]
  - frontend/src/pages/staff/StaffFormFields.tsx:43 [omitted]
  - frontend/src/pages/staff/StaffFormFields.tsx:51 [omitted]
  - frontend/src/pages/staff/StaffFormFields.tsx:59 [email]
  - frontend/src/pages/staff/StaffFormFields.tsx:82 [omitted]
  - frontend/src/pages/staff/StaffPage.tsx:238 [omitted]
  - frontend/src/pages/staff/StaffPage.tsx:241 [omitted]
  - frontend/src/pages/staff/StaffPage.tsx:244 [omitted]
  - frontend/src/pages/staff/StaffPage.tsx:247 [omitted]
  - frontend/src/pages/staff/StaffPage.tsx:250 [omitted]
  - frontend/src/pages/staff/StaffPage.tsx:253 [omitted]
  - frontend/src/pages/staff/StaffPage.tsx:256 [email]
  - frontend/src/pages/staff/StaffPage.tsx:259 [omitted]
  - frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:464 [omitted]
  - frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:467 [omitted]
  - frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:470 [number]
  - frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:516 [omitted]
  - frontend/src/pages/suppliers/SupplierFormFields.tsx:32 [omitted]
  - frontend/src/pages/suppliers/SupplierFormFields.tsx:40 [omitted]
  - frontend/src/pages/suppliers/SupplierFormFields.tsx:47 [email]
  - frontend/src/pages/suppliers/SupplierFormFields.tsx:55 [omitted]
  - frontend/src/pages/teams/TeamFormFields.tsx:28 [omitted]
  - frontend/src/pages/teams/TeamFormFields.tsx:36 [number]
  - frontend/src/pages/teams/TeamsPage.tsx:242 [number]

### G02（61 件）

- type: {"text":38,"omitted":12,"email":5,"number":3,"datetime-local":1,"dynamic":1,"tel":1}
- 適用規則:
  - (なし)
- 静的className: `input` `w-full` `manual-record-datetime` `qty-input`
- inline style: 0件 
- disabled属性あり: 4件 / unconfirmedを持つ: 15件
- 領域: pages/register:41, pages/super-admin:11, pages/admin:3, components/master-list-editor:2, features/tcg-analysis-review:1, pages/commission-settings:1, pages/inbox:1, pages/inventory:1
- ファイル:
  - pages/register/RegisterPage.tsx : 21
  - pages/register/RegisterAddressPage.tsx : 10
  - pages/register/RegisterChangeBillingPage.tsx : 9
  - pages/super-admin/DexTab.tsx : 5
  - pages/super-admin/TcgSeriesTab.tsx : 5
  - components/master-list-editor/MasterListEditor.tsx : 2
  - pages/admin/ChannelMastersPage.tsx : 2
  - features/tcg-analysis-review/ItemComparison.tsx : 1
  - pages/admin/DiscordAnnouncePage.tsx : 1
  - pages/commission-settings/CommissionSettingsPage.tsx : 1
  - pages/inbox/ManualRecordSection.tsx : 1
  - pages/inventory/OwnInventoryPage.tsx : 1
  - pages/register/CountryCombobox.tsx : 1
  - pages/super-admin/LLMBudgetTab.tsx : 1
- メンバー(file:line):
  - frontend/src/components/master-list-editor/MasterListEditor.tsx:157 [omitted]
  - frontend/src/components/master-list-editor/MasterListEditor.tsx:164 [omitted]
  - frontend/src/features/tcg-analysis-review/ItemComparison.tsx:28 [dynamic]
  - frontend/src/pages/admin/ChannelMastersPage.tsx:115 [text]
  - frontend/src/pages/admin/ChannelMastersPage.tsx:123 [text]
  - frontend/src/pages/admin/DiscordAnnouncePage.tsx:81 [text] className="input w-full"
  - frontend/src/pages/commission-settings/CommissionSettingsPage.tsx:220 [number]
  - frontend/src/pages/inbox/ManualRecordSection.tsx:148 [datetime-local] className="manual-record-datetime"
  - frontend/src/pages/inventory/OwnInventoryPage.tsx:232 [number] className="qty-input"
  - frontend/src/pages/register/CountryCombobox.tsx:46 [text] className="input"
  - frontend/src/pages/register/RegisterAddressPage.tsx:115 [text] className="input"
  - frontend/src/pages/register/RegisterAddressPage.tsx:316 [text] className="input"
  - frontend/src/pages/register/RegisterAddressPage.tsx:357 [email] className="input"
  - frontend/src/pages/register/RegisterAddressPage.tsx:368 [text] className="input"
  - frontend/src/pages/register/RegisterAddressPage.tsx:379 [text] className="input"
  - frontend/src/pages/register/RegisterAddressPage.tsx:390 [text] className="input"
  - frontend/src/pages/register/RegisterAddressPage.tsx:401 [text] className="input"
  - frontend/src/pages/register/RegisterAddressPage.tsx:412 [text] className="input"
  - frontend/src/pages/register/RegisterAddressPage.tsx:423 [text] className="input"
  - frontend/src/pages/register/RegisterAddressPage.tsx:434 [text] className="input"
  - frontend/src/pages/register/RegisterChangeBillingPage.tsx:253 [text] className="input"
  - frontend/src/pages/register/RegisterChangeBillingPage.tsx:298 [email] className="input"
  - frontend/src/pages/register/RegisterChangeBillingPage.tsx:313 [text] className="input"
  - frontend/src/pages/register/RegisterChangeBillingPage.tsx:324 [text] className="input"
  - frontend/src/pages/register/RegisterChangeBillingPage.tsx:335 [text] className="input"
  - frontend/src/pages/register/RegisterChangeBillingPage.tsx:347 [text] className="input"
  - frontend/src/pages/register/RegisterChangeBillingPage.tsx:358 [text] className="input"
  - frontend/src/pages/register/RegisterChangeBillingPage.tsx:369 [text] className="input"
  - frontend/src/pages/register/RegisterChangeBillingPage.tsx:380 [text] className="input"
  - frontend/src/pages/register/RegisterPage.tsx:306 [text] className="input"
  - frontend/src/pages/register/RegisterPage.tsx:351 [email] className="input"
  - frontend/src/pages/register/RegisterPage.tsx:366 [text] className="input"
  - frontend/src/pages/register/RegisterPage.tsx:377 [text] className="input"
  - frontend/src/pages/register/RegisterPage.tsx:388 [text] className="input"
  - frontend/src/pages/register/RegisterPage.tsx:400 [text] className="input"
  - frontend/src/pages/register/RegisterPage.tsx:411 [text] className="input"
  - frontend/src/pages/register/RegisterPage.tsx:422 [text] className="input"
  - frontend/src/pages/register/RegisterPage.tsx:433 [text] className="input"
  - frontend/src/pages/register/RegisterPage.tsx:511 [text] className="input"
  - frontend/src/pages/register/RegisterPage.tsx:520 [email] className="input"
  - frontend/src/pages/register/RegisterPage.tsx:529 [tel] className="input"
  - frontend/src/pages/register/RegisterPage.tsx:567 [text] className="input"
  - frontend/src/pages/register/RegisterPage.tsx:609 [email] className="input"
  - frontend/src/pages/register/RegisterPage.tsx:620 [text] className="input"
  - frontend/src/pages/register/RegisterPage.tsx:631 [text] className="input"
  - frontend/src/pages/register/RegisterPage.tsx:643 [text] className="input"
  - frontend/src/pages/register/RegisterPage.tsx:654 [text] className="input"
  - frontend/src/pages/register/RegisterPage.tsx:665 [text] className="input"
  - frontend/src/pages/register/RegisterPage.tsx:676 [text] className="input"
  - frontend/src/pages/register/RegisterPage.tsx:687 [text] className="input"
  - frontend/src/pages/super-admin/DexTab.tsx:200 [omitted]
  - frontend/src/pages/super-admin/DexTab.tsx:298 [omitted]
  - frontend/src/pages/super-admin/DexTab.tsx:303 [omitted]
  - frontend/src/pages/super-admin/DexTab.tsx:309 [omitted]
  - frontend/src/pages/super-admin/DexTab.tsx:315 [omitted]
  - frontend/src/pages/super-admin/LLMBudgetTab.tsx:187 [number]
  - frontend/src/pages/super-admin/TcgSeriesTab.tsx:230 [omitted]
  - frontend/src/pages/super-admin/TcgSeriesTab.tsx:238 [omitted]
  - frontend/src/pages/super-admin/TcgSeriesTab.tsx:311 [omitted]
  - frontend/src/pages/super-admin/TcgSeriesTab.tsx:317 [omitted]
  - frontend/src/pages/super-admin/TcgSeriesTab.tsx:323 [omitted]

### G03（32 件）

- type: {"omitted":29,"email":2,"number":1}
- 適用規則:
  - `company-forms.css:100 .form-grid > .form-row input:not([type="checkbox"]):not([type="radio"])`
  - `company-forms.css:113 .form-grid > .form-row input:focus`
  - `company-forms.css:147 .modal-content-wide .form-row input:not([type="checkbox"]):not([type="radio"])`
  - `company-forms.css:163 .modal-content-wide .form-row input:focus`
- 静的className: (なし)
- inline style: 0件 
- disabled属性あり: 0件 / unconfirmedを持つ: 0件
- 領域: pages/companies:24, pages/contacts:8
- ファイル:
  - pages/companies/CompaniesPage.tsx : 24
  - pages/contacts/ContactsPage.tsx : 8
- メンバー(file:line):
  - frontend/src/pages/companies/CompaniesPage.tsx:452 [omitted]
  - frontend/src/pages/companies/CompaniesPage.tsx:456 [omitted]
  - frontend/src/pages/companies/CompaniesPage.tsx:460 [omitted]
  - frontend/src/pages/companies/CompaniesPage.tsx:464 [omitted]
  - frontend/src/pages/companies/CompaniesPage.tsx:468 [omitted]
  - frontend/src/pages/companies/CompaniesPage.tsx:472 [omitted]
  - frontend/src/pages/companies/CompaniesPage.tsx:476 [omitted]
  - frontend/src/pages/companies/CompaniesPage.tsx:480 [number]
  - frontend/src/pages/companies/CompaniesPage.tsx:484 [omitted]
  - frontend/src/pages/companies/CompaniesPage.tsx:488 [omitted]
  - frontend/src/pages/companies/CompaniesPage.tsx:492 [omitted]
  - frontend/src/pages/companies/CompaniesPage.tsx:496 [omitted]
  - frontend/src/pages/companies/CompaniesPage.tsx:504 [omitted]
  - frontend/src/pages/companies/CompaniesPage.tsx:533 [omitted]
  - frontend/src/pages/companies/CompaniesPage.tsx:535 [omitted]
  - frontend/src/pages/companies/CompaniesPage.tsx:536 [email]
  - frontend/src/pages/companies/CompaniesPage.tsx:539 [omitted]
  - frontend/src/pages/companies/CompaniesPage.tsx:542 [omitted]
  - frontend/src/pages/companies/CompaniesPage.tsx:543 [omitted]
  - frontend/src/pages/companies/CompaniesPage.tsx:544 [omitted]
  - frontend/src/pages/companies/CompaniesPage.tsx:545 [omitted]
  - frontend/src/pages/companies/CompaniesPage.tsx:546 [omitted]
  - frontend/src/pages/companies/CompaniesPage.tsx:547 [omitted]
  - frontend/src/pages/companies/CompaniesPage.tsx:548 [omitted]
  - frontend/src/pages/contacts/ContactsPage.tsx:306 [omitted]
  - frontend/src/pages/contacts/ContactsPage.tsx:316 [omitted]
  - frontend/src/pages/contacts/ContactsPage.tsx:319 [omitted]
  - frontend/src/pages/contacts/ContactsPage.tsx:322 [omitted]
  - frontend/src/pages/contacts/ContactsPage.tsx:325 [omitted]
  - frontend/src/pages/contacts/ContactsPage.tsx:328 [omitted]
  - frontend/src/pages/contacts/ContactsPage.tsx:337 [email]
  - frontend/src/pages/contacts/ContactsPage.tsx:340 [omitted]

### G04（22 件）

- type: {"text":11,"number":6,"email":2,"tel":2,"date":1}
- 適用規則:
  - `pages/inbox/InboxPage.css:1160 .right-panel-field`
  - `pages/inbox/InboxPage.css:1168 .right-panel-field::placeholder`
  - `pages/inbox/InboxPage.css:1169 .right-panel-field:focus`
- 静的className: `right-panel-field`
- inline style: 0件 
- disabled属性あり: 0件 / unconfirmedを持つ: 0件
- 領域: pages/inbox:22
- ファイル:
  - pages/inbox/InboxProfileModal.tsx : 12
  - pages/inbox/InboxKartePanel.tsx : 10
- メンバー(file:line):
  - frontend/src/pages/inbox/InboxKartePanel.tsx:372 [text] className="right-panel-field"
  - frontend/src/pages/inbox/InboxKartePanel.tsx:379 [email] className="right-panel-field"
  - frontend/src/pages/inbox/InboxKartePanel.tsx:386 [tel] className="right-panel-field"
  - frontend/src/pages/inbox/InboxKartePanel.tsx:404 [text] className="right-panel-field"
  - frontend/src/pages/inbox/InboxKartePanel.tsx:437 [text] className="right-panel-field"
  - frontend/src/pages/inbox/InboxKartePanel.tsx:443 [text] className="right-panel-field"
  - frontend/src/pages/inbox/InboxKartePanel.tsx:461 [text] className="right-panel-field"
  - frontend/src/pages/inbox/InboxKartePanel.tsx:569 [number] className="right-panel-field"
  - frontend/src/pages/inbox/InboxKartePanel.tsx:575 [number] className="right-panel-field"
  - frontend/src/pages/inbox/InboxKartePanel.tsx:581 [number] className="right-panel-field"
  - frontend/src/pages/inbox/InboxProfileModal.tsx:117 [email] className="right-panel-field"
  - frontend/src/pages/inbox/InboxProfileModal.tsx:122 [tel] className="right-panel-field"
  - frontend/src/pages/inbox/InboxProfileModal.tsx:129 [text] className="right-panel-field"
  - frontend/src/pages/inbox/InboxProfileModal.tsx:148 [text] className="right-panel-field"
  - frontend/src/pages/inbox/InboxProfileModal.tsx:153 [text] className="right-panel-field"
  - frontend/src/pages/inbox/InboxProfileModal.tsx:158 [text] className="right-panel-field"
  - frontend/src/pages/inbox/InboxProfileModal.tsx:172 [text] className="right-panel-field"
  - frontend/src/pages/inbox/InboxProfileModal.tsx:178 [text] className="right-panel-field"
  - frontend/src/pages/inbox/InboxProfileModal.tsx:197 [date] className="right-panel-field"
  - frontend/src/pages/inbox/InboxProfileModal.tsx:238 [number] className="right-panel-field"
  - frontend/src/pages/inbox/InboxProfileModal.tsx:243 [number] className="right-panel-field"
  - frontend/src/pages/inbox/InboxProfileModal.tsx:248 [number] className="right-panel-field"

### G05（16 件）

- type: {"omitted":15,"number":1}
- 適用規則:
  - `company-forms.css:100 .form-grid > .form-row input:not([type="checkbox"]):not([type="radio"])`
  - `company-forms.css:113 .form-grid > .form-row input:focus`
- 静的className: (なし)
- inline style: 0件 
- disabled属性あり: 16件 / unconfirmedを持つ: 0件
- 領域: pages/company-detail:16
- ファイル:
  - pages/company-detail/CompanyBasicTab.tsx : 11
  - pages/company-detail/CompanyDiscordTab.tsx : 4
  - pages/company-detail/CompanyChannelsTab.tsx : 1
- メンバー(file:line):
  - frontend/src/pages/company-detail/CompanyBasicTab.tsx:38 [omitted]
  - frontend/src/pages/company-detail/CompanyBasicTab.tsx:42 [omitted]
  - frontend/src/pages/company-detail/CompanyBasicTab.tsx:46 [omitted]
  - frontend/src/pages/company-detail/CompanyBasicTab.tsx:50 [omitted]
  - frontend/src/pages/company-detail/CompanyBasicTab.tsx:54 [omitted]
  - frontend/src/pages/company-detail/CompanyBasicTab.tsx:58 [omitted]
  - frontend/src/pages/company-detail/CompanyBasicTab.tsx:62 [number]
  - frontend/src/pages/company-detail/CompanyBasicTab.tsx:66 [omitted]
  - frontend/src/pages/company-detail/CompanyBasicTab.tsx:70 [omitted]
  - frontend/src/pages/company-detail/CompanyBasicTab.tsx:74 [omitted]
  - frontend/src/pages/company-detail/CompanyBasicTab.tsx:78 [omitted]
  - frontend/src/pages/company-detail/CompanyChannelsTab.tsx:32 [omitted]
  - frontend/src/pages/company-detail/CompanyDiscordTab.tsx:53 [omitted]
  - frontend/src/pages/company-detail/CompanyDiscordTab.tsx:62 [omitted]
  - frontend/src/pages/company-detail/CompanyDiscordTab.tsx:71 [omitted]
  - frontend/src/pages/company-detail/CompanyDiscordTab.tsx:80 [omitted]

### G06（14 件）

- type: {"number":7,"omitted":5,"date":1,"url":1}
- 適用規則:
  - `company-forms.css:238 .product-edit-form .form-group input:not([type="checkbox"]):not([type="radio"])`
  - `components.css:19 .form-group input`
  - `components.css:30 .form-group input:focus`
- 静的className: (なし)
- inline style: 0件 
- disabled属性あり: 0件 / unconfirmedを持つ: 0件
- 領域: pages/products:14
- ファイル:
  - pages/products/ProductEditPage.tsx : 14
- メンバー(file:line):
  - frontend/src/pages/products/ProductEditPage.tsx:215 [omitted]
  - frontend/src/pages/products/ProductEditPage.tsx:224 [omitted]
  - frontend/src/pages/products/ProductEditPage.tsx:251 [omitted]
  - frontend/src/pages/products/ProductEditPage.tsx:262 [date]
  - frontend/src/pages/products/ProductEditPage.tsx:270 [omitted]
  - frontend/src/pages/products/ProductEditPage.tsx:274 [omitted]
  - frontend/src/pages/products/ProductEditPage.tsx:294 [number]
  - frontend/src/pages/products/ProductEditPage.tsx:298 [url]
  - frontend/src/pages/products/ProductEditPage.tsx:317 [number]
  - frontend/src/pages/products/ProductEditPage.tsx:321 [number]
  - frontend/src/pages/products/ProductEditPage.tsx:325 [number]
  - frontend/src/pages/products/ProductEditPage.tsx:329 [number]
  - frontend/src/pages/products/ProductEditPage.tsx:333 [number]
  - frontend/src/pages/products/ProductEditPage.tsx:337 [number]

### G07（7 件）

- type: {"omitted":6,"date":1}
- 適用規則:
  - `features/tcg-analysis-review/supplier-detail-view.css:244 .pmd-field input`
- 静的className: (なし)
- inline style: 0件 
- disabled属性あり: 0件 / unconfirmedを持つ: 1件
- 領域: features/tcg-analysis-review:7
- ファイル:
  - features/tcg-analysis-review/ProductMasterDrawer.tsx : 7
- メンバー(file:line):
  - frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:68 [omitted]
  - frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:201 [omitted]
  - frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:205 [omitted]
  - frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:209 [omitted]
  - frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:213 [date]
  - frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:338 [omitted]
  - frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:470 [omitted]

### G08（6 件）

- type: {"date":2,"omitted":2,"time":2}
- 適用規則:
  - `pages/schedule.css:813 .schedule-input`
  - `pages/schedule.css:822 .schedule-input`
  - `pages/schedule.css:827 .schedule-input:focus`
- 静的className: `schedule-input`
- inline style: 0件 
- disabled属性あり: 0件 / unconfirmedを持つ: 0件
- 領域: pages/schedule:6
- ファイル:
  - pages/schedule/SchedulePageImpl.tsx : 6
- メンバー(file:line):
  - frontend/src/pages/schedule/SchedulePageImpl.tsx:280 [omitted] className="schedule-input"
  - frontend/src/pages/schedule/SchedulePageImpl.tsx:324 [date] className="schedule-input"
  - frontend/src/pages/schedule/SchedulePageImpl.tsx:334 [time] className="schedule-input"
  - frontend/src/pages/schedule/SchedulePageImpl.tsx:347 [date] className="schedule-input"
  - frontend/src/pages/schedule/SchedulePageImpl.tsx:357 [time] className="schedule-input"
  - frontend/src/pages/schedule/SchedulePageImpl.tsx:369 [omitted] className="schedule-input"

### G09（6 件）

- type: {"omitted":4,"number":2}
- 適用規則:
  - (なし)
- 静的className: (なし)
- inline style: 6件 `style{width:var(--input-width-weight)}`
- disabled属性あり: 0件 / unconfirmedを持つ: 0件
- 領域: pages/invoice-create:3, pages/quote-create:3
- ファイル:
  - pages/invoice-create/InvoiceCreatePage.tsx : 3
  - pages/quote-create/QuoteCreatePage.tsx : 3
- メンバー(file:line):
  - frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:367 [omitted] style{width:var(--input-width-weight)}
  - frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:371 [omitted] style{width:var(--input-width-weight)}
  - frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:390 [number] style{width:var(--input-width-weight)}
  - frontend/src/pages/quote-create/QuoteCreatePage.tsx:216 [omitted] style{width:var(--input-width-weight)}
  - frontend/src/pages/quote-create/QuoteCreatePage.tsx:220 [omitted] style{width:var(--input-width-weight)}
  - frontend/src/pages/quote-create/QuoteCreatePage.tsx:239 [number] style{width:var(--input-width-weight)}

### G10（4 件）

- type: {"tel":4}
- 適用規則:
  - (なし)
- 静的className: `input`
- inline style: 4件 `style{flex:1}`
- disabled属性あり: 0件 / unconfirmedを持つ: 0件
- 領域: pages/register:4
- ファイル:
  - pages/register/RegisterPage.tsx : 2
  - pages/register/RegisterAddressPage.tsx : 1
  - pages/register/RegisterChangeBillingPage.tsx : 1
- メンバー(file:line):
  - frontend/src/pages/register/RegisterAddressPage.tsx:344 [tel] className="input" style{flex:1}
  - frontend/src/pages/register/RegisterChangeBillingPage.tsx:284 [tel] className="input" style{flex:1}
  - frontend/src/pages/register/RegisterPage.tsx:337 [tel] className="input" style{flex:1}
  - frontend/src/pages/register/RegisterPage.tsx:596 [tel] className="input" style{flex:1}

### G11（3 件）

- type: {"email":2,"password":1}
- 適用規則:
  - `components.css:19 .form-group input`
  - `components.css:30 .form-group input:focus`
  - `pages-layout.css:246 .login-card .form-group input`
  - `pages-layout.css:255 .login-card .form-group input:focus`
- 静的className: (なし)
- inline style: 0件 
- disabled属性あり: 0件 / unconfirmedを持つ: 0件
- 領域: pages/login:3
- ファイル:
  - pages/login/LoginPage.tsx : 3
- メンバー(file:line):
  - frontend/src/pages/login/LoginPage.tsx:93 [email]
  - frontend/src/pages/login/LoginPage.tsx:104 [password]
  - frontend/src/pages/login/LoginPage.tsx:136 [email]

### G12（3 件）

- type: {"search":2,"text":1}
- 適用規則:
  - `components/field-size.css:15 .field-w-md`
  - `components/field-size.css:22 .content-toolbar .field-w-md`
  - `components/field-size.css:8 .field-h-md`
- 静的className: `search-input` `field-h-md` `field-w-md`
- inline style: 0件 
- disabled属性あり: 0件 / unconfirmedを持つ: 0件
- 領域: pages/companies:1, pages/inventory:1, pages/orders:1
- ファイル:
  - pages/companies/CompaniesPage.tsx : 1
  - pages/inventory/InventoryPage.tsx : 1
  - pages/orders/OrdersFilterBar.tsx : 1
- メンバー(file:line):
  - frontend/src/pages/companies/CompaniesPage.tsx:386 [text] className="search-input field-h-md field-w-md"
  - frontend/src/pages/inventory/InventoryPage.tsx:384 [search] className="field-h-md field-w-md"
  - frontend/src/pages/orders/OrdersFilterBar.tsx:32 [search] className="field-h-md field-w-md"

### G13（3 件）

- type: {"text":3}
- 適用規則:
  - `features/tcg-distribution/distribution.css:322 .dist-input`
  - `features/tcg-distribution/distribution.css:334 .dist-input:focus`
  - `features/tcg-distribution/distribution.css:340 .dist-input--error ?conditional-class`
- 静的className: `dist-input`
- inline style: 0件 
- disabled属性あり: 0件 / unconfirmedを持つ: 3件
- 領域: features/tcg-distribution:3
- ファイル:
  - features/tcg-distribution/DistributionTargetForm.tsx : 3
- メンバー(file:line):
  - frontend/src/features/tcg-distribution/DistributionTargetForm.tsx:182 [text] className={`dist-input${errors.name ? " dist-input--error" : ""}`}
  - frontend/src/features/tcg-distribution/DistributionTargetForm.tsx:199 [text] className={`dist-input${errors.spreadsheet_id ? " dist-input--error" : ""}`}
  - frontend/src/features/tcg-distribution/DistributionTargetForm.tsx:223 [text] className={`dist-input${errors.sheet_name ? " dist-input--error" : ""}`}

### G14（2 件）

- type: {"text":2}
- 適用規則:
  - `components.css:50 .search-bar input`
  - `components/field-size.css:13 .field-w-sm`
  - `components/field-size.css:22 .content-toolbar .field-w-sm`
  - `components/field-size.css:8 .field-h-md`
- 静的className: `field-h-md` `field-w-sm`
- inline style: 0件 
- disabled属性あり: 0件 / unconfirmedを持つ: 1件
- 領域: components/master-list-editor:1, pages/products:1
- ファイル:
  - components/master-list-editor/MasterListEditor.tsx : 1
  - pages/products/ProductsPage.tsx : 1
- メンバー(file:line):
  - frontend/src/components/master-list-editor/MasterListEditor.tsx:135 [text] className="field-h-md field-w-sm"
  - frontend/src/pages/products/ProductsPage.tsx:219 [text] className="field-h-md field-w-sm"

### G15（2 件）

- type: {"date":2}
- 適用規則:
  - `pages/dashboard/WeeklyAdvisorSection.css:205 .db-weekly-composer-input`
  - `pages/dashboard/WeeklyAdvisorSection.css:216 .db-weekly-composer-input:focus`
- 静的className: `db-weekly-composer-input`
- inline style: 0件 
- disabled属性あり: 0件 / unconfirmedを持つ: 2件
- 領域: pages/dashboard:2
- ファイル:
  - pages/dashboard/PriorityProspectsSection.tsx : 1
  - pages/dashboard/WeeklyAdvisorSection.tsx : 1
- メンバー(file:line):
  - frontend/src/pages/dashboard/PriorityProspectsSection.tsx:424 [date] className="db-weekly-composer-input"
  - frontend/src/pages/dashboard/WeeklyAdvisorSection.tsx:395 [date] className="db-weekly-composer-input"

### G16（2 件）

- type: {"text":2}
- 適用規則:
  - (なし)
- 静的className: (なし)
- inline style: 2件 `style{background:var(--bg-primary);border-radius:4px;border:1px solid var(--border-color);color:var(--text-primary);font-size:0.85rem;min-width:200px;padding:0.4rem 0.6rem}`
- disabled属性あり: 0件 / unconfirmedを持つ: 0件
- 領域: pages/super-admin:2
- ファイル:
  - pages/super-admin/TcgLineImportPage.tsx : 2
- メンバー(file:line):
  - frontend/src/pages/super-admin/TcgLineImportPage.tsx:374 [text] style{background:var(--bg-primary);border-radius:4px;border:1px solid var(--border-color);color:var(--text-primary);font-size:0.85rem;min-width:200px;padding:0.4rem 0.6rem}
  - frontend/src/pages/super-admin/TcgLineImportPage.tsx:395 [text] style{background:var(--bg-primary);border-radius:4px;border:1px solid var(--border-color);color:var(--text-primary);font-size:0.85rem;min-width:200px;padding:0.4rem 0.6rem}

### G17（2 件）

- type: {"text":2}
- 適用規則:
  - (なし)
- 静的className: (なし)
- inline style: 2件 `style{border-radius:4px;border:1px solid var(--border);font-size:13px;padding:6px 8px;width:80px}`
- disabled属性あり: 0件 / unconfirmedを持つ: 0件
- 領域: components:2
- ファイル:
  - components/FedExRateModal.tsx : 2
- メンバー(file:line):
  - frontend/src/components/FedExRateModal.tsx:176 [text] style{border-radius:4px;border:1px solid var(--border);font-size:13px;padding:6px 8px;width:80px}
  - frontend/src/components/FedExRateModal.tsx:193 [text] style{border-radius:4px;border:1px solid var(--border);font-size:13px;padding:6px 8px;width:80px}

### G18（2 件）

- type: {"omitted":2}
- 適用規則:
  - (なし)
- 静的className: (なし)
- inline style: 2件 `style{color:var(--text-secondary);font-size:var(--font-sm);margin-top:var(--space-1);min-width:var(--input-width-product-name);width:100%}`
- disabled属性あり: 0件 / unconfirmedを持つ: 0件
- 領域: pages/invoice-create:1, pages/quote-create:1
- ファイル:
  - pages/invoice-create/InvoiceCreatePage.tsx : 1
  - pages/quote-create/QuoteCreatePage.tsx : 1
- メンバー(file:line):
  - frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:349 [omitted] style{color:var(--text-secondary);font-size:var(--font-sm);margin-top:var(--space-1);min-width:var(--input-width-product-name);width:100%}
  - frontend/src/pages/quote-create/QuoteCreatePage.tsx:198 [omitted] style{color:var(--text-secondary);font-size:var(--font-sm);margin-top:var(--space-1);min-width:var(--input-width-product-name);width:100%}

### G19（2 件）

- type: {"omitted":2}
- 適用規則:
  - (なし)
- 静的className: (なし)
- inline style: 2件 `style{font-weight:var(--font-weight-semi);min-width:var(--input-width-product-name);width:100%}`
- disabled属性あり: 0件 / unconfirmedを持つ: 0件
- 領域: pages/invoice-create:1, pages/quote-create:1
- ファイル:
  - pages/invoice-create/InvoiceCreatePage.tsx : 1
  - pages/quote-create/QuoteCreatePage.tsx : 1
- メンバー(file:line):
  - frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:342 [omitted] style{font-weight:var(--font-weight-semi);min-width:var(--input-width-product-name);width:100%}
  - frontend/src/pages/quote-create/QuoteCreatePage.tsx:191 [omitted] style{font-weight:var(--font-weight-semi);min-width:var(--input-width-product-name);width:100%}

### G20（2 件）

- type: {"number":2}
- 適用規則:
  - (なし)
- 静的className: (なし)
- inline style: 2件 `style{margin-left:var(--space-2);width:var(--input-width-month)}`
- disabled属性あり: 0件 / unconfirmedを持つ: 0件
- 領域: pages/commission-settings:1, pages/commissions:1
- ファイル:
  - pages/commission-settings/CommissionSettingsPage.tsx : 1
  - pages/commissions/CommissionsPage.tsx : 1
- メンバー(file:line):
  - frontend/src/pages/commission-settings/CommissionSettingsPage.tsx:287 [number] style{margin-left:var(--space-2);width:var(--input-width-month)}
  - frontend/src/pages/commissions/CommissionsPage.tsx:153 [number] style{margin-left:var(--space-2);width:var(--input-width-month)}

### G21（2 件）

- type: {"number":2}
- 適用規則:
  - (なし)
- 静的className: (なし)
- inline style: 2件 `style{margin-left:var(--space-2);width:var(--input-width-year)}`
- disabled属性あり: 0件 / unconfirmedを持つ: 0件
- 領域: pages/commission-settings:1, pages/commissions:1
- ファイル:
  - pages/commission-settings/CommissionSettingsPage.tsx : 1
  - pages/commissions/CommissionsPage.tsx : 1
- メンバー(file:line):
  - frontend/src/pages/commission-settings/CommissionSettingsPage.tsx:275 [number] style{margin-left:var(--space-2);width:var(--input-width-year)}
  - frontend/src/pages/commissions/CommissionsPage.tsx:141 [number] style{margin-left:var(--space-2);width:var(--input-width-year)}

### G22（2 件）

- type: {"omitted":2}
- 適用規則:
  - (なし)
- 静的className: (なし)
- inline style: 2件 `style{max-width:100%;width:SEARCH_WIDTH}`
- disabled属性あり: 0件 / unconfirmedを持つ: 0件
- 領域: pages/super-admin:2
- ファイル:
  - pages/super-admin/KnowledgeAliasesTab.tsx : 2
- メンバー(file:line):
  - frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:295 [omitted] style{max-width:100%;width:SEARCH_WIDTH}
  - frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:374 [omitted] style{max-width:100%;width:SEARCH_WIDTH}

### G23（2 件）

- type: {"number":2}
- 適用規則:
  - (なし)
- 静的className: (なし)
- inline style: 2件 `style{width:6rem}`
- disabled属性あり: 0件 / unconfirmedを持つ: 0件
- 領域: pages/inventory:2
- ファイル:
  - pages/inventory/InventoryFilterPanel.tsx : 2
- メンバー(file:line):
  - frontend/src/pages/inventory/InventoryFilterPanel.tsx:287 [number] style{width:6rem}
  - frontend/src/pages/inventory/InventoryFilterPanel.tsx:290 [number] style{width:6rem}

### G24（2 件）

- type: {"number":2}
- 適用規則:
  - (なし)
- 静的className: (なし)
- inline style: 2件 `style{width:7rem}`
- disabled属性あり: 0件 / unconfirmedを持つ: 0件
- 領域: pages/inventory:2
- ファイル:
  - pages/inventory/InventoryFilterPanel.tsx : 2
- メンバー(file:line):
  - frontend/src/pages/inventory/InventoryFilterPanel.tsx:295 [number] style{width:7rem}
  - frontend/src/pages/inventory/InventoryFilterPanel.tsx:298 [number] style{width:7rem}

### G25（2 件）

- type: {"number":2}
- 適用規則:
  - (なし)
- 静的className: (なし)
- inline style: 2件 `style{width:var(--input-width-qty)}`
- disabled属性あり: 0件 / unconfirmedを持つ: 0件
- 領域: pages/invoice-create:1, pages/quote-create:1
- ファイル:
  - pages/invoice-create/InvoiceCreatePage.tsx : 1
  - pages/quote-create/QuoteCreatePage.tsx : 1
- メンバー(file:line):
  - frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:384 [number] style{width:var(--input-width-qty)}
  - frontend/src/pages/quote-create/QuoteCreatePage.tsx:233 [number] style{width:var(--input-width-qty)}

### G26（2 件）

- type: {"number":2}
- 適用規則:
  - (なし)
- 静的className: (なし)
- inline style: 2件 `style{width:var(--input-width-year)}`
- disabled属性あり: 0件 / unconfirmedを持つ: 0件
- 領域: pages/invoice-create:1, pages/quote-create:1
- ファイル:
  - pages/invoice-create/InvoiceCreatePage.tsx : 1
  - pages/quote-create/QuoteCreatePage.tsx : 1
- メンバー(file:line):
  - frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:387 [number] style{width:var(--input-width-year)}
  - frontend/src/pages/quote-create/QuoteCreatePage.tsx:236 [number] style{width:var(--input-width-year)}

### G27（1 件）

- type: {"text":1}
- 適用規則:
  - `company-forms.css:147 .modal-content-wide .form-row input:not([type="checkbox"]):not([type="radio"])`
  - `company-forms.css:163 .modal-content-wide .form-row input:focus`
- 静的className: (なし)
- inline style: 0件 
- disabled属性あり: 0件 / unconfirmedを持つ: 0件
- 領域: components:1
- ファイル:
  - components/MergeLeadModal.tsx : 1
- メンバー(file:line):
  - frontend/src/components/MergeLeadModal.tsx:146 [text]

### G28（1 件）

- type: {"text":1}
- 適用規則:
  - `components.css:19 .form-group input`
  - `components.css:30 .form-group input:focus`
- 静的className: (なし)
- inline style: 1件 `style{min-width:var(--min-width-input-sm);padding:var(--space-6px) var(--space-2);width:100%}`
- disabled属性あり: 1件 / unconfirmedを持つ: 0件
- 領域: components:1
- ファイル:
  - components/InventoryPicker.tsx : 1
- メンバー(file:line):
  - frontend/src/components/InventoryPicker.tsx:217 [text] style{min-width:var(--min-width-input-sm);padding:var(--space-6px) var(--space-2);width:100%}

### G29（1 件）

- type: {"omitted":1}
- 適用規則:
  - `components.css:19 .form-group input`
  - `components.css:30 .form-group input:focus`
- 静的className: (なし)
- inline style: 1件 `style{min-width:var(--min-width-input-sm)}`
- disabled属性あり: 0件 / unconfirmedを持つ: 0件
- 領域: pages/purchase-orders:1
- ファイル:
  - pages/purchase-orders/PurchaseOrdersFormModal.tsx : 1
- メンバー(file:line):
  - frontend/src/pages/purchase-orders/PurchaseOrdersFormModal.tsx:191 [omitted] style{min-width:var(--min-width-input-sm)}

### G30（1 件）

- type: {"number":1}
- 適用規則:
  - `components.css:19 .form-group input`
  - `components.css:30 .form-group input:focus`
- 静的className: (なし)
- inline style: 1件 `style{width:var(--input-width-qty)}`
- disabled属性あり: 0件 / unconfirmedを持つ: 0件
- 領域: pages/purchase-orders:1
- ファイル:
  - pages/purchase-orders/PurchaseOrdersFormModal.tsx : 1
- メンバー(file:line):
  - frontend/src/pages/purchase-orders/PurchaseOrdersFormModal.tsx:194 [number] style{width:var(--input-width-qty)}

### G31（1 件）

- type: {"number":1}
- 適用規則:
  - `components.css:19 .form-group input`
  - `components.css:30 .form-group input:focus`
- 静的className: (なし)
- inline style: 1件 `style{width:var(--input-width-year)}`
- disabled属性あり: 0件 / unconfirmedを持つ: 0件
- 領域: pages/purchase-orders:1
- ファイル:
  - pages/purchase-orders/PurchaseOrdersFormModal.tsx : 1
- メンバー(file:line):
  - frontend/src/pages/purchase-orders/PurchaseOrdersFormModal.tsx:197 [number] style{width:var(--input-width-year)}

### G32（1 件）

- type: {"text":1}
- 適用規則:
  - `components.css:67 .search-input-field`
  - `components.css:77 .search-input-field::placeholder`
  - `components.css:80 .search-input-field:focus`
  - `pages/inbox/InboxPage.css:116 .inbox-search-input`
- 静的className: `search-input-field` `inbox-search-input`
- inline style: 0件 
- disabled属性あり: 0件 / unconfirmedを持つ: 0件
- 領域: pages/inbox:1
- ファイル:
  - pages/inbox/InboxConversationList.tsx : 1
- メンバー(file:line):
  - frontend/src/pages/inbox/InboxConversationList.tsx:62 [text] className="search-input-field inbox-search-input"

### G33（1 件）

- type: {"text":1}
- 適用規則:
  - `components/field-size.css:13 .field-w-sm`
  - `components/field-size.css:22 .content-toolbar .field-w-sm`
  - `components/field-size.css:8 .field-h-md`
- 静的className: `search-input` `field-h-md` `field-w-sm`
- inline style: 0件 
- disabled属性あり: 0件 / unconfirmedを持つ: 0件
- 領域: pages/contacts:1
- ファイル:
  - pages/contacts/ContactsPage.tsx : 1
- メンバー(file:line):
  - frontend/src/pages/contacts/ContactsPage.tsx:281 [text] className="search-input field-h-md field-w-sm"

### G34（1 件）

- type: {"omitted":1}
- 適用規則:
  - `features/tcg-analysis-review/source-raw-pane.css:48 .source-search input`
- 静的className: (なし)
- inline style: 0件 
- disabled属性あり: 0件 / unconfirmedを持つ: 1件
- 領域: features/tcg-analysis-review:1
- ファイル:
  - features/tcg-analysis-review/SourceRawPane.tsx : 1
- メンバー(file:line):
  - frontend/src/features/tcg-analysis-review/SourceRawPane.tsx:30 [omitted]

### G35（1 件）

- type: {"number":1}
- 適用規則:
  - `pages/goal-setting/GoalSettingPage.css:119 .gs-advisor__monthly-input`
  - `pages/goal-setting/GoalSettingPage.css:510 .gs-input`
  - `pages/goal-setting/GoalSettingPage.css:522 .gs-input:focus`
- 静的className: `gs-input` `gs-advisor__monthly-input`
- inline style: 0件 
- disabled属性あり: 0件 / unconfirmedを持つ: 0件
- 領域: pages/goal-setting:1
- ファイル:
  - pages/goal-setting/GoalSettingPage.tsx : 1
- メンバー(file:line):
  - frontend/src/pages/goal-setting/GoalSettingPage.tsx:334 [number] className="gs-input gs-advisor__monthly-input"

### G36（1 件）

- type: {"number":1}
- 適用規則:
  - `pages/goal-setting/GoalSettingPage.css:277 .gs-advisor__metric-input`
  - `pages/goal-setting/GoalSettingPage.css:281 .gs-advisor__metric-input:focus-visible`
  - `pages/goal-setting/GoalSettingPage.css:510 .gs-input`
  - `pages/goal-setting/GoalSettingPage.css:522 .gs-input:focus`
- 静的className: `gs-input` `gs-advisor__metric-input`
- inline style: 0件 
- disabled属性あり: 0件 / unconfirmedを持つ: 0件
- 領域: pages/goal-setting:1
- ファイル:
  - pages/goal-setting/GoalSettingPage.tsx : 1
- メンバー(file:line):
  - frontend/src/pages/goal-setting/GoalSettingPage.tsx:230 [number] className="gs-input gs-advisor__metric-input"

### G37（1 件）

- type: {"number":1}
- 適用規則:
  - `pages/goal-setting/GoalSettingPage.css:510 .gs-input`
  - `pages/goal-setting/GoalSettingPage.css:522 .gs-input:focus`
  - `pages/goal-setting/GoalSettingPage.css:527 .gs-input.gs-input-saved ?conditional-class`
- 静的className: `gs-input`
- inline style: 0件 
- disabled属性あり: 0件 / unconfirmedを持つ: 0件
- 領域: pages/goal-setting:1
- ファイル:
  - pages/goal-setting/GoalSettingPage.tsx : 1
- メンバー(file:line):
  - frontend/src/pages/goal-setting/GoalSettingPage.tsx:157 [number] className={`gs-input${saved ? " gs-input-saved" : ""}`}

### G38（1 件）

- type: {"date":1}
- 適用規則:
  - `pages/inbox/InboxPage.css:1160 .right-panel-field`
  - `pages/inbox/InboxPage.css:1168 .right-panel-field::placeholder`
  - `pages/inbox/InboxPage.css:1169 .right-panel-field:focus`
  - `pages/inbox/InboxPage.css:1339 input[type="date"].karte-field-empty:not(:focus)::-webkit-datetime-edit ?conditional-class`
- 静的className: `right-panel-field`
- inline style: 0件 
- disabled属性あり: 0件 / unconfirmedを持つ: 0件
- 領域: pages/inbox:1
- ファイル:
  - pages/inbox/InboxKartePanel.tsx : 1
- メンバー(file:line):
  - frontend/src/pages/inbox/InboxKartePanel.tsx:509 [date] className={`right-panel-field${!cardForm.next_action_date ? " karte-field-empty" : ""}`}

### G39（1 件）

- type: {"text":1}
- 適用規則:
  - `pages/inbox/InboxPage.css:1160 .right-panel-field`
  - `pages/inbox/InboxPage.css:1168 .right-panel-field::placeholder`
  - `pages/inbox/InboxPage.css:1169 .right-panel-field:focus`
  - `pages/inbox/InboxPage.css:1630 .sales-form-other-input`
- 静的className: `right-panel-field` `sales-form-other-input`
- inline style: 0件 
- disabled属性あり: 0件 / unconfirmedを持つ: 0件
- 領域: pages/inbox:1
- ファイル:
  - pages/inbox/SalesFormMultiSelect.tsx : 1
- メンバー(file:line):
  - frontend/src/pages/inbox/SalesFormMultiSelect.tsx:148 [text] className="right-panel-field sales-form-other-input"

### G40（1 件）

- type: {"number":1}
- 適用規則:
  - `pages/super-admin/components/AnalysisDashboardPanel.css:75 .analysis-dashboard-window-input`
- 静的className: `analysis-dashboard-window-input`
- inline style: 0件 
- disabled属性あり: 0件 / unconfirmedを持つ: 0件
- 領域: pages/super-admin:1
- ファイル:
  - pages/super-admin/components/AnalysisDashboardPanel.tsx : 1
- メンバー(file:line):
  - frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:803 [number] className="analysis-dashboard-window-input"

### G41（1 件）

- type: {"text":1}
- 適用規則:
  - (なし)
- 静的className: (なし)
- inline style: 1件 `style{background:var(--bg-primary);border-radius:4px;border:1px solid var(--border-color);box-sizing:border-box;color:var(--text-primary);font-size:0.85rem;margin-bottom:0.5rem;padding:0.4rem 0.6rem;width:100%}`
- disabled属性あり: 0件 / unconfirmedを持つ: 0件
- 領域: features/tcg-import-review:1
- ファイル:
  - features/tcg-import-review/ReviewSection.tsx : 1
- メンバー(file:line):
  - frontend/src/features/tcg-import-review/ReviewSection.tsx:289 [text] style{background:var(--bg-primary);border-radius:4px;border:1px solid var(--border-color);box-sizing:border-box;color:var(--text-primary);font-size:0.85rem;margin-bottom:0.5rem;padding:0.4rem 0.6rem;width:100%}

### G42（1 件）

- type: {"number":1}
- 適用規則:
  - (なし)
- 静的className: (なし)
- inline style: 1件 `style{background:var(--bg-primary);border-radius:4px;border:1px solid var(--border-color);color:var(--text-primary);font-size:0.85rem;padding:0.4rem 0.6rem;width:80px}`
- disabled属性あり: 0件 / unconfirmedを持つ: 0件
- 領域: pages/super-admin:1
- ファイル:
  - pages/super-admin/TcgLineImportPage.tsx : 1
- メンバー(file:line):
  - frontend/src/pages/super-admin/TcgLineImportPage.tsx:353 [number] style{background:var(--bg-primary);border-radius:4px;border:1px solid var(--border-color);color:var(--text-primary);font-size:0.85rem;padding:0.4rem 0.6rem;width:80px}

### G43（1 件）

- type: {"number":1}
- 適用規則:
  - (なし)
- 静的className: (なし)
- inline style: 1件 `style{border-radius:4px;border:1px solid var(--border);font-size:13px;padding:6px 8px;width:100px}`
- disabled属性あり: 0件 / unconfirmedを持つ: 0件
- 領域: components:1
- ファイル:
  - components/FedExRateModal.tsx : 1
- メンバー(file:line):
  - frontend/src/components/FedExRateModal.tsx:210 [number] style{border-radius:4px;border:1px solid var(--border);font-size:13px;padding:6px 8px;width:100px}

### G44（1 件）

- type: {"text":1}
- 適用規則:
  - (なし)
- 静的className: (なし)
- inline style: 1件 `style{border-radius:4px;border:1px solid var(--border);font-size:13px;padding:6px 8px;width:160px}`
- disabled属性あり: 0件 / unconfirmedを持つ: 0件
- 領域: components:1
- ファイル:
  - components/FedExRateModal.tsx : 1
- メンバー(file:line):
  - frontend/src/components/FedExRateModal.tsx:239 [text] style{border-radius:4px;border:1px solid var(--border);font-size:13px;padding:6px 8px;width:160px}

### G45（1 件）

- type: {"omitted":1}
- 適用規則:
  - (なし)
- 静的className: (なし)
- inline style: 1件 `style{border-radius:var(--radius-sm);border:1px solid var(--border);flex:1;font-size:var(--font-sm);padding:var(--space-2)}`
- disabled属性あり: 0件 / unconfirmedを持つ: 0件
- 領域: pages/invoice-detail:1
- ファイル:
  - pages/invoice-detail/InvoiceDetailPage.tsx : 1
- メンバー(file:line):
  - frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx:222 [omitted] style{border-radius:var(--radius-sm);border:1px solid var(--border);flex:1;font-size:var(--font-sm);padding:var(--space-2)}

### G46（1 件）

- type: {"omitted":1}
- 適用規則:
  - (なし)
- 静的className: (なし)
- inline style: 1件 `style{border-radius:var(--radius-sm);border:1px solid var(--border);padding:var(--space-2);width:100%}`
- disabled属性あり: 0件 / unconfirmedを持つ: 0件
- 領域: pages/invoice-detail:1
- ファイル:
  - pages/invoice-detail/InvoiceDetailPage.tsx : 1
- メンバー(file:line):
  - frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx:271 [omitted] style{border-radius:var(--radius-sm);border:1px solid var(--border);padding:var(--space-2);width:100%}

### G47（1 件）

- type: {"text":1}
- 適用規則:
  - (なし)
- 静的className: (なし)
- inline style: 1件 `style{flex:1;min-width:var(--min-width-input-sm);padding:var(--space-6px) var(--space-2)}`
- disabled属性あり: 1件 / unconfirmedを持つ: 0件
- 領域: components:1
- ファイル:
  - components/InventorySearchBar.tsx : 1
- メンバー(file:line):
  - frontend/src/components/InventorySearchBar.tsx:272 [text] style{flex:1;min-width:var(--min-width-input-sm);padding:var(--space-6px) var(--space-2)}
