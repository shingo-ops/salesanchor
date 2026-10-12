# AS candidate review — correction of the proposed 85-button batch

Source evidence: `/tmp/as-button-inventory.json` (85 proposed entries) and `/tmp/as-button-inventory.md`; code/CSS read from `release-frontend-button-batch-result`. This is read-only classification, not an implementation design.

## Finding

The 85 entries are **not one proven same-shape batch**.

- **39 entries / 27 files** have one static, explicit legacy color variant (`btn-primary`, `btn-secondary`, `btn-ghost`, or `btn-danger`). Their Button `variant` is mechanically determined by the existing class; `btn-sm` determines `size="sm"`, absence of `btn-sm` determines md, and an existing `field-h-md` can be forwarded as the existing layout class. This is the maximum set whose variant and size can be mapped without inventing appearance semantics.
- Within those 39, **34** are modal/editor open/close, pagination, or internal navigation/local-state actions. They are the lowest-risk first cohort. The remaining **5** are search/reload handlers and require exact query/API and pending/error tests; their visual mapping is still explicit, but they should not be described as side-effect-free.
- **42 entries / 21 files** are bare `btn-sm`. Legacy CSS defines size *and* a neutral background/color directly; it does not name that appearance “secondary”, “ghost”, or “outline”. Button has no neutral/unclassified variant. Assigning `secondary` would add a border/surface background, while `ghost` would change padding/font/weight/background. All 42 require a design decision or a new evidence-backed mapping and are excluded from mechanical implementation.
- **4 entries / 3 files** use dynamic classes. This measured count is four, not three: Inventory 1, InvoiceCreate 2, Products 1. Three toggle explicitly between primary/secondary; Products toggles primary/bare-`btn-sm`, leaving one state unmappable. Dynamic visual/ARIA semantics need individual design and are excluded from the mechanical cohort.

Therefore the defensible maximum is **39**, with **34** recommended as the first non-reload cohort. Claiming 85 same-shape replacements is unsupported.

## CSS evidence for the classification

- Legacy primary: `frontend/src/components.css:54-66`; secondary `:68-78`; ghost `:81-93`; bare sm `:95-105`; danger `:107-122`; compound sm secondary/danger/primary `:145-163`.
- Shared variants are explicit in `frontend/src/components/Button.tsx:20,40-47`; size mapping is `:21,49-73`.
- Legacy bare `btn-sm` is padding 4px/10px, xs font, neutral `bg-hover`, no border, 3px radius (`components.css:95-103`; tokens `:68,84,88`). Shared sm is min-height 28px, padding 4px/12px, xs font (`Button.css:20-24`). Shared secondary adds surface background + border (`Button.css:42-46`); ghost is transparent and inherits shared base padding/weight (`Button.css:2-18,48-52`). No exact named variant equivalence exists.
- `field-h-md` is min-height 36px plus border-box only (`components/field-size.css:6-9`). Preserving it does not make old and new pixels identical: shared Button also changes border/radius/padding. The contract is adoption of the existing Button mold, not pixel identity.
- Button preserves omitted/explicit type and native handler props, but `loading` would add disabled/aria-busy (`Button.tsx:75-86`). No candidate should gain `loading` merely during tag conversion.

## Static explicit-variant set: 39 (maximum mechanically mappable)

Mapping rule: primary→`variant="primary"`; secondary→`variant="secondary"`; ghost→`variant="ghost"`; danger→`variant="danger"`; `btn-sm`→`size="sm"`; otherwise `size="md"`; existing `field-h-md` remains placement/min-height evidence. Event/type/disabled expressions below must remain verbatim in behavior.

