# AT admin/form button backend trace and test plan

Fixed evidence: commit `a1cd9ea379cc7d85b797cca6b1cc092192296bc3`, read with `git show`/`git grep`. Planned ownership is seven nodes in six products: `ProfileSection`, `CompanyBasicTab`, `CompanyChannelsTab`, `PurchaseOrdersFormModal`, Dex edit Save only, and TCG type/series submit. No product was edited.

## Backend trace

| Frontend control / endpoint | Server authorization | DB scope and persistent effects | External side effect finding |
|---|---|---|---|
| `ProfileSection.tsx:124` → `PATCH /staff/me/profile` | `staff.py:275-290`: authenticated `get_current_tenant` + `get_current_user`; no admin permission, identifies the current staff row by authenticated email; only `_PROFILE_UPDATABLE` seven profile fields pass | Tenant `staff` row update, audit log, commit, tenant-context reset, then reread. It cannot change email/role/status. | No outbound client, message, payment, identity-provider mutation, cache invalidation, or public-table write in `staff.py:275-344`. Authentication is read to identify self. |
| `CompanyBasicTab.tsx:97` and `CompanyChannelsTab.tsx:37` → `PATCH /companies/{id}` | `companies.py:495-505`: server `require_permission("customers.update")`. UI `CompanyDetailPage.tsx:34-37,124-179` independently uses `customers.update` to render the forms' Save buttons. Reload GET additionally requires `customers.view`. | Tenant `companies`; channels submit additionally replaces tenant sales-channel rows. The general endpoint snapshots company subtables for audit, records audit log, commits, resets tenant context, invalidates dashboard cache, and recomposes response. It reads/writes no public master for these two payloads. | No external HTTP/client, customer notification, billing, auth-provider change, or bulk operation in `update_company`. The shared endpoint can modify addresses/Discord when those keys are sent, but these handlers send only the exact basic payload or `{sales_channels}`. |
| `PurchaseOrdersFormModal.tsx:138` → `POST /purchase-orders` | `purchase_orders.py:158-165`: `require_permission("purchase_orders.create")`; UI opener owns the permission gate, while the reusable modal itself does not check permission. | Reads central `public.suppliers`. `_resolve_tenant_supplier_id` may copy one previously unseen active public supplier into tenant `suppliers`; then inserts tenant `purchase_orders` and `purchase_order_items`, audit log, commit, tenant-context reset, dashboard-cache invalidation. This is more than the visible PO row write and must be recorded in design. | The create handler does not call PDF/email functions even though the same router imports them for separate endpoints. No external HTTP, message delivery, payment, or auth-provider operation on create. |
| `DexTab.tsx:322` → `PATCH /super-admin/dex/{kind}/{id}` | `super_admin_dex.py:123-132`: `require_super_admin`; UI component has no local permission hook because it is hosted under the super-admin surface. | Direct shared/public master mutation: `public.pokemon_dex` or `public.trainer_dex`, allowlisted fields only, commit. No audit log/cache invalidation in this handler. This affects every tenant consuming the public master. | No outbound client call. The separate import endpoints have PokeAPI behavior, but the planned edit Save calls only `update_dex`; tests must select the edit Save and never import controls. |
| `TcgSeriesTab.tsx:244` → `POST /super-admin/tcg/types` | `super_admin_tcg.py:171-177`: `require_super_admin`; no local UI permission hook | Direct shared/public master insert into `public.type_master`; server generates `tcgtype_{MAX(id)+1}` when code absent; commit. No audit/cache action here. | No outbound client/message/payment/auth mutation. Shared cross-tenant master mutation remains material. |
| `TcgSeriesTab.tsx:327` → `POST /super-admin/tcg/series` or `PATCH /super-admin/tcg/series/{id}` | `super_admin_tcg.py:72-80,103-112`: `require_super_admin` | Direct shared/public `public.tcg_series_master` insert/update and commit. Empty update rejected; conflicts return 409. No audit/cache action here. | No outbound client/message/payment/auth mutation. Shared cross-tenant master mutation remains material. |

The last three product areas are locally testable through the mocked frontend `api`, but their production writes are shared master-data writes. That is a governance distinction, not a reason to weaken their payload/state tests.

## Proposed test ownership and fixtures

Create two focused suites so page fixtures and failure attribution stay bounded.

### A. `AccountCompanySaveButtonMigration.test.tsx` — Profile + Company Basic/Channels (3 nodes)

Use real `ProfileSection`, real `UiPrefsProvider`, real `CompanyDetailPage`, real `useCompanyDetail`, router and permissions. Mock only the `api` module and Auth boundary. Do not mock `patchMyProfile`, `useUiPrefs`, `useCompanyDetail`, the tabs, or submit handlers.

Profile fixture:

- Render `<UiPrefsProvider><ProfileSection /></UiPrefsProvider>` with Auth boundary returning a non-null user and `loading=false`.
- Because both provider and Profile independently GET `/staff/me`, await the initial calls and return a complete staff object including `id`, names, email, phone and `ui_preferences`. This proves the real provider path; rendering without the provider would silently use the forbidden no-op `refresh` at `UiPrefsContext.tsx:154-167`.
- Before submit record exact `/staff/me` GET count. After `PATCH /staff/me/profile` resolves, assert the provider's real `refresh()` causes exactly one additional `/staff/me` GET before success is accepted.

Company fixture:

- Render real route `/companies/41` with a complete `Company` response, `/companies/41/contacts`, and settled `/me/permissions` response.
- Give `customers.view` + `customers.update` for positive cases. Wait for initial company, contacts, and permission reads before operating Save. Switch to Channels through the real tab control.
- For denial, use only `customers.view`, wait for the permissions request and initial page load, then assert both Basic and Channels Save controls are absent. Clear or baseline API call counts before the denial render to prevent history-based false positives.

