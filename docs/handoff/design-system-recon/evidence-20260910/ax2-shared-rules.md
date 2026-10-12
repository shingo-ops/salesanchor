# AX-2 共有・孤立する CSS 規則（ax2-shared.cjs。AST + postcss、origin/main dfcd31c05）

対象: ax2-applied-css.json で page 側 textarea53件のいずれかに適用された規則 26 本（file:line 単位）。
候補要素: raw <textarea> 53 / <Textarea> 金型利用 13（金型は祖先 div.comp-field + textarea.comp-field__textarea として判定）/ raw <input> 449 / <TextField|TextFieldControl> 利用 220。
「definite」= 祖先まで一致が確定、「unconfirmed」= 属性/関数擬似クラス（:not([type=...]) 等）または祖先を静的に確定できず。
「残る宣言」= その規則から textarea 側セレクタ（と textarea 専用の宣言ブロック）を取り除いたとき、残りのセレクタ（input 等）に残る宣言。

## company-forms.css:154

- セレクタ全文: `.modal-content .form-row input:not([type="checkbox"]):not([type="radio"]), .modal-content .form-row textarea, .modal-content-wide .form-row input:not([type="checkbox"]):not([type="radio"]), .modal-content-wide .form-row textarea`（状態: base）
- 宣言: padding: var(--space-2) var(--space-3); border: 1px solid var(--border-strong); border-radius: var(--radius-md); font-size: var(--font-base); background: var(--bg-surface); color: var(--text-primary); width: 100%; box-sizing: border-box; font-family: inherit
- 適用先 raw textarea(53のうち): 4 件 — components/MergeLeadModal.tsx:234, pages/companies/CompaniesPage.tsx:499, pages/companies/CompaniesPage.tsx:516, pages/contacts/ContactsPage.tsx:349
- 選択子 `.modal-content .form-row input:not([type="checkbox"]):not([type="radio"])`:
  - raw <input>: definite 0 / unconfirmed 4
  - <TextField> mold usages: definite 0 / unconfirmed 0
- 選択子 `.modal-content .form-row textarea`:
  - rawTextarea(page-side 53): definite 0 / unconfirmed 0
  - <Textarea> mold usages(13): definite 0 / unconfirmed 0
- 選択子 `.modal-content-wide .form-row input:not([type="checkbox"]):not([type="radio"])`:
  - raw <input>: definite 0 / unconfirmed 40
  - <TextField> mold usages: definite 0 / unconfirmed 13
- 選択子 `.modal-content-wide .form-row textarea`:
  - rawTextarea(page-side 53): definite 4 / unconfirmed 0（例 frontend/src/components/MergeLeadModal.tsx:234, frontend/src/pages/companies/CompaniesPage.tsx:499, frontend/src/pages/companies/CompaniesPage.tsx:516, frontend/src/pages/contacts/ContactsPage.tsx:349）
  - <Textarea> mold usages(13): definite 1 / unconfirmed 0（例 frontend/src/components/MergeCompanyModal.tsx:246）
- 残る: `.modal-content .form-row input:not([type="checkbox"]):not([type="radio"])`, `.modal-content-wide .form-row input:not([type="checkbox"]):not([type="radio"])` に上記宣言すべてが残る（宣言は共有）

## company-forms.css:169

- セレクタ全文: `.modal-content .form-row textarea, .modal-content-wide .form-row textarea`（状態: base）
- 宣言: min-height: var(--textarea-min-h); resize: vertical
- 適用先 raw textarea(53のうち): 4 件 — components/MergeLeadModal.tsx:234, pages/companies/CompaniesPage.tsx:499, pages/companies/CompaniesPage.tsx:516, pages/contacts/ContactsPage.tsx:349
- 選択子 `.modal-content .form-row textarea`:
  - rawTextarea(page-side 53): definite 0 / unconfirmed 0
  - <Textarea> mold usages(13): definite 0 / unconfirmed 0
- 選択子 `.modal-content-wide .form-row textarea`:
  - rawTextarea(page-side 53): definite 4 / unconfirmed 0（例 frontend/src/components/MergeLeadModal.tsx:234, frontend/src/pages/companies/CompaniesPage.tsx:499, frontend/src/pages/companies/CompaniesPage.tsx:516, frontend/src/pages/contacts/ContactsPage.tsx:349）
  - <Textarea> mold usages(13): definite 1 / unconfirmed 0（例 frontend/src/components/MergeCompanyModal.tsx:246）
- 残るセレクタなし＝この規則は textarea だけが使う。textarea 側を外す（または金型へ移す）と規則ごと孤立（削除可）。金型 <Textarea> 利用への適用件数は上記のとおり（削除すると金型利用側の見え方も変わる）

## company-forms.css:177

