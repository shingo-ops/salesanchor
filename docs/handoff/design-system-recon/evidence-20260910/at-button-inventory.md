# AT Button inventory (read-only)

Fixed commit: `a1cd9ea379cc7d85b797cca6b1cc092192296bc3`

## Recount

| Measure | Count |
|---|---:|
| commonButton | 265 |
| legacyTotalIncludingLinks | 232 |
| legacyNativeButton | 224 |
| legacyLinks | 8 |
| staticColor | 158 |
| singleBtnSm | 60 |
| dynamic | 6 |
| inlineCallbacksWithinLegacy | 139 |
| candidate | 11 |
| candidateFiles | 9 |

Definition: Babel AST over the fixed `git archive`; product TSX only, excluding test/spec/story/design-preview. A legacy node requires a class token `btn` or `btn-*`; suffixes such as `dist-btn` are not counted. The current total is 232 = 224 native buttons + 8 `a`/`Link` nodes. This independently reproduces the current residual instead of carrying the AS number forward.

Native classification is 158 static explicit-color + 60 bare `btn-sm` + 6 dynamic = 224. Of these, 139 use inline arrow callbacks. The 8 links remain separate because the current `Button` always renders a native button.

## Recommended mechanically mapped pool: 11 controls / 9 files

Each selected control has an explicit legacy primary/secondary class and no inline callback or extra custom class. Mapping is token-for-token: primary→`variant="primary"`, secondary→`variant="secondary"`, `btn-sm`→`size="sm"`, `field-h-md` or no size token→`size="md"`. This is a mold adoption, so pixel identity is not claimed.

| Source | raw class | type/form | onClick | disabled | Contract / API clue | Existing test clue |
|---|---|---|---|---|---|---|
| `frontend/src/pages/account-settings/ProfileSection.tsx:124` | `btn-primary` | `submit` / `None` | `None` | `saving` | submit profile form through patchMyProfile, refresh session profile, success/error and saving state; PATCH /staff/me/profile; then refresh() | none found by component-import scan |
| `frontend/src/pages/company-detail/CompanyBasicTab.tsx:97` | `btn-primary` | `submit` / `None` | `None` | `!basicDirty || basicSubmitting` | submit parent handleBasicSubmit; disabled unless dirty and not submitting; reload on success; PATCH /companies/{company.id} with normalized basic payload; then load() | frontend/src/components/PageFormButtonMigration.test.tsx |
| `frontend/src/pages/company-detail/CompanyChannelsTab.tsx:37` | `btn-primary` | `submit` / `None` | `None` | `!channelsDirty || channelsSubmitting` | submit parent handleChannelsSubmit; disabled unless dirty and not submitting; split/trim channels and reload; PATCH /companies/{company.id} {sales_channels:list}; then load() | none found by component-import scan |
| `frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:404` | `btn-secondary` | `button` / `None` | `addItem` | `None` | append one blank invoice line item; no API | frontend/src/components/CommerceNavigationButtonMigration.test.tsx |
| `frontend/src/pages/products/ProductEditPage.tsx:184` | `btn-primary field-h-md` | `submit` / `product-edit-page-form` | `None` | `saving || loading` | submit product edit page form; disabled while saving/loading; POST /products for create or PATCH /products/{id} for edit, then navigate back | frontend/src/components/CommerceNavigationButtonMigration.test.tsx |
| `frontend/src/pages/purchase-orders/PurchaseOrdersFormModal.tsx:138` | `btn-primary` | `submit` / `po-form` | `None` | `saving` | submit external form po-form with saving disabled state; POST /purchase-orders | frontend/src/components/PurchaseAdminEditorButtonMigration.test.tsx |
| `frontend/src/pages/quote-create/QuoteCreatePage.tsx:253` | `btn-secondary` | `button` / `None` | `addItem` | `None` | append one blank quote line item; no API | frontend/src/components/CommerceNavigationButtonMigration.test.tsx |
| `frontend/src/pages/quote-create/QuoteCreatePage.tsx:284` | `btn-primary` | `submit` / `None` | `None` | `saving` | submit quote draft with existing payload then navigate /quotes; POST /quotes | frontend/src/components/CommerceNavigationButtonMigration.test.tsx |
| `frontend/src/pages/super-admin/DexTab.tsx:322` | `btn-primary` | `submit` / `None` | `None` | `None` | submit active inline edit form; PATCH /super-admin/dex/{kind}/{editing.id}, then exact filtered GET reload | frontend/src/components/PurchaseAdminEditorButtonMigration.test.tsx |
| `frontend/src/pages/super-admin/TcgSeriesTab.tsx:244` | `btn-primary` | `submit` / `None` | `None` | `None` | submit new TCG type form; POST /super-admin/tcg/types, then GET /super-admin/tcg/types | frontend/src/components/PurchaseAdminEditorButtonMigration.test.tsx |
| `frontend/src/pages/super-admin/TcgSeriesTab.tsx:327` | `btn-primary` | `submit` / `None` | `None` | `None` | submit TCG series create/edit form; POST /super-admin/tcg/series or PATCH /super-admin/tcg/series/{editId}, then filtered GET | frontend/src/components/PurchaseAdminEditorButtonMigration.test.tsx |

These targets preserve their existing business writes; the button migration itself must change only import/tag/class mapping. No target deletes data, changes authentication/permissions, performs billing, or sends to an external integration. `type`, `form`, `onClick`, `disabled`, data attributes, children, payloads, reset/error/pending behavior and callback wiring must remain verbatim.

## Exclusions and occupancy

- Static explicit-color native controls: 158 total; only the 11 listed above form the proposed pool. Others include inline callbacks, extra layout/custom classes, external integrations, downloads, destructive operations, auth/registration, permission saving, or need separate flow evidence.
- Bare `btn-sm`: all 60 remain unconfirmed. Its neutral gray appearance does not establish a secondary variant contract; the earlier 36-item draft was rejected and is not a recommendation.
- Dynamic: 6. Runtime-dependent variant/active mapping needs separate design.
- Styled `a`/`Link`: 8. Existing Button cannot preserve `href`/`to` semantics.
- `InvoicesPage.tsx` is excluded: `release/field-size-invoices` is IN_PROGRESS.
- `SuppliersPage.tsx` is excluded: `release/supplier-button-alignment` is IN_PROGRESS and exact ownership is not clear.
- `release/deal-removal-quotes-dealid` is stale as IN_PROGRESS in the official ledger, while GitHub PR #3084 is MERGED; the remote branch still exists at `5a6c4ea`. Its formal scope owns `QuotesPage.tsx` and `QuoteDetailPage.tsx`, not `QuoteCreatePage.tsx`. QuoteCreate therefore has no declared file overlap; the stale ledger entry should still be corrected independently.
- Utilization frequency, user impact, revenue effect and time savings were not measured.

The JSON contains every excluded native complete JSX element with file/line/class/type/onClick/disabled and its exclusion reason, plus all eight complete link JSX elements and candidate file SHA-256 hashes.

## Evidence integrity

This report read the fixed archive, the common Button/Button.css and legacy components.css, the official `scripts/ledger-view.sh`, `active-work.d`, the fixed deal-removal design/recon, `git ls-remote`, and `gh pr list`. It followed CompanyBasic/CompanyChannels callbacks into `useCompanyDetail.ts` and Profile into `staffProfile.ts`. It did not use dirty product files, modify product/docs/git, invoke product APIs, or run UI behavior tests.
