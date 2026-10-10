# AY-2k recon: 請求書作成・見積作成の明細入力欄 14件

実測時の origin/main: 34da7b297（調査の基準は 994543744。対象行・金型・FormField.css の差分は 0）。調査全文は /tmp/CC報告ファイル/ssot-ay2k/recon.md。
既存 ADR の検索: ADR-027（i18n・変更なし）、ADR-144（UI 金型）、ADR-067（デザイントークン。トークン表は docs/adr/ADR-067-design-token-enforcement.md）。

## 1. 現在地（変更前）
- 対象は14件の生 `<input`。請求書 frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:343,350,368,372,385,388,391 の7件、見積 frontend/src/pages/quote-create/QuoteCreatePage.tsx:192,199,217,221,234,237,240 の7件。2画面は共有部品ではなく複製。
- 14件とも table.data-table のセルの中。className なし、CSS 規則0。インライン style はすべてトークン。
- 単価欄は frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:388 と frontend/src/pages/quote-create/QuoteCreatePage.tsx:237（width var(--input-width-year) = 90px、frontend/src/tokens.css:425）。
- 金型 frontend/src/components/TextField.tsx（TextFieldControl、size sm|md|lg）、外観 frontend/src/components/FormField.css:47-62、sm は :133-140。
- TextFieldControl の import は両ファイルに既存（frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:27、frontend/src/pages/quote-create/QuoteCreatePage.tsx:32）。
- 試験の依存: frontend/src/components/CommerceSubmitButtonMigration.test.tsx（testid と spinbutton の順）、frontend/tests-e2e/quote-create-inventory-search.spec.ts:137,:143。
- 別枠: frontend/src/components/InventorySearchBar.tsx:272（1件）、frontend/src/components/FedExRateModal.tsx:176,193,210,239（4件）。
- groups.cjs（/tmp/CC報告ファイル/ssot-ay2d/tools/groups.cjs）での対象総数: 70（変更前）。

## 2. 実測で分かったこと
- 初回実装（単価 90px のまま）で、単価の値 12345.67 が金型 sm の余白と枠で切れた（scrollWidth 90 / clientWidth 88、4画面とも）。
- 対策: 単価用トークン --input-width-price（120px）を frontend/src/tokens.css に追加し、単価欄2件だけに使う（design.md 参照）。
