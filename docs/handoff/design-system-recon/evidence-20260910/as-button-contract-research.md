# AS native button contract research

Read-only source: `/Users/tanizawashingo/worktrees/salesanchor/release-frontend-button-batch-result` (frontend aligned through `origin/main` 157cd6799 per assignment). No product/docs/git edits.

## 1. Shared Button versus legacy CSS: contracts that a migration must preserve

### DOM/type/event contract

- `frontend/src/components/Button.tsx:38` accepts native `ButtonHTMLAttributes` except appearance-owned `className`/`style`; `:61-83` forwards remaining native props to the same `<button>`.
- It does **not** invent a `type` (`:75-83`). An omitted type therefore keeps native `button.type === "submit"` inside/for a form. Preserve the source's explicit or omitted type byte-for-contract; do not add `type="button"` merely because the handler currently uses `onClick`.
- `disabled` becomes `disabled || loading` and `loading` also emits `aria-busy` (`:79-80`). A mechanical legacy migration must not introduce `loading`; doing so changes repeat-click/pending behavior.
- Native event identity and propagation remain available because props are spread onto the same element. Existing proof: `frontend/src/components/Button.test.tsx:23-50` covers omitted/explicit type and form submit; `:52-61` covers `currentTarget` and `stopPropagation`; `:64-94` covers disabled/loading callback suppression.
- Default props are `variant="primary"`, `size="md"` (`Button.tsx:49-53`). Every migrated legacy button should state the intended variant/size explicitly so a source `btn-sm`, danger, secondary, or ghost contract cannot silently become primary/md.

### Variant/focus/disabled contract

- Variants are exactly primary/secondary/ghost/danger/outline/tab (`Button.tsx:20`, class mapping `:40-47`). Tab alone emits `aria-pressed` from `active` (`:63,68,81`). A plain screen-switch button must not be changed to `variant="tab"` unless it already has a selected-state contract that should become `aria-pressed`.
- Shared primary/secondary/ghost/outline/danger colors and hover/active states are centralized in `Button.css:32-93`. All shared buttons get the same `:focus-visible` outline (`:95-98`) and disabled opacity/cursor (`:100-103`). Legacy CSS has explicit focus only for `.btn-outline` (`components.css:127-143`); `.btn-primary`, `.btn-secondary`, `.btn-sm`, `.btn-danger`, `.btn-ghost` have no shared explicit focus rule (`:54-122`). Thus migration intentionally adopts the shared focus treatment; verify focusability and focus return, not computed-pixel equality.
- Legacy `.btn-primary:disabled` changes background plus opacity `--opacity-muted` 0.7 (`components.css:65-66`, `tokens.css:259`). Shared disabled leaves variant background and uses `--opacity-disabled` 0.6 (`Button.css:100-103`, `tokens.css:264`). This is a source-proven visual difference. Behavioral tests should assert native `disabled` and suppressed handler/API, not the old color.
- `layoutClassName` is placement-only (`Button.tsx:34-35,72`); `className` and `style` are intentionally rejected (`:38`, compile-time examples in `Button.test.tsx:112-118`). A legacy inline appearance override is not mechanically transferable and must be excluded or separately designed.

### Size contract: do not claim pixel equivalence

- Shared md: min-height `--field-h-md` = 36px, padding 8px/20px, base font, 1px transparent border, border-box, radius `--comp-btn-radius` = 6px (`Button.css:2-17`; `tokens.css:68-72,163,449`).
- Shared sm: min-height 28px, padding 4px/12px, xs font (`Button.css:20-24`; `tokens.css:68,70,162`).
- Legacy `.btn-sm`: **no min-height and no box-sizing**, padding 4px/10px, xs font, radius 3px (`components.css:95-103`; tokens `:68,84,88`). Its primary/secondary/danger combinations retain that padding/font through `components.css:149-163`.
- `.field-h-md` contributes min-height 36px and border-box only (`components/field-size.css:6-9`). A raw `btn-sm field-h-md` therefore has xs font + 4/10 padding + 36px min-height. `Button size="sm" layoutClassName="field-h-md"` keeps xs font and 36px minimum but changes horizontal padding 10→12, radius 3→6 and introduces a 1px transparent border. `Button size="md"` keeps 36px minimum but changes font/padding more substantially. Record this as adoption of the shared mold, never exact rendering equivalence.
- Mobile shared buttons get 44px minimum height (`Button.css:134-147`), while legacy classes have no equivalent rule in the inspected legacy block. DOM/unit tests cannot prove this layout; CSS source comparison or browser viewport verification is needed when visual parity is an acceptance item.