- セレクタ全文: `.modal-content .form-row input:focus, .modal-content .form-row textarea:focus, .modal-content-wide .form-row input:focus, .modal-content-wide .form-row textarea:focus`（状態: self:focus）
- 宣言: outline: none; border-color: var(--accent); box-shadow: var(--focus-ring-shadow)
- 適用先 raw textarea(53のうち): 4 件 — components/MergeLeadModal.tsx:234, pages/companies/CompaniesPage.tsx:499, pages/companies/CompaniesPage.tsx:516, pages/contacts/ContactsPage.tsx:349
- 選択子 `.modal-content .form-row input:focus`:
  - raw <input>: definite 0 / unconfirmed 4
  - <TextField> mold usages: definite 0 / unconfirmed 0
- 選択子 `.modal-content .form-row textarea:focus`:
  - rawTextarea(page-side 53): definite 0 / unconfirmed 0
  - <Textarea> mold usages(13): definite 0 / unconfirmed 0
- 選択子 `.modal-content-wide .form-row input:focus`:
  - raw <input>: definite 35 / unconfirmed 5（例 frontend/src/components/MergeLeadModal.tsx:145, frontend/src/pages/companies/CompaniesPage.tsx:451, frontend/src/pages/companies/CompaniesPage.tsx:455, frontend/src/pages/companies/CompaniesPage.tsx:459）
  - <TextField> mold usages: definite 13 / unconfirmed 0（例 frontend/src/components/MergeCompanyModal.tsx:158, frontend/src/pages/company-detail/CompanyAddressModal.tsx:96, frontend/src/pages/company-detail/CompanyAddressModal.tsx:100, frontend/src/pages/company-detail/CompanyAddressModal.tsx:104）
- 選択子 `.modal-content-wide .form-row textarea:focus`:
  - rawTextarea(page-side 53): definite 4 / unconfirmed 0（例 frontend/src/components/MergeLeadModal.tsx:234, frontend/src/pages/companies/CompaniesPage.tsx:499, frontend/src/pages/companies/CompaniesPage.tsx:516, frontend/src/pages/contacts/ContactsPage.tsx:349）
  - <Textarea> mold usages(13): definite 1 / unconfirmed 0（例 frontend/src/components/MergeCompanyModal.tsx:246）
- 残る: `.modal-content .form-row input:focus`, `.modal-content-wide .form-row input:focus` に上記宣言すべてが残る（宣言は共有）

## components.css:19

- セレクタ全文: `.form-group input, .form-group textarea`（状態: base）
- 宣言: width: 100%; padding: var(--space-2) var(--space-3); border: 1px solid var(--border); border-radius: var(--radius-sm); font-size: var(--font-base); color: var(--text-primary); background: var(--bg-surface); box-sizing: border-box
- 適用先 raw textarea(53のうち): 27 件 — components/OrderFinancialPanel.tsx:239, components/PriorityScoreOverride.tsx:91, components/PurchaseDetailPanel.tsx:442, components/ShippingDetailPanel.tsx:551, pages/admin/TenantProfilePage.tsx:170, pages/badges/BadgesPage.tsx:62, pages/buddy/BuddyPage.tsx:66, pages/companies/CompanyFormFields.tsx:64, pages/conditions/ConditionsPage.tsx:340, pages/conditions/ConditionsPage.tsx:350, pages/contacts/ContactEditPage.tsx:191, pages/leads/LeadEditPage.tsx:279, pages/leads/LeadFormFields.tsx:84, pages/leads/LeadFormFields.tsx:153, pages/leads/LeadsPage.tsx:429, pages/orders/OrdersFormModal.tsx:95, pages/products/ProductEditPage.tsx:309, pages/purchase-orders/PurchaseOrdersFormModal.tsx:217, pages/roles/RolesPage.tsx:538, pages/staff-reports/StaffReportsPage.tsx:90, pages/staff-reports/StaffReportsPage.tsx:91, pages/staff-reports/StaffReportsPage.tsx:92, pages/super-admin/components/ConditionsMasterPanel.tsx:367, pages/super-admin/components/ConditionsMasterPanel.tsx:380, pages/suppliers/SupplierFormFields.tsx:61, pages/suppliers/SupplierFormFields.tsx:68, pages/teams/TeamFormFields.tsx:44
- 選択子 `.form-group input`:
  - raw <input>: definite 166 / unconfirmed 29（例 frontend/src/components/ChannelTypeCombobox.tsx:91, frontend/src/components/CountryCombobox.tsx:90, frontend/src/components/InventoryPicker.tsx:217, frontend/src/components/OrderFinancialPanel.tsx:222）
  - <TextField> mold usages: definite 99 / unconfirmed 23（例 frontend/src/pages/conditions/ConditionsPage.tsx:306, frontend/src/pages/conditions/ConditionsPage.tsx:314, frontend/src/pages/conditions/ConditionsPage.tsx:322, frontend/src/pages/conditions/ConditionsPage.tsx:329）
- 選択子 `.form-group textarea`:
  - rawTextarea(page-side 53): definite 27 / unconfirmed 0（例 frontend/src/components/OrderFinancialPanel.tsx:239, frontend/src/components/PriorityScoreOverride.tsx:91, frontend/src/components/PurchaseDetailPanel.tsx:442, frontend/src/components/ShippingDetailPanel.tsx:551）
  - <Textarea> mold usages(13): definite 0 / unconfirmed 3
