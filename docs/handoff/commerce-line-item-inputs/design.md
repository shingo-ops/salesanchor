# AY-2k design: 請求書・見積の明細入力欄を金型 TextFieldControl sm へ

正本は docs/specs/design-system/design.md の「#### AY-2k」節（契約改訂・実装結果を含む）。本ファイルは PR 用の写し。recon は docs/handoff/commerce-line-item-inputs/recon.md。対象 ADR: ADR-027（docs/adr/ADR-027-ui-internationalization.md）、ADR-144、ADR-067（docs/adr/ADR-067-design-token-enforcement.md）。

## 変更契約
1. 14件の `<input` を `<TextFieldControl size="sm"` に置換（属性・style・onChange は逐語保持、自己終了のまま）。
1b. frontend/src/tokens.css に --input-width-price: 120px を追加し、単価欄（unit_price）2件の style の幅だけを var(--input-width-price) にする。--input-width-year は他の4か所が使うため変えない。
2. import は既存（frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:27、frontend/src/pages/quote-create/QuoteCreatePage.tsx:32）のため追加0行。
3. トークン表 docs/adr/ADR-067-design-token-enforcement.md に1行追記（node scripts/generate-adr-index.js 実行済み、README 差分なし）。
4. 変更しない: 金型本体、CSS、i18n、API、backend、試験・e2e、InventorySearchBar、FedExRateModal。

## 受入
|基準|検証方法|
|---|---|
|並びと幅が保たれる|開発モード build と preview（偽ログイン・API モック・明細2行）、幅1280・1440、DPR2。各欄の幅が前後 ±2px（単価 90→120 と商品名 -30 を除く）、表の幅 ±2px、横はみ出しは前と同じ（ay2k-measure-before.json、ay2k-measure-after.json）|
|単価が切れない|12345.67 でフォーカス無し・有りの両方で scrollWidth <= clientWidth（ay2k-measure-after.json の priceCheck）|
|外観が前後表どおり|computed style を前後採取。name_en の font-weight、product_name の color・font-size は同じ|
|非外観属性が不変|git diff origin/main -- frontend/src（ay2k-diff.txt）が置換14行と tokens.css +1 以外に無い|
|置換漏れ0|groups.cjs の targets が 70→56|
|試験|単体試験全件成功。変えた expect 0件。e2e の testid（frontend/tests-e2e/quote-create-inventory-search.spec.ts:137,:143）が保持|
|品質|tsc、lint、check:all、test:coverage 相当、build、build-storybook（ay2k-chk-*）|
|本番|Deploy 成功。app と /api/health が 200（merge 後）|

## 維持の仕組み
守り手: frontend/src/components/TextField.test.tsx、frontend/src/components/CommerceSubmitButtonMigration.test.tsx、.github/workflows/frontend-check.yml。切戻しは merge commit の revert（DB 影響なし）。

## 外部・過去事例の参照と我々への応用
外部事例: 不要（既存金型の踏襲）。過去事例: AY-2e、AY-2j（PR #4119）。