## 2. Representative next-batch candidates and verification plans

### A. RolesPage: Modal launch/close plus in-page role switching and permission saving

Candidate raw controls:

- create opener `frontend/src/pages/roles/RolesPage.tsx:339-341` (`btn-primary btn-sm`, permission `roles.create`);
- role-row screen switch `:343-360` (`role-item`, calls `selectRole`);
- assignment Modal opener `:365-368` (`btn-secondary btn-block`, permission `roles.assign`);
- edit/delete openers `:395-401` (`btn-sm`, `btn-sm btn-danger`, gated by `canEditPerms`, `roles.delete`);
- permission cancel/save `:404-409`, disabled from `dirty`, `savingPerms`, and `canEditPerms`.

Event/state/API chain:

- Create calls `openCreateRole`, which clears edit id, restores `emptyRoleForm`, opens Modal (`:253-257`). Edit copies the selected role with the existing null-color fallback and opens (`:258-267`). Submit selects exact POST `/roles` or PATCH `/roles/:id`, then GET `/roles` and closes only on success (`:268-287`).
- Role-row click calls `selectRole`; dirty state requires `window.confirm`, rejection keeps the old selection, acceptance changes `selectedRoleId` (`:246-250,354-358`). This is a screen-switch contract distinct from a form submit.
- Permission save sends exact PUT `/roles/:selectedRoleId/permissions` with `permission_ids`, then copies edited to original; `savingPerms` is reset in `finally` (`:230-240`). Cancel restores the original Set without an API call (`:243-244`).
- Assignment save sends PUT `/users/:targetUserId/roles`, then closes and resets id/selection; close also resets without writing (`:303-326`). Modal itself supplies Escape, overlay/X close, first focus, trap, and trigger restoration (`frontend/src/components/Modal.tsx:49-110,112-151`).

Verification:

1. Render the real page with only API mocked and permissions resolved asynchronously. Before permission response, do not assert absence; after `/me/permissions` settles, assert each gated opener present/absent.
2. For each opener, focus it, click, assert real dialog name, first focus on Modal close button, X/Escape/cancel close and trigger focus restoration. Assert zero POST/PATCH/PUT/DELETE for close paths.
3. For role switching, create two roles and dirty a real permission checkbox. Stub `window.confirm` false then true; assert selected heading/checkbox state stays then switches. A class-only assertion on `active` is insufficient.
4. For save/cancel, assert native disabled before dirty, enabled after actual checkbox change, exact PUT payload, repeat click blocked only if current logic blocks it, and post-success baseline/cancel state. Do not add `loading` to make a currently unlocked button lock.
5. Reuse `frontend/src/components/RoleKnowledgeButtonMigration.test.tsx` for real Modal create/edit/assignment, permission settlement, exact payload, X/Escape/focus and async patterns. Extend it for role-row switch and permission PUT rather than mocking page logic. `Button.test.tsx:23-94` already proves generic native forwarding and should not be duplicated.

Migration classification: primary/secondary/danger cases are mechanically expressible. `btn-block` needs evidence that `fullWidth` is equivalent before replacing. `role-item` has custom dynamic class/style and is **not** a simple Button migration under the no-className/no-style API.

### B. InventoryPage: toolbar toggle/search/reset and pagination reload

Candidate raw controls:

