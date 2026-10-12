# AS static primary/secondary callback contracts

- fixed commit: `49970e337b2b72ed171a6a297fd7dec56ccdc85f`
- source read method: `git archive` from fixed commit into `/tmp`; dirty working-tree product files were not read.
- exact fixed-commit AST recheck: 34/34 `file:line:className` matched.
- scope: eight allowed static primary/secondary class strings only; ghost/danger/bare/dynamic and btn-sm+field-h-md combination excluded before tracing.
- result: **34/34 INCLUDE, 25 files**. Callback bodies, parent callbacks, and modal mount behavior contain no direct write (POST/PUT/PATCH/DELETE) or external send for these clicks.

## Contracts

| Target | class / type | State and callback body | API caused by click | Permission / disabled | Cancellation and error contract |
|---|---|---|---|---|---|
| `frontend/src/components/CommissionPanel.tsx:263` | `btn-secondary` / `button` | invoke parent onClose; production parent sets assigning=null | none | permission: none; disabled: none | Modal also owns same onClose; callback evidence CommissionsPage:251-258; errors unchanged |
| `frontend/src/components/master-list-editor/MasterListEditor.tsx:209` | `btn-secondary btn-sm` / `implicit` | startEdit sets editId=r.id and copies name_ja/name_en into form | none | permission: none; disabled: none | no cancellation/error branch in callback; definition 71-74 |
| `frontend/src/pages/badges/BadgesPage.tsx:49` | `btn-primary field-h-md` / `implicit` | setShowForm(true) | none | permission: badges.manage gate at 47-50; disabled: none | Modal close/cancel set false; opener does not clear form/error |
| `frontend/src/pages/buddy/BuddyPage.tsx:54` | `btn-primary field-h-md` / `implicit` | setShowForm(true) | none | permission: buddy.manage gate at 52-55; disabled: none | Modal close/cancel set false; opener does not clear form/error |
| `frontend/src/pages/integrations/CarrierCredentialForm.tsx:136` | `btn-secondary` / `implicit` | invoke parent onCancel; parent sets editingEnv=null and error="" | none | permission: none; disabled: busy | not a form (update-form div); callback evidence CarrierIntegrationPage:178-187 |
| `frontend/src/pages/integrations/CarrierIntegrationPage.tsx:205` | `btn-secondary` / `implicit` | openEdit clears error and sets editingEnv=env | none | permission: none; disabled: busy | renders CarrierCredentialForm; definition 103-106 |
| `frontend/src/pages/integrations/CarrierIntegrationPage.tsx:276` | `btn-secondary` / `implicit` | openEdit clears error and sets editingEnv=env | none | permission: none; disabled: busy | renders CarrierCredentialForm; definition 103-106 |
| `frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:474` | `btn-primary` / `button` | invoke parent onOpenCredentialsTab; routed use navigates to /management-center/integrations/${carrier} | none | permission: none; disabled: none | type=button; parent evidence CarrierSetupGuidePage:43-47; passthrough-only alternate component usage has no production caller found |
| `frontend/src/pages/inventory/InventoryPage.tsx:602` | `btn-secondary` / `implicit` | setPage(max(1,page-1)); page change reruns load effect | GET /inventory?page={page}&per_page={PER_PAGE}&sort={sortField}&order={sortDir} plus optional q/category/tcg_type/filter query | permission: none; disabled: page<=1 \|\| loading | load clears error, sets loading, catches fetchError, finally clears loading; load 148 onward |
| `frontend/src/pages/inventory/InventoryPage.tsx:608` | `btn-secondary` / `implicit` | setPage(min(totalPages,page+1)); page change reruns load effect | GET /inventory with same query contract as previous | permission: none; disabled: page>=totalPages \|\| loading | same load error/finally contract |
| `frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:223` | `btn-secondary` / `implicit` | navigate("/management-center/tenant-profile") | none | permission: none; disabled: none | headerAction outside invoice form; no cancel/error branch |
| `frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:271` | `btn-sm btn-primary` / `implicit` | clear error; saving=true; GET quote; populate company/contact/currency/items/sourceQuoteCode; mode=inventory | GET /quotes/${quoteId} | permission: quote list originates approved quotes load; no separate click permission gate found; disabled: saving | catch sets common.fetchError; finally saving=false; definition 138-168; button outside invoice submit form |
| `frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:434` | `btn-secondary` / `button` | navigate("/invoices") | none | permission: none; disabled: none | type=button cancel; no state reset/error branch |
| `frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx:272` | `btn-secondary` / `implicit` | setShowVoidForm(false) | none | permission: void UI gated by invoice status/permission outside this callback; disabled: none | does not clear voidReason or error |
| `frontend/src/pages/notifications/NotificationsPage.tsx:52` | `btn-primary field-h-md` / `implicit` | setShowForm(true) | none | permission: notifications.manage gate at 50-54; disabled: none | Modal close/cancel false; opener retains form/error |
| `frontend/src/pages/orders/OrdersPage.tsx:48` | `btn-primary field-h-md` / `implicit` | showForm=true; editId=null; form=emptyForm; reset companyId/contactId to null and selectorError="" | none | permission: orders.create gate at 46; disabled: none | OrdersFormModal has no API-on-open; resetSelector definition useOrdersState:249-253 |
| `frontend/src/pages/products/ProductEditPage.tsx:175` | `btn-secondary field-h-md` / `button` | navigate(-1) | none | permission: none; disabled: saving | type=button; no reset/error branch |
| `frontend/src/pages/products/ProductsPage.tsx:190` | `btn-primary` / `button` | navigate("/admin/products/new") | none | permission: products.create gate at 189; disabled: none | type=button; no state/error branch |
| `frontend/src/pages/purchase-orders/PurchaseOrdersFormModal.tsx:134` | `btn-secondary` / `button` | invoke parent onClose; parent sets showNewModal=false | none | permission: none; disabled: saving | type=button; leaves local form state until next open resets it; parent PurchaseOrdersPage:182-188 |
| `frontend/src/pages/purchase-orders/PurchaseOrdersPage.tsx:198` | `btn-primary field-h-md` / `implicit` | poInitial=null; showNewModal=true; modal open resets fields and loads supplier catalog | GET /suppliers/catalog | permission: purchase_orders.create gate at 197; disabled: none | GET catch sets common.fetchError; modal lines 44-67 |
| `frontend/src/pages/quote-create/QuoteCreatePage.tsx:267` | `btn-sm btn-secondary` / `button` | setShowFedExModal(true) | none on open | permission: none; disabled: none | type=button; FedEx modal POST /shipping/calculate occurs only on its separate quote action, not opener |
| `frontend/src/pages/quote-create/QuoteCreatePage.tsx:282` | `btn-secondary` / `button` | navigate("/quotes") | none | permission: none; disabled: none | type=button; no state reset/error branch |
| `frontend/src/pages/quotes/QuotesPage.tsx:137` | `btn-primary field-h-md` / `implicit` | navigate("/quotes/new") | none | permission: quotes.create gate at 136; disabled: none | no state/error branch |
| `frontend/src/pages/roles/RolesPage.tsx:404` | `btn-secondary` / `implicit` | replace editedPermIds with copy of originalPermIds | none | permission: visible in selected-role actions; save additionally checks canEditPerms; disabled: !dirty \|\| savingPerms | no confirmation/error mutation; definition 243-244 |
| `frontend/src/pages/shifts/ShiftsPage.tsx:53` | `btn-primary field-h-md` / `implicit` | setShowForm(true) | none | permission: shifts.manage gate at 52; disabled: none | Modal close/cancel false; opener retains form/error |
| `frontend/src/pages/staff-reports/StaffReportsPage.tsx:69` | `btn-primary field-h-md` / `implicit` | setShowForm(true) | none | permission: staff_reports.create gate at 68; disabled: none | Modal close/cancel false; opener retains form/error |
| `frontend/src/pages/super-admin/DexTab.tsx:173` | `btn-secondary` / `implicit` | startEdit sets editing=item and copies all editable fields to editValues | none | permission: none; disabled: none | definition 71-80; no error reset |
| `frontend/src/pages/super-admin/DexTab.tsx:206` | `btn-secondary` / `implicit` | derive encoded optional search query; GET; replace items | GET /super-admin/dex/${kind}?q=${encodeURIComponent(search)} (query omitted when empty) | permission: none; disabled: none | catch sets common.fetchError; no loading/disabled state; definition 56-64 |
| `frontend/src/pages/super-admin/DexTab.tsx:324` | `btn-secondary` / `button` | setEditing(null) | none | permission: none; disabled: none | type=button cancel; editValues/error retained |
| `frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:339` | `btn-secondary btn-sm` / `implicit` | loadRules(ruleSearch); encoded optional query; replace rules | GET /super-admin/knowledge?q=${encodeURIComponent(ruleSearch)} (query omitted when empty) | permission: none; disabled: none | catch sets ruleError common.fetchError; no loading/disabled state; 170-179 |
| `frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:417` | `btn-secondary btn-sm` / `implicit` | loadAliases(aliasSearch); encoded optional query; replace aliases | GET /super-admin/aliases?q=${encodeURIComponent(aliasSearch)} (query omitted when empty) | permission: none; disabled: none | catch sets aliasError common.fetchError; no loading/disabled state; 181-190 |
| `frontend/src/pages/super-admin/LLMBudgetTab.tsx:148` | `btn-secondary` / `button` | startEdit copies tenant_id,budget,hard_stop,notify_admin; clears info and error | none | permission: none; disabled: none | definition 70-79 |
| `frontend/src/pages/super-admin/TcgSeriesTab.tsx:197` | `btn-secondary` / `button` | toggle showTypeManager boolean | none | permission: none; disabled: none | type=button; types were loaded independently on mount; no callback error branch |
| `frontend/src/pages/super-admin/TcgSeriesTab.tsx:359` | `btn-secondary` / `implicit` | startEdit sets editId and copies tcg_type,series_code,names,release_date,category into form | none | permission: none; disabled: none | definition 123-133; no error reset |

