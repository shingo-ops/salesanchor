# AS 34-button existing-test coverage and minimum regression plan

Fixed source only: `git show 49970e337b2b72ed171a6a297fd7dec56ccdc85f:frontend/...`. The dirty main worktree was not used as source. Candidate selection is exactly the root-provided eight static class forms; ghost, danger, dynamic, bare `btn-sm`, and `btn-sm+field-h-md` are absent.

## Measured result

- Candidates: **34 nodes / 25 product files**.
- Existing tests that actually click the target callback and assert a state/API/navigation result: **10 nodes / 9 product files**.
- Uncovered: **24 nodes / 16 product files**.
- Import/reference matching alone was not counted. A test is covered only where the fixed test body operates the named target and checks its result.
- The ten covered targets need no new mirror tests. Their current suites should be rerun after migration.

## All 34: callback-level coverage audit

| # | target | existing class | callback | status | fixed-test evidence | result assertion |
|---:|---|---|---|---|---|---|
| 1 | `src/components/CommissionPanel.tsx:263` | `btn-secondary` | `onClose` | **COVERED** | `SharedButtonMigration.test.tsx:99-106` | clicks the panel close button and asserts onClose once after the real panel API flow |
| 2 | `src/components/master-list-editor/MasterListEditor.tsx:209` | `btn-secondary btn-sm` | `() => startEdit(r)` | **COVERED** | `MasterSearchButtonMigration.test.tsx:79-96` | clicks common.edit, verifies populated edit, exact update, cancel and required guard |
| 3 | `src/pages/badges/BadgesPage.tsx:49` | `btn-primary field-h-md` | `() => setShowForm(true)` | **COVERED** | `FormActionButtonMigration.test.tsx:88-157` | opens real form via configured opener; payload/reset/close/focus/permission outcomes |
| 4 | `src/pages/buddy/BuddyPage.tsx:54` | `btn-primary field-h-md` | `() => setShowForm(true)` | **COVERED** | `FormActionButtonMigration.test.tsx:88-157` | opens real form via configured opener; payload/reset/close/focus/permission outcomes |
| 5 | `src/pages/integrations/CarrierCredentialForm.tsx:136` | `btn-secondary` | `onCancel` | **UNCOVERED** | `—` | — |
| 6 | `src/pages/integrations/CarrierIntegrationPage.tsx:205` | `btn-secondary` | `() => openEdit(env)` | **UNCOVERED** | `—` | — |
| 7 | `src/pages/integrations/CarrierIntegrationPage.tsx:276` | `btn-secondary` | `() => openEdit(env)` | **UNCOVERED** | `—` | — |
| 8 | `src/pages/integrations/FedexEtdSetupGuide.tsx:474` | `btn-primary` | `onOpenCredentialsTab` | **UNCOVERED** | `—` | — |
| 9 | `src/pages/inventory/InventoryPage.tsx:602` | `btn-secondary` | `() => setPage(Math.max(1, page - 1))` | **UNCOVERED** | `—` | — |
| 10 | `src/pages/inventory/InventoryPage.tsx:608` | `btn-secondary` | `() => setPage(Math.min(totalPages, page + 1))` | **UNCOVERED** | `—` | — |
| 11 | `src/pages/invoice-create/InvoiceCreatePage.tsx:223` | `btn-secondary` | `() => navigate("/management-center/tenant-profile")` | **UNCOVERED** | `—` | — |
| 12 | `src/pages/invoice-create/InvoiceCreatePage.tsx:271` | `btn-sm btn-primary` | `() => loadQuoteForEdit(q.id)` | **UNCOVERED** | `—` | — |
| 13 | `src/pages/invoice-create/InvoiceCreatePage.tsx:434` | `btn-secondary` | `() => navigate("/invoices")` | **UNCOVERED** | `—` | — |
| 14 | `src/pages/invoice-detail/InvoiceDetailPage.tsx:272` | `btn-secondary` | `() => setShowVoidForm(false)` | **UNCOVERED** | `—` | — |
| 15 | `src/pages/notifications/NotificationsPage.tsx:52` | `btn-primary field-h-md` | `() => setShowForm(true)` | **COVERED** | `FormActionButtonMigration.test.tsx:88-157` | opens real form via configured opener; payload/reset/close/focus/permission outcomes |
| 16 | `src/pages/orders/OrdersPage.tsx:48` | `btn-primary field-h-md` | `() => { setShowForm(true); setEditId(null); setForm(emptyForm); resetSelector(); }` | **COVERED** | `OrderLeadButtonMigration.test.tsx:47-112,154-159` | clicks new-order opener; verifies reset/selector/dialog/payload/reload/focus/permission |
| 17 | `src/pages/products/ProductEditPage.tsx:175` | `btn-secondary field-h-md` | `() => navigate(-1)` | **UNCOVERED** | `—` | — |
| 18 | `src/pages/products/ProductsPage.tsx:190` | `btn-primary` | `() => navigate("/admin/products/new")` | **UNCOVERED** | `—` | — |
| 19 | `src/pages/purchase-orders/PurchaseOrdersFormModal.tsx:134` | `btn-secondary` | `onClose` | **UNCOVERED** | `—` | — |
| 20 | `src/pages/purchase-orders/PurchaseOrdersPage.tsx:198` | `btn-primary field-h-md` | `() => { setPoInitial(null); setShowNewModal(true); }` | **UNCOVERED** | `—` | — |
| 21 | `src/pages/quote-create/QuoteCreatePage.tsx:267` | `btn-sm btn-secondary` | `() => setShowFedExModal(true)` | **UNCOVERED** | `—` | — |
| 22 | `src/pages/quote-create/QuoteCreatePage.tsx:282` | `btn-secondary` | `() => navigate("/quotes")` | **UNCOVERED** | `—` | — |
| 23 | `src/pages/quotes/QuotesPage.tsx:137` | `btn-primary field-h-md` | `() => navigate("/quotes/new")` | **UNCOVERED** | `—` | — |
| 24 | `src/pages/roles/RolesPage.tsx:404` | `btn-secondary` | `cancelEdits` | **UNCOVERED** | `—` | — |
| 25 | `src/pages/shifts/ShiftsPage.tsx:53` | `btn-primary field-h-md` | `() => setShowForm(true)` | **COVERED** | `FormActionButtonMigration.test.tsx:88-157` | opens real form via configured opener; payload/reset/close/focus/permission outcomes |
| 26 | `src/pages/staff-reports/StaffReportsPage.tsx:69` | `btn-primary field-h-md` | `() => setShowForm(true)` | **COVERED** | `StaffReportFormButtonMigration.test.tsx:89-189` | openForm clicks add trigger; payload/reset/cancel/X/Escape/focus/permission contracts |
| 27 | `src/pages/super-admin/DexTab.tsx:173` | `btn-secondary` | `() => startEdit(it)` | **UNCOVERED** | `—` | — |
| 28 | `src/pages/super-admin/DexTab.tsx:206` | `btn-secondary` | `load` | **UNCOVERED** | `—` | — |
| 29 | `src/pages/super-admin/DexTab.tsx:324` | `btn-secondary` | `() => setEditing(null)` | **UNCOVERED** | `—` | — |
| 30 | `src/pages/super-admin/KnowledgeAliasesTab.tsx:339` | `btn-secondary btn-sm` | `() => loadRules(ruleSearch)` | **COVERED** | `RoleKnowledgeButtonMigration.test.tsx:153-164` | clicks rules search button and asserts exact filtered GET and post-success same-filter reload |
| 31 | `src/pages/super-admin/KnowledgeAliasesTab.tsx:417` | `btn-secondary btn-sm` | `() => loadAliases(aliasSearch)` | **COVERED** | `RoleKnowledgeButtonMigration.test.tsx:153-164` | clicks aliases search button and asserts exact filtered GET and post-success same-filter reload |
| 32 | `src/pages/super-admin/LLMBudgetTab.tsx:148` | `btn-secondary` | `() => startEdit(b)` | **UNCOVERED** | `—` | — |
| 33 | `src/pages/super-admin/TcgSeriesTab.tsx:197` | `btn-secondary` | `() => setShowTypeManager((v) => !v)` | **UNCOVERED** | `—` | — |
| 34 | `src/pages/super-admin/TcgSeriesTab.tsx:359` | `btn-secondary` | `() => startEdit(it)` | **UNCOVERED** | `—` | — |

