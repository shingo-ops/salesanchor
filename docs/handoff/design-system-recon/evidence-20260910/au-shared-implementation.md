本報告はカードCARD-AU-SHARED-02の実行結果である（CARD-AU-SHARED-01の成果を継承）。

# AU shared Button implementation result

- Official worktree: `/Users/tanizawashingo/worktrees/salesanchor/release-frontend-all-buttons`
- Base: `303c3cfe756b1d82c042cba342c3a3150fc5ab8c`
- Preflight: success before implementation.

## Implemented ownership

- Extracted the existing Button class composition unchanged into `frontend/src/components/buttonAppearance.ts`; Button still renders the same native button and retains its attribute/disabled/ARIA ordering.
- Added `ButtonLink` as an exclusive `to` Router Link / `href` anchor union with `HTMLAnchorElement` ref, no tab/loading/disabled/className/style API, and the shared class builder/CSS.
- Added link underline normalization and four approved token-only placement classes to Button.css.
- Added ButtonLink tests and Storybook stories.
- Corrected the one historical FullPage legacy appearance section to assert the shared primary/base classes while retaining all operation assertions.
- After raw221 migration reached zero, detected an indirect legacy CSS dependency through HeaderButton and stopped deletion. CARD-AU-SHARED-02 then authorized the correction.
- HeaderButton text variants now delegate to Button with explicit `type="button"`, `size="md"`, and the same variant/public props/children. Icon remains a native `icon-btn` button.
- Added HeaderButton contract tests for all four variants, click/disabled, type, ARIA/data and classes.
- Migrated six raw legacy catalog buttons in three authorized story files.
- Removed the now-unused legacy primary/secondary/ghost/sm/danger/outline definitions, compound size rules, header modifiers, mobile compatibility block, login override and btn-block. `icon-btn` and unrelated CSS remain.

## Validation

- Initial unit launch failed before code execution because sandbox denied creation of `frontend/node_modules/.vite-temp`; raw log: `/tmp/au-shared-validation/unit-initial.log`.
- Second non-escalated launch failed writing the bundled Vite config; raw log: `/tmp/au-shared-validation/unit-recheck.log`.
- First TypeScript pass found union narrowing at `ButtonLink.tsx:44`; preserved raw log: `/tmp/au-shared-validation/tsc-initial.log`. Fixed by an explicit exclusive-branch type guard; no API relaxation.
- Final targeted unit: **4 files, 36 tests passed**, `/tmp/au-shared-validation/unit-supplement.log`. jsdom prints four expected `Not implemented: navigation to another Document` notices for modified-click browser-default behavior; tests prove Router location remains unchanged and no external service is contacted.
- Final TypeScript: exit 0, `/tmp/au-shared-validation/tsc-supplement.log`.
- Final scoped ESLint with `--max-warnings=0`: exit 0, `/tmp/au-shared-validation/eslint-supplement.log`.
- Final stylelint for owned CSS: exit 0, `/tmp/au-shared-validation/stylelint-supplement.log`.
- Final `git diff --check`: exit 0, `/tmp/au-shared-validation/diff-check-final.log`.
- Production build before supplemental HeaderButton/story changes: exit 0, `/tmp/au-shared-validation/build.log`.
- Storybook build before supplemental story changes: exit 0, `/tmp/au-shared-validation/storybook.log`.
- Final supplemental files are covered by final TypeScript/ESLint/unit. Root owns the non-concurrent final full build/check/Storybook decision.
- Exact class/selector search after cleanup returned zero legacy consumers/definitions. A DesignSystemPage prose label containing `.btn-ghost` remains text, not a class or CSS selector, and was outside shared ownership.

## Limits and remaining work

- Did not edit APIs, DB, routes, business handlers, authorization, translations, dependencies, CI, tokens, GO/PR/deploy state.
- Did not run authenticated production forms, visual browser review or production writes.
- Page implementation and global full-suite validation are owned by the other assigned agents/root.