Acceptance cases:

1. **Profile exact payload, success refresh and normalization.** Populate all seven editable values including surrounding spaces and clear phone. Submit the real form. Assert exactly `PATCH /staff/me/profile` with all seven keys, preserving entered strings and `phone:null`; pending Save disabled; second click/submit produces no second PATCH; resolve, then exact additional `/staff/me` refresh and success UI. This also proves `patchMyProfile` is real.
2. **Profile failure retention/retry.** Reject first PATCH; assert error, every representative input retained, Save unlocked, no refresh increment. Retry, assert the same full payload, resolve, assert refresh/success. Settle every deferred promise.
3. **Company Basic required/dirty/permission guards.** Initial Save disabled; blank required name is blocked by native validation at zero PATCH; edit name makes it enabled. Denied `customers.update` removes the control after permission settlement.
4. **Company Basic exact 14-key payload and successful reload.** Fill values that demonstrate `name.trim()`, empty-to-null, numeric monthly-frequency parsing, fallback status and raw amount strings. Assert full equality, not partial matching. During pending assert disabled and a repeated submit makes no extra PATCH. On resolve assert exact increments for both `/companies/41` and `/companies/41/contacts`, returned server state replaces the form, dirty becomes false and Save disables again.
5. **Company Basic failure retention/retry.** Reject first PATCH, verify error, edited field preserved, button unlocks and no reload increment; retry exact same payload, resolve and verify reload.
6. **Channels exact normalization/success.** Real Channels tab, enter a string containing ASCII comma, Japanese `、`, full-width `，`, whitespace and empty segments. Assert `PATCH /companies/41`, `{sales_channels:[...]}` exactly. Pending disables and blocks duplicate; resolve and assert both reload GET increments plus server-returned channel text and disabled clean Save.
7. **Channels failure retention/retry.** Reject, assert error and exact typed text retained, no reload; retry and settle success.

### B. `AdminMasterSaveButtonMigration.test.tsx` — PO + Dex + TCG (4 nodes)

Reuse real `PurchaseOrdersFormModal`, `DexTab`, `TcgSeriesTab`, i18n and API mock patterns from AS `PurchaseAdminEditorButtonMigration.test.tsx`. Mock API/Auth boundaries only. Do not replace callbacks inside Dex/TCG or mock their component logic.

Acceptance cases:

1. **PO required guards.** Submit with no supplier, then with supplier but invalid/empty item; assert visible guard and zero POST. The native supplier `required` and handler item guard are separate observations.
2. **PO exact full payload, pending and success callbacks.** Use supplier, notes and at least two items to prove mapping. Assert exact `{supplier_id,notes,items:[{product_id,quantity,unit_cost},...]}`. Save and existing Cancel both disabled during pending; repeated Save and Cancel are inert. Resolve and assert `onCreated` once then `onClose` once. The real page separately owns the permission gate; add a real `PurchaseOrdersPage` denial case only if this suite also claims opener authorization.
3. **PO failure retention/retry.** Reject; assert dialog stays open, supplier/notes/items retained, controls unlock, callbacks remain zero. Retry exact payload and settle success.
4. **Dex pokemon exact PATCH/success reload.** Load a concrete entry, operate its real edit control, change all exposed edit fields, click only the edit-form Save. Assert exact `PATCH /super-admin/dex/pokemon/{id}` with the complete `editValues` object, then exact filtered/unfiltered GET increment, editor closed and new server row displayed.
5. **Dex trainer branch.** Change real kind selector to trainer, await `/super-admin/dex/trainer`, edit/save and assert trainer payload includes `era` and not pokemon-only fields. This is necessary because one migrated button dispatches two schema branches.
6. **Dex failure retention/retry and pending semantics.** Reject and verify editor/values/error retained; retry succeeds. Product has no saving state or disabled guard, so a deferred PATCH leaves Save enabled and a second click dispatches a second PATCH. Assert that current behavior explicitly and settle both promises; do not invent a guard as part of migration.
7. **TCG type required/exact POST/reload.** Open the real type manager. Empty required `name_ja` gives zero POST. Submit spaced names and assert exact payload `{name_ja:trimmed,name_en:trimmed|null,sort_order:100,is_active:true}`; success exact `/super-admin/tcg/types` increment and form reset. Failure retains inputs and retry works.
8. **TCG series create and edit exact payloads.** Required empty `series_code`/`name_ja` yield zero write. Create asserts full six-key normalized payload and filtered GET increment/reset. Open a real series with Edit, submit and assert exact `PATCH /super-admin/tcg/series/{id}`, then reload/reset.
9. **TCG failure and pending semantics.** For both type and series, rejection retains values and retry succeeds. Neither handler has a pending flag/disabled guard; deferred repeat clicks currently issue repeated requests. Assert enabled/no `aria-busy`, exact additional call count, and settle every deferred request without changing production behavior.
10. **Super-admin authorization evidence.** Frontend components contain no permission hook, so unit tests cannot honestly prove route authorization by checking hidden buttons. Record server `require_super_admin` as the authorization evidence and keep frontend tests focused on handler contracts. Do not mock a fictitious UI denial state.

## Validation boundaries

- Exact payload assertions must enumerate every key; no `objectContaining` for save writes.
- Each success that calls a reload must baseline the initial GET count and assert the exact endpoint increases by one.
- Failure cases must show input retention and no success reload/callback.
- Pending cases must reflect existing product behavior. Profile, Company and PO disable; Dex and TCG currently allow repeat submission.
- Permission assertions must wait for the real permissions response. Super-admin server authorization is evidenced from the backend route because these tab components have no local gate.
- All deferred promises resolve or reject inside `act`; no unresolved work, timeout extension, skips, or handler mocks.