| Source | Existing class | type | event | disabled | inventory group |
|---|---|---|---|---|---|
| `src/components/CommissionPanel.tsx:263` | `btn-secondary` | `button` | `onClose` | `- ` | `modal-close-or-cancel` |
| `src/components/master-list-editor/MasterListEditor.tsx:209` | `btn-secondary btn-sm` | `None` | `() => startEdit(r)` | `- ` | `modal-or-editor-launch` |
| `src/pages/badges/BadgesPage.tsx:49` | `btn-primary field-h-md` | `None` | `() => setShowForm(true)` | `- ` | `modal-or-editor-launch` |
| `src/pages/buddy/BuddyPage.tsx:54` | `btn-primary field-h-md` | `None` | `() => setShowForm(true)` | `- ` | `modal-or-editor-launch` |
| `src/pages/channels/ChannelsPage.tsx:600` | `btn-sm btn-ghost` | `None` | `() => navigate("/admin/discord-config")` | `- ` | `internal-navigation` |
| `src/pages/inbox/InboxPage.tsx:46` | `btn-ghost` | `button` | `() => navigate("/templates")` | `- ` | `internal-navigation` |
| `src/pages/inbox/InboxPage.tsx:55` | `btn-ghost` | `button` | `() => navigate("/faq")` | `- ` | `internal-navigation` |
| `src/pages/integrations/CarrierCredentialForm.tsx:136` | `btn-secondary` | `None` | `onCancel` | `busy ` | `modal-close-or-cancel` |
| `src/pages/integrations/CarrierIntegrationPage.tsx:205` | `btn-secondary` | `None` | `() => openEdit(env)` | `busy ` | `modal-or-editor-launch` |
| `src/pages/integrations/CarrierIntegrationPage.tsx:276` | `btn-secondary` | `None` | `() => openEdit(env)` | `busy ` | `modal-or-editor-launch` |
| `src/pages/integrations/FedexEtdSetupGuide.tsx:474` | `btn-primary` | `button` | `onOpenCredentialsTab` | `- ` | `modal-or-editor-launch` |
| `src/pages/inventory/InventoryPage.tsx:394` | `btn-primary btn-sm field-h-md` | `button` | `runSearch` | `- ` | `search-or-reload` |
| `src/pages/inventory/InventoryPage.tsx:602` | `btn-secondary` | `None` | `() => setPage(Math.max(1, page - 1))` | `page <= 1 || loading ` | `pagination-or-clear` |
| `src/pages/inventory/InventoryPage.tsx:608` | `btn-secondary` | `None` | `() => setPage(Math.min(totalPages, page + 1))` | `page >= totalPages || loading ` | `pagination-or-clear` |
| `src/pages/invoice-create/InvoiceCreatePage.tsx:223` | `btn-secondary` | `None` | `() => navigate("/management-center/tenant-profile")` | `- ` | `internal-navigation` |
| `src/pages/invoice-create/InvoiceCreatePage.tsx:271` | `btn-sm btn-primary` | `None` | `() => loadQuoteForEdit(q.id)` | `saving ` | `search-or-reload` |
| `src/pages/invoice-create/InvoiceCreatePage.tsx:434` | `btn-secondary` | `button` | `() => navigate("/invoices")` | `- ` | `internal-navigation` |
| `src/pages/invoice-detail/InvoiceDetailPage.tsx:206` | `btn-danger field-h-md` | `None` | `() => setShowVoidForm(true)` | `- ` | `modal-or-editor-launch` |
| `src/pages/invoice-detail/InvoiceDetailPage.tsx:272` | `btn-secondary` | `None` | `() => setShowVoidForm(false)` | `- ` | `modal-or-editor-launch` |
| `src/pages/notifications/NotificationsPage.tsx:52` | `btn-primary field-h-md` | `None` | `() => setShowForm(true)` | `- ` | `modal-or-editor-launch` |
| `src/pages/orders/OrdersPage.tsx:48` | `btn-primary field-h-md` | `None` | `() => { setShowForm(true); setEditId(null); setForm(emptyForm); resetSelector(); }` | `- ` | `modal-or-editor-launch` |
| `src/pages/products/ProductEditPage.tsx:175` | `btn-secondary field-h-md` | `button` | `() => navigate(-1)` | `saving ` | `internal-navigation` |
| `src/pages/products/ProductsPage.tsx:190` | `btn-primary` | `button` | `() => navigate("/admin/products/new")` | `- ` | `internal-navigation` |
| `src/pages/purchase-orders/PurchaseOrdersFormModal.tsx:134` | `btn-secondary` | `button` | `onClose` | `saving ` | `modal-close-or-cancel` |
| `src/pages/purchase-orders/PurchaseOrdersPage.tsx:198` | `btn-primary field-h-md` | `None` | `() => { setPoInitial(null); setShowNewModal(true); }` | `- ` | `modal-or-editor-launch` |
| `src/pages/quote-create/QuoteCreatePage.tsx:267` | `btn-sm btn-secondary` | `button` | `() => setShowFedExModal(true)` | `- ` | `modal-or-editor-launch` |
| `src/pages/quote-create/QuoteCreatePage.tsx:282` | `btn-secondary` | `button` | `() => navigate("/quotes")` | `- ` | `internal-navigation` |
| `src/pages/quotes/QuotesPage.tsx:137` | `btn-primary field-h-md` | `None` | `() => navigate("/quotes/new")` | `- ` | `internal-navigation` |
| `src/pages/roles/RolesPage.tsx:404` | `btn-secondary` | `None` | `cancelEdits` | `!dirty || savingPerms ` | `modal-close-or-cancel` |
| `src/pages/shifts/ShiftsPage.tsx:53` | `btn-primary field-h-md` | `None` | `() => setShowForm(true)` | `- ` | `modal-or-editor-launch` |
| `src/pages/staff-reports/StaffReportsPage.tsx:69` | `btn-primary field-h-md` | `None` | `() => setShowForm(true)` | `- ` | `modal-or-editor-launch` |
| `src/pages/super-admin/DexTab.tsx:173` | `btn-secondary` | `None` | `() => startEdit(it)` | `- ` | `modal-or-editor-launch` |
| `src/pages/super-admin/DexTab.tsx:206` | `btn-secondary` | `None` | `load` | `- ` | `search-or-reload` |
| `src/pages/super-admin/DexTab.tsx:324` | `btn-secondary` | `button` | `() => setEditing(null)` | `- ` | `modal-close-or-cancel` |
| `src/pages/super-admin/KnowledgeAliasesTab.tsx:339` | `btn-secondary btn-sm` | `None` | `() => loadRules(ruleSearch)` | `- ` | `search-or-reload` |
| `src/pages/super-admin/KnowledgeAliasesTab.tsx:417` | `btn-secondary btn-sm` | `None` | `() => loadAliases(aliasSearch)` | `- ` | `search-or-reload` |
| `src/pages/super-admin/LLMBudgetTab.tsx:148` | `btn-secondary` | `button` | `() => startEdit(b)` | `- ` | `modal-or-editor-launch` |
| `src/pages/super-admin/TcgSeriesTab.tsx:197` | `btn-secondary` | `button` | `() => setShowTypeManager((v) => !v)` | `- ` | `modal-or-editor-launch` |
| `src/pages/super-admin/TcgSeriesTab.tsx:359` | `btn-secondary` | `None` | `() => startEdit(it)` | `- ` | `modal-or-editor-launch` |

