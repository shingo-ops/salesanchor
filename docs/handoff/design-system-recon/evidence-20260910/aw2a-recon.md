# AW-2a recon (origin/main 57090e4576e8cdcd7c66cdcb17958c188ac28e86)
Snapshot: scratchpad/aw2a/frontend/src. Raw grep: out/grep.txt. Mapping evidence baseSha was 3210edeea250e269102bedd3546ebc48ddb89b77; all 13 file:line in it equal current lines (no line moves).

## Counts: 13 confirmed (karte 5 + modal 4 + header 2 + tabbar 1+1). No count/line differences.

## Table
| target | className | children | proposed | layout stays page side | rules unused after |
|---|---|---|---|---|---|
| InboxKartePanel.tsx:447 | "right-panel-field" | static 3 option, t() | variant=karte fullWidth, children mode | width:100% -> fullWidth | see per-class |
| InboxKartePanel.tsx:514 | same | static 4 | same | same | |
| InboxKartePanel.tsx:527 | same | static 4 | same | same | |
| InboxKartePanel.tsx:541 | same | static 3 (value=competitorValue, onChange has setTimeout, NO onBlur) | same | same | |
| InboxKartePanel.tsx:557 | same | static 4 | same | same | |
| InboxProfileModal.tsx:161 | same | static 3, t() | same | same | |
| InboxProfileModal.tsx:200 | same | static 4 | same | same | |
| InboxProfileModal.tsx:215 | same | static 4, literal Hot/Warm/Cold | same | same | |
| InboxProfileModal.tsx:226 | same | static 4, literal Small/Medium/Large | same | same | |
| DashboardPage.tsx:412 | "page-header-select" | map over monthOptions (key=o.value) | variant=header, children mode | none (height owned by variant) | see per-class |
| DashboardPage.tsx:441 | same | static 5 option, t() | variant=header | none | |
| InboxPage.tsx:92 | "inbox-platform-select" | static 4 option, t() | variant=tabbar | margin-left:auto; flex-shrink:0 | |
| InboxMessageThread.tsx:409 | same | static 3 option, t() | variant=tabbar | margin-left:auto; flex-shrink:0 | |
Options in all 13 are JSX <option> children (not options[] data). Only DashboardPage:412 uses map. All are controlled (value+onChange).

## (a)-(d) verbatim: see transcript of sed in source; summary of attrs
- Karte 447: value={cardForm.customer_type ?? ""}; onChange={(e) => handleCardFieldChange("customer_type", e.target.value || null)}; onBlur={handleCardFieldBlur}. children: <option value="">—</option><option value="信頼重視">{t("leads.customerType_trust")}</option><option value="価格重視">{t("leads.customerType_price")}</option>. lines 447-452
- Karte 514-520 response_speed (options "" / 24h以内 / 3日以内 / 3日超), same handler pattern + onBlur
- Karte 527-533 temperature ("" / Hot / Warm / Cold with t("leads.temperature_*")), + onBlur
- Karte 541-550 competitorValue: onChange={(e)=>{const v=e.target.value; handleCardFieldChange("competitor_check", v===""?null:v==="true"); setTimeout(handleCardFieldBlur,0);}}; no onBlur; options "" / "false" t("leads.competitorUnconfirmed") / "true" t("leads.competitorFound")
- Karte 557-563 estimated_scale ("" / Small / Medium / Large via t("leads.estimatedScale_*")), + onBlur
- Modal 161-166 customer_type; 200-206 response_speed; 215-221 temperature (literal Hot/Warm/Cold labels); 226-232 estimated_scale (literal Small/Medium/Large labels); same value/onChange/onBlur pattern
- Dashboard 412-421: value={funnelMonth} onChange={(e)=>setFunnelMonth(e.target.value)} aria-label={t("funnel.monthLabel")}; {monthOptions.map((o)=>(<option key={o.value} value={o.value}>{o.label}</option>))}
- Dashboard 441-452: value={period} onChange={(e)=>setPeriod(e.target.value as Period)} aria-label={t("dashboard.periodLabel")}; options 1w/1m/3m/6m/12m via t("dashboard.period*")
- InboxPage 92-102: value={state.platformFilter} onChange={(e)=>state.setPlatformFilter(e.target.value as PlatformFilter)} aria-label={t("inbox.platformFilter")}; options all/messenger/instagram/discord
- InboxMessageThread 409-418: value={recipientLanguageSetting} onChange={(e)=>setRecipientLanguage(e.target.value as "auto"|"ja"|"en")} aria-label={t("translation.sendGuard.langToggleLabel")}; options auto/ja/en. Preceded by comment `{/* ui-allow: ADR-143 Phase A send-guard lang toggle, back-merged from main (#2624) */}` at :408
- No select of the 13 has id, style, data-testid, disabled, or aria-* other than the aria-label above (karte/modal: none).