## GET-only click paths

- `InventoryPage:602,608`: state change reruns the existing list load: `GET /inventory` with page/per_page/sort/order and the existing optional filter query. Error/loading behavior remains in `load`.
- `InvoiceCreatePage:271`: `GET /quotes/${quoteId}`; populates the invoice draft. It is outside the submit form and performs no invoice write.
- `PurchaseOrdersPage:198`: opening `PurchaseOrdersFormModal` triggers `GET /suppliers/catalog`; the opener performs no create request.
- `DexTab:206`: `GET /super-admin/dex/${kind}` with optional encoded `q`.
- `KnowledgeAliasesTab:339,417`: `GET /super-admin/knowledge` and `GET /super-admin/aliases`, each with optional encoded `q`.

The other 27 clicks perform only local state changes, parent callback state changes, or React Router navigation. `QuoteCreatePage:267` only opens the FedEx modal; `/shipping/calculate` remains behind a separate button. `FedexEtdSetupGuide:474` resolves to internal navigation through its production caller.

## Contract-sensitive observations

- Preserve implicit `type` where recorded. No candidate with implicit type is nested in a submit form in a way that adds a write; `InvoiceCreatePage:271` is outside its invoice form, and `CarrierCredentialForm` uses a `div.update-form`, not a form.
- Preserve permission placement for badges, buddy, notifications, orders, products, purchase orders, quotes, shifts, and staff reports. The Button replacement must stay inside the same conditional expression.
- Preserve every existing disabled expression exactly. Do not convert it to `loading`, because Button would add `aria-busy` and replace children, changing the contract.
- Modal launchers intentionally retain existing form/error values unless their callback explicitly resets them. The table records reset behavior; adding resets is out of scope.
- No candidate changes API, query encoding, i18n, CSS tokens, or navigation destinations.

