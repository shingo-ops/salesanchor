# Sol1 read-only cross-review — CARD-AS-STATIC-BUTTONS-02

## Scope separation

This review covers only Sol1's 16 product files / 21 audited nodes, `CommerceNavigationButtonMigration.test.tsx`, and the narrowly authorized `StaffReportFormButtonMigration.test.tsx` change. It does not evaluate Sol2's 9 products or 2 new suites.

## Product migration: APPROVE

- Audit owner `sol1`: 16 files, 21 nodes.
- All 21 audited `migrated` JSX strings occur exactly once and all 21 corresponding raw native strings are absent.
- Replacing each audited migrated string with its raw string and removing only the added `Button` import reproduces the fixed baseline SHA-256 for all 16/16 files.
- Added imports resolve to the existing shared `Button` component with the correct relative path. Files that already imported it received no duplicate import.
- The diff preserves target children, callback, `type`, `disabled`, test id, and surrounding business body. No target permission gate, API callback, route, CSS, shared component, or non-target native button changed.

## Existing StaffReport test adjustment: APPROVE

The diff is exactly the design §AS correction: one title changes from the obsolete legacy-trigger statement to the common-primary statement, and exactly two class assertions change from `btn-primary field-h-md` / `comp-btn=false` to `comp-btn=true` / `comp-btn--primary=true`. Filtering GET, count, permission, and all other assertions remain byte-identical.

## CommerceNavigation suite: REVISE

Reviewed final SHA-256: `b888d279ada07f5735036e156974cb23a6377517788fb00904f29a630f21b7e3`.

The suite operates all 11 target controls through the real seven pages and covers the main results: page-2 pagination and loading/last-page inertness; six exact router outcomes; quote detail pending duplicate prevention, rejection/retry, populated item and source marker; void cancel closure with zero POST; ProductEdit pending cancel inertness and settled rejection; FedEx dialog open/cancel with zero POST. Permission-backed openers wait for their real rendered state; no production guard is bypassed.

One explicit `as-test-plan.md` acceptance remains unproved: Inventory page-2 Previous must return the **exact page-1 GET**. The test clicks Previous and asserts only that the number of calls containing `page=1` becomes two:

```ts
expect(mock.get.mock.calls.filter(c => String(c[0]).includes('page=1'))).toHaveLength(2)
```

This passes for any second URL containing that substring and does not establish the exact method/URL contract. Add an increment assertion for the literal expected URL `/inventory?page=1&per_page=50&sort=release_date&order=desc&tcg_type=pokemon_booster_box` after the Previous click (and, preferably, use the same literal for the initial page-1 read). No product change is needed.

## Verdict

**REVISE** for the Sol1 test scope only. Product migration and the limited StaffReport change are approved. After the exact page-1 URL assertion is added and its focused suite succeeds, this review has no remaining finding.

## Final re-review after Sol1 correction

Reviewed replacement SHA-256: `93a0f0250a9ce0018ebe391265226366f2c588c5635a99124bab6ef4f2821abe`.

- Inventory now defines literal page-1/page-2 URLs, accepts only those literals in the fixture, records the exact page-1 call count before Previous, and asserts the exact literal count increases by one after the click.
- Invoice quote retry now proves both populated item state (`Card`) and the dedicated `invoice-source-quote` state containing `Q-7`; it no longer relies on the quote-list text for the source marker.
- Focused rerun `/tmp/as-sol1-validation/12-unit-cross-fix.log`: 1 file / 11 tests passed.
- Strict ESLint `/tmp/as-sol1-validation/13-eslint-cross-fix.log`: exit 0, zero output. Diff check `/tmp/as-sol1-validation/14-diff-check-cross-fix.log`: exit 0, zero output.

**Final verdict: APPROVE.** The earlier test finding is resolved. No remaining Sol1 product, limited StaffReport, or CommerceNavigation acceptance finding was observed.