### Event-risk split inside the 39

The 34 non-reload entries preserve direct local state, callbacks, pagination setters, or router navigation. They still require DOM outcome tests (dialog/editor visibility and focus; exact destination; boundary disabled), but variant selection is settled by CSS.

The five search/reload entries must have focused API/state evidence before implementation acceptance:

- `src/pages/inventory/InventoryPage.tsx:394` `runSearch` — preserve exact query/read count, disabled/pending behavior if present, failure state, and zero writes unless the existing helper writes.
- `src/pages/invoice-create/InvoiceCreatePage.tsx:271` `() => loadQuoteForEdit(q.id)` — preserve exact query/read count, disabled/pending behavior if present, failure state, and zero writes unless the existing helper writes.
- `src/pages/super-admin/DexTab.tsx:206` `load` — preserve exact query/read count, disabled/pending behavior if present, failure state, and zero writes unless the existing helper writes.
- `src/pages/super-admin/KnowledgeAliasesTab.tsx:339` `() => loadRules(ruleSearch)` — preserve exact query/read count, disabled/pending behavior if present, failure state, and zero writes unless the existing helper writes.
- `src/pages/super-admin/KnowledgeAliasesTab.tsx:417` `() => loadAliases(aliasSearch)` — preserve exact query/read count, disabled/pending behavior if present, failure state, and zero writes unless the existing helper writes.