## Fixed evidence

- `frontend/src/components/CommissionPanel.tsx` `a225570d80f5e8eb9cba69e8c8d0ad62423b26492d14fb2c141de64344deac37`
- `frontend/src/components/master-list-editor/MasterListEditor.tsx` `7b3f111341ac68e445e534a4d999e691eed027f65881fa700eb74e985c4c9293`
- `frontend/src/pages/badges/BadgesPage.tsx` `bb08f3ff91f36097ac7e574b827dfc7710f857ca37d685138e2568ea11ed3e8f`
- `frontend/src/pages/buddy/BuddyPage.tsx` `7982207598efba033ebb31cbe293fadad36c38cf87d1b5519a9cf169e6233505`
- `frontend/src/pages/integrations/CarrierCredentialForm.tsx` `50ff2a0db2459f990b9c48bbd816913da6e477a00a2e9c1d4f806a893c116ec8`
- `frontend/src/pages/integrations/CarrierIntegrationPage.tsx` `e174e54687dc2202f018dc7354ffca77ffc580f6a05d898874713945f4d23bab`
- `frontend/src/pages/integrations/FedexEtdSetupGuide.tsx` `8b342bf3bf133409403222ded31cb2211ccfa98a0791438b13facda10e4d82d4`
- `frontend/src/pages/inventory/InventoryPage.tsx` `b3fdeea6e653d1a5e1f3b676e241a73b355930a5dd7275112c27dd279a0e9d09`
- `frontend/src/pages/invoice-create/InvoiceCreatePage.tsx` `1eeaa518348aef6c96267e2360ecb97929a1dbd37d4f864ccb3d36bc731d8229`
- `frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx` `c410f2b36e2aa1c20a48ea4f51f3e551124abba60bef71edaec55cb04036a90f`
- `frontend/src/pages/notifications/NotificationsPage.tsx` `9c8dfa7fa1dba33c1835e64af45898ba7d8851393c2bb3227b6ca04471289897`
- `frontend/src/pages/orders/OrdersPage.tsx` `3ade03e176ed81e02033f193e477d64a99d8a2c022152aba0f9bd782eaa690b2`
- `frontend/src/pages/products/ProductEditPage.tsx` `41e0e77f5b48b59a1178ca32b125a3cd63df644b9f7304f0c474bf3126c0714d`
- `frontend/src/pages/products/ProductsPage.tsx` `556157df2f5686af40173ab4d2d503478543e5cf00092882b989e11c8ea83305`
- `frontend/src/pages/purchase-orders/PurchaseOrdersFormModal.tsx` `680d951af798be84d6457fbce5fbb3c6d5d331a5e452f56aa6d7b791570ebe55`
- `frontend/src/pages/purchase-orders/PurchaseOrdersPage.tsx` `6a43185caca83c2e78137b9442d9575124af9e3bc2461e12d308e78e4f2ec0b5`
- `frontend/src/pages/quote-create/QuoteCreatePage.tsx` `01a9046f739a43d564fb7b1c0a6deefcaa0433da7a302c43caccded7f749a672`
- `frontend/src/pages/quotes/QuotesPage.tsx` `f9d6733f1b1627a7b5c2547434a2810f066db1b3dd56ef3fd18baaa01c012f2f`
- `frontend/src/pages/roles/RolesPage.tsx` `809da1034f480b5d8321c5e25a25b5044a837a56b93f01a83f62f4dc108e4fd8`
- `frontend/src/pages/shifts/ShiftsPage.tsx` `bef46eedc7f9c8c0a97639e7f1234c7dd7de77102cfd64e163f60cb76070899a`
- `frontend/src/pages/staff-reports/StaffReportsPage.tsx` `c5fa6f5af93ef99fca806c1af66602a25f420ba6c06febf1673766ee5f7dda42`
- `frontend/src/pages/super-admin/DexTab.tsx` `895655551e1bc1cf7b2c7ec933b7839ab6ec14e09fc222ff496b451cab19a7e9`
- `frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx` `e65a9e21955dbaf53a441c6294a06a97fe6647c95934cd866cbbe76371c00b98`
- `frontend/src/pages/super-admin/LLMBudgetTab.tsx` `8a51b9c2344a9285d3d0b7274637548de6cb4f480f825b40fc9954e60618c7cc`
- `frontend/src/pages/super-admin/TcgSeriesTab.tsx` `a7a69efd7b8b01ee6c77bdb14523ff43931bbd6bfb9180da02149b606fcd6470`
