# AU legacy button → existing shared molds: source-pinned contract

## Scope and source

- Read-only official worktree base: **`303c3cfe756b1d82c042cba342c3a3150fc5ab8c`** (`git rev-parse 303c3cfe7`) in `/Users/tanizawashingo/worktrees/salesanchor/release-frontend-all-buttons`.
- A targeted diff from the earlier inspected `origin/main` SHA `1102afa9fe3d9cb69fea6797766820c154e8649a` to this official base returned no changes for Button/Button CSS, legacy CSS, HeaderButton, the five legacy link sites, the danger-link sites, component-standard, page-header-v2 design, or ADR-144. All conclusions below are therefore pinned to the official base.
- No working-tree files were used as authority and no product file was edited.
- This report describes what the existing code can express. It does not invent a new API or infer undocumented visual equivalence.

## Authoritative shared `Button` API

Source: `frontend/src/components/Button.tsx` at the pinned SHA.

- Variants are exactly `primary | secondary | ghost | danger | outline | tab`; sizes exactly `sm | md | lg` (lines 20–21). Defaults are `primary` and `md` (49–53).
- Options: `fullWidth`, `loading`, `loadingText`, `active` (tab only), `iconOnly`, `children`, and placement-only `layoutClassName` (23–36).
- Native props are `ButtonHTMLAttributes<HTMLButtonElement>` except appearance-owned `className` and `style` (38). This means native `type`, `form`, `name`, `value`, `onClick`, `disabled`, `aria-*`, `data-*`, etc. are forwarded; arbitrary appearance classes/styles are deliberately unavailable.
- `forwardRef<HTMLButtonElement>` points to the same native `<button>` (49, 75–83). Tests prove node identity/focus through rerender and null on unmount (`Button.test.tsx:8–21`).
- Class composition order is fixed: `comp-btn`, variant, size (omitted for tab), active (tab only), full, loading, icon-only, then `layoutClassName` (64–73). `layoutClassName` can therefore add placement/layout classes, but its documented purpose does not authorize appearance overrides.
- No `type` is synthesized. Omitted type remains omitted and has native submit behavior in a form; explicit `button`/`submit` remains exact (`Button.test.tsx:23–50`). Preserve the source type exactly, including omission.
- Caller events retain the native event/currentTarget and `stopPropagation` (`Button.test.tsx:52–62`). Preserve existing handler bodies and propagation calls byte-for-contract.
- Effective disabled is `disabled || loading`; loading also sets `aria-busy`, inserts a decorative spinner, and substitutes `loadingText ?? children` (79–86; tests 64–105). Do not introduce `loading` during a visual migration unless the legacy control already locked while pending; it changes repeat-click behavior.
- Because `{...rest}` follows owned `disabled`, `aria-busy`, `aria-pressed`, and `aria-label` attributes (79–83), forwarded native ARIA can override owned values. This is tested for `aria-pressed={false}` and `aria-busy={false}` (`Button.test.tsx:97–109`). For a tab migration, omit a caller `aria-pressed` only when Button should own it; otherwise preserve the explicit caller value.
- `active` has semantics only with `variant="tab"`: it adds `comp-btn--active` and Button emits `aria-pressed` (63, 67–68, 81). Do not map every dynamic primary/secondary toggle to tab; only use tab when the existing action is a selected-state view/sort switch and that pressed-state semantic is intended.

## Exact legacy-class mapping and differences

Legacy source is `frontend/src/components.css:53–163`; shared source is `frontend/src/components/Button.css:1–148`.

