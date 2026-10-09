# ay2b-after-check（実装後の実測。Chromium 147.0.7727.15、幅 1280・375、light）

方法: ay2b-visual.cjs after-real。before / 事前予測 after の CSS は git HEAD（base fb036a238）、after-real の CSS は作業ツリーの実ファイル（components.css 絞り込み規則・pages-layout.css・company-forms.css 独立規則・FormField.css login 規則を含む）。after-real の DOM は ay2b-ast-check.json の after（実装後の TSX の AST）から class（comp-field__input [+ comp-input--login]）・type・inline style・disabled を読む。祖先連鎖は base 時点の静的解決（移管で祖先は変わらない=ast-check で確認）。
状態: normal・focus、disabled 属性がある要素は disabled も。

| # | 区分 | 測定数 | 要素数 | 差のある数 | 期待 | 判定 |
|---|---|---|---|---|---|---|
| 1 | text 系 140: after-real vs 事前予測 after | 280 | 140 | 0 | 0 | ○ |
| 2 | ログイン 3: before vs after-real | 6 | 3 | 0 | 0 | ○ |
| 3 | 商品編集 14: before vs after-real | 28 | 14 | 0 | 0 | ○ |
| 4 | 非 text: before vs after-real（確定 9 + 祖先未確定 10） | 0（未測定） | - | - | 0 | 未測定（下の注） |
| 5 | .form-group 内の既存 TextField 代表: before vs after-real（角丸以外） | 12 | - | 0 | 角丸以外 0（角丸 4→6px は許容） | ○ |

(5) の角丸差のあった代表: 12/12

## 食い違い

なし

## 参考: inline style を持つ 4 件の after-real（配置宣言は保持、InventoryPicker の padding は外れて標準の余白）

- frontend/src/components/InventoryPicker.tsx:217 inline(before)=width:100%;min-width:var(--min-width-input-sm);padding:var(--space-6px) var(--space-2)
- frontend/src/pages/purchase-orders/PurchaseOrdersFormModal.tsx:191 inline(before)=min-width:var(--min-width-input-sm)
- frontend/src/pages/purchase-orders/PurchaseOrdersFormModal.tsx:194 inline(before)=width:var(--input-width-qty)
- frontend/src/pages/purchase-orders/PurchaseOrdersFormModal.tsx:197 inline(before)=width:var(--input-width-year)

## 参考: (1) の before → after-real で差のある要素（幅1280・sig0）: 140 / 140（角丸・書体・行の高さ等。主な値は ay2b-visual.md §1）

## 注（再実行時の入力欠落）

(4) 非 text 19 件は未測定。祖先連鎖の調査入力 /tmp/CC報告ファイル/ay2b-recon/（415行版 ay2-applied-css.json・ay2b-mold-users.json）が失われ、evidence の ay2-applied-css.json（360行）に該当行が無いため、スクリプトは該当行を飛ばした。代替: 実装前に同じ絞り込み規則で 102 条件・差分0 を確認した ay2b-nontext-keep.json。実装の components.css は同じ4型の絞り込みで宣言不変（git diff で確認）。(5) の既存 TextField 代表 12 は、ay2b-visual.json の moldUsers 6代表から入力を再構成して測定（祖先は先頭5段まで）。