- 残る: `.form-group input` に上記宣言すべてが残る（宣言は共有）

## components.css:31

- セレクタ全文: `.form-group input:focus, .form-group textarea:focus`（状態: self:focus）
- 宣言: outline: none; border-color: var(--accent); box-shadow: var(--focus-ring-shadow)
- 適用先 raw textarea(53のうち): 27 件 — components/OrderFinancialPanel.tsx:239, components/PriorityScoreOverride.tsx:91, components/PurchaseDetailPanel.tsx:442, components/ShippingDetailPanel.tsx:551, pages/admin/TenantProfilePage.tsx:170, pages/badges/BadgesPage.tsx:62, pages/buddy/BuddyPage.tsx:66, pages/companies/CompanyFormFields.tsx:64, pages/conditions/ConditionsPage.tsx:340, pages/conditions/ConditionsPage.tsx:350, pages/contacts/ContactEditPage.tsx:191, pages/leads/LeadEditPage.tsx:279, pages/leads/LeadFormFields.tsx:84, pages/leads/LeadFormFields.tsx:153, pages/leads/LeadsPage.tsx:429, pages/orders/OrdersFormModal.tsx:95, pages/products/ProductEditPage.tsx:309, pages/purchase-orders/PurchaseOrdersFormModal.tsx:217, pages/roles/RolesPage.tsx:538, pages/staff-reports/StaffReportsPage.tsx:90, pages/staff-reports/StaffReportsPage.tsx:91, pages/staff-reports/StaffReportsPage.tsx:92, pages/super-admin/components/ConditionsMasterPanel.tsx:367, pages/super-admin/components/ConditionsMasterPanel.tsx:380, pages/suppliers/SupplierFormFields.tsx:61, pages/suppliers/SupplierFormFields.tsx:68, pages/teams/TeamFormFields.tsx:44
- 選択子 `.form-group input:focus`:
  - raw <input>: definite 166 / unconfirmed 29（例 frontend/src/components/ChannelTypeCombobox.tsx:91, frontend/src/components/CountryCombobox.tsx:90, frontend/src/components/InventoryPicker.tsx:217, frontend/src/components/OrderFinancialPanel.tsx:222）
  - <TextField> mold usages: definite 99 / unconfirmed 23（例 frontend/src/pages/conditions/ConditionsPage.tsx:306, frontend/src/pages/conditions/ConditionsPage.tsx:314, frontend/src/pages/conditions/ConditionsPage.tsx:322, frontend/src/pages/conditions/ConditionsPage.tsx:329）
- 選択子 `.form-group textarea:focus`:
  - rawTextarea(page-side 53): definite 27 / unconfirmed 0（例 frontend/src/components/OrderFinancialPanel.tsx:239, frontend/src/components/PriorityScoreOverride.tsx:91, frontend/src/components/PurchaseDetailPanel.tsx:442, frontend/src/components/ShippingDetailPanel.tsx:551）
  - <Textarea> mold usages(13): definite 0 / unconfirmed 3
- 残る: `.form-group input:focus` に上記宣言すべてが残る（宣言は共有）

## components.css:39

- セレクタ全文: `.form-group textarea`（状態: base）
- 宣言: min-height: var(--textarea-min-h); resize: vertical
- 適用先 raw textarea(53のうち): 27 件 — components/OrderFinancialPanel.tsx:239, components/PriorityScoreOverride.tsx:91, components/PurchaseDetailPanel.tsx:442, components/ShippingDetailPanel.tsx:551, pages/admin/TenantProfilePage.tsx:170, pages/badges/BadgesPage.tsx:62, pages/buddy/BuddyPage.tsx:66, pages/companies/CompanyFormFields.tsx:64, pages/conditions/ConditionsPage.tsx:340, pages/conditions/ConditionsPage.tsx:350, pages/contacts/ContactEditPage.tsx:191, pages/leads/LeadEditPage.tsx:279, pages/leads/LeadFormFields.tsx:84, pages/leads/LeadFormFields.tsx:153, pages/leads/LeadsPage.tsx:429, pages/orders/OrdersFormModal.tsx:95, pages/products/ProductEditPage.tsx:309, pages/purchase-orders/PurchaseOrdersFormModal.tsx:217, pages/roles/RolesPage.tsx:538, pages/staff-reports/StaffReportsPage.tsx:90, pages/staff-reports/StaffReportsPage.tsx:91, pages/staff-reports/StaffReportsPage.tsx:92, pages/super-admin/components/ConditionsMasterPanel.tsx:367, pages/super-admin/components/ConditionsMasterPanel.tsx:380, pages/suppliers/SupplierFormFields.tsx:61, pages/suppliers/SupplierFormFields.tsx:68, pages/teams/TeamFormFields.tsx:44
- 選択子 `.form-group textarea`:
  - rawTextarea(page-side 53): definite 27 / unconfirmed 0（例 frontend/src/components/OrderFinancialPanel.tsx:239, frontend/src/components/PriorityScoreOverride.tsx:91, frontend/src/components/PurchaseDetailPanel.tsx:442, frontend/src/components/ShippingDetailPanel.tsx:551）
  - <Textarea> mold usages(13): definite 0 / unconfirmed 3
