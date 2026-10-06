Base SHA: 3210edeea250e269102bedd3546ebc48ddb89b77 (origin/main snapshot; frontend/src identical at worktree HEAD 3f4dbbdf9, git diff --stat empty)

# AV-2 recon2 (read-only)

- snapshot: origin/main `3210edeea250e269102bedd3546ebc48ddb89b77`; scripts in this dir: av2-r1.cjs (R1), av2-recon2-md.cjs; resolver = av2-project.cjs / av2-css.cjs (unchanged)
- Mold specificity: `.comp-select__control` = (0,1,0), `.comp-field__select` = (0,1,0) (FormField.css:47/74/89/208 and :47/74/85/208); mold `:focus` = (0,2,0) (FormField.css:95), `.comp-field--error .comp-field__select:focus` = (0,3,0) (FormField.css:199).

## R1 usage counts

- JSX usages resolved to components/Select.tsx (import resolves to the file; excl. stories/tests/Select.tsx itself): **86** = `<Select>` 66 + `<SelectControl>` 20.
- Raw grep `<(Select|SelectControl)\b` over *.tsx excl. stories/tests gives 87 lines; the 1 extra is `components/Select.tsx:149` (the `<SelectControl>` inside `Select` itself). The brief's 69+22=91 does not match either number; 未確認 where 91 came from (stories/tests likely).
- Select (field wrapper): rendered DOM is `div.comp-field[+className] > label + select.comp-field__select`; `className` goes to the wrapper div (Select.tsx:120-131), not the select. So page rules match through the wrapper as an ancestor. SelectControl: className goes onto the select itself (Select.tsx:58-68); appearance default `bare` -> `.comp-select__control`.
- Resolver status: `definite` = ancestor chain resolved on every usage chain; `unconfirmed` = e.g. component with no JSX usage found (FormSection, RuleCreateDrawer: referenced outside a JSX tag). Unconfirmed entries are labelled per usage below.

Line numbers for rules = first line of the rule block (postcss rule start); the selector may sit on a later line of a selector list (e.g. components.css:19 block contains `.form-group select,` at :20).

## R1 Inventory: every CSS rule in frontend/src whose last compound is bare `select` (no class/id/attr)

|#|file:line|selector|specificity|pseudo on select|declarations|
|---|---|---|---|---|---|
|1|frontend/src/company-forms.css:100|`.form-grid > .form-row select`|(0,2,1)|-|padding: var(--space-2) var(--space-3) (L103); border: 1px solid var(--border-strong) (L104); border-radius: var(--radius-md) (L105); font-size: var(--font-base) (L106); background: var(--bg-surface) (L107); color: var(--text-primary) (L108); width: 100% (L109); box-sizing: border-box (L110); font-family: inherit (L111)|
|2|frontend/src/company-forms.css:120|`.form-grid > .form-row select:focus`|(0,3,1)|:focus|outline: none (L123); border-color: var(--accent) (L124); box-shadow: var(--focus-ring-shadow) (L125)|
|3|frontend/src/company-forms.css:156|`.modal-content .form-row select`|(0,2,1)|-|padding: var(--space-2) var(--space-3) (L162); border: 1px solid var(--border-strong) (L163); border-radius: var(--radius-md) (L164); font-size: var(--font-base) (L165); background: var(--bg-surface) (L166); color: var(--text-primary) (L167); width: 100% (L168); box-sizing: border-box (L169); font-family: inherit (L170)|
|4|frontend/src/company-forms.css:156|`.modal-content-wide .form-row select`|(0,2,1)|-|padding: var(--space-2) var(--space-3) (L162); border: 1px solid var(--border-strong) (L163); border-radius: var(--radius-md) (L164); font-size: var(--font-base) (L165); background: var(--bg-surface) (L166); color: var(--text-primary) (L167); width: 100% (L168); box-sizing: border-box (L169); font-family: inherit (L170)|
|5|frontend/src/company-forms.css:181|`.modal-content .form-row select:focus`|(0,3,1)|:focus|outline: none (L187); border-color: var(--accent) (L188); box-shadow: var(--focus-ring-shadow) (L189)|
|6|frontend/src/company-forms.css:181|`.modal-content-wide .form-row select:focus`|(0,3,1)|:focus|outline: none (L187); border-color: var(--accent) (L188); box-shadow: var(--focus-ring-shadow) (L189)|
|7|frontend/src/company-forms.css:260|`.product-edit-form .form-group select`|(0,2,1)|-|border: 1px solid var(--border-strong) (L263)|
|8|frontend/src/components.css:19|`.form-group select`|(0,1,1)|-|width: 100% (L22); padding: var(--space-2) var(--space-3) (L23); border: 1px solid var(--border) (L24); border-radius: var(--radius-sm) (L25); font-size: var(--font-base) (L26); color: var(--text-primary) (L27); background: var(--bg-surface) (L28); box-sizing: border-box (L29)|
|9|frontend/src/components.css:32|`.form-group select:focus`|(0,2,1)|:focus|outline: none (L35); border-color: var(--accent) (L36); box-shadow: var(--focus-ring-shadow) (L37)|
|10|frontend/src/components.css:60|`.filter-bar select`|(0,1,1)|-|padding: var(--space-2) var(--space-3) (L62); border: 1px solid var(--border) (L63); border-radius: var(--radius-sm) (L64); font-size: var(--font-base) (L65); min-width: var(--input-select-min-w) (L66); background: var(--bg-surface) (L67); color: var(--text-primary) (L68)|

Total bare-select rules (selector list split): 10 across 3 files (components.css, company-forms.css; no other). No `@media`-gated bare-select rule (media column empty for all). No `:is/:where/:not(...select)` rule (grep). Not bare (tag+class, listed for completeness, not in the counts): `frontend/src/pages/inbox/InboxPage.css:1198 select.right-panel-field { appearance:none; -webkit-appearance:none }` (0,1,1). `DashboardPage.css:29` only mentions select in a comment. Raw `grep -rnE "(^|[ ,>+~(])select\b" --include=*.css` = 12 hits = 10 rules + that 1 + that 1 comment.