## CSS rules mentioning the 3 classes (frontend/src/**/*.css)
components.css:585-599 .page-header-select | components.css:600-603 :hover | components.css:604-608 :focus
InboxPage.css:69-81 .inbox-platform-select | :82-86 :focus
InboxPage.css:1196-1203 .right-panel-field | :1204 ::placeholder{color:var(--text-muted)} | :1206 select.right-panel-field{appearance:none;-webkit-appearance:none} | :1207 :focus{outline:none;border-color:var(--accent)} | :1208 textarea.right-panel-field{resize:none;min-height:var(--inbox-textarea-min-h)}
Comment-only mentions: FormField.css:194,215,233; DashboardPage.css:23 (db-tabs height comment, no rule).
No ancestor-scoped / compound rule found (grep of all CSS: none). av2-select-mapping.json rows for the 13: classification iv, unconfirmedRules 0, chainCount 2 closedChains 2; applied rules = own-class only (.page-header-select x3; .inbox-platform-select x2; .right-panel-field 1196/1204/1206/1207), universal `* {margin:0;padding:0;box-sizing:border-box}` index.css:419 applies to all. layoutProperties per mapping: header [height], tabbar [margin-left, flex-shrink, height], karte/modal [width].

## Declaration splits
.page-header-select (585-599) LAYOUT: height:var(--size-icon-btn). DECORATION: appearance, -webkit-appearance, box-sizing, padding(sp1 sp5 sp1 sp3), border 1px solid var(--border), border-radius pill, background (surface + svg arrow), color, font-size sm, cursor pointer, transition, white-space. hover: background-color, border-color. focus: outline, border-color, box-shadow focus-ring.
.inbox-platform-select (69-81) LAYOUT: margin-left:auto; flex-shrink:0; height:var(--height-tab-item). DECORATION: padding 0 sp2, border 1px solid, border-radius sm, background surface, color text-secondary, font-size xs, font-family inherit, cursor pointer. focus: outline none, border-color accent, color text-primary.
.right-panel-field (1196-1203) LAYOUT: width:100%. DECORATION: box-sizing, background(karte-field-bg), border 0.5px solid karte-field-bd, border-radius md, padding karte-field-py/px, font-size sm, color text-primary, font-family inherit, transition. 1206 appearance none (decoration). 1207 focus outline/border-color. 1204 placeholder, 1208 textarea: not select-relevant.

## Every element using each class (tsx)
page-header-select: DashboardPage.tsx:413, :442 (both select). Also tests-e2e/scene1-dashboard.spec.ts:367 `page.locator(".page-header-select")` (selector, would break if class dropped; strict mode with 2 matches also toBeVisible). frontend/scripts/check-page-header-actions.js:8,63-70,110 only forbids definitions outside components.css; does not require usage in tsx (check 1 lines ~21-60 not read: 未確認).
inbox-platform-select: InboxMessageThread.tsx:410, InboxPage.tsx:93 (both select). No other.
right-panel-field: input / textarea / a / button, not select: InboxKartePanel.tsx:362(a),370,377,384,402,435,441,459,508(input date, +karte-field-empty),567,573,579 (input); 483,502,536,587 (textarea); InboxProfileModal.tsx:115,120,127,146,151,156,170,176,195,236,241,246 (input); 180,190,209,264 (textarea); SalesFormMultiSelect.tsx:104 (button, +sales-form-trigger), :150 (input, +sales-form-other-input). Full list in out/grep.txt.

## Becomes unused after migration (only if all 13 drop the class)
- .page-header-select 585-608: unused by any element; BUT e2e scene1-dashboard.spec.ts:367 depends on class. Decision needed: keep a hook class/testid or change e2e.
- .inbox-platform-select 69-86: decoration unused; layout margin-left:auto/flex-shrink:0 must move to a page-side layout class (no layoutClassName prop exists; see API).
- .right-panel-field: still used by 30+ input/textarea/a/button -> keep 1196-1203,1204,1207,1208. Only `select.right-panel-field` 1206 (appearance none) becomes dead. width:100% stays needed for non-selects.

