# recon（入力部品の寸法 現状全数調査）

> この文書は何か（専門用語なしの1行）:
> 今のプルダウン・入力欄の高さと幅が、どこにどんな値で散らばっているかを実測した記録。
> 親: [../../specs/design-system/component-ssot/field-size/README.md](../../specs/design-system/component-ssot/field-size/README.md)

実測SHA: 51c9d1263bbff537de7c1ffedaab6d491927085b

## 主要引用（path:N）
- `frontend/src/components/FormField.css:49`
- `frontend/src/components/FormField.css:75`
- `frontend/src/components/FormField.css:89`
- `frontend/src/components/FormField.css:139`
- `frontend/src/components/FormField.css:164`
- `frontend/src/components/FormField.css:195`
- `frontend/src/components.css:166`
- `frontend/src/components.css:172`
- `frontend/src/components/Select.tsx:15`
- `frontend/src/components/Select.tsx:25`
- `frontend/src/components/Select.tsx:36`
- `frontend/src/components/Select.tsx:45`
- `frontend/src/pages/leads/LeadsPage.tsx:272`
- `frontend/src/pages/leads/LeadsPage.tsx:274`
- `frontend/src/pages/purchase-orders/PurchaseOrdersPage.tsx:182`
- `frontend/src/pages/purchase-orders/PurchaseOrdersPage.tsx:196`

## 高さの現状（3系統）
- md既定: min-height指定なし・padding依存（frontend/src/components/FormField.css:47-51）
- sm: --comp-input-height-sm（FormField.css:139）
- lg/mobile: --comp-input-height-mobile（FormField.css:164, :195）

## 幅の現状（3系統）
- width:100%: .comp-field__select / .comp-field__input / .comp-select__control--full（FormField.css:51, :86, :174）
- auto+max-width: .comp-select__control（FormField.css:89-91）
- min-widthトークン: .search-bar input / .filter-bar select = --input-select-min-w（components.css:172-178）

## 影響範囲
- Select金型使用: 23ファイル（内フィルタ用途とフォーム用途が混在）
- 生select残存: 38ページ（金型未適用・要寄せ。例: PurchaseOrdersPage）
- 既存 Select size型: sm/md/lg は高さ/padding寄り・幅は fullWidth 別prop（Select.tsx:15,25,36,45-46）

## 手本
- リード（LeadsPage.tsx）: Select金型経由・操作台に載せ替え済み（#3009）
- 発注管理（PurchaseOrdersPage.tsx）: 生select・page-content-actions別系統（未載せ替え）