## R1 Per rule: specificity vs mold, winner, and matches

### `company-forms.css:100 .form-grid > .form-row select`
- specificity (0,2,1) vs mold (0,1,0): **rule wins (higher specificity)**
- declared: padding: var(--space-2) var(--space-3) (L103); border: 1px solid var(--border-strong) (L104); border-radius: var(--radius-md) (L105); font-size: var(--font-base) (L106); background: var(--bg-surface) (L107); color: var(--text-primary) (L108); width: 100% (L109); box-sizing: border-box (L110); font-family: inherit (L111)
- properties this rule sets that the mold also sets (rule wins): padding, border, border-radius, font-size, background, color, width, box-sizing, font-family; shorthand `padding` also overrides mold padding-right (arrow room, FormField.css:74) at higher specificity; shorthand `background` also resets mold background-image/repeat/position (the chevron, FormField.css:74) at higher specificity
- existing mold usages matched: definite **1**, incl. unconfirmed **1**
  - frontend/src/pages/company-detail/CompanyAddressModal.tsx:84 `<Select>` -> `comp-field__select` definite
- raw `<select>` matched (from av2-select-mapping.json): **4**
  - frontend/src/pages/companies/CompaniesPage.tsx:506 definite
  - frontend/src/pages/company-detail/CompanyBasicTab.tsx:84 definite
  - frontend/src/pages/contacts/ContactsPage.tsx:308 definite
  - frontend/src/pages/contacts/ContactsPage.tsx:341 definite

### `company-forms.css:120 .form-grid > .form-row select:focus`
- specificity (0,3,1) (select:focus) vs mold `:focus` (0,2,0) / `.comp-field--error ... :focus` (0,3,0): **rule wins (higher specificity)**
- declared: outline: none (L123); border-color: var(--accent) (L124); box-shadow: var(--focus-ring-shadow) (L125)
- properties this rule sets that the mold also sets (rule wins): border-color
- existing mold usages matched: definite **1**, incl. unconfirmed **1**
  - frontend/src/pages/company-detail/CompanyAddressModal.tsx:84 `<Select>` -> `comp-field__select` definite
- raw `<select>` matched (from av2-select-mapping.json): **4**
  - frontend/src/pages/companies/CompaniesPage.tsx:506 definite
  - frontend/src/pages/company-detail/CompanyBasicTab.tsx:84 definite
  - frontend/src/pages/contacts/ContactsPage.tsx:308 definite
  - frontend/src/pages/contacts/ContactsPage.tsx:341 definite

### `company-forms.css:156 .modal-content .form-row select`
- specificity (0,2,1) vs mold (0,1,0): **rule wins (higher specificity)**
- declared: padding: var(--space-2) var(--space-3) (L162); border: 1px solid var(--border-strong) (L163); border-radius: var(--radius-md) (L164); font-size: var(--font-base) (L165); background: var(--bg-surface) (L166); color: var(--text-primary) (L167); width: 100% (L168); box-sizing: border-box (L169); font-family: inherit (L170)
- properties this rule sets that the mold also sets (rule wins): padding, border, border-radius, font-size, background, color, width, box-sizing, font-family; shorthand `padding` also overrides mold padding-right (arrow room, FormField.css:74) at higher specificity; shorthand `background` also resets mold background-image/repeat/position (the chevron, FormField.css:74) at higher specificity
- existing mold usages matched: definite **0**, incl. unconfirmed **0**
- raw `<select>` matched (from av2-select-mapping.json): **0**

### `company-forms.css:156 .modal-content-wide .form-row select`
- specificity (0,2,1) vs mold (0,1,0): **rule wins (higher specificity)**
- declared: padding: var(--space-2) var(--space-3) (L162); border: 1px solid var(--border-strong) (L163); border-radius: var(--radius-md) (L164); font-size: var(--font-base) (L165); background: var(--bg-surface) (L166); color: var(--text-primary) (L167); width: 100% (L168); box-sizing: border-box (L169); font-family: inherit (L170)
- properties this rule sets that the mold also sets (rule wins): padding, border, border-radius, font-size, background, color, width, box-sizing, font-family; shorthand `padding` also overrides mold padding-right (arrow room, FormField.css:74) at higher specificity; shorthand `background` also resets mold background-image/repeat/position (the chevron, FormField.css:74) at higher specificity
- existing mold usages matched: definite **1**, incl. unconfirmed **1**
  - frontend/src/pages/company-detail/CompanyAddressModal.tsx:84 `<Select>` -> `comp-field__select` definite
- raw `<select>` matched (from av2-select-mapping.json): **3**
  - frontend/src/pages/companies/CompaniesPage.tsx:506 definite
  - frontend/src/pages/contacts/ContactsPage.tsx:308 definite
  - frontend/src/pages/contacts/ContactsPage.tsx:341 definite

### `company-forms.css:181 .modal-content .form-row select:focus`
- specificity (0,3,1) (select:focus) vs mold `:focus` (0,2,0) / `.comp-field--error ... :focus` (0,3,0): **rule wins (higher specificity)**
- declared: outline: none (L187); border-color: var(--accent) (L188); box-shadow: var(--focus-ring-shadow) (L189)
- properties this rule sets that the mold also sets (rule wins): border-color
- existing mold usages matched: definite **0**, incl. unconfirmed **0**
- raw `<select>` matched (from av2-select-mapping.json): **0**

### `company-forms.css:181 .modal-content-wide .form-row select:focus`
- specificity (0,3,1) (select:focus) vs mold `:focus` (0,2,0) / `.comp-field--error ... :focus` (0,3,0): **rule wins (higher specificity)**
- declared: outline: none (L187); border-color: var(--accent) (L188); box-shadow: var(--focus-ring-shadow) (L189)
- properties this rule sets that the mold also sets (rule wins): border-color
- existing mold usages matched: definite **1**, incl. unconfirmed **1**
  - frontend/src/pages/company-detail/CompanyAddressModal.tsx:84 `<Select>` -> `comp-field__select` definite