No sales or revenue effect is inferred. The measurable effect of choosing 39 is removal of 39 legacy nodes with 39 exact Button additions, subject to inverse/raw audits and behavioral tests.

## Bare btn-sm: 42 excluded pending design

Every event is recorded to show that exclusion is visual-contract uncertainty, not lack of handler inventory.

| Source | Existing class | type | event | disabled | inventory group |
|---|---|---|---|---|---|
| `src/components/DataTable.tsx:286` | `btn-sm` | `button` | `() => onPageChange(Math.max(1, page - 1))` | `page <= 1 ` | `pagination-or-clear` |
| `src/components/DataTable.tsx:298` | `btn-sm` | `button` | `() => onPageChange(page + 1)` | `!hasNextPage ` | `pagination-or-clear` |
| `src/components/master-list-editor/MasterListEditor.tsx:144` | `btn-sm` | `button` | `() => { setSearch(""); setSearchInput(""); }` | `- ` | `pagination-or-clear` |
| `src/pages/bots/BotsPage.tsx:311` | `btn-sm` | `None` | `(e) => { e.stopPropagation(); handleRowClick(b); }` | `- ` | `modal-or-editor-launch` |
| `src/pages/companies/CompaniesPage.tsx:410` | `btn-sm` | `None` | `(e) => { e.stopPropagation(); handleRowClick(c); }` | `- ` | `modal-or-editor-launch` |
| `src/pages/company-detail/CompanyAddressesTab.tsx:52` | `btn-sm` | `None` | `() => openAddressEdit(a)` | `- ` | `modal-or-editor-launch` |
| `src/pages/conditions/ConditionsPage.tsx:279` | `btn-sm` | `None` | `(e) => { e.stopPropagation(); openEdit(c); }` | `- ` | `modal-or-editor-launch` |
| `src/pages/conditions/ConditionsPage.tsx:420` | `btn-sm` | `button` | `() => { setSearch(""); setSearchInput(""); setPage(1); }` | `- ` | `pagination-or-clear` |
| `src/pages/conditions/ConditionsPage.tsx:595` | `btn-sm` | `None` | `() => setPage(p => Math.max(1, p - 1))` | `page <= 1 ` | `pagination-or-clear` |
| `src/pages/conditions/ConditionsPage.tsx:608` | `btn-sm` | `None` | `() => setPage(p => p + 1)` | `!hasNext ` | `pagination-or-clear` |
| `src/pages/contacts/ContactsPage.tsx:397` | `btn-sm` | `None` | `(e) => { e.stopPropagation(); handleRowClick(c); }` | `- ` | `modal-or-editor-launch` |
| `src/pages/inventory/InventoryFilterPanel.tsx:304` | `btn-sm` | `button` | `onClose` | `- ` | `modal-close-or-cancel` |
| `src/pages/note-master/NoteMasterPage.tsx:236` | `btn-sm` | `None` | `(e) => { e.stopPropagation(); openEdit(n); }` | `- ` | `modal-or-editor-launch` |
| `src/pages/orders/OrdersTable.tsx:181` | `btn-sm` | `None` | `() => setShippingTarget(o)` | `- ` | `modal-or-editor-launch` |
| `src/pages/orders/OrdersTable.tsx:184` | `btn-sm` | `None` | `() => setPurchaseTarget(o)` | `- ` | `modal-or-editor-launch` |
| `src/pages/product-categories/ProductCategoriesPage.tsx:181` | `btn-sm` | `None` | `(e) => { e.stopPropagation(); openEdit(c); }` | `- ` | `modal-or-editor-launch` |
| `src/pages/product-categories/ProductCategoriesPage.tsx:294` | `btn-sm` | `button` | `() => { setSearch(""); setSearchInput(""); setPage(1); }` | `- ` | `pagination-or-clear` |
| `src/pages/product-categories/ProductCategoriesPage.tsx:377` | `btn-sm` | `None` | `() => setPage(p => Math.max(1, p - 1))` | `page <= 1 ` | `pagination-or-clear` |
| `src/pages/product-categories/ProductCategoriesPage.tsx:390` | `btn-sm` | `None` | `() => setPage(p => p + 1)` | `!hasNext ` | `pagination-or-clear` |
| `src/pages/products/ProductsPage.tsx:274` | `btn-sm` | `None` | `() => setSelectedIds(new Set())` | `- ` | `in-page-switch` |
| `src/pages/products/ProductsPage.tsx:422` | `btn-sm` | `None` | `() => setPage((p) => Math.max(1, p - 1))` | `page <= 1 ` | `pagination-or-clear` |
| `src/pages/products/ProductsPage.tsx:435` | `btn-sm` | `None` | `() => setPage((p) => p + 1)` | `!hasNext ` | `pagination-or-clear` |
| `src/pages/quotes/QuotesPage.tsx:167` | `btn-sm` | `None` | `() => navigate(`/quotes/${q.id}`)` | `- ` | `internal-navigation` |
| `src/pages/roles/RolesPage.tsx:398` | `btn-sm` | `None` | `() => openEditRole(selectedRole)` | `- ` | `modal-or-editor-launch` |
| `src/pages/sales/SalesPage.tsx:167` | `btn-sm` | `button` | `() => setEditing(o)` | `- ` | `modal-or-editor-launch` |
| `src/pages/staff/StaffPage.tsx:366` | `btn-sm` | `None` | `(e) => { e.stopPropagation(); handleRowClick(s); }` | `- ` | `modal-or-editor-launch` |
| `src/pages/status-master/StatusMasterPage.tsx:208` | `btn-sm` | `None` | `(e) => { e.stopPropagation(); openEdit(s); }` | `- ` | `modal-or-editor-launch` |
| `src/pages/status-master/StatusMasterPage.tsx:362` | `btn-sm` | `button` | `() => { setSearch(""); setSearchInput(""); setPage(1); }` | `- ` | `pagination-or-clear` |
| `src/pages/status-master/StatusMasterPage.tsx:445` | `btn-sm` | `None` | `() => setPage(p => Math.max(1, p - 1))` | `page <= 1 ` | `pagination-or-clear` |
| `src/pages/status-master/StatusMasterPage.tsx:458` | `btn-sm` | `None` | `() => setPage(p => p + 1)` | `!hasNext ` | `pagination-or-clear` |
| `src/pages/super-admin/KnowledgeAliasesTab.tsx:390` | `btn-sm` | `None` | `() => openEditRule(r)` | `- ` | `modal-or-editor-launch` |
| `src/pages/super-admin/KnowledgeAliasesTab.tsx:462` | `btn-sm` | `None` | `() => openEditAlias(a)` | `- ` | `modal-or-editor-launch` |
| `src/pages/suppliers/SuppliersPage.tsx:179` | `btn-sm` | `button` | `() => { setSearch(""); setSearchInput(""); setPage(1); }` | `- ` | `pagination-or-clear` |
| `src/pages/suppliers/SuppliersPage.tsx:239` | `btn-sm` | `None` | `(e) => { e.stopPropagation(); handleRowClick(s); }` | `- ` | `modal-or-editor-launch` |
| `src/pages/suppliers/SuppliersPage.tsx:275` | `btn-sm` | `None` | `() => setPage((p) => Math.max(1, p - 1))` | `page <= 1 ` | `pagination-or-clear` |
| `src/pages/suppliers/SuppliersPage.tsx:288` | `btn-sm` | `None` | `() => setPage((p) => p + 1)` | `!hasNext ` | `pagination-or-clear` |
| `src/pages/teams/TeamsPage.tsx:281` | `btn-sm` | `None` | `(e) => { e.stopPropagation(); openMembers(team); }` | `- ` | `modal-or-editor-launch` |
| `src/pages/teams/TeamsPage.tsx:283` | `btn-sm` | `None` | `(e) => { e.stopPropagation(); handleRowClick(team); }` | `- ` | `modal-or-editor-launch` |
| `src/pages/units/UnitsPage.tsx:189` | `btn-sm` | `None` | `(e) => { e.stopPropagation(); openEdit(u); }` | `- ` | `modal-or-editor-launch` |
| `src/pages/units/UnitsPage.tsx:253` | `btn-sm` | `button` | `() => { setSearch(""); setSearchInput(""); setPage(1); }` | `- ` | `pagination-or-clear` |
| `src/pages/units/UnitsPage.tsx:400` | `btn-sm` | `None` | `() => setPage(p => Math.max(1, p - 1))` | `page <= 1 ` | `pagination-or-clear` |
| `src/pages/units/UnitsPage.tsx:413` | `btn-sm` | `None` | `() => setPage(p => p + 1)` | `!hasNext ` | `pagination-or-clear` |