| Legacy token(s) | Existing mold expression | Contract / known difference |
|---|---|---|
| `btn-primary` | `<Button variant="primary" size="md">` | Semantic mapping is supported. Legacy radius 4px, no min-height/box-sizing, `border:none`; shared radius 6px, 36px min-height, border-box and transparent 1px border. Legacy disabled changes background to muted and opacity 0.7; shared retains variant background and uses opacity 0.6. Legacy definitions: components.css 54–66; shared: Button.css 2–18, 32–40, 100–103. |
| `btn-secondary` | `<Button variant="secondary" size="md">` | Semantic mapping is supported. Both use surface/background, secondary text and border, but legacy radius 4px/no min-height; shared radius 6px/36px minimum and shared active/focus states. Legacy 68–78; shared 2–18, 42–46, 63–75, 95–103. |
| `btn-ghost` | `<Button variant="ghost" size="md">` | Supported role mapping. Legacy uses horizontal padding 12px, `font-sm` + semibold; shared md uses 20px, base font + medium, 36px min-height. Legacy 81–93; shared 2–18, 48–52, 63–75. |
| `btn-danger` | `<Button variant="danger" size="md">` | Supported role mapping. Legacy text uses `--danger`; shared uses `--danger-text`. Legacy has padding 8/12, radius 4px; shared 8/20, radius 6px, min-height 36px. Legacy 107–122; shared 2–18, 77–85. |
| `btn-outline` | `<Button variant="outline" size="md">` | Closest and explicitly supported. Shared centralizes focus and disabled. Legacy hover also changes border color to `--text-secondary`; shared hover leaves border token unchanged. Legacy 124–143; shared 48–56, 63–75, 95–103. |
| `btn-primary btn-sm` | `<Button variant="primary" size="sm">` | Semantic/size mapping supported, but not pixel-identical. Legacy composite restores accent and uses 4/10 padding, xs font, 3px radius, no min-height (149, 155–163); shared uses 4/12, xs, 6px radius, 28px min-height (20–24). |
| `btn-secondary btn-sm` | `<Button variant="secondary" size="sm">` | Supported mapping with same shared-mold differences: horizontal padding 10→12, radius 3/4→6, minimum height 28. Legacy composite sizing is explicit at 149–153. |
| `btn-danger btn-sm` / `btn-sm btn-danger` | `<Button variant="danger" size="sm">` | Supported mapping. Legacy composite exists specifically to undo later `.btn-danger` size overrides (145–153). Preserve semantic danger; expect shared color/radius/min-height changes above. |
| bare `btn-sm` | **No exact existing Button variant. Decision required.** | It is an independent filled neutral style: `background: --bg-hover`, no border, secondary text, 4/10 padding, xs font, 3px radius (95–105). Shared `secondary sm` adds surface background + border; `ghost sm` is transparent until hover. `secondary sm` is the safest semantic default for ordinary row actions, while `ghost sm` is closer in borderlessness, but neither preserves appearance. Do not silently treat bare `btn-sm` as primary (Button default). `component-standard.md:104–110` explicitly records this as an unresolved redesign item. |
| `btn-sm field-h-md` (and variant combinations) | Matching variant + `size="sm" layoutClassName="field-h-md"` is mechanically expressible | It preserves the existing 36px minimum placement sizing while adopting shared horizontal padding/radius/border. `Button` md is another possible visual standard but changes font and padding more. Existing research documents this exact non-equivalence (`as-button-contract-research.md:22–28`). |
| `btn-block` with a supported variant | `fullWidth` **only after verifying** legacy `btn-block` is width-only at the pinned source/use site | Button's `fullWidth` is exactly `width:100%` (Button.css 110–112). If the legacy class also owns placement/spacing, retain an approved layout class or stop; do not assume full equivalence from the name.
| dynamic `cond ? "btn-primary..." : "btn-secondary..."` | `variant={cond ? "primary" : "secondary"}` plus fixed `size`/layout props | Preserves current visual state without introducing tab semantics. Keep all existing `aria-expanded`, `aria-pressed`, disabled and event props. Example at `InventoryPage.tsx:403`; existing source research warns that its expanded and pressed states are distinct (`as-button-contract-research.md:63–83`). |
| dynamic in-page selected switch currently primary/secondary | Prefer the same conditional primary/secondary mapping for mechanical migration. `tab` requires a design decision. | `tab` ignores size classes and adds Button-owned pressed semantics (Button.tsx 63–68, 81). Page-header design permits tab for view/sort selection (`page-header-v2/design.md:9–17,44–52`), but changing an established primary/secondary switch is a semantic and visual redesign, not mechanical replacement. |

All shared variants gain a common focus-visible outline (`Button.css:95–98`), common disabled opacity/cursor (`100–103`), and 44px mobile minimum (`134–147`). Most legacy classes lack those rules. These are intended mold adoption differences and need browser focus/mobile verification if appearance is an acceptance criterion.