- raw `<select>` matched (from av2-select-mapping.json): **3**
  - frontend/src/pages/companies/CompaniesPage.tsx:506 definite
  - frontend/src/pages/contacts/ContactsPage.tsx:308 definite
  - frontend/src/pages/contacts/ContactsPage.tsx:341 definite

### `company-forms.css:260 .product-edit-form .form-group select`
- specificity (0,2,1) vs mold (0,1,0): **rule wins (higher specificity)**
- declared: border: 1px solid var(--border-strong) (L263)
- properties this rule sets that the mold also sets (rule wins): border
- existing mold usages matched: definite **0**, incl. unconfirmed **0**
- raw `<select>` matched (from av2-select-mapping.json): **12**
  - frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:493 unconfirmed
  - frontend/src/pages/products/ProductEditPage.tsx:231 definite
  - frontend/src/pages/products/ProductEditPage.tsx:238 definite
  - frontend/src/pages/products/ProductEditPage.tsx:255 definite
  - frontend/src/pages/products/ProductEditPage.tsx:278 definite
  - frontend/src/pages/products/ProductEditPage.tsx:285 definite
  - frontend/src/pages/products/ProductEditPage.tsx:302 definite
  - frontend/src/pages/products/ProductEditPage.tsx:346 definite
  - frontend/src/pages/products/ProductEditPage.tsx:353 definite
  - frontend/src/pages/products/ProductEditPage.tsx:360 definite
  - frontend/src/pages/super-admin/components/StatusMasterPanel.tsx:311 unconfirmed
  - frontend/src/pages/super-admin/components/StatusMasterPanel.tsx:325 unconfirmed

