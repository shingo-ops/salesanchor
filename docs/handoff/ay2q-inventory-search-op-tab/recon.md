# recon: 在庫検索バー AND/OR 切替の金型化（AY-2q）

調査全文: /tmp/CC報告ファイル/ssot-ay2q/recon-raw.md、変更前の実測 /tmp/CC報告ファイル/ssot-ay2q/before/ay2q-measure-before.json（origin/main d3e8327016f5 時点。実装時の基準は 0819129aa。行番号は変更前のもの）。

## 現在地（変更前）
- 行 div: frontend/src/components/InventorySearchBar.tsx:272 `<div style={{ display: "flex", gap: "var(--space-2)", alignItems: "center" }}>`（検索欄 TextFieldControl と AND/OR 群を並べる）。
- 群 div: frontend/src/components/InventorySearchBar.tsx:289-334 `role="radiogroup"`、`title`（無効時の理由）、`display: inline-flex`・`gap: 0`・`border: 1px solid var(--border-color)`・`borderRadius: var(--radius-sm)`・`opacity: opToggleDisabled ? var(--opacity-disabled) : 1`、`data-testid={`${testIdPrefix}-op-toggle`}`。
- AND: frontend/src/components/InventorySearchBar.tsx:302-317 className なしの生 `<button type="button">`。inline style（padding `var(--space-1) var(--space-10px)`・border none・background `var(--accent-bg)`／transparent・color `var(--on-accent)`／inherit・cursor）、`aria-pressed={op === "and"}`、`disabled={opToggleDisabled}`、`data-testid={`${testIdPrefix}-op-and`}`。
- OR: frontend/src/components/InventorySearchBar.tsx:318-333 同じ形（op === "or"）。
- 状態: frontend/src/components/InventorySearchBar.tsx:104（op の useState）。API 呼出: frontend/src/components/InventorySearchBar.tsx:175 `op=${currentOp}`。
- 使用ページ: frontend/src/pages/quote-create/QuoteCreatePage.tsx:259（`<form>` は :145）、frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:410（`<form>` は :290）。いずれも InventorySearchBar は form の中にある。
- 金型: frontend/src/components/buttonAppearance.ts:1（型 ButtonVariant に "tab"）、:10（VARIANT_CLASS tab → comp-btn--tab）、:32（isTab && active → comp-btn--active）。frontend/src/components/Button.tsx:40（className・style のみ Omit）、:52（disabled は明示 prop）、:54・:67（その他は rest で渡る）、:64（`aria-pressed={isTab ? active : undefined}`）。type 属性の既定は無い。
- 金型の見た目: frontend/src/components/Button.css:8（white-space: nowrap）、:9（min-height var(--field-h-md)）、:10（padding var(--space-2) var(--space-5)）、:11-12（border 1px transparent・角 var(--comp-btn-radius)）、:78-113（tab と active）、:115（focus-visible）、:120-123（disabled の opacity）、:166-168（767px 以下 min-height var(--size-icon-btn-lg)）。
- 既存の tab 利用: frontend/src/pages/company-detail/CompanyDetailPage.tsx:104-119、frontend/src/features/tcg-import-review/ReviewSection.tsx:252。試験: frontend/src/components/Button.test.tsx:103。
- e2e: frontend/tests-e2e/quote-create-inventory-search.spec.ts:106-117（AND/OR の aria-pressed）。.github/workflows/e2e.yml:207 `if: false` で CI では動かない。
- 検出: frontend/scripts/check-ui-governance.js は生 `<button` を検出しない（select・input・自作タブのみ）。
- 変更前の見た目（実測 before/ay2q-measure-before.json、quote-w1280）: AND/OR とも高さ 29・padding 4px 10px・13.33px・weight 400。選択中 rgb(30,58,138)・白文字、未選択は透明・rgb(26,32,44)。hover 変化なし。focus は `rgb(0,95,204) auto 1px`。無効時は群 opacity 0.6。幅 375 は文言が2〜3行に折返し（各 71px、群 73px、行幅 279）。

## ADR 検索結果
- ADR-144（UI ガバナンス・金型優先）: 生 button を金型へ置き換える側。docs/adr/ADR-144-ui-component-governance.md、docs/CC_UI_GOVERNANCE.md。
- ADR-067（デザイントークン）: 新トークンなし。
- ADR-027（i18n）: 既存キー opAnd・opOr・opGroupLabel・opNeedsMultipleTokens をそのまま使用（新規文字列なし）。
- AY-2n（#4223）: 同じコンポーネントの検索欄を金型化済み。docs/specs/design-system/design.md の AY-2n 節。