### Scoped/override cases that must not be missed

- Login submit: `.login-card .btn-primary` owns `width:100%`, 12/16 padding, md font, semibold and 6px radius (`frontend/src/pages-layout.css:261–275`). Proposed standard mapping is `variant="primary" size="lg" fullWidth`: it deliberately adopts standard lg 12/24 padding and 48px minimum while preserving full width and md font (`Button.css:26–30,110–112`). Do not leave the legacy selector targeting the migrated element, and do not carry its padding/font through `layoutClassName`.
- `.btn-block` is **not width-only** at this official base: it sets both `width:100%` and `padding:var(--space-2)` (`pages-layout.css:546–549`). Mapping is `fullWidth` plus the variant's standard `size` inferred from the underlying control; remove the padding override. `fullWidth` preserves width, while Button size owns padding. This is a visual standardization, not pixel parity.
- Registration language toggles use `className="btn btn-ghost"` plus inline `fontSize:var(--font-size-sm)` in `RegisterAddressPage.tsx:294`, `RegisterChangeBillingPage.tsx:227`, and `RegisterPage.tsx:279`. Proposed mapping is `Button variant="ghost" size="sm" type="button"` with the same handler/children and **no style**. It adopts shared xs-size typography/padding. If PO instead requires md standard typography, use size md consistently across all three; do not add a one-off font-size entry to Button.
- Other inline appearance overrides, e.g. Channels connect buttons with md font and 12/24 padding (`ChannelsPage.tsx:436–441,558–563`), map naturally to `variant="primary" size="lg"` while preserving their disabled expressions. Remove inline style rather than recreating it.

## Icon controls

1. General square icon control: `<Button variant="ghost" iconOnly aria-label={...}>…</Button>` is the available standard expression. `iconOnly` is documented to require an accessible label (`Button.tsx:31–32`) and sets 36px square at md, 28px at sm, 44px at lg; mobile becomes 44px (`Button.css:114–147`; token sizes at `tokens.css:159–164`). Preserve explicit `type`, tooltip/data attributes and handlers.
2. Legacy `.icon-btn` is 36px square, transparent, radius 6px, icon-action color; danger is only a `.danger:hover` modifier (`components.css:738–754`). `Button ghost iconOnly` has the same standard square/radius dimensions but different text/icon color tokens and shared focus/mobile behavior. A `.danger` icon cannot be translated via `layoutClassName="danger"` because that is an appearance modifier; `variant="danger" iconOnly` makes danger text persistent, unlike legacy hover-only danger. This needs explicit acceptance.
3. Legacy `.modal-icon-btn` is 36px square with **full/pill radius** and muted color; its danger modifier affects hover only (`components.css:518–540`). No current Button option provides a full-radius modal icon appearance. `ghost iconOnly` is the safest existing common mold but visibly changes radius/color; `danger iconOnly` changes resting color. Stop for design acceptance rather than smuggling `modal-icon-btn` through `layoutClassName`.
4. Header-specific existing mold: `HeaderButton` supports `ghost | primary | secondary | icon`, always emits `type="button"`, and requires `aria-label` for `icon` (`frontend/src/components/HeaderButton.tsx:15–59`). It reproduces legacy page-header classes and is safe only for page-header actions whose source contract is type=button and whose props fit its narrow API. It cannot preserve arbitrary native props, event parameters, refs, form association, or caller type. Page-header design also forbids primary in headers and allows ghost/icon/tab/settings plus limited period navigation (`page-header-v2/design.md:9–18,34–52`).

## Links and anchors