## Why 24 remain uncovered

`git grep` at the fixed commit found no direct test import or target operation for Carrier credentials/integration, FedEx ETD guide, Inventory, invoice create/detail, Products, purchase orders, quote create/list, Dex, LLM budget, or TCG series. RolesPage is imported by RoleKnowledge tests, but candidate `RolesPage:404 cancelEdits` is not operated there: existing `common.cancel` operations close role/assignment Modals, while `roles.cancelChanges` restores permission edits. It is therefore uncovered.

## Minimum meaningful added regression plan

Use **three new real-component suites**. This is the smallest coherent split that avoids one fixture spanning unrelated API domains and avoids 24 one-assert mirror tests.

### 1. `IntegrationLaunchButtonMigration.test.tsx` — 4 nodes / 3 products

Products: `CarrierCredentialForm.tsx:136`; `CarrierIntegrationPage.tsx:205,276`; `FedexEtdSetupGuide.tsx:474`.

Parameterized contracts:

- Carrier credential cancel: render the real form with `busy=false/true`; click the exact cancel control; assert `onCancel` once when enabled and zero when disabled, explicit/implicit type unchanged, no API call.
- Carrier environment edit pair: render both environments, click each concrete opener, assert the editor receives the corresponding environment, busy disables both and prevents state change. Do not assert only dialog truthiness.
- FedEx credentials-tab callback: render the real guide at the step exposing the control, click, assert `onOpenCredentialsTab` exactly once and no API/write. Preserve explicit `type=button`.

