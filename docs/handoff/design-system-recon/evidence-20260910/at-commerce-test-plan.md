# AT commerce button contract test plan

Fixed product source: `a1cd9ea379cc7d85b797cca6b1cc092192296bc3`.
Planned suite: `frontend/src/components/CommerceSubmitButtonMigration.test.tsx`.
Use real pages, Router, i18n and common Button. Mock only the API/auth boundary, reject unexpected network calls, and settle every deferred promise with `act` plus a rendered-state assertion.

## Ownership and overlap

- Owned targets: `InvoiceCreatePage.tsx:404` addItem; `QuoteCreatePage.tsx:253,284` addItem/submit; `ProductEditPage.tsx:184` submit.
- PR #3084 (`release/deal-removal-quotes-dealid`) is MERGED at `2026-07-24T03:55:15Z`. Its GitHub file list contains `QuotesPage.tsx` and `QuoteDetailPage.tsx`, not `QuoteCreatePage.tsx`. No local worktree for that branch appears in `git worktree list`. The remote branch remains at `5a6c4ea`; the official ledger is stale `IN_PROGRESS`. There is no product-file overlap with QuoteCreate.

## Contract matrix

### InvoiceCreate add blank line

Target: `type=button`, `onClick={addItem}`, no disabled prop, `data-testid=invoice-add-blank`.

1. Render the real page in inventory mode with all initial GET fixtures settled. Record POST/PATCH/DELETE counts and current item-row count.
2. Click once: row count is exactly `before + 1`; the appended row has the real `blankItem` defaults exposed by its inputs. All write counts remain unchanged.
3. Click twice more: row count is exactly `before + 3`, proving independent clicks remain allowed and no accidental submit occurs.
4. Assert the target stays enabled and has no `aria-busy`. This target has no pending state by product design.

### QuoteCreate add blank line

Target: `type=button`, `onClick={addItem}`, no disabled prop, `data-testid=quote-add-blank`.

1. Render the real page with CompanyContactSelector API fixtures. Record write counts and `quote-item-row-*` count.
2. Click once and assert exactly one additional row. Verify its name is empty, quantity is `1`, unit price is `0`, and optional weight is empty/null through the real inputs.
3. Assert POST/PATCH/DELETE counts are unchanged. Click again and assert another single row increment; target remains enabled and `aria-busy` absent.

### QuoteCreate submit

Target: `type=submit`, disabled only by `saving`; handler guards contact and valid line items.

1. **Contact guard:** leave `contactId=null`, make the line valid if needed, submit, assert POST `/quotes` count stays zero, selector-required error appears, route and form values remain.
2. **Item guard:** select a contact but exercise each invalid class in a table: empty `product_name`, `unit_price<=0`, `quantity<=0`. Each submit produces zero writes, the existing `quotes.itemsRequired` error, no navigation, and preserves entered values.
3. **Exact payload:** enter non-default values that expose every conversion. Expect exactly one `POST /quotes` with:
   - `company_id`, `contact_id`, `currency` unchanged;
   - `shipping_fee` and `tax_amount` converted with `Number`, with a separate empty-input case proving `null`;
   - `notes || null` with non-empty and empty cases;
   - each item containing exactly `product_id`, `product_name`, `name_en ?? null`, `condition ?? null`, `unit ?? null`, numeric `quantity`, numeric `unit_price`, and `weight`.
4. **Success:** resolve the deferred POST and assert exact route `/quotes`; POST count remains one.
5. **Pending:** before resolution, the submit button is disabled and its saving text is shown. A second click produces no second POST. Resolve or reject every deferred.
6. **Failure and retry:** reject first POST; assert exact error text, same contact/currency/fees/tax/notes/items remain, route unchanged, and button re-enables. Retry with a resolving POST and assert the exact same payload, total POST count `before + 2`, then `/quotes` navigation.

### ProductEdit submit

Target: external `form=product-edit-page-form`, `type=submit`, disabled by `saving || loading`, `data-testid=product-edit-save`.

Run create and edit modes as a parameterized contract. Set every field to distinguish strings, numeric conversion, empty-to-null and fallback behavior. Exact payload keys:

`name_ja`, `name_en`, `product_kind`, `tcg_type`, `set_type`, `category`, `mark`, `status`, `unit_price`, `quantity`, `weight`, `notes`, `release_date`, `jan_code`, `card_number`, `expansion_code`, `rarity`, `language`, `unit_price_usd`, `unit_price_eur`, `image_url`, `boxes_per_case`, `packs_per_box`, `box_weight_kg`, `case_weight_kg`, `volume_weight`, `moq`, `hs_code`, `material`, `item`, `required_output_value`, `search_keywords`, `exclude_keywords`, `related_series`.

1. **Create:** expect exactly one `POST /products` with the full payload. Empty optional strings become `null`; numeric strings use `Number`; `quantity` always uses `Number`; `product_kind` falls back to `null` only when empty.
2. **Edit:** fixture `GET /products/{id}` populates the form; expect exactly one `PATCH /products/{id}` with the full edited payload. Initial master GETs remain `/products/tcg-types` and `/products/attribute-options` and are not counted as writes.
3. **Required guard:** clear the real required `name_ja` input and activate the submit control. Assert POST/PATCH stay zero and route/form state remain. Record that this is native form constraint validation, not a handler-level guard.
4. **Loading guard:** in edit mode hold `GET /products/{id}` pending; submit is disabled and clicking causes zero write. Resolve the GET before continuing.
5. **Pending:** hold POST/PATCH pending; submit and cancel are disabled, saving text is shown, repeat clicks cause no duplicate write, and route does not change. Settle the promise.
6. **Success:** after resolve, assert `navigate(-1)` by using a preceding MemoryRouter entry and checking that exact previous route appears.
7. **Failure and retry:** reject first write; assert exact surfaced message, all entered values retained, route unchanged, submit/cancel re-enabled. Retry with success; assert identical exact payload, write count `before + 2`, then previous-route navigation.

## Acceptance boundaries

- Assert common Button class/variant/size separately from business behavior: Invoice/Quote add are secondary md; Quote/Product submit are primary md.
- Preserve implicit/explicit attributes exactly: do not add loading, `aria-busy`, guards, reset, or disabled behavior beyond current props.
- No real API, DB, external integration, browser visual claim, authentication change, deletion or billing action.
- Existing related suites are supporting evidence only; this suite must exercise all four target controls directly. No `skip`, `todo`, fake handler-only component, unresolved deferred, console-warning suppression, or loose URL substring matching.
