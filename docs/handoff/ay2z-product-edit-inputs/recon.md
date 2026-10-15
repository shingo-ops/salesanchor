# AY-2z recon（商品編集ページの入力14欄）

基準: origin/main 4c9d037ef。生出力: /tmp/CC報告ファイル/ssot-ay2z/recon/。設計: docs/handoff/ay2z-product-edit-inputs/design.md。

## 既存 ADR の検索
- 継承元は ADR-144（UI 部品は金型へ）、ADR-067（デザイントークン）、ADR-027（i18n、本便は文言の変更なし）。docs/specs/design-system/design.md の §AY-2a・§AY-2b が前例。
- 2026-10-05 の PO 方針「③商品編集9か所は『枠が薄い』問題があるため保留して別に確認」（docs/specs/design-system/design.md の AY-2a 根拠節）を受け、2026-10-15 に PO「Y」で種類として登録する方針に決定。

## 金型（変更前）
- frontend/src/components/TextField.tsx:33 `TextFieldVariant`（standard・karte・search・schedule・composer・login）。
- frontend/src/components/TextField.tsx:43-52 class の付与（`comp-input--${variant}`）。
- frontend/src/components/FormField.css:47-61 基本 (0,1,0)、:95-102 focus (0,2,0)、:409-428 login の種類、:445-451 モバイル min-height (0,1,0)。
- frontend/src/components/TextField.test.tsx:202 `VARIANTS`。
- frontend/src/components/TextField.stories.tsx:112-131 variant の story。

## 商品編集の現在
- frontend/src/pages/products/ProductEditPage.tsx の生 input 14件: :215、:224、:251、:262（type="date"）、:270、:274、:294、:298、:317、:321、:325、:329、:333、:337。select 9、textarea 1（:309）。id・name・className・style は 14件とも無い。
- frontend/src/company-forms.css:210-231 に input 専用の3規則（`.product-edit-form .form-group input:not([type="checkbox"]):not([type="radio"])`）。詳細度は (0,4,1)/(0,5,1) で、種類の (0,2,0)/(0,3,0) より強い。残すと種類が効かない（§AY-2b login と同じ構図）。textarea の規則は :233 以降で別。
- frontend/src/company-forms.css:210 の旧コメント「入力枠が薄くて見えない問題の解消」が --border-strong の理由。

## 試験の制約
- frontend/src/components/CommerceSubmitButtonMigration.test.tsx:43 が form 内の input・select・textarea を DOM 順に 24個と確認し、:148 が index で触る。ラッパー追加・順序変更・個数変更は壊す。
- frontend/src/components/CommerceNavigationButtonMigration.test.tsx:107、:127 も ProductEditPage を描画する。

## 実測の前例
- /tmp/CC報告ファイル/ssot-ay2x/impl/ay2x-measure.spec.ts と frontend/tests-e2e/product-edit-tcg-type.spec.ts:1-125。