- 残るセレクタなし＝この規則は textarea だけが使う。textarea 側を外す（または金型へ移す）と規則ごと孤立（削除可）。金型 <Textarea> 利用への適用件数は上記のとおり（削除すると金型利用側の見え方も変わる）

## features/tcg-analysis-review/supplier-detail-view.css:244

- セレクタ全文: `.pmd-field input, .pmd-field textarea`（状態: base）
- 宣言: border: 1px solid var(--border); border-radius: var(--radius-md); background: var(--bg-surface); padding: var(--space-2); font: inherit; width: 100%; box-sizing: border-box
- 適用先 raw textarea(53のうち): 2 件 — features/tcg-analysis-review/ProductMasterDrawer.tsx:217, features/tcg-analysis-review/ProductMasterDrawer.tsx:221
- 選択子 `.pmd-field input`:
  - raw <input>: definite 7 / unconfirmed 43（例 frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:68, frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:201, frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:205, frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:209）
  - <TextField> mold usages: definite 0 / unconfirmed 29
- 選択子 `.pmd-field textarea`:
  - rawTextarea(page-side 53): definite 2 / unconfirmed 3（例 frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:217, frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:221）
  - <Textarea> mold usages(13): definite 0 / unconfirmed 3
- 残る: `.pmd-field input` に上記宣言すべてが残る（宣言は共有）

## features/tcg-analysis-review/supplier-detail-view.css:255

- セレクタ全文: `.pmd-field textarea`（状態: base）
- 宣言: min-height: var(--pmd-textarea-min-h); resize: vertical
- 適用先 raw textarea(53のうち): 2 件 — features/tcg-analysis-review/ProductMasterDrawer.tsx:217, features/tcg-analysis-review/ProductMasterDrawer.tsx:221
- 選択子 `.pmd-field textarea`:
  - rawTextarea(page-side 53): definite 2 / unconfirmed 3（例 frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:217, frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:221）
  - <Textarea> mold usages(13): definite 0 / unconfirmed 3
- 残るセレクタなし＝この規則は textarea だけが使う。textarea 側を外す（または金型へ移す）と規則ごと孤立（削除可）。金型 <Textarea> 利用への適用件数は上記のとおり（削除すると金型利用側の見え方も変わる）

## company-forms.css:100

- セレクタ全文: `.form-grid > .form-row input:not([type="checkbox"]):not([type="radio"]), .form-grid > .form-row textarea`（状態: base）
- 宣言: padding: var(--space-2) var(--space-3); border: 1px solid var(--border-strong); border-radius: var(--radius-md); font-size: var(--font-base); background: var(--bg-surface); color: var(--text-primary); width: 100%; box-sizing: border-box; font-family: inherit
- 適用先 raw textarea(53のうち): 5 件 — pages/companies/CompaniesPage.tsx:499, pages/companies/CompaniesPage.tsx:516, pages/company-detail/CompanyBasicTab.tsx:81, pages/company-detail/CompanyBasicTab.tsx:94, pages/contacts/ContactsPage.tsx:349
- 選択子 `.form-grid > .form-row input:not([type="checkbox"]):not([type="radio"])`:
  - raw <input>: definite 0 / unconfirmed 54
  - <TextField> mold usages: definite 0 / unconfirmed 12
- 選択子 `.form-grid > .form-row textarea`:
  - rawTextarea(page-side 53): definite 5 / unconfirmed 0（例 frontend/src/pages/companies/CompaniesPage.tsx:499, frontend/src/pages/companies/CompaniesPage.tsx:516, frontend/src/pages/company-detail/CompanyBasicTab.tsx:81, frontend/src/pages/company-detail/CompanyBasicTab.tsx:94）
  - <Textarea> mold usages(13): definite 0 / unconfirmed 0
- 残る: `.form-grid > .form-row input:not([type="checkbox"]):not([type="radio"])` に上記宣言すべてが残る（宣言は共有）

## company-forms.css:113

- セレクタ全文: `.form-grid > .form-row textarea`（状態: base）
- 宣言: min-height: var(--textarea-min-h); resize: vertical
- 適用先 raw textarea(53のうち): 5 件 — pages/companies/CompaniesPage.tsx:499, pages/companies/CompaniesPage.tsx:516, pages/company-detail/CompanyBasicTab.tsx:81, pages/company-detail/CompanyBasicTab.tsx:94, pages/contacts/ContactsPage.tsx:349
- 選択子 `.form-grid > .form-row textarea`:
  - rawTextarea(page-side 53): definite 5 / unconfirmed 0（例 frontend/src/pages/companies/CompaniesPage.tsx:499, frontend/src/pages/companies/CompaniesPage.tsx:516, frontend/src/pages/company-detail/CompanyBasicTab.tsx:81, frontend/src/pages/company-detail/CompanyBasicTab.tsx:94）
  - <Textarea> mold usages(13): definite 0 / unconfirmed 0