- Shared `Button` always renders native `<button>` (`Button.tsx:75–88`). There is no ButtonLink/anchor mold under `frontend/src/components` at this SHA (tree listing contains only `Button.tsx` and `HeaderButton.tsx` as button molds).
- Measured legacy non-button uses include one Router `<Link className="btn-sm">` (`CompaniesPage.tsx:408`) and four `<a>` primary/secondary external/internal links (`PaypalIntegrationPage.tsx:231,234`; `InvoiceDetailPage.tsx:222,232`). Converting these to Button changes native navigation, open-in-new-tab, href/status-bar, target/rel and keyboard/link semantics. They are **not safely migratable to existing Button**.
- Safe current behavior is to keep semantic `Link`/`a` until the already-designed **ButtonLink extension** is registered and implemented. The design SSoT explicitly says: “ButtonLink is native anchor appearance sharing” and must retain `href/target/rel/download` and ordinary link operation; it also says anchor disabled must not be treated as button disabled (`docs/specs/design-system/design.md:832`). The raw audit assigns the link group to a ButtonLink batch that retains `href/to/target/rel` (`docs/handoff/design-system-recon/evidence-20260910/raw-shared-raw-audit.md:170`). This is an explicit repository design, but no `ButtonLink` implementation exists in the component tree at this base.

### Concrete registered extension contract for the link batch

- Implement/register `ButtonLink` as a shared appearance owner; do **not** translate links to Button `onClick` navigation.
- It needs two semantic branches: Router navigation retaining `to` and native anchor navigation retaining `href`. Both must keep their original element behavior. The one existing Router Link must remain a React Router `Link`; the four measured anchors must remain `<a>`.
- Retain all current link-native props exactly: `to` or `href`, `target`, `rel`, download if encountered, click event/`stopPropagation`, children, ARIA and data attributes. Do not add `disabled`, `loading`, `aria-busy`, form props, or imperative `navigate`/`window.open`.
- Reuse the Button-owned appearance vocabulary (`variant`, `size`, `fullWidth` if actually needed, placement-only `layoutClassName`) and Button CSS classes so visual ownership remains one mold. Extract/export one pure class builder from `Button.tsx` (or an adjacent owner module) and have both `Button` and `ButtonLink` call it; do not duplicate the class table/composition. The extension must add only anchor normalization needed for the same appearance (for example text-decoration) in owner CSS; call sites must not receive arbitrary `className/style`.
- The public type should be a discriminated union so `to` and `href` cannot both be supplied and button-only props cannot leak into anchors. Ref types must match the rendered anchor/Router Link element rather than `HTMLButtonElement`.
- Registration evidence must use the repository's planned owner record fields: stable `componentId`, exact module, `exportName`, native tag/use, story and approved design decision (`docs/specs/design-system/ci-registry-design.md:39–56`). The registry document notes the machine-readable owner files are still proposed/unimplemented at this base (`:18–19`) and that adding a new owner needs a distinct approved path (`:58–72`); until that mechanism exists, the component implementation + Storybook + tests + design reference are the reviewable registration evidence.
- Required tests: Router `to`/modified-click behavior and `stopPropagation`; anchor exact `href/target/rel/download`; ref points to the rendered link element; variant/size class output; compile-time rejection of simultaneous `to`+`href`, `disabled/loading`, `className/style`; no conversion to click-driven navigation.

ADR-144 says when a mold is absent, stop/report and obtain PO permission before creating it (`ADR-144-ui-component-governance.md:59–64`). This task's stated PO authorization covers migrating all remaining legacy buttons, so the root design should record ButtonLink as the necessary bounded extension rather than claiming an existing implementation.

## `btn-danger-link` gap

- Two usages exist at `frontend/src/pages/super-admin/TcgSeriesTab.tsx:279,365`.
- `git grep 'btn-danger-link'` across all pinned `frontend/src/**/*.css` returned no definition. Therefore its actual appearance cannot be mapped from repository CSS evidence; it may currently be unstyled except inherited styles.
- The element at line 279 and the one at 365 are native buttons, but mapping to `variant="danger"` would add a full standardized danger button appearance and is a visible behavior change. There is no `link` variant. Required decision: accept standardized `danger` (likely `size="sm"` if intended as compact inline action) or establish a missing shared text-link action mold. Do not call it an exact migration.

## Placement and form/event preservation checklist for every call site