- search `frontend/src/pages/inventory/InventoryPage.tsx:394-396`: explicit `type="button"`, `btn-primary btn-sm field-h-md`;
- reset `:397-399`: explicit button, secondary/sm/field-h-md;
- filter panel toggle `:400-409`: dynamic primary/secondary class plus `aria-expanded`, `aria-pressed`;
- previous/next `:602-610`: secondary with disabled boundary/loading logic;
- sort header `:336-365`: custom inline style, exclude from mechanical Button migration.

Event/state/API chain:

- Search input changes `searchQ` and page=1, Enter and click both call `runSearch`, which copies raw input to `debouncedQ` and page=1 (`:382-393`, handler `:297-300`). `load` trims q, builds exact `/inventory?...` with page/per_page/sort/order/category/tab/filter values (`:148-180`).
- Reset clears search/category, sets sort name/asc and page 1 while deliberately preserving user detail filters (`:287-296`). Test the resulting GET parameters; checking only empty input would miss the sort/page contract.
- Filter toggle changes only panel visibility (`:400-409`); it already exposes expanded/pressed state. Preserve both ARIA props when converting. Filter setting persistence separately PATCHes `/me/inventory-filters` after 250ms (`:250-267`), so fake timers must advance and pending promises must settle.
- Prev/next change page within `[1,totalPages]` and are disabled at bounds or while loading (`:602-610`); page change triggers the load callback. Verify exact next/previous GET and no call on disabled click.

Verification:

1. Mock `/inventory` by URL and reject all unexpected writes/network. Cover click and Enter, leading/trailing whitespace encoding, reset to exact `page=1&sort=name&order=asc`, and detail-filter preservation.
2. Filter toggle: assert same element keeps explicit `type=button`, `aria-expanded` tracks panel, `aria-pressed` continues to describe enabled filter state (these are different states). Do not replace it with `variant="tab"`; tab would introduce Button-owned `aria-pressed` semantics and can overwrite the caller value depending on spread order.
3. Pagination: return total > 50, assert prev disabled on page 1, next GET page 2, controls disabled during a deferred GET, bounds suppress calls, failure surfaces `inventory-error` and controls recover.
4. No matching inventory action test was found by `rg` for the four test ids. This candidate needs a new real-page suite. Use stable `data-testid`s already present and assert URL/state, not implementation setter calls.

Migration classification: search/reset are mechanically expressible as `Button` with explicit variant, `size="sm"`, `layoutClassName="field-h-md"`, accepting the documented mold differences. Prev/next are secondary/md and preserve omitted type only after confirming they remain outside a form. Filter toggle needs an explicit ARIA/variant design decision; sort headers are excluded due inline appearance.

### C. ContactsPage: permission-gated Modal/Drawer action launchers and reload after destructive/resolve actions

Candidate raw controls:

- create Modal opener `frontend/src/pages/contacts/ContactsPage.tsx:252-262` (`btn-primary field-h-md`, `customers.create`);
- row edit Drawer opener `:394-398` (`btn-sm`, `customers.update`, stops row propagation);
- distinct-confirm Modal opener `:399-403` (`btn-sm`, update permission plus pending status, stops propagation);
- delete ConfirmModal opener `:404-406` (`btn-sm btn-danger`, `customers.delete`, stops propagation).

Event/state/API chain:

- Create opener seeds company from the current filter and opens (`:253-258`); this state initialization must survive migration.
- Edit button must retain `event.stopPropagation()` because the DataTable row itself also opens edit (`:397`, row click wiring `:411-417`). Verify one open action, not merely dialog presence.
- Delete confirm sends exact DELETE `/contacts/:id`, closes target and reloads contacts on success; on failure it reports error and still closes (`:214-223`). ConfirmModal uses explicit `type="button"`, danger/primary variant and calls supplied callbacks (`frontend/src/components/ConfirmModal.tsx:31-44`).
- Distinct confirm sends exact PATCH `/contacts/:id`, `{status:"active"}`, closes and awaits reload (`ContactsPage.tsx:226-239,430-438`). Although `dedupSubmitting` is set/reset (`:123,229,238`), it is not passed into ConfirmModal and has no other read; the current confirm button therefore remains enabled while pending. Migration must not silently convert that unused state into `disabled`/`loading`.
- Existing create/edit success/failure/cancel coverage is reusable in `frontend/src/components/PageFormButtonMigration.test.tsx:100-177`; required company guard is at `:202-217`. It globally forces permission true (`:11`) and therefore cannot prove launcher denial.

