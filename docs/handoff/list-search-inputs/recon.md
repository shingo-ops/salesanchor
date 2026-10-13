# recon: 一覧画面の検索欄5件の標準化（AY-2p）

調査全文: /tmp/CC報告ファイル/ssot-ay2p/recon-raw.md・recon-fieldw.md・recon-searchbar.md（origin/main d39e251 時点。実装時の基準は 6c8a5955a。行番号は変更前のもの）。

## 現在地（変更前）
- S1 frontend/src/pages/companies/CompaniesPage.tsx:387-393 `<input type="text" className="search-input field-h-md field-w-md" placeholder={t("companies.searchPlaceholder")} value onChange>`（ContentToolbar left 内）。TextFieldControl は frontend/src/pages/companies/CompaniesPage.tsx:30 で import 済み。
- S2 frontend/src/pages/contacts/ContactsPage.tsx:282-288 `<input type="text" … className="search-input field-h-md field-w-sm">`。直前 :276 に SelectControl field-w-sm。TextFieldControl は frontend/src/pages/contacts/ContactsPage.tsx:33 で import 済み。
- S3 frontend/src/pages/inventory/InventoryPage.tsx:384-395 `<input type="search" className="field-h-md field-w-md" data-testid="inventory-search" … onKeyDown>`。兄弟は Button sm ×3（:397 ほか）。import なし。
- S4 frontend/src/pages/orders/OrdersFilterBar.tsx:32-40 `<input type="search" className="field-h-md field-w-md" aria-label={t("orders.title")} placeholder={t("common.search")} data-testid="orders-search-input">`。e2e 6件が testid で参照（frontend/tests-e2e/orders-list.spec.ts:154,222、frontend/tests-e2e/order-commission.spec.ts:376 ほか）。import なし。
- S5 frontend/src/pages/products/ProductsPage.tsx:218-219 親 `<div className="search-bar" style={{display:"flex",gap:"var(--space-4)",alignItems:"center"}}>`、`<input className="field-h-md field-w-sm" type="text" placeholder={t("common.search")} value onChange>`。import なし。
- 5件とも ref・ui-allow なし。`.search-input` に当たる CSS 規則は0（死にクラス）。
- 変更前の見た目（実測 /tmp/CC報告ファイル/ssot-ay2p/before2/measure-before2.json）: S1〜S4 はブラウザ既定（padding 0・2px inset・角0・13.33px）、高さ 36（frontend/src/components/field-size.css:8 の min-height）。S5 は frontend/src/components.css:56-65 `.search-bar input`（1px・角4px・min-width）で幅 280（field-w-sm 160 は min-width に負けている）。
- TextFieldControl は className を input 自身に付ける（frontend/src/components/TextField.tsx:43-50）。`.comp-field__input{width:100%}`（frontend/src/components/FormField.css:47-62）は field-size.css より後に読み込まれ詳細度が同じなので `field-w-*` が負ける（実測で 280 にならず 301.8）。SelectControl は前例 AW-2b（#4033）の複合セレクタ `.comp-select__control.field-w-*`（frontend/src/components/field-size.css:13-16）で解決済み。TextFieldControl に field-w-*/field-h-* を渡す既存箇所は0件（本実装前の走査）。
- `.search-bar` は frontend/src/pages/products/ProductsPage.tsx の div と、frontend/src/pages/conditions/ConditionsPage.tsx:394・frontend/src/pages/product-categories/ProductCategoriesPage.tsx:273・frontend/src/pages/status-master/StatusMasterPage.tsx:340・frontend/src/pages/suppliers/SuppliersPage.tsx:158・frontend/src/pages/units/UnitsPage.tsx:232 の form（計6）で使う共有クラス。規則は frontend/src/components.css:50-65 のみ。
- 幅 767px 以下は frontend/src/components/FormField.css:442-448 の min-height（--comp-input-height-mobile）が field-h-md に勝つ。ContentToolbar は frontend/src/components/ContentToolbar.css:12 に min-height field-h-md。

## ADR 検索結果
- ADR-144（UIガバナンス）: 生 input の新規追加禁止。今回は生 input を金型へ置き換える側。docs/CC_UI_GOVERNANCE.md。
- ADR-067（デザイントークン強制）: 新トークンなし。
- ADR-027（i18n）: placeholder・aria-label の t() キーは変えない。
- ADR-1003（GO の委任）: GO は Claude Opus が発行。
