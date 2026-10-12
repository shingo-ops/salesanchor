> 基準: 本ファイルは snapshot origin/main 946e6dbcdffa7e314b119cb9cd67b400182a679a で生成。frontend/src は 55d99a97e441b4c0604f2b8f42418d2a7bc8ffab と差分なし（git diff --stat 946e6dbc 55d99a97e -- frontend/src が空）。TypeScript 5.9.3。このmdの再生成スクリプトは未整備のため946e6dbc時点の出力をコピー。

## 1. element-level CSS（select/input/textarea を裸タグで含むセレクタ）

方法: frontend/src 配下の全 .css をコメント除去後に `{}` 単位で走査し、カンマ分割した各セレクタの空白/`>`区切り要素に select|input|textarea が含まれるもの。62セレクタ。分類: (a)=先頭が裸タグ(スコープなし) (b)=ページ/コンテナclass配下。
結果: 裸の `select {` `textarea {` `input {` 単独の全域ルールは0件。(a)は1件のみ。

- [b-scoped] company-forms.css:100  `.form-grid > .form-row input:not([type="checkbox"]):not([type="radio"])`
    { padding: var(--space-2) var(--space-3); border: 1px solid var(--border-strong); border-radius: var(--radius-md); font-size: var(--font-base); background: var(--bg-surface); color: var(--text-primary); width: 100%; box-sizing: border-box; font-family: inherit; }
- [b-scoped] company-forms.css:100  `.form-grid > .form-row select`  (同ルールのグループ)
- [b-scoped] company-forms.css:100  `.form-grid > .form-row textarea`  (同ルールのグループ)
- [b-scoped] company-forms.css:114  `.form-grid > .form-row textarea`
    { min-height: var(--textarea-min-h); resize: vertical; }
- [b-scoped] company-forms.css:120  `.form-grid > .form-row input:focus`
    { outline: none; border-color: var(--accent); box-shadow: var(--focus-ring-shadow); }
- [b-scoped] company-forms.css:120  `.form-grid > .form-row select:focus`  (同ルールのグループ)
- [b-scoped] company-forms.css:120  `.form-grid > .form-row textarea:focus`  (同ルールのグループ)
- [b-scoped] company-forms.css:156  `.modal-content .form-row input:not([type="checkbox"]):not([type="radio"])`
    { padding: var(--space-2) var(--space-3); border: 1px solid var(--border-strong); border-radius: var(--radius-md); font-size: var(--font-base); background: var(--bg-surface); color: var(--text-primary); width: 100%; box-sizing: border-box; font-family: inherit; }
- [b-scoped] company-forms.css:156  `.modal-content .form-row select`  (同ルールのグループ)
- [b-scoped] company-forms.css:156  `.modal-content .form-row textarea`  (同ルールのグループ)
- [b-scoped] company-forms.css:156  `.modal-content-wide .form-row input:not([type="checkbox"]):not([type="radio"])`  (同ルールのグループ)
- [b-scoped] company-forms.css:156  `.modal-content-wide .form-row select`  (同ルールのグループ)
- [b-scoped] company-forms.css:156  `.modal-content-wide .form-row textarea`  (同ルールのグループ)
- [b-scoped] company-forms.css:173  `.modal-content .form-row textarea`
    { min-height: var(--textarea-min-h); resize: vertical; }
- [b-scoped] company-forms.css:173  `.modal-content-wide .form-row textarea`  (同ルールのグループ)
- [b-scoped] company-forms.css:181  `.modal-content .form-row input:focus`
    { outline: none; border-color: var(--accent); box-shadow: var(--focus-ring-shadow); }
- [b-scoped] company-forms.css:181  `.modal-content .form-row select:focus`  (同ルールのグループ)
- [b-scoped] company-forms.css:181  `.modal-content .form-row textarea:focus`  (同ルールのグループ)
- [b-scoped] company-forms.css:181  `.modal-content-wide .form-row input:focus`  (同ルールのグループ)
- [b-scoped] company-forms.css:181  `.modal-content-wide .form-row select:focus`  (同ルールのグループ)
- [b-scoped] company-forms.css:181  `.modal-content-wide .form-row textarea:focus`  (同ルールのグループ)
- [b-scoped] company-forms.css:260  `.product-edit-form .form-group input:not([type="checkbox"]):not([type="radio"])`
    { border: 1px solid var(--border-strong); }
- [b-scoped] company-forms.css:260  `.product-edit-form .form-group select`  (同ルールのグループ)
- [b-scoped] company-forms.css:260  `.product-edit-form .form-group textarea`  (同ルールのグループ)
- [b-scoped] components.css:19  `.form-group input`
    { width: 100%; padding: var(--space-2) var(--space-3); border: 1px solid var(--border); border-radius: var(--radius-sm); font-size: var(--font-base); color: var(--text-primary); background: var(--bg-surface); box-sizing: border-box; }
- [b-scoped] components.css:19  `.form-group select`  (同ルールのグループ)
- [b-scoped] components.css:19  `.form-group textarea`  (同ルールのグループ)
- [b-scoped] components.css:32  `.form-group input:focus`
    { outline: none; border-color: var(--accent); box-shadow: var(--focus-ring-shadow); }
- [b-scoped] components.css:32  `.form-group select:focus`  (同ルールのグループ)
- [b-scoped] components.css:32  `.form-group textarea:focus`  (同ルールのグループ)
- [b-scoped] components.css:41  `.form-group textarea`
    { min-height: var(--textarea-min-h); resize: vertical; }
- [b-scoped] components.css:60  `.search-bar input`
    { padding: var(--space-2) var(--space-3); border: 1px solid var(--border); border-radius: var(--radius-sm); font-size: var(--font-base); min-width: var(--input-select-min-w); background: var(--bg-surface); color: var(--text-primary); }
- [b-scoped] components.css:60  `.filter-bar select`  (同ルールのグループ)
- [b-scoped] components.css:781  `.toggle-switch input`
    { opacity: 0; width: 0; height: 0; }
- [b-scoped] components.css:793  `.toggle-switch input:checked + .toggle-switch-slider`
    { background: var(--accent); }
- [b-scoped] components.css:794  `.toggle-switch input:checked + .toggle-switch-slider::before`
    { transform: translateX(18px); }
- [b-scoped] features/tcg-analysis-review/source-raw-pane.css:48  `.source-search input`
    { min-width: 0; }
- [b-scoped] features/tcg-analysis-review/supplier-detail-view.css:244  `.pmd-field input`
    { border: 1px solid var(--border); border-radius: var(--radius-md); background: var(--bg-surface); padding: var(--space-2); font: inherit; width: 100%; box-sizing: border-box; }
- [b-scoped] features/tcg-analysis-review/supplier-detail-view.css:244  `.pmd-field textarea`  (同ルールのグループ)
- [b-scoped] features/tcg-analysis-review/supplier-detail-view.css:255  `.pmd-field textarea`
    { min-height: var(--pmd-textarea-min-h); resize: vertical; }
- [b-scoped] pages/account-settings/account-settings.css:111  `.toggle-switch input`
    { opacity: 0; width: 0; height: 0; position: absolute; }
- [b-scoped] pages/account-settings/account-settings.css:139  `.toggle-switch input:checked + .toggle-slider`
    { background: var(--accent); }
- [b-scoped] pages/account-settings/account-settings.css:143  `.toggle-switch input:checked + .toggle-slider::before`
    { transform: translateX(var(--space-5)); }
- [b-scoped] pages/account-settings/account-settings.css:147  `.toggle-switch input:focus-visible + .toggle-slider`
    { box-shadow: var(--focus-ring-shadow); }
- [b-scoped] pages/inbox/InboxPage.css:1206  `select.right-panel-field`
    { appearance: none; -webkit-appearance: none; }
- [b-scoped] pages/inbox/InboxPage.css:1208  `textarea.right-panel-field`
    { resize: none; min-height: var(--inbox-textarea-min-h); }
- [a-global-unscoped] pages/inbox/InboxPage.css:1378  `input[type="date"].karte-field-empty:not(:focus)::-webkit-datetime-edit`
    { color: transparent; }
- [b-scoped] pages/inbox/InboxPage.css:1457  `.inbox-toggle input`
    { opacity: 0; width: 0; height: 0; }
- [b-scoped] pages/inbox/InboxPage.css:1469  `.inbox-toggle input:checked + .inbox-toggle-slider`
    { background: var(--accent); }
- [b-scoped] pages/inbox/InboxPage.css:1470  `.inbox-toggle input:checked + .inbox-toggle-slider::before`
    { transform: translateX(var(--toggle-translate)); }
- [b-scoped] pages/inbox/InboxPage.css:1673  `.sales-form-option input[type="checkbox"]`
    { accent-color: var(--accent); cursor: pointer; }
- [b-scoped] pages/schedule.css:1242  `.schedule-settings .toggle-switch input:checked + .toggle-switch-slider`
    { background: var(--accent); }
- [b-scoped] pages/schedule.css:1242  `.schedule-page .toggle-switch input:checked + .toggle-switch-slider`  (同ルールのグループ)
- [b-scoped] pages/schedule.css:1247  `.schedule-settings .toggle-switch input:checked + .toggle-switch-slider::before`
    { transform: translateX(1.125rem); }