## SelectControl API (frontend/src/components/Select.tsx)
:15 SelectSize "sm"|"md"|"lg"; :16 SelectIndicator "default"|"none"; :17 SelectVariant "standard"|"karte"|"header"|"tabbar"
:25-31 own props: options, size, fullWidth, placeholder, appearance "field"|"bare"
:38-41 options mode (children?: never); :43-50 children mode (Pick size/fullWidth/appearance; children: ReactNode; options?: never)
:53-55 variant allowed only with appearance bare (default); appearance field -> variant "standard" only
:63-76 destructure defaults size md, fullWidth false, appearance bare, indicator default, variant standard, className
:78-87 controlClass: comp-select__control (bare) [+ --sm/--lg if size!=md] [+ comp-select__control--full if fullWidth] [comp-select--no-indicator] [comp-select--<variant> if !=standard] + className
:89-95 children mode renders <select ref className {...rest}>{children}; :97-110 options mode. No layoutClassName prop exists (only className, appended last).
## FormField.css variant rules
:173-175 .comp-select__control--full{width:100%}
:195-208 .comp-select__control.comp-select--karte ; :210-213 ...--karte:focus
:216-226 ...--header ; :228-231 ...--header:hover
:234-248 ...--tabbar ; :250-254 ...--tabbar:focus
Notes: karte variant sets no font-family (source had font-family:inherit; base rule not read: 未確認). header sets font-family:revert, tabbar sets appearance:auto (differs from source appearance default of select with border/bg set: 未確認 visual equivalence, aw1-equivalence is cited at FormField.css:194).
Existing usage of variants elsewhere: Select.stories.tsx:127-135, Select.test.tsx:304,312 only.

## F. Follow-ups (origin/main 57090e45)
### F1 frontend/scripts/check-page-header-actions.js
Checks (lines 49-124): (1) L50-61 any CSS under src except components.css matching /\.page-header-actions\s*\{/ -> error; (2) L63-74 any CSS except components.css matching /\.page-header-select[\s:{]/ -> error; (3) L76-124 pages/**/*.css must not define *-header-btns/-header-actions {, *-period-select/-view-select, *-faq-btn/-settings-btn. Exit 1 if errors>0 (L132-138), else prints OK (L127-131).
It reads CSS only (readFileSync of .css; collectCSS L33-44). It does NOT read .tsx. It does NOT fail if .page-header-select is absent from components.css, nor if the class is used/unused in TSX. Removing the class from components.css would pass.
Wiring: NOT wired. package.json has no script for it; check:all (package.json:45) does not include it; `git grep check-page-header` on origin/main (excluding docs/src) finds only the file's own header; no workflow/husky/lint-staged reference found. Header comment L20 says "check:all に含まれる。CI で自動実行" but that is false on 57090e45.
### F2 tests-e2e/scene1-dashboard.spec.ts:349-380 (verbatim L358-368)
    // 0:12 の Dashboard 描画
    await page.goto("/");
    // h2 "ダッシュボード"
    await expect(page.getByRole("heading", { name: "ダッシュボード" })).toBeVisible({ timeout: 20_000 });
    // 期間プルダウンが描画される
    const periodSelect = page.locator(".page-header-select");
    await expect(periodSelect).toBeVisible();
Note: locator matches 2 elements when FUNNEL_MODE != off (DashboardPage:412,441); toBeVisible on multi-match is a strict-mode violation (behaviour with FUNNEL_MODE off in test env: 未確認).
CI: .github/workflows/e2e.yml job `playwright` name "Playwright E2E (chromium)" has `if: false # 一時停止 2026-06-01` (e2e.yml:105; commit 037dde856), runs `npm run test:e2e` (e2e.yml:163) = playwright test (package.json:11), testDir ./tests-e2e (playwright.config.ts:24). So the full suite incl. scene1-dashboard does NOT run in CI on origin/main (consistent with the skip on #3996). Other workflows run only karte-gate.yml:75/110 (karte-visual-gate, karte-screenshot-compare) and qa-smoke.yml:128 (tests/qa-smoke config). Local run only.
Other e2e touching these: inbox-header-ui-screenshots.spec.ts:58-61 langSelect = page.getByLabel("送信先言語") (aria-label, not class; survives migration if aria-label kept; also not in CI). karte-visual-gate.spec.ts:401,408 toHaveScreenshot(".inbox-right-panel") baselines "karte-lead-deal.png"/"karte-customer-company.png" (karte-gate.yml:75, runs on PR; pixel baseline would be affected by karte select migration; whether these views render the 5 selects: 未確認). Its other selectors use .right-panel-tab-content/.right-panel-label/.right-panel-section/input[type=url], not select classes.
### F3 unit tests
Test files existing for the target components: only frontend/src/pages/inbox/InboxMessageThread.discordSendError.test.tsx. grep for select|combobox|langToggle|platform in it: only `selectedLeadId`, `selectedConversation` (L28-29) and `alert.querySelector("button")` (L119,126). It does not query any select. No *.test.tsx exists for InboxKartePanel, InboxProfileModal, DashboardPage, InboxPage (git ls-tree + git grep on origin/main). No unit test references right-panel-field / page-header-select / inbox-platform-select (grep over src tests: none). Only stories: DashboardPage.stories.tsx, InboxPage.stories.tsx (render these pages). Select mold tests: components/Select.test.tsx (:304,:312 variant karte). Related: pages/leads/LeadFormFields.test.tsx (not a target).