### 2. `CommerceNavigationButtonMigration.test.tsx` — 11 nodes / 7 products

Products: `InventoryPage.tsx:602,608`; `InvoiceCreatePage.tsx:223,271,434`; `InvoiceDetailPage.tsx:272`; `ProductEditPage.tsx:175`; `ProductsPage.tsx:190`; `QuoteCreatePage.tsx:267,282`; `QuotesPage.tsx:137`.

Contracts, grouped rather than mirrored per tag:

- Inventory pagination: mock real `/inventory` responses for at least two pages; assert prev disabled at page 1, next click issues exact page-2 GET, loading disables both, page-2 prev returns exact page-1 GET, last-page next is inert.
- Router navigation table: profile settings, invoices cancel, product back, new product, quote cancel, new quote. Use MemoryRouter history/location probes and assert exact destination or `navigate(-1)`, plus disabled `saving` on ProductEdit. One parameterized navigation test can cover six nodes.
- Invoice quote reload: operate `loadQuoteForEdit(q.id)` through the real row control; assert exact GET(s), form/source quote state populated, `saving` disables the control and prevents a duplicate call, and rejection state is visible. This is the only target in the 34 whose named callback directly loads a selected record.
- Invoice detail void cancel: first open the void form through its existing non-target opener/setup, then click target line 272 and assert the form closes with zero action API calls.
- Quote FedEx launcher: fill only prerequisites necessary to expose it, click line 267, assert the named FedEx dialog opens and cancel produces zero quote/FedEx writes.

### 3. `PurchaseAdminEditorButtonMigration.test.tsx` — 9 nodes / 6 products

Products: `PurchaseOrdersFormModal.tsx:134`; `PurchaseOrdersPage.tsx:198`; `RolesPage.tsx:404`; `DexTab.tsx:173,206,324`; `LLMBudgetTab.tsx:148`; `TcgSeriesTab.tsx:197,359`.

Contracts:

- Purchase order close/new pair: new opener must clear `poInitial` and open a blank form; close must call onClose only when not `saving`, remain disabled/inert while saving, and issue zero POST/PATCH.
- Role permission cancel: render real roles/permissions, change an actual permission to make dirty, assert cancel becomes enabled, click `roles.cancelChanges`, verify checkbox restored to the server baseline, cancel/save disabled again, and PUT count remains zero. Existing Modal cancel tests do not cover this.
- Dex: edit opener populates selected record; reload invokes the exact list GET and updates displayed data/error; editor cancel clears editing with zero write. These three can share one fixture and exact starting GET counts.
- LLM budget edit: click a concrete budget edit control and assert the editor fields receive that record; zero write until submit.
- TCG series: type-manager toggle opens then closes the real manager; item edit populates exact series fields; neither action writes. Preserve explicit type on the toggle.

## Existing suites to rerun, without adding mirror cases

- `SharedButtonMigration.test.tsx`: Commission close target.
- `MasterSearchButtonMigration.test.tsx`: MasterList edit target.
- `FormActionButtonMigration.test.tsx`: Badges/Buddy/Notifications/Shifts openers.
- `OrderLeadButtonMigration.test.tsx`: Orders create opener.
- `StaffReportFormButtonMigration.test.tsx`: Staff report opener.
- `RoleKnowledgeButtonMigration.test.tsx`: both Knowledge search/reload targets.

Generic `Button.test.tsx` continues to prove native type/disabled/event forwarding. New page suites should not repeat class construction or ref forwarding.

## Disjoint two-Sol ownership proposal

### Sol 1 — commerce navigation (11 uncovered nodes)

Exclusive products (7):

- `InventoryPage.tsx`
- `InvoiceCreatePage.tsx`
- `InvoiceDetailPage.tsx`
- `ProductEditPage.tsx`
- `ProductsPage.tsx`
- `QuoteCreatePage.tsx`
- `QuotesPage.tsx`

Exclusive test: `CommerceNavigationButtonMigration.test.tsx`.

### Sol 2 — integrations, purchase, admin editors (13 uncovered nodes)

Exclusive products (9):

- `CarrierCredentialForm.tsx`
- `CarrierIntegrationPage.tsx`
- `FedexEtdSetupGuide.tsx`
- `PurchaseOrdersFormModal.tsx`
- `PurchaseOrdersPage.tsx`
- `RolesPage.tsx`
- `DexTab.tsx`
- `LLMBudgetTab.tsx`
- `TcgSeriesTab.tsx`

Exclusive tests (2):

- `IntegrationLaunchButtonMigration.test.tsx`
- `PurchaseAdminEditorButtonMigration.test.tsx`

### Already-covered product nodes (10) — assign product-only by file, tests read-only

These nine product files can be distributed to balance implementation counts, but neither Sol should edit their existing test suites solely to mirror conversion:

- CommissionPanel, MasterListEditor, BadgesPage, BuddyPage, NotificationsPage, OrdersPage, ShiftsPage, StaffReportsPage, KnowledgeAliasesTab.

If product ownership must be fully disjoint in one card, give these nine to Sol 1 (10 additional nodes): Sol 1 then owns 21 nodes/16 files plus one new test; Sol 2 owns 13 nodes/9 files plus two new tests. Sol 2 never edits Sol 1 products/tests, and each new test file has exactly one owner.

## Acceptance accounting

- Targeted DOM coverage after additions: 10 existing-covered + 24 newly-covered = **34/34 callbacks**.
- No test is counted for merely rendering a page, finding a class, or invoking a mocked page handler.
- Each deferred API is settled; permission absence is asserted only after permission GET settles; router assertions inspect resulting location; reload assertions use starting call counts and exact URLs.
- Preserve each node's type, handler, disabled, ARIA/testid/title, children, and event propagation. Do not introduce loading or new disabled behavior.
- Static audit: exactly these 34 legacy nodes convert; every non-target raw node remains byte-identical; shared Button/CSS and API/DB/i18n remain unchanged.
