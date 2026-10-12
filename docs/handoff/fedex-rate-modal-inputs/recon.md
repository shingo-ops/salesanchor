# recon: FedEx 送料比較モーダルの入力欄の標準化（AY-2m）

調査全文: /tmp/CC報告ファイル/ssot-ay2m/recon-raw.md（origin/main 8fa6deb41 時点。実装時の基準は 0f3ce723a で、対象行は一致を確認済み）。

## 現在地（変更前。行番号は変更前の frontend/src/components/FedExRateModal.tsx）
- 生 `<input` 4件: frontend/src/components/FedExRateModal.tsx:176（発送元）、:193（宛先国コード）、:210（重量）、:239（郵便番号）。
- 各 `<label>`: frontend/src/components/FedExRateModal.tsx:170-175、:187-192、:204-209、:233-238。
- input の style の px 直書き: frontend/src/components/FedExRateModal.tsx:183、:200、:217、:246（width 80/80/100/160px、padding 6px 8px、border 1px、borderRadius 4px、fontSize 13px）。
- label の style の px 直書き: frontend/src/components/FedExRateModal.tsx:172、:189、:206、:235。
- 枠の余白の px 直書き: frontend/src/components/FedExRateModal.tsx:167（marginBottom 12px）、:168（gap 16px・marginBottom 8px）、:232（marginBottom 16px）。
- Modal・Button は金型使用済み: frontend/src/components/FedExRateModal.tsx:20-21。
- 使用元は1か所: frontend/src/pages/quote-create/QuoteCreatePage.tsx:289（開くボタン :270、data-testid="fedex-estimate-btn"）。
- 試験の依存: frontend/src/components/FedExRateModal.test.tsx:73,:124,:134（getByLabelText）、:78-79（getByDisplayValue・id 確認）。e2e の参照 0。
- 金型: frontend/src/components/TextField.tsx:57-103（TextField。ラベル comp-field__label、id 素通し）。frontend/src/components/FormField.css:17-22（.comp-field: flex 縦、gap var(--space-1)、margin-bottom var(--space-4)）。
- トークン: frontend/src/tokens.css:165（--field-w-sm 160px）、:425（--input-width-weight 80px）、:427（--input-width-price 120px）。国コード・発送重量用のトークンは無い。

## ADR 検索結果
- ADR-067（デザイントークン強制）: docs/adr/ADR-067-design-token-enforcement.md。トークン表に新トークン2行を追記する。
- ADR-144（UIガバナンス）: docs/adr/ADR-144 系。生 input の新規追加禁止。docs/CC_UI_GOVERNANCE.md。今回は生 input を金型へ置き換える側。
- ADR-027（i18n）: docs/adr/ADR-027-ui-internationalization.md。ラベルの t() キーは変えない。
- docs/CC_UI_GOVERNANCE.md: 金型を先に使う規約。

## 変更前の実測
frontend の変更前計測: docs/handoff/design-system-recon/evidence-20260910/ay2m-measure-before.json、ay2m-before-1280.png、ay2m-before-1440.png。