### `components.css:19 .form-group select`
- specificity (0,1,1) vs mold (0,1,0): **rule wins (higher specificity)**
- declared: width: 100% (L22); padding: var(--space-2) var(--space-3) (L23); border: 1px solid var(--border) (L24); border-radius: var(--radius-sm) (L25); font-size: var(--font-base) (L26); color: var(--text-primary) (L27); background: var(--bg-surface) (L28); box-sizing: border-box (L29)
- properties this rule sets that the mold also sets (rule wins): width, padding, border, border-radius, font-size, color, background, box-sizing; shorthand `padding` also overrides mold padding-right (arrow room, FormField.css:74) at higher specificity; shorthand `background` also resets mold background-image/repeat/position (the chevron, FormField.css:74) at higher specificity
- existing mold usages matched: definite **7**, incl. unconfirmed **16**
  - frontend/src/pages/design-preview/sections/FormSection.tsx:53 `<Select>` -> `comp-field__select` unconfirmed (no JSX usage found for FormSection (frontend/src/pages/design-preview/sections/FormSection)
  - frontend/src/pages/design-preview/sections/FormSection.tsx:57 `<Select>` -> `comp-field__select` unconfirmed (no JSX usage found for FormSection (frontend/src/pages/design-preview/sections/FormSection)
  - frontend/src/pages/design-preview/sections/FormSection.tsx:61 `<Select>` -> `comp-field__select` unconfirmed (no JSX usage found for FormSection (frontend/src/pages/design-preview/sections/FormSection)
  - frontend/src/pages/design-preview/sections/FormSection.tsx:65 `<Select>` -> `comp-field__select` unconfirmed (no JSX usage found for FormSection (frontend/src/pages/design-preview/sections/FormSection)
  - frontend/src/pages/design-preview/sections/FormSection.tsx:105 `<Select>` -> `comp-field__select` unconfirmed (no JSX usage found for FormSection (frontend/src/pages/design-preview/sections/FormSection)
  - frontend/src/pages/design-preview/sections/FormSection.tsx:109 `<Select>` -> `comp-field__select` unconfirmed (no JSX usage found for FormSection (frontend/src/pages/design-preview/sections/FormSection)
  - frontend/src/pages/design-preview/sections/FormSection.tsx:113 `<Select>` -> `comp-field__select` unconfirmed (no JSX usage found for FormSection (frontend/src/pages/design-preview/sections/FormSection)
  - frontend/src/pages/note-master/NoteMasterPage.tsx:290 `<Select>` -> `comp-field__select` definite
  - frontend/src/pages/super-admin/components/NoteMasterPanel.tsx:278 `<Select>` -> `comp-field__select` definite
  - frontend/src/pages/super-admin/components/ProductFormatsMasterPanel.tsx:279 `<SelectControl>` -> `comp-select__control` definite
  - frontend/src/pages/super-admin/components/ProductFormatsMasterPanel.tsx:293 `<SelectControl>` -> `comp-select__control` definite
  - frontend/src/pages/super-admin/components/ProductLinesMasterPanel.tsx:278 `<SelectControl>` -> `comp-select__control` definite
  - frontend/src/pages/super-admin/components/ProductLinesMasterPanel.tsx:292 `<SelectControl>` -> `comp-select__control` definite
  - frontend/src/pages/super-admin/components/RuleCreateDrawer.tsx:197 `<Select>` -> `comp-field__select` unconfirmed (no JSX usage found for RuleCreateDrawer (frontend/src/pages/super-admin/components/RuleCre)
  - frontend/src/pages/super-admin/components/RuleCreateDrawer.tsx:209 `<Select>` -> `comp-field__select` unconfirmed (no JSX usage found for RuleCreateDrawer (frontend/src/pages/super-admin/components/RuleCre)
  - frontend/src/pages/super-admin/components/TypeMasterPanel.tsx:253 `<SelectControl>` -> `comp-select__control` definite
- raw `<select>` matched (from av2-select-mapping.json): **42**
  - frontend/src/components/CompanyContactSelector.tsx:190 definite
  - frontend/src/components/CompanyContactSelector.tsx:214 definite
  - frontend/src/components/PurchaseDetailPanel.tsx:424 definite
  - frontend/src/components/ShippingDetailPanel.tsx:511 definite
  - frontend/src/pages/admin/TenantPolicyPage.tsx:167 definite
  - frontend/src/pages/admin/TenantPolicyPage.tsx:266 definite
  - frontend/src/pages/admin/TenantPolicyPage.tsx:283 definite
  - frontend/src/pages/admin/TenantProfilePage.tsx:234 definite
  - frontend/src/pages/bots/BotsPage.tsx:233 definite
  - frontend/src/pages/bots/BotsPage.tsx:241 definite
  - frontend/src/pages/bots/BotsPage.tsx:248 definite
  - frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:493 definite
  - frontend/src/pages/integrations/PaypalIntegrationPage.tsx:164 definite
  - frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:308 definite
  - frontend/src/pages/orders/OrdersFormModal.tsx:86 definite
  - frontend/src/pages/products/ProductEditPage.tsx:231 definite
  - frontend/src/pages/products/ProductEditPage.tsx:238 definite
  - frontend/src/pages/products/ProductEditPage.tsx:255 definite
  - frontend/src/pages/products/ProductEditPage.tsx:278 definite
  - frontend/src/pages/products/ProductEditPage.tsx:285 definite
  - frontend/src/pages/products/ProductEditPage.tsx:302 definite
  - frontend/src/pages/products/ProductEditPage.tsx:346 definite
  - frontend/src/pages/products/ProductEditPage.tsx:353 definite
  - frontend/src/pages/products/ProductEditPage.tsx:360 definite
  - frontend/src/pages/purchase-orders/PurchaseOrdersFormModal.tsx:156 definite
  - frontend/src/pages/quote-create/QuoteCreatePage.tsx:157 definite
  - frontend/src/pages/status-master/StatusMasterPage.tsx:260 definite
  - frontend/src/pages/status-master/StatusMasterPage.tsx:274 definite
  - frontend/src/pages/super-admin/components/ConditionsMasterPanel.tsx:322 definite
  - frontend/src/pages/super-admin/components/ConditionsMasterPanel.tsx:338 definite
  - frontend/src/pages/super-admin/components/ConditionsMasterPanel.tsx:393 definite
  - frontend/src/pages/super-admin/components/ConditionsMasterPanel.tsx:409 definite
  - frontend/src/pages/super-admin/components/StatusMasterPanel.tsx:311 definite
  - frontend/src/pages/super-admin/components/StatusMasterPanel.tsx:325 definite
  - frontend/src/pages/super-admin/DexTab.tsx:194 unconfirmed
  - frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:447 definite
  - frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:455 definite
  - frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:472 definite
  - frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:501 definite
  - frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:523 definite
  - frontend/src/pages/super-admin/TcgSeriesTab.tsx:190 unconfirmed
  - frontend/src/pages/super-admin/TcgSeriesTab.tsx:300 unconfirmed

### `components.css:32 .form-group select:focus`
- specificity (0,2,1) (select:focus) vs mold `:focus` (0,2,0) / `.comp-field--error ... :focus` (0,3,0): **rule wins (higher specificity)**
- declared: outline: none (L35); border-color: var(--accent) (L36); box-shadow: var(--focus-ring-shadow) (L37)
- properties this rule sets that the mold also sets (rule wins): border-color
- existing mold usages matched: definite **7**, incl. unconfirmed **16**
  - frontend/src/pages/design-preview/sections/FormSection.tsx:53 `<Select>` -> `comp-field__select` unconfirmed (no JSX usage found for FormSection (frontend/src/pages/design-preview/sections/FormSection)
  - frontend/src/pages/design-preview/sections/FormSection.tsx:57 `<Select>` -> `comp-field__select` unconfirmed (no JSX usage found for FormSection (frontend/src/pages/design-preview/sections/FormSection)
  - frontend/src/pages/design-preview/sections/FormSection.tsx:61 `<Select>` -> `comp-field__select` unconfirmed (no JSX usage found for FormSection (frontend/src/pages/design-preview/sections/FormSection)
  - frontend/src/pages/design-preview/sections/FormSection.tsx:65 `<Select>` -> `comp-field__select` unconfirmed (no JSX usage found for FormSection (frontend/src/pages/design-preview/sections/FormSection)
  - frontend/src/pages/design-preview/sections/FormSection.tsx:105 `<Select>` -> `comp-field__select` unconfirmed (no JSX usage found for FormSection (frontend/src/pages/design-preview/sections/FormSection)
  - frontend/src/pages/design-preview/sections/FormSection.tsx:109 `<Select>` -> `comp-field__select` unconfirmed (no JSX usage found for FormSection (frontend/src/pages/design-preview/sections/FormSection)
  - frontend/src/pages/design-preview/sections/FormSection.tsx:113 `<Select>` -> `comp-field__select` unconfirmed (no JSX usage found for FormSection (frontend/src/pages/design-preview/sections/FormSection)
  - frontend/src/pages/note-master/NoteMasterPage.tsx:290 `<Select>` -> `comp-field__select` definite
  - frontend/src/pages/super-admin/components/NoteMasterPanel.tsx:278 `<Select>` -> `comp-field__select` definite
  - frontend/src/pages/super-admin/components/ProductFormatsMasterPanel.tsx:279 `<SelectControl>` -> `comp-select__control` definite
  - frontend/src/pages/super-admin/components/ProductFormatsMasterPanel.tsx:293 `<SelectControl>` -> `comp-select__control` definite
  - frontend/src/pages/super-admin/components/ProductLinesMasterPanel.tsx:278 `<SelectControl>` -> `comp-select__control` definite
  - frontend/src/pages/super-admin/components/ProductLinesMasterPanel.tsx:292 `<SelectControl>` -> `comp-select__control` definite
  - frontend/src/pages/super-admin/components/RuleCreateDrawer.tsx:197 `<Select>` -> `comp-field__select` unconfirmed (no JSX usage found for RuleCreateDrawer (frontend/src/pages/super-admin/components/RuleCre)
  - frontend/src/pages/super-admin/components/RuleCreateDrawer.tsx:209 `<Select>` -> `comp-field__select` unconfirmed (no JSX usage found for RuleCreateDrawer (frontend/src/pages/super-admin/components/RuleCre)
  - frontend/src/pages/super-admin/components/TypeMasterPanel.tsx:253 `<SelectControl>` -> `comp-select__control` definite
- raw `<select>` matched (from av2-select-mapping.json): **42**
  - frontend/src/components/CompanyContactSelector.tsx:190 definite
  - frontend/src/components/CompanyContactSelector.tsx:214 definite
  - frontend/src/components/PurchaseDetailPanel.tsx:424 definite
  - frontend/src/components/ShippingDetailPanel.tsx:511 definite
  - frontend/src/pages/admin/TenantPolicyPage.tsx:167 definite
  - frontend/src/pages/admin/TenantPolicyPage.tsx:266 definite
  - frontend/src/pages/admin/TenantPolicyPage.tsx:283 definite
  - frontend/src/pages/admin/TenantProfilePage.tsx:234 definite
  - frontend/src/pages/bots/BotsPage.tsx:233 definite
  - frontend/src/pages/bots/BotsPage.tsx:241 definite
  - frontend/src/pages/bots/BotsPage.tsx:248 definite
  - frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:493 definite
  - frontend/src/pages/integrations/PaypalIntegrationPage.tsx:164 definite
  - frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:308 definite
  - frontend/src/pages/orders/OrdersFormModal.tsx:86 definite
  - frontend/src/pages/products/ProductEditPage.tsx:231 definite
  - frontend/src/pages/products/ProductEditPage.tsx:238 definite
  - frontend/src/pages/products/ProductEditPage.tsx:255 definite
  - frontend/src/pages/products/ProductEditPage.tsx:278 definite
  - frontend/src/pages/products/ProductEditPage.tsx:285 definite
  - frontend/src/pages/products/ProductEditPage.tsx:302 definite
  - frontend/src/pages/products/ProductEditPage.tsx:346 definite
  - frontend/src/pages/products/ProductEditPage.tsx:353 definite
  - frontend/src/pages/products/ProductEditPage.tsx:360 definite
  - frontend/src/pages/purchase-orders/PurchaseOrdersFormModal.tsx:156 definite
  - frontend/src/pages/quote-create/QuoteCreatePage.tsx:157 definite
  - frontend/src/pages/status-master/StatusMasterPage.tsx:260 definite
  - frontend/src/pages/status-master/StatusMasterPage.tsx:274 definite
  - frontend/src/pages/super-admin/components/ConditionsMasterPanel.tsx:322 definite
  - frontend/src/pages/super-admin/components/ConditionsMasterPanel.tsx:338 definite
  - frontend/src/pages/super-admin/components/ConditionsMasterPanel.tsx:393 definite
  - frontend/src/pages/super-admin/components/ConditionsMasterPanel.tsx:409 definite
  - frontend/src/pages/super-admin/components/StatusMasterPanel.tsx:311 definite
  - frontend/src/pages/super-admin/components/StatusMasterPanel.tsx:325 definite
  - frontend/src/pages/super-admin/DexTab.tsx:194 unconfirmed
  - frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:447 definite
  - frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:455 definite
  - frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:472 definite
  - frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:501 definite
  - frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:523 definite
  - frontend/src/pages/super-admin/TcgSeriesTab.tsx:190 unconfirmed
  - frontend/src/pages/super-admin/TcgSeriesTab.tsx:300 unconfirmed

### `components.css:60 .filter-bar select`
- specificity (0,1,1) vs mold (0,1,0): **rule wins (higher specificity)**
- declared: padding: var(--space-2) var(--space-3) (L62); border: 1px solid var(--border) (L63); border-radius: var(--radius-sm) (L64); font-size: var(--font-base) (L65); min-width: var(--input-select-min-w) (L66); background: var(--bg-surface) (L67); color: var(--text-primary) (L68)
- properties this rule sets that the mold also sets (rule wins): padding, border, border-radius, font-size, background, color; shorthand `padding` also overrides mold padding-right (arrow room, FormField.css:74) at higher specificity; shorthand `background` also resets mold background-image/repeat/position (the chevron, FormField.css:74) at higher specificity
- existing mold usages matched: definite **0**, incl. unconfirmed **9**
  - frontend/src/pages/design-preview/sections/FormSection.tsx:53 `<Select>` -> `comp-field__select` unconfirmed (no JSX usage found for FormSection (frontend/src/pages/design-preview/sections/FormSection)
  - frontend/src/pages/design-preview/sections/FormSection.tsx:57 `<Select>` -> `comp-field__select` unconfirmed (no JSX usage found for FormSection (frontend/src/pages/design-preview/sections/FormSection)
  - frontend/src/pages/design-preview/sections/FormSection.tsx:61 `<Select>` -> `comp-field__select` unconfirmed (no JSX usage found for FormSection (frontend/src/pages/design-preview/sections/FormSection)
  - frontend/src/pages/design-preview/sections/FormSection.tsx:65 `<Select>` -> `comp-field__select` unconfirmed (no JSX usage found for FormSection (frontend/src/pages/design-preview/sections/FormSection)
  - frontend/src/pages/design-preview/sections/FormSection.tsx:105 `<Select>` -> `comp-field__select` unconfirmed (no JSX usage found for FormSection (frontend/src/pages/design-preview/sections/FormSection)
  - frontend/src/pages/design-preview/sections/FormSection.tsx:109 `<Select>` -> `comp-field__select` unconfirmed (no JSX usage found for FormSection (frontend/src/pages/design-preview/sections/FormSection)
  - frontend/src/pages/design-preview/sections/FormSection.tsx:113 `<Select>` -> `comp-field__select` unconfirmed (no JSX usage found for FormSection (frontend/src/pages/design-preview/sections/FormSection)
  - frontend/src/pages/super-admin/components/RuleCreateDrawer.tsx:197 `<Select>` -> `comp-field__select` unconfirmed (no JSX usage found for RuleCreateDrawer (frontend/src/pages/super-admin/components/RuleCre)
  - frontend/src/pages/super-admin/components/RuleCreateDrawer.tsx:209 `<Select>` -> `comp-field__select` unconfirmed (no JSX usage found for RuleCreateDrawer (frontend/src/pages/super-admin/components/RuleCre)
- raw `<select>` matched (from av2-select-mapping.json): **6**
  - frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:493 unconfirmed
  - frontend/src/pages/super-admin/components/StatusMasterPanel.tsx:311 unconfirmed
  - frontend/src/pages/super-admin/components/StatusMasterPanel.tsx:325 unconfirmed
  - frontend/src/pages/super-admin/DexTab.tsx:194 unconfirmed
  - frontend/src/pages/super-admin/TcgSeriesTab.tsx:190 unconfirmed
  - frontend/src/pages/super-admin/TcgSeriesTab.tsx:300 unconfirmed

Note: components.css and company-forms.css are both imported globally (frontend/src/App.tsx:122, App.tsx:125), so every matching rule is live on every route; the winner is decided by specificity, not import order, because no rule ties at (0,1,0).

## R2 Measurement feasibility (Playwright / Chromium)

Raw commands and output:

```
$ ls -d /Users/tanizawashingo/salesanchor/frontend/node_modules/playwright* -d
node_modules/playwright
node_modules/playwright-core
$ ls -d .../node_modules/@playwright      -> node_modules/@playwright  (contains: test)
$ ls ~/Library/Caches/ms-playwright
b
chromium_headless_shell-1217
chromium-1217
ffmpeg-1011
installed playwright / playwright-core version: 1.60.0
```

Probe 1 (/tmp/CC報告ファイル/pw-probe.cjs, default `chromium.launch()`), exit=1:
```
ERR browserType.launch: Executable doesn't exist at /Users/tanizawashingo/Library/Caches/ms-playwright/chromium_headless_shell-1223/chrome-headless-shell-mac-arm64/chrome-headless-shell
Looks like Playwright was just installed or updated. Please run the following command to download new browsers: npx playwright install
```
Cause: Playwright 1.60.0 wants browser revision 1223; cache holds 1217 (older) only. No network used, nothing installed.

Probe 2 (/tmp/CC報告ファイル/pw-probe-exe.cjs, same script with `executablePath` = cached 1217 headless shell), exit=0:
```
version 147.0.7727.15
fontSize 14px
```
Result: measurement IS runnable locally by passing `executablePath: ~/Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell`; default launch fails until `npx playwright install` (network, not done). Headless shell only (chromium-1217 dir has no `Chromium`/app binary found by `find`; headed/full Chromium 未確認). `<select>` computed style is readable (setContent works, no network).

Extra measurement (/tmp/CC報告ファイル/pw-ua-select.cjs, Chromium 147 headless shell, page = `* {margin:0;padding:0;box-sizing:border-box}` + body font-family/line-height 1.6 + bare `<select>`):
```
{"fontSize":"13.3333px","fontFamily":"Arial","lineHeight":"normal","color":"rgb(0, 0, 0)","height":"19px","bodyFontSize":"16px"}
```
i.e. a bare select does not inherit body font/line-height/color (UA defaults), at least in this Chromium build (macOS headless shell; other platforms 未確認).

## R3 Base / inherited CSS affecting selects

Rules found (all `*.css` under frontend/src, rules whose selector is html, body, *, or a button/input/select/textarea element group):

|selector|file:line|declarations|
|---|---|---|
|`*`|frontend/src/index.css:419-423|margin: 0; padding: 0; box-sizing: border-box|
|`body`|frontend/src/index.css:425-435|font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif; -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; background: var(--bg-primary); color: var(--text-primary); line-height: 1.6|
|`html`|(none)|no `html` rule in frontend/src (only `:root` / `:root.force-dark` token blocks: index.css:8, :220; tokens.css:11, :551; `color-scheme: light` at index.css:~19)|
|`button, input, select, textarea` (global reset / font inherit)|(none)|grep for `^(html|body|input|button|textarea|select|\*|:root)\b` finds only the rows above plus `select.right-panel-field` (InboxPage.css:1198, appearance:none) and `textarea.right-panel-field` (:1200); `font: inherit` / `font-family: inherit` occur only in class-scoped rules (e.g. components/FormField.css:59 for the mold, company-forms.css:111/170, components.css:875), not as a global element rule|

No `font-size` declaration exists in index.css (grep empty) and none on body -> body font-size is browser 16px (measured above). Consequence (fact): without a class rule, a `<select>` gets Chromium UA font (13.3333px, Arial), line-height normal, color black; `*` zeroes padding/margin and sets border-box on it.
`@import "./components/field-size.css"` (index.css:2) adds `.field-h-*` / `.field-w-*` classes only (min-height/width), no element rule.
Dark theme mechanism: only `:root.force-dark` class (index.css:220, tokens.css:551); `prefers-color-scheme` is not used for tokens (index.css:6 and :212 comments; grep finds no @media).

Token values (light = `:root`; dark = `:root.force-dark` override only where one exists):

|token|light value (source)|dark override|
|---|---|---|
|--radius-sm|4px (tokens.css:90)|none|
|--radius-md|6px (tokens.css:91)|none|
|--radius-pill|20px (tokens.css:95)|none|
|--comp-input-radius|var(--radius-md) = 6px (tokens.css:453)|none|
|--space-1|4px (tokens.css:68)|none|
|--space-2|8px (tokens.css:69)|none|
|--space-3|12px (tokens.css:70)|none|
|--space-5|20px (tokens.css:72)|none|
|--font-xs|0.75rem = 12px (tokens.css:14)|none|
|--font-sm|0.85rem = 13.6px (tokens.css:15)|none|
|--font-base|0.9rem = 14.4px (tokens.css:16)|none|
|--line-height-base|1.5 (tokens.css:35)|none|
|--border|#e2e8f0 (index.css:28)|#334155 (index.css:237)|
|--border-strong|#cbd5e0 (index.css:29)|#475569 (index.css:238)|
|--bg-surface|#ffffff (index.css:17)|#1e293b (index.css:228)|
|--bg-primary|#f5f7fa (index.css:16)|var(--palette-ink-deep) = #0f172a (index.css:227; palette at :9/:221)|
|--text-primary|#1a202c (index.css:23)|#f1f5f9 (index.css:233)|
|--text-secondary|#4a5568 (index.css:24)|#cbd5e1 (index.css:234)|
|--karte-field-py|7px (tokens.css:300)|none|
|--karte-field-px|9px (tokens.css:301)|none|
|--karte-field-bg|#fafbfc (tokens.css:309)|none|
|--karte-field-bd|#dde0e4 (tokens.css:310)|none|
|--size-icon-btn|36px (tokens.css:159)|none|
|--height-tab-item|36px (tokens.css:257)|none|
|--comp-input-height-sm|28px (tokens.css:456)|none|
|--comp-input-height-mobile|44px (tokens.css:457)|none|
|--transition-micro|100ms ease (tokens.css:142)|none|
|--transition-fast|150ms ease (tokens.css:143)|none|
|--focus-ring-shadow|0 0 0 3px rgba(30, 58, 138, 0.15) (index.css:93)|0 0 0 3px rgba(91, 141, 217, 0.3) (index.css:287)|

Only `--karte-field-{py,px,bg,bd}` exist (grep `--karte-field` in tokens.css/index.css). "None" = no definition in the force-dark blocks (grep of each token name over all css returns the single definition shown). Each token was defined exactly once per theme except as noted. Responsive overrides in tokens.css (@media max-width:1279px) touch only `--schedule-*` tokens.

DONE

## R4 Documented design intent for distinct select looks (origin/main 3210edeea)

Method: CSS/JSX quoted from the snapshot (line numbers = snapshot). Docs grep = `git grep -n -- "<name>" 3210edeea -- docs/adr docs/specs docs/handoff` (head -10 each) and again excluding `docs/handoff/design-system-recon/evidence-20260910` (our own AV-0/AV-1 audit dumps, which are inventories, not design intent). Result for ALL five names: hits only inside `docs/handoff/design-system-recon/evidence-20260910/*` (av0-input-audit.json, av1-css-mapping.md, av1-css-rules.md, av1-select-detail.{json,md}, av1-summary.json; they restate the CSS rule / JSX tag verbatim, no rationale). Hits outside that evidence dir: 0 for every name (docs/adr: 0, docs/specs: 0, other docs/handoff: 0). `ui-allow` comments in the 4 TSX files and the 2 schedule TSX files: 0.

First-10 hits per name (verbatim path:line) are reproduced by the grep above; representative lines:
- inbox-page-filter-select: `av1-css-rules.md:66: `.inbox-page-filter-select` { width: 100%; padding: var(--space-1) var(--space-2); font-size: var(--font-xs); border-radius: var(--radius-xl); ... }`
- inbox-settings-select: `av1-css-rules.md:70: `.inbox-settings-select` { background: var(--bg-primary); border: 1px solid var(--border); ... cursor: pointer; }`
- gs-select: `av1-css-rules.md:62: `.gs-select` { flex: 1; padding: var(--space-2) var(--space-3); ... font-size: var(--font-sm); cursor: pointer; }`
- account-settings-lang-select: `av1-css-rules.md:50` / `:52` (rule and :focus), `av1-css-mapping.md:347` (recon extraction condition list)
- schedule-input: `av0-input-audit.json:19623,19663,19748,...` (className occurrences), `av1-css-mapping.md:347`

### 1. `.inbox-page-filter-select` (InboxConversationList.tsx:147)
```
InboxPage.css
406: }
407: 
408: /* ページフィルター（複数Page時のドロップダウン） */
409: .inbox-page-filter-wrap {
410:   padding: var(--space-1) var(--space-3) var(--space-6px);
411: }
412: .inbox-page-filter-select {
413:   width: 100%;
414:   padding: var(--space-1) var(--space-2);
415:   font-size: var(--font-xs);
416:   border-radius: var(--radius-xl);
417:   border: 1px solid var(--border);
418:   background: var(--bg-surface);
419:   color: var(--text-primary);
420:   font-family: inherit;
421:   box-sizing: border-box;
422: }
```
JSX 144-152: `{/* Page フィルタ */}` then `<div className="inbox-page-filter-wrap"><select value={pageIdFilter} ... aria-label="Filter by Page" className="inbox-page-filter-select">`.
Documented intent for distinct look (radius-xl, xs font): **none found**. Only comments: "ページフィルター（複数Page時のドロップダウン）" (describes function, not the look) and "Page フィルタ". grep used: the git grep above (0 hits outside evidence dir).

### 2. `.inbox-settings-select` (InboxSettingsModal.tsx:37)
```
InboxPage.css
1434: }
1435: .inbox-settings-row {
1436:   display: flex; align-items: center; justify-content: space-between;
1437:   padding: var(--space-2) 0; border-bottom: 1px solid var(--border);
1438: }
1439: .inbox-settings-label { font-size: var(--font-sm); color: var(--text-primary); }
1440: .inbox-settings-select {
1441:   background: var(--bg-primary); border: 1px solid var(--border);
1442:   border-radius: var(--radius-sm); padding: var(--space-1) var(--space-2);
1443:   font-size: var(--font-sm); color: var(--text-primary);
1444:   cursor: pointer;
1445: }
1446: .inbox-settings-close-btn {
1447:   margin-top: var(--space-5); width: 100%;
...
```
JSX 35-39: `<div className="inbox-settings-row"><span className="inbox-settings-label">...</span><select className="inbox-settings-select" value={inboxSettings.defaultTab} ...>` (no comment). Documented intent (bg-primary instead of bg-surface, radius-sm): **none found**. grep: as above.

### 3. `.gs-select` (GoalSettingPage.tsx:711)
```
GoalSettingPage.css
549: .gs-team-select-wrap {
550:   display: flex;
551:   align-items: center;
552:   gap: var(--space-3);
553: }
554: 
555: .gs-select {
556:   flex: 1;
557:   padding: var(--space-2) var(--space-3);
558:   border: 1px solid var(--border);
559:   border-radius: var(--radius-md);
560:   background: var(--bg-surface);
561:   color: var(--text-primary);
562:   font-size: var(--font-sm);
563:   cursor: pointer;
564: }
565: 
566: /* ── 権限なしメッセージ ── */
```
JSX 708-715: `{/* チーム選択 */}` `<div className="gs-team-select-wrap"><label className="gs-label">...<select className="gs-select" value={selectedTeamId ?? ""} ...>`. Documented intent: **none found** (comment only labels the block "チーム選択"). grep as above.

### 4. `.account-settings-lang-select` (PreferencesSection.tsx:38)
```
account-settings.css
146: 
147: .toggle-switch input:focus-visible + .toggle-slider {
148:   box-shadow: var(--focus-ring-shadow);
149: }
150: 
151: /* Language select */
152: .account-settings-lang-select {
153:   padding: var(--space-1) var(--space-3);
154:   border: 1px solid var(--border);
155:   border-radius: var(--radius-sm);
156:   background: var(--bg-surface);
157:   color: var(--text-primary);
158:   font-size: var(--font-sm);
159:   cursor: pointer;
160:   min-width: var(--size-lang-select-min);
161: }
162: 
163: .account-settings-lang-select:focus {
164:   outline: none;
165:   border-color: var(--accent);
166:   box-shadow: var(--focus-ring-shadow);
167: }
168: 
169: .account-settings-success {
```
JSX 34-43: `<div className="account-settings-pref-row"><label htmlFor="language-select" ...><select id="language-select" value={locale} ... className="account-settings-lang-select">`. Documented intent: **none found** (comment "/* Language select */" only names it). grep as above.

### 5. `.schedule-input` (Schedule pages; usages SchedulePageImpl.tsx:279,289,322,332,345,355,367; ScheduleSettingsPage.tsx:171,226; element types per usage 未確認 here, the rule is shared by input/select/textarea-like fields)
```
pages/schedule.css
807: .schedule-field-group {
808:   display: grid;
809:   grid-template-columns: repeat(2, minmax(0, 1fr));
810:   gap: var(--space-2);
811: }
812: 
813: .schedule-input,
814: .schedule-textarea {
815:   width: 100%;
816:   border: 1px solid var(--border);
817:   border-radius: var(--radius-md);
818:   background: var(--bg-surface);
819:   color: var(--text-primary);
820:   font-size: var(--font-sm);
821: }
822: 
823: .schedule-input {
824:   min-height: var(--comp-input-height-sm);
825:   padding: 0 var(--space-3);
826: }
827: 
828: .schedule-textarea {
829:   padding: var(--space-2) var(--space-3);
830:   resize: vertical;
831: }
832: 
833: .schedule-input:focus,
834: .schedule-textarea:focus {
835:   outline: none;
836:   border-color: var(--accent);
837:   box-shadow: var(--focus-ring-shadow);
838: }
```
Documented intent: **none found** (no comment on these rules). Only indirect fact: `min-height: var(--comp-input-height-sm)` (28px) reuses the mold's size token (tokens.css:456). grep as above.

### 6. Inline style at InventoryPage.tsx:477 (the `<select` opening; style object on :481)
```
472:               >{label}</button>
473:             );
474:           })}
475:           {tcgTypes.filter((tt) => !["pokemon_booster_box", "one_piece", "dragon_ball"].includes(tt.code)).length > 0 && (
476:             // ui-allow: TCG "other types" dropdown from main back-merge, ADR-143 D-1 (#2624)
477:             <select
478:               value={["pokemon_booster_box", "one_piece", "dragon_ball", "all"].includes(activeTab) ? "" : activeTab}
479:               onChange={(e) => { if (e.target.value) { setActiveTab(e.target.value); setPage(1); } }}
480:               aria-label={t("inventory.filter.otherTypes")}
481:               style={{ fontSize: "var(--font-xs)", padding: "var(--space-1) var(--space-10px)", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", background: "var(--bg-surface)" }}
482:             >
```
Also (same file, from audit dump) a preceding block comment: `{/* TCG種別タブ: すべて/ポケモン/ワンピース/ドラゴンボール（4ボタン）＋その他ドロップダウン ＋ 警告（右端固定） */}` and `{/* ui-allow: TCG type tab bar from main back-merge, ADR-143 D-1 inventory v2 (#2624) */}`.
Documented intent for the distinct look: **none found**. The `ui-allow` comment cites a reason for existing as a raw select ("from main back-merge, ADR-143 D-1 (#2624)"), not for its look. Verification of that citation: `git grep -n -E "D-1|タブ|その他|dropdown|ドロップ"` over docs/adr/ADR-143-inventory-public-v2-canonical.md and ADR-143-send-guard.md at 3210edeea returned 0 lines; `git grep -n "ADR-143" -- docs/specs` 0 lines. So the "ADR-143 D-1" reference does not resolve to any text in the two ADR-143 files (未確認 whether another ADR carries "D-1"). `#2624` appears in docs only in `docs/handoff/color-tokens-ssot/recon.md:270` (unrelated color count row) and in the AV evidence dumps.
