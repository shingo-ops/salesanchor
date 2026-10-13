# recon: 在庫検索バー（InventorySearchBar）の入力欄の標準化（AY-2n）

調査全文: /tmp/CC報告ファイル/ssot-ay2n/recon-raw.md（origin/main 5cb680d05 時点。実装時の基準は 28c3e8e8f）。

## 現在地（変更前。行番号は変更前の frontend/src/components/InventorySearchBar.tsx）
- 生 `<input type="text">` 1件: frontend/src/components/InventorySearchBar.tsx:272-287。style は :285 `{ flex: 1, minWidth: "var(--min-width-input-sm)", padding: "var(--space-6px) var(--space-2)" }`。className なし。
- ref: frontend/src/components/InventorySearchBar.tsx:119（inputRef）、:126-127（getBoundingClientRect で候補一覧の位置と幅）、:152（contains で外側クリック判定）、:273。
- AND/OR の切り替え（生 `<button>` 2つ）: frontend/src/components/InventorySearchBar.tsx:288-330。
- 使用元2か所: frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:410-414（testIdPrefix="invoice-add-search"）、frontend/src/pages/quote-create/QuoteCreatePage.tsx:259-263（"quote-add-search"）。外側の div は幅 min(100%, 40rem)。
- 金型: frontend/src/components/TextField.tsx:41-54（TextFieldControl、forwardRef で ref を input に渡す）。ラベル付きの TextField（:57）は ref を受けない。
- variant "search": frontend/src/components/FormField.css:359-377（左にアイコン前提の余白）。既存の利用は frontend/src/pages/inbox/InboxConversationList.tsx:75 のみ。
- 試験の依存: frontend/tests-e2e/quote-create-inventory-search.spec.ts:94-133（testid・placeholder・aria-pressed・fill）。単体試験の参照0。stories は testid 非依存。
- CI の e2e: .github/workflows/e2e.yml:207 `if: false`。
- 請求書は既定 mode="quote"（frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:75）で検索欄が出ない（:252）。invoice-mode-inventory（:239）を押してから出る。明細の名前欄は :355 の invoice-item-row-${i}-name。

## ADR 検索結果
- ADR-144（UIガバナンス）: 生 input の新規追加禁止。docs/CC_UI_GOVERNANCE.md。今回は生 input を金型へ置き換える側。
- ADR-067（デザイントークン強制）: 新トークンなし。
- ADR-027（i18n）: t() のキーは変えない。