- 残るセレクタなし＝この規則は textarea だけが使う。textarea 側を外す（または金型へ移す）と規則ごと孤立（削除可）。金型 <Textarea> 利用への適用件数は上記のとおり（削除すると金型利用側の見え方も変わる）

## company-forms.css:119

- セレクタ全文: `.form-grid > .form-row input:focus, .form-grid > .form-row textarea:focus`（状態: self:focus）
- 宣言: outline: none; border-color: var(--accent); box-shadow: var(--focus-ring-shadow)
- 適用先 raw textarea(53のうち): 5 件 — pages/companies/CompaniesPage.tsx:499, pages/companies/CompaniesPage.tsx:516, pages/company-detail/CompanyBasicTab.tsx:81, pages/company-detail/CompanyBasicTab.tsx:94, pages/contacts/ContactsPage.tsx:349
- 選択子 `.form-grid > .form-row input:focus`:
  - raw <input>: definite 53 / unconfirmed 1（例 frontend/src/components/ContactChannelForm.tsx:227, frontend/src/pages/companies/CompaniesPage.tsx:451, frontend/src/pages/companies/CompaniesPage.tsx:455, frontend/src/pages/companies/CompaniesPage.tsx:459）
  - <TextField> mold usages: definite 12 / unconfirmed 0（例 frontend/src/pages/company-detail/CompanyAddressModal.tsx:96, frontend/src/pages/company-detail/CompanyAddressModal.tsx:100, frontend/src/pages/company-detail/CompanyAddressModal.tsx:104, frontend/src/pages/company-detail/CompanyAddressModal.tsx:108）
- 選択子 `.form-grid > .form-row textarea:focus`:
  - rawTextarea(page-side 53): definite 5 / unconfirmed 0（例 frontend/src/pages/companies/CompaniesPage.tsx:499, frontend/src/pages/companies/CompaniesPage.tsx:516, frontend/src/pages/company-detail/CompanyBasicTab.tsx:81, frontend/src/pages/company-detail/CompanyBasicTab.tsx:94）
  - <Textarea> mold usages(13): definite 0 / unconfirmed 0
- 残る: `.form-grid > .form-row input:focus` に上記宣言すべてが残る（宣言は共有）

## components/field-size.css:8

- セレクタ全文: `.field-h-md`（状態: base）
- 宣言: min-height: var(--field-h-md, 36px); box-sizing: border-box
- 適用先 raw textarea(53のうち): 2 件 — pages/conditions/ConditionsPage.tsx:340, pages/conditions/ConditionsPage.tsx:350
- 選択子 `.field-h-md`:
  - elements with class .field-h-md: 12 件（タグ別 {"input":6,"textarea":2,"SelectControl":1,"Select":2,"button":1}）例: frontend/src/components/master-list-editor/MasterListEditor.tsx:135 <input>, frontend/src/pages/companies/CompaniesPage.tsx:385 <input>, frontend/src/pages/conditions/ConditionsPage.tsx:340 <textarea>, frontend/src/pages/conditions/ConditionsPage.tsx:350 <textarea>, frontend/src/pages/contacts/ContactsPage.tsx:280 <input>, frontend/src/pages/inventory/InventoryPage.tsx:384 <input>
- 残る: `.field-h-md` (textarea 以外の 10 要素: {"input":6,"SelectControl":1,"Select":2,"button":1}) に上記宣言すべてが残る（宣言は共有）

## pages/dashboard/WeeklyAdvisorSection.css:205

- セレクタ全文: `.db-weekly-composer-input`（状態: base）
- 宣言: width: 100%; border-radius: var(--radius-md); border: 1px solid var(--border-subtle); background: var(--bg-primary); color: var(--text-primary); padding: var(--space-2) var(--space-3); font: inherit; resize: vertical
- 適用先 raw textarea(53のうち): 2 件 — pages/dashboard/PriorityProspectsSection.tsx:410, pages/dashboard/WeeklyAdvisorSection.tsx:381
- 選択子 `.db-weekly-composer-input`:
  - elements with class .db-weekly-composer-input: 4 件（タグ別 {"textarea":2,"input":2}）例: frontend/src/pages/dashboard/PriorityProspectsSection.tsx:410 <textarea>, frontend/src/pages/dashboard/PriorityProspectsSection.tsx:423 <input>, frontend/src/pages/dashboard/WeeklyAdvisorSection.tsx:381 <textarea>, frontend/src/pages/dashboard/WeeklyAdvisorSection.tsx:394 <input>
- 残る: `.db-weekly-composer-input` (textarea 以外の 2 要素: {"input":2}) に上記宣言すべてが残る（宣言は共有）