- [b-scoped] pages/schedule.css:1247  `.schedule-page .toggle-switch input:checked + .toggle-switch-slider::before`  (同ルールのグループ)
- [b-scoped] pages-layout.css:246  `.login-card .form-group input`
    { background: var(--bg-surface); color: var(--text-primary); border: 1px solid var(--border); border-radius: var(--radius-md); padding: var(--space-3) var(--space-4); font-size: var(--font-md); }
- [b-scoped] pages-layout.css:255  `.login-card .form-group input:focus`
    { outline: none; border-color: var(--accent); box-shadow: var(--focus-ring-shadow); }
- [b-scoped] pages-layout.css:354  `.color-swatch input[type="radio"]`
    { position: absolute; inset: 0; width: 100%; height: 100%; opacity: 0; cursor: pointer; }
- [b-scoped] pages-layout.css:609  `.chk-label input[type="checkbox"]`
    { margin: 0; }
- [b-scoped] pages-layout.css:633  `.permission-item input[type="checkbox"]`
    { margin-top: var(--space-1); flex-shrink: 0; }
- [b-scoped] topbar.css:44  `.topbar-search input`
    { flex: 1; border: none; background: transparent; padding: var(--space-10px) 0; font-size: var(--font-base); color: var(--text-primary); outline: none; }
- [b-scoped] topbar.css:54  `.topbar-search input::placeholder`
    { color: var(--text-muted); }

未検出の可能性: @importやCSS-in-TSX・インラインstyleは対象外。:is()/:where()内のタグは文字列分割では拾えない場合あり（未確認）。

## 2. クラス無し46 select の祖先className（最大4）と成立しうる select 対象ルール

対象ルール(select末尾の11セレクタ): comp... は含まず、company-forms.css:100/120/156/181/260 と components.css:19/32/60 の .form-row/.form-group/.filter-bar 系。「成立」=同一ファイルのJSX祖先に必要classが順序/直下条件(>)付きで揃う。それ以外は 未確認（親コンポーネントや呼出元の祖先は追跡していない）。注意: 成立でも当該CSSファイルが当該画面で読込まれるか・詳細度競合は未検証。

