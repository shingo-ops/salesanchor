# AW-2b per-select migration recon (read-only)

- origin/main sha: `c0936057e3a9fa1c89881cf8a7366e4fc06062e1`
- raw `<select>` in frontend/src/**/*.tsx (excl. *.test/*.stories, excl. components/Select.tsx): **63**
- held (excluded): 10 = ProductEditPage x9 + CommissionPanel x1 -> components/CommissionPanel.tsx:205, pages/products/ProductEditPage.tsx:231, pages/products/ProductEditPage.tsx:238, pages/products/ProductEditPage.tsx:255, pages/products/ProductEditPage.tsx:278, pages/products/ProductEditPage.tsx:285, pages/products/ProductEditPage.tsx:302, pages/products/ProductEditPage.tsx:346, pages/products/ProductEditPage.tsx:353, pages/products/ProductEditPage.tsx:360
- in-scope count: **53** (expected 53; difference: none)
- in-scope classification (av2 classes: i=no rule, iii=declared deco subset of one mold size, iv=differs, v=unconfirmed rule): {"iv":39,"i":4,"iii":4,"v":6}
- mold size by lead rule (font-base->md, font-sm/xs->sm, none->md): {"md":45,"sm":8}; width:100% (fullWidth) = 38 / 53
- Select/SelectControl usages total {"total":99,"Select":66,"SelectControl":33}; overridden by a bare-tag rule: 17 (definite 8, unconfirmed-only 9)
- universal baseline applied to every select (not per-select): frontend/src/index.css:419 * { margin: 0; padding: 0; box-sizing: border-box }
- JSON: out/aw2b-plan.json (same dir)

## 0. Method / caveats (facts)
- Inventory = TypeScript AST over snapshot of origin/main (git archive). CSS = postcss over all frontend/src/**/*.css; selector match against JSX ancestor chain (in-file + component def + usage sites up to depth 10). Scripts: av2-project/av2-css/av2-select-mapping/av2-r1 (path constants only) + aw2b-plan.cjs.
- LAYOUT = display, position, inset*, top/right/bottom/left, z-index, width, min/max-width, margin*, flex*, align-self, justify-self, order, grid*. DIMENSION (mold-owned) = height, min-height, max-height. Everything else = DECORATION.
- Mobile: mold has `@media (max-width:767px)` min-height var(--comp-input-height-mobile)=44px at all sizes (FormField.css:272-275). The before->after tables are for >767px (base). 未確認: computed pixel heights (no browser run).
- Not modeled: background shorthand resetting background-position/repeat; `.comp-field--error`; cross-file equal-specificity ordering (ambiguity flagged in av2 effectiveBaseAll).
- Rows with no matching rule show padding 0 / margin 0 from universal `*` rule (index.css:419-423) as "before"; 未確認: browser UA defaults beyond that.

## 1. Summary table
| # | select | cls | className | inline | size | fullW | rules (selector@file:line) | dimension owned by mold |
|---|---|---|---|---|---|---|---|---|
| 1 | components/CompanyContactSelector.tsx:190 | iv | - | - | md | Y | .form-group select@components.css:19; .form-group select:focus@components.css:32 | - |
| 2 | components/CompanyContactSelector.tsx:214 | iv | - | - | md | Y | .form-group select@components.css:19; .form-group select:focus@components.css:32 | - |
| 3 | components/PurchaseDetailPanel.tsx:424 | iv | - | - | md | Y | .form-group select@components.css:19; .form-group select:focus@components.css:32 | - |
| 4 | components/ShippingDetailPanel.tsx:511 | iv | - | - | md | Y | .form-group select@components.css:19; .form-group select:focus@components.css:32 | - |
| 5 | features/tcg-analysis-review/ItemComparison.tsx:26 | i | - | - | md | N | (none) | - |
| 6 | pages/account-settings/PreferencesSection.tsx:38 | iv | "account-settings-lang-select" | - | sm | N | .account-settings-lang-select@pages/account-settings/account-settings.css:152; .account-settings-lang-select:focus@pages/account-settings/account-settings.css:163 | - |
| 7 | pages/admin/TenantPolicyPage.tsx:167 | iv | - | - | md | Y | .form-group select@components.css:19; .form-group select:focus@components.css:32 | - |
| 8 | pages/admin/TenantPolicyPage.tsx:266 | iv | - | - | md | Y | .form-group select@components.css:19; .form-group select:focus@components.css:32 | - |
| 9 | pages/admin/TenantPolicyPage.tsx:283 | iv | - | - | md | Y | .form-group select@components.css:19; .form-group select:focus@components.css:32 | - |
| 10 | pages/admin/TenantProfilePage.tsx:234 | iv | - | - | md | Y | .form-group select@components.css:19; .form-group select:focus@components.css:32 | - |
| 11 | pages/bots/BotsPage.tsx:233 | iv | - | - | md | Y | .form-group select@components.css:19; .form-group select:focus@components.css:32 | - |
| 12 | pages/bots/BotsPage.tsx:241 | iv | - | - | md | Y | .form-group select@components.css:19; .form-group select:focus@components.css:32 | - |
| 13 | pages/bots/BotsPage.tsx:248 | iv | - | - | md | Y | .form-group select@components.css:19; .form-group select:focus@components.css:32 | - |
| 14 | pages/commission-settings/CommissionSettingsPage.tsx:206 | i | - | - | md | N | (none) | - |
| 15 | pages/companies/CompaniesPage.tsx:506 | iv | - | - | md | Y | .form-grid > .form-row select@company-forms.css:100; .form-grid > .form-row select:focus@company-forms.css:120; .modal-content-wide .form-row select@company-forms.css:156; .modal-content-wide .form-row select:focus@company-forms.css:181 | - |
| 16 | pages/company-detail/CompanyBasicTab.tsx:84 | iv | - | - | md | Y | .form-grid > .form-row select@company-forms.css:100; .form-grid > .form-row select:focus@company-forms.css:120 | - |
| 17 | pages/company-detail/CompanyConvLogsTab.tsx:73 | i | "conv-logs-filter-select" | - | md | N | (none) | - |
| 18 | pages/contacts/ContactsPage.tsx:273 | iii | "search-input field-h-md field-w-sm" | - | md | N | .field-h-md@components/field-size.css:8; .field-w-sm@components/field-size.css:12; .content-toolbar .field-w-sm@components/field-size.css:18 | min-height:var(--field-h-md, 36px) |
| 19 | pages/contacts/ContactsPage.tsx:308 | iv | - | - | md | Y | .form-grid > .form-row select@company-forms.css:100; .form-grid > .form-row select:focus@company-forms.css:120; .modal-content-wide .form-row select@company-forms.css:156; .modal-content-wide .form-row select:focus@company-forms.css:181 | - |
| 20 | pages/contacts/ContactsPage.tsx:341 | iv | - | - | md | Y | .form-grid > .form-row select@company-forms.css:100; .form-grid > .form-row select:focus@company-forms.css:120; .modal-content-wide .form-row select@company-forms.css:156; .modal-content-wide .form-row select:focus@company-forms.css:181 | - |
| 21 | pages/goal-setting/GoalSettingPage.tsx:711 | iv | "gs-select" | - | sm | N | .gs-select@pages/goal-setting/GoalSettingPage.css:555 | - |
| 22 | pages/inbox/InboxConversationList.tsx:147 | iv | "inbox-page-filter-select" | - | sm | Y | .inbox-page-filter-select@pages/inbox/InboxPage.css:398 | - |
| 23 | pages/inbox/InboxSettingsModal.tsx:37 | iv | "inbox-settings-select" | - | sm | N | .inbox-settings-select@pages/inbox/InboxPage.css:1424 | - |
| 24 | pages/inbox/ManualRecordSection.tsx:126 | i | "manual-record-select" | - | md | N | (none) | - |
| 25 | pages/integrations/FedexEtdSetupGuide.tsx:493 | v | - | - | md | Y | .form-group select@components.css:19; .form-group select:focus@components.css:32 | - |
| 26 | pages/integrations/PaypalIntegrationPage.tsx:164 | iv | - | - | md | Y | .form-group select@components.css:19; .form-group select:focus@components.css:32 | - |
| 27 | pages/inventory/InventoryPage.tsx:477 | iv | - | yes | sm | N | (none) | - |
| 28 | pages/invoice-create/InvoiceCreatePage.tsx:308 | iv | - | - | md | Y | .form-group select@components.css:19; .form-group select:focus@components.css:32 | - |
| 29 | pages/orders/OrdersFilterBar.tsx:40 | iii | "field-h-md field-w-sm" | - | md | N | .field-h-md@components/field-size.css:8; .field-w-sm@components/field-size.css:12; .content-toolbar .field-w-sm@components/field-size.css:18 | min-height:var(--field-h-md, 36px) |
| 30 | pages/orders/OrdersFormModal.tsx:86 | iv | - | - | md | Y | .form-group select@components.css:19; .form-group select:focus@components.css:32 | - |
| 31 | pages/products/ProductsPage.tsx:220 | iii | "field-h-md field-w-sm" | - | md | N | .field-h-md@components/field-size.css:8; .field-w-sm@components/field-size.css:12; .content-toolbar .field-w-sm@components/field-size.css:18 | min-height:var(--field-h-md, 36px) |
| 32 | pages/purchase-orders/PurchaseOrdersFormModal.tsx:156 | iv | - | - | md | Y | .form-group select@components.css:19; .form-group select:focus@components.css:32 | - |
| 33 | pages/purchase-orders/PurchaseOrdersPage.tsx:193 | iii | "field-h-md field-w-sm" | - | md | N | .field-h-md@components/field-size.css:8; .field-w-sm@components/field-size.css:12; .content-toolbar .field-w-sm@components/field-size.css:18 | min-height:var(--field-h-md, 36px) |
| 34 | pages/quote-create/QuoteCreatePage.tsx:157 | iv | - | - | md | Y | .form-group select@components.css:19; .form-group select:focus@components.css:32 | - |
| 35 | pages/schedule/SchedulePageImpl.tsx:288 | iv | "schedule-input" | - | sm | Y | .schedule-input@pages/schedule.css:813; .schedule-input@pages/schedule.css:823; .schedule-input:focus@pages/schedule.css:833 | min-height:var(--comp-input-height-sm) |
| 36 | pages/schedule/ScheduleSettingsPage.tsx:170 | iv | "schedule-input" | - | sm | Y | .schedule-input@pages/schedule.css:813; .schedule-input@pages/schedule.css:823; .schedule-input:focus@pages/schedule.css:833 | min-height:var(--comp-input-height-sm) |
| 37 | pages/schedule/ScheduleSettingsPage.tsx:225 | iv | "schedule-input" | - | sm | Y | .schedule-input@pages/schedule.css:813; .schedule-input@pages/schedule.css:823; .schedule-input:focus@pages/schedule.css:833 | min-height:var(--comp-input-height-sm) |
| 38 | pages/status-master/StatusMasterPage.tsx:260 | iv | "field field-h-md" | - | md | Y | .field-h-md@components/field-size.css:8; .form-group select@components.css:19; .form-group select:focus@components.css:32 | min-height:var(--field-h-md, 36px) |
| 39 | pages/status-master/StatusMasterPage.tsx:274 | iv | "field field-h-md" | - | md | Y | .field-h-md@components/field-size.css:8; .form-group select@components.css:19; .form-group select:focus@components.css:32 | min-height:var(--field-h-md, 36px) |
| 40 | pages/super-admin/components/ConditionsMasterPanel.tsx:322 | iv | "field field-h-md" | - | md | Y | .field-h-md@components/field-size.css:8; .form-group select@components.css:19; .form-group select:focus@components.css:32 | min-height:var(--field-h-md, 36px) |
| 41 | pages/super-admin/components/ConditionsMasterPanel.tsx:338 | iv | "field field-h-md" | - | md | Y | .field-h-md@components/field-size.css:8; .form-group select@components.css:19; .form-group select:focus@components.css:32 | min-height:var(--field-h-md, 36px) |
| 42 | pages/super-admin/components/ConditionsMasterPanel.tsx:393 | iv | "field field-h-md" | - | md | Y | .field-h-md@components/field-size.css:8; .form-group select@components.css:19; .form-group select:focus@components.css:32 | min-height:var(--field-h-md, 36px) |
| 43 | pages/super-admin/components/ConditionsMasterPanel.tsx:409 | iv | "field field-h-md" | - | md | Y | .field-h-md@components/field-size.css:8; .form-group select@components.css:19; .form-group select:focus@components.css:32 | min-height:var(--field-h-md, 36px) |
| 44 | pages/super-admin/components/StatusMasterPanel.tsx:311 | v | "field field-h-md" | - | md | Y | .field-h-md@components/field-size.css:8; .form-group select@components.css:19; .form-group select:focus@components.css:32 | min-height:var(--field-h-md, 36px) |
| 45 | pages/super-admin/components/StatusMasterPanel.tsx:325 | v | "field field-h-md" | - | md | Y | .field-h-md@components/field-size.css:8; .form-group select@components.css:19; .form-group select:focus@components.css:32 | min-height:var(--field-h-md, 36px) |
| 46 | pages/super-admin/DexTab.tsx:194 | v | - | - | md | N | (none) | - |
| 47 | pages/super-admin/KnowledgeAliasesTab.tsx:447 | iv | - | - | md | Y | .form-group select@components.css:19; .form-group select:focus@components.css:32 | - |
| 48 | pages/super-admin/KnowledgeAliasesTab.tsx:455 | iv | - | - | md | Y | .form-group select@components.css:19; .form-group select:focus@components.css:32 | - |
| 49 | pages/super-admin/KnowledgeAliasesTab.tsx:472 | iv | - | - | md | Y | .form-group select@components.css:19; .form-group select:focus@components.css:32 | - |
| 50 | pages/super-admin/KnowledgeAliasesTab.tsx:501 | iv | - | - | md | Y | .form-group select@components.css:19; .form-group select:focus@components.css:32 | - |
| 51 | pages/super-admin/KnowledgeAliasesTab.tsx:523 | iv | - | - | md | Y | .form-group select@components.css:19; .form-group select:focus@components.css:32 | - |
| 52 | pages/super-admin/TcgSeriesTab.tsx:190 | v | - | - | md | N | (none) | - |
| 53 | pages/super-admin/TcgSeriesTab.tsx:300 | v | - | - | md | N | (none) | - |

## 2. Per-select detail

### 1. components/CompanyContactSelector.tsx:190  (CompanyContactSelector)
- opening tag: `<select required={required} disabled={disabled} value={value.companyId !== null ? String(value.companyId) : ""} onChange={(e) => handleCompanyChange(e.target.value)} >`
- className expr: (none) | inline style: (none)
- children kind: map (["option","map"]), disabledOption=false, onChange=`{(e) => handleCompanyChange(e.target.value)}`, reads=["target.value"], numericConverted=false
- applied CSS rules:
  - `.form-group select` @ frontend/src/components.css:19 (0,1,1) state=base [definite]
    - LAYOUT: width: 100% (L22)
    - DECORATION: padding: var(--space-2) var(--space-3) (L23); border: 1px solid var(--border) (L24); border-radius: var(--radius-sm) (L25); font-size: var(--font-base) (L26); color: var(--text-primary) (L27); background: var(--bg-surface) (L28); box-sizing: border-box (L29)
  - `.form-group select:focus` @ frontend/src/components.css:32 (0,2,1) state=self:focus [definite]
    - DECORATION: outline: none (L35); border-color: var(--accent) (L36); box-shadow: var(--focus-ring-shadow) (L37)
- nearest mold size: **md** (font-size token; font-size=var(--font-base)); padding T/R/B/L = var(--space-2) / var(--space-3) / var(--space-2) / var(--space-3); width=100% @frontend/src/components.css:22 -> fullWidth=true
- layout-only residue to keep as layoutClassName/className: width: 100% [.form-group select]
- before -> after vs SelectControl bare md (7/13 equal):
  - padding-top: var(--space-2) -> var(--space-2)  (same)
  - padding-right: var(--space-3) -> var(--space-5)
  - padding-bottom: var(--space-2) -> var(--space-2)  (same)
  - padding-left: var(--space-3) -> var(--space-3)  (same)
  - border: 1px solid var(--border) -> 1px solid var(--border)  (same)
  - border-radius: var(--radius-sm) -> var(--comp-input-radius)
  - font-size: var(--font-base) -> var(--font-base)  (same)
  - color: var(--text-primary) -> var(--text-primary)  (same)
  - background-color: var(--bg-surface) -> var(--bg-surface)  (same)
  - background-image: none -> arrow-svg(url data:image/svg+xml chevron #888)
  - height: (unset: browser default) -> (none)
  - min-height: (unset: browser default) -> (none)
  - line-height: (unset: browser default) -> var(--line-height-base)

### 2. components/CompanyContactSelector.tsx:214  (CompanyContactSelector)
- opening tag: `<select required={required} disabled={ disabled || value.companyId === null || companyIdMissing || loadingContacts } value={value.contactId !== null ? String(value.contactId) : ""} onChange={(e) => handleContactChange(e.target.value)} >`
- className expr: (none) | inline style: (none)
- children kind: map (["option","map"]), disabledOption=false, onChange=`{(e) => handleContactChange(e.target.value)}`, reads=["target.value"], numericConverted=false
- applied CSS rules:
  - `.form-group select` @ frontend/src/components.css:19 (0,1,1) state=base [definite]
    - LAYOUT: width: 100% (L22)
    - DECORATION: padding: var(--space-2) var(--space-3) (L23); border: 1px solid var(--border) (L24); border-radius: var(--radius-sm) (L25); font-size: var(--font-base) (L26); color: var(--text-primary) (L27); background: var(--bg-surface) (L28); box-sizing: border-box (L29)
  - `.form-group select:focus` @ frontend/src/components.css:32 (0,2,1) state=self:focus [definite]
    - DECORATION: outline: none (L35); border-color: var(--accent) (L36); box-shadow: var(--focus-ring-shadow) (L37)
- nearest mold size: **md** (font-size token; font-size=var(--font-base)); padding T/R/B/L = var(--space-2) / var(--space-3) / var(--space-2) / var(--space-3); width=100% @frontend/src/components.css:22 -> fullWidth=true
- layout-only residue to keep as layoutClassName/className: width: 100% [.form-group select]
- before -> after vs SelectControl bare md (7/13 equal):
  - padding-top: var(--space-2) -> var(--space-2)  (same)
  - padding-right: var(--space-3) -> var(--space-5)
  - padding-bottom: var(--space-2) -> var(--space-2)  (same)
  - padding-left: var(--space-3) -> var(--space-3)  (same)
  - border: 1px solid var(--border) -> 1px solid var(--border)  (same)
  - border-radius: var(--radius-sm) -> var(--comp-input-radius)
  - font-size: var(--font-base) -> var(--font-base)  (same)
  - color: var(--text-primary) -> var(--text-primary)  (same)
  - background-color: var(--bg-surface) -> var(--bg-surface)  (same)
  - background-image: none -> arrow-svg(url data:image/svg+xml chevron #888)
  - height: (unset: browser default) -> (none)
  - min-height: (unset: browser default) -> (none)
  - line-height: (unset: browser default) -> var(--line-height-base)

### 3. components/PurchaseDetailPanel.tsx:424  (PurchaseDetailPanel)
- opening tag: `<select value={form.purchase_status} onChange={(ev) => setField("purchase_status", ev.target.value)} data-testid="pur-input-purchase_status" >`
- className expr: (none) | inline style: (none)
- children kind: map (["map"]), disabledOption=false, onChange=`{(ev) => setField("purchase_status", ev.target.value)}`, reads=["target.value"], numericConverted=false
- applied CSS rules:
  - `.form-group select` @ frontend/src/components.css:19 (0,1,1) state=base [definite]
    - LAYOUT: width: 100% (L22)
    - DECORATION: padding: var(--space-2) var(--space-3) (L23); border: 1px solid var(--border) (L24); border-radius: var(--radius-sm) (L25); font-size: var(--font-base) (L26); color: var(--text-primary) (L27); background: var(--bg-surface) (L28); box-sizing: border-box (L29)
  - `.form-group select:focus` @ frontend/src/components.css:32 (0,2,1) state=self:focus [definite]
    - DECORATION: outline: none (L35); border-color: var(--accent) (L36); box-shadow: var(--focus-ring-shadow) (L37)
- nearest mold size: **md** (font-size token; font-size=var(--font-base)); padding T/R/B/L = var(--space-2) / var(--space-3) / var(--space-2) / var(--space-3); width=100% @frontend/src/components.css:22 -> fullWidth=true
- layout-only residue to keep as layoutClassName/className: width: 100% [.form-group select]
- before -> after vs SelectControl bare md (7/13 equal):
  - padding-top: var(--space-2) -> var(--space-2)  (same)
  - padding-right: var(--space-3) -> var(--space-5)
  - padding-bottom: var(--space-2) -> var(--space-2)  (same)
  - padding-left: var(--space-3) -> var(--space-3)  (same)
  - border: 1px solid var(--border) -> 1px solid var(--border)  (same)
  - border-radius: var(--radius-sm) -> var(--comp-input-radius)
  - font-size: var(--font-base) -> var(--font-base)  (same)
  - color: var(--text-primary) -> var(--text-primary)  (same)
  - background-color: var(--bg-surface) -> var(--bg-surface)  (same)
  - background-image: none -> arrow-svg(url data:image/svg+xml chevron #888)
  - height: (unset: browser default) -> (none)
  - min-height: (unset: browser default) -> (none)
  - line-height: (unset: browser default) -> var(--line-height-base)

### 4. components/ShippingDetailPanel.tsx:511  (ShippingDetailPanel)
- opening tag: `<select value={form.carrier} onChange={(ev) => setField("carrier", ev.target.value)} data-testid="ship-input-carrier" >`
- className expr: (none) | inline style: (none)
- children kind: map (["map"]), disabledOption=false, onChange=`{(ev) => setField("carrier", ev.target.value)}`, reads=["target.value"], numericConverted=false
- applied CSS rules:
  - `.form-group select` @ frontend/src/components.css:19 (0,1,1) state=base [definite]
    - LAYOUT: width: 100% (L22)
    - DECORATION: padding: var(--space-2) var(--space-3) (L23); border: 1px solid var(--border) (L24); border-radius: var(--radius-sm) (L25); font-size: var(--font-base) (L26); color: var(--text-primary) (L27); background: var(--bg-surface) (L28); box-sizing: border-box (L29)
  - `.form-group select:focus` @ frontend/src/components.css:32 (0,2,1) state=self:focus [definite]
    - DECORATION: outline: none (L35); border-color: var(--accent) (L36); box-shadow: var(--focus-ring-shadow) (L37)
- nearest mold size: **md** (font-size token; font-size=var(--font-base)); padding T/R/B/L = var(--space-2) / var(--space-3) / var(--space-2) / var(--space-3); width=100% @frontend/src/components.css:22 -> fullWidth=true
- layout-only residue to keep as layoutClassName/className: width: 100% [.form-group select]
- before -> after vs SelectControl bare md (7/13 equal):
  - padding-top: var(--space-2) -> var(--space-2)  (same)
  - padding-right: var(--space-3) -> var(--space-5)
  - padding-bottom: var(--space-2) -> var(--space-2)  (same)
  - padding-left: var(--space-3) -> var(--space-3)  (same)
  - border: 1px solid var(--border) -> 1px solid var(--border)  (same)
  - border-radius: var(--radius-sm) -> var(--comp-input-radius)
  - font-size: var(--font-base) -> var(--font-base)  (same)
  - color: var(--text-primary) -> var(--text-primary)  (same)
  - background-color: var(--bg-surface) -> var(--bg-surface)  (same)
  - background-image: none -> arrow-svg(url data:image/svg+xml chevron #888)
  - height: (unset: browser default) -> (none)
  - min-height: (unset: browser default) -> (none)
  - line-height: (unset: browser default) -> var(--line-height-base)

### 5. features/tcg-analysis-review/ItemComparison.tsx:26  (ManualInput)
- opening tag: `<select value={values[key]} disabled={!options} aria-label={t('tcgAnalysisReview.manualCorrection', { field: t(labelKey) })} onChange={(event) => onChange(key, event.target.value)}>`
- className expr: (none) | inline style: (none)
- children kind: map (["option","map"]), disabledOption=false, onChange=`{(event) => onChange(key, event.target.value)}`, reads=["target.value"], numericConverted=false
- applied CSS rules:
  - (none) -> unstyled
- nearest mold size: **md** (font-size token; font-size=unset); padding T/R/B/L = 0 / 0 / 0 / 0; width=unset -> fullWidth=false
- layout-only residue to keep as layoutClassName/className: (none)
- before -> after vs SelectControl bare md (0/13 equal):
  - padding-top: 0 -> var(--space-2)
  - padding-right: 0 -> var(--space-5)
  - padding-bottom: 0 -> var(--space-2)
  - padding-left: 0 -> var(--space-3)
  - border: (unset: browser default) -> 1px solid var(--border)
  - border-radius: (unset: browser default) -> var(--comp-input-radius)
  - font-size: (unset: browser default) -> var(--font-base)
  - color: (unset: browser default) -> var(--text-primary)
  - background-color: (unset: browser default) -> var(--bg-surface)
  - background-image: (unset: browser default) -> arrow-svg(url data:image/svg+xml chevron #888)
  - height: (unset: browser default) -> (none)
  - min-height: (unset: browser default) -> (none)
  - line-height: (unset: browser default) -> var(--line-height-base)

### 6. pages/account-settings/PreferencesSection.tsx:38  (PreferencesSection)
- opening tag: `<select id="language-select" value={locale} onChange={(e) => changeLanguage(e.target.value)} className="account-settings-lang-select" >`
- className expr: `"account-settings-lang-select"` | inline style: (none)
- children kind: static-option (["option","option"]), disabledOption=false, onChange=`{(e) => changeLanguage(e.target.value)}`, reads=["target.value"], numericConverted=false
- applied CSS rules:
  - `.account-settings-lang-select` @ frontend/src/pages/account-settings/account-settings.css:152 (0,1,0) state=base [definite]
    - LAYOUT: min-width: var(--size-lang-select-min) (L160)
    - DECORATION: padding: var(--space-1) var(--space-3) (L153); border: 1px solid var(--border) (L154); border-radius: var(--radius-sm) (L155); background: var(--bg-surface) (L156); color: var(--text-primary) (L157); font-size: var(--font-sm) (L158); cursor: pointer (L159)
  - `.account-settings-lang-select:focus` @ frontend/src/pages/account-settings/account-settings.css:163 (0,2,0) state=self:focus [definite]
    - DECORATION: outline: none (L164); border-color: var(--accent) (L165); box-shadow: var(--focus-ring-shadow) (L166)
- nearest mold size: **sm** (font-size token; font-size=var(--font-sm)); padding T/R/B/L = var(--space-1) / var(--space-3) / var(--space-1) / var(--space-3); width=unset -> fullWidth=false
- layout-only residue to keep as layoutClassName/className: min-width: var(--size-lang-select-min) [.account-settings-lang-select]
- before -> after vs SelectControl bare sm (6/13 equal):
  - padding-top: var(--space-1) -> var(--space-1)  (same)
  - padding-right: var(--space-3) -> var(--space-5)
  - padding-bottom: var(--space-1) -> var(--space-1)  (same)
  - padding-left: var(--space-3) -> var(--space-2)
  - border: 1px solid var(--border) -> 1px solid var(--border)  (same)
  - border-radius: var(--radius-sm) -> var(--comp-input-radius)
  - font-size: var(--font-sm) -> var(--font-sm)  (same)
  - color: var(--text-primary) -> var(--text-primary)  (same)
  - background-color: var(--bg-surface) -> var(--bg-surface)  (same)
  - background-image: none -> arrow-svg(url data:image/svg+xml chevron #888)
  - height: (unset: browser default) -> (none)
  - min-height: (unset: browser default) -> var(--comp-input-height-sm)
  - line-height: (unset: browser default) -> var(--line-height-base)

### 7. pages/admin/TenantPolicyPage.tsx:167  (TenantPolicyPage)
- opening tag: `<select id="tp-agg-filter" data-testid="tp-agg-filter" value={form.inventory_agg_filter} onChange={handleChange("inventory_agg_filter")} disabled={!canEdit} >`
- className expr: (none) | inline style: (none)
- children kind: static-option (["option","option","option"]), disabledOption=false, onChange=`{handleChange("inventory_agg_filter")}`, reads=["other/unresolved"], numericConverted=false
- applied CSS rules:
  - `.form-group select` @ frontend/src/components.css:19 (0,1,1) state=base [definite]
    - LAYOUT: width: 100% (L22)
    - DECORATION: padding: var(--space-2) var(--space-3) (L23); border: 1px solid var(--border) (L24); border-radius: var(--radius-sm) (L25); font-size: var(--font-base) (L26); color: var(--text-primary) (L27); background: var(--bg-surface) (L28); box-sizing: border-box (L29)
  - `.form-group select:focus` @ frontend/src/components.css:32 (0,2,1) state=self:focus [definite]
    - DECORATION: outline: none (L35); border-color: var(--accent) (L36); box-shadow: var(--focus-ring-shadow) (L37)
- nearest mold size: **md** (font-size token; font-size=var(--font-base)); padding T/R/B/L = var(--space-2) / var(--space-3) / var(--space-2) / var(--space-3); width=100% @frontend/src/components.css:22 -> fullWidth=true
- layout-only residue to keep as layoutClassName/className: width: 100% [.form-group select]
- before -> after vs SelectControl bare md (7/13 equal):
  - padding-top: var(--space-2) -> var(--space-2)  (same)
  - padding-right: var(--space-3) -> var(--space-5)
  - padding-bottom: var(--space-2) -> var(--space-2)  (same)
  - padding-left: var(--space-3) -> var(--space-3)  (same)
  - border: 1px solid var(--border) -> 1px solid var(--border)  (same)
  - border-radius: var(--radius-sm) -> var(--comp-input-radius)
  - font-size: var(--font-base) -> var(--font-base)  (same)
  - color: var(--text-primary) -> var(--text-primary)  (same)
  - background-color: var(--bg-surface) -> var(--bg-surface)  (same)
  - background-image: none -> arrow-svg(url data:image/svg+xml chevron #888)
  - height: (unset: browser default) -> (none)
  - min-height: (unset: browser default) -> (none)
  - line-height: (unset: browser default) -> var(--line-height-base)

### 8. pages/admin/TenantPolicyPage.tsx:266  (TenantPolicyPage)
- opening tag: `<select id="tp-incoterms" data-testid="tp-incoterms" value={form.duty_incoterms} onChange={handleChange("duty_incoterms")} disabled={!canEdit} >`
- className expr: (none) | inline style: (none)
- children kind: static-option (["option","option","option"]), disabledOption=false, onChange=`{handleChange("duty_incoterms")}`, reads=["other/unresolved"], numericConverted=false
- applied CSS rules:
  - `.form-group select` @ frontend/src/components.css:19 (0,1,1) state=base [definite]
    - LAYOUT: width: 100% (L22)
    - DECORATION: padding: var(--space-2) var(--space-3) (L23); border: 1px solid var(--border) (L24); border-radius: var(--radius-sm) (L25); font-size: var(--font-base) (L26); color: var(--text-primary) (L27); background: var(--bg-surface) (L28); box-sizing: border-box (L29)
  - `.form-group select:focus` @ frontend/src/components.css:32 (0,2,1) state=self:focus [definite]
    - DECORATION: outline: none (L35); border-color: var(--accent) (L36); box-shadow: var(--focus-ring-shadow) (L37)
- nearest mold size: **md** (font-size token; font-size=var(--font-base)); padding T/R/B/L = var(--space-2) / var(--space-3) / var(--space-2) / var(--space-3); width=100% @frontend/src/components.css:22 -> fullWidth=true
- layout-only residue to keep as layoutClassName/className: width: 100% [.form-group select]
- before -> after vs SelectControl bare md (7/13 equal):
  - padding-top: var(--space-2) -> var(--space-2)  (same)
  - padding-right: var(--space-3) -> var(--space-5)
  - padding-bottom: var(--space-2) -> var(--space-2)  (same)
  - padding-left: var(--space-3) -> var(--space-3)  (same)
  - border: 1px solid var(--border) -> 1px solid var(--border)  (same)
  - border-radius: var(--radius-sm) -> var(--comp-input-radius)
  - font-size: var(--font-base) -> var(--font-base)  (same)
  - color: var(--text-primary) -> var(--text-primary)  (same)
  - background-color: var(--bg-surface) -> var(--bg-surface)  (same)
  - background-image: none -> arrow-svg(url data:image/svg+xml chevron #888)
  - height: (unset: browser default) -> (none)
  - min-height: (unset: browser default) -> (none)
  - line-height: (unset: browser default) -> var(--line-height-base)

### 9. pages/admin/TenantPolicyPage.tsx:283  (TenantPolicyPage)
- opening tag: `<select id="tp-issue-mode" data-testid="tp-issue-mode" value={form.issue_mode} onChange={handleChange("issue_mode")} disabled={!canEdit} >`
- className expr: (none) | inline style: (none)
- children kind: static-option (["option","option","option","option"]), disabledOption=false, onChange=`{handleChange("issue_mode")}`, reads=["other/unresolved"], numericConverted=false
- applied CSS rules:
  - `.form-group select` @ frontend/src/components.css:19 (0,1,1) state=base [definite]
    - LAYOUT: width: 100% (L22)
    - DECORATION: padding: var(--space-2) var(--space-3) (L23); border: 1px solid var(--border) (L24); border-radius: var(--radius-sm) (L25); font-size: var(--font-base) (L26); color: var(--text-primary) (L27); background: var(--bg-surface) (L28); box-sizing: border-box (L29)
  - `.form-group select:focus` @ frontend/src/components.css:32 (0,2,1) state=self:focus [definite]
    - DECORATION: outline: none (L35); border-color: var(--accent) (L36); box-shadow: var(--focus-ring-shadow) (L37)
- nearest mold size: **md** (font-size token; font-size=var(--font-base)); padding T/R/B/L = var(--space-2) / var(--space-3) / var(--space-2) / var(--space-3); width=100% @frontend/src/components.css:22 -> fullWidth=true
- layout-only residue to keep as layoutClassName/className: width: 100% [.form-group select]
- before -> after vs SelectControl bare md (7/13 equal):
  - padding-top: var(--space-2) -> var(--space-2)  (same)
  - padding-right: var(--space-3) -> var(--space-5)
  - padding-bottom: var(--space-2) -> var(--space-2)  (same)
  - padding-left: var(--space-3) -> var(--space-3)  (same)
  - border: 1px solid var(--border) -> 1px solid var(--border)  (same)
  - border-radius: var(--radius-sm) -> var(--comp-input-radius)
  - font-size: var(--font-base) -> var(--font-base)  (same)
  - color: var(--text-primary) -> var(--text-primary)  (same)
  - background-color: var(--bg-surface) -> var(--bg-surface)  (same)
  - background-image: none -> arrow-svg(url data:image/svg+xml chevron #888)
  - height: (unset: browser default) -> (none)
  - min-height: (unset: browser default) -> (none)
  - line-height: (unset: browser default) -> var(--line-height-base)

### 10. pages/admin/TenantProfilePage.tsx:234  (TenantProfilePage)
- opening tag: `<select id="tp-default-language" data-testid="tp-default-language" value={form.default_language} onChange={handleChange("default_language")} disabled={!canEdit} >`
- className expr: (none) | inline style: (none)
- children kind: static-option (["option","option","option","option"]), disabledOption=false, onChange=`{handleChange("default_language")}`, reads=["other/unresolved"], numericConverted=false
- applied CSS rules:
  - `.form-group select` @ frontend/src/components.css:19 (0,1,1) state=base [definite]
    - LAYOUT: width: 100% (L22)
    - DECORATION: padding: var(--space-2) var(--space-3) (L23); border: 1px solid var(--border) (L24); border-radius: var(--radius-sm) (L25); font-size: var(--font-base) (L26); color: var(--text-primary) (L27); background: var(--bg-surface) (L28); box-sizing: border-box (L29)
  - `.form-group select:focus` @ frontend/src/components.css:32 (0,2,1) state=self:focus [definite]
    - DECORATION: outline: none (L35); border-color: var(--accent) (L36); box-shadow: var(--focus-ring-shadow) (L37)
- nearest mold size: **md** (font-size token; font-size=var(--font-base)); padding T/R/B/L = var(--space-2) / var(--space-3) / var(--space-2) / var(--space-3); width=100% @frontend/src/components.css:22 -> fullWidth=true
- layout-only residue to keep as layoutClassName/className: width: 100% [.form-group select]
- before -> after vs SelectControl bare md (7/13 equal):
  - padding-top: var(--space-2) -> var(--space-2)  (same)
  - padding-right: var(--space-3) -> var(--space-5)
  - padding-bottom: var(--space-2) -> var(--space-2)  (same)
  - padding-left: var(--space-3) -> var(--space-3)  (same)
  - border: 1px solid var(--border) -> 1px solid var(--border)  (same)
  - border-radius: var(--radius-sm) -> var(--comp-input-radius)
  - font-size: var(--font-base) -> var(--font-base)  (same)
  - color: var(--text-primary) -> var(--text-primary)  (same)
  - background-color: var(--bg-surface) -> var(--bg-surface)  (same)
  - background-image: none -> arrow-svg(url data:image/svg+xml chevron #888)
  - height: (unset: browser default) -> (none)
  - min-height: (unset: browser default) -> (none)
  - line-height: (unset: browser default) -> var(--line-height-base)

### 11. pages/bots/BotsPage.tsx:233  (BotsPage)
- opening tag: `<select required value={createForm.purpose} onChange={(e) => setCreateForm({ ...createForm, purpose: e.target.value })}>`
- className expr: (none) | inline style: (none)
- children kind: static-option (["option","option","option","option"]), disabledOption=false, onChange=`{(e) => setCreateForm({ ...createForm, purpose: e.target.value })}`, reads=["target.value"], numericConverted=false
- applied CSS rules:
  - `.form-group select` @ frontend/src/components.css:19 (0,1,1) state=base [definite]
    - LAYOUT: width: 100% (L22)
    - DECORATION: padding: var(--space-2) var(--space-3) (L23); border: 1px solid var(--border) (L24); border-radius: var(--radius-sm) (L25); font-size: var(--font-base) (L26); color: var(--text-primary) (L27); background: var(--bg-surface) (L28); box-sizing: border-box (L29)
  - `.form-group select:focus` @ frontend/src/components.css:32 (0,2,1) state=self:focus [definite]
    - DECORATION: outline: none (L35); border-color: var(--accent) (L36); box-shadow: var(--focus-ring-shadow) (L37)
- nearest mold size: **md** (font-size token; font-size=var(--font-base)); padding T/R/B/L = var(--space-2) / var(--space-3) / var(--space-2) / var(--space-3); width=100% @frontend/src/components.css:22 -> fullWidth=true
- layout-only residue to keep as layoutClassName/className: width: 100% [.form-group select]
- before -> after vs SelectControl bare md (7/13 equal):
  - padding-top: var(--space-2) -> var(--space-2)  (same)
  - padding-right: var(--space-3) -> var(--space-5)
  - padding-bottom: var(--space-2) -> var(--space-2)  (same)
  - padding-left: var(--space-3) -> var(--space-3)  (same)
  - border: 1px solid var(--border) -> 1px solid var(--border)  (same)
  - border-radius: var(--radius-sm) -> var(--comp-input-radius)
  - font-size: var(--font-base) -> var(--font-base)  (same)
  - color: var(--text-primary) -> var(--text-primary)  (same)
  - background-color: var(--bg-surface) -> var(--bg-surface)  (same)
  - background-image: none -> arrow-svg(url data:image/svg+xml chevron #888)
  - height: (unset: browser default) -> (none)
  - min-height: (unset: browser default) -> (none)
  - line-height: (unset: browser default) -> var(--line-height-base)

### 12. pages/bots/BotsPage.tsx:241  (BotsPage)
- opening tag: `<select value={createForm.status} onChange={(e) => setCreateForm({ ...createForm, status: e.target.value })}>`
- className expr: (none) | inline style: (none)
- children kind: static-option (["option","option","option"]), disabledOption=false, onChange=`{(e) => setCreateForm({ ...createForm, status: e.target.value })}`, reads=["target.value"], numericConverted=false
- applied CSS rules:
  - `.form-group select` @ frontend/src/components.css:19 (0,1,1) state=base [definite]
    - LAYOUT: width: 100% (L22)
    - DECORATION: padding: var(--space-2) var(--space-3) (L23); border: 1px solid var(--border) (L24); border-radius: var(--radius-sm) (L25); font-size: var(--font-base) (L26); color: var(--text-primary) (L27); background: var(--bg-surface) (L28); box-sizing: border-box (L29)
  - `.form-group select:focus` @ frontend/src/components.css:32 (0,2,1) state=self:focus [definite]
    - DECORATION: outline: none (L35); border-color: var(--accent) (L36); box-shadow: var(--focus-ring-shadow) (L37)
- nearest mold size: **md** (font-size token; font-size=var(--font-base)); padding T/R/B/L = var(--space-2) / var(--space-3) / var(--space-2) / var(--space-3); width=100% @frontend/src/components.css:22 -> fullWidth=true
- layout-only residue to keep as layoutClassName/className: width: 100% [.form-group select]
- before -> after vs SelectControl bare md (7/13 equal):
  - padding-top: var(--space-2) -> var(--space-2)  (same)
  - padding-right: var(--space-3) -> var(--space-5)
  - padding-bottom: var(--space-2) -> var(--space-2)  (same)
  - padding-left: var(--space-3) -> var(--space-3)  (same)
  - border: 1px solid var(--border) -> 1px solid var(--border)  (same)
  - border-radius: var(--radius-sm) -> var(--comp-input-radius)
  - font-size: var(--font-base) -> var(--font-base)  (same)
  - color: var(--text-primary) -> var(--text-primary)  (same)
  - background-color: var(--bg-surface) -> var(--bg-surface)  (same)
  - background-image: none -> arrow-svg(url data:image/svg+xml chevron #888)
  - height: (unset: browser default) -> (none)
  - min-height: (unset: browser default) -> (none)
  - line-height: (unset: browser default) -> var(--line-height-base)

### 13. pages/bots/BotsPage.tsx:248  (BotsPage)
- opening tag: `<select required value={createForm.owner_staff_id} onChange={(e) => setCreateForm({ ...createForm, owner_staff_id: e.target.value })}>`
- className expr: (none) | inline style: (none)
- children kind: map (["option","map"]), disabledOption=false, onChange=`{(e) => setCreateForm({ ...createForm, owner_staff_id: e.target.value })}`, reads=["target.value"], numericConverted=false
- applied CSS rules:
  - `.form-group select` @ frontend/src/components.css:19 (0,1,1) state=base [definite]
    - LAYOUT: width: 100% (L22)
    - DECORATION: padding: var(--space-2) var(--space-3) (L23); border: 1px solid var(--border) (L24); border-radius: var(--radius-sm) (L25); font-size: var(--font-base) (L26); color: var(--text-primary) (L27); background: var(--bg-surface) (L28); box-sizing: border-box (L29)
  - `.form-group select:focus` @ frontend/src/components.css:32 (0,2,1) state=self:focus [definite]
    - DECORATION: outline: none (L35); border-color: var(--accent) (L36); box-shadow: var(--focus-ring-shadow) (L37)
- nearest mold size: **md** (font-size token; font-size=var(--font-base)); padding T/R/B/L = var(--space-2) / var(--space-3) / var(--space-2) / var(--space-3); width=100% @frontend/src/components.css:22 -> fullWidth=true
- layout-only residue to keep as layoutClassName/className: width: 100% [.form-group select]
- before -> after vs SelectControl bare md (7/13 equal):
  - padding-top: var(--space-2) -> var(--space-2)  (same)
  - padding-right: var(--space-3) -> var(--space-5)
  - padding-bottom: var(--space-2) -> var(--space-2)  (same)
  - padding-left: var(--space-3) -> var(--space-3)  (same)
  - border: 1px solid var(--border) -> 1px solid var(--border)  (same)
  - border-radius: var(--radius-sm) -> var(--comp-input-radius)
  - font-size: var(--font-base) -> var(--font-base)  (same)
  - color: var(--text-primary) -> var(--text-primary)  (same)
  - background-color: var(--bg-surface) -> var(--bg-surface)  (same)
  - background-image: none -> arrow-svg(url data:image/svg+xml chevron #888)
  - height: (unset: browser default) -> (none)
  - min-height: (unset: browser default) -> (none)
  - line-height: (unset: browser default) -> var(--line-height-base)

### 14. pages/commission-settings/CommissionSettingsPage.tsx:206  (CommissionSettingsPage)
- opening tag: `<select value={cfg.type} onChange={(e) => updateRole(role, { type: e.target.value as RateType }) } aria-label={`${ROLE_LABELS[role]} ${t("commissions.colCalcType")}`} data-testid={`settings-type-${role}`} >`
- className expr: (none) | inline style: (none)
- children kind: static-option (["option","option"]), disabledOption=false, onChange=`{(e) => updateRole(role, { type: e.target.value as RateType }) }`, reads=["target.value"], numericConverted=false
- applied CSS rules:
  - (none) -> unstyled
- nearest mold size: **md** (font-size token; font-size=unset); padding T/R/B/L = 0 / 0 / 0 / 0; width=unset -> fullWidth=false
- layout-only residue to keep as layoutClassName/className: (none)
- before -> after vs SelectControl bare md (0/13 equal):
  - padding-top: 0 -> var(--space-2)
  - padding-right: 0 -> var(--space-5)
  - padding-bottom: 0 -> var(--space-2)
  - padding-left: 0 -> var(--space-3)
  - border: (unset: browser default) -> 1px solid var(--border)
  - border-radius: (unset: browser default) -> var(--comp-input-radius)
  - font-size: (unset: browser default) -> var(--font-base)
  - color: (unset: browser default) -> var(--text-primary)
  - background-color: (unset: browser default) -> var(--bg-surface)
  - background-image: (unset: browser default) -> arrow-svg(url data:image/svg+xml chevron #888)
  - height: (unset: browser default) -> (none)
  - min-height: (unset: browser default) -> (none)
  - line-height: (unset: browser default) -> var(--line-height-base)

### 15. pages/companies/CompaniesPage.tsx:506  (CompaniesPage)
- opening tag: `<select value={createForm.status} onChange={(e) => setCreateForm({ ...createForm, status: e.target.value })}>`
- className expr: (none) | inline style: (none)
- children kind: static-option (["option","option","option","option"]), disabledOption=false, onChange=`{(e) => setCreateForm({ ...createForm, status: e.target.value })}`, reads=["target.value"], numericConverted=false
- applied CSS rules:
  - `.form-grid > .form-row select` @ frontend/src/company-forms.css:100 (0,2,1) state=base [definite]
    - LAYOUT: width: 100% (L109)
    - DECORATION: padding: var(--space-2) var(--space-3) (L103); border: 1px solid var(--border-strong) (L104); border-radius: var(--radius-md) (L105); font-size: var(--font-base) (L106); background: var(--bg-surface) (L107); color: var(--text-primary) (L108); box-sizing: border-box (L110); font-family: inherit (L111)
  - `.form-grid > .form-row select:focus` @ frontend/src/company-forms.css:120 (0,3,1) state=self:focus [definite]
    - DECORATION: outline: none (L123); border-color: var(--accent) (L124); box-shadow: var(--focus-ring-shadow) (L125)
  - `.modal-content-wide .form-row select` @ frontend/src/company-forms.css:156 (0,2,1) state=base [definite]
    - LAYOUT: width: 100% (L168)
    - DECORATION: padding: var(--space-2) var(--space-3) (L162); border: 1px solid var(--border-strong) (L163); border-radius: var(--radius-md) (L164); font-size: var(--font-base) (L165); background: var(--bg-surface) (L166); color: var(--text-primary) (L167); box-sizing: border-box (L169); font-family: inherit (L170)
  - `.modal-content-wide .form-row select:focus` @ frontend/src/company-forms.css:181 (0,3,1) state=self:focus [definite]
    - DECORATION: outline: none (L187); border-color: var(--accent) (L188); box-shadow: var(--focus-ring-shadow) (L189)
- nearest mold size: **md** (font-size token; font-size=var(--font-base)); padding T/R/B/L = var(--space-2) / var(--space-3) / var(--space-2) / var(--space-3); width=100% @frontend/src/company-forms.css:168 -> fullWidth=true
- layout-only residue to keep as layoutClassName/className: width: 100% [.form-grid > .form-row select]; width: 100% [.modal-content-wide .form-row select]
- before -> after vs SelectControl bare md (6/13 equal):
  - padding-top: var(--space-2) -> var(--space-2)  (same)
  - padding-right: var(--space-3) -> var(--space-5)
  - padding-bottom: var(--space-2) -> var(--space-2)  (same)
  - padding-left: var(--space-3) -> var(--space-3)  (same)
  - border: 1px solid var(--border-strong) -> 1px solid var(--border)
  - border-radius: var(--radius-md) -> var(--comp-input-radius)
  - font-size: var(--font-base) -> var(--font-base)  (same)
  - color: var(--text-primary) -> var(--text-primary)  (same)
  - background-color: var(--bg-surface) -> var(--bg-surface)  (same)
  - background-image: none -> arrow-svg(url data:image/svg+xml chevron #888)
  - height: (unset: browser default) -> (none)
  - min-height: (unset: browser default) -> (none)
  - line-height: (unset: browser default) -> var(--line-height-base)

### 16. pages/company-detail/CompanyBasicTab.tsx:84  (CompanyBasicTab)
- opening tag: `<select disabled={!canEdit} value={basicForm.status} onChange={(e) => { setBasicForm({ ...basicForm, status: e.target.value }); setBasicDirty(true); }}>`
- className expr: (none) | inline style: (none)
- children kind: static-option (["option","option","option","option"]), disabledOption=false, onChange=`{(e) => { setBasicForm({ ...basicForm, status: e.target.value }); setBasicDirty(true); }}`, reads=["target.value"], numericConverted=false
- applied CSS rules:
  - `.form-grid > .form-row select` @ frontend/src/company-forms.css:100 (0,2,1) state=base [definite]
    - LAYOUT: width: 100% (L109)
    - DECORATION: padding: var(--space-2) var(--space-3) (L103); border: 1px solid var(--border-strong) (L104); border-radius: var(--radius-md) (L105); font-size: var(--font-base) (L106); background: var(--bg-surface) (L107); color: var(--text-primary) (L108); box-sizing: border-box (L110); font-family: inherit (L111)
  - `.form-grid > .form-row select:focus` @ frontend/src/company-forms.css:120 (0,3,1) state=self:focus [definite]
    - DECORATION: outline: none (L123); border-color: var(--accent) (L124); box-shadow: var(--focus-ring-shadow) (L125)
- nearest mold size: **md** (font-size token; font-size=var(--font-base)); padding T/R/B/L = var(--space-2) / var(--space-3) / var(--space-2) / var(--space-3); width=100% @frontend/src/company-forms.css:109 -> fullWidth=true
- layout-only residue to keep as layoutClassName/className: width: 100% [.form-grid > .form-row select]
- before -> after vs SelectControl bare md (6/13 equal):
  - padding-top: var(--space-2) -> var(--space-2)  (same)
  - padding-right: var(--space-3) -> var(--space-5)
  - padding-bottom: var(--space-2) -> var(--space-2)  (same)
  - padding-left: var(--space-3) -> var(--space-3)  (same)
  - border: 1px solid var(--border-strong) -> 1px solid var(--border)
  - border-radius: var(--radius-md) -> var(--comp-input-radius)
  - font-size: var(--font-base) -> var(--font-base)  (same)
  - color: var(--text-primary) -> var(--text-primary)  (same)
  - background-color: var(--bg-surface) -> var(--bg-surface)  (same)
  - background-image: none -> arrow-svg(url data:image/svg+xml chevron #888)
  - height: (unset: browser default) -> (none)
  - min-height: (unset: browser default) -> (none)
  - line-height: (unset: browser default) -> var(--line-height-base)

### 17. pages/company-detail/CompanyConvLogsTab.tsx:73  (CompanyConvLogsTab)
- opening tag: `<select id="conv-contact-filter" className="conv-logs-filter-select" value={selectedContactId} onChange={(e) => setSelectedContactId(e.target.value)} aria-label={t("companies.convHistory.filterByContact")} >`
- className expr: `"conv-logs-filter-select"` | inline style: (none)
- children kind: map (["option","map"]), disabledOption=false, onChange=`{(e) => setSelectedContactId(e.target.value)}`, reads=["target.value"], numericConverted=false
- applied CSS rules:
  - (none) -> unstyled
- nearest mold size: **md** (font-size token; font-size=unset); padding T/R/B/L = 0 / 0 / 0 / 0; width=unset -> fullWidth=false
- layout-only residue to keep as layoutClassName/className: (none)
- before -> after vs SelectControl bare md (0/13 equal):
  - padding-top: 0 -> var(--space-2)
  - padding-right: 0 -> var(--space-5)
  - padding-bottom: 0 -> var(--space-2)
  - padding-left: 0 -> var(--space-3)
  - border: (unset: browser default) -> 1px solid var(--border)
  - border-radius: (unset: browser default) -> var(--comp-input-radius)
  - font-size: (unset: browser default) -> var(--font-base)
  - color: (unset: browser default) -> var(--text-primary)
  - background-color: (unset: browser default) -> var(--bg-surface)
  - background-image: (unset: browser default) -> arrow-svg(url data:image/svg+xml chevron #888)
  - height: (unset: browser default) -> (none)
  - min-height: (unset: browser default) -> (none)
  - line-height: (unset: browser default) -> var(--line-height-base)

### 18. pages/contacts/ContactsPage.tsx:273  (ContactsPage)
- opening tag: `<select className="search-input field-h-md field-w-sm" value={companyFilter} onChange={(e) => setCompanyFilter(e.target.value)}>`
- className expr: `"search-input field-h-md field-w-sm"` | inline style: (none)
- children kind: map (["option","map"]), disabledOption=false, onChange=`{(e) => setCompanyFilter(e.target.value)}`, reads=["target.value"], numericConverted=false
- applied CSS rules:
  - `.field-h-md` @ frontend/src/components/field-size.css:8 (0,1,0) state=base [definite]
    - DIMENSION owned by mold: min-height: var(--field-h-md, 36px) (L8)
    - DECORATION: box-sizing: border-box (L8)
  - `.field-w-sm` @ frontend/src/components/field-size.css:12 (0,1,0) state=base [definite]
    - LAYOUT: width: var(--field-w-sm, 160px) (L12)
  - `.content-toolbar .field-w-sm` @ frontend/src/components/field-size.css:18 (0,2,0) state=base [definite]
    - LAYOUT: margin-bottom: 0 (L20)
- nearest mold size: **md** (font-size token; font-size=unset); padding T/R/B/L = 0 / 0 / 0 / 0; width=var(--field-w-sm, 160px) @frontend/src/components/field-size.css:12 -> fullWidth=false
- layout-only residue to keep as layoutClassName/className: width: var(--field-w-sm, 160px) [.field-w-sm]; margin-bottom: 0 [.content-toolbar .field-w-sm]
- before -> after vs SelectControl bare md (0/13 equal):
  - padding-top: 0 -> var(--space-2)
  - padding-right: 0 -> var(--space-5)
  - padding-bottom: 0 -> var(--space-2)
  - padding-left: 0 -> var(--space-3)
  - border: (unset: browser default) -> 1px solid var(--border)
  - border-radius: (unset: browser default) -> var(--comp-input-radius)
  - font-size: (unset: browser default) -> var(--font-base)
  - color: (unset: browser default) -> var(--text-primary)
  - background-color: (unset: browser default) -> var(--bg-surface)
  - background-image: (unset: browser default) -> arrow-svg(url data:image/svg+xml chevron #888)
  - height: (unset: browser default) -> (none)
  - min-height: var(--field-h-md, 36px) -> (none)
  - line-height: (unset: browser default) -> var(--line-height-base)

### 19. pages/contacts/ContactsPage.tsx:308  (ContactsPage)
- opening tag: `<select required value={createForm.company_id} onChange={(e) => setCreateForm({ ...createForm, company_id: e.target.value })}>`
- className expr: (none) | inline style: (none)
- children kind: map (["option","map"]), disabledOption=false, onChange=`{(e) => setCreateForm({ ...createForm, company_id: e.target.value })}`, reads=["target.value"], numericConverted=false
- applied CSS rules:
  - `.form-grid > .form-row select` @ frontend/src/company-forms.css:100 (0,2,1) state=base [definite]
    - LAYOUT: width: 100% (L109)
    - DECORATION: padding: var(--space-2) var(--space-3) (L103); border: 1px solid var(--border-strong) (L104); border-radius: var(--radius-md) (L105); font-size: var(--font-base) (L106); background: var(--bg-surface) (L107); color: var(--text-primary) (L108); box-sizing: border-box (L110); font-family: inherit (L111)
  - `.form-grid > .form-row select:focus` @ frontend/src/company-forms.css:120 (0,3,1) state=self:focus [definite]
    - DECORATION: outline: none (L123); border-color: var(--accent) (L124); box-shadow: var(--focus-ring-shadow) (L125)
  - `.modal-content-wide .form-row select` @ frontend/src/company-forms.css:156 (0,2,1) state=base [definite]
    - LAYOUT: width: 100% (L168)
    - DECORATION: padding: var(--space-2) var(--space-3) (L162); border: 1px solid var(--border-strong) (L163); border-radius: var(--radius-md) (L164); font-size: var(--font-base) (L165); background: var(--bg-surface) (L166); color: var(--text-primary) (L167); box-sizing: border-box (L169); font-family: inherit (L170)
  - `.modal-content-wide .form-row select:focus` @ frontend/src/company-forms.css:181 (0,3,1) state=self:focus [definite]
    - DECORATION: outline: none (L187); border-color: var(--accent) (L188); box-shadow: var(--focus-ring-shadow) (L189)
- nearest mold size: **md** (font-size token; font-size=var(--font-base)); padding T/R/B/L = var(--space-2) / var(--space-3) / var(--space-2) / var(--space-3); width=100% @frontend/src/company-forms.css:168 -> fullWidth=true
- layout-only residue to keep as layoutClassName/className: width: 100% [.form-grid > .form-row select]; width: 100% [.modal-content-wide .form-row select]
- before -> after vs SelectControl bare md (6/13 equal):
  - padding-top: var(--space-2) -> var(--space-2)  (same)
  - padding-right: var(--space-3) -> var(--space-5)
  - padding-bottom: var(--space-2) -> var(--space-2)  (same)
  - padding-left: var(--space-3) -> var(--space-3)  (same)
  - border: 1px solid var(--border-strong) -> 1px solid var(--border)
  - border-radius: var(--radius-md) -> var(--comp-input-radius)
  - font-size: var(--font-base) -> var(--font-base)  (same)
  - color: var(--text-primary) -> var(--text-primary)  (same)
  - background-color: var(--bg-surface) -> var(--bg-surface)  (same)
  - background-image: none -> arrow-svg(url data:image/svg+xml chevron #888)
  - height: (unset: browser default) -> (none)
  - min-height: (unset: browser default) -> (none)
  - line-height: (unset: browser default) -> var(--line-height-base)

### 20. pages/contacts/ContactsPage.tsx:341  (ContactsPage)
- opening tag: `<select value={createForm.status} onChange={(e) => setCreateForm({ ...createForm, status: e.target.value })}>`
- className expr: (none) | inline style: (none)
- children kind: static-option (["option","option","option"]), disabledOption=false, onChange=`{(e) => setCreateForm({ ...createForm, status: e.target.value })}`, reads=["target.value"], numericConverted=false
- applied CSS rules:
  - `.form-grid > .form-row select` @ frontend/src/company-forms.css:100 (0,2,1) state=base [definite]
    - LAYOUT: width: 100% (L109)
    - DECORATION: padding: var(--space-2) var(--space-3) (L103); border: 1px solid var(--border-strong) (L104); border-radius: var(--radius-md) (L105); font-size: var(--font-base) (L106); background: var(--bg-surface) (L107); color: var(--text-primary) (L108); box-sizing: border-box (L110); font-family: inherit (L111)
  - `.form-grid > .form-row select:focus` @ frontend/src/company-forms.css:120 (0,3,1) state=self:focus [definite]
    - DECORATION: outline: none (L123); border-color: var(--accent) (L124); box-shadow: var(--focus-ring-shadow) (L125)
  - `.modal-content-wide .form-row select` @ frontend/src/company-forms.css:156 (0,2,1) state=base [definite]
    - LAYOUT: width: 100% (L168)
    - DECORATION: padding: var(--space-2) var(--space-3) (L162); border: 1px solid var(--border-strong) (L163); border-radius: var(--radius-md) (L164); font-size: var(--font-base) (L165); background: var(--bg-surface) (L166); color: var(--text-primary) (L167); box-sizing: border-box (L169); font-family: inherit (L170)
  - `.modal-content-wide .form-row select:focus` @ frontend/src/company-forms.css:181 (0,3,1) state=self:focus [definite]
    - DECORATION: outline: none (L187); border-color: var(--accent) (L188); box-shadow: var(--focus-ring-shadow) (L189)
- nearest mold size: **md** (font-size token; font-size=var(--font-base)); padding T/R/B/L = var(--space-2) / var(--space-3) / var(--space-2) / var(--space-3); width=100% @frontend/src/company-forms.css:168 -> fullWidth=true
- layout-only residue to keep as layoutClassName/className: width: 100% [.form-grid > .form-row select]; width: 100% [.modal-content-wide .form-row select]
- before -> after vs SelectControl bare md (6/13 equal):
  - padding-top: var(--space-2) -> var(--space-2)  (same)
  - padding-right: var(--space-3) -> var(--space-5)
  - padding-bottom: var(--space-2) -> var(--space-2)  (same)
  - padding-left: var(--space-3) -> var(--space-3)  (same)
  - border: 1px solid var(--border-strong) -> 1px solid var(--border)
  - border-radius: var(--radius-md) -> var(--comp-input-radius)
  - font-size: var(--font-base) -> var(--font-base)  (same)
  - color: var(--text-primary) -> var(--text-primary)  (same)
  - background-color: var(--bg-surface) -> var(--bg-surface)  (same)
  - background-image: none -> arrow-svg(url data:image/svg+xml chevron #888)
  - height: (unset: browser default) -> (none)
  - min-height: (unset: browser default) -> (none)
  - line-height: (unset: browser default) -> var(--line-height-base)

### 21. pages/goal-setting/GoalSettingPage.tsx:711  (GoalSettingPage)
- opening tag: `<select className="gs-select" value={selectedTeamId ?? ""} onChange={(e) => setSelectedTeamId(Number(e.target.value))} >`
- className expr: `"gs-select"` | inline style: (none)
- children kind: map (["map"]), disabledOption=false, onChange=`{(e) => setSelectedTeamId(Number(e.target.value))}`, reads=["target.value"], numericConverted=true
- applied CSS rules:
  - `.gs-select` @ frontend/src/pages/goal-setting/GoalSettingPage.css:555 (0,1,0) state=base [definite]
    - LAYOUT: flex: 1 (L556)
    - DECORATION: padding: var(--space-2) var(--space-3) (L557); border: 1px solid var(--border) (L558); border-radius: var(--radius-md) (L559); background: var(--bg-surface) (L560); color: var(--text-primary) (L561); font-size: var(--font-sm) (L562); cursor: pointer (L563)
- nearest mold size: **sm** (font-size token; font-size=var(--font-sm)); padding T/R/B/L = var(--space-2) / var(--space-3) / var(--space-2) / var(--space-3); width=unset -> fullWidth=false
- layout-only residue to keep as layoutClassName/className: flex: 1 [.gs-select]
- before -> after vs SelectControl bare sm (4/13 equal):
  - padding-top: var(--space-2) -> var(--space-1)
  - padding-right: var(--space-3) -> var(--space-5)
  - padding-bottom: var(--space-2) -> var(--space-1)
  - padding-left: var(--space-3) -> var(--space-2)
  - border: 1px solid var(--border) -> 1px solid var(--border)  (same)
  - border-radius: var(--radius-md) -> var(--comp-input-radius)
  - font-size: var(--font-sm) -> var(--font-sm)  (same)
  - color: var(--text-primary) -> var(--text-primary)  (same)
  - background-color: var(--bg-surface) -> var(--bg-surface)  (same)
  - background-image: none -> arrow-svg(url data:image/svg+xml chevron #888)
  - height: (unset: browser default) -> (none)
  - min-height: (unset: browser default) -> var(--comp-input-height-sm)
  - line-height: (unset: browser default) -> var(--line-height-base)

### 22. pages/inbox/InboxConversationList.tsx:147  (InboxConversationList)
- opening tag: `<select value={pageIdFilter} onChange={(e) => onPageFilterChange(e.target.value)} aria-label="Filter by Page" className="inbox-page-filter-select" >`
- className expr: `"inbox-page-filter-select"` | inline style: (none)
- children kind: map (["option","map"]), disabledOption=false, onChange=`{(e) => onPageFilterChange(e.target.value)}`, reads=["target.value"], numericConverted=false
- applied CSS rules:
  - `.inbox-page-filter-select` @ frontend/src/pages/inbox/InboxPage.css:398 (0,1,0) state=base [definite]
    - LAYOUT: width: 100% (L399)
    - DECORATION: padding: var(--space-1) var(--space-2) (L400); font-size: var(--font-xs) (L401); border-radius: var(--radius-xl) (L402); border: 1px solid var(--border) (L403); background: var(--bg-surface) (L404); color: var(--text-primary) (L405); font-family: inherit (L406); box-sizing: border-box (L407)
- nearest mold size: **sm** (font-size token; font-size=var(--font-xs)); padding T/R/B/L = var(--space-1) / var(--space-2) / var(--space-1) / var(--space-2); width=100% @frontend/src/pages/inbox/InboxPage.css:399 -> fullWidth=true
- layout-only residue to keep as layoutClassName/className: width: 100% [.inbox-page-filter-select]
- before -> after vs SelectControl bare sm (6/13 equal):
  - padding-top: var(--space-1) -> var(--space-1)  (same)
  - padding-right: var(--space-2) -> var(--space-5)
  - padding-bottom: var(--space-1) -> var(--space-1)  (same)
  - padding-left: var(--space-2) -> var(--space-2)  (same)
  - border: 1px solid var(--border) -> 1px solid var(--border)  (same)
  - border-radius: var(--radius-xl) -> var(--comp-input-radius)
  - font-size: var(--font-xs) -> var(--font-sm)
  - color: var(--text-primary) -> var(--text-primary)  (same)
  - background-color: var(--bg-surface) -> var(--bg-surface)  (same)
  - background-image: none -> arrow-svg(url data:image/svg+xml chevron #888)
  - height: (unset: browser default) -> (none)
  - min-height: (unset: browser default) -> var(--comp-input-height-sm)
  - line-height: (unset: browser default) -> var(--line-height-base)

### 23. pages/inbox/InboxSettingsModal.tsx:37  (InboxSettingsModal)
- opening tag: `<select className="inbox-settings-select" value={inboxSettings.defaultTab} onChange={(e) => updateInboxSetting("defaultTab", e.target.value as StatusTabKey)}>`
- className expr: `"inbox-settings-select"` | inline style: (none)
- children kind: static-option (["option","option","option","option","option","option"]), disabledOption=false, onChange=`{(e) => updateInboxSetting("defaultTab", e.target.value as StatusTabKey)}`, reads=["target.value"], numericConverted=false
- applied CSS rules:
  - `.inbox-settings-select` @ frontend/src/pages/inbox/InboxPage.css:1424 (0,1,0) state=base [definite]
    - DECORATION: background: var(--bg-primary) (L1425); border: 1px solid var(--border) (L1425); border-radius: var(--radius-sm) (L1426); padding: var(--space-1) var(--space-2) (L1426); font-size: var(--font-sm) (L1427); color: var(--text-primary) (L1427); cursor: pointer (L1428)
- nearest mold size: **sm** (font-size token; font-size=var(--font-sm)); padding T/R/B/L = var(--space-1) / var(--space-2) / var(--space-1) / var(--space-2); width=unset -> fullWidth=false
- layout-only residue to keep as layoutClassName/className: (none)
- before -> after vs SelectControl bare sm (6/13 equal):
  - padding-top: var(--space-1) -> var(--space-1)  (same)
  - padding-right: var(--space-2) -> var(--space-5)
  - padding-bottom: var(--space-1) -> var(--space-1)  (same)
  - padding-left: var(--space-2) -> var(--space-2)  (same)
  - border: 1px solid var(--border) -> 1px solid var(--border)  (same)
  - border-radius: var(--radius-sm) -> var(--comp-input-radius)
  - font-size: var(--font-sm) -> var(--font-sm)  (same)
  - color: var(--text-primary) -> var(--text-primary)  (same)
  - background-color: var(--bg-primary) -> var(--bg-surface)
  - background-image: none -> arrow-svg(url data:image/svg+xml chevron #888)
  - height: (unset: browser default) -> (none)
  - min-height: (unset: browser default) -> var(--comp-input-height-sm)
  - line-height: (unset: browser default) -> var(--line-height-base)

### 24. pages/inbox/ManualRecordSection.tsx:126  (ManualRecordSection)
- opening tag: `<select id="manual-channel-select" className="manual-record-select" value={channelType} onChange={(e) => setChannelType(e.target.value)} disabled={saving} aria-label={t("inbox.manualRecord.channelLabel")} >`
- className expr: `"manual-record-select"` | inline style: (none)
- children kind: map (["map"]), disabledOption=false, onChange=`{(e) => setChannelType(e.target.value)}`, reads=["target.value"], numericConverted=false
- applied CSS rules:
  - (none) -> unstyled
- nearest mold size: **md** (font-size token; font-size=unset); padding T/R/B/L = 0 / 0 / 0 / 0; width=unset -> fullWidth=false
- layout-only residue to keep as layoutClassName/className: (none)
- before -> after vs SelectControl bare md (0/13 equal):
  - padding-top: 0 -> var(--space-2)
  - padding-right: 0 -> var(--space-5)
  - padding-bottom: 0 -> var(--space-2)
  - padding-left: 0 -> var(--space-3)
  - border: (unset: browser default) -> 1px solid var(--border)
  - border-radius: (unset: browser default) -> var(--comp-input-radius)
  - font-size: (unset: browser default) -> var(--font-base)
  - color: (unset: browser default) -> var(--text-primary)
  - background-color: (unset: browser default) -> var(--bg-surface)
  - background-image: (unset: browser default) -> arrow-svg(url data:image/svg+xml chevron #888)
  - height: (unset: browser default) -> (none)
  - min-height: (unset: browser default) -> (none)
  - line-height: (unset: browser default) -> var(--line-height-base)

### 25. pages/integrations/FedexEtdSetupGuide.tsx:493  (FedexEtdSetupGuide)
- opening tag: `<select id="etd-environment" value={etdEnvironment} onChange={(e) => setEtdEnvironment(e.target.value as Env)} >`
- className expr: (none) | inline style: (none)
- children kind: static-option (["option","option"]), disabledOption=false, onChange=`{(e) => setEtdEnvironment(e.target.value as Env)}`, reads=["target.value"], numericConverted=false
- resolution note: unconfirmed rules (.product-edit-form .form-group select, .filter-bar select) arise only from the alternative usage chain via FedexLabelValidationTab, which has no JSX/import site in src (grep FedexLabelValidationTab: only itself + FedexEtdSetupGuide.tsx:8 css import). Live chain = CarrierSetupGuidePage.tsx:43 -> FedexEtdSetupGuide -> div.form-group (definite). Effective rules = the definite ones.
- applied CSS rules:
  - `.form-group select` @ frontend/src/components.css:19 (0,1,1) state=base [definite]
    - LAYOUT: width: 100% (L22)
    - DECORATION: padding: var(--space-2) var(--space-3) (L23); border: 1px solid var(--border) (L24); border-radius: var(--radius-sm) (L25); font-size: var(--font-base) (L26); color: var(--text-primary) (L27); background: var(--bg-surface) (L28); box-sizing: border-box (L29)
  - `.form-group select:focus` @ frontend/src/components.css:32 (0,2,1) state=self:focus [definite]
    - DECORATION: outline: none (L35); border-color: var(--accent) (L36); box-shadow: var(--focus-ring-shadow) (L37)
- unconfirmed rules (not counted): .product-edit-form .form-group select@frontend/src/company-forms.css:260; .filter-bar select@frontend/src/components.css:60
- nearest mold size: **md** (font-size token; font-size=var(--font-base)); padding T/R/B/L = var(--space-2) / var(--space-3) / var(--space-2) / var(--space-3); width=100% @frontend/src/components.css:22 -> fullWidth=true
- layout-only residue to keep as layoutClassName/className: width: 100% [.form-group select]
- before -> after vs SelectControl bare md (7/13 equal):
  - padding-top: var(--space-2) -> var(--space-2)  (same)
  - padding-right: var(--space-3) -> var(--space-5)
  - padding-bottom: var(--space-2) -> var(--space-2)  (same)
  - padding-left: var(--space-3) -> var(--space-3)  (same)
  - border: 1px solid var(--border) -> 1px solid var(--border)  (same)
  - border-radius: var(--radius-sm) -> var(--comp-input-radius)
  - font-size: var(--font-base) -> var(--font-base)  (same)
  - color: var(--text-primary) -> var(--text-primary)  (same)
  - background-color: var(--bg-surface) -> var(--bg-surface)  (same)
  - background-image: none -> arrow-svg(url data:image/svg+xml chevron #888)
  - height: (unset: browser default) -> (none)
  - min-height: (unset: browser default) -> (none)
  - line-height: (unset: browser default) -> var(--line-height-base)

### 26. pages/integrations/PaypalIntegrationPage.tsx:164  (PaypalIntegrationPage)
- opening tag: `<select id="paypal-env" value={environment} onChange={(e) => setEnvironment(e.target.value)} >`
- className expr: (none) | inline style: (none)
- children kind: static-option (["option","option"]), disabledOption=false, onChange=`{(e) => setEnvironment(e.target.value)}`, reads=["target.value"], numericConverted=false
- applied CSS rules:
  - `.form-group select` @ frontend/src/components.css:19 (0,1,1) state=base [definite]
    - LAYOUT: width: 100% (L22)
    - DECORATION: padding: var(--space-2) var(--space-3) (L23); border: 1px solid var(--border) (L24); border-radius: var(--radius-sm) (L25); font-size: var(--font-base) (L26); color: var(--text-primary) (L27); background: var(--bg-surface) (L28); box-sizing: border-box (L29)
  - `.form-group select:focus` @ frontend/src/components.css:32 (0,2,1) state=self:focus [definite]
    - DECORATION: outline: none (L35); border-color: var(--accent) (L36); box-shadow: var(--focus-ring-shadow) (L37)
- nearest mold size: **md** (font-size token; font-size=var(--font-base)); padding T/R/B/L = var(--space-2) / var(--space-3) / var(--space-2) / var(--space-3); width=100% @frontend/src/components.css:22 -> fullWidth=true
- layout-only residue to keep as layoutClassName/className: width: 100% [.form-group select]
- before -> after vs SelectControl bare md (7/13 equal):
  - padding-top: var(--space-2) -> var(--space-2)  (same)
  - padding-right: var(--space-3) -> var(--space-5)
  - padding-bottom: var(--space-2) -> var(--space-2)  (same)
  - padding-left: var(--space-3) -> var(--space-3)  (same)
  - border: 1px solid var(--border) -> 1px solid var(--border)  (same)
  - border-radius: var(--radius-sm) -> var(--comp-input-radius)
  - font-size: var(--font-base) -> var(--font-base)  (same)
  - color: var(--text-primary) -> var(--text-primary)  (same)
  - background-color: var(--bg-surface) -> var(--bg-surface)  (same)
  - background-image: none -> arrow-svg(url data:image/svg+xml chevron #888)
  - height: (unset: browser default) -> (none)
  - min-height: (unset: browser default) -> (none)
  - line-height: (unset: browser default) -> var(--line-height-base)

### 27. pages/inventory/InventoryPage.tsx:477  (InventoryPage)
- opening tag: `<select value={["pokemon_booster_box", "one_piece", "dragon_ball", "all"].includes(activeTab) ? "" : activeTab} onChange={(e) => { if (e.target.value) { setActiveTab(e.target.value); setPage(1); } }} aria-label={t("inventory.filter.otherTypes")} style={{ fontSize: "var(--font-xs)", padding: "var(--space-1) var(--space-10px)", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", background: "var(--bg-surface)" }} >`
- className expr: (none) | inline style: `{{ fontSize: "var(--font-xs)", padding: "var(--space-1) var(--space-10px)", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", background: "var(--bg-surface)" }}`
- children kind: map (["option","map"]), disabledOption=false, onChange=`{(e) => { if (e.target.value) { setActiveTab(e.target.value); setPage(1); } }}`, reads=["target.value"], numericConverted=false
- ui-allow (verbatim): `// ui-allow: TCG "other types" dropdown from main back-merge, ADR-143 D-1 (#2624)` (L476, preceding)
- applied CSS rules:
  - (none) -> unstyled
- inline style props: font-size: var(--font-xs) [decoration]; padding: var(--space-1) var(--space-10px) [decoration]; border: 1px solid var(--border) [decoration]; border-radius: var(--radius-sm) [decoration]; background: var(--bg-surface) [decoration]  | non-var() residue: [{"prop":"border","value":"1px solid var(--border)","residual":"1px solid"}]
- nearest mold size: **sm** (font-size token; font-size=var(--font-xs)); padding T/R/B/L = var(--space-1) / var(--space-10px) / var(--space-1) / var(--space-10px); width=unset -> fullWidth=false
- layout-only residue to keep as layoutClassName/className: (none)
- before -> after vs SelectControl bare sm (4/13 equal):
  - padding-top: var(--space-1) -> var(--space-1)  (same)
  - padding-right: var(--space-10px) -> var(--space-5)
  - padding-bottom: var(--space-1) -> var(--space-1)  (same)
  - padding-left: var(--space-10px) -> var(--space-2)
  - border: 1px solid var(--border) -> 1px solid var(--border)  (same)
  - border-radius: var(--radius-sm) -> var(--comp-input-radius)
  - font-size: var(--font-xs) -> var(--font-sm)
  - color: (unset: browser default) -> var(--text-primary)
  - background-color: var(--bg-surface) -> var(--bg-surface)  (same)
  - background-image: none -> arrow-svg(url data:image/svg+xml chevron #888)
  - height: (unset: browser default) -> (none)
  - min-height: (unset: browser default) -> var(--comp-input-height-sm)
  - line-height: (unset: browser default) -> var(--line-height-base)

### 28. pages/invoice-create/InvoiceCreatePage.tsx:308  (InvoiceCreatePage)
- opening tag: `<select value={currency} onChange={(e) => setCurrency(e.target.value)}>`
- className expr: (none) | inline style: (none)
- children kind: static-option (["option","option","option"]), disabledOption=false, onChange=`{(e) => setCurrency(e.target.value)}`, reads=["target.value"], numericConverted=false
- applied CSS rules:
  - `.form-group select` @ frontend/src/components.css:19 (0,1,1) state=base [definite]
    - LAYOUT: width: 100% (L22)
    - DECORATION: padding: var(--space-2) var(--space-3) (L23); border: 1px solid var(--border) (L24); border-radius: var(--radius-sm) (L25); font-size: var(--font-base) (L26); color: var(--text-primary) (L27); background: var(--bg-surface) (L28); box-sizing: border-box (L29)
  - `.form-group select:focus` @ frontend/src/components.css:32 (0,2,1) state=self:focus [definite]
    - DECORATION: outline: none (L35); border-color: var(--accent) (L36); box-shadow: var(--focus-ring-shadow) (L37)
- nearest mold size: **md** (font-size token; font-size=var(--font-base)); padding T/R/B/L = var(--space-2) / var(--space-3) / var(--space-2) / var(--space-3); width=100% @frontend/src/components.css:22 -> fullWidth=true
- layout-only residue to keep as layoutClassName/className: width: 100% [.form-group select]
- before -> after vs SelectControl bare md (7/13 equal):
  - padding-top: var(--space-2) -> var(--space-2)  (same)
  - padding-right: var(--space-3) -> var(--space-5)
  - padding-bottom: var(--space-2) -> var(--space-2)  (same)
  - padding-left: var(--space-3) -> var(--space-3)  (same)
  - border: 1px solid var(--border) -> 1px solid var(--border)  (same)
  - border-radius: var(--radius-sm) -> var(--comp-input-radius)
  - font-size: var(--font-base) -> var(--font-base)  (same)
  - color: var(--text-primary) -> var(--text-primary)  (same)
  - background-color: var(--bg-surface) -> var(--bg-surface)  (same)
  - background-image: none -> arrow-svg(url data:image/svg+xml chevron #888)
  - height: (unset: browser default) -> (none)
  - min-height: (unset: browser default) -> (none)
  - line-height: (unset: browser default) -> var(--line-height-base)

### 29. pages/orders/OrdersFilterBar.tsx:40  (OrdersFilterBar)
- opening tag: `<select className="field-h-md field-w-sm" value={sortBy} onChange={(e) => setSortBy(e.target.value)} aria-label={t("common.filter")} data-testid="orders-sort-by" >`
- className expr: `"field-h-md field-w-sm"` | inline style: (none)
- children kind: map (["map"]), disabledOption=false, onChange=`{(e) => setSortBy(e.target.value)}`, reads=["target.value"], numericConverted=false
- applied CSS rules:
  - `.field-h-md` @ frontend/src/components/field-size.css:8 (0,1,0) state=base [definite]
    - DIMENSION owned by mold: min-height: var(--field-h-md, 36px) (L8)
    - DECORATION: box-sizing: border-box (L8)
  - `.field-w-sm` @ frontend/src/components/field-size.css:12 (0,1,0) state=base [definite]
    - LAYOUT: width: var(--field-w-sm, 160px) (L12)
  - `.content-toolbar .field-w-sm` @ frontend/src/components/field-size.css:18 (0,2,0) state=base [definite]
    - LAYOUT: margin-bottom: 0 (L20)
- nearest mold size: **md** (font-size token; font-size=unset); padding T/R/B/L = 0 / 0 / 0 / 0; width=var(--field-w-sm, 160px) @frontend/src/components/field-size.css:12 -> fullWidth=false
- layout-only residue to keep as layoutClassName/className: width: var(--field-w-sm, 160px) [.field-w-sm]; margin-bottom: 0 [.content-toolbar .field-w-sm]
- before -> after vs SelectControl bare md (0/13 equal):
  - padding-top: 0 -> var(--space-2)
  - padding-right: 0 -> var(--space-5)
  - padding-bottom: 0 -> var(--space-2)
  - padding-left: 0 -> var(--space-3)
  - border: (unset: browser default) -> 1px solid var(--border)
  - border-radius: (unset: browser default) -> var(--comp-input-radius)
  - font-size: (unset: browser default) -> var(--font-base)
  - color: (unset: browser default) -> var(--text-primary)
  - background-color: (unset: browser default) -> var(--bg-surface)
  - background-image: (unset: browser default) -> arrow-svg(url data:image/svg+xml chevron #888)
  - height: (unset: browser default) -> (none)
  - min-height: var(--field-h-md, 36px) -> (none)
  - line-height: (unset: browser default) -> var(--line-height-base)

### 30. pages/orders/OrdersFormModal.tsx:86  (OrdersFormModal)
- opening tag: `<select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>`
- className expr: (none) | inline style: (none)
- children kind: map (["map"]), disabledOption=false, onChange=`{(e) => setForm({ ...form, status: e.target.value })}`, reads=["target.value"], numericConverted=false
- applied CSS rules:
  - `.form-group select` @ frontend/src/components.css:19 (0,1,1) state=base [definite]
    - LAYOUT: width: 100% (L22)
    - DECORATION: padding: var(--space-2) var(--space-3) (L23); border: 1px solid var(--border) (L24); border-radius: var(--radius-sm) (L25); font-size: var(--font-base) (L26); color: var(--text-primary) (L27); background: var(--bg-surface) (L28); box-sizing: border-box (L29)
  - `.form-group select:focus` @ frontend/src/components.css:32 (0,2,1) state=self:focus [definite]
    - DECORATION: outline: none (L35); border-color: var(--accent) (L36); box-shadow: var(--focus-ring-shadow) (L37)
- nearest mold size: **md** (font-size token; font-size=var(--font-base)); padding T/R/B/L = var(--space-2) / var(--space-3) / var(--space-2) / var(--space-3); width=100% @frontend/src/components.css:22 -> fullWidth=true
- layout-only residue to keep as layoutClassName/className: width: 100% [.form-group select]
- before -> after vs SelectControl bare md (7/13 equal):
  - padding-top: var(--space-2) -> var(--space-2)  (same)
  - padding-right: var(--space-3) -> var(--space-5)
  - padding-bottom: var(--space-2) -> var(--space-2)  (same)
  - padding-left: var(--space-3) -> var(--space-3)  (same)
  - border: 1px solid var(--border) -> 1px solid var(--border)  (same)
  - border-radius: var(--radius-sm) -> var(--comp-input-radius)
  - font-size: var(--font-base) -> var(--font-base)  (same)
  - color: var(--text-primary) -> var(--text-primary)  (same)
  - background-color: var(--bg-surface) -> var(--bg-surface)  (same)
  - background-image: none -> arrow-svg(url data:image/svg+xml chevron #888)
  - height: (unset: browser default) -> (none)
  - min-height: (unset: browser default) -> (none)
  - line-height: (unset: browser default) -> var(--line-height-base)

### 31. pages/products/ProductsPage.tsx:220  (ProductsPage)
- opening tag: `<select className="field-h-md field-w-sm" value={tcgType} onChange={(e) => { setTcgType(e.target.value); setPage(1); }} aria-label={t("products.filterByTcgType")} data-testid="products-tcg-type-filter" >`
- className expr: `"field-h-md field-w-sm"` | inline style: (none)
- children kind: map (["option","map"]), disabledOption=false, onChange=`{(e) => { setTcgType(e.target.value); setPage(1); }}`, reads=["target.value"], numericConverted=false
- applied CSS rules:
  - `.field-h-md` @ frontend/src/components/field-size.css:8 (0,1,0) state=base [definite]
    - DIMENSION owned by mold: min-height: var(--field-h-md, 36px) (L8)
    - DECORATION: box-sizing: border-box (L8)
  - `.field-w-sm` @ frontend/src/components/field-size.css:12 (0,1,0) state=base [definite]
    - LAYOUT: width: var(--field-w-sm, 160px) (L12)
  - `.content-toolbar .field-w-sm` @ frontend/src/components/field-size.css:18 (0,2,0) state=base [definite]
    - LAYOUT: margin-bottom: 0 (L20)
- nearest mold size: **md** (font-size token; font-size=unset); padding T/R/B/L = 0 / 0 / 0 / 0; width=var(--field-w-sm, 160px) @frontend/src/components/field-size.css:12 -> fullWidth=false
- layout-only residue to keep as layoutClassName/className: width: var(--field-w-sm, 160px) [.field-w-sm]; margin-bottom: 0 [.content-toolbar .field-w-sm]
- before -> after vs SelectControl bare md (0/13 equal):
  - padding-top: 0 -> var(--space-2)
  - padding-right: 0 -> var(--space-5)
  - padding-bottom: 0 -> var(--space-2)
  - padding-left: 0 -> var(--space-3)
  - border: (unset: browser default) -> 1px solid var(--border)
  - border-radius: (unset: browser default) -> var(--comp-input-radius)
  - font-size: (unset: browser default) -> var(--font-base)
  - color: (unset: browser default) -> var(--text-primary)
  - background-color: (unset: browser default) -> var(--bg-surface)
  - background-image: (unset: browser default) -> arrow-svg(url data:image/svg+xml chevron #888)
  - height: (unset: browser default) -> (none)
  - min-height: var(--field-h-md, 36px) -> (none)
  - line-height: (unset: browser default) -> var(--line-height-base)

### 32. pages/purchase-orders/PurchaseOrdersFormModal.tsx:156  (PurchaseOrdersFormModal)
- opening tag: `<select required value={supplierId} onChange={(e) => setSupplierId(e.target.value ? Number(e.target.value) : "")}>`
- className expr: (none) | inline style: (none)
- children kind: map (["option","map"]), disabledOption=false, onChange=`{(e) => setSupplierId(e.target.value ? Number(e.target.value) : "")}`, reads=["target.value"], numericConverted=true
- applied CSS rules:
  - `.form-group select` @ frontend/src/components.css:19 (0,1,1) state=base [definite]
    - LAYOUT: width: 100% (L22)
    - DECORATION: padding: var(--space-2) var(--space-3) (L23); border: 1px solid var(--border) (L24); border-radius: var(--radius-sm) (L25); font-size: var(--font-base) (L26); color: var(--text-primary) (L27); background: var(--bg-surface) (L28); box-sizing: border-box (L29)
  - `.form-group select:focus` @ frontend/src/components.css:32 (0,2,1) state=self:focus [definite]
    - DECORATION: outline: none (L35); border-color: var(--accent) (L36); box-shadow: var(--focus-ring-shadow) (L37)
- nearest mold size: **md** (font-size token; font-size=var(--font-base)); padding T/R/B/L = var(--space-2) / var(--space-3) / var(--space-2) / var(--space-3); width=100% @frontend/src/components.css:22 -> fullWidth=true
- layout-only residue to keep as layoutClassName/className: width: 100% [.form-group select]
- before -> after vs SelectControl bare md (7/13 equal):
  - padding-top: var(--space-2) -> var(--space-2)  (same)
  - padding-right: var(--space-3) -> var(--space-5)
  - padding-bottom: var(--space-2) -> var(--space-2)  (same)
  - padding-left: var(--space-3) -> var(--space-3)  (same)
  - border: 1px solid var(--border) -> 1px solid var(--border)  (same)
  - border-radius: var(--radius-sm) -> var(--comp-input-radius)
  - font-size: var(--font-base) -> var(--font-base)  (same)
  - color: var(--text-primary) -> var(--text-primary)  (same)
  - background-color: var(--bg-surface) -> var(--bg-surface)  (same)
  - background-image: none -> arrow-svg(url data:image/svg+xml chevron #888)
  - height: (unset: browser default) -> (none)
  - min-height: (unset: browser default) -> (none)
  - line-height: (unset: browser default) -> var(--line-height-base)

### 33. pages/purchase-orders/PurchaseOrdersPage.tsx:193  (PurchaseOrdersPage)
- opening tag: `<select className="field-h-md field-w-sm" value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>`
- className expr: `"field-h-md field-w-sm"` | inline style: (none)
- children kind: map (["option","map"]), disabledOption=false, onChange=`{e => setStatusFilter(e.target.value)}`, reads=["target.value"], numericConverted=false
- applied CSS rules:
  - `.field-h-md` @ frontend/src/components/field-size.css:8 (0,1,0) state=base [definite]
    - DIMENSION owned by mold: min-height: var(--field-h-md, 36px) (L8)
    - DECORATION: box-sizing: border-box (L8)
  - `.field-w-sm` @ frontend/src/components/field-size.css:12 (0,1,0) state=base [definite]
    - LAYOUT: width: var(--field-w-sm, 160px) (L12)
  - `.content-toolbar .field-w-sm` @ frontend/src/components/field-size.css:18 (0,2,0) state=base [definite]
    - LAYOUT: margin-bottom: 0 (L20)
- nearest mold size: **md** (font-size token; font-size=unset); padding T/R/B/L = 0 / 0 / 0 / 0; width=var(--field-w-sm, 160px) @frontend/src/components/field-size.css:12 -> fullWidth=false
- layout-only residue to keep as layoutClassName/className: width: var(--field-w-sm, 160px) [.field-w-sm]; margin-bottom: 0 [.content-toolbar .field-w-sm]
- before -> after vs SelectControl bare md (0/13 equal):
  - padding-top: 0 -> var(--space-2)
  - padding-right: 0 -> var(--space-5)
  - padding-bottom: 0 -> var(--space-2)
  - padding-left: 0 -> var(--space-3)
  - border: (unset: browser default) -> 1px solid var(--border)
  - border-radius: (unset: browser default) -> var(--comp-input-radius)
  - font-size: (unset: browser default) -> var(--font-base)
  - color: (unset: browser default) -> var(--text-primary)
  - background-color: (unset: browser default) -> var(--bg-surface)
  - background-image: (unset: browser default) -> arrow-svg(url data:image/svg+xml chevron #888)
  - height: (unset: browser default) -> (none)
  - min-height: var(--field-h-md, 36px) -> (none)
  - line-height: (unset: browser default) -> var(--line-height-base)

### 34. pages/quote-create/QuoteCreatePage.tsx:157  (QuoteCreatePage)
- opening tag: `<select value={currency} onChange={(e) => setCurrency(e.target.value)}>`
- className expr: (none) | inline style: (none)
- children kind: static-option (["option","option","option"]), disabledOption=false, onChange=`{(e) => setCurrency(e.target.value)}`, reads=["target.value"], numericConverted=false
- applied CSS rules:
  - `.form-group select` @ frontend/src/components.css:19 (0,1,1) state=base [definite]
    - LAYOUT: width: 100% (L22)
    - DECORATION: padding: var(--space-2) var(--space-3) (L23); border: 1px solid var(--border) (L24); border-radius: var(--radius-sm) (L25); font-size: var(--font-base) (L26); color: var(--text-primary) (L27); background: var(--bg-surface) (L28); box-sizing: border-box (L29)
  - `.form-group select:focus` @ frontend/src/components.css:32 (0,2,1) state=self:focus [definite]
    - DECORATION: outline: none (L35); border-color: var(--accent) (L36); box-shadow: var(--focus-ring-shadow) (L37)
- nearest mold size: **md** (font-size token; font-size=var(--font-base)); padding T/R/B/L = var(--space-2) / var(--space-3) / var(--space-2) / var(--space-3); width=100% @frontend/src/components.css:22 -> fullWidth=true
- layout-only residue to keep as layoutClassName/className: width: 100% [.form-group select]
- before -> after vs SelectControl bare md (7/13 equal):
  - padding-top: var(--space-2) -> var(--space-2)  (same)
  - padding-right: var(--space-3) -> var(--space-5)
  - padding-bottom: var(--space-2) -> var(--space-2)  (same)
  - padding-left: var(--space-3) -> var(--space-3)  (same)
  - border: 1px solid var(--border) -> 1px solid var(--border)  (same)
  - border-radius: var(--radius-sm) -> var(--comp-input-radius)
  - font-size: var(--font-base) -> var(--font-base)  (same)
  - color: var(--text-primary) -> var(--text-primary)  (same)
  - background-color: var(--bg-surface) -> var(--bg-surface)  (same)
  - background-image: none -> arrow-svg(url data:image/svg+xml chevron #888)
  - height: (unset: browser default) -> (none)
  - min-height: (unset: browser default) -> (none)
  - line-height: (unset: browser default) -> var(--line-height-base)

### 35. pages/schedule/SchedulePageImpl.tsx:288  (SchedulePopover)
- opening tag: `<select className="schedule-input" value={draft.category} onChange={(event) => onDraftChange({ ...draft, category: event.target.value as CalendarId })} >`
- className expr: `"schedule-input"` | inline style: (none)
- children kind: map (["map"]), disabledOption=false, onChange=`{(event) => onDraftChange({ ...draft, category: event.target.value as CalendarId })}`, reads=["target.value"], numericConverted=false
- applied CSS rules:
  - `.schedule-input` @ frontend/src/pages/schedule.css:813 (0,1,0) state=base [definite]
    - LAYOUT: width: 100% (L815)
    - DECORATION: border: 1px solid var(--border) (L816); border-radius: var(--radius-md) (L817); background: var(--bg-surface) (L818); color: var(--text-primary) (L819); font-size: var(--font-sm) (L820)
  - `.schedule-input` @ frontend/src/pages/schedule.css:823 (0,1,0) state=base [definite]
    - DIMENSION owned by mold: min-height: var(--comp-input-height-sm) (L824)
    - DECORATION: padding: 0 var(--space-3) (L825)
  - `.schedule-input:focus` @ frontend/src/pages/schedule.css:833 (0,2,0) state=self:focus [definite]
    - DECORATION: outline: none (L835); border-color: var(--accent) (L836); box-shadow: var(--focus-ring-shadow) (L837)
- nearest mold size: **sm** (font-size token; font-size=var(--font-sm)); padding T/R/B/L = 0 / var(--space-3) / 0 / var(--space-3); width=100% @frontend/src/pages/schedule.css:815 -> fullWidth=true
- layout-only residue to keep as layoutClassName/className: width: 100% [.schedule-input]
- before -> after vs SelectControl bare sm (5/13 equal):
  - padding-top: 0 -> var(--space-1)
  - padding-right: var(--space-3) -> var(--space-5)
  - padding-bottom: 0 -> var(--space-1)
  - padding-left: var(--space-3) -> var(--space-2)
  - border: 1px solid var(--border) -> 1px solid var(--border)  (same)
  - border-radius: var(--radius-md) -> var(--comp-input-radius)
  - font-size: var(--font-sm) -> var(--font-sm)  (same)
  - color: var(--text-primary) -> var(--text-primary)  (same)
  - background-color: var(--bg-surface) -> var(--bg-surface)  (same)
  - background-image: none -> arrow-svg(url data:image/svg+xml chevron #888)
  - height: (unset: browser default) -> (none)
  - min-height: var(--comp-input-height-sm) -> var(--comp-input-height-sm)  (same)
  - line-height: (unset: browser default) -> var(--line-height-base)

### 36. pages/schedule/ScheduleSettingsPage.tsx:170  (ScheduleSettingsPage)
- opening tag: `<select className="schedule-input" value={selfOwner.shareMode} onChange={(event) => updateOwner(selfOwner.staffId, { shareMode: event.target.value as CalendarOwner["shareMode"] })} >`
- className expr: `"schedule-input"` | inline style: (none)
- children kind: static-option (["option","option","option"]), disabledOption=false, onChange=`{(event) => updateOwner(selfOwner.staffId, { shareMode: event.target.value as CalendarOwner["shareMode"] })}`, reads=["target.value"], numericConverted=false
- applied CSS rules:
  - `.schedule-input` @ frontend/src/pages/schedule.css:813 (0,1,0) state=base [definite]
    - LAYOUT: width: 100% (L815)
    - DECORATION: border: 1px solid var(--border) (L816); border-radius: var(--radius-md) (L817); background: var(--bg-surface) (L818); color: var(--text-primary) (L819); font-size: var(--font-sm) (L820)
  - `.schedule-input` @ frontend/src/pages/schedule.css:823 (0,1,0) state=base [definite]
    - DIMENSION owned by mold: min-height: var(--comp-input-height-sm) (L824)
    - DECORATION: padding: 0 var(--space-3) (L825)
  - `.schedule-input:focus` @ frontend/src/pages/schedule.css:833 (0,2,0) state=self:focus [definite]
    - DECORATION: outline: none (L835); border-color: var(--accent) (L836); box-shadow: var(--focus-ring-shadow) (L837)
- nearest mold size: **sm** (font-size token; font-size=var(--font-sm)); padding T/R/B/L = 0 / var(--space-3) / 0 / var(--space-3); width=100% @frontend/src/pages/schedule.css:815 -> fullWidth=true
- layout-only residue to keep as layoutClassName/className: width: 100% [.schedule-input]
- before -> after vs SelectControl bare sm (5/13 equal):
  - padding-top: 0 -> var(--space-1)
  - padding-right: var(--space-3) -> var(--space-5)
  - padding-bottom: 0 -> var(--space-1)
  - padding-left: var(--space-3) -> var(--space-2)
  - border: 1px solid var(--border) -> 1px solid var(--border)  (same)
  - border-radius: var(--radius-md) -> var(--comp-input-radius)
  - font-size: var(--font-sm) -> var(--font-sm)  (same)
  - color: var(--text-primary) -> var(--text-primary)  (same)
  - background-color: var(--bg-surface) -> var(--bg-surface)  (same)
  - background-image: none -> arrow-svg(url data:image/svg+xml chevron #888)
  - height: (unset: browser default) -> (none)
  - min-height: var(--comp-input-height-sm) -> var(--comp-input-height-sm)  (same)
  - line-height: (unset: browser default) -> var(--line-height-base)

### 37. pages/schedule/ScheduleSettingsPage.tsx:225  (ScheduleSettingsPage)
- opening tag: `<select className="schedule-input" value={owner.shareMode} onChange={(event) => updateOwner(owner.staffId, { shareMode: event.target.value as CalendarOwner["shareMode"] })} >`
- className expr: `"schedule-input"` | inline style: (none)
- children kind: static-option (["option","option","option"]), disabledOption=false, onChange=`{(event) => updateOwner(owner.staffId, { shareMode: event.target.value as CalendarOwner["shareMode"] })}`, reads=["target.value"], numericConverted=false
- applied CSS rules:
  - `.schedule-input` @ frontend/src/pages/schedule.css:813 (0,1,0) state=base [definite]
    - LAYOUT: width: 100% (L815)
    - DECORATION: border: 1px solid var(--border) (L816); border-radius: var(--radius-md) (L817); background: var(--bg-surface) (L818); color: var(--text-primary) (L819); font-size: var(--font-sm) (L820)
  - `.schedule-input` @ frontend/src/pages/schedule.css:823 (0,1,0) state=base [definite]
    - DIMENSION owned by mold: min-height: var(--comp-input-height-sm) (L824)
    - DECORATION: padding: 0 var(--space-3) (L825)
  - `.schedule-input:focus` @ frontend/src/pages/schedule.css:833 (0,2,0) state=self:focus [definite]
    - DECORATION: outline: none (L835); border-color: var(--accent) (L836); box-shadow: var(--focus-ring-shadow) (L837)
- nearest mold size: **sm** (font-size token; font-size=var(--font-sm)); padding T/R/B/L = 0 / var(--space-3) / 0 / var(--space-3); width=100% @frontend/src/pages/schedule.css:815 -> fullWidth=true
- layout-only residue to keep as layoutClassName/className: width: 100% [.schedule-input]
- before -> after vs SelectControl bare sm (5/13 equal):
  - padding-top: 0 -> var(--space-1)
  - padding-right: var(--space-3) -> var(--space-5)
  - padding-bottom: 0 -> var(--space-1)
  - padding-left: var(--space-3) -> var(--space-2)
  - border: 1px solid var(--border) -> 1px solid var(--border)  (same)
  - border-radius: var(--radius-md) -> var(--comp-input-radius)
  - font-size: var(--font-sm) -> var(--font-sm)  (same)
  - color: var(--text-primary) -> var(--text-primary)  (same)
  - background-color: var(--bg-surface) -> var(--bg-surface)  (same)
  - background-image: none -> arrow-svg(url data:image/svg+xml chevron #888)
  - height: (unset: browser default) -> (none)
  - min-height: var(--comp-input-height-sm) -> var(--comp-input-height-sm)  (same)
  - line-height: (unset: browser default) -> var(--line-height-base)

### 38. pages/status-master/StatusMasterPage.tsx:260  (renderFormFields)
- opening tag: `<select className="field field-h-md" value={form.match_type} onChange={e => setForm({ ...form, match_type: e.target.value })} required >`
- className expr: `"field field-h-md"` | inline style: (none)
- children kind: map (["map"]), disabledOption=false, onChange=`{e => setForm({ ...form, match_type: e.target.value })}`, reads=["target.value"], numericConverted=false
- ui-allow (verbatim): `{/* ui-allow: enum select for status match_type; no SelectControl variant with option map (#3594) */}` (L259, preceding)
- applied CSS rules:
  - `.field-h-md` @ frontend/src/components/field-size.css:8 (0,1,0) state=base [definite]
    - DIMENSION owned by mold: min-height: var(--field-h-md, 36px) (L8)
    - DECORATION: box-sizing: border-box (L8)
  - `.form-group select` @ frontend/src/components.css:19 (0,1,1) state=base [definite]
    - LAYOUT: width: 100% (L22)
    - DECORATION: padding: var(--space-2) var(--space-3) (L23); border: 1px solid var(--border) (L24); border-radius: var(--radius-sm) (L25); font-size: var(--font-base) (L26); color: var(--text-primary) (L27); background: var(--bg-surface) (L28); box-sizing: border-box (L29)
  - `.form-group select:focus` @ frontend/src/components.css:32 (0,2,1) state=self:focus [definite]
    - DECORATION: outline: none (L35); border-color: var(--accent) (L36); box-shadow: var(--focus-ring-shadow) (L37)
- nearest mold size: **md** (font-size token; font-size=var(--font-base)); padding T/R/B/L = var(--space-2) / var(--space-3) / var(--space-2) / var(--space-3); width=100% @frontend/src/components.css:22 -> fullWidth=true
- layout-only residue to keep as layoutClassName/className: width: 100% [.form-group select]
- before -> after vs SelectControl bare md (7/13 equal):
  - padding-top: var(--space-2) -> var(--space-2)  (same)
  - padding-right: var(--space-3) -> var(--space-5)
  - padding-bottom: var(--space-2) -> var(--space-2)  (same)
  - padding-left: var(--space-3) -> var(--space-3)  (same)
  - border: 1px solid var(--border) -> 1px solid var(--border)  (same)
  - border-radius: var(--radius-sm) -> var(--comp-input-radius)
  - font-size: var(--font-base) -> var(--font-base)  (same)
  - color: var(--text-primary) -> var(--text-primary)  (same)
  - background-color: var(--bg-surface) -> var(--bg-surface)  (same)
  - background-image: none -> arrow-svg(url data:image/svg+xml chevron #888)
  - height: (unset: browser default) -> (none)
  - min-height: var(--field-h-md, 36px) -> (none)
  - line-height: (unset: browser default) -> var(--line-height-base)

### 39. pages/status-master/StatusMasterPage.tsx:274  (renderFormFields)
- opening tag: `<select className="field field-h-md" value={form.effect} onChange={e => setForm({ ...form, effect: e.target.value })} required >`
- className expr: `"field field-h-md"` | inline style: (none)
- children kind: map (["map"]), disabledOption=false, onChange=`{e => setForm({ ...form, effect: e.target.value })}`, reads=["target.value"], numericConverted=false
- ui-allow (verbatim): `{/* ui-allow: enum select for status effect; no SelectControl variant with option map (#3594) */}` (L273, preceding)
- applied CSS rules:
  - `.field-h-md` @ frontend/src/components/field-size.css:8 (0,1,0) state=base [definite]
    - DIMENSION owned by mold: min-height: var(--field-h-md, 36px) (L8)
    - DECORATION: box-sizing: border-box (L8)
  - `.form-group select` @ frontend/src/components.css:19 (0,1,1) state=base [definite]
    - LAYOUT: width: 100% (L22)
    - DECORATION: padding: var(--space-2) var(--space-3) (L23); border: 1px solid var(--border) (L24); border-radius: var(--radius-sm) (L25); font-size: var(--font-base) (L26); color: var(--text-primary) (L27); background: var(--bg-surface) (L28); box-sizing: border-box (L29)
  - `.form-group select:focus` @ frontend/src/components.css:32 (0,2,1) state=self:focus [definite]
    - DECORATION: outline: none (L35); border-color: var(--accent) (L36); box-shadow: var(--focus-ring-shadow) (L37)
- nearest mold size: **md** (font-size token; font-size=var(--font-base)); padding T/R/B/L = var(--space-2) / var(--space-3) / var(--space-2) / var(--space-3); width=100% @frontend/src/components.css:22 -> fullWidth=true
- layout-only residue to keep as layoutClassName/className: width: 100% [.form-group select]
- before -> after vs SelectControl bare md (7/13 equal):
  - padding-top: var(--space-2) -> var(--space-2)  (same)
  - padding-right: var(--space-3) -> var(--space-5)
  - padding-bottom: var(--space-2) -> var(--space-2)  (same)
  - padding-left: var(--space-3) -> var(--space-3)  (same)
  - border: 1px solid var(--border) -> 1px solid var(--border)  (same)
  - border-radius: var(--radius-sm) -> var(--comp-input-radius)
  - font-size: var(--font-base) -> var(--font-base)  (same)
  - color: var(--text-primary) -> var(--text-primary)  (same)
  - background-color: var(--bg-surface) -> var(--bg-surface)  (same)
  - background-image: none -> arrow-svg(url data:image/svg+xml chevron #888)
  - height: (unset: browser default) -> (none)
  - min-height: var(--field-h-md, 36px) -> (none)
  - line-height: (unset: browser default) -> var(--line-height-base)

### 40. pages/super-admin/components/ConditionsMasterPanel.tsx:322  (ConditionsMasterPanel)
- opening tag: `<select className="field field-h-md" value={form.condition_def_id} onChange={e => setForm({ ...form, condition_def_id: e.target.value })} >`
- className expr: `"field field-h-md"` | inline style: (none)
- children kind: map (["option","map"]), disabledOption=false, onChange=`{e => setForm({ ...form, condition_def_id: e.target.value })}`, reads=["target.value"], numericConverted=false
- ui-allow (verbatim): `{/* ui-allow: reference pulldown for condition_def_id; no SelectControl variant with dynamic option list (#3594) */}` (L321, preceding)
- applied CSS rules:
  - `.field-h-md` @ frontend/src/components/field-size.css:8 (0,1,0) state=base [definite]
    - DIMENSION owned by mold: min-height: var(--field-h-md, 36px) (L8)
    - DECORATION: box-sizing: border-box (L8)
  - `.form-group select` @ frontend/src/components.css:19 (0,1,1) state=base [definite]
    - LAYOUT: width: 100% (L22)
    - DECORATION: padding: var(--space-2) var(--space-3) (L23); border: 1px solid var(--border) (L24); border-radius: var(--radius-sm) (L25); font-size: var(--font-base) (L26); color: var(--text-primary) (L27); background: var(--bg-surface) (L28); box-sizing: border-box (L29)
  - `.form-group select:focus` @ frontend/src/components.css:32 (0,2,1) state=self:focus [definite]
    - DECORATION: outline: none (L35); border-color: var(--accent) (L36); box-shadow: var(--focus-ring-shadow) (L37)
- nearest mold size: **md** (font-size token; font-size=var(--font-base)); padding T/R/B/L = var(--space-2) / var(--space-3) / var(--space-2) / var(--space-3); width=100% @frontend/src/components.css:22 -> fullWidth=true
- layout-only residue to keep as layoutClassName/className: width: 100% [.form-group select]
- before -> after vs SelectControl bare md (7/13 equal):
  - padding-top: var(--space-2) -> var(--space-2)  (same)
  - padding-right: var(--space-3) -> var(--space-5)
  - padding-bottom: var(--space-2) -> var(--space-2)  (same)
  - padding-left: var(--space-3) -> var(--space-3)  (same)
  - border: 1px solid var(--border) -> 1px solid var(--border)  (same)
  - border-radius: var(--radius-sm) -> var(--comp-input-radius)
  - font-size: var(--font-base) -> var(--font-base)  (same)
  - color: var(--text-primary) -> var(--text-primary)  (same)
  - background-color: var(--bg-surface) -> var(--bg-surface)  (same)
  - background-image: none -> arrow-svg(url data:image/svg+xml chevron #888)
  - height: (unset: browser default) -> (none)
  - min-height: var(--field-h-md, 36px) -> (none)
  - line-height: (unset: browser default) -> var(--line-height-base)

### 41. pages/super-admin/components/ConditionsMasterPanel.tsx:338  (ConditionsMasterPanel)
- opening tag: `<select className="field field-h-md" value={form.unit_id} onChange={e => setForm({ ...form, unit_id: e.target.value })} >`
- className expr: `"field field-h-md"` | inline style: (none)
- children kind: map (["option","map"]), disabledOption=false, onChange=`{e => setForm({ ...form, unit_id: e.target.value })}`, reads=["target.value"], numericConverted=false
- ui-allow (verbatim): `{/* ui-allow: reference pulldown for unit_id; no SelectControl variant with dynamic option list (#3594) */}` (L337, preceding)
- applied CSS rules:
  - `.field-h-md` @ frontend/src/components/field-size.css:8 (0,1,0) state=base [definite]
    - DIMENSION owned by mold: min-height: var(--field-h-md, 36px) (L8)
    - DECORATION: box-sizing: border-box (L8)
  - `.form-group select` @ frontend/src/components.css:19 (0,1,1) state=base [definite]
    - LAYOUT: width: 100% (L22)
    - DECORATION: padding: var(--space-2) var(--space-3) (L23); border: 1px solid var(--border) (L24); border-radius: var(--radius-sm) (L25); font-size: var(--font-base) (L26); color: var(--text-primary) (L27); background: var(--bg-surface) (L28); box-sizing: border-box (L29)
  - `.form-group select:focus` @ frontend/src/components.css:32 (0,2,1) state=self:focus [definite]
    - DECORATION: outline: none (L35); border-color: var(--accent) (L36); box-shadow: var(--focus-ring-shadow) (L37)
- nearest mold size: **md** (font-size token; font-size=var(--font-base)); padding T/R/B/L = var(--space-2) / var(--space-3) / var(--space-2) / var(--space-3); width=100% @frontend/src/components.css:22 -> fullWidth=true
- layout-only residue to keep as layoutClassName/className: width: 100% [.form-group select]
- before -> after vs SelectControl bare md (7/13 equal):
  - padding-top: var(--space-2) -> var(--space-2)  (same)
  - padding-right: var(--space-3) -> var(--space-5)
  - padding-bottom: var(--space-2) -> var(--space-2)  (same)
  - padding-left: var(--space-3) -> var(--space-3)  (same)
  - border: 1px solid var(--border) -> 1px solid var(--border)  (same)
  - border-radius: var(--radius-sm) -> var(--comp-input-radius)
  - font-size: var(--font-base) -> var(--font-base)  (same)
  - color: var(--text-primary) -> var(--text-primary)  (same)
  - background-color: var(--bg-surface) -> var(--bg-surface)  (same)
  - background-image: none -> arrow-svg(url data:image/svg+xml chevron #888)
  - height: (unset: browser default) -> (none)
  - min-height: var(--field-h-md, 36px) -> (none)
  - line-height: (unset: browser default) -> var(--line-height-base)

### 42. pages/super-admin/components/ConditionsMasterPanel.tsx:393  (ConditionsMasterPanel)
- opening tag: `<select className="field field-h-md" value={form.match_type} onChange={e => setForm({ ...form, match_type: e.target.value })} required >`
- className expr: `"field field-h-md"` | inline style: (none)
- children kind: map (["map"]), disabledOption=false, onChange=`{e => setForm({ ...form, match_type: e.target.value })}`, reads=["target.value"], numericConverted=false
- ui-allow (verbatim): `{/* ui-allow: enum select for condition match_type; no SelectControl variant with option map (#3594) */}` (L392, preceding)
- applied CSS rules:
  - `.field-h-md` @ frontend/src/components/field-size.css:8 (0,1,0) state=base [definite]
    - DIMENSION owned by mold: min-height: var(--field-h-md, 36px) (L8)
    - DECORATION: box-sizing: border-box (L8)
  - `.form-group select` @ frontend/src/components.css:19 (0,1,1) state=base [definite]
    - LAYOUT: width: 100% (L22)
    - DECORATION: padding: var(--space-2) var(--space-3) (L23); border: 1px solid var(--border) (L24); border-radius: var(--radius-sm) (L25); font-size: var(--font-base) (L26); color: var(--text-primary) (L27); background: var(--bg-surface) (L28); box-sizing: border-box (L29)
  - `.form-group select:focus` @ frontend/src/components.css:32 (0,2,1) state=self:focus [definite]
    - DECORATION: outline: none (L35); border-color: var(--accent) (L36); box-shadow: var(--focus-ring-shadow) (L37)
- nearest mold size: **md** (font-size token; font-size=var(--font-base)); padding T/R/B/L = var(--space-2) / var(--space-3) / var(--space-2) / var(--space-3); width=100% @frontend/src/components.css:22 -> fullWidth=true
- layout-only residue to keep as layoutClassName/className: width: 100% [.form-group select]
- before -> after vs SelectControl bare md (7/13 equal):
  - padding-top: var(--space-2) -> var(--space-2)  (same)
  - padding-right: var(--space-3) -> var(--space-5)
  - padding-bottom: var(--space-2) -> var(--space-2)  (same)
  - padding-left: var(--space-3) -> var(--space-3)  (same)
  - border: 1px solid var(--border) -> 1px solid var(--border)  (same)
  - border-radius: var(--radius-sm) -> var(--comp-input-radius)
  - font-size: var(--font-base) -> var(--font-base)  (same)
  - color: var(--text-primary) -> var(--text-primary)  (same)
  - background-color: var(--bg-surface) -> var(--bg-surface)  (same)
  - background-image: none -> arrow-svg(url data:image/svg+xml chevron #888)
  - height: (unset: browser default) -> (none)
  - min-height: var(--field-h-md, 36px) -> (none)
  - line-height: (unset: browser default) -> var(--line-height-base)

### 43. pages/super-admin/components/ConditionsMasterPanel.tsx:409  (ConditionsMasterPanel)
- opening tag: `<select className="field field-h-md" value={form.effect} onChange={e => setForm({ ...form, effect: e.target.value })} required >`
- className expr: `"field field-h-md"` | inline style: (none)
- children kind: map (["map"]), disabledOption=false, onChange=`{e => setForm({ ...form, effect: e.target.value })}`, reads=["target.value"], numericConverted=false
- ui-allow (verbatim): `{/* ui-allow: enum select for condition effect; no SelectControl variant with option map (#3594) */}` (L408, preceding)
- applied CSS rules:
  - `.field-h-md` @ frontend/src/components/field-size.css:8 (0,1,0) state=base [definite]
    - DIMENSION owned by mold: min-height: var(--field-h-md, 36px) (L8)
    - DECORATION: box-sizing: border-box (L8)
  - `.form-group select` @ frontend/src/components.css:19 (0,1,1) state=base [definite]
    - LAYOUT: width: 100% (L22)
    - DECORATION: padding: var(--space-2) var(--space-3) (L23); border: 1px solid var(--border) (L24); border-radius: var(--radius-sm) (L25); font-size: var(--font-base) (L26); color: var(--text-primary) (L27); background: var(--bg-surface) (L28); box-sizing: border-box (L29)
  - `.form-group select:focus` @ frontend/src/components.css:32 (0,2,1) state=self:focus [definite]
    - DECORATION: outline: none (L35); border-color: var(--accent) (L36); box-shadow: var(--focus-ring-shadow) (L37)
- nearest mold size: **md** (font-size token; font-size=var(--font-base)); padding T/R/B/L = var(--space-2) / var(--space-3) / var(--space-2) / var(--space-3); width=100% @frontend/src/components.css:22 -> fullWidth=true
- layout-only residue to keep as layoutClassName/className: width: 100% [.form-group select]
- before -> after vs SelectControl bare md (7/13 equal):
  - padding-top: var(--space-2) -> var(--space-2)  (same)
  - padding-right: var(--space-3) -> var(--space-5)
  - padding-bottom: var(--space-2) -> var(--space-2)  (same)
  - padding-left: var(--space-3) -> var(--space-3)  (same)
  - border: 1px solid var(--border) -> 1px solid var(--border)  (same)
  - border-radius: var(--radius-sm) -> var(--comp-input-radius)
  - font-size: var(--font-base) -> var(--font-base)  (same)
  - color: var(--text-primary) -> var(--text-primary)  (same)
  - background-color: var(--bg-surface) -> var(--bg-surface)  (same)
  - background-image: none -> arrow-svg(url data:image/svg+xml chevron #888)
  - height: (unset: browser default) -> (none)
  - min-height: var(--field-h-md, 36px) -> (none)
  - line-height: (unset: browser default) -> var(--line-height-base)

### 44. pages/super-admin/components/StatusMasterPanel.tsx:311  (StatusMasterPanel)
- opening tag: `<select className="field field-h-md" value={form.match_type} onChange={e => setForm({ ...form, match_type: e.target.value })} required >`
- className expr: `"field field-h-md"` | inline style: (none)
- children kind: map (["map"]), disabledOption=false, onChange=`{e => setForm({ ...form, match_type: e.target.value })}`, reads=["target.value"], numericConverted=false
- ui-allow (verbatim): `{/* ui-allow: enum select for status match_type; no SelectControl variant with option map (#3594) */}` (L310, preceding)
- resolution note: StatusMasterPanel has no import/JSX site anywhere in frontend/src (grep StatusMasterPanel: self + a comment in RuleManagementPanel.tsx:5 only). Unconfirmed rules are unreachable; effective = definite rules.
- applied CSS rules:
  - `.field-h-md` @ frontend/src/components/field-size.css:8 (0,1,0) state=base [definite]
    - DIMENSION owned by mold: min-height: var(--field-h-md, 36px) (L8)
    - DECORATION: box-sizing: border-box (L8)
  - `.form-group select` @ frontend/src/components.css:19 (0,1,1) state=base [definite]
    - LAYOUT: width: 100% (L22)
    - DECORATION: padding: var(--space-2) var(--space-3) (L23); border: 1px solid var(--border) (L24); border-radius: var(--radius-sm) (L25); font-size: var(--font-base) (L26); color: var(--text-primary) (L27); background: var(--bg-surface) (L28); box-sizing: border-box (L29)
  - `.form-group select:focus` @ frontend/src/components.css:32 (0,2,1) state=self:focus [definite]
    - DECORATION: outline: none (L35); border-color: var(--accent) (L36); box-shadow: var(--focus-ring-shadow) (L37)
- unconfirmed rules (not counted): .product-edit-form .form-group select@frontend/src/company-forms.css:260; .filter-bar select@frontend/src/components.css:60
- nearest mold size: **md** (font-size token; font-size=var(--font-base)); padding T/R/B/L = var(--space-2) / var(--space-3) / var(--space-2) / var(--space-3); width=100% @frontend/src/components.css:22 -> fullWidth=true
- layout-only residue to keep as layoutClassName/className: width: 100% [.form-group select]
- before -> after vs SelectControl bare md (7/13 equal):
  - padding-top: var(--space-2) -> var(--space-2)  (same)
  - padding-right: var(--space-3) -> var(--space-5)
  - padding-bottom: var(--space-2) -> var(--space-2)  (same)
  - padding-left: var(--space-3) -> var(--space-3)  (same)
  - border: 1px solid var(--border) -> 1px solid var(--border)  (same)
  - border-radius: var(--radius-sm) -> var(--comp-input-radius)
  - font-size: var(--font-base) -> var(--font-base)  (same)
  - color: var(--text-primary) -> var(--text-primary)  (same)
  - background-color: var(--bg-surface) -> var(--bg-surface)  (same)
  - background-image: none -> arrow-svg(url data:image/svg+xml chevron #888)
  - height: (unset: browser default) -> (none)
  - min-height: var(--field-h-md, 36px) -> (none)
  - line-height: (unset: browser default) -> var(--line-height-base)

### 45. pages/super-admin/components/StatusMasterPanel.tsx:325  (StatusMasterPanel)
- opening tag: `<select className="field field-h-md" value={form.effect} onChange={e => setForm({ ...form, effect: e.target.value })} required >`
- className expr: `"field field-h-md"` | inline style: (none)
- children kind: map (["map"]), disabledOption=false, onChange=`{e => setForm({ ...form, effect: e.target.value })}`, reads=["target.value"], numericConverted=false
- ui-allow (verbatim): `{/* ui-allow: enum select for status effect; no SelectControl variant with option map (#3594) */}` (L324, preceding)
- resolution note: same as StatusMasterPanel.tsx:311
- applied CSS rules:
  - `.field-h-md` @ frontend/src/components/field-size.css:8 (0,1,0) state=base [definite]
    - DIMENSION owned by mold: min-height: var(--field-h-md, 36px) (L8)
    - DECORATION: box-sizing: border-box (L8)
  - `.form-group select` @ frontend/src/components.css:19 (0,1,1) state=base [definite]
    - LAYOUT: width: 100% (L22)
    - DECORATION: padding: var(--space-2) var(--space-3) (L23); border: 1px solid var(--border) (L24); border-radius: var(--radius-sm) (L25); font-size: var(--font-base) (L26); color: var(--text-primary) (L27); background: var(--bg-surface) (L28); box-sizing: border-box (L29)
  - `.form-group select:focus` @ frontend/src/components.css:32 (0,2,1) state=self:focus [definite]
    - DECORATION: outline: none (L35); border-color: var(--accent) (L36); box-shadow: var(--focus-ring-shadow) (L37)
- unconfirmed rules (not counted): .product-edit-form .form-group select@frontend/src/company-forms.css:260; .filter-bar select@frontend/src/components.css:60
- nearest mold size: **md** (font-size token; font-size=var(--font-base)); padding T/R/B/L = var(--space-2) / var(--space-3) / var(--space-2) / var(--space-3); width=100% @frontend/src/components.css:22 -> fullWidth=true
- layout-only residue to keep as layoutClassName/className: width: 100% [.form-group select]
- before -> after vs SelectControl bare md (7/13 equal):
  - padding-top: var(--space-2) -> var(--space-2)  (same)
  - padding-right: var(--space-3) -> var(--space-5)
  - padding-bottom: var(--space-2) -> var(--space-2)  (same)
  - padding-left: var(--space-3) -> var(--space-3)  (same)
  - border: 1px solid var(--border) -> 1px solid var(--border)  (same)
  - border-radius: var(--radius-sm) -> var(--comp-input-radius)
  - font-size: var(--font-base) -> var(--font-base)  (same)
  - color: var(--text-primary) -> var(--text-primary)  (same)
  - background-color: var(--bg-surface) -> var(--bg-surface)  (same)
  - background-image: none -> arrow-svg(url data:image/svg+xml chevron #888)
  - height: (unset: browser default) -> (none)
  - min-height: var(--field-h-md, 36px) -> (none)
  - line-height: (unset: browser default) -> var(--line-height-base)

### 46. pages/super-admin/DexTab.tsx:194  (DexTab)
- opening tag: `<select value={kind} onChange={(e) => setKind(e.target.value as DexKind)}>`
- className expr: (none) | inline style: (none)
- children kind: static-option (["option","option"]), disabledOption=false, onChange=`{(e) => setKind(e.target.value as DexKind)}`, reads=["target.value"], numericConverted=false
- resolution note: DexTab has no non-test importer in frontend/src (only AdminMasterSaveButtonMigration.test.tsx:7, PurchaseAdminEditorButtonMigration.test.tsx:9). In-file chain (label > div > div.super-admin-dex-tab) has no .form-group/.filter-bar; the unconfirmed rules need an unknown outer ancestor. Effective = no rule (unstyled -> md).
- applied CSS rules:
  - (none) -> unstyled
- unconfirmed rules (not counted): .form-group select@frontend/src/components.css:19; .form-group select:focus@frontend/src/components.css:32; .filter-bar select@frontend/src/components.css:60
- nearest mold size: **md** (font-size token; font-size=unset); padding T/R/B/L = 0 / 0 / 0 / 0; width=unset -> fullWidth=false
- layout-only residue to keep as layoutClassName/className: (none)
- before -> after vs SelectControl bare md (0/13 equal):
  - padding-top: 0 -> var(--space-2)
  - padding-right: 0 -> var(--space-5)
  - padding-bottom: 0 -> var(--space-2)
  - padding-left: 0 -> var(--space-3)
  - border: (unset: browser default) -> 1px solid var(--border)
  - border-radius: (unset: browser default) -> var(--comp-input-radius)
  - font-size: (unset: browser default) -> var(--font-base)
  - color: (unset: browser default) -> var(--text-primary)
  - background-color: (unset: browser default) -> var(--bg-surface)
  - background-image: (unset: browser default) -> arrow-svg(url data:image/svg+xml chevron #888)
  - height: (unset: browser default) -> (none)
  - min-height: (unset: browser default) -> (none)
  - line-height: (unset: browser default) -> var(--line-height-base)

### 47. pages/super-admin/KnowledgeAliasesTab.tsx:447  (KnowledgeAliasesTab)
- opening tag: `<select required value={ruleForm.category} onChange={(e) => setRuleForm({ ...ruleForm, category: e.target.value })}>`
- className expr: (none) | inline style: (none)
- children kind: map (["map"]), disabledOption=false, onChange=`{(e) => setRuleForm({ ...ruleForm, category: e.target.value })}`, reads=["target.value"], numericConverted=false
- applied CSS rules:
  - `.form-group select` @ frontend/src/components.css:19 (0,1,1) state=base [definite]
    - LAYOUT: width: 100% (L22)
    - DECORATION: padding: var(--space-2) var(--space-3) (L23); border: 1px solid var(--border) (L24); border-radius: var(--radius-sm) (L25); font-size: var(--font-base) (L26); color: var(--text-primary) (L27); background: var(--bg-surface) (L28); box-sizing: border-box (L29)
  - `.form-group select:focus` @ frontend/src/components.css:32 (0,2,1) state=self:focus [definite]
    - DECORATION: outline: none (L35); border-color: var(--accent) (L36); box-shadow: var(--focus-ring-shadow) (L37)
- nearest mold size: **md** (font-size token; font-size=var(--font-base)); padding T/R/B/L = var(--space-2) / var(--space-3) / var(--space-2) / var(--space-3); width=100% @frontend/src/components.css:22 -> fullWidth=true
- layout-only residue to keep as layoutClassName/className: width: 100% [.form-group select]
- before -> after vs SelectControl bare md (7/13 equal):
  - padding-top: var(--space-2) -> var(--space-2)  (same)
  - padding-right: var(--space-3) -> var(--space-5)
  - padding-bottom: var(--space-2) -> var(--space-2)  (same)
  - padding-left: var(--space-3) -> var(--space-3)  (same)
  - border: 1px solid var(--border) -> 1px solid var(--border)  (same)
  - border-radius: var(--radius-sm) -> var(--comp-input-radius)
  - font-size: var(--font-base) -> var(--font-base)  (same)
  - color: var(--text-primary) -> var(--text-primary)  (same)
  - background-color: var(--bg-surface) -> var(--bg-surface)  (same)
  - background-image: none -> arrow-svg(url data:image/svg+xml chevron #888)
  - height: (unset: browser default) -> (none)
  - min-height: (unset: browser default) -> (none)
  - line-height: (unset: browser default) -> var(--line-height-base)

### 48. pages/super-admin/KnowledgeAliasesTab.tsx:455  (KnowledgeAliasesTab)
- opening tag: `<select value={ruleForm.pattern_type} onChange={(e) => setRuleForm({ ...ruleForm, pattern_type: e.target.value })}>`
- className expr: (none) | inline style: (none)
- children kind: map (["map"]), disabledOption=false, onChange=`{(e) => setRuleForm({ ...ruleForm, pattern_type: e.target.value })}`, reads=["target.value"], numericConverted=false
- applied CSS rules:
  - `.form-group select` @ frontend/src/components.css:19 (0,1,1) state=base [definite]
    - LAYOUT: width: 100% (L22)
    - DECORATION: padding: var(--space-2) var(--space-3) (L23); border: 1px solid var(--border) (L24); border-radius: var(--radius-sm) (L25); font-size: var(--font-base) (L26); color: var(--text-primary) (L27); background: var(--bg-surface) (L28); box-sizing: border-box (L29)
  - `.form-group select:focus` @ frontend/src/components.css:32 (0,2,1) state=self:focus [definite]
    - DECORATION: outline: none (L35); border-color: var(--accent) (L36); box-shadow: var(--focus-ring-shadow) (L37)
- nearest mold size: **md** (font-size token; font-size=var(--font-base)); padding T/R/B/L = var(--space-2) / var(--space-3) / var(--space-2) / var(--space-3); width=100% @frontend/src/components.css:22 -> fullWidth=true
- layout-only residue to keep as layoutClassName/className: width: 100% [.form-group select]
- before -> after vs SelectControl bare md (7/13 equal):
  - padding-top: var(--space-2) -> var(--space-2)  (same)
  - padding-right: var(--space-3) -> var(--space-5)
  - padding-bottom: var(--space-2) -> var(--space-2)  (same)
  - padding-left: var(--space-3) -> var(--space-3)  (same)
  - border: 1px solid var(--border) -> 1px solid var(--border)  (same)
  - border-radius: var(--radius-sm) -> var(--comp-input-radius)
  - font-size: var(--font-base) -> var(--font-base)  (same)
  - color: var(--text-primary) -> var(--text-primary)  (same)
  - background-color: var(--bg-surface) -> var(--bg-surface)  (same)
  - background-image: none -> arrow-svg(url data:image/svg+xml chevron #888)
  - height: (unset: browser default) -> (none)
  - min-height: (unset: browser default) -> (none)
  - line-height: (unset: browser default) -> var(--line-height-base)

### 49. pages/super-admin/KnowledgeAliasesTab.tsx:472  (KnowledgeAliasesTab)
- opening tag: `<select value={ruleForm.language} onChange={(e) => setRuleForm({ ...ruleForm, language: e.target.value })}>`
- className expr: (none) | inline style: (none)
- children kind: map (["map"]), disabledOption=false, onChange=`{(e) => setRuleForm({ ...ruleForm, language: e.target.value })}`, reads=["target.value"], numericConverted=false
- applied CSS rules:
  - `.form-group select` @ frontend/src/components.css:19 (0,1,1) state=base [definite]
    - LAYOUT: width: 100% (L22)
    - DECORATION: padding: var(--space-2) var(--space-3) (L23); border: 1px solid var(--border) (L24); border-radius: var(--radius-sm) (L25); font-size: var(--font-base) (L26); color: var(--text-primary) (L27); background: var(--bg-surface) (L28); box-sizing: border-box (L29)
  - `.form-group select:focus` @ frontend/src/components.css:32 (0,2,1) state=self:focus [definite]
    - DECORATION: outline: none (L35); border-color: var(--accent) (L36); box-shadow: var(--focus-ring-shadow) (L37)
- nearest mold size: **md** (font-size token; font-size=var(--font-base)); padding T/R/B/L = var(--space-2) / var(--space-3) / var(--space-2) / var(--space-3); width=100% @frontend/src/components.css:22 -> fullWidth=true
- layout-only residue to keep as layoutClassName/className: width: 100% [.form-group select]
- before -> after vs SelectControl bare md (7/13 equal):
  - padding-top: var(--space-2) -> var(--space-2)  (same)
  - padding-right: var(--space-3) -> var(--space-5)
  - padding-bottom: var(--space-2) -> var(--space-2)  (same)
  - padding-left: var(--space-3) -> var(--space-3)  (same)
  - border: 1px solid var(--border) -> 1px solid var(--border)  (same)
  - border-radius: var(--radius-sm) -> var(--comp-input-radius)
  - font-size: var(--font-base) -> var(--font-base)  (same)
  - color: var(--text-primary) -> var(--text-primary)  (same)
  - background-color: var(--bg-surface) -> var(--bg-surface)  (same)
  - background-image: none -> arrow-svg(url data:image/svg+xml chevron #888)
  - height: (unset: browser default) -> (none)
  - min-height: (unset: browser default) -> (none)
  - line-height: (unset: browser default) -> var(--line-height-base)

### 50. pages/super-admin/KnowledgeAliasesTab.tsx:501  (KnowledgeAliasesTab)
- opening tag: `<select required value={aliasForm.supplier_id || ""} data-testid="alias-supplier-select" onChange={(e) => setAliasForm({ ...aliasForm, supplier_id: Number(e.target.value) })} >`
- className expr: (none) | inline style: (none)
- children kind: map (["option","map"]), disabledOption=false, onChange=`{(e) => setAliasForm({ ...aliasForm, supplier_id: Number(e.target.value) })}`, reads=["target.value"], numericConverted=true
- applied CSS rules:
  - `.form-group select` @ frontend/src/components.css:19 (0,1,1) state=base [definite]
    - LAYOUT: width: 100% (L22)
    - DECORATION: padding: var(--space-2) var(--space-3) (L23); border: 1px solid var(--border) (L24); border-radius: var(--radius-sm) (L25); font-size: var(--font-base) (L26); color: var(--text-primary) (L27); background: var(--bg-surface) (L28); box-sizing: border-box (L29)
  - `.form-group select:focus` @ frontend/src/components.css:32 (0,2,1) state=self:focus [definite]
    - DECORATION: outline: none (L35); border-color: var(--accent) (L36); box-shadow: var(--focus-ring-shadow) (L37)
- nearest mold size: **md** (font-size token; font-size=var(--font-base)); padding T/R/B/L = var(--space-2) / var(--space-3) / var(--space-2) / var(--space-3); width=100% @frontend/src/components.css:22 -> fullWidth=true
- layout-only residue to keep as layoutClassName/className: width: 100% [.form-group select]
- before -> after vs SelectControl bare md (7/13 equal):
  - padding-top: var(--space-2) -> var(--space-2)  (same)
  - padding-right: var(--space-3) -> var(--space-5)
  - padding-bottom: var(--space-2) -> var(--space-2)  (same)
  - padding-left: var(--space-3) -> var(--space-3)  (same)
  - border: 1px solid var(--border) -> 1px solid var(--border)  (same)
  - border-radius: var(--radius-sm) -> var(--comp-input-radius)
  - font-size: var(--font-base) -> var(--font-base)  (same)
  - color: var(--text-primary) -> var(--text-primary)  (same)
  - background-color: var(--bg-surface) -> var(--bg-surface)  (same)
  - background-image: none -> arrow-svg(url data:image/svg+xml chevron #888)
  - height: (unset: browser default) -> (none)
  - min-height: (unset: browser default) -> (none)
  - line-height: (unset: browser default) -> var(--line-height-base)

### 51. pages/super-admin/KnowledgeAliasesTab.tsx:523  (KnowledgeAliasesTab)
- opening tag: `<select value={aliasForm.product_id ?? ""} data-testid="alias-product-select" onChange={(e) => setAliasForm({ ...aliasForm, product_id: e.target.value ? Number(e.target.value) : null })} >`
- className expr: (none) | inline style: (none)
- children kind: map (["option","map"]), disabledOption=false, onChange=`{(e) => setAliasForm({ ...aliasForm, product_id: e.target.value ? Number(e.target.value) : null })}`, reads=["target.value"], numericConverted=true
- applied CSS rules:
  - `.form-group select` @ frontend/src/components.css:19 (0,1,1) state=base [definite]
    - LAYOUT: width: 100% (L22)
    - DECORATION: padding: var(--space-2) var(--space-3) (L23); border: 1px solid var(--border) (L24); border-radius: var(--radius-sm) (L25); font-size: var(--font-base) (L26); color: var(--text-primary) (L27); background: var(--bg-surface) (L28); box-sizing: border-box (L29)
  - `.form-group select:focus` @ frontend/src/components.css:32 (0,2,1) state=self:focus [definite]
    - DECORATION: outline: none (L35); border-color: var(--accent) (L36); box-shadow: var(--focus-ring-shadow) (L37)
- nearest mold size: **md** (font-size token; font-size=var(--font-base)); padding T/R/B/L = var(--space-2) / var(--space-3) / var(--space-2) / var(--space-3); width=100% @frontend/src/components.css:22 -> fullWidth=true
- layout-only residue to keep as layoutClassName/className: width: 100% [.form-group select]
- before -> after vs SelectControl bare md (7/13 equal):
  - padding-top: var(--space-2) -> var(--space-2)  (same)
  - padding-right: var(--space-3) -> var(--space-5)
  - padding-bottom: var(--space-2) -> var(--space-2)  (same)
  - padding-left: var(--space-3) -> var(--space-3)  (same)
  - border: 1px solid var(--border) -> 1px solid var(--border)  (same)
  - border-radius: var(--radius-sm) -> var(--comp-input-radius)
  - font-size: var(--font-base) -> var(--font-base)  (same)
  - color: var(--text-primary) -> var(--text-primary)  (same)
  - background-color: var(--bg-surface) -> var(--bg-surface)  (same)
  - background-image: none -> arrow-svg(url data:image/svg+xml chevron #888)
  - height: (unset: browser default) -> (none)
  - min-height: (unset: browser default) -> (none)
  - line-height: (unset: browser default) -> var(--line-height-base)

### 52. pages/super-admin/TcgSeriesTab.tsx:190  (TcgSeriesTab)
- opening tag: `<select value={filter} onChange={(e) => setFilter(e.target.value)}>`
- className expr: (none) | inline style: (none)
- children kind: map (["map"]), disabledOption=false, onChange=`{(e) => setFilter(e.target.value)}`, reads=["target.value"], numericConverted=false
- resolution note: TcgSeriesTab has no non-test importer in frontend/src (only the two *.test.tsx above). In-file chain has no .form-group/.filter-bar. Effective = no rule (unstyled -> md).
- applied CSS rules:
  - (none) -> unstyled
- unconfirmed rules (not counted): .form-group select@frontend/src/components.css:19; .form-group select:focus@frontend/src/components.css:32; .filter-bar select@frontend/src/components.css:60
- nearest mold size: **md** (font-size token; font-size=unset); padding T/R/B/L = 0 / 0 / 0 / 0; width=unset -> fullWidth=false
- layout-only residue to keep as layoutClassName/className: (none)
- before -> after vs SelectControl bare md (0/13 equal):
  - padding-top: 0 -> var(--space-2)
  - padding-right: 0 -> var(--space-5)
  - padding-bottom: 0 -> var(--space-2)
  - padding-left: 0 -> var(--space-3)
  - border: (unset: browser default) -> 1px solid var(--border)
  - border-radius: (unset: browser default) -> var(--comp-input-radius)
  - font-size: (unset: browser default) -> var(--font-base)
  - color: (unset: browser default) -> var(--text-primary)
  - background-color: (unset: browser default) -> var(--bg-surface)
  - background-image: (unset: browser default) -> arrow-svg(url data:image/svg+xml chevron #888)
  - height: (unset: browser default) -> (none)
  - min-height: (unset: browser default) -> (none)
  - line-height: (unset: browser default) -> var(--line-height-base)

### 53. pages/super-admin/TcgSeriesTab.tsx:300  (TcgSeriesTab)
- opening tag: `<select value={form.tcg_type} onChange={(e) => setForm({ ...form, tcg_type: e.target.value })} >`
- className expr: (none) | inline style: (none)
- children kind: map (["map"]), disabledOption=false, onChange=`{(e) => setForm({ ...form, tcg_type: e.target.value })}`, reads=["target.value"], numericConverted=false
- resolution note: same as TcgSeriesTab.tsx:190
- applied CSS rules:
  - (none) -> unstyled
- unconfirmed rules (not counted): .form-group select@frontend/src/components.css:19; .form-group select:focus@frontend/src/components.css:32; .filter-bar select@frontend/src/components.css:60
- nearest mold size: **md** (font-size token; font-size=unset); padding T/R/B/L = 0 / 0 / 0 / 0; width=unset -> fullWidth=false
- layout-only residue to keep as layoutClassName/className: (none)
- before -> after vs SelectControl bare md (0/13 equal):
  - padding-top: 0 -> var(--space-2)
  - padding-right: 0 -> var(--space-5)
  - padding-bottom: 0 -> var(--space-2)
  - padding-left: 0 -> var(--space-3)
  - border: (unset: browser default) -> 1px solid var(--border)
  - border-radius: (unset: browser default) -> var(--comp-input-radius)
  - font-size: (unset: browser default) -> var(--font-base)
  - color: (unset: browser default) -> var(--text-primary)
  - background-color: (unset: browser default) -> var(--bg-surface)
  - background-image: (unset: browser default) -> arrow-svg(url data:image/svg+xml chevron #888)
  - height: (unset: browser default) -> (none)
  - min-height: (unset: browser default) -> (none)
  - line-height: (unset: browser default) -> var(--line-height-base)

## 3. Bare-tag rules: every select they match

### frontend/src/company-forms.css:100 .form-grid > .form-row select (0,2,1) (rule wins (higher specificity))
- decls: padding: var(--space-2) var(--space-3) (L103); border: 1px solid var(--border-strong) (L104); border-radius: var(--radius-md) (L105); font-size: var(--font-base) (L106); background: var(--bg-surface) (L107); color: var(--text-primary) (L108); width: 100% (L109); box-sizing: border-box (L110); font-family: inherit (L111)
- raw selects matched (4): pages/companies/CompaniesPage.tsx:506 [definite, in-53], pages/company-detail/CompanyBasicTab.tsx:84 [definite, in-53], pages/contacts/ContactsPage.tsx:308 [definite, in-53], pages/contacts/ContactsPage.tsx:341 [definite, in-53]
- Select/SelectControl matched (1): pages/company-detail/CompanyAddressModal.tsx:84 Select [definite]
- after all 53 migrate: raw selects still matched = held 0 (in-53 raw selects matched: 4, all removed by migration); mold usages still affected = 1

### frontend/src/company-forms.css:120 .form-grid > .form-row select:focus (0,3,1) (rule wins (higher specificity))
- decls: outline: none (L123); border-color: var(--accent) (L124); box-shadow: var(--focus-ring-shadow) (L125)
- raw selects matched (4): pages/companies/CompaniesPage.tsx:506 [definite, in-53], pages/company-detail/CompanyBasicTab.tsx:84 [definite, in-53], pages/contacts/ContactsPage.tsx:308 [definite, in-53], pages/contacts/ContactsPage.tsx:341 [definite, in-53]
- Select/SelectControl matched (1): pages/company-detail/CompanyAddressModal.tsx:84 Select [definite]
- after all 53 migrate: raw selects still matched = held 0 (in-53 raw selects matched: 4, all removed by migration); mold usages still affected = 1

### frontend/src/company-forms.css:156 .modal-content .form-row select (0,2,1) (rule wins (higher specificity))
- decls: padding: var(--space-2) var(--space-3) (L162); border: 1px solid var(--border-strong) (L163); border-radius: var(--radius-md) (L164); font-size: var(--font-base) (L165); background: var(--bg-surface) (L166); color: var(--text-primary) (L167); width: 100% (L168); box-sizing: border-box (L169); font-family: inherit (L170)
- raw selects matched (0): (none)
- Select/SelectControl matched (0): (none)
- after all 53 migrate: raw selects still matched = held 0 (in-53 raw selects matched: 0, all removed by migration); mold usages still affected = 0

### frontend/src/company-forms.css:156 .modal-content-wide .form-row select (0,2,1) (rule wins (higher specificity))
- decls: padding: var(--space-2) var(--space-3) (L162); border: 1px solid var(--border-strong) (L163); border-radius: var(--radius-md) (L164); font-size: var(--font-base) (L165); background: var(--bg-surface) (L166); color: var(--text-primary) (L167); width: 100% (L168); box-sizing: border-box (L169); font-family: inherit (L170)
- raw selects matched (3): pages/companies/CompaniesPage.tsx:506 [definite, in-53], pages/contacts/ContactsPage.tsx:308 [definite, in-53], pages/contacts/ContactsPage.tsx:341 [definite, in-53]
- Select/SelectControl matched (1): pages/company-detail/CompanyAddressModal.tsx:84 Select [definite]
- after all 53 migrate: raw selects still matched = held 0 (in-53 raw selects matched: 3, all removed by migration); mold usages still affected = 1

### frontend/src/company-forms.css:181 .modal-content .form-row select:focus (0,3,1) (rule wins (higher specificity))
- decls: outline: none (L187); border-color: var(--accent) (L188); box-shadow: var(--focus-ring-shadow) (L189)
- raw selects matched (0): (none)
- Select/SelectControl matched (0): (none)
- after all 53 migrate: raw selects still matched = held 0 (in-53 raw selects matched: 0, all removed by migration); mold usages still affected = 0

### frontend/src/company-forms.css:181 .modal-content-wide .form-row select:focus (0,3,1) (rule wins (higher specificity))
- decls: outline: none (L187); border-color: var(--accent) (L188); box-shadow: var(--focus-ring-shadow) (L189)
- raw selects matched (3): pages/companies/CompaniesPage.tsx:506 [definite, in-53], pages/contacts/ContactsPage.tsx:308 [definite, in-53], pages/contacts/ContactsPage.tsx:341 [definite, in-53]
- Select/SelectControl matched (1): pages/company-detail/CompanyAddressModal.tsx:84 Select [definite]
- after all 53 migrate: raw selects still matched = held 0 (in-53 raw selects matched: 3, all removed by migration); mold usages still affected = 1

### frontend/src/company-forms.css:260 .product-edit-form .form-group select (0,2,1) (rule wins (higher specificity))
- decls: border: 1px solid var(--border-strong) (L263)
- raw selects matched (12): pages/integrations/FedexEtdSetupGuide.tsx:493 [unconfirmed, in-53], pages/products/ProductEditPage.tsx:231 [definite, held], pages/products/ProductEditPage.tsx:238 [definite, held], pages/products/ProductEditPage.tsx:255 [definite, held], pages/products/ProductEditPage.tsx:278 [definite, held], pages/products/ProductEditPage.tsx:285 [definite, held], pages/products/ProductEditPage.tsx:302 [definite, held], pages/products/ProductEditPage.tsx:346 [definite, held], pages/products/ProductEditPage.tsx:353 [definite, held], pages/products/ProductEditPage.tsx:360 [definite, held], pages/super-admin/components/StatusMasterPanel.tsx:311 [unconfirmed, in-53], pages/super-admin/components/StatusMasterPanel.tsx:325 [unconfirmed, in-53]
- Select/SelectControl matched (0): (none)
- after all 53 migrate: raw selects still matched = held 9 (in-53 raw selects matched: 3, all removed by migration); mold usages still affected = 0

### frontend/src/components.css:19 .form-group select (0,1,1) (rule wins (higher specificity))
- decls: width: 100% (L22); padding: var(--space-2) var(--space-3) (L23); border: 1px solid var(--border) (L24); border-radius: var(--radius-sm) (L25); font-size: var(--font-base) (L26); color: var(--text-primary) (L27); background: var(--bg-surface) (L28); box-sizing: border-box (L29)
- raw selects matched (42): components/CompanyContactSelector.tsx:190 [definite, in-53], components/CompanyContactSelector.tsx:214 [definite, in-53], components/PurchaseDetailPanel.tsx:424 [definite, in-53], components/ShippingDetailPanel.tsx:511 [definite, in-53], pages/admin/TenantPolicyPage.tsx:167 [definite, in-53], pages/admin/TenantPolicyPage.tsx:266 [definite, in-53], pages/admin/TenantPolicyPage.tsx:283 [definite, in-53], pages/admin/TenantProfilePage.tsx:234 [definite, in-53], pages/bots/BotsPage.tsx:233 [definite, in-53], pages/bots/BotsPage.tsx:241 [definite, in-53], pages/bots/BotsPage.tsx:248 [definite, in-53], pages/integrations/FedexEtdSetupGuide.tsx:493 [definite, in-53], pages/integrations/PaypalIntegrationPage.tsx:164 [definite, in-53], pages/invoice-create/InvoiceCreatePage.tsx:308 [definite, in-53], pages/orders/OrdersFormModal.tsx:86 [definite, in-53], pages/products/ProductEditPage.tsx:231 [definite, held], pages/products/ProductEditPage.tsx:238 [definite, held], pages/products/ProductEditPage.tsx:255 [definite, held], pages/products/ProductEditPage.tsx:278 [definite, held], pages/products/ProductEditPage.tsx:285 [definite, held], pages/products/ProductEditPage.tsx:302 [definite, held], pages/products/ProductEditPage.tsx:346 [definite, held], pages/products/ProductEditPage.tsx:353 [definite, held], pages/products/ProductEditPage.tsx:360 [definite, held], pages/purchase-orders/PurchaseOrdersFormModal.tsx:156 [definite, in-53], pages/quote-create/QuoteCreatePage.tsx:157 [definite, in-53], pages/status-master/StatusMasterPage.tsx:260 [definite, in-53], pages/status-master/StatusMasterPage.tsx:274 [definite, in-53], pages/super-admin/components/ConditionsMasterPanel.tsx:322 [definite, in-53], pages/super-admin/components/ConditionsMasterPanel.tsx:338 [definite, in-53], pages/super-admin/components/ConditionsMasterPanel.tsx:393 [definite, in-53], pages/super-admin/components/ConditionsMasterPanel.tsx:409 [definite, in-53], pages/super-admin/components/StatusMasterPanel.tsx:311 [definite, in-53], pages/super-admin/components/StatusMasterPanel.tsx:325 [definite, in-53], pages/super-admin/DexTab.tsx:194 [unconfirmed, in-53], pages/super-admin/KnowledgeAliasesTab.tsx:447 [definite, in-53], pages/super-admin/KnowledgeAliasesTab.tsx:455 [definite, in-53], pages/super-admin/KnowledgeAliasesTab.tsx:472 [definite, in-53], pages/super-admin/KnowledgeAliasesTab.tsx:501 [definite, in-53], pages/super-admin/KnowledgeAliasesTab.tsx:523 [definite, in-53], pages/super-admin/TcgSeriesTab.tsx:190 [unconfirmed, in-53], pages/super-admin/TcgSeriesTab.tsx:300 [unconfirmed, in-53]
- Select/SelectControl matched (16): pages/design-preview/sections/FormSection.tsx:53 Select [unconfirmed], pages/design-preview/sections/FormSection.tsx:57 Select [unconfirmed], pages/design-preview/sections/FormSection.tsx:61 Select [unconfirmed], pages/design-preview/sections/FormSection.tsx:65 Select [unconfirmed], pages/design-preview/sections/FormSection.tsx:105 Select [unconfirmed], pages/design-preview/sections/FormSection.tsx:109 Select [unconfirmed], pages/design-preview/sections/FormSection.tsx:113 Select [unconfirmed], pages/note-master/NoteMasterPage.tsx:290 Select [definite], pages/super-admin/components/NoteMasterPanel.tsx:278 Select [definite], pages/super-admin/components/ProductFormatsMasterPanel.tsx:279 SelectControl [definite], pages/super-admin/components/ProductFormatsMasterPanel.tsx:293 SelectControl [definite], pages/super-admin/components/ProductLinesMasterPanel.tsx:278 SelectControl [definite], pages/super-admin/components/ProductLinesMasterPanel.tsx:292 SelectControl [definite], pages/super-admin/components/RuleCreateDrawer.tsx:197 Select [unconfirmed], pages/super-admin/components/RuleCreateDrawer.tsx:209 Select [unconfirmed], pages/super-admin/components/TypeMasterPanel.tsx:253 SelectControl [definite]
- after all 53 migrate: raw selects still matched = held 9 (in-53 raw selects matched: 33, all removed by migration); mold usages still affected = 16

### frontend/src/components.css:32 .form-group select:focus (0,2,1) (rule wins (higher specificity))
- decls: outline: none (L35); border-color: var(--accent) (L36); box-shadow: var(--focus-ring-shadow) (L37)
- raw selects matched (42): components/CompanyContactSelector.tsx:190 [definite, in-53], components/CompanyContactSelector.tsx:214 [definite, in-53], components/PurchaseDetailPanel.tsx:424 [definite, in-53], components/ShippingDetailPanel.tsx:511 [definite, in-53], pages/admin/TenantPolicyPage.tsx:167 [definite, in-53], pages/admin/TenantPolicyPage.tsx:266 [definite, in-53], pages/admin/TenantPolicyPage.tsx:283 [definite, in-53], pages/admin/TenantProfilePage.tsx:234 [definite, in-53], pages/bots/BotsPage.tsx:233 [definite, in-53], pages/bots/BotsPage.tsx:241 [definite, in-53], pages/bots/BotsPage.tsx:248 [definite, in-53], pages/integrations/FedexEtdSetupGuide.tsx:493 [definite, in-53], pages/integrations/PaypalIntegrationPage.tsx:164 [definite, in-53], pages/invoice-create/InvoiceCreatePage.tsx:308 [definite, in-53], pages/orders/OrdersFormModal.tsx:86 [definite, in-53], pages/products/ProductEditPage.tsx:231 [definite, held], pages/products/ProductEditPage.tsx:238 [definite, held], pages/products/ProductEditPage.tsx:255 [definite, held], pages/products/ProductEditPage.tsx:278 [definite, held], pages/products/ProductEditPage.tsx:285 [definite, held], pages/products/ProductEditPage.tsx:302 [definite, held], pages/products/ProductEditPage.tsx:346 [definite, held], pages/products/ProductEditPage.tsx:353 [definite, held], pages/products/ProductEditPage.tsx:360 [definite, held], pages/purchase-orders/PurchaseOrdersFormModal.tsx:156 [definite, in-53], pages/quote-create/QuoteCreatePage.tsx:157 [definite, in-53], pages/status-master/StatusMasterPage.tsx:260 [definite, in-53], pages/status-master/StatusMasterPage.tsx:274 [definite, in-53], pages/super-admin/components/ConditionsMasterPanel.tsx:322 [definite, in-53], pages/super-admin/components/ConditionsMasterPanel.tsx:338 [definite, in-53], pages/super-admin/components/ConditionsMasterPanel.tsx:393 [definite, in-53], pages/super-admin/components/ConditionsMasterPanel.tsx:409 [definite, in-53], pages/super-admin/components/StatusMasterPanel.tsx:311 [definite, in-53], pages/super-admin/components/StatusMasterPanel.tsx:325 [definite, in-53], pages/super-admin/DexTab.tsx:194 [unconfirmed, in-53], pages/super-admin/KnowledgeAliasesTab.tsx:447 [definite, in-53], pages/super-admin/KnowledgeAliasesTab.tsx:455 [definite, in-53], pages/super-admin/KnowledgeAliasesTab.tsx:472 [definite, in-53], pages/super-admin/KnowledgeAliasesTab.tsx:501 [definite, in-53], pages/super-admin/KnowledgeAliasesTab.tsx:523 [definite, in-53], pages/super-admin/TcgSeriesTab.tsx:190 [unconfirmed, in-53], pages/super-admin/TcgSeriesTab.tsx:300 [unconfirmed, in-53]
- Select/SelectControl matched (16): pages/design-preview/sections/FormSection.tsx:53 Select [unconfirmed], pages/design-preview/sections/FormSection.tsx:57 Select [unconfirmed], pages/design-preview/sections/FormSection.tsx:61 Select [unconfirmed], pages/design-preview/sections/FormSection.tsx:65 Select [unconfirmed], pages/design-preview/sections/FormSection.tsx:105 Select [unconfirmed], pages/design-preview/sections/FormSection.tsx:109 Select [unconfirmed], pages/design-preview/sections/FormSection.tsx:113 Select [unconfirmed], pages/note-master/NoteMasterPage.tsx:290 Select [definite], pages/super-admin/components/NoteMasterPanel.tsx:278 Select [definite], pages/super-admin/components/ProductFormatsMasterPanel.tsx:279 SelectControl [definite], pages/super-admin/components/ProductFormatsMasterPanel.tsx:293 SelectControl [definite], pages/super-admin/components/ProductLinesMasterPanel.tsx:278 SelectControl [definite], pages/super-admin/components/ProductLinesMasterPanel.tsx:292 SelectControl [definite], pages/super-admin/components/RuleCreateDrawer.tsx:197 Select [unconfirmed], pages/super-admin/components/RuleCreateDrawer.tsx:209 Select [unconfirmed], pages/super-admin/components/TypeMasterPanel.tsx:253 SelectControl [definite]
- after all 53 migrate: raw selects still matched = held 9 (in-53 raw selects matched: 33, all removed by migration); mold usages still affected = 16

### frontend/src/components.css:60 .filter-bar select (0,1,1) (rule wins (higher specificity))
- decls: padding: var(--space-2) var(--space-3) (L62); border: 1px solid var(--border) (L63); border-radius: var(--radius-sm) (L64); font-size: var(--font-base) (L65); min-width: var(--input-select-min-w) (L66); background: var(--bg-surface) (L67); color: var(--text-primary) (L68)
- raw selects matched (6): pages/integrations/FedexEtdSetupGuide.tsx:493 [unconfirmed, in-53], pages/super-admin/components/StatusMasterPanel.tsx:311 [unconfirmed, in-53], pages/super-admin/components/StatusMasterPanel.tsx:325 [unconfirmed, in-53], pages/super-admin/DexTab.tsx:194 [unconfirmed, in-53], pages/super-admin/TcgSeriesTab.tsx:190 [unconfirmed, in-53], pages/super-admin/TcgSeriesTab.tsx:300 [unconfirmed, in-53]
- Select/SelectControl matched (9): pages/design-preview/sections/FormSection.tsx:53 Select [unconfirmed], pages/design-preview/sections/FormSection.tsx:57 Select [unconfirmed], pages/design-preview/sections/FormSection.tsx:61 Select [unconfirmed], pages/design-preview/sections/FormSection.tsx:65 Select [unconfirmed], pages/design-preview/sections/FormSection.tsx:105 Select [unconfirmed], pages/design-preview/sections/FormSection.tsx:109 Select [unconfirmed], pages/design-preview/sections/FormSection.tsx:113 Select [unconfirmed], pages/super-admin/components/RuleCreateDrawer.tsx:197 Select [unconfirmed], pages/super-admin/components/RuleCreateDrawer.tsx:209 Select [unconfirmed]
- after all 53 migrate: raw selects still matched = held 0 (in-53 raw selects matched: 6, all removed by migration); mold usages still affected = 9

## 4. Class rules: all users in frontend/src/**/*.tsx

### .schedule-input  tally {"non-select":6,"in-53-select":3}
- rule `.schedule-input` @ frontend/src/pages/schedule.css:813: width: 100% (L815); border: 1px solid var(--border) (L816); border-radius: var(--radius-md) (L817); background: var(--bg-surface) (L818); color: var(--text-primary) (L819); font-size: var(--font-sm) (L820) | layout=["width"] dimension=[] decoration=["border","border-radius","background","color","font-size"]
- rule `.schedule-input` @ frontend/src/pages/schedule.css:823: min-height: var(--comp-input-height-sm) (L824); padding: 0 var(--space-3) (L825) | layout=[] dimension=["min-height"] decoration=["padding"]
- rule `.schedule-input:focus` @ frontend/src/pages/schedule.css:833: outline: none (L835); border-color: var(--accent) (L836); box-shadow: var(--focus-ring-shadow) (L837) | layout=[] dimension=[] decoration=["outline","border-color","box-shadow"]
  - non-select:input | `<input>` pages/schedule/SchedulePageImpl.tsx:278 (static)
  - in-53-select | `<select>` pages/schedule/SchedulePageImpl.tsx:288 (static)
  - non-select:input | `<input>` pages/schedule/SchedulePageImpl.tsx:321 (static)
  - non-select:input | `<input>` pages/schedule/SchedulePageImpl.tsx:331 (static)
  - non-select:input | `<input>` pages/schedule/SchedulePageImpl.tsx:344 (static)
  - non-select:input | `<input>` pages/schedule/SchedulePageImpl.tsx:354 (static)
  - non-select:input | `<input>` pages/schedule/SchedulePageImpl.tsx:366 (static)
  - in-53-select | `<select>` pages/schedule/ScheduleSettingsPage.tsx:170 (static)
  - in-53-select | `<select>` pages/schedule/ScheduleSettingsPage.tsx:225 (static)

### .gs-select  tally {"in-53-select":1}
- rule `.gs-select` @ frontend/src/pages/goal-setting/GoalSettingPage.css:555: flex: 1 (L556); padding: var(--space-2) var(--space-3) (L557); border: 1px solid var(--border) (L558); border-radius: var(--radius-md) (L559); background: var(--bg-surface) (L560); color: var(--text-primary) (L561); font-size: var(--font-sm) (L562); cursor: pointer (L563) | layout=["flex"] dimension=[] decoration=["padding","border","border-radius","background","color","font-size","cursor"]
  - in-53-select | `<select>` pages/goal-setting/GoalSettingPage.tsx:711 (static)

### .account-settings-lang-select  tally {"in-53-select":1}
- rule `.account-settings-lang-select` @ frontend/src/pages/account-settings/account-settings.css:152: padding: var(--space-1) var(--space-3) (L153); border: 1px solid var(--border) (L154); border-radius: var(--radius-sm) (L155); background: var(--bg-surface) (L156); color: var(--text-primary) (L157); font-size: var(--font-sm) (L158); cursor: pointer (L159); min-width: var(--size-lang-select-min) (L160) | layout=["min-width"] dimension=[] decoration=["padding","border","border-radius","background","color","font-size","cursor"]
- rule `.account-settings-lang-select:focus` @ frontend/src/pages/account-settings/account-settings.css:163: outline: none (L164); border-color: var(--accent) (L165); box-shadow: var(--focus-ring-shadow) (L166) | layout=[] dimension=[] decoration=["outline","border-color","box-shadow"]
  - in-53-select | `<select>` pages/account-settings/PreferencesSection.tsx:38 (static)

### .inbox-page-filter-select  tally {"in-53-select":1}
- rule `.inbox-page-filter-select` @ frontend/src/pages/inbox/InboxPage.css:398: width: 100% (L399); padding: var(--space-1) var(--space-2) (L400); font-size: var(--font-xs) (L401); border-radius: var(--radius-xl) (L402); border: 1px solid var(--border) (L403); background: var(--bg-surface) (L404); color: var(--text-primary) (L405); font-family: inherit (L406); box-sizing: border-box (L407) | layout=["width"] dimension=[] decoration=["padding","font-size","border-radius","border","background","color","font-family","box-sizing"]
  - in-53-select | `<select>` pages/inbox/InboxConversationList.tsx:147 (static)

### .inbox-settings-select  tally {"in-53-select":1}
- rule `.inbox-settings-select` @ frontend/src/pages/inbox/InboxPage.css:1424: background: var(--bg-primary) (L1425); border: 1px solid var(--border) (L1425); border-radius: var(--radius-sm) (L1426); padding: var(--space-1) var(--space-2) (L1426); font-size: var(--font-sm) (L1427); color: var(--text-primary) (L1427); cursor: pointer (L1428) | layout=[] dimension=[] decoration=["background","border","border-radius","padding","font-size","color","cursor"]
  - in-53-select | `<select>` pages/inbox/InboxSettingsModal.tsx:37 (static)

### .field-h-md  tally {"non-select":9,"in-53-select":12,"mold-SelectControl":1,"mold-Select":2}
- rule `.field-h-md` @ frontend/src/components/field-size.css:8: min-height: var(--field-h-md, 36px) (L8); box-sizing: border-box (L8) | layout=[] dimension=["min-height"] decoration=["box-sizing"]
  - non-select:input | `<input>` components/master-list-editor/MasterListEditor.tsx:135 (static)
  - non-select:input | `<input>` pages/companies/CompaniesPage.tsx:384 (static)
  - non-select:textarea | `<textarea>` pages/conditions/ConditionsPage.tsx:340 (static)
  - non-select:textarea | `<textarea>` pages/conditions/ConditionsPage.tsx:350 (static)
  - in-53-select | `<select>` pages/contacts/ContactsPage.tsx:273 (static)
  - non-select:input | `<input>` pages/contacts/ContactsPage.tsx:279 (static)
  - non-select:input | `<input>` pages/inventory/InventoryPage.tsx:383 (static)
  - mold-SelectControl | `<SelectControl>` pages/invoices/InvoicesPage.tsx:132 (static)
  - mold-Select | `<Select>` pages/leads/LeadsPage.tsx:302 (static)
  - non-select:input | `<input>` pages/orders/OrdersFilterBar.tsx:31 (static)
  - in-53-select | `<select>` pages/orders/OrdersFilterBar.tsx:40 (static)
  - non-select:button | `<button>` pages/orders/OrdersFilterBar.tsx:51 (static)
  - non-select:input | `<input>` pages/products/ProductsPage.tsx:218 (static)
  - in-53-select | `<select>` pages/products/ProductsPage.tsx:220 (static)
  - in-53-select | `<select>` pages/purchase-orders/PurchaseOrdersPage.tsx:193 (static)
  - mold-Select | `<Select>` pages/staff-reports/StaffReportsPage.tsx:57 (static)
  - in-53-select | `<select>` pages/status-master/StatusMasterPage.tsx:260 (static)
  - in-53-select | `<select>` pages/status-master/StatusMasterPage.tsx:274 (static)
  - in-53-select | `<select>` pages/super-admin/components/ConditionsMasterPanel.tsx:322 (static)
  - in-53-select | `<select>` pages/super-admin/components/ConditionsMasterPanel.tsx:338 (static)
  - in-53-select | `<select>` pages/super-admin/components/ConditionsMasterPanel.tsx:393 (static)
  - in-53-select | `<select>` pages/super-admin/components/ConditionsMasterPanel.tsx:409 (static)
  - in-53-select | `<select>` pages/super-admin/components/StatusMasterPanel.tsx:311 (static)
  - in-53-select | `<select>` pages/super-admin/components/StatusMasterPanel.tsx:325 (static)
- other text hits (not JSX className; e.g. Button layoutClassName prop):
  - pages/bots/BotsPage.tsx:203: `<Button variant="primary" size="sm" layoutClassName="field-h-md" onClick={() => { setShowCreate(true); setCreateForm(emptyCreateForm); }}>`
  - pages/erp/ERPPage.tsx:59: `<Button variant="primary" size="sm" layoutClassName="field-h-md" onClick={exportInvoices} disabled={exporting}>`
  - pages/invoice-detail/InvoiceDetailPage.tsx:196: `<Button variant="primary" size="sm" layoutClassName="field-h-md" onClick={() => doAction("issue")}>{t("invoices.issueAction")}</Button>`
  - pages/invoice-detail/InvoiceDetailPage.tsx:199: `<Button variant="primary" size="sm" layoutClassName="field-h-md" onClick={() => doAction("pay")}>{t("invoices.payAction")}</Button>`
  - pages/invoice-detail/InvoiceDetailPage.tsx:202: `<Button variant="secondary" size="sm" layoutClassName="field-h-md" onClick={() => doAction("paypal-link")}>{t("invoices.paypal.issueLink")}<`
  - pages/invoice-detail/InvoiceDetailPage.tsx:205: `<Button variant="primary" size="sm" layoutClassName="field-h-md" onClick={() => doAction("paypal-confirm")}>{t("invoices.paypal.confirm")}</`
  - pages/invoice-detail/InvoiceDetailPage.tsx:208: `<Button variant="danger" size="sm" layoutClassName="field-h-md" onClick={() => setShowVoidForm(true)}>{t("invoices.voidAction")}</Button>`
  - pages/invoice-detail/InvoiceDetailPage.tsx:210: `<Button variant="secondary" size="sm" layoutClassName="field-h-md" onClick={handleDownloadPdf}>{t("invoices.snapshot.downloadPdf")}</Button>`
  - pages/quote-detail/QuoteDetailPage.tsx:134: `<Button variant="primary" size="sm" layoutClassName="field-h-md" onClick={() => doAction("send")}>{t("quotes.send")}</Button>`
  - pages/quote-detail/QuoteDetailPage.tsx:138: `<Button variant="primary" size="sm" layoutClassName="field-h-md" onClick={() => doAction("approve")}>{t("quotes.approve")}</Button>`
  - pages/quote-detail/QuoteDetailPage.tsx:139: `<Button variant="danger" size="sm" layoutClassName="field-h-md" onClick={() => doAction("reject")}>{t("quotes.reject")}</Button>`
  - pages/quote-detail/QuoteDetailPage.tsx:143: `<Button variant="primary" size="sm" layoutClassName="field-h-md" onClick={convertToInvoice}>{t("quotes.convertToInvoice")}</Button>`
  - pages/quote-detail/QuoteDetailPage.tsx:146: `<Button variant="secondary" size="sm" layoutClassName="field-h-md" onClick={handleFetchFxRate} disabled={fxLoading}>`
  - pages/quote-detail/QuoteDetailPage.tsx:150: `<Button variant="secondary" size="sm" layoutClassName="field-h-md" onClick={handleDownloadPdf}>{t("invoices.snapshot.downloadPdf")}</Button>`
  - pages/staff/StaffPage.tsx:223: `<Button variant="primary" size="sm" layoutClassName="field-h-md" onClick={() => { setShowCreate(true); setCreateForm(emptyCreateForm); }}>`
  - pages/super-admin/FxRatePage.tsx:94: `<Button variant="primary" size="sm" layoutClassName="field-h-md"`
  - pages/teams/TeamsPage.tsx:181: `<Button variant="primary" size="sm" layoutClassName="field-h-md" onClick={() => { setShowCreate(true); setCreateForm(emptyForm); }}>`

### .field-w-sm  tally {"non-select":3,"in-53-select":4,"mold-SelectControl":1,"mold-Select":2}
- rule `.field-w-sm` @ frontend/src/components/field-size.css:12: width: var(--field-w-sm, 160px) (L12) | layout=["width"] dimension=[] decoration=[]
- rule `.content-toolbar .field-w-sm` @ frontend/src/components/field-size.css:18: margin-bottom: 0 (L20) | layout=["margin-bottom"] dimension=[] decoration=[]
  - non-select:input | `<input>` components/master-list-editor/MasterListEditor.tsx:135 (static)
  - in-53-select | `<select>` pages/contacts/ContactsPage.tsx:273 (static)
  - non-select:input | `<input>` pages/contacts/ContactsPage.tsx:279 (static)
  - mold-SelectControl | `<SelectControl>` pages/invoices/InvoicesPage.tsx:132 (static)
  - mold-Select | `<Select>` pages/leads/LeadsPage.tsx:302 (static)
  - in-53-select | `<select>` pages/orders/OrdersFilterBar.tsx:40 (static)
  - non-select:input | `<input>` pages/products/ProductsPage.tsx:218 (static)
  - in-53-select | `<select>` pages/products/ProductsPage.tsx:220 (static)
  - in-53-select | `<select>` pages/purchase-orders/PurchaseOrdersPage.tsx:193 (static)
  - mold-Select | `<Select>` pages/staff-reports/StaffReportsPage.tsx:57 (static)

### .conv-logs-filter-select  tally {"in-53-select":1}
- CSS rules: NONE (class has no rule anywhere in frontend/src/**/*.css)
  - in-53-select | `<select>` pages/company-detail/CompanyConvLogsTab.tsx:73 (static)

### .manual-record-select  tally {"in-53-select":1}
- CSS rules: NONE (class has no rule anywhere in frontend/src/**/*.css)
  - in-53-select | `<select>` pages/inbox/ManualRecordSection.tsx:126 (static)

### .field  tally {"non-select":2,"in-53-select":8}
- CSS rules: NONE (class has no rule anywhere in frontend/src/**/*.css)
  - non-select:textarea | `<textarea>` pages/conditions/ConditionsPage.tsx:340 (static)
  - non-select:textarea | `<textarea>` pages/conditions/ConditionsPage.tsx:350 (static)
  - in-53-select | `<select>` pages/status-master/StatusMasterPage.tsx:260 (static)
  - in-53-select | `<select>` pages/status-master/StatusMasterPage.tsx:274 (static)
  - in-53-select | `<select>` pages/super-admin/components/ConditionsMasterPanel.tsx:322 (static)
  - in-53-select | `<select>` pages/super-admin/components/ConditionsMasterPanel.tsx:338 (static)
  - in-53-select | `<select>` pages/super-admin/components/ConditionsMasterPanel.tsx:393 (static)
  - in-53-select | `<select>` pages/super-admin/components/ConditionsMasterPanel.tsx:409 (static)
  - in-53-select | `<select>` pages/super-admin/components/StatusMasterPanel.tsx:311 (static)
  - in-53-select | `<select>` pages/super-admin/components/StatusMasterPanel.tsx:325 (static)

### .search-input  tally {"non-select":2,"in-53-select":1}
- CSS rules: NONE (class has no rule anywhere in frontend/src/**/*.css)
  - non-select:input | `<input>` pages/companies/CompaniesPage.tsx:384 (static)
  - in-53-select | `<select>` pages/contacts/ContactsPage.tsx:273 (static)
  - non-select:input | `<input>` pages/contacts/ContactsPage.tsx:279 (static)

## 5. Existing Select/SelectControl overridden by bare-tag rules: what changes when those rules stop applying

- pages/company-detail/CompanyAddressModal.tsx:84 `<Select>` size=md fullWidth=false appearance=field(Select) indicator=default variant=standard className=- | **definite**
  - rules: company-forms.css:100 .form-grid > .form-row select [definite] ; company-forms.css:120 .form-grid > .form-row select:focus [definite] ; company-forms.css:156 .modal-content-wide .form-row select [definite] ; company-forms.css:181 .modal-content-wide .form-row select:focus [definite]
  - [base] padding-right: var(--space-3) (@company-forms.css:162) -> var(--space-5) (@components/FormField.css:79)
  - [base] border: 1px solid var(--border-strong) (@company-forms.css:163) -> 1px solid var(--border) (@components/FormField.css:53)
  - [base] border-radius: var(--radius-md) (@company-forms.css:164) -> var(--comp-input-radius) (@components/FormField.css:54)
  - [base] background-image: none (@company-forms.css:166) -> arrow-svg(url data:image/svg+xml chevron #888) (@components/FormField.css:80)

- pages/design-preview/sections/FormSection.tsx:53 `<Select>` size=md fullWidth=false appearance=field(Select) indicator=default variant=standard className=- | **unconfirmed-only** (diffs below are HYPOTHETICAL: assume unconfirmed ancestor rules apply)
  - rules: components.css:19 .form-group select [unconfirmed] ; components.css:32 .form-group select:focus [unconfirmed] ; components.css:60 .filter-bar select [unconfirmed]
  - [base] border-radius: var(--radius-sm) (@components.css:64) -> var(--comp-input-radius) (@components/FormField.css:54)
  - [base] background-image: none (@components.css:67) -> arrow-svg(url data:image/svg+xml chevron #888) (@components/FormField.css:80)
  - [base] min-width: var(--input-select-min-w) (@components.css:66) -> (unset)

- pages/design-preview/sections/FormSection.tsx:57 `<Select>` size=md fullWidth=false appearance=field(Select) indicator=default variant=standard className=- | **unconfirmed-only** (diffs below are HYPOTHETICAL: assume unconfirmed ancestor rules apply)
  - rules: components.css:19 .form-group select [unconfirmed] ; components.css:32 .form-group select:focus [unconfirmed] ; components.css:60 .filter-bar select [unconfirmed]
  - [base] border-radius: var(--radius-sm) (@components.css:64) -> var(--comp-input-radius) (@components/FormField.css:54)
  - [base] background-image: none (@components.css:67) -> arrow-svg(url data:image/svg+xml chevron #888) (@components/FormField.css:80)
  - [base] min-width: var(--input-select-min-w) (@components.css:66) -> (unset)

- pages/design-preview/sections/FormSection.tsx:61 `<Select>` size=md fullWidth=false appearance=field(Select) indicator=default variant=standard className=- | **unconfirmed-only** (diffs below are HYPOTHETICAL: assume unconfirmed ancestor rules apply)
  - rules: components.css:19 .form-group select [unconfirmed] ; components.css:32 .form-group select:focus [unconfirmed] ; components.css:60 .filter-bar select [unconfirmed]
  - flags: error prop present (comp-field--error border-color not modeled)
  - [base] border-radius: var(--radius-sm) (@components.css:64) -> var(--comp-input-radius) (@components/FormField.css:54)
  - [base] background-image: none (@components.css:67) -> arrow-svg(url data:image/svg+xml chevron #888) (@components/FormField.css:80)
  - [base] min-width: var(--input-select-min-w) (@components.css:66) -> (unset)

- pages/design-preview/sections/FormSection.tsx:65 `<Select>` size=md fullWidth=false appearance=field(Select) indicator=default variant=standard className=- | **unconfirmed-only** (diffs below are HYPOTHETICAL: assume unconfirmed ancestor rules apply)
  - rules: components.css:19 .form-group select [unconfirmed] ; components.css:32 .form-group select:focus [unconfirmed] ; components.css:60 .filter-bar select [unconfirmed]
  - [base] border-radius: var(--radius-sm) (@components.css:64) -> var(--comp-input-radius) (@components/FormField.css:54)
  - [base] background-image: none (@components.css:67) -> arrow-svg(url data:image/svg+xml chevron #888) (@components/FormField.css:80)
  - [base] min-width: var(--input-select-min-w) (@components.css:66) -> (unset)

- pages/design-preview/sections/FormSection.tsx:105 `<Select>` size=sm fullWidth=false appearance=field(Select) indicator=default variant=standard className=- | **unconfirmed-only** (diffs below are HYPOTHETICAL: assume unconfirmed ancestor rules apply)
  - rules: components.css:19 .form-group select [unconfirmed] ; components.css:32 .form-group select:focus [unconfirmed] ; components.css:60 .filter-bar select [unconfirmed]
  - [base] border-radius: var(--radius-sm) (@components.css:64) -> var(--comp-input-radius) (@components/FormField.css:54)
  - [base] background-image: none (@components.css:67) -> arrow-svg(url data:image/svg+xml chevron #888) (@components/FormField.css:80)
  - [base] min-width: var(--input-select-min-w) (@components.css:66) -> (unset)

- pages/design-preview/sections/FormSection.tsx:109 `<Select>` size=md fullWidth=false appearance=field(Select) indicator=default variant=standard className=- | **unconfirmed-only** (diffs below are HYPOTHETICAL: assume unconfirmed ancestor rules apply)
  - rules: components.css:19 .form-group select [unconfirmed] ; components.css:32 .form-group select:focus [unconfirmed] ; components.css:60 .filter-bar select [unconfirmed]
  - [base] border-radius: var(--radius-sm) (@components.css:64) -> var(--comp-input-radius) (@components/FormField.css:54)
  - [base] background-image: none (@components.css:67) -> arrow-svg(url data:image/svg+xml chevron #888) (@components/FormField.css:80)
  - [base] min-width: var(--input-select-min-w) (@components.css:66) -> (unset)

- pages/design-preview/sections/FormSection.tsx:113 `<Select>` size=lg fullWidth=false appearance=field(Select) indicator=default variant=standard className=- | **unconfirmed-only** (diffs below are HYPOTHETICAL: assume unconfirmed ancestor rules apply)
  - rules: components.css:19 .form-group select [unconfirmed] ; components.css:32 .form-group select:focus [unconfirmed] ; components.css:60 .filter-bar select [unconfirmed]
  - [base] border-radius: var(--radius-sm) (@components.css:64) -> var(--comp-input-radius) (@components/FormField.css:54)
  - [base] background-image: none (@components.css:67) -> arrow-svg(url data:image/svg+xml chevron #888) (@components/FormField.css:80)
  - [base] min-width: var(--input-select-min-w) (@components.css:66) -> (unset)

- pages/note-master/NoteMasterPage.tsx:290 `<Select>` size=md fullWidth=true appearance=field(Select) indicator=default variant=standard className=- | **definite**
  - rules: components.css:19 .form-group select [definite] ; components.css:32 .form-group select:focus [definite]
  - [base] padding-right: var(--space-3) (@components.css:23) -> var(--space-5) (@components/FormField.css:79)
  - [base] border-radius: var(--radius-sm) (@components.css:25) -> var(--comp-input-radius) (@components/FormField.css:54)
  - [base] background-image: none (@components.css:28) -> arrow-svg(url data:image/svg+xml chevron #888) (@components/FormField.css:80)

- pages/super-admin/components/NoteMasterPanel.tsx:278 `<Select>` size=md fullWidth=true appearance=field(Select) indicator=default variant=standard className=- | **definite**
  - rules: components.css:19 .form-group select [definite] ; components.css:32 .form-group select:focus [definite]
  - [base] padding-right: var(--space-3) (@components.css:23) -> var(--space-5) (@components/FormField.css:79)
  - [base] border-radius: var(--radius-sm) (@components.css:25) -> var(--comp-input-radius) (@components/FormField.css:54)
  - [base] background-image: none (@components.css:28) -> arrow-svg(url data:image/svg+xml chevron #888) (@components/FormField.css:80)

- pages/super-admin/components/ProductFormatsMasterPanel.tsx:279 `<SelectControl>` size=md fullWidth=true appearance=bare indicator=default variant=standard className=- | **definite**
  - rules: components.css:19 .form-group select [definite] ; components.css:32 .form-group select:focus [definite]
  - [base] padding-right: var(--space-3) (@components.css:23) -> var(--space-5) (@components/FormField.css:79)
  - [base] border-radius: var(--radius-sm) (@components.css:25) -> var(--comp-input-radius) (@components/FormField.css:54)
  - [base] background-image: none (@components.css:28) -> arrow-svg(url data:image/svg+xml chevron #888) (@components/FormField.css:80)

- pages/super-admin/components/ProductFormatsMasterPanel.tsx:293 `<SelectControl>` size=md fullWidth=true appearance=bare indicator=default variant=standard className=- | **definite**
  - rules: components.css:19 .form-group select [definite] ; components.css:32 .form-group select:focus [definite]
  - [base] padding-right: var(--space-3) (@components.css:23) -> var(--space-5) (@components/FormField.css:79)
  - [base] border-radius: var(--radius-sm) (@components.css:25) -> var(--comp-input-radius) (@components/FormField.css:54)
  - [base] background-image: none (@components.css:28) -> arrow-svg(url data:image/svg+xml chevron #888) (@components/FormField.css:80)

- pages/super-admin/components/ProductLinesMasterPanel.tsx:278 `<SelectControl>` size=md fullWidth=true appearance=bare indicator=default variant=standard className=- | **definite**
  - rules: components.css:19 .form-group select [definite] ; components.css:32 .form-group select:focus [definite]
  - [base] padding-right: var(--space-3) (@components.css:23) -> var(--space-5) (@components/FormField.css:79)
  - [base] border-radius: var(--radius-sm) (@components.css:25) -> var(--comp-input-radius) (@components/FormField.css:54)
  - [base] background-image: none (@components.css:28) -> arrow-svg(url data:image/svg+xml chevron #888) (@components/FormField.css:80)

- pages/super-admin/components/ProductLinesMasterPanel.tsx:292 `<SelectControl>` size=md fullWidth=true appearance=bare indicator=default variant=standard className=- | **definite**
  - rules: components.css:19 .form-group select [definite] ; components.css:32 .form-group select:focus [definite]
  - [base] padding-right: var(--space-3) (@components.css:23) -> var(--space-5) (@components/FormField.css:79)
  - [base] border-radius: var(--radius-sm) (@components.css:25) -> var(--comp-input-radius) (@components/FormField.css:54)
  - [base] background-image: none (@components.css:28) -> arrow-svg(url data:image/svg+xml chevron #888) (@components/FormField.css:80)

- pages/super-admin/components/RuleCreateDrawer.tsx:197 `<Select>` size=md fullWidth=true appearance=field(Select) indicator=default variant=standard className=- | **unconfirmed-only** (diffs below are HYPOTHETICAL: assume unconfirmed ancestor rules apply)
  - rules: components.css:19 .form-group select [unconfirmed] ; components.css:32 .form-group select:focus [unconfirmed] ; components.css:60 .filter-bar select [unconfirmed]
  - [base] border-radius: var(--radius-sm) (@components.css:64) -> var(--comp-input-radius) (@components/FormField.css:54)
  - [base] background-image: none (@components.css:67) -> arrow-svg(url data:image/svg+xml chevron #888) (@components/FormField.css:80)
  - [base] min-width: var(--input-select-min-w) (@components.css:66) -> (unset)

- pages/super-admin/components/RuleCreateDrawer.tsx:209 `<Select>` size=md fullWidth=true appearance=field(Select) indicator=default variant=standard className=- | **unconfirmed-only** (diffs below are HYPOTHETICAL: assume unconfirmed ancestor rules apply)
  - rules: components.css:19 .form-group select [unconfirmed] ; components.css:32 .form-group select:focus [unconfirmed] ; components.css:60 .filter-bar select [unconfirmed]
  - [base] border-radius: var(--radius-sm) (@components.css:64) -> var(--comp-input-radius) (@components/FormField.css:54)
  - [base] background-image: none (@components.css:67) -> arrow-svg(url data:image/svg+xml chevron #888) (@components/FormField.css:80)
  - [base] min-width: var(--input-select-min-w) (@components.css:66) -> (unset)

- pages/super-admin/components/TypeMasterPanel.tsx:253 `<SelectControl>` size=md fullWidth=true appearance=bare indicator=default variant=standard className=- | **definite**
  - rules: components.css:19 .form-group select [definite] ; components.css:32 .form-group select:focus [definite]
  - [base] padding-right: var(--space-3) (@components.css:23) -> var(--space-5) (@components/FormField.css:79)
  - [base] border-radius: var(--radius-sm) (@components.css:25) -> var(--comp-input-radius) (@components/FormField.css:54)
  - [base] background-image: none (@components.css:28) -> arrow-svg(url data:image/svg+xml chevron #888) (@components/FormField.css:80)

## 6. ui-allow comments attached to the 53 (verbatim)
- pages/inventory/InventoryPage.tsx:477 L476 (preceding): `// ui-allow: TCG "other types" dropdown from main back-merge, ADR-143 D-1 (#2624)`
- pages/status-master/StatusMasterPage.tsx:260 L259 (preceding): `{/* ui-allow: enum select for status match_type; no SelectControl variant with option map (#3594) */}`
- pages/status-master/StatusMasterPage.tsx:274 L273 (preceding): `{/* ui-allow: enum select for status effect; no SelectControl variant with option map (#3594) */}`
- pages/super-admin/components/ConditionsMasterPanel.tsx:322 L321 (preceding): `{/* ui-allow: reference pulldown for condition_def_id; no SelectControl variant with dynamic option list (#3594) */}`
- pages/super-admin/components/ConditionsMasterPanel.tsx:338 L337 (preceding): `{/* ui-allow: reference pulldown for unit_id; no SelectControl variant with dynamic option list (#3594) */}`
- pages/super-admin/components/ConditionsMasterPanel.tsx:393 L392 (preceding): `{/* ui-allow: enum select for condition match_type; no SelectControl variant with option map (#3594) */}`
- pages/super-admin/components/ConditionsMasterPanel.tsx:409 L408 (preceding): `{/* ui-allow: enum select for condition effect; no SelectControl variant with option map (#3594) */}`
- pages/super-admin/components/StatusMasterPanel.tsx:311 L310 (preceding): `{/* ui-allow: enum select for status match_type; no SelectControl variant with option map (#3594) */}`
- pages/super-admin/components/StatusMasterPanel.tsx:325 L324 (preceding): `{/* ui-allow: enum select for status effect; no SelectControl variant with option map (#3594) */}`

## 7. Inline style objects on the 53 (verbatim)
- pages/inventory/InventoryPage.tsx:477: `{{ fontSize: "var(--font-xs)", padding: "var(--space-1) var(--space-10px)", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", background: "var(--bg-surface)" }}`
  - non-var() residue: [{"prop":"border","value":"1px solid var(--border)","residual":"1px solid"}]