## pages/dashboard/WeeklyAdvisorSection.css:216

- セレクタ全文: `.db-weekly-composer-input:focus`（状態: self:focus）
- 宣言: outline: 2px solid var(--accent); outline-offset: 1px
- 適用先 raw textarea(53のうち): 2 件 — pages/dashboard/PriorityProspectsSection.tsx:410, pages/dashboard/WeeklyAdvisorSection.tsx:381
- 選択子 `.db-weekly-composer-input:focus`:
  - elements with class .db-weekly-composer-input: 4 件（タグ別 {"textarea":2,"input":2}）例: frontend/src/pages/dashboard/PriorityProspectsSection.tsx:410 <textarea>, frontend/src/pages/dashboard/PriorityProspectsSection.tsx:423 <input>, frontend/src/pages/dashboard/WeeklyAdvisorSection.tsx:381 <textarea>, frontend/src/pages/dashboard/WeeklyAdvisorSection.tsx:394 <input>
- 残る: `.db-weekly-composer-input:focus` (textarea 以外の 2 要素: {"input":2}) に上記宣言すべてが残る（宣言は共有）

## pages/inbox/InboxPage.css:1171

- セレクタ全文: `.right-panel-field`（状態: base）
- 宣言: width: 100%; box-sizing: border-box; background: var(--karte-field-bg); border: 0.5px solid var(--karte-field-bd); border-radius: var(--radius-md); padding: var(--karte-field-py) var(--karte-field-px); font-size: var(--font-sm); color: var(--text-primary); font-family: inherit; transition: border-color var(--transition-micro)
- 適用先 raw textarea(53のうち): 8 件 — pages/inbox/InboxKartePanel.tsx:484, pages/inbox/InboxKartePanel.tsx:503, pages/inbox/InboxKartePanel.tsx:537, pages/inbox/InboxKartePanel.tsx:588, pages/inbox/InboxProfileModal.tsx:181, pages/inbox/InboxProfileModal.tsx:191, pages/inbox/InboxProfileModal.tsx:210, pages/inbox/InboxProfileModal.tsx:265
- 選択子 `.right-panel-field`:
  - elements with class .right-panel-field: 34 件（タグ別 {"a":1,"input":24,"textarea":8,"button":1}）例: frontend/src/pages/inbox/InboxKartePanel.tsx:359 <a>, frontend/src/pages/inbox/InboxKartePanel.tsx:371 <input>, frontend/src/pages/inbox/InboxKartePanel.tsx:378 <input>, frontend/src/pages/inbox/InboxKartePanel.tsx:385 <input>, frontend/src/pages/inbox/InboxKartePanel.tsx:403 <input>, frontend/src/pages/inbox/InboxKartePanel.tsx:436 <input>
- 残る: `.right-panel-field` (textarea 以外の 26 要素: {"a":1,"input":24,"button":1}) に上記宣言すべてが残る（宣言は共有）

## pages/inbox/InboxPage.css:1179

- セレクタ全文: `.right-panel-field::placeholder`（状態: self::placeholder）
- 宣言: color: var(--text-muted)
- 適用先 raw textarea(53のうち): 8 件 — pages/inbox/InboxKartePanel.tsx:484, pages/inbox/InboxKartePanel.tsx:503, pages/inbox/InboxKartePanel.tsx:537, pages/inbox/InboxKartePanel.tsx:588, pages/inbox/InboxProfileModal.tsx:181, pages/inbox/InboxProfileModal.tsx:191, pages/inbox/InboxProfileModal.tsx:210, pages/inbox/InboxProfileModal.tsx:265
- 選択子 `.right-panel-field::placeholder`:
  - elements with class .right-panel-field: 34 件（タグ別 {"a":1,"input":24,"textarea":8,"button":1}）例: frontend/src/pages/inbox/InboxKartePanel.tsx:359 <a>, frontend/src/pages/inbox/InboxKartePanel.tsx:371 <input>, frontend/src/pages/inbox/InboxKartePanel.tsx:378 <input>, frontend/src/pages/inbox/InboxKartePanel.tsx:385 <input>, frontend/src/pages/inbox/InboxKartePanel.tsx:403 <input>, frontend/src/pages/inbox/InboxKartePanel.tsx:436 <input>
- 残る: `.right-panel-field::placeholder` (textarea 以外の 26 要素: {"a":1,"input":24,"button":1}) に上記宣言すべてが残る（宣言は共有）

## pages/inbox/InboxPage.css:1180

