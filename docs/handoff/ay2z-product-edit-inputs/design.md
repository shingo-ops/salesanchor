# AY-2z 設計: 商品編集ページの入力14欄を、濃い枠の種類（variant）product-edit として金型に登録して移す

状態: 設計審査済み（Fable APPROVE、/tmp/CC報告ファイル/ssot-ay2z/design-review.md）。PO「Y」2026-10-15。mode: handoff。親: docs/specs/design-system/README.md。ADR-144 / ADR-067 / ADR-027 を継承。
recon: docs/handoff/ay2z-product-edit-inputs/recon.md。実測: docs/handoff/design-system-recon/evidence-20260910/ay2z-acceptance.md。

## 1. 目的（PO が見える変化）
- 商品編集ページの入力欄14個が金型 TextFieldControl の管理下に入る。見た目と動きは変えない（濃い枠 --border-strong、角 4px、focus は影だけ）。
- docs/specs/design-system/design.md の保留（商品編集 14）が 0 になる。

## 2. 変更
- frontend/src/components/TextField.tsx: `TextFieldVariant` に `"product-edit"` を追加。
- frontend/src/components/FormField.css: `.comp-field__input.comp-input--product-edit`（min-height auto、border-color --border-strong、border-radius --radius-sm、font-family revert、line-height normal、transition initial）と `:focus`（border-color --border-strong）。新しい数値・色・トークンなし。
- frontend/src/company-forms.css: input 専用の3規則と説明コメントを削除（詳細度が種類より強く、残すと種類が効かないため）。textarea・select の規則は触らない。
- frontend/src/pages/products/ProductEditPage.tsx: 生 input 14件を `<TextFieldControl variant="product-edit"` へ。ほかの属性は逐語。ラッパーなし。
- 試験: TextField.test.tsx の VARIANTS に product-edit、新規 frontend/src/pages/products/ProductEditPage.inputs.test.tsx。story: TextField.stories.tsx に ControlProductEdit。

## 3. 触らない範囲
select・textarea・ボタン・label、ほかのページ、ほかの TextFieldControl 利用、i18n キー、API・backend・DB・migrations・deploy.yml・scripts。

## 4. 停止条件
B1 computed style 差、B2 class 以外の DOM 属性差またはラッパー増、B3 select・textarea・ボタンの差、B4 新しい数値・色・トークンが要る、B5 既存試験の失敗または書き換え、B6 stylelint・check:all・check:new-tokens・check-ui-governance・eslint の失敗。実測では B1〜B6 いずれも該当なし（ay2z-acceptance.md）。

## 5. 受入条件
|基準|検証方法|
|---|---|
|14欄が種類 product-edit を持つ|新規試験 ProductEditPage.inputs.test.tsx と実測 DOM|
|見た目が変わらない|8条件 × 3状態で computed style の差 0|
|DOM 属性が class 以外で同じ|実測の属性差 0|
|select・textarea・ボタンが変わらない|実測|
|既存試験が書き換えなしで通る|vitest|
|新しい色・数値なし、直書きなし|stylelint・check:all・check:new-tokens・check-ui-governance・eslint が exit 0|
|型・ビルド|tsc・build・build-storybook・test:coverage|
|本番|merge 後、本番 CSS に `.comp-field__input.comp-input--product-edit` があり `.product-edit-form .form-group input:not(` が 0 件。app と /api/health が 200|

## 外部・過去事例の参照と我々への応用
- 外部事例は不要（自社の金型へ自社の現行の見た目を写す便。自社の実物の前後比較が直接の根拠）。
- 過去事例: docs/specs/design-system/design.md の §AY-2b login。旧ページ規則の詳細度が種類より強く、同じ便で撤去して実測差 0 を確認した。本便も同じ手順（種類の登録、旧規則の撤去、前後の実測比較）を適用した。
- 代替案: B 標準へ統一（枠が --border に戻り「薄くて見えない」が再発するため不採用）、C company-forms.css を残して className で付ける（見た目の定義が金型の外に分かれ SSOT に反するため不採用）。

## 戻し方
本 PR の merge commit を revert する（DB の影響なし）。

## 維持の仕組み
守り手: frontend/src/components/TextField.tsx、frontend/src/components/FormField.css、frontend/src/components/TextField.test.tsx（VARIANTS）、frontend/src/pages/products/ProductEditPage.inputs.test.tsx、docs/CC_UI_GOVERNANCE.md、scripts/check-ui-governance.js。
- 商品編集の入力が金型を外れる（生 input に戻る）と ProductEditPage.inputs.test.tsx が落ちる。
- 種類の class 名が変わると TextField.test.tsx の VARIANTS が落ちる。
- 生 input・色直値は check-ui-governance と stylelint が止める。