- Preserve element semantics. Native button sites can use `Button`; anchors/Links cannot.
- Preserve `type` exactly, including omission. An omitted type submits when inside or associated with a form.
- Preserve `form`, `name`, `value`, `formAction`/other native attributes and the submitter contract.
- Preserve `ref` type/identity; Button accepts `HTMLButtonElement` refs.
- Preserve handler function/body, event argument, `stopPropagation`, and navigation/write callbacks.
- Preserve caller `disabled` expression exactly. Do not replace it with `loading`, and do not add pending locks absent in current behavior.
- Preserve every `aria-*`, `data-*`, title and tooltip. For `iconOnly`, ensure an existing or newly translated `aria-label`; do not migrate an unnamed icon button as compliant.
- Translate only appearance tokens to `variant`/`size`/`iconOnly`/`fullWidth`. Use `layoutClassName` for verified outside placement classes (grid/flex placement, width contract), never for `btn-*`, icon danger, shape, color, padding, font or inline-style substitution.
- Existing inline `style` cannot be passed to Button and arbitrary `className` is rejected at compile time (`Button.tsx:38`; `Button.test.tsx:112–118`). A styled legacy site must first map the layout declaration to an already-approved layout class; appearance overrides require a design decision.
- State variants must be explicit. Never rely on Button's default primary/md during migration.

## Design and governance evidence

- `docs/specs/component-standard.md:39–67` gives the original semantic variant/size/options table, while lines 104–110 explicitly leave bare `btn-sm` redesign unresolved. The current implementation is newer than the document's old “existing class” wording; implementation/CSS is authoritative for actual classes.
- `docs/specs/design-system/component-ssot/page-header-v2/design.md:44–52` defines primary/secondary/ghost/tab roles, says shape/spacing/type are mold-owned, and prohibits caller class/style appearance overrides.
- `docs/adr/ADR-144-ui-component-governance.md:27–39,59–69` requires pages to use shared molds, requires stopping/reporting when none exists, and treats migration as a separate controlled track.

## Decisions that remain unresolved from pinned evidence

1. **Bare `btn-sm`:** choose a project-wide semantic mapping (`secondary sm` is the safest ordinary-action default) or approve case-by-case `ghost sm`; there is no exact mold.
2. **Anchors/Router Links:** no implemented shared link-button mold at the official base. Repository design already specifies a native-semantics-preserving ButtonLink batch; implement and register that bounded extension. Button `onClick` navigation is not an equivalent fallback.
3. **`btn-danger-link`:** no CSS definition and no Button `link` variant. Decide standardized danger versus a new text-danger action mold.
4. **Modal icon / hover-only danger icon:** current Button cannot reproduce pill radius or hover-only danger. Accept `ghost/danger iconOnly` visual standardization or approve a dedicated shared mold.
5. **Dynamic selected controls:** preserve primary/secondary for a mechanical migration; changing to `tab` needs an explicit semantics/visual decision.
6. **Inline appearance styles and custom button classes:** Button intentionally rejects them. Each needs an existing layout-only class or separate design; none can be hidden in `layoutClassName`.

These are evidence-backed blockers to claiming a lossless, all-sites mechanical conversion. All ordinary native `btn-primary/secondary/ghost/danger/outline` combinations, including supported `sm`, are expressible through the existing shared `Button` while preserving native props/events and accepting the documented shared-mold appearance changes.

## Finite verification strategy for the migration

- Keep the existing primitive `Button.test.tsx` as the proof for native type/form/submitter, ref identity, event/currentTarget/stopPropagation, disabled/loading, ARIA override order and appearance-prop rejection. Do not fabricate hundreds of page integration claims for behavior the primitive already proves.
- Generate a source-level before/after inventory keyed by file plus stable syntax/occurrence (not line number alone). For every migrated native button, inverse-compare all non-appearance attributes and children: element kind, explicit/omitted type, handlers including body text, disabled expression, ref/form/name/value, ARIA/data/title, conditional wrapper and order. Allowed deltas are tag/import plus removal of legacy class/style and addition of explicit Button appearance props.
- Add focused page tests only where migration transforms something beyond primitive forwarding: dynamic variant/ARIA state, row stopPropagation wiring, native form association/submit branches, link semantics through ButtonLink, and intentional removal of scoped/inline appearance overrides. These tests should assert existing outcomes or exact props/requests already observable, not claim unmeasured integration coverage.
- Run a final zero-audit for legacy `btn-*` consumers and separately report deliberate CSS definitions/catalog fixtures until their cleanup scope is approved. Ensure semantic link count is preserved as Link/a, not reduced by conversion to click handlers.
