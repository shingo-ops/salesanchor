# AY-3a 設計: 商品編集ページの選択欄9・複数行欄1を、濃い枠の種類（variant）product-edit として金型に登録して移す

状態: 設計審査済み（Fable r2 APPROVE、/tmp/CC報告ファイル/ssot-pe2/design-review.md）。PO「Y」2026-10-15。mode: handoff。親: docs/specs/design-system/README.md。ADR-144 / ADR-067 / ADR-027 を継承。
recon: docs/handoff/ay3a-product-edit-select-textarea/recon.md。実測: docs/handoff/design-system-recon/evidence-20260910/ay3a-acceptance.md。

## 1. 目的（PO が見える変化）
- 商品編集ページの選択欄9個と複数行欄（備考）1個が金型（SelectControl・TextareaControl）の管理下に入る。
- 見た目と動きは変えない（濃い枠 --border-strong、角 4px、選択欄は OS 標準の▽、focus は影だけで枠色は変わらない）。
- company-forms.css の商品編集専用規則が0になる。

## 2. 変更
- frontend/src/components/Select.tsx: `SelectVariant` に `"product-edit"`。frontend/src/components/Textarea.tsx: `TextareaVariant` に `"product-edit"`。ヘッダコメントに1行ずつ。
- frontend/src/components/FormField.css（input の product-edit の直後）: `.comp-select__control.comp-select--product-edit`（min-height auto、max-width none、padding-right --space-3、border-color --border-strong、border-radius --radius-sm、background-image none、background-repeat・background-position・font-family・cursor・appearance・-webkit-appearance は revert、line-height normal、transition initial）と `:focus`。`.comp-field__textarea.comp-textarea--product-edit`（border-color、border-radius、font-family revert、line-height normal、transition initial）と `:focus`。新しい数値・色・トークンなし。
- frontend/src/company-forms.css: select・textarea の商品編集規則と説明コメント（:210-249）を削除。
- frontend/src/pages/products/ProductEditPage.tsx: select 9件を `<SelectControl variant="product-edit" fullWidth`、textarea 1件を `<TextareaControl variant="product-edit"` へ。ほかの属性・子要素は逐語。ラッパーなし。
- 試験: ProductEditPage.inputs.test.tsx の断言を書き換え、Select.test.tsx の VARIANTS と Textarea.test.tsx の it.each に product-edit。story: Select.stories.tsx・Textarea.stories.tsx に1件ずつ。

## 3. 触らない範囲
ほかのページ、ほかの SelectControl・TextareaControl 利用、label、fieldset・legend、input 14件、ボタン、option の文言、i18n キー、API・backend・DB・migrations・deploy.yml・scripts。

## 4. 停止条件
B1 computed style 差、B2 class 以外の DOM 差・option 差・ラッパー増、B3 input・ボタンの差、B4 新しい数値・色・トークンが要る、B5 既存試験の失敗または書き換え、B6 stylelint・check:all・check:new-tokens・check:i18n-missing-keys・check-ui-governance・eslint・tsc の失敗、B7 `.product-edit-form` の select・textarea 規則が他ページに当たる。実測では B1〜B7 いずれも該当なし（ay3a-acceptance.md）。

## 5. 受入条件
|基準|検証方法|
|---|---|
|select 9・textarea 1 が種類 product-edit を持つ|ProductEditPage.inputs.test.tsx と実測 DOM の class|
|見た目が変わらない|8条件 × 3状態で computed style の差 0|
|DOM・選択肢が class 以外で同じ|実測の属性・option 差 0|
|input・ボタンが変わらない|実測|
|既存試験が書き換えなしで通る|vitest|
|新しい色・数値なし、直書きなし|stylelint・check:all・check:new-tokens・check-ui-governance・eslint が exit 0|
|型・ビルド|tsc・build・build-storybook・test:coverage|
|本番|merge 後、本番 CSS に `.comp-select__control.comp-select--product-edit` と `.comp-field__textarea.comp-textarea--product-edit` があり、`.product-edit-form .form-group select` と `.product-edit-form .form-group textarea` が 0 件。app と /api/health が 200|

## 外部・過去事例の参照と我々への応用
- 外部事例は不要（自社の金型へ自社の現行の見た目を写す便。自社の実物の前後比較が直接の根拠）。
- 過去事例: docs/specs/design-system/design.md の §AY-2z（同じページの input、旧規則を同じ便で撤去して実測差 0）と §AY-2b login。本便も同じ手順（種類の登録、旧規則の撤去、前後の実測比較）を適用した。select 固有の差（max-width・background-repeat・background-position）は設計審査 r1 の指摘で revert 宣言を足した。
- 代替案: B 標準へ統一（枠が --border に戻り「薄くて見えない」が再発し、▽も SVG に変わるため不採用）、C company-forms.css を残して className で付ける（見た目の定義が金型の外に分かれ SSOT に反するため不採用）。

## 戻し方
本 PR の merge commit を revert する（DB の影響なし）。

## 維持の仕組み
守り手: frontend/src/components/Select.tsx、frontend/src/components/Textarea.tsx、frontend/src/components/FormField.css、frontend/src/components/Select.test.tsx（VARIANTS）、frontend/src/components/Textarea.test.tsx、frontend/src/pages/products/ProductEditPage.inputs.test.tsx、docs/CC_UI_GOVERNANCE.md、scripts/check-ui-governance.js。
- 商品編集の select・textarea が金型を外れる（生要素に戻る）と ProductEditPage.inputs.test.tsx が落ちる。
- 種類の class 名が変わると Select.test.tsx・Textarea.test.tsx が落ちる。
- 生 select・色直値は check-ui-governance と stylelint が止める。
