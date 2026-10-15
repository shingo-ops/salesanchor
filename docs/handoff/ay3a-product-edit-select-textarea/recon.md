# AY-3a recon（商品編集ページの選択欄9・複数行欄1）

基準: origin/main 597a1a80d。生出力: /tmp/CC報告ファイル/ssot-pe2/（summary.md ほか）。設計: docs/handoff/ay3a-product-edit-select-textarea/design.md。

## 既存 ADR の検索
- 継承元は ADR-144（UI 部品は金型へ）、ADR-067（デザイントークン）、ADR-027（i18n、本便は文言の変更なし）。docs/specs/design-system/design.md の §AY-2z（同じページの input 14件）が前例。
- 2026-10-05 の PO 方針「③商品編集9か所は『枠が薄い』問題があるため保留して別に確認」（docs/specs/design-system/design.md:2043）を受け、2026-10-15 に PO「Y」で種類として登録する方針に決定。

## 金型（変更前）
- frontend/src/components/Select.tsx:17 `SelectVariant`（standard・karte・header・tabbar）。:52-55 は bare 専用の型制約。:83 で class `comp-select--${variant}` を付与。
- frontend/src/components/Textarea.tsx:31 `TextareaVariant`（standard・karte・embedded・composer・schedule）。:49 で class `comp-textarea--${variant}`。
- frontend/src/components/FormField.css:47-62 基本、:65-68 textarea 専用、:74-83 select の bare 由来（background-repeat・background-position を含む）、:89-92 `max-width: 100%`、:95-102 focus、:178 fullWidth、:430-442 input の product-edit（AY-2z）、:459-464 モバイル min-height。
- frontend/src/components/Select.test.tsx:280 `VARIANTS`、frontend/src/components/Textarea.test.tsx:183 it.each、frontend/src/components/Select.stories.tsx:127-135、frontend/src/components/Textarea.stories.tsx:109-112。

## 商品編集の現在
- frontend/src/pages/products/ProductEditPage.tsx の生 select 9件: :232、:239、:256、:279、:286、:303、:347、:354、:361。生 textarea 1件: :310。form は :210 の `.product-edit-form`。
- frontend/src/company-forms.css:210-249 に select・textarea の商品編集専用規則（`.product-edit-form .form-group select` / `textarea` と各 `:focus`）。詳細度 (0,2,1)/(0,3,1) が種類 (0,2,0)/(0,3,0) より強く、残すと種類が効かない。
- `.product-edit-form` の利用は ProductEditPage.tsx:210 と company-forms.css、試験の data-testid 参照のみ（frontend/src 全体の grep、他ページなし）。

## 試験の制約
- frontend/src/components/CommerceSubmitButtonMigration.test.tsx:42 と :148 が form 内の input・select・textarea を DOM 順で触る。ラッパー追加・順序変更は壊す。
- frontend/src/components/CommerceNavigationButtonMigration.test.tsx:107、:127 も ProductEditPage を描画する。
- frontend/src/pages/products/ProductEditPage.inputs.test.tsx:37-39 は select・textarea に `comp-` が無いことを断言していた（本便で書き換え）。