These include 20 pagination/clear, 19 modal/editor launch, and three other actions. Similar event purpose does not establish a Button color variant. A later design may group them only after naming the desired appearance and accepting the CSS differences.

## Dynamic class: 4 excluded pending individual design

| Source | Existing class expression | type | event | disabled | inventory group |
|---|---|---|---|---|---|
| `src/pages/inventory/InventoryPage.tsx:400` | `filterEnabled ? "btn-primary btn-sm field-h-md" : "btn-secondary btn-sm field-h-md"` | `button` | `() => setShowFilterPanel((v) => !v)` | `- ` | `modal-or-editor-launch` |
| `src/pages/invoice-create/InvoiceCreatePage.tsx:233` | `mode === "inventory" ? "btn-primary" : "btn-secondary"` | `None` | `() => setMode("inventory")` | `- ` | `in-page-switch` |
| `src/pages/invoice-create/InvoiceCreatePage.tsx:240` | `mode === "quote" ? "btn-primary" : "btn-secondary"` | `None` | `() => { setSourceQuoteCode(null); setMode("quote"); }` | `- ` | `in-page-switch` |
| `src/pages/products/ProductsPage.tsx:234` | `reorderMode ? "btn-primary btn-sm" : "btn-sm"` | `button` | `toggleReorderMode` | `- ` | `in-page-switch` |