Verification:

1. Use real ContactsPage/DataTable/Modal/Drawer/ConfirmModal; mock API and resolve `/me/permissions` before asserting launchers. Test create/update/delete permissions independently.
2. Focus each raw row button, click, assert only the intended dialog/drawer. For edit/dedup/delete, also attach the real row behavior and prove stopPropagation by one open/one write target, not a mocked handler.
3. Cancel/X/Escape must yield zero writes and restore focus where Modal guarantees it. Confirm success exact method/path/payload, one added contacts GET, the currently unlocked duplicate-pending behavior for distinct confirmation, and failure close/error behavior as implemented.
4. Reuse PageForm tests for create/edit form contracts and `SharedButtonMigration.test.tsx:54-63` for generic ConfirmModal callback/type/variant. Add page-specific delete/dedup tests; a generic ConfirmModal callback test cannot prove ContactsPage target id, reload, permission, or error state.

Migration classification: create/edit/dedup/delete launchers are mechanically representable if `stopPropagation`, omitted type, permission/status gates and field-h sizing are preserved. ConfirmModal internal buttons are already shared and are not candidates.

## 3. Fixture and assertion traps to avoid

- **Hex guard:** never duplicate product color literals in a test or encode/split them to hide detection. Derive an existing value from real DOM when the contract is DOM→payload, and combine with source/byte audit when value-definition immutability matters.
- **Emoji guard:** direct emoji literals in JSX/TSX fixtures trip `check:jsx-emoji`; use semantic icon components for UI. Do not disguise a new UI glyph with code points. If an existing text-field payload genuinely requires the same character, establish the repository-approved fixture form before implementation.
- **Async permission false positives:** a launcher can be absent before `/me/permissions` resolves. Record the permission GET count, await its response and page data, then assert presence/absence. Do not mock `usePermissions` to always true in permission tests.
- **Stale GET history:** cleanup does not clear mock calls. Clear calls or record a starting count before a second render, then assert the increment/exact URL.
- **Unsettled deferreds:** every pending promise must resolve/reject inside `act`; otherwise later tests can receive state updates. Assert write count before and after repeated clicks.
- **Native validation masking handler guards:** click first to prove native `required`; then populate native-required fields and `fireEvent.submit(form)` when separately proving a submit-handler guard.
- **Meaningless appearance assertions:** `textContent` truthiness, generic dialog presence, or only checking a new class does not prove behavior. Assert exact type, disabled/ARIA where contractual, exact event outcome, exact method/path/payload, close/focus, reload increment and error/retry state.
- **Over-mocking:** mock API/auth boundaries only. Do not mock page handlers, Modal, Button, permissions state machine, DataTable row events, or router when those are the contract under test.
- **Pending semantics:** Button itself disables only for caller `disabled` or `loading`. Migration must reflect current page state. Do not add loading/disabled to make a test easier or assume every pending action locks.

## 4. Recommended smallest representative set

Use three pages because each covers a distinct risk with little redundant proof:

1. **RolesPage** — permission-gated Modal open/close, in-page selection with dirty confirmation, exact permission PUT and cancel reset.
2. **InventoryPage** — click/Enter search, toggle ARIA, reset and pagination-driven GET with boundary/loading disabled behavior.
3. **ContactsPage** — row `stopPropagation`, Drawer/ConfirmModal launch, permission/status gates, exact PATCH/DELETE and reload/error behavior.

Generic Button/Modal behavior should remain in existing `Button.test.tsx` and `SharedButtonMigration.test.tsx`; page suites should prove wiring and business outcomes. This split avoids repeating implementation assertions while detecting the regressions a tag/class-only migration can introduce.