- セレクタ全文: `.right-panel-field:focus`（状態: self:focus）
- 宣言: outline: none; border-color: var(--accent)
- 適用先 raw textarea(53のうち): 8 件 — pages/inbox/InboxKartePanel.tsx:484, pages/inbox/InboxKartePanel.tsx:503, pages/inbox/InboxKartePanel.tsx:537, pages/inbox/InboxKartePanel.tsx:588, pages/inbox/InboxProfileModal.tsx:181, pages/inbox/InboxProfileModal.tsx:191, pages/inbox/InboxProfileModal.tsx:210, pages/inbox/InboxProfileModal.tsx:265
- 選択子 `.right-panel-field:focus`:
  - elements with class .right-panel-field: 34 件（タグ別 {"a":1,"input":24,"textarea":8,"button":1}）例: frontend/src/pages/inbox/InboxKartePanel.tsx:359 <a>, frontend/src/pages/inbox/InboxKartePanel.tsx:371 <input>, frontend/src/pages/inbox/InboxKartePanel.tsx:378 <input>, frontend/src/pages/inbox/InboxKartePanel.tsx:385 <input>, frontend/src/pages/inbox/InboxKartePanel.tsx:403 <input>, frontend/src/pages/inbox/InboxKartePanel.tsx:436 <input>
- 残る: `.right-panel-field:focus` (textarea 以外の 26 要素: {"a":1,"input":24,"button":1}) に上記宣言すべてが残る（宣言は共有）

## pages/inbox/InboxPage.css:1181

- セレクタ全文: `textarea.right-panel-field`（状態: base）
- 宣言: resize: none; min-height: var(--inbox-textarea-min-h)
- 適用先 raw textarea(53のうち): 8 件 — pages/inbox/InboxKartePanel.tsx:484, pages/inbox/InboxKartePanel.tsx:503, pages/inbox/InboxKartePanel.tsx:537, pages/inbox/InboxKartePanel.tsx:588, pages/inbox/InboxProfileModal.tsx:181, pages/inbox/InboxProfileModal.tsx:191, pages/inbox/InboxProfileModal.tsx:210, pages/inbox/InboxProfileModal.tsx:265
- 選択子 `textarea.right-panel-field`:
  - rawTextarea(page-side 53): definite 8 / unconfirmed 0（例 frontend/src/pages/inbox/InboxKartePanel.tsx:484, frontend/src/pages/inbox/InboxKartePanel.tsx:503, frontend/src/pages/inbox/InboxKartePanel.tsx:537, frontend/src/pages/inbox/InboxKartePanel.tsx:588）
  - <Textarea> mold usages(13): definite 0 / unconfirmed 0
- 残るセレクタなし＝この規則は textarea だけが使う。textarea 側を外す（または金型へ移す）と規則ごと孤立（削除可）。金型 <Textarea> 利用への適用件数は上記のとおり（削除すると金型利用側の見え方も変わる）

## pages/inbox/InboxPage.css:633

- セレクタ全文: `.inbox-textarea`（状態: base）
- 宣言: flex: 1; min-width: 0; border: none; padding: 0; font-size: var(--font-base); resize: none; font-family: inherit; outline: none; background: transparent; color: var(--text-primary); box-sizing: border-box; line-height: 1.4
- 適用先 raw textarea(53のうち): 1 件 — pages/inbox/InboxMessageThread.tsx:736
- 選択子 `.inbox-textarea`:
  - elements with class .inbox-textarea: 1 件（タグ別 {"textarea":1}）例: frontend/src/pages/inbox/InboxMessageThread.tsx:736 <textarea>
- 残るセレクタなし＝この規則は textarea だけが使う。textarea 側を外す（または金型へ移す）と規則ごと孤立（削除可）

## pages/inbox/InboxPage.css:647

- セレクタ全文: `.inbox-textarea:disabled`（状態: self:disabled）
- 宣言: cursor: not-allowed; opacity: var(--opacity-disabled)
- 適用先 raw textarea(53のうち): 1 件 — pages/inbox/InboxMessageThread.tsx:736
- 選択子 `.inbox-textarea:disabled`:
  - elements with class .inbox-textarea: 1 件（タグ別 {"textarea":1}）例: frontend/src/pages/inbox/InboxMessageThread.tsx:736 <textarea>
- 残るセレクタなし＝この規則は textarea だけが使う。textarea 側を外す（または金型へ移す）と規則ごと孤立（削除可）

## pages/inbox/InboxPage.css:1529

- セレクタ全文: `.outbound-translation-edit`（状態: base）
- 宣言: width: 100%; padding: var(--space-3); resize: vertical; border: 1px solid var(--border); border-radius: var(--radius-sm); background: var(--bg-input); color: var(--text); font-size: var(--font-sm); line-height: 1.5; font-family: inherit
- 適用先 raw textarea(53のうち): 1 件 — pages/inbox/OutboundTranslationPreview.tsx:147
- 選択子 `.outbound-translation-edit`:
  - elements with class .outbound-translation-edit: 1 件（タグ別 {"textarea":1}）例: frontend/src/pages/inbox/OutboundTranslationPreview.tsx:147 <textarea>
- 残るセレクタなし＝この規則は textarea だけが使う。textarea 側を外す（または金型へ移す）と規則ごと孤立（削除可）

## pages/inbox/InboxPage.css:1535

