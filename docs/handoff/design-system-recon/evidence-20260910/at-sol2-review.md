# Sol2 read-only cross-review of Sol1 — CARD-AT-FORM-BUTTONS-SOL2

Final reviewed test SHA-256: `5d611bd28fd270b5381cd8729e49eaff2b5fa80eccb5ad1566b981a84b2e9dec`.

## Product migration

**APPROVE.** Audit owner `sol1` contains three files / four nodes. Every migrated JSX string occurs once, every raw string occurs zero times, and replacing only the four migrated strings with the audited raw strings reproduces the fixed file SHA-256 for all 3/3 products. Existing shared `Button` imports are reused. Children, `type`, external `form`, disabled state, callbacks and test ids are preserved. No handler/API/permission/business body changed.

## CommerceSubmitButtonMigration test

**APPROVE.** The suite uses real `InvoiceCreatePage`, `QuoteCreatePage`, `ProductEditPage`, Router and form handlers, mocking only the API/network boundary.

- Invoice and Quote add-item controls each prove one blank row per click and zero POST/PATCH/DELETE.
- Quote required contact and item guards prove zero writes, including empty name, zero price and zero quantity.
- Quote submit proves the complete payload, nonempty and null normalization, pending native-disabled duplicate prevention, rejection/input retention, identical retry and exact `/quotes` success route.
- Product create and edit each prove a 34-key payload with exact POST/PATCH endpoint, pending Save/Cancel disabled and duplicate click prevention, rejection/input retention, identical retry and successful history back navigation.
- Product required and edit-loading guards prove zero writes.
- All deferred promises settle. The suite does not exercise Invoice submit, consistent with the design exclusion for its non-JPY backend FX outbound request.

Observed evidence: `/tmp/at-sol1-validation/10-unit-exact-null.log` reports 1 file / 11 tests passed; `/tmp/at-sol1-validation/11-eslint-exact-null.log` is zero-output strict ESLint success. No guard bypass, partial-payload matcher, class-only mirror assertion, or external write path was found.

## Final verdict

**APPROVE**, with no remaining Sol1 product or test finding.