- Inventory's condition is `filterEnabled`, while its click toggles panel visibility; `aria-pressed` and `aria-expanded` describe different state. Mapping to Button tab/active would be a semantic change unless explicitly designed.
- InvoiceCreate has two mutually exclusive primary/secondary mode buttons. It can likely map after tests prove selected mode and source-quote reset, but remains a screen-switch design rather than a blind class replacement.
- Products mixes primary with bare `btn-sm`; the inactive appearance has no proven Button variant, so the pair cannot be mechanically mapped.

## Verification boundary for an implementation card

1. AST/raw audit should target exactly the approved subset, not 85. For the 39 maximum: 39 old nodes removed, 39 Button nodes added, other 227 of the measured 266 production legacy entries unchanged. If only the recommended 34 are used, expected residual is 232.
2. Preserve each row's native/implicit `type`, handler expression, disabled, test id, title/ARIA, children and `stopPropagation`. Do not “improve” pending locking.
3. Modal/editor actions: real page/component tests for open target, cancel/X/Escape, trigger focus return, initial state/reset, permission settlement, zero writes on close.
4. Pagination/navigation: boundary disabled, exact page/destination/history direction and no handler on disabled click.
5. Search/reload five: exact GET/query/read increment, click/Enter only where existing UI supports both, pending/rejection recovery, and unexpected write/network rejection.
6. Existing suites named in the inventory can be reused, but class-only assertions do not prove event/state/API behavior. Add real-page tests for “none found” entries.
7. Strict ESLint, focused unit tests, `git diff --check`, inverse byte audit of every non-target node, and shared Button/CSS hash checks are required.

## Final recommendation

Use **34 static explicit-variant, non-reload entries** as the first design candidate. The design may expand to **39** by accepting the five focused reload/API test obligations. Keep all **42 bare btn-sm** and **4 dynamic-class** entries outside until their appearance and state semantics are explicitly decided. This yields a fact-based batch size and avoids converting neutral legacy styling into an invented secondary/ghost meaning.
