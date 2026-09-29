# AU 71-file product migration review

Status: **APPROVE** — source mapping and the replacement real-page suites are approved. Root's repository-wide coverage/build/Storybook remain the final integration gate.

## Pinned manifest

- Baseline commit: `303c3cfe756b1d82c042cba342c3a3150fc5ab8c`.
- Final exact 71-file baseline/current SHA-256 manifest: `/tmp/au-pages-audit-final.json` under each `.files[]` record (`file`, `beforeSha256`, `afterSha256`, `targets`, `inverseEqual`, per-target hashes).
- Final manifest SHA-256: `614c8bf910d65ab3c324e9b8601cad37e2fd3266b3356903669c31d9b5b5486c`.
- Final canonical TSV projection (`file`, `beforeSha256`, `afterSha256`, `targets`, `inverseEqual`) SHA-256: `bbff332b2d3af7b8aacfbeb0a3c4f3b5cdf29ae2b3a5678ca35f2f34af78347d`.
- Final manifest facts rechecked from current files: `fileCount=71`, `uniqueFiles=71`, `before=221`, `afterLegacy=0`, `common=494`, `links=8`, `pass=true`, `errors=[]`, all 71 `inverseEqual=true`, and all 179 outside native controls unchanged.
- The approved GoalSetting i18n delta is included: `ja goals.advisorRecommended = おすすめ {{value}}`, `en = Recommended {{value}}`; both locale records report `valueMatches=true` and `otherKeysUnchanged=true`.

The full 71-row hash list is kept in the JSON manifest rather than duplicated here. The hashes pin both the baseline file and current migrated file exactly.

## Review scope and findings

Root had already proved all non-appearance attributes and children by the 71-file inverse audit. This review independently inspected the higher-risk design mappings: all ButtonLink sites, all dynamic variants, and every planned layout mapping.

### Link semantics — APPROVE

- All eight planned link sites render `ButtonLink`.
- Companies remains the sole Router branch with `to={`/companies/${c.id}`}` and retains `stopPropagation`.
- The other seven remain native `href` branches. This includes the FedEx `mailtoHref` site.
- Every original `target="_blank"` and `rel="noopener noreferrer"` pair is retained.
- No site was converted to Button plus `navigate`, `window.open`, or another click-driven substitute.

### Dynamic six — APPROVE

- Inventory retains `filterEnabled ? primary : secondary`, `size="sm"`, `field-h-md`, `aria-expanded={showFilterPanel}`, `aria-pressed={filterEnabled}`, and its original panel-toggle handler. Expanded and pressed states remain distinct.
- InvoiceCreate retains its two independent mode predicates and original handler bodies, including clearing `sourceQuoteCode` on quote selection.
- Products retains `reorderMode ? primary : secondary`, `aria-pressed`, title, type and handler.
- Quotes retains `statusFilter === "" ? primary : secondary`, `aria-pressed`, type and handler.
- ProductMasters retains `attr === a.key ? primary : secondary`, `role="tab"`, `aria-selected`, key/test id and handler. The old explicit 4/12 padding maps to standard `size="sm"`; no Button `tab` variant or new pressed state was introduced.

### Layout mappings — APPROVE

- Every plan entry using `field-h-md` is present as `size="sm" layoutClassName="field-h-md"`.
- Registered token-only mappings are exact: margin top 8px → `comp-btn-layout--mt-2`; margin left 8px → `--ml-2`; margin left 12px → `--ml-3`; auto left margin → `--ml-auto`.
- `gs-save-btn` and `gs-advisor__run-btn` remain only at their approved layout-only call sites.
- Carrier environment delete is `danger`/`md` with `comp-btn-layout--ml-auto`; its old custom appearance class is absent.
- Purchase-order add item uses the registered top-margin class. Knowledge aliases, LLMBudget and ParseReview margin mappings match the transform plan.
- No unplanned layout class or inline appearance substitute was found in the reviewed mappings.

## Replacement real-page test review — APPROVE

The first page test draft used synthetic Button fixtures and omitted destructive/invoice cases; that evidence was correctly rejected. The replacement files were read directly:

- `AllLegacyButtonDynamicMigration.test.tsx` renders five real pages and exercises all six conditions: Inventory false/true cases plus InvoiceCreate's two controls, Products, Quotes and ProductMasters. It checks actual shared variant classes and absence of `comp-btn--tab`; Inventory proves expanded state changes without changing the independent enabled variant.
- `AllLegacyButtonOperationMigration.test.tsx` renders the real Login, CarrierIntegration and InvoiceDetail pages. It asserts exact login credentials, pending duplicate suppression and original-route navigation; reset exact address, rejection/no navigation and retry success; carrier cancel zero writes then exact sandbox DELETE once; invoice PDF exact `window.open('/api/invoices/3/pdf', '_blank')` with zero API writes. It also verifies both locale interpolation values.
- Initial carrier test failure is preserved in `/tmp/au-pages-validation/new-suites-first-fail.log` and `/tmp/au-pages-validation/new-suites.log`; the failing accessible-name assumption was corrected against the real page.
- Stable replacement run: `/tmp/au-pages-validation/new-suites-final.log`, **2 files / 11 tests passed**.
- Focused combined run: `/tmp/au-pages-validation/focused-final.log`, **6 files / 47 tests passed**.
- Final page ESLint and diff-check logs are empty (success); i18n log reports all prefixes passed.

No invented server persistence or visual claims are made. The suites mock API/Auth boundaries and validate client wiring. Authenticated production forms, browser appearance and production writes remain unverified.

No product edits were made during this review.