- セレクタ全文: `.outbound-translation-edit:focus`（状態: self:focus）
- 宣言: outline: none; border-color: var(--accent)
- 適用先 raw textarea(53のうち): 1 件 — pages/inbox/OutboundTranslationPreview.tsx:147
- 選択子 `.outbound-translation-edit:focus`:
  - elements with class .outbound-translation-edit: 1 件（タグ別 {"textarea":1}）例: frontend/src/pages/inbox/OutboundTranslationPreview.tsx:147 <textarea>
- 残るセレクタなし＝この規則は textarea だけが使う。textarea 側を外す（または金型へ移す）と規則ごと孤立（削除可）

## company-forms.css:254

- セレクタ全文: `.product-edit-form .form-group input:not([type="checkbox"]):not([type="radio"]), .product-edit-form .form-group textarea`（状態: base）
- 宣言: border: 1px solid var(--border-strong)
- 適用先 raw textarea(53のうち): 1 件 — pages/products/ProductEditPage.tsx:309
- 選択子 `.product-edit-form .form-group input:not([type="checkbox"]):not([type="radio"])`:
  - raw <input>: definite 0 / unconfirmed 30
  - <TextField> mold usages: definite 0 / unconfirmed 6
- 選択子 `.product-edit-form .form-group textarea`:
  - rawTextarea(page-side 53): definite 1 / unconfirmed 3（例 frontend/src/pages/products/ProductEditPage.tsx:309）
  - <Textarea> mold usages(13): definite 0 / unconfirmed 0
- 残る: `.product-edit-form .form-group input:not([type="checkbox"]):not([type="radio"])` に上記宣言すべてが残る（宣言は共有）

## pages/schedule.css:813

- セレクタ全文: `.schedule-input, .schedule-textarea`（状態: base）
- 宣言: width: 100%; border: 1px solid var(--border); border-radius: var(--radius-md); background: var(--bg-surface); color: var(--text-primary); font-size: var(--font-sm)
- 適用先 raw textarea(53のうち): 1 件 — pages/schedule/SchedulePageImpl.tsx:378
- 選択子 `.schedule-input`:
  - elements with class .schedule-input: 6 件（タグ別 {"input":6}）例: frontend/src/pages/schedule/SchedulePageImpl.tsx:279 <input>, frontend/src/pages/schedule/SchedulePageImpl.tsx:323 <input>, frontend/src/pages/schedule/SchedulePageImpl.tsx:333 <input>, frontend/src/pages/schedule/SchedulePageImpl.tsx:346 <input>, frontend/src/pages/schedule/SchedulePageImpl.tsx:356 <input>, frontend/src/pages/schedule/SchedulePageImpl.tsx:368 <input>
- 選択子 `.schedule-textarea`:
  - elements with class .schedule-textarea: 1 件（タグ別 {"textarea":1}）例: frontend/src/pages/schedule/SchedulePageImpl.tsx:378 <textarea>
- 残る: `.schedule-input` (textarea 以外の 6 要素: {"input":6}) に上記宣言すべてが残る（宣言は共有）

## pages/schedule.css:828

- セレクタ全文: `.schedule-textarea`（状態: base）
- 宣言: padding: var(--space-2) var(--space-3); resize: vertical
- 適用先 raw textarea(53のうち): 1 件 — pages/schedule/SchedulePageImpl.tsx:378
- 選択子 `.schedule-textarea`:
  - elements with class .schedule-textarea: 1 件（タグ別 {"textarea":1}）例: frontend/src/pages/schedule/SchedulePageImpl.tsx:378 <textarea>
- 残るセレクタなし＝この規則は textarea だけが使う。textarea 側を外す（または金型へ移す）と規則ごと孤立（削除可）

## pages/schedule.css:833

- セレクタ全文: `.schedule-input:focus, .schedule-textarea:focus`（状態: self:focus）
- 宣言: outline: none; border-color: var(--accent); box-shadow: var(--focus-ring-shadow)
- 適用先 raw textarea(53のうち): 1 件 — pages/schedule/SchedulePageImpl.tsx:378
- 選択子 `.schedule-input:focus`:
  - elements with class .schedule-input: 6 件（タグ別 {"input":6}）例: frontend/src/pages/schedule/SchedulePageImpl.tsx:279 <input>, frontend/src/pages/schedule/SchedulePageImpl.tsx:323 <input>, frontend/src/pages/schedule/SchedulePageImpl.tsx:333 <input>, frontend/src/pages/schedule/SchedulePageImpl.tsx:346 <input>, frontend/src/pages/schedule/SchedulePageImpl.tsx:356 <input>, frontend/src/pages/schedule/SchedulePageImpl.tsx:368 <input>
- 選択子 `.schedule-textarea:focus`:
  - elements with class .schedule-textarea: 1 件（タグ別 {"textarea":1}）例: frontend/src/pages/schedule/SchedulePageImpl.tsx:378 <textarea>
- 残る: `.schedule-input:focus` (textarea 以外の 6 要素: {"input":6}) に上記宣言すべてが残る（宣言は共有）