### frontend/src/components/CommissionPanel.tsx:205
- 祖先className(近い順・最大4): "data-table"
- 成立ルール: なし
- 未確認ルール数: 10（未確認(必要祖先が同ファイル内に無い→親）

### frontend/src/components/CompanyContactSelector.tsx:190
- 祖先className(近い順・最大4): "form-group"
- 成立ルール: components.css:19 .form-group select ; components.css:32 .form-group select:focus
- 未確認ルール数: 8（未確認(必要祖先が同ファイル内に無い→親）

### frontend/src/components/CompanyContactSelector.tsx:214
- 祖先className(近い順・最大4): "form-group"
- 成立ルール: components.css:19 .form-group select ; components.css:32 .form-group select:focus
- 未確認ルール数: 8（未確認(必要祖先が同ファイル内に無い→親）

### frontend/src/components/PurchaseDetailPanel.tsx:424
- 祖先className(近い順・最大4): "form-group"
- 成立ルール: components.css:19 .form-group select ; components.css:32 .form-group select:focus
- 未確認ルール数: 8（未確認(必要祖先が同ファイル内に無い→親）

### frontend/src/components/ShippingDetailPanel.tsx:511
- 祖先className(近い順・最大4): "form-group"
- 成立ルール: components.css:19 .form-group select ; components.css:32 .form-group select:focus
- 未確認ルール数: 8（未確認(必要祖先が同ファイル内に無い→親）

### frontend/src/features/tcg-analysis-review/ItemComparison.tsx:26
- 祖先className(近い順・最大4): (同一コンポーネント内に無し)
- 成立ルール: なし
- 未確認ルール数: 10（未確認(必要祖先が同ファイル内に無い→親）

### frontend/src/pages/admin/TenantPolicyPage.tsx:167
- 祖先className(近い順・最大4): "form-group" < "form"
- 成立ルール: components.css:19 .form-group select ; components.css:32 .form-group select:focus
- 未確認ルール数: 8（未確認(必要祖先が同ファイル内に無い→親）

### frontend/src/pages/admin/TenantPolicyPage.tsx:266
- 祖先className(近い順・最大4): "form-group" < "form"
- 成立ルール: components.css:19 .form-group select ; components.css:32 .form-group select:focus
- 未確認ルール数: 8（未確認(必要祖先が同ファイル内に無い→親）

### frontend/src/pages/admin/TenantPolicyPage.tsx:283
- 祖先className(近い順・最大4): "form-group" < "form"
- 成立ルール: components.css:19 .form-group select ; components.css:32 .form-group select:focus
- 未確認ルール数: 8（未確認(必要祖先が同ファイル内に無い→親）

### frontend/src/pages/admin/TenantProfilePage.tsx:234
- 祖先className(近い順・最大4): "form-group" < "form"
- 成立ルール: components.css:19 .form-group select ; components.css:32 .form-group select:focus
- 未確認ルール数: 8（未確認(必要祖先が同ファイル内に無い→親）

### frontend/src/pages/bots/BotsPage.tsx:233
- 祖先className(近い順・最大4): "form-group"
- 成立ルール: components.css:19 .form-group select ; components.css:32 .form-group select:focus
- 未確認ルール数: 8（未確認(必要祖先が同ファイル内に無い→親）

### frontend/src/pages/bots/BotsPage.tsx:241
- 祖先className(近い順・最大4): "form-group"
- 成立ルール: components.css:19 .form-group select ; components.css:32 .form-group select:focus
- 未確認ルール数: 8（未確認(必要祖先が同ファイル内に無い→親）

### frontend/src/pages/bots/BotsPage.tsx:248
- 祖先className(近い順・最大4): "form-group"
- 成立ルール: components.css:19 .form-group select ; components.css:32 .form-group select:focus
- 未確認ルール数: 8（未確認(必要祖先が同ファイル内に無い→親）

### frontend/src/pages/commission-settings/CommissionSettingsPage.tsx:206
- 祖先className(近い順・最大4): "data-table"
- 成立ルール: なし
- 未確認ルール数: 10（未確認(必要祖先が同ファイル内に無い→親）

### frontend/src/pages/companies/CompaniesPage.tsx:506
- 祖先className(近い順・最大4): "form-row" < "form-grid" < "modal-content-wide"
- 成立ルール: company-forms.css:100 .form-grid > .form-row select ; company-forms.css:120 .form-grid > .form-row select:focus ; company-forms.css:156 .modal-content-wide .form-row select ; company-forms.css:181 .modal-content-wide .form-row select:focus
- 未確認ルール数: 6（未確認(必要祖先が同ファイル内に無い→親）

### frontend/src/pages/company-detail/CompanyBasicTab.tsx:84
- 祖先className(近い順・最大4): "form-row" < "form-grid"
- 成立ルール: company-forms.css:100 .form-grid > .form-row select ; company-forms.css:120 .form-grid > .form-row select:focus
- 未確認ルール数: 8（未確認(必要祖先が同ファイル内に無い→親）

### frontend/src/pages/contacts/ContactsPage.tsx:308
- 祖先className(近い順・最大4): "form-row" < "form-grid" < "modal-content-wide"
- 成立ルール: company-forms.css:100 .form-grid > .form-row select ; company-forms.css:120 .form-grid > .form-row select:focus ; company-forms.css:156 .modal-content-wide .form-row select ; company-forms.css:181 .modal-content-wide .form-row select:focus
- 未確認ルール数: 6（未確認(必要祖先が同ファイル内に無い→親）

### frontend/src/pages/contacts/ContactsPage.tsx:341
- 祖先className(近い順・最大4): "form-row" < "form-grid" < "modal-content-wide"
- 成立ルール: company-forms.css:100 .form-grid > .form-row select ; company-forms.css:120 .form-grid > .form-row select:focus ; company-forms.css:156 .modal-content-wide .form-row select ; company-forms.css:181 .modal-content-wide .form-row select:focus
- 未確認ルール数: 6（未確認(必要祖先が同ファイル内に無い→親）

### frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:493
- 祖先className(近い順・最大4): "form-group" < "etd-upload" < "etd-guide"
- 成立ルール: components.css:19 .form-group select ; components.css:32 .form-group select:focus
- 未確認ルール数: 8（未確認(必要祖先が同ファイル内に無い→親）

### frontend/src/pages/integrations/PaypalIntegrationPage.tsx:164
- 祖先className(近い順・最大4): "form-group" < "card"
- 成立ルール: components.css:19 .form-group select ; components.css:32 .form-group select:focus
- 未確認ルール数: 8（未確認(必要祖先が同ファイル内に無い→親）

### frontend/src/pages/inventory/InventoryPage.tsx:477
- 祖先className(近い順・最大4): "tabs"
- 成立ルール: なし
- 未確認ルール数: 10（未確認(必要祖先が同ファイル内に無い→親）

### frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:308
- 祖先className(近い順・最大4): "form-group"
- 成立ルール: components.css:19 .form-group select ; components.css:32 .form-group select:focus
- 未確認ルール数: 8（未確認(必要祖先が同ファイル内に無い→親）

### frontend/src/pages/orders/OrdersFormModal.tsx:86
- 祖先className(近い順・最大4): "form-group"
- 成立ルール: components.css:19 .form-group select ; components.css:32 .form-group select:focus
- 未確認ルール数: 8（未確認(必要祖先が同ファイル内に無い→親）

### frontend/src/pages/products/ProductEditPage.tsx:231
- 祖先className(近い順・最大4): "form-group" < "product-edit-form" < "page page--full"
- 成立ルール: company-forms.css:260 .product-edit-form .form-group select ; components.css:19 .form-group select ; components.css:32 .form-group select:focus
- 未確認ルール数: 7（未確認(必要祖先が同ファイル内に無い→親）

### frontend/src/pages/products/ProductEditPage.tsx:238
- 祖先className(近い順・最大4): "form-group" < "product-edit-form" < "page page--full"
- 成立ルール: company-forms.css:260 .product-edit-form .form-group select ; components.css:19 .form-group select ; components.css:32 .form-group select:focus
- 未確認ルール数: 7（未確認(必要祖先が同ファイル内に無い→親）

### frontend/src/pages/products/ProductEditPage.tsx:255
- 祖先className(近い順・最大4): "form-group" < "product-edit-form" < "page page--full"
- 成立ルール: company-forms.css:260 .product-edit-form .form-group select ; components.css:19 .form-group select ; components.css:32 .form-group select:focus
- 未確認ルール数: 7（未確認(必要祖先が同ファイル内に無い→親）

### frontend/src/pages/products/ProductEditPage.tsx:278
- 祖先className(近い順・最大4): "form-group" < "product-edit-form" < "page page--full"
- 成立ルール: company-forms.css:260 .product-edit-form .form-group select ; components.css:19 .form-group select ; components.css:32 .form-group select:focus
- 未確認ルール数: 7（未確認(必要祖先が同ファイル内に無い→親）

### frontend/src/pages/products/ProductEditPage.tsx:285
- 祖先className(近い順・最大4): "form-group" < "product-edit-form" < "page page--full"
- 成立ルール: company-forms.css:260 .product-edit-form .form-group select ; components.css:19 .form-group select ; components.css:32 .form-group select:focus
- 未確認ルール数: 7（未確認(必要祖先が同ファイル内に無い→親）

### frontend/src/pages/products/ProductEditPage.tsx:302
- 祖先className(近い順・最大4): "form-group" < "product-edit-form" < "page page--full"
- 成立ルール: company-forms.css:260 .product-edit-form .form-group select ; components.css:19 .form-group select ; components.css:32 .form-group select:focus
- 未確認ルール数: 7（未確認(必要祖先が同ファイル内に無い→親）

### frontend/src/pages/products/ProductEditPage.tsx:346
- 祖先className(近い順・最大4): "form-group" < "product-edit-form" < "page page--full"
- 成立ルール: company-forms.css:260 .product-edit-form .form-group select ; components.css:19 .form-group select ; components.css:32 .form-group select:focus
- 未確認ルール数: 7（未確認(必要祖先が同ファイル内に無い→親）

### frontend/src/pages/products/ProductEditPage.tsx:353
- 祖先className(近い順・最大4): "form-group" < "product-edit-form" < "page page--full"
- 成立ルール: company-forms.css:260 .product-edit-form .form-group select ; components.css:19 .form-group select ; components.css:32 .form-group select:focus
- 未確認ルール数: 7（未確認(必要祖先が同ファイル内に無い→親）

### frontend/src/pages/products/ProductEditPage.tsx:360
- 祖先className(近い順・最大4): "form-group" < "product-edit-form" < "page page--full"
- 成立ルール: company-forms.css:260 .product-edit-form .form-group select ; components.css:19 .form-group select ; components.css:32 .form-group select:focus
- 未確認ルール数: 7（未確認(必要祖先が同ファイル内に無い→親）

### frontend/src/pages/purchase-orders/PurchaseOrdersFormModal.tsx:156
- 祖先className(近い順・最大4): "form-group"
- 成立ルール: components.css:19 .form-group select ; components.css:32 .form-group select:focus
- 未確認ルール数: 8（未確認(必要祖先が同ファイル内に無い→親）

### frontend/src/pages/quote-create/QuoteCreatePage.tsx:157
- 祖先className(近い順・最大4): "form-group"
- 成立ルール: components.css:19 .form-group select ; components.css:32 .form-group select:focus
- 未確認ルール数: 8（未確認(必要祖先が同ファイル内に無い→親）

### frontend/src/pages/super-admin/DexTab.tsx:194
- 祖先className(近い順・最大4): "super-admin-dex-tab"
- 成立ルール: なし
- 未確認ルール数: 10（未確認(必要祖先が同ファイル内に無い→親）

### frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:447
- 祖先className(近い順・最大4): "form-group" < "super-admin-knowledge-tab"
- 成立ルール: components.css:19 .form-group select ; components.css:32 .form-group select:focus
- 未確認ルール数: 8（未確認(必要祖先が同ファイル内に無い→親）

### frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:455
- 祖先className(近い順・最大4): "form-group" < "super-admin-knowledge-tab"
- 成立ルール: components.css:19 .form-group select ; components.css:32 .form-group select:focus
- 未確認ルール数: 8（未確認(必要祖先が同ファイル内に無い→親）

### frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:472
- 祖先className(近い順・最大4): "form-group" < "super-admin-knowledge-tab"
- 成立ルール: components.css:19 .form-group select ; components.css:32 .form-group select:focus
- 未確認ルール数: 8（未確認(必要祖先が同ファイル内に無い→親）

### frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:501
- 祖先className(近い順・最大4): "form-group" < "super-admin-knowledge-tab"
- 成立ルール: components.css:19 .form-group select ; components.css:32 .form-group select:focus
- 未確認ルール数: 8（未確認(必要祖先が同ファイル内に無い→親）

### frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:523
- 祖先className(近い順・最大4): "form-group" < "super-admin-knowledge-tab"
- 成立ルール: components.css:19 .form-group select ; components.css:32 .form-group select:focus
- 未確認ルール数: 8（未確認(必要祖先が同ファイル内に無い→親）

### frontend/src/pages/super-admin/ParseReviewPage.tsx:575
- 祖先className(近い順・最大4): "data-table" < "review-table-scroll" < "review-main" < "review-split"
- 成立ルール: なし
- 未確認ルール数: 10（未確認(必要祖先が同ファイル内に無い→親）

### frontend/src/pages/super-admin/ParseReviewPage.tsx:596
- 祖先className(近い順・最大4): "data-table" < "review-table-scroll" < "review-main" < "review-split"
- 成立ルール: なし
- 未確認ルール数: 10（未確認(必要祖先が同ファイル内に無い→親）

### frontend/src/pages/super-admin/ParseReviewPage.tsx:617
- 祖先className(近い順・最大4): "data-table" < "review-table-scroll" < "review-main" < "review-split"
- 成立ルール: なし
- 未確認ルール数: 10（未確認(必要祖先が同ファイル内に無い→親）

### frontend/src/pages/super-admin/ParseReviewPage.tsx:638
- 祖先className(近い順・最大4): "data-table" < "review-table-scroll" < "review-main" < "review-split"
- 成立ルール: なし
- 未確認ルール数: 10（未確認(必要祖先が同ファイル内に無い→親）

### frontend/src/pages/super-admin/TcgSeriesTab.tsx:190
- 祖先className(近い順・最大4): "super-admin-tcg-tab"
- 成立ルール: なし
- 未確認ルール数: 10（未確認(必要祖先が同ファイル内に無い→親）

### frontend/src/pages/super-admin/TcgSeriesTab.tsx:300
- 祖先className(近い順・最大4): "super-admin-tcg-tab"
- 成立ルール: なし
- 未確認ルール数: 10（未確認(必要祖先が同ファイル内に無い→親）


## 3. CSSI entries

抽出条件: selector文字列が select(selected除く)/right-panel-field/page-header-select/inbox-platform-select/account-settings-lang-select/schedule-input/field-h-md/field-w-sm/comp-select を含む。selected系(CSSI-0193/0199/0200/0291)は部分一致の誤検出なので除外。31件。JSON原文(selector-impact-audit.json rows[])の該当フィールドをそのまま転記。

### CSSI-0006  src/company-forms.css:100
selector: `.form-grid > .form-row select` conditions=[] tags=["select"]
disposition: 部品CSSへ削除移管
reason: 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持
actions: [{"action":"部品CSSへ削除移管","declarations":[{"property":"padding","value":"var(--space-2) var(--space-3)","important":false,"line":103},{"property":"border","value":"1px solid var(--border-strong)","important":false,"line":104},{"property":"border-radius","value":"var(--radius-md)","important":false,"line":105},{"property":"font-size","value":"var(--font-base)","important":false,"line":106},{"property":"background","value":"var(--bg-surface)","important":false,"line":107},{"property":"color","value":"var(--text-primary)","important":false,"line":108},{"property":"width","value":"100%","important":false,"line":109},{"property":"box-sizing","value":"border-box","important":false,"line":110},{"property":"font-family","value":"inherit","important":false,"line":111}],"owner":"Button/裸Control/Tabs等、対応JSONで登録した外観owner。width/min-width/flex/resize等の原値は用途契約として維持"}]
selector_retention_note: selector/ownerを維持する判定と、宣言値の維持を区別する。元declarationsは観測値、移管後の値はdesign_contract/actionsに従う
layout: [{"property":"width","value":"100%","important":false,"line":109}]
appearance: [{"property":"padding","value":"var(--space-2) var(--space-3)","important":false,"line":103},{"property":"border","value":"1px solid var(--border-strong)","important":false,"line":104},{"property":"border-radius","value":"var(--radius-md)","important":false,"line":105},{"property":"font-size","value":"var(--font-base)","important":false,"line":106},{"property":"background","value":"var(--bg-surface)","important":false,"line":107},{"property":"color","value":"var(--text-primary)","important":false,"line":108},{"property":"box-sizing","value":"border-box","important":false,"line":110},{"property":"font-family","value":"inherit","important":false,"line":111}]
declarations: padding: var(--space-2) var(--space-3); border: 1px solid var(--border-strong); border-radius: var(--radius-md); font-size: var(--font-base); background: var(--bg-surface); color: var(--text-primary); width: 100%; box-sizing: border-box; font-family: inherit

### CSSI-0010  src/company-forms.css:120
selector: `.form-grid > .form-row select:focus` conditions=[] tags=["select"]
disposition: 部品CSSへ削除移管
reason: 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持
actions: [{"action":"部品CSSへ削除移管","declarations":[{"property":"outline","value":"none","important":false,"line":123},{"property":"border-color","value":"var(--accent)","important":false,"line":124},{"property":"box-shadow","value":"var(--focus-ring-shadow)","important":false,"line":125}],"owner":"Button/裸Control/Tabs等、対応JSONで登録した外観owner。width/min-width/flex/resize等の原値は用途契約として維持"}]
selector_retention_note: selector/ownerを維持する判定と、宣言値の維持を区別する。元declarationsは観測値、移管後の値はdesign_contract/actionsに従う
layout: []
appearance: [{"property":"outline","value":"none","important":false,"line":123},{"property":"border-color","value":"var(--accent)","important":false,"line":124},{"property":"box-shadow","value":"var(--focus-ring-shadow)","important":false,"line":125}]
declarations: outline: none; border-color: var(--accent); box-shadow: var(--focus-ring-shadow)

### CSSI-0013  src/company-forms.css:156
selector: `.modal-content .form-row select` conditions=[] tags=["select"]
disposition: 部品CSSへ削除移管
reason: 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持
actions: [{"action":"部品CSSへ削除移管","declarations":[{"property":"padding","value":"var(--space-2) var(--space-3)","important":false,"line":162},{"property":"border","value":"1px solid var(--border-strong)","important":false,"line":163},{"property":"border-radius","value":"var(--radius-md)","important":false,"line":164},{"property":"font-size","value":"var(--font-base)","important":false,"line":165},{"property":"background","value":"var(--bg-surface)","important":false,"line":166},{"property":"color","value":"var(--text-primary)","important":false,"line":167},{"property":"width","value":"100%","important":false,"line":168},{"property":"box-sizing","value":"border-box","important":false,"line":169},{"property":"font-family","value":"inherit","important":false,"line":170}],"owner":"Button/裸Control/Tabs等、対応JSONで登録した外観owner。width/min-width/flex/resize等の原値は用途契約として維持"}]
selector_retention_note: selector/ownerを維持する判定と、宣言値の維持を区別する。元declarationsは観測値、移管後の値はdesign_contract/actionsに従う
layout: [{"property":"width","value":"100%","important":false,"line":168}]
appearance: [{"property":"padding","value":"var(--space-2) var(--space-3)","important":false,"line":162},{"property":"border","value":"1px solid var(--border-strong)","important":false,"line":163},{"property":"border-radius","value":"var(--radius-md)","important":false,"line":164},{"property":"font-size","value":"var(--font-base)","important":false,"line":165},{"property":"background","value":"var(--bg-surface)","important":false,"line":166},{"property":"color","value":"var(--text-primary)","important":false,"line":167},{"property":"box-sizing","value":"border-box","important":false,"line":169},{"property":"font-family","value":"inherit","important":false,"line":170}]
declarations: padding: var(--space-2) var(--space-3); border: 1px solid var(--border-strong); border-radius: var(--radius-md); font-size: var(--font-base); background: var(--bg-surface); color: var(--text-primary); width: 100%; box-sizing: border-box; font-family: inherit

### CSSI-0016  src/company-forms.css:156
selector: `.modal-content-wide .form-row select` conditions=[] tags=["select"]
disposition: 部品CSSへ削除移管
reason: 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持
actions: [{"action":"部品CSSへ削除移管","declarations":[{"property":"padding","value":"var(--space-2) var(--space-3)","important":false,"line":162},{"property":"border","value":"1px solid var(--border-strong)","important":false,"line":163},{"property":"border-radius","value":"var(--radius-md)","important":false,"line":164},{"property":"font-size","value":"var(--font-base)","important":false,"line":165},{"property":"background","value":"var(--bg-surface)","important":false,"line":166},{"property":"color","value":"var(--text-primary)","important":false,"line":167},{"property":"width","value":"100%","important":false,"line":168},{"property":"box-sizing","value":"border-box","important":false,"line":169},{"property":"font-family","value":"inherit","important":false,"line":170}],"owner":"Button/裸Control/Tabs等、対応JSONで登録した外観owner。width/min-width/flex/resize等の原値は用途契約として維持"}]
selector_retention_note: selector/ownerを維持する判定と、宣言値の維持を区別する。元declarationsは観測値、移管後の値はdesign_contract/actionsに従う
layout: [{"property":"width","value":"100%","important":false,"line":168}]
appearance: [{"property":"padding","value":"var(--space-2) var(--space-3)","important":false,"line":162},{"property":"border","value":"1px solid var(--border-strong)","important":false,"line":163},{"property":"border-radius","value":"var(--radius-md)","important":false,"line":164},{"property":"font-size","value":"var(--font-base)","important":false,"line":165},{"property":"background","value":"var(--bg-surface)","important":false,"line":166},{"property":"color","value":"var(--text-primary)","important":false,"line":167},{"property":"box-sizing","value":"border-box","important":false,"line":169},{"property":"font-family","value":"inherit","important":false,"line":170}]
declarations: padding: var(--space-2) var(--space-3); border: 1px solid var(--border-strong); border-radius: var(--radius-md); font-size: var(--font-base); background: var(--bg-surface); color: var(--text-primary); width: 100%; box-sizing: border-box; font-family: inherit

### CSSI-0021  src/company-forms.css:181
selector: `.modal-content .form-row select:focus` conditions=[] tags=["select"]
disposition: 部品CSSへ削除移管
reason: 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持
actions: [{"action":"部品CSSへ削除移管","declarations":[{"property":"outline","value":"none","important":false,"line":187},{"property":"border-color","value":"var(--accent)","important":false,"line":188},{"property":"box-shadow","value":"var(--focus-ring-shadow)","important":false,"line":189}],"owner":"Button/裸Control/Tabs等、対応JSONで登録した外観owner。width/min-width/flex/resize等の原値は用途契約として維持"}]
selector_retention_note: selector/ownerを維持する判定と、宣言値の維持を区別する。元declarationsは観測値、移管後の値はdesign_contract/actionsに従う
layout: []
appearance: [{"property":"outline","value":"none","important":false,"line":187},{"property":"border-color","value":"var(--accent)","important":false,"line":188},{"property":"box-shadow","value":"var(--focus-ring-shadow)","important":false,"line":189}]
declarations: outline: none; border-color: var(--accent); box-shadow: var(--focus-ring-shadow)

### CSSI-0024  src/company-forms.css:181
selector: `.modal-content-wide .form-row select:focus` conditions=[] tags=["select"]
disposition: 部品CSSへ削除移管
reason: 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持
actions: [{"action":"部品CSSへ削除移管","declarations":[{"property":"outline","value":"none","important":false,"line":187},{"property":"border-color","value":"var(--accent)","important":false,"line":188},{"property":"box-shadow","value":"var(--focus-ring-shadow)","important":false,"line":189}],"owner":"Button/裸Control/Tabs等、対応JSONで登録した外観owner。width/min-width/flex/resize等の原値は用途契約として維持"}]
selector_retention_note: selector/ownerを維持する判定と、宣言値の維持を区別する。元declarationsは観測値、移管後の値はdesign_contract/actionsに従う
layout: []
appearance: [{"property":"outline","value":"none","important":false,"line":187},{"property":"border-color","value":"var(--accent)","important":false,"line":188},{"property":"box-shadow","value":"var(--focus-ring-shadow)","important":false,"line":189}]
declarations: outline: none; border-color: var(--accent); box-shadow: var(--focus-ring-shadow)

### CSSI-0027  src/company-forms.css:260
selector: `.product-edit-form .form-group select` conditions=[] tags=["select"]
disposition: 部品CSSへ削除移管
reason: 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持
actions: [{"action":"部品CSSへ削除移管","declarations":[{"property":"border","value":"1px solid var(--border-strong)","important":false,"line":263}],"owner":"Button/裸Control/Tabs等、対応JSONで登録した外観owner。width/min-width/flex/resize等の原値は用途契約として維持"}]
selector_retention_note: selector/ownerを維持する判定と、宣言値の維持を区別する。元declarationsは観測値、移管後の値はdesign_contract/actionsに従う
layout: []
appearance: [{"property":"border","value":"1px solid var(--border-strong)","important":false,"line":263}]
declarations: border: 1px solid var(--border-strong)

### CSSI-0060  src/components/field-size.css:8
selector: `.field-h-md` conditions=[] tags=[]
disposition: 部品CSSへ削除移管
reason: 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持
actions: [{"action":"部品CSSへ削除移管","declarations":[{"property":"min-height","value":"var(--field-h-md, 36px)","important":false,"line":8},{"property":"box-sizing","value":"border-box","important":false,"line":8}],"owner":"Button/裸Control/Tabs等、対応JSONで登録した外観owner。width/min-width/flex/resize等の原値は用途契約として維持"}]
selector_retention_note: selector/ownerを維持する判定と、宣言値の維持を区別する。元declarationsは観測値、移管後の値はdesign_contract/actionsに従う
layout: [{"property":"min-height","value":"var(--field-h-md, 36px)","important":false,"line":8}]
appearance: [{"property":"box-sizing","value":"border-box","important":false,"line":8}]
declarations: min-height: var(--field-h-md, 36px); box-sizing: border-box

### CSSI-0061  src/components/field-size.css:12
selector: `.field-w-sm` conditions=[] tags=[]
disposition: 部品CSSへ削除移管
reason: 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持
actions: [{"action":"部品CSSへ削除移管","declarations":[{"property":"width","value":"var(--field-w-sm, 160px)","important":false,"line":12}],"owner":"Button/裸Control/Tabs等、対応JSONで登録した外観owner。width/min-width/flex/resize等の原値は用途契約として維持"}]
selector_retention_note: selector/ownerを維持する判定と、宣言値の維持を区別する。元declarationsは観測値、移管後の値はdesign_contract/actionsに従う
layout: [{"property":"width","value":"var(--field-w-sm, 160px)","important":false,"line":12}]
appearance: []
declarations: width: var(--field-w-sm, 160px)

### CSSI-0063  src/components/field-size.css:18
selector: `.content-toolbar .field-w-sm` conditions=[] tags=[]
disposition: 外配置へ移管
reason: 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持
actions: [{"action":"外配置へ移管","declarations":[{"property":"margin-bottom","value":"0","important":false,"line":20}],"owner":"既存page/feature layout。nativeに新規wrapperを加えない"}]
selector_retention_note: selector/ownerを維持する判定と、宣言値の維持を区別する。元declarationsは観測値、移管後の値はdesign_contract/actionsに従う
layout: [{"property":"margin-bottom","value":"0","important":false,"line":20}]
appearance: []
declarations: margin-bottom: 0

### CSSI-0066  src/components.css:19
selector: `.form-group select` conditions=[] tags=["select"]
disposition: 部品CSSへ削除移管
reason: 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持
actions: [{"action":"部品CSSへ削除移管","declarations":[{"property":"width","value":"100%","important":false,"line":22},{"property":"padding","value":"var(--space-2) var(--space-3)","important":false,"line":23},{"property":"border","value":"1px solid var(--border)","important":false,"line":24},{"property":"border-radius","value":"var(--radius-sm)","important":false,"line":25},{"property":"font-size","value":"var(--font-base)","important":false,"line":26},{"property":"color","value":"var(--text-primary)","important":false,"line":27},{"property":"background","value":"var(--bg-surface)","important":false,"line":28},{"property":"box-sizing","value":"border-box","important":false,"line":29}],"owner":"Button/裸Control/Tabs等、対応JSONで登録した外観owner。width/min-width/flex/resize等の原値は用途契約として維持"}]
selector_retention_note: selector/ownerを維持する判定と、宣言値の維持を区別する。元declarationsは観測値、移管後の値はdesign_contract/actionsに従う
layout: [{"property":"width","value":"100%","important":false,"line":22}]
appearance: [{"property":"padding","value":"var(--space-2) var(--space-3)","important":false,"line":23},{"property":"border","value":"1px solid var(--border)","important":false,"line":24},{"property":"border-radius","value":"var(--radius-sm)","important":false,"line":25},{"property":"font-size","value":"var(--font-base)","important":false,"line":26},{"property":"color","value":"var(--text-primary)","important":false,"line":27},{"property":"background","value":"var(--bg-surface)","important":false,"line":28},{"property":"box-sizing","value":"border-box","important":false,"line":29}]
declarations: width: 100%; padding: var(--space-2) var(--space-3); border: 1px solid var(--border); border-radius: var(--radius-sm); font-size: var(--font-base); color: var(--text-primary); background: var(--bg-surface); box-sizing: border-box

### CSSI-0069  src/components.css:32
selector: `.form-group select:focus` conditions=[] tags=["select"]
disposition: 部品CSSへ削除移管
reason: 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持
actions: [{"action":"部品CSSへ削除移管","declarations":[{"property":"outline","value":"none","important":false,"line":35},{"property":"border-color","value":"var(--accent)","important":false,"line":36},{"property":"box-shadow","value":"var(--focus-ring-shadow)","important":false,"line":37}],"owner":"Button/裸Control/Tabs等、対応JSONで登録した外観owner。width/min-width/flex/resize等の原値は用途契約として維持"}]
selector_retention_note: selector/ownerを維持する判定と、宣言値の維持を区別する。元declarationsは観測値、移管後の値はdesign_contract/actionsに従う
layout: []
appearance: [{"property":"outline","value":"none","important":false,"line":35},{"property":"border-color","value":"var(--accent)","important":false,"line":36},{"property":"box-shadow","value":"var(--focus-ring-shadow)","important":false,"line":37}]
declarations: outline: none; border-color: var(--accent); box-shadow: var(--focus-ring-shadow)

### CSSI-0088  src/components.css:172
selector: `.filter-bar select` conditions=[] tags=["select"]
disposition: 部品CSSへ削除移管
reason: 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持
actions: [{"action":"部品CSSへ削除移管","declarations":[{"property":"padding","value":"var(--space-2) var(--space-3)","important":false,"line":174},{"property":"border","value":"1px solid var(--border)","important":false,"line":175},{"property":"border-radius","value":"var(--radius-sm)","important":false,"line":176},{"property":"font-size","value":"var(--font-base)","important":false,"line":177},{"property":"min-width","value":"var(--input-select-min-w)","important":false,"line":178},{"property":"background","value":"var(--bg-surface)","important":false,"line":179},{"property":"color","value":"var(--text-primary)","important":false,"line":180}],"owner":"Button/裸Control/Tabs等、対応JSONで登録した外観owner。width/min-width/flex/resize等の原値は用途契約として維持"}]
selector_retention_note: selector/ownerを維持する判定と、宣言値の維持を区別する。元declarationsは観測値、移管後の値はdesign_contract/actionsに従う
layout: [{"property":"min-width","value":"var(--input-select-min-w)","important":false,"line":178}]
appearance: [{"property":"padding","value":"var(--space-2) var(--space-3)","important":false,"line":174},{"property":"border","value":"1px solid var(--border)","important":false,"line":175},{"property":"border-radius","value":"var(--radius-sm)","important":false,"line":176},{"property":"font-size","value":"var(--font-base)","important":false,"line":177},{"property":"background","value":"var(--bg-surface)","important":false,"line":179},{"property":"color","value":"var(--text-primary)","important":false,"line":180}]
declarations: padding: var(--space-2) var(--space-3); border: 1px solid var(--border); border-radius: var(--radius-sm); font-size: var(--font-base); min-width: var(--input-select-min-w); background: var(--bg-surface); color: var(--text-primary)

### CSSI-0102  src/components.css:711
selector: `.page-header-select` conditions=[] tags=[]
disposition: 部品CSSへ削除移管
reason: 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持
actions: [{"action":"部品CSSへ削除移管","declarations":[{"property":"appearance","value":"none","important":false,"line":712},{"property":"-webkit-appearance","value":"none","important":false,"line":713},{"property":"box-sizing","value":"border-box","important":false,"line":714},{"property":"height","value":"var(--size-icon-btn)","important":false,"line":715},{"property":"padding","value":"var(--space-1) var(--space-5) var(--space-1) var(--space-3)","important":false,"line":716},{"property":"border","value":"1px solid var(--border)","important":false,"line":717},{"property":"border-radius","value":"var(--radius-pill)","important":false,"line":718},{"property":"background","value":"var(--bg-surface) url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='8' viewBox='0 0 12 8'%3E%3Cpath d='M1 1l5 5 5-5' stroke='%23888' stroke-width='1.5' fill='none' stroke-linecap='round'/%3E%3C/svg%3E\") no-repeat right var(--space-2) center","important":false,"line":719},{"property":"color","value":"var(--text-primary)","important":false,"line":720},{"property":"font-size","value":"var(--font-sm)","important":false,"line":721},{"property":"cursor","value":"pointer","important":false,"line":722},{"property":"transition","value":"border-color var(--transition-fast), background-color var(--transition-fast)","important":false,"line":723},{"property":"white-space","value":"nowrap","important":false,"line":724}],"owner":"Button/裸Control/Tabs等、対応JSONで登録した外観owner。width/min-width/flex/resize等の原値は用途契約として維持"}]
selector_retention_note: selector/ownerを維持する判定と、宣言値の維持を区別する。元declarationsは観測値、移管後の値はdesign_contract/actionsに従う
layout: [{"property":"height","value":"var(--size-icon-btn)","important":false,"line":715}]
appearance: [{"property":"appearance","value":"none","important":false,"line":712},{"property":"-webkit-appearance","value":"none","important":false,"line":713},{"property":"box-sizing","value":"border-box","important":false,"line":714},{"property":"padding","value":"var(--space-1) var(--space-5) var(--space-1) var(--space-3)","important":false,"line":716},{"property":"border","value":"1px solid var(--border)","important":false,"line":717},{"property":"border-radius","value":"var(--radius-pill)","important":false,"line":718},{"property":"background","value":"var(--bg-surface) url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='8' viewBox='0 0 12 8'%3E%3Cpath d='M1 1l5 5 5-5' stroke='%23888' stroke-width='1.5' fill='none' stroke-linecap='round'/%3E%3C/svg%3E\") no-repeat right var(--space-2) center","important":false,"line":719},{"property":"color","value":"var(--text-primary)","important":false,"line":720},{"property":"font-size","value":"var(--font-sm)","important":false,"line":721},{"property":"cursor","value":"pointer","important":false,"line":722},{"property":"transition","value":"border-color var(--transition-fast), background-color var(--transition-fast)","important":false,"line":723},{"property":"white-space","value":"nowrap","important":false,"line":724}]
declarations: appearance: none; -webkit-appearance: none; box-sizing: border-box; height: var(--size-icon-btn); padding: var(--space-1) var(--space-5) var(--space-1) var(--space-3); border: 1px solid var(--border); border-radius: var(--radius-pill); background: var(--bg-surface) url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='8' viewBox='0 0 12 8'%3E%3Cpath d='M1 1l5 5 5-5' stroke='%23888' stroke-width='1.5' fill='none' stroke-linecap='round'/%3E%3C/svg%3E") no-repeat right var(--space-2) center; color: var(--text-primary); font-size: var(--font-sm); cursor: pointer; transition: border-color var(--transition-fast), background-color var(--transition-fast); white-space: nowrap

### CSSI-0103  src/components.css:726
selector: `.page-header-select:hover` conditions=[] tags=[]
disposition: 部品CSSへ削除移管
reason: 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持
actions: [{"action":"部品CSSへ削除移管","declarations":[{"property":"background-color","value":"var(--bg-hover)","important":false,"line":727},{"property":"border-color","value":"var(--border-strong)","important":false,"line":728}],"owner":"Button/裸Control/Tabs等、対応JSONで登録した外観owner。width/min-width/flex/resize等の原値は用途契約として維持"}]
selector_retention_note: selector/ownerを維持する判定と、宣言値の維持を区別する。元declarationsは観測値、移管後の値はdesign_contract/actionsに従う
layout: []
appearance: [{"property":"background-color","value":"var(--bg-hover)","important":false,"line":727},{"property":"border-color","value":"var(--border-strong)","important":false,"line":728}]
declarations: background-color: var(--bg-hover); border-color: var(--border-strong)

### CSSI-0104  src/components.css:730
selector: `.page-header-select:focus` conditions=[] tags=[]
disposition: 部品CSSへ削除移管
reason: 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持
actions: [{"action":"部品CSSへ削除移管","declarations":[{"property":"outline","value":"none","important":false,"line":731},{"property":"border-color","value":"var(--accent)","important":false,"line":732},{"property":"box-shadow","value":"var(--focus-ring-shadow)","important":false,"line":733}],"owner":"Button/裸Control/Tabs等、対応JSONで登録した外観owner。width/min-width/flex/resize等の原値は用途契約として維持"}]
selector_retention_note: selector/ownerを維持する判定と、宣言値の維持を区別する。元declarationsは観測値、移管後の値はdesign_contract/actionsに従う
layout: []
appearance: [{"property":"outline","value":"none","important":false,"line":731},{"property":"border-color","value":"var(--accent)","important":false,"line":732},{"property":"box-shadow","value":"var(--focus-ring-shadow)","important":false,"line":733}]
declarations: outline: none; border-color: var(--accent); box-shadow: var(--focus-ring-shadow)

### CSSI-0148  src/pages/account-settings/account-settings.css:147
selector: `.account-settings-lang-select` conditions=[] tags=[]
disposition: 部品CSSへ削除移管
reason: 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持
actions: [{"action":"部品CSSへ削除移管","declarations":[{"property":"padding","value":"var(--space-1) var(--space-3)","important":false,"line":148},{"property":"border","value":"1px solid var(--border)","important":false,"line":149},{"property":"border-radius","value":"var(--radius-sm)","important":false,"line":150},{"property":"background","value":"var(--bg-surface)","important":false,"line":151},{"property":"color","value":"var(--text-primary)","important":false,"line":152},{"property":"font-size","value":"var(--font-sm)","important":false,"line":153},{"property":"cursor","value":"pointer","important":false,"line":154},{"property":"min-width","value":"var(--size-lang-select-min)","important":false,"line":155}],"owner":"Button/裸Control/Tabs等、対応JSONで登録した外観owner。width/min-width/flex/resize等の原値は用途契約として維持"}]
selector_retention_note: selector/ownerを維持する判定と、宣言値の維持を区別する。元declarationsは観測値、移管後の値はdesign_contract/actionsに従う
layout: [{"property":"min-width","value":"var(--size-lang-select-min)","important":false,"line":155}]
appearance: [{"property":"padding","value":"var(--space-1) var(--space-3)","important":false,"line":148},{"property":"border","value":"1px solid var(--border)","important":false,"line":149},{"property":"border-radius","value":"var(--radius-sm)","important":false,"line":150},{"property":"background","value":"var(--bg-surface)","important":false,"line":151},{"property":"color","value":"var(--text-primary)","important":false,"line":152},{"property":"font-size","value":"var(--font-sm)","important":false,"line":153},{"property":"cursor","value":"pointer","important":false,"line":154}]
declarations: padding: var(--space-1) var(--space-3); border: 1px solid var(--border); border-radius: var(--radius-sm); background: var(--bg-surface); color: var(--text-primary); font-size: var(--font-sm); cursor: pointer; min-width: var(--size-lang-select-min)

### CSSI-0149  src/pages/account-settings/account-settings.css:158
selector: `.account-settings-lang-select:focus` conditions=[] tags=[]
disposition: 部品CSSへ削除移管
reason: 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持
actions: [{"action":"部品CSSへ削除移管","declarations":[{"property":"outline","value":"none","important":false,"line":159},{"property":"border-color","value":"var(--accent)","important":false,"line":160},{"property":"box-shadow","value":"var(--focus-ring-shadow)","important":false,"line":161}],"owner":"Button/裸Control/Tabs等、対応JSONで登録した外観owner。width/min-width/flex/resize等の原値は用途契約として維持"}]
selector_retention_note: selector/ownerを維持する判定と、宣言値の維持を区別する。元declarationsは観測値、移管後の値はdesign_contract/actionsに従う
layout: []
appearance: [{"property":"outline","value":"none","important":false,"line":159},{"property":"border-color","value":"var(--accent)","important":false,"line":160},{"property":"box-shadow","value":"var(--focus-ring-shadow)","important":false,"line":161}]
declarations: outline: none; border-color: var(--accent); box-shadow: var(--focus-ring-shadow)

### CSSI-0178  src/pages/goal-setting/GoalSettingPage.css:555
selector: `.gs-select` conditions=[] tags=[]
disposition: 部品CSSへ削除移管
reason: 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持
actions: [{"action":"部品CSSへ削除移管","declarations":[{"property":"flex","value":"1","important":false,"line":556},{"property":"padding","value":"var(--space-2) var(--space-3)","important":false,"line":557},{"property":"border","value":"1px solid var(--border)","important":false,"line":558},{"property":"border-radius","value":"var(--radius-md)","important":false,"line":559},{"property":"background","value":"var(--bg-surface)","important":false,"line":560},{"property":"color","value":"var(--text-primary)","important":false,"line":561},{"property":"font-size","value":"var(--font-sm)","important":false,"line":562},{"property":"cursor","value":"pointer","important":false,"line":563}],"owner":"Button/裸Control/Tabs等、対応JSONで登録した外観owner。width/min-width/flex/resize等の原値は用途契約として維持"}]
selector_retention_note: selector/ownerを維持する判定と、宣言値の維持を区別する。元declarationsは観測値、移管後の値はdesign_contract/actionsに従う
layout: [{"property":"flex","value":"1","important":false,"line":556}]
appearance: [{"property":"padding","value":"var(--space-2) var(--space-3)","important":false,"line":557},{"property":"border","value":"1px solid var(--border)","important":false,"line":558},{"property":"border-radius","value":"var(--radius-md)","important":false,"line":559},{"property":"background","value":"var(--bg-surface)","important":false,"line":560},{"property":"color","value":"var(--text-primary)","important":false,"line":561},{"property":"font-size","value":"var(--font-sm)","important":false,"line":562},{"property":"cursor","value":"pointer","important":false,"line":563}]
declarations: flex: 1; padding: var(--space-2) var(--space-3); border: 1px solid var(--border); border-radius: var(--radius-md); background: var(--bg-surface); color: var(--text-primary); font-size: var(--font-sm); cursor: pointer

### CSSI-0182  src/pages/inbox/InboxPage.css:69
selector: `.inbox-platform-select` conditions=[] tags=[]
disposition: 外配置へ移管＋部品CSSへ削除移管
reason: 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持
actions: [{"action":"外配置へ移管","declarations":[{"property":"margin-left","value":"auto","important":false,"line":70}],"owner":"既存page/feature layout。nativeに新規wrapperを加えない"},{"action":"部品CSSへ削除移管","declarations":[{"property":"flex-shrink","value":"0","important":false,"line":71},{"property":"height","value":"var(--height-tab-item)","important":false,"line":72},{"property":"padding","value":"0 var(--space-2)","important":false,"line":73},{"property":"border","value":"1px solid var(--border)","important":false,"line":74},{"property":"border-radius","value":"var(--radius-sm)","important":false,"line":75},{"property":"background","value":"var(--bg-surface)","important":false,"line":76},{"property":"color","value":"var(--text-secondary)","important":false,"line":77},{"property":"font-size","value":"var(--font-xs)","important":false,"line":78},{"property":"font-family","value":"inherit","important":false,"line":79},{"property":"cursor","value":"pointer","important":false,"line":80}],"owner":"Button/裸Control/Tabs等、対応JSONで登録した外観owner。width/min-width/flex/resize等の原値は用途契約として維持"}]
selector_retention_note: selector/ownerを維持する判定と、宣言値の維持を区別する。元declarationsは観測値、移管後の値はdesign_contract/actionsに従う
layout: [{"property":"margin-left","value":"auto","important":false,"line":70},{"property":"flex-shrink","value":"0","important":false,"line":71},{"property":"height","value":"var(--height-tab-item)","important":false,"line":72}]
appearance: [{"property":"padding","value":"0 var(--space-2)","important":false,"line":73},{"property":"border","value":"1px solid var(--border)","important":false,"line":74},{"property":"border-radius","value":"var(--radius-sm)","important":false,"line":75},{"property":"background","value":"var(--bg-surface)","important":false,"line":76},{"property":"color","value":"var(--text-secondary)","important":false,"line":77},{"property":"font-size","value":"var(--font-xs)","important":false,"line":78},{"property":"font-family","value":"inherit","important":false,"line":79},{"property":"cursor","value":"pointer","important":false,"line":80}]
declarations: margin-left: auto; flex-shrink: 0; height: var(--height-tab-item); padding: 0 var(--space-2); border: 1px solid var(--border); border-radius: var(--radius-sm); background: var(--bg-surface); color: var(--text-secondary); font-size: var(--font-xs); font-family: inherit; cursor: pointer

### CSSI-0183  src/pages/inbox/InboxPage.css:82
selector: `.inbox-platform-select:focus` conditions=[] tags=[]
disposition: 部品CSSへ削除移管
reason: 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持
actions: [{"action":"部品CSSへ削除移管","declarations":[{"property":"outline","value":"none","important":false,"line":83},{"property":"border-color","value":"var(--accent)","important":false,"line":84},{"property":"color","value":"var(--text-primary)","important":false,"line":85}],"owner":"Button/裸Control/Tabs等、対応JSONで登録した外観owner。width/min-width/flex/resize等の原値は用途契約として維持"}]
selector_retention_note: selector/ownerを維持する判定と、宣言値の維持を区別する。元declarationsは観測値、移管後の値はdesign_contract/actionsに従う
layout: []
appearance: [{"property":"outline","value":"none","important":false,"line":83},{"property":"border-color","value":"var(--accent)","important":false,"line":84},{"property":"color","value":"var(--text-primary)","important":false,"line":85}]
declarations: outline: none; border-color: var(--accent); color: var(--text-primary)

### CSSI-0202  src/pages/inbox/InboxPage.css:412
selector: `.inbox-page-filter-select` conditions=[] tags=[]
disposition: 部品CSSへ削除移管
reason: 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持
actions: [{"action":"部品CSSへ削除移管","declarations":[{"property":"width","value":"100%","important":false,"line":413},{"property":"padding","value":"var(--space-1) var(--space-2)","important":false,"line":414},{"property":"font-size","value":"var(--font-xs)","important":false,"line":415},{"property":"border-radius","value":"var(--radius-xl)","important":false,"line":416},{"property":"border","value":"1px solid var(--border)","important":false,"line":417},{"property":"background","value":"var(--bg-surface)","important":false,"line":418},{"property":"color","value":"var(--text-primary)","important":false,"line":419},{"property":"font-family","value":"inherit","important":false,"line":420},{"property":"box-sizing","value":"border-box","important":false,"line":421}],"owner":"Button/裸Control/Tabs等、対応JSONで登録した外観owner。width/min-width/flex/resize等の原値は用途契約として維持"}]
selector_retention_note: selector/ownerを維持する判定と、宣言値の維持を区別する。元declarationsは観測値、移管後の値はdesign_contract/actionsに従う
layout: [{"property":"width","value":"100%","important":false,"line":413}]
appearance: [{"property":"padding","value":"var(--space-1) var(--space-2)","important":false,"line":414},{"property":"font-size","value":"var(--font-xs)","important":false,"line":415},{"property":"border-radius","value":"var(--radius-xl)","important":false,"line":416},{"property":"border","value":"1px solid var(--border)","important":false,"line":417},{"property":"background","value":"var(--bg-surface)","important":false,"line":418},{"property":"color","value":"var(--text-primary)","important":false,"line":419},{"property":"font-family","value":"inherit","important":false,"line":420},{"property":"box-sizing","value":"border-box","important":false,"line":421}]
declarations: width: 100%; padding: var(--space-1) var(--space-2); font-size: var(--font-xs); border-radius: var(--radius-xl); border: 1px solid var(--border); background: var(--bg-surface); color: var(--text-primary); font-family: inherit; box-sizing: border-box

### CSSI-0229  src/pages/inbox/InboxPage.css:1188
selector: `.right-panel-field` conditions=[] tags=[]
disposition: 部品CSSへ削除移管
reason: 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持
actions: [{"action":"部品CSSへ削除移管","declarations":[{"property":"width","value":"100%","important":false,"line":1189},{"property":"box-sizing","value":"border-box","important":false,"line":1189},{"property":"background","value":"var(--karte-field-bg)","important":false,"line":1190},{"property":"border","value":"0.5px solid var(--karte-field-bd)","important":false,"line":1190},{"property":"border-radius","value":"var(--radius-md)","important":false,"line":1191},{"property":"padding","value":"var(--karte-field-py) var(--karte-field-px)","important":false,"line":1191},{"property":"font-size","value":"var(--font-sm)","important":false,"line":1192},{"property":"color","value":"var(--text-primary)","important":false,"line":1192},{"property":"font-family","value":"inherit","important":false,"line":1193},{"property":"transition","value":"border-color var(--transition-micro)","important":false,"line":1194}],"owner":"Button/裸Control/Tabs等、対応JSONで登録した外観owner。width/min-width/flex/resize等の原値は用途契約として維持"}]
selector_retention_note: selector/ownerを維持する判定と、宣言値の維持を区別する。元declarationsは観測値、移管後の値はdesign_contract/actionsに従う
layout: [{"property":"width","value":"100%","important":false,"line":1189}]
appearance: [{"property":"box-sizing","value":"border-box","important":false,"line":1189},{"property":"background","value":"var(--karte-field-bg)","important":false,"line":1190},{"property":"border","value":"0.5px solid var(--karte-field-bd)","important":false,"line":1190},{"property":"border-radius","value":"var(--radius-md)","important":false,"line":1191},{"property":"padding","value":"var(--karte-field-py) var(--karte-field-px)","important":false,"line":1191},{"property":"font-size","value":"var(--font-sm)","important":false,"line":1192},{"property":"color","value":"var(--text-primary)","important":false,"line":1192},{"property":"font-family","value":"inherit","important":false,"line":1193},{"property":"transition","value":"border-color var(--transition-micro)","important":false,"line":1194}]
declarations: width: 100%; box-sizing: border-box; background: var(--karte-field-bg); border: 0.5px solid var(--karte-field-bd); border-radius: var(--radius-md); padding: var(--karte-field-py) var(--karte-field-px); font-size: var(--font-sm); color: var(--text-primary); font-family: inherit; transition: border-color var(--transition-micro)

### CSSI-0230  src/pages/inbox/InboxPage.css:1196
selector: `.right-panel-field::placeholder` conditions=[] tags=[]
disposition: 部品CSSへ削除移管
reason: 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持
actions: [{"action":"部品CSSへ削除移管","declarations":[{"property":"color","value":"var(--text-muted)","important":false,"line":1196}],"owner":"Button/裸Control/Tabs等、対応JSONで登録した外観owner。width/min-width/flex/resize等の原値は用途契約として維持"}]
selector_retention_note: selector/ownerを維持する判定と、宣言値の維持を区別する。元declarationsは観測値、移管後の値はdesign_contract/actionsに従う
layout: []
appearance: [{"property":"color","value":"var(--text-muted)","important":false,"line":1196}]
declarations: color: var(--text-muted)

### CSSI-0231  src/pages/inbox/InboxPage.css:1198
selector: `select.right-panel-field` conditions=[] tags=["select"]
disposition: 部品CSSへ削除移管
reason: root設計案で解決: SelectControl indicator=none。現行appearance:noneと矢印なしを維持。native select1個、追加矢印DOMなし
actions: [{"action":"外配置へ移管","declarations":[],"owner":"同nativeの配置専用class。新wrapperなし"},{"action":"部品CSSへ削除移管","declarations":[{"property":"appearance","value":"none","important":false,"line":1198},{"property":"-webkit-appearance","value":"none","important":false,"line":1198}],"owner":"共通入力Control。design_contractを適用"}]
selector_retention_note: selector/ownerを維持する判定と、宣言値の維持を区別する。元declarationsは観測値、移管後の値はdesign_contract/actionsに従う
layout: []
appearance: [{"property":"appearance","value":"none","important":false,"line":1198},{"property":"-webkit-appearance","value":"none","important":false,"line":1198}]
declarations: appearance: none; -webkit-appearance: none

### CSSI-0232  src/pages/inbox/InboxPage.css:1199
selector: `.right-panel-field:focus` conditions=[] tags=[]
disposition: 部品CSSへ削除移管
reason: 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持
actions: [{"action":"部品CSSへ削除移管","declarations":[{"property":"outline","value":"none","important":false,"line":1199},{"property":"border-color","value":"var(--accent)","important":false,"line":1199}],"owner":"Button/裸Control/Tabs等、対応JSONで登録した外観owner。width/min-width/flex/resize等の原値は用途契約として維持"}]
selector_retention_note: selector/ownerを維持する判定と、宣言値の維持を区別する。元declarationsは観測値、移管後の値はdesign_contract/actionsに従う
layout: []
appearance: [{"property":"outline","value":"none","important":false,"line":1199},{"property":"border-color","value":"var(--accent)","important":false,"line":1199}]
declarations: outline: none; border-color: var(--accent)

### CSSI-0233  src/pages/inbox/InboxPage.css:1200
selector: `textarea.right-panel-field` conditions=[] tags=["textarea"]
disposition: 外配置へ移管＋部品CSSへ削除移管
reason: root設計案で解決: TextareaControl resize=none。min-height=var(--inbox-textarea-min-h)は同nativeの名前付き配置classで保持。wrapperなし
actions: [{"action":"外配置へ移管","declarations":[{"property":"min-height","value":"var(--inbox-textarea-min-h)","important":false,"line":1200}],"owner":"同nativeの配置専用class。新wrapperなし"},{"action":"部品CSSへ削除移管","declarations":[{"property":"resize","value":"none","important":false,"line":1200}],"owner":"共通入力Control。design_contractを適用"}]
selector_retention_note: selector/ownerを維持する判定と、宣言値の維持を区別する。元declarationsは観測値、移管後の値はdesign_contract/actionsに従う
layout: [{"property":"min-height","value":"var(--inbox-textarea-min-h)","important":false,"line":1200}]
appearance: [{"property":"resize","value":"none","important":false,"line":1200}]
declarations: resize: none; min-height: var(--inbox-textarea-min-h)

### CSSI-0244  src/pages/inbox/InboxPage.css:1432
selector: `.inbox-settings-select` conditions=[] tags=[]
disposition: 部品CSSへ削除移管
reason: 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持
actions: [{"action":"部品CSSへ削除移管","declarations":[{"property":"background","value":"var(--bg-primary)","important":false,"line":1433},{"property":"border","value":"1px solid var(--border)","important":false,"line":1433},{"property":"border-radius","value":"var(--radius-sm)","important":false,"line":1434},{"property":"padding","value":"var(--space-1) var(--space-2)","important":false,"line":1434},{"property":"font-size","value":"var(--font-sm)","important":false,"line":1435},{"property":"color","value":"var(--text-primary)","important":false,"line":1435},{"property":"cursor","value":"pointer","important":false,"line":1436}],"owner":"Button/裸Control/Tabs等、対応JSONで登録した外観owner。width/min-width/flex/resize等の原値は用途契約として維持"}]
selector_retention_note: selector/ownerを維持する判定と、宣言値の維持を区別する。元declarationsは観測値、移管後の値はdesign_contract/actionsに従う
layout: []
appearance: [{"property":"background","value":"var(--bg-primary)","important":false,"line":1433},{"property":"border","value":"1px solid var(--border)","important":false,"line":1433},{"property":"border-radius","value":"var(--radius-sm)","important":false,"line":1434},{"property":"padding","value":"var(--space-1) var(--space-2)","important":false,"line":1434},{"property":"font-size","value":"var(--font-sm)","important":false,"line":1435},{"property":"color","value":"var(--text-primary)","important":false,"line":1435},{"property":"cursor","value":"pointer","important":false,"line":1436}]
declarations: background: var(--bg-primary); border: 1px solid var(--border); border-radius: var(--radius-sm); padding: var(--space-1) var(--space-2); font-size: var(--font-sm); color: var(--text-primary); cursor: pointer

### CSSI-0271  src/pages/schedule.css:843
selector: `.schedule-input` conditions=[] tags=[]
disposition: 部品CSSへ削除移管
reason: 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持
actions: [{"action":"部品CSSへ削除移管","declarations":[{"property":"width","value":"100%","important":false,"line":845},{"property":"border","value":"1px solid var(--border)","important":false,"line":846},{"property":"border-radius","value":"var(--radius-md)","important":false,"line":847},{"property":"background","value":"var(--bg-surface)","important":false,"line":848},{"property":"color","value":"var(--text-primary)","important":false,"line":849},{"property":"font-size","value":"var(--font-sm)","important":false,"line":850}],"owner":"Button/裸Control/Tabs等、対応JSONで登録した外観owner。width/min-width/flex/resize等の原値は用途契約として維持"}]
selector_retention_note: selector/ownerを維持する判定と、宣言値の維持を区別する。元declarationsは観測値、移管後の値はdesign_contract/actionsに従う
layout: [{"property":"width","value":"100%","important":false,"line":845}]
appearance: [{"property":"border","value":"1px solid var(--border)","important":false,"line":846},{"property":"border-radius","value":"var(--radius-md)","important":false,"line":847},{"property":"background","value":"var(--bg-surface)","important":false,"line":848},{"property":"color","value":"var(--text-primary)","important":false,"line":849},{"property":"font-size","value":"var(--font-sm)","important":false,"line":850}]
declarations: width: 100%; border: 1px solid var(--border); border-radius: var(--radius-md); background: var(--bg-surface); color: var(--text-primary); font-size: var(--font-sm)

### CSSI-0273  src/pages/schedule.css:853
selector: `.schedule-input` conditions=[] tags=[]
disposition: 部品CSSへ削除移管
reason: 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持
actions: [{"action":"部品CSSへ削除移管","declarations":[{"property":"min-height","value":"var(--comp-input-height-sm)","important":false,"line":854},{"property":"padding","value":"0 var(--space-3)","important":false,"line":855}],"owner":"Button/裸Control/Tabs等、対応JSONで登録した外観owner。width/min-width/flex/resize等の原値は用途契約として維持"}]
selector_retention_note: selector/ownerを維持する判定と、宣言値の維持を区別する。元declarationsは観測値、移管後の値はdesign_contract/actionsに従う
layout: [{"property":"min-height","value":"var(--comp-input-height-sm)","important":false,"line":854}]
appearance: [{"property":"padding","value":"0 var(--space-3)","important":false,"line":855}]
declarations: min-height: var(--comp-input-height-sm); padding: 0 var(--space-3)

### CSSI-0275  src/pages/schedule.css:863
selector: `.schedule-input:focus` conditions=[] tags=[]
disposition: 部品CSSへ削除移管
reason: 今回置換するclass/タグへ掛かる外観宣言。page/featureからpaintを削除し共通Button/裸Control/Tabsのownerへ。配置は既存layout側が同じ要素を対象に保持
actions: [{"action":"部品CSSへ削除移管","declarations":[{"property":"outline","value":"none","important":false,"line":865},{"property":"border-color","value":"var(--accent)","important":false,"line":866},{"property":"box-shadow","value":"var(--focus-ring-shadow)","important":false,"line":867}],"owner":"Button/裸Control/Tabs等、対応JSONで登録した外観owner。width/min-width/flex/resize等の原値は用途契約として維持"}]
selector_retention_note: selector/ownerを維持する判定と、宣言値の維持を区別する。元declarationsは観測値、移管後の値はdesign_contract/actionsに従う
layout: []
appearance: [{"property":"outline","value":"none","important":false,"line":865},{"property":"border-color","value":"var(--accent)","important":false,"line":866},{"property":"box-shadow","value":"var(--focus-ring-shadow)","important":false,"line":867}]
declarations: outline: none; border-color: var(--accent); box-shadow: var(--focus-ring-shadow)


## 4. layoutClassName 許可property（final-ci-contract-audit.md 原文ママ）
```
    42	## layoutClassNameの有限契約（root確定）
    43	
    44	共通部品に渡すlayoutClassNameの配置classだけを対象とする。ページ一般のlayout styleを一律禁止する規則ではない。許可propertyの上限は次の完全リスト。実物から得た19propertyを含むことはrootの照合報告であり、本追補で独立再測定はしていない。
    45	
    46	```text
    47	display, position, inset, top, right, bottom, left, z-index,
    48	width, min-width, max-width, height, min-height, max-height,
    49	margin, margin-top, margin-right, margin-bottom, margin-left,
    50	margin-inline, margin-inline-start, margin-inline-end,
    51	margin-block, margin-block-start, margin-block-end,
    52	flex, flex-grow, flex-shrink, flex-basis, align-self, justify-self, order,
    53	grid-area, grid-column, grid-column-start, grid-column-end,
    54	grid-row, grid-row-start, grid-row-end
    55	```
    56	
    57	padding/gap/color/font/border/outline/shadow/radius/opacity/transformと独自CSS変数宣言は許可しない。上限リスト外のproperty、!important、定義を解決できないclassは規則違反exit1。CSS自体を読めない・解析できない場合はexit2。各classの関連宣言を有限selectorパターンで照合し、装飾を配置という名前で免除しない。
    58	
    59	部品が所有する寸法は上限リストからさらに除く。
    60	- Button/Toggle/Checkbox/Radio/通常TextField/Select: height/min-height/max-heightを禁止。size propsと所有CSSが管理する。
    61	- Icon: width/min-width/max-width/height/min-height/max-heightを禁止。sizeが管理する。
    62	- Textarea: min-heightを許可。Card等containerの寸法も許可。
```
