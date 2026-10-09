# AY-2b 外観の前後（Chromium 147.0.7727.15、幅 1280・375、light。base = origin/main fb036a238）

方法: ay2b-visual.cjs（ax2b-visual.cjs と同じ手法）。before = 現行ソースの CSS と className/inline style。after = 取り除く 4 規則を postcss で落とした CSS（ファイルは書き換えない）＋ TextFieldControl 標準（class は `comp-field__input` のみ。type・disabled・inline style は保持）。
取り除いた規則（実測時の postcss 走査ログ）: components.css:19 `.form-group input`（規則ごと削除=true） / components.css:30 `.form-group input:focus`（規則ごと削除=true） / pages-layout.css:246 `.login-card .form-group input`（規則ごと削除=true） / pages-layout.css:255 `.login-card .form-group input:focus`（規則ごと削除=true）
測定プロパティ: 42 件（padding・border・radius・font・line-height・color・background・height・min-height・width・transition・cursor・opacity・outline/box-shadow 等）+ ::placeholder color + offsetHeight/Width。状態: normal・focus、disabled 属性があるものだけ disabled。
祖先の外側（サイドバー等）は再現していないため width は合成コンテナ基準。before/after の比較にだけ使う。console 警告: なし
祖先未確定のみの要素（移管対象 18・非テキスト 10）は DOM を決められないため移管対象の測定には含めない（§4 の非テキストは「祖先連鎖どおり」で測定、差0は規則が当たらない連鎖だったことを意味する）。

## 1. 移管対象（確定 143 件）: before → after（TextFieldControl 標準）

### G01 .form-group input（136 件）幅 1280

測定 37 件（祖先シグネチャ(近傍4)×type×disabled属性ごとに 1 件）、代表が覆うメンバー延べ 154。type: text, number, date, dynamic, tel, omitted, password, email, url, time

normal（差のある 37 / 測定 37 件）:

| 項目 | before → after | 件数 |
|---|---|---|
| border-top-left-radius | 4px → 6px | 37/37 |
| border-top-right-radius | 4px → 6px | 37/37 |
| border-bottom-right-radius | 4px → 6px | 37/37 |
| border-bottom-left-radius | 4px → 6px | 37/37 |
| font-family | Arial → システムフォント列(-apple-system,…) | 34/37 |
| font-family | monospace → システムフォント列(-apple-system,…) | 3/37 |
| line-height | normal → 21.6px | 37/37 |
| height | 34px → 39.6094px | 34/37 |
| height | 37px → 41.6094px | 2/37 |
| height | 39.1094px → 41.6094px | 1/37 |
| transition-property | all → border-color, box-shadow | 37/37 |
| transition-duration | 0s → 0.1s, 0.1s | 37/37 |
| offsetHeight | 34 → 40 | 34/37 |
| offsetHeight | 37 → 42 | 2/37 |
| offsetHeight | 39 → 42 | 1/37 |

focus（差のある 37 / 測定 37 件）:

| 項目 | before → after | 件数 |
|---|---|---|
| border-top-left-radius | 4px → 6px | 37/37 |
| border-top-right-radius | 4px → 6px | 37/37 |
| border-bottom-right-radius | 4px → 6px | 37/37 |
| border-bottom-left-radius | 4px → 6px | 37/37 |
| font-family | Arial → システムフォント列(-apple-system,…) | 34/37 |
| font-family | monospace → システムフォント列(-apple-system,…) | 3/37 |
| line-height | normal → 21.6px | 37/37 |
| height | 34px → 39.6094px | 34/37 |
| height | 37px → 41.6094px | 2/37 |
| height | 39.1094px → 41.6094px | 1/37 |
| transition-property | all → border-color, box-shadow | 37/37 |
| transition-duration | 0s → 0.1s, 0.1s | 37/37 |
| offsetHeight | 34 → 40 | 34/37 |
| offsetHeight | 37 → 42 | 2/37 |
| offsetHeight | 39 → 42 | 1/37 |

disabled（差のある 4 / 測定 37 件）:

| 項目 | before → after | 件数 |
|---|---|---|
| border-top-left-radius | 4px → 6px | 4/4 |
| border-top-right-radius | 4px → 6px | 4/4 |
| border-bottom-right-radius | 4px → 6px | 4/4 |
| border-bottom-left-radius | 4px → 6px | 4/4 |
| font-family | Arial → システムフォント列(-apple-system,…) | 4/4 |
| line-height | normal → 21.6px | 4/4 |
| background-color | rgb(255, 255, 255) → rgb(226, 232, 240) | 4/4 |
| height | 34px → 39.6094px | 4/4 |
| cursor | default → not-allowed | 4/4 |
| opacity | 1 → 0.5 | 4/4 |
| transition-property | all → border-color, box-shadow | 4/4 |
| transition-duration | 0s → 0.1s, 0.1s | 4/4 |
| offsetHeight | 34 → 40 | 4/4 |

<details><summary>測定した要素</summary>

- components/ChannelTypeCombobox.tsx:91 [text] div<div<div.form-group<form<div (disabled属性あり)
- components/OrderFinancialPanel.tsx:223 [number] div.form-group<div<form<div.comp-modal-body<div.comp-modal-dialog
- components/PurchaseDetailPanel.tsx:328 [text] div.form-group<div<fieldset<form<div.comp-modal-body
- components/PurchaseDetailPanel.tsx:338 [date] div.form-group<div<fieldset<form<div.comp-modal-body
- components/PurchaseDetailPanel.tsx:361 [dynamic] div.form-group<div<fieldset<form<div.comp-modal-body
- components/PurchaseDetailPanel.tsx:385 [number] div.form-group<div<fieldset<form<div.comp-modal-body
- pages/account-settings/ProfileSection.tsx:163 [tel] div.form-group<form<section.account-settings-section<div.account-settings-layout<div
- pages/account-settings/ProfileSection.tsx:169 [omitted] div.form-group<div.account-settings-row<form<section.account-settings-section<div.account-settings-layout
- pages/account-settings/SecuritySection.tsx:67 [password] div.form-group<form<section.account-settings-section<div.account-settings-layout<div
- pages/admin/TenantPolicyPage.tsx:192 [number] div.form-group<form.form<div<div.page-layout<div.admin-hub-content (disabled属性あり)
- pages/admin/TenantPolicyPage.tsx:238 [text] div.form-group<form.form<div<div.page-layout<div.admin-hub-content (disabled属性あり)
- pages/admin/TenantProfilePage.tsx:196 [email] div.form-group<form.form<div<div.page-layout<div.admin-hub-content (disabled属性あり)
- pages/badges/BadgesPage.tsx:61 [omitted] div.form-group<form<div.comp-modal-body<div.comp-modal-dialog<div.comp-modal-overlay
- pages/badges/BadgesPage.tsx:66 [number] div.form-group<form<div.comp-modal-body<div.comp-modal-dialog<div.comp-modal-overlay
- pages/bots/BotFormFields.tsx:54 [omitted] div.form-group<form<div<div.page-layout<main.mobile-content
- pages/bots/BotFormFields.tsx:54 [omitted] div.form-group<form<div.comp-drawer-body<div.comp-drawer-panel<div
- pages/bots/BotFormFields.tsx:90 [email] div.form-group<form<div<div.page-layout<main.mobile-content
- pages/bots/BotFormFields.tsx:90 [email] div.form-group<form<div.comp-drawer-body<div.comp-drawer-panel<div
- pages/bots/BotsPage.tsx:258 [email] div.form-group<form<div.comp-modal-body<div.comp-modal-dialog<div.comp-modal-overlay
- pages/integrations/CarrierCredentialForm.tsx:95 [text] div.form-group<div.update-form<section.card.carrier-env-card.carrier-env-card--editing<div<div.page-layout
- pages/integrations/CarrierCredentialForm.tsx:95 [text] div.form-group<div.update-form<section.card.carrier-env-card.carrier-env-card--editing<section.etd-guide__step<section.etd-guide
- pages/integrations/CarrierCredentialForm.tsx:106 [password] div.form-group<div.update-form<section.card.carrier-env-card.carrier-env-card--editing<div<div.page-layout
- pages/integrations/CarrierCredentialForm.tsx:106 [password] div.form-group<div.update-form<section.card.carrier-env-card.carrier-env-card--editing<section.etd-guide__step<section.etd-guide
- pages/integrations/FedexLabelValidationTab.tsx:334 [text] div.form-group<div.update-form<section.lv-step.card<div.lv-part<div.lv-wizard
- pages/integrations/GoogleDriveIntegrationPage.tsx:162 [url] div.form-group<section.card<div<div.page-layout<div.hub-content
- pages/integrations/PaypalIntegrationPage.tsx:144 [text] div.form-group<section.card<div<div.page-layout<div.hub-content
- pages/integrations/PaypalIntegrationPage.tsx:154 [password] div.form-group<section.card<div<div.page-layout<div.hub-content
- pages/invoice-create/InvoiceCreatePage.tsx:317 [omitted] div.form-group<div<form<div<div.page-layout
- pages/invoice-create/InvoiceCreatePage.tsx:419 [number] div.form-group<div<form<div<div.page-layout
- pages/leads/LeadEditPage.tsx:277 [number] div.form-group<form<div<div.page-layout<main.mobile-content
- pages/quote-create/QuoteCreatePage.tsx:268 [number] div<div.form-group<div<form<div
- pages/roles/RolesPage.tsx:556 [number] div.form-group<div.comp-modal-body<div.comp-modal-dialog<div.comp-modal-overlay<div.page.roles-page
- pages/shifts/ShiftsPage.tsx:64 [date] div.form-group<form<div.comp-modal-body<div.comp-modal-dialog<div.comp-modal-overlay
- pages/shifts/ShiftsPage.tsx:65 [time] div.form-group<form<div.comp-modal-body<div.comp-modal-dialog<div.comp-modal-overlay
- pages/super-admin/KnowledgeAliasesTab.tsx:464 [omitted] div.form-group<div<form<div.comp-modal-body<div.comp-modal-dialog
- pages/teams/TeamFormFields.tsx:36 [number] div.form-group<form<div.comp-drawer-body<div.comp-drawer-panel<div
- pages/teams/TeamsPage.tsx:242 [number] div.form-group<form.teams-add-member-form<div.comp-modal-body<div.comp-modal-dialog<div.comp-modal-overlay

</details>

### G01 .form-group input（136 件）幅 375

測定 37 件（祖先シグネチャ(近傍4)×type×disabled属性ごとに 1 件）、代表が覆うメンバー延べ 154。type: text, number, date, dynamic, tel, omitted, password, email, url, time

normal（差のある 37 / 測定 37 件）:

| 項目 | before → after | 件数 |
|---|---|---|
| border-top-left-radius | 4px → 6px | 37/37 |
| border-top-right-radius | 4px → 6px | 37/37 |
| border-bottom-right-radius | 4px → 6px | 37/37 |
| border-bottom-left-radius | 4px → 6px | 37/37 |
| font-family | Arial → システムフォント列(-apple-system,…) | 34/37 |
| font-family | monospace → システムフォント列(-apple-system,…) | 3/37 |
| line-height | normal → 21.6px | 37/37 |
| height | 34px → 44px | 34/37 |
| height | 37px → 44px | 2/37 |
| height | 39.1094px → 44px | 1/37 |
| min-height | 0px → 44px | 37/37 |
| transition-property | all → border-color, box-shadow | 37/37 |
| transition-duration | 0s → 0.1s, 0.1s | 37/37 |
| offsetHeight | 34 → 44 | 34/37 |
| offsetHeight | 37 → 44 | 2/37 |
| offsetHeight | 39 → 44 | 1/37 |

focus（差のある 37 / 測定 37 件）:

| 項目 | before → after | 件数 |
|---|---|---|
| border-top-left-radius | 4px → 6px | 37/37 |
| border-top-right-radius | 4px → 6px | 37/37 |
| border-bottom-right-radius | 4px → 6px | 37/37 |
| border-bottom-left-radius | 4px → 6px | 37/37 |
| font-family | Arial → システムフォント列(-apple-system,…) | 34/37 |
| font-family | monospace → システムフォント列(-apple-system,…) | 3/37 |
| line-height | normal → 21.6px | 37/37 |
| height | 34px → 44px | 34/37 |
| height | 37px → 44px | 2/37 |
| height | 39.1094px → 44px | 1/37 |
| min-height | 0px → 44px | 37/37 |
| transition-property | all → border-color, box-shadow | 37/37 |
| transition-duration | 0s → 0.1s, 0.1s | 37/37 |
| offsetHeight | 34 → 44 | 34/37 |
| offsetHeight | 37 → 44 | 2/37 |
| offsetHeight | 39 → 44 | 1/37 |

disabled（差のある 4 / 測定 37 件）:

| 項目 | before → after | 件数 |
|---|---|---|
| border-top-left-radius | 4px → 6px | 4/4 |
| border-top-right-radius | 4px → 6px | 4/4 |
| border-bottom-right-radius | 4px → 6px | 4/4 |
| border-bottom-left-radius | 4px → 6px | 4/4 |
| font-family | Arial → システムフォント列(-apple-system,…) | 4/4 |
| line-height | normal → 21.6px | 4/4 |
| background-color | rgb(255, 255, 255) → rgb(226, 232, 240) | 4/4 |
| height | 34px → 44px | 4/4 |
| min-height | 0px → 44px | 4/4 |
| cursor | default → not-allowed | 4/4 |
| opacity | 1 → 0.5 | 4/4 |
| transition-property | all → border-color, box-shadow | 4/4 |
| transition-duration | 0s → 0.1s, 0.1s | 4/4 |
| offsetHeight | 34 → 44 | 4/4 |

<details><summary>測定した要素</summary>

- components/ChannelTypeCombobox.tsx:91 [text] div<div<div.form-group<form<div (disabled属性あり)
- components/OrderFinancialPanel.tsx:223 [number] div.form-group<div<form<div.comp-modal-body<div.comp-modal-dialog
- components/PurchaseDetailPanel.tsx:328 [text] div.form-group<div<fieldset<form<div.comp-modal-body
- components/PurchaseDetailPanel.tsx:338 [date] div.form-group<div<fieldset<form<div.comp-modal-body
- components/PurchaseDetailPanel.tsx:361 [dynamic] div.form-group<div<fieldset<form<div.comp-modal-body
- components/PurchaseDetailPanel.tsx:385 [number] div.form-group<div<fieldset<form<div.comp-modal-body
- pages/account-settings/ProfileSection.tsx:163 [tel] div.form-group<form<section.account-settings-section<div.account-settings-layout<div
- pages/account-settings/ProfileSection.tsx:169 [omitted] div.form-group<div.account-settings-row<form<section.account-settings-section<div.account-settings-layout
- pages/account-settings/SecuritySection.tsx:67 [password] div.form-group<form<section.account-settings-section<div.account-settings-layout<div
- pages/admin/TenantPolicyPage.tsx:192 [number] div.form-group<form.form<div<div.page-layout<div.admin-hub-content (disabled属性あり)
- pages/admin/TenantPolicyPage.tsx:238 [text] div.form-group<form.form<div<div.page-layout<div.admin-hub-content (disabled属性あり)
- pages/admin/TenantProfilePage.tsx:196 [email] div.form-group<form.form<div<div.page-layout<div.admin-hub-content (disabled属性あり)
- pages/badges/BadgesPage.tsx:61 [omitted] div.form-group<form<div.comp-modal-body<div.comp-modal-dialog<div.comp-modal-overlay
- pages/badges/BadgesPage.tsx:66 [number] div.form-group<form<div.comp-modal-body<div.comp-modal-dialog<div.comp-modal-overlay
- pages/bots/BotFormFields.tsx:54 [omitted] div.form-group<form<div<div.page-layout<main.mobile-content
- pages/bots/BotFormFields.tsx:54 [omitted] div.form-group<form<div.comp-drawer-body<div.comp-drawer-panel<div
- pages/bots/BotFormFields.tsx:90 [email] div.form-group<form<div<div.page-layout<main.mobile-content
- pages/bots/BotFormFields.tsx:90 [email] div.form-group<form<div.comp-drawer-body<div.comp-drawer-panel<div
- pages/bots/BotsPage.tsx:258 [email] div.form-group<form<div.comp-modal-body<div.comp-modal-dialog<div.comp-modal-overlay
- pages/integrations/CarrierCredentialForm.tsx:95 [text] div.form-group<div.update-form<section.card.carrier-env-card.carrier-env-card--editing<div<div.page-layout
- pages/integrations/CarrierCredentialForm.tsx:95 [text] div.form-group<div.update-form<section.card.carrier-env-card.carrier-env-card--editing<section.etd-guide__step<section.etd-guide
- pages/integrations/CarrierCredentialForm.tsx:106 [password] div.form-group<div.update-form<section.card.carrier-env-card.carrier-env-card--editing<div<div.page-layout
- pages/integrations/CarrierCredentialForm.tsx:106 [password] div.form-group<div.update-form<section.card.carrier-env-card.carrier-env-card--editing<section.etd-guide__step<section.etd-guide
- pages/integrations/FedexLabelValidationTab.tsx:334 [text] div.form-group<div.update-form<section.lv-step.card<div.lv-part<div.lv-wizard
- pages/integrations/GoogleDriveIntegrationPage.tsx:162 [url] div.form-group<section.card<div<div.page-layout<div.hub-content
- pages/integrations/PaypalIntegrationPage.tsx:144 [text] div.form-group<section.card<div<div.page-layout<div.hub-content
- pages/integrations/PaypalIntegrationPage.tsx:154 [password] div.form-group<section.card<div<div.page-layout<div.hub-content
- pages/invoice-create/InvoiceCreatePage.tsx:317 [omitted] div.form-group<div<form<div<div.page-layout
- pages/invoice-create/InvoiceCreatePage.tsx:419 [number] div.form-group<div<form<div<div.page-layout
- pages/leads/LeadEditPage.tsx:277 [number] div.form-group<form<div<div.page-layout<main.mobile-content
- pages/quote-create/QuoteCreatePage.tsx:268 [number] div<div.form-group<div<form<div
- pages/roles/RolesPage.tsx:556 [number] div.form-group<div.comp-modal-body<div.comp-modal-dialog<div.comp-modal-overlay<div.page.roles-page
- pages/shifts/ShiftsPage.tsx:64 [date] div.form-group<form<div.comp-modal-body<div.comp-modal-dialog<div.comp-modal-overlay
- pages/shifts/ShiftsPage.tsx:65 [time] div.form-group<form<div.comp-modal-body<div.comp-modal-dialog<div.comp-modal-overlay
- pages/super-admin/KnowledgeAliasesTab.tsx:464 [omitted] div.form-group<div<form<div.comp-modal-body<div.comp-modal-dialog
- pages/teams/TeamFormFields.tsx:36 [number] div.form-group<form<div.comp-drawer-body<div.comp-drawer-panel<div
- pages/teams/TeamsPage.tsx:242 [number] div.form-group<form.teams-add-member-form<div.comp-modal-body<div.comp-modal-dialog<div.comp-modal-overlay

</details>

### G28-31 .form-group input + inline style（4 件）幅 1280

測定 12 件（全メンバー）、代表が覆うメンバー延べ 12。type: text, omitted, number

normal（差のある 12 / 測定 12 件）:

| 項目 | before → after | 件数 |
|---|---|---|
| border-top-left-radius | 4px → 6px | 12/12 |
| border-top-right-radius | 4px → 6px | 12/12 |
| border-bottom-right-radius | 4px → 6px | 12/12 |
| border-bottom-left-radius | 4px → 6px | 12/12 |
| font-family | Arial → システムフォント列(-apple-system,…) | 12/12 |
| line-height | normal → 21.6px | 12/12 |
| height | 30px → 35.6094px | 3/12 |
| height | 34px → 39.6094px | 9/12 |
| transition-property | all → border-color, box-shadow | 12/12 |
| transition-duration | 0s → 0.1s, 0.1s | 12/12 |
| offsetHeight | 30 → 36 | 3/12 |
| offsetHeight | 34 → 40 | 9/12 |

focus（差のある 12 / 測定 12 件）:

| 項目 | before → after | 件数 |
|---|---|---|
| border-top-left-radius | 4px → 6px | 12/12 |
| border-top-right-radius | 4px → 6px | 12/12 |
| border-bottom-right-radius | 4px → 6px | 12/12 |
| border-bottom-left-radius | 4px → 6px | 12/12 |
| font-family | Arial → システムフォント列(-apple-system,…) | 12/12 |
| line-height | normal → 21.6px | 12/12 |
| height | 30px → 35.6094px | 3/12 |
| height | 34px → 39.6094px | 9/12 |
| transition-property | all → border-color, box-shadow | 12/12 |
| transition-duration | 0s → 0.1s, 0.1s | 12/12 |
| offsetHeight | 30 → 36 | 3/12 |
| offsetHeight | 34 → 40 | 9/12 |

disabled（差のある 3 / 測定 12 件）:

| 項目 | before → after | 件数 |
|---|---|---|
| border-top-left-radius | 4px → 6px | 3/3 |
| border-top-right-radius | 4px → 6px | 3/3 |
| border-bottom-right-radius | 4px → 6px | 3/3 |
| border-bottom-left-radius | 4px → 6px | 3/3 |
| font-family | Arial → システムフォント列(-apple-system,…) | 3/3 |
| line-height | normal → 21.6px | 3/3 |
| background-color | rgb(255, 255, 255) → rgb(226, 232, 240) | 3/3 |
| height | 30px → 35.6094px | 3/3 |
| cursor | default → not-allowed | 3/3 |
| opacity | 1 → 0.5 | 3/3 |
| transition-property | all → border-color, box-shadow | 3/3 |
| transition-duration | 0s → 0.1s, 0.1s | 3/3 |
| offsetHeight | 30 → 36 | 3/3 |

inline style を外した場合（標準の素の値との差、normal のみ）: {"padding-top":["6px","8px"],"padding-right":["8px","12px"],"padding-bottom":["6px","8px"],"padding-left":["8px","12px"],"border-top-left-radius":["4px","6px"],"border-top-right-radius":["4px","6px"],"border-bottom-right-radius":["4px","6px"],"border-bottom-left-radius":["4px","6px"],"font-family":[ ; {"border-top-left-radius":["4px","6px"],"border-top-right-radius":["4px","6px"],"border-bottom-right-radius":["4px","6px"],"border-bottom-left-radius":["4px","6px"],"font-family":["Arial","-apple-system, \"system-ui\", \"Segoe UI\", Roboto, Oxygen, Ubuntu, Cantarell, \"Fira Sans\", \"Droid Sans\", \

inline style の内訳: width:100%;min-width:var(--min-width-input-sm);padding:var(--space-6px) var(--space-2) ; min-width:var(--min-width-input-sm) ; width:var(--input-width-qty) ; width:var(--input-width-year)。この inline が指定する width/min-width/padding は after でも保持され、前後差には現れない。

<details><summary>測定した要素</summary>

- components/InventoryPicker.tsx:217 [text] div.inventory-picker<td<tr<tbody<table.data-table (disabled属性あり)
- components/InventoryPicker.tsx:217 [text] div.inventory-picker<td<tr<tbody<table.data-table (disabled属性あり)
- components/InventoryPicker.tsx:217 [text] div.inventory-picker<td<tr<tbody<table.data-table (disabled属性あり)
- pages/purchase-orders/PurchaseOrdersFormModal.tsx:191 [omitted] td<tr<tbody<table.data-table<div.form-group
- pages/purchase-orders/PurchaseOrdersFormModal.tsx:191 [omitted] td<tr<tbody<table.data-table<div.form-group
- pages/purchase-orders/PurchaseOrdersFormModal.tsx:191 [omitted] td<tr<tbody<table.data-table<div.form-group
- pages/purchase-orders/PurchaseOrdersFormModal.tsx:194 [number] td<tr<tbody<table.data-table<div.form-group
- pages/purchase-orders/PurchaseOrdersFormModal.tsx:194 [number] td<tr<tbody<table.data-table<div.form-group
- pages/purchase-orders/PurchaseOrdersFormModal.tsx:194 [number] td<tr<tbody<table.data-table<div.form-group
- pages/purchase-orders/PurchaseOrdersFormModal.tsx:197 [number] td<tr<tbody<table.data-table<div.form-group
- pages/purchase-orders/PurchaseOrdersFormModal.tsx:197 [number] td<tr<tbody<table.data-table<div.form-group
- pages/purchase-orders/PurchaseOrdersFormModal.tsx:197 [number] td<tr<tbody<table.data-table<div.form-group

</details>

### G28-31 .form-group input + inline style（4 件）幅 375

測定 12 件（全メンバー）、代表が覆うメンバー延べ 12。type: text, omitted, number

normal（差のある 12 / 測定 12 件）:

| 項目 | before → after | 件数 |
|---|---|---|
| border-top-left-radius | 4px → 6px | 12/12 |
| border-top-right-radius | 4px → 6px | 12/12 |
| border-bottom-right-radius | 4px → 6px | 12/12 |
| border-bottom-left-radius | 4px → 6px | 12/12 |
| font-family | Arial → システムフォント列(-apple-system,…) | 12/12 |
| line-height | normal → 21.6px | 12/12 |
| height | 30px → 44px | 3/12 |
| height | 34px → 44px | 9/12 |
| min-height | 0px → 44px | 12/12 |
| transition-property | all → border-color, box-shadow | 12/12 |
| transition-duration | 0s → 0.1s, 0.1s | 12/12 |
| offsetHeight | 30 → 44 | 3/12 |
| offsetHeight | 34 → 44 | 9/12 |

focus（差のある 12 / 測定 12 件）:

| 項目 | before → after | 件数 |
|---|---|---|
| border-top-left-radius | 4px → 6px | 12/12 |
| border-top-right-radius | 4px → 6px | 12/12 |
| border-bottom-right-radius | 4px → 6px | 12/12 |
| border-bottom-left-radius | 4px → 6px | 12/12 |
| font-family | Arial → システムフォント列(-apple-system,…) | 12/12 |
| line-height | normal → 21.6px | 12/12 |
| height | 30px → 44px | 3/12 |
| height | 34px → 44px | 9/12 |
| min-height | 0px → 44px | 12/12 |
| transition-property | all → border-color, box-shadow | 12/12 |
| transition-duration | 0s → 0.1s, 0.1s | 12/12 |
| offsetHeight | 30 → 44 | 3/12 |
| offsetHeight | 34 → 44 | 9/12 |

disabled（差のある 3 / 測定 12 件）:

| 項目 | before → after | 件数 |
|---|---|---|
| border-top-left-radius | 4px → 6px | 3/3 |
| border-top-right-radius | 4px → 6px | 3/3 |
| border-bottom-right-radius | 4px → 6px | 3/3 |
| border-bottom-left-radius | 4px → 6px | 3/3 |
| font-family | Arial → システムフォント列(-apple-system,…) | 3/3 |
| line-height | normal → 21.6px | 3/3 |
| background-color | rgb(255, 255, 255) → rgb(226, 232, 240) | 3/3 |
| height | 30px → 44px | 3/3 |
| min-height | 0px → 44px | 3/3 |
| cursor | default → not-allowed | 3/3 |
| opacity | 1 → 0.5 | 3/3 |
| transition-property | all → border-color, box-shadow | 3/3 |
| transition-duration | 0s → 0.1s, 0.1s | 3/3 |
| offsetHeight | 30 → 44 | 3/3 |

inline style を外した場合（標準の素の値との差、normal のみ）: {"padding-top":["6px","8px"],"padding-right":["8px","12px"],"padding-bottom":["6px","8px"],"padding-left":["8px","12px"],"border-top-left-radius":["4px","6px"],"border-top-right-radius":["4px","6px"],"border-bottom-right-radius":["4px","6px"],"border-bottom-left-radius":["4px","6px"],"font-family":[ ; {"border-top-left-radius":["4px","6px"],"border-top-right-radius":["4px","6px"],"border-bottom-right-radius":["4px","6px"],"border-bottom-left-radius":["4px","6px"],"font-family":["Arial","-apple-system, \"system-ui\", \"Segoe UI\", Roboto, Oxygen, Ubuntu, Cantarell, \"Fira Sans\", \"Droid Sans\", \

inline style の内訳: width:100%;min-width:var(--min-width-input-sm);padding:var(--space-6px) var(--space-2) ; min-width:var(--min-width-input-sm) ; width:var(--input-width-qty) ; width:var(--input-width-year)。この inline が指定する width/min-width/padding は after でも保持され、前後差には現れない。

<details><summary>測定した要素</summary>

- components/InventoryPicker.tsx:217 [text] div.inventory-picker<td<tr<tbody<table.data-table (disabled属性あり)
- components/InventoryPicker.tsx:217 [text] div.inventory-picker<td<tr<tbody<table.data-table (disabled属性あり)
- components/InventoryPicker.tsx:217 [text] div.inventory-picker<td<tr<tbody<table.data-table (disabled属性あり)
- pages/purchase-orders/PurchaseOrdersFormModal.tsx:191 [omitted] td<tr<tbody<table.data-table<div.form-group
- pages/purchase-orders/PurchaseOrdersFormModal.tsx:191 [omitted] td<tr<tbody<table.data-table<div.form-group
- pages/purchase-orders/PurchaseOrdersFormModal.tsx:191 [omitted] td<tr<tbody<table.data-table<div.form-group
- pages/purchase-orders/PurchaseOrdersFormModal.tsx:194 [number] td<tr<tbody<table.data-table<div.form-group
- pages/purchase-orders/PurchaseOrdersFormModal.tsx:194 [number] td<tr<tbody<table.data-table<div.form-group
- pages/purchase-orders/PurchaseOrdersFormModal.tsx:194 [number] td<tr<tbody<table.data-table<div.form-group
- pages/purchase-orders/PurchaseOrdersFormModal.tsx:197 [number] td<tr<tbody<table.data-table<div.form-group
- pages/purchase-orders/PurchaseOrdersFormModal.tsx:197 [number] td<tr<tbody<table.data-table<div.form-group
- pages/purchase-orders/PurchaseOrdersFormModal.tsx:197 [number] td<tr<tbody<table.data-table<div.form-group

</details>

### G11 login (.login-card .form-group input)（3 件）幅 1280

測定 3 件（全メンバー）、代表が覆うメンバー延べ 3。type: email, password

normal（差のある 3 / 測定 3 件）:

| 項目 | before → after | 件数 |
|---|---|---|
| padding-top | 12px → 8px | 3/3 |
| padding-right | 16px → 12px | 3/3 |
| padding-bottom | 12px → 8px | 3/3 |
| padding-left | 16px → 12px | 3/3 |
| font-size | 16px → 14.4px | 3/3 |
| font-family | Arial → システムフォント列(-apple-system,…) | 3/3 |
| line-height | normal → 21.6px | 3/3 |
| height | 44px → 39.6094px | 3/3 |
| transition-property | all → border-color, box-shadow | 3/3 |
| transition-duration | 0s → 0.1s, 0.1s | 3/3 |
| offsetHeight | 44 → 40 | 3/3 |

focus（差のある 3 / 測定 3 件）:

| 項目 | before → after | 件数 |
|---|---|---|
| padding-top | 12px → 8px | 3/3 |
| padding-right | 16px → 12px | 3/3 |
| padding-bottom | 12px → 8px | 3/3 |
| padding-left | 16px → 12px | 3/3 |
| font-size | 16px → 14.4px | 3/3 |
| font-family | Arial → システムフォント列(-apple-system,…) | 3/3 |
| line-height | normal → 21.6px | 3/3 |
| height | 44px → 39.6094px | 3/3 |
| transition-property | all → border-color, box-shadow | 3/3 |
| transition-duration | 0s → 0.1s, 0.1s | 3/3 |
| offsetHeight | 44 → 40 | 3/3 |

<details><summary>測定した要素</summary>

- pages/login/LoginPage.tsx:93 [email] div.form-group<form<div.login-card<div.login-page
- pages/login/LoginPage.tsx:104 [password] div.form-group<form<div.login-card<div.login-page
- pages/login/LoginPage.tsx:136 [email] div.form-group<form<div.login-card<div.login-page

</details>

### G11 login (.login-card .form-group input)（3 件）幅 375

測定 3 件（全メンバー）、代表が覆うメンバー延べ 3。type: email, password

normal（差のある 3 / 測定 3 件）:

| 項目 | before → after | 件数 |
|---|---|---|
| padding-top | 12px → 8px | 3/3 |
| padding-right | 16px → 12px | 3/3 |
| padding-bottom | 12px → 8px | 3/3 |
| padding-left | 16px → 12px | 3/3 |
| font-size | 16px → 14.4px | 3/3 |
| font-family | Arial → システムフォント列(-apple-system,…) | 3/3 |
| line-height | normal → 21.6px | 3/3 |
| min-height | 0px → 44px | 3/3 |
| transition-property | all → border-color, box-shadow | 3/3 |
| transition-duration | 0s → 0.1s, 0.1s | 3/3 |

focus（差のある 3 / 測定 3 件）:

| 項目 | before → after | 件数 |
|---|---|---|
| padding-top | 12px → 8px | 3/3 |
| padding-right | 16px → 12px | 3/3 |
| padding-bottom | 12px → 8px | 3/3 |
| padding-left | 16px → 12px | 3/3 |
| font-size | 16px → 14.4px | 3/3 |
| font-family | Arial → システムフォント列(-apple-system,…) | 3/3 |
| line-height | normal → 21.6px | 3/3 |
| min-height | 0px → 44px | 3/3 |
| transition-property | all → border-color, box-shadow | 3/3 |
| transition-duration | 0s → 0.1s, 0.1s | 3/3 |

<details><summary>測定した要素</summary>

- pages/login/LoginPage.tsx:93 [email] div.form-group<form<div.login-card<div.login-page
- pages/login/LoginPage.tsx:104 [password] div.form-group<form<div.login-card<div.login-page
- pages/login/LoginPage.tsx:136 [email] div.form-group<form<div.login-card<div.login-page

</details>

## 2. 商品編集 G06（保留、14 件）

### 2-1. 4 規則だけ外した場合（独立規則なし）の before → after

幅 1280（14 件）:

normal（差のある 14 / 測定 14 件）:

| 項目 | before → after | 件数 |
|---|---|---|
| padding-top | 8px → 0px | 14/14 |
| padding-right | 12px → 0px | 14/14 |
| padding-bottom | 8px → 0px | 14/14 |
| padding-left | 12px → 0px | 14/14 |
| border-top-left-radius | 4px → 0px | 14/14 |
| border-top-right-radius | 4px → 0px | 14/14 |
| border-bottom-right-radius | 4px → 0px | 14/14 |
| border-bottom-left-radius | 4px → 0px | 14/14 |
| font-size | 14.4px → 13.3333px | 14/14 |
| color | rgb(26, 32, 44) → rgb(0, 0, 0) | 14/14 |
| height | 34px → 17px | 13/14 |
| height | 37px → 19.3281px | 1/14 |
| width | 1232px → 147px | 3/14 |
| width | 233.594px → 147px | 2/14 |
| width | 233.594px → 121.328px | 1/14 |
| width | 232.797px → 147px | 8/14 |
| outline-color | rgb(26, 32, 44) → rgb(0, 0, 0) | 14/14 |
| offsetHeight | 34 → 17 | 13/14 |
| offsetHeight | 37 → 19 | 1/14 |
| offsetWidth | 1232 → 147 | 3/14 |
| offsetWidth | 234 → 147 | 2/14 |
| offsetWidth | 234 → 121 | 1/14 |
| offsetWidth | 233 → 147 | 8/14 |
| ::placeholder color | rgb(26, 32, 44) → rgb(0, 0, 0) | 1/14 |

focus（差のある 14 / 測定 14 件）:

| 項目 | before → after | 件数 |
|---|---|---|
| padding-top | 8px → 0px | 14/14 |
| padding-right | 12px → 0px | 14/14 |
| padding-bottom | 8px → 0px | 14/14 |
| padding-left | 12px → 0px | 14/14 |
| border-top-left-radius | 4px → 0px | 14/14 |
| border-top-right-radius | 4px → 0px | 14/14 |
| border-bottom-right-radius | 4px → 0px | 14/14 |
| border-bottom-left-radius | 4px → 0px | 14/14 |
| font-size | 14.4px → 13.3333px | 14/14 |
| color | rgb(26, 32, 44) → rgb(0, 0, 0) | 14/14 |
| height | 34px → 17px | 13/14 |
| height | 37px → 19.3281px | 1/14 |
| width | 1232px → 147px | 3/14 |
| width | 233.594px → 147px | 2/14 |
| width | 233.594px → 121.328px | 1/14 |
| width | 232.797px → 147px | 8/14 |
| outline-style | none → auto | 14/14 |
| outline-width | 3px → 1px | 14/14 |
| outline-color | rgb(26, 32, 44) → rgb(0, 95, 204) | 14/14 |
| box-shadow | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px → none | 14/14 |
| offsetHeight | 34 → 17 | 13/14 |
| offsetHeight | 37 → 19 | 1/14 |
| offsetWidth | 1232 → 147 | 3/14 |
| offsetWidth | 234 → 147 | 2/14 |
| offsetWidth | 234 → 121 | 1/14 |
| offsetWidth | 233 → 147 | 8/14 |
| ::placeholder color | rgb(26, 32, 44) → rgb(0, 0, 0) | 1/14 |

幅 375（14 件）:

normal（差のある 14 / 測定 14 件）:

| 項目 | before → after | 件数 |
|---|---|---|
| padding-top | 8px → 0px | 14/14 |
| padding-right | 12px → 0px | 14/14 |
| padding-bottom | 8px → 0px | 14/14 |
| padding-left | 12px → 0px | 14/14 |
| border-top-left-radius | 4px → 0px | 14/14 |
| border-top-right-radius | 4px → 0px | 14/14 |
| border-bottom-right-radius | 4px → 0px | 14/14 |
| border-bottom-left-radius | 4px → 0px | 14/14 |
| font-size | 14.4px → 13.3333px | 14/14 |
| color | rgb(26, 32, 44) → rgb(0, 0, 0) | 14/14 |
| height | 34px → 17px | 13/14 |
| height | 37px → 19.3281px | 1/14 |
| width | 343px → 147px | 5/14 |
| width | 343px → 121.328px | 1/14 |
| width | 339px → 147px | 8/14 |
| outline-color | rgb(26, 32, 44) → rgb(0, 0, 0) | 14/14 |
| offsetHeight | 34 → 17 | 13/14 |
| offsetHeight | 37 → 19 | 1/14 |
| offsetWidth | 343 → 147 | 5/14 |
| offsetWidth | 343 → 121 | 1/14 |
| offsetWidth | 339 → 147 | 8/14 |
| ::placeholder color | rgb(26, 32, 44) → rgb(0, 0, 0) | 1/14 |

focus（差のある 14 / 測定 14 件）:

| 項目 | before → after | 件数 |
|---|---|---|
| padding-top | 8px → 0px | 14/14 |
| padding-right | 12px → 0px | 14/14 |
| padding-bottom | 8px → 0px | 14/14 |
| padding-left | 12px → 0px | 14/14 |
| border-top-left-radius | 4px → 0px | 14/14 |
| border-top-right-radius | 4px → 0px | 14/14 |
| border-bottom-right-radius | 4px → 0px | 14/14 |
| border-bottom-left-radius | 4px → 0px | 14/14 |
| font-size | 14.4px → 13.3333px | 14/14 |
| color | rgb(26, 32, 44) → rgb(0, 0, 0) | 14/14 |
| height | 34px → 17px | 13/14 |
| height | 37px → 19.3281px | 1/14 |
| width | 343px → 147px | 5/14 |
| width | 343px → 121.328px | 1/14 |
| width | 339px → 147px | 8/14 |
| outline-style | none → auto | 14/14 |
| outline-width | 3px → 1px | 14/14 |
| outline-color | rgb(26, 32, 44) → rgb(0, 95, 204) | 14/14 |
| box-shadow | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px → none | 14/14 |
| offsetHeight | 34 → 17 | 13/14 |
| offsetHeight | 37 → 19 | 1/14 |
| offsetWidth | 343 → 147 | 5/14 |
| offsetWidth | 343 → 121 | 1/14 |
| offsetWidth | 339 → 147 | 8/14 |
| ::placeholder color | rgb(26, 32, 44) → rgb(0, 0, 0) | 1/14 |

### 2-2. 独立規則を足した場合（差分0 の確認）

追加する規則（旧 `.form-group input` の宣言から border を除いたもの。border は company-forms.css:238 の既存規則が同値で持つ。focus の border-color も 238 が (0,4,1) で後勝ちのため不要）:

```css
.product-edit-form .form-group input:not([type="checkbox"]):not([type="radio"]) { width: 100%; padding: var(--space-2) var(--space-3); border-radius: var(--radius-sm); font-size: var(--font-base); color: var(--text-primary); background: var(--bg-surface); box-sizing: border-box; }
.product-edit-form .form-group input:not([type="checkbox"]):not([type="radio"]):focus { outline: none; box-shadow: var(--focus-ring-shadow); }
```

- 幅 1280: 差分 0 = 14 / 14 件（normal・focus、disabled 属性なし）
- 幅 375: 差分 0 = 14 / 14 件（normal・focus、disabled 属性なし）

（独立規則の宣言は旧 `.form-group input`/`:focus` の写し。light テーマでは --bg-surface=白・UA 既定背景も白のため background は測定上区別できない。dark では差が出うる。dark は本調査の範囲外=未確認 [?]。）

## 3. 既存 TextField/TextFieldControl（`.form-group` 配下 99 件）: 規則あり → なし

近傍4祖先×type×fullWidth/error/label/size/variant/tag ごとの代表 6 種。構造: `.form-group > div.comp-field > label + input.comp-field__input`。

### 幅 1280

- 代表 32 件 text div.form-group<div<form<div.comp-modal-body (pages/conditions/ConditionsPage.tsx他)
- 代表 3 件 number div.form-group<div<form<div.comp-modal-body (pages/conditions/ConditionsPage.tsx他)
- 代表 1 件 email div.form-group<div<form<div.comp-modal-body (pages/super-admin/SupplierMasterPage.tsx他)
- 代表 49 件 text div.form-group<div<form<div.comp-drawer-body (pages/super-admin/components/ConditionDefsMasterPanel.tsx他)
- 代表 13 件 number div.form-group<div<form<div.comp-drawer-body (pages/super-admin/components/ConditionDefsMasterPanel.tsx他)
- 代表 1 件 email div.form-group<div<form<div.comp-drawer-body (pages/super-admin/components/SupplierMasterPanel.tsx他)

normal（差のある 6 / 測定 6 件）:

| 項目 | before → after | 件数 |
|---|---|---|
| border-top-left-radius | 4px → 6px | 6/6 |
| border-top-right-radius | 4px → 6px | 6/6 |
| border-bottom-right-radius | 4px → 6px | 6/6 |
| border-bottom-left-radius | 4px → 6px | 6/6 |

focus（差のある 6 / 測定 6 件）:

| 項目 | before → after | 件数 |
|---|---|---|
| border-top-left-radius | 4px → 6px | 6/6 |
| border-top-right-radius | 4px → 6px | 6/6 |
| border-bottom-right-radius | 4px → 6px | 6/6 |
| border-bottom-left-radius | 4px → 6px | 6/6 |

### 幅 375

- 代表 32 件 text div.form-group<div<form<div.comp-modal-body (pages/conditions/ConditionsPage.tsx他)
- 代表 3 件 number div.form-group<div<form<div.comp-modal-body (pages/conditions/ConditionsPage.tsx他)
- 代表 1 件 email div.form-group<div<form<div.comp-modal-body (pages/super-admin/SupplierMasterPage.tsx他)
- 代表 49 件 text div.form-group<div<form<div.comp-drawer-body (pages/super-admin/components/ConditionDefsMasterPanel.tsx他)
- 代表 13 件 number div.form-group<div<form<div.comp-drawer-body (pages/super-admin/components/ConditionDefsMasterPanel.tsx他)
- 代表 1 件 email div.form-group<div<form<div.comp-drawer-body (pages/super-admin/components/SupplierMasterPanel.tsx他)

normal（差のある 6 / 測定 6 件）:

| 項目 | before → after | 件数 |
|---|---|---|
| border-top-left-radius | 4px → 6px | 6/6 |
| border-top-right-radius | 4px → 6px | 6/6 |
| border-bottom-right-radius | 4px → 6px | 6/6 |
| border-bottom-left-radius | 4px → 6px | 6/6 |

focus（差のある 6 / 測定 6 件）:

| 項目 | before → after | 件数 |
|---|---|---|
| border-top-left-radius | 4px → 6px | 6/6 |
| border-top-right-radius | 4px → 6px | 6/6 |
| border-bottom-right-radius | 4px → 6px | 6/6 |
| border-bottom-left-radius | 4px → 6px | 6/6 |

## 4. 非テキスト input（規則が当たるもの 19 件。要素は変えず規則だけ外す）

### 幅 1280

| 場所 | type | 当たり方 | normal の差（項目数: 主な前→後） | 規則がなくなった素の値と一致 |
|---|---|---|---|---|
| components/DataTable.tsx:174 | checkbox | unconfirmed-only(ancestor not resolved) | 差0 | はい |
| components/DataTable.tsx:262 | checkbox | unconfirmed-only(ancestor not resolved) | 差0 | はい |
| components/PriorityScoreOverride.tsx:81 | range | definite | 28項目: width 1200px→129px; padding-top 8px→0px; border-top-width 1px→0px; border-top-style solid→none; border-top-left-radius 4px→0px; font-size 14.4px→13.3333px; height 34px→16px; color rgb(26, 32, 44)→rgb(16, 16, 16) | はい |
| features/supplier-master/SupplierDetailDrawer.tsx:413 | checkbox | unconfirmed-only(ancestor not resolved) | 差0 | はい |
| features/tcg-distribution/DistributionTargetForm.tsx:238 | checkbox | unconfirmed-only(ancestor not resolved) | 差0 | いいえ(祖先の他規則あり) |
| pages/contacts/ContactEditPage.tsx:170 | checkbox | definite | 11項目: width 1280px→13px; font-size 14.4px→13.3333px; background-color rgb(255, 255, 255)→rgba(0, 0, 0, 0); color rgb(26, 32, 44)→rgb(0, 0, 0) | はい |
| pages/integrations/FedexEtdSetupGuide.tsx:509 | file | definite | 26項目: width 592px→253px; padding-top 8px→0px; border-top-width 1px→0px; border-top-style solid→none; border-top-left-radius 4px→0px; font-size 14.4px→13.3333px; background-color rgb(255, 255, 255)→rgba(0, 0, 0, 0); height 40px→21px | はい |
| pages/integrations/FedexEtdSetupGuide.tsx:538 | file | definite | 26項目: width 592px→253px; padding-top 8px→0px; border-top-width 1px→0px; border-top-style solid→none; border-top-left-radius 4px→0px; font-size 14.4px→13.3333px; background-color rgb(255, 255, 255)→rgba(0, 0, 0, 0); height 40px→21px | はい |
| pages/integrations/FedexLabelValidationTab.tsx:288 | checkbox | unconfirmed-only(ancestor not resolved) | 差0 | いいえ(祖先の他規則あり) |
| pages/integrations/FedexLabelValidationTab.tsx:302 | checkbox | unconfirmed-only(ancestor not resolved) | 差0 | いいえ(祖先の他規則あり) |
| pages/integrations/FedexLabelValidationTab.tsx:316 | checkbox | unconfirmed-only(ancestor not resolved) | 差0 | いいえ(祖先の他規則あり) |
| pages/roles/RolesPage.tsx:505 | radio | definite | 9項目: font-size 14.4px→13.3333px; background-color rgb(255, 255, 255)→rgba(0, 0, 0, 0); color rgb(26, 32, 44)→rgb(0, 0, 0) | いいえ(祖先の他規則あり) |
| pages/roles/RolesPage.tsx:521 | radio | definite | 9項目: font-size 14.4px→13.3333px; background-color rgb(255, 255, 255)→rgba(0, 0, 0, 0); color rgb(26, 32, 44)→rgb(0, 0, 0) | いいえ(祖先の他規則あり) |
| pages/roles/RolesPage.tsx:561 | checkbox | definite | 11項目: width 1200px→13px; font-size 14.4px→13.3333px; background-color rgb(255, 255, 255)→rgba(0, 0, 0, 0); color rgb(26, 32, 44)→rgb(0, 0, 0) | はい |
| pages/staff/StaffEditPage.tsx:219 | checkbox | definite | 11項目: width 1280px→13px; font-size 14.4px→13.3333px; background-color rgb(255, 255, 255)→rgba(0, 0, 0, 0); color rgb(26, 32, 44)→rgb(0, 0, 0) | はい |
| pages/staff/StaffPage.tsx:292 | checkbox | definite | 11項目: width 1200px→13px; font-size 14.4px→13.3333px; background-color rgb(255, 255, 255)→rgba(0, 0, 0, 0); color rgb(26, 32, 44)→rgb(0, 0, 0) | はい |
| pages/super-admin/LLMBudgetTab.tsx:202 | checkbox | unconfirmed-only(ancestor not resolved) | 差0 | はい |
| pages/super-admin/LLMBudgetTab.tsx:215 | checkbox | unconfirmed-only(ancestor not resolved) | 差0 | はい |
| pages/super-admin/components/StatusMasterPanel.tsx:352 | checkbox | unconfirmed-only(ancestor not resolved) | 差0 | はい |

### 幅 375

| 場所 | type | 当たり方 | normal の差（項目数: 主な前→後） | 規則がなくなった素の値と一致 |
|---|---|---|---|---|
| components/DataTable.tsx:174 | checkbox | unconfirmed-only(ancestor not resolved) | 差0 | はい |
| components/DataTable.tsx:262 | checkbox | unconfirmed-only(ancestor not resolved) | 差0 | はい |
| components/PriorityScoreOverride.tsx:81 | range | definite | 28項目: width 327px→129px; padding-top 8px→0px; border-top-width 1px→0px; border-top-style solid→none; border-top-left-radius 4px→0px; font-size 14.4px→13.3333px; height 34px→16px; color rgb(26, 32, 44)→rgb(16, 16, 16) | はい |
| features/supplier-master/SupplierDetailDrawer.tsx:413 | checkbox | unconfirmed-only(ancestor not resolved) | 差0 | はい |
| features/tcg-distribution/DistributionTargetForm.tsx:238 | checkbox | unconfirmed-only(ancestor not resolved) | 差0 | いいえ(祖先の他規則あり) |
| pages/contacts/ContactEditPage.tsx:170 | checkbox | definite | 11項目: width 375px→13px; font-size 14.4px→13.3333px; background-color rgb(255, 255, 255)→rgba(0, 0, 0, 0); color rgb(26, 32, 44)→rgb(0, 0, 0) | はい |
| pages/integrations/FedexEtdSetupGuide.tsx:509 | file | definite | 26項目: width 139.5px→253px; padding-top 8px→0px; border-top-width 1px→0px; border-top-style solid→none; border-top-left-radius 4px→0px; font-size 14.4px→13.3333px; background-color rgb(255, 255, 255)→rgba(0, 0, 0, 0); height 40px→21px | はい |
| pages/integrations/FedexEtdSetupGuide.tsx:538 | file | definite | 26項目: width 139.5px→253px; padding-top 8px→0px; border-top-width 1px→0px; border-top-style solid→none; border-top-left-radius 4px→0px; font-size 14.4px→13.3333px; background-color rgb(255, 255, 255)→rgba(0, 0, 0, 0); height 40px→21px | はい |
| pages/integrations/FedexLabelValidationTab.tsx:288 | checkbox | unconfirmed-only(ancestor not resolved) | 差0 | いいえ(祖先の他規則あり) |
| pages/integrations/FedexLabelValidationTab.tsx:302 | checkbox | unconfirmed-only(ancestor not resolved) | 差0 | いいえ(祖先の他規則あり) |
| pages/integrations/FedexLabelValidationTab.tsx:316 | checkbox | unconfirmed-only(ancestor not resolved) | 差0 | いいえ(祖先の他規則あり) |
| pages/roles/RolesPage.tsx:505 | radio | definite | 9項目: font-size 14.4px→13.3333px; background-color rgb(255, 255, 255)→rgba(0, 0, 0, 0); color rgb(26, 32, 44)→rgb(0, 0, 0) | いいえ(祖先の他規則あり) |
| pages/roles/RolesPage.tsx:521 | radio | definite | 9項目: font-size 14.4px→13.3333px; background-color rgb(255, 255, 255)→rgba(0, 0, 0, 0); color rgb(26, 32, 44)→rgb(0, 0, 0) | いいえ(祖先の他規則あり) |
| pages/roles/RolesPage.tsx:561 | checkbox | definite | 11項目: width 327px→13px; font-size 14.4px→13.3333px; background-color rgb(255, 255, 255)→rgba(0, 0, 0, 0); color rgb(26, 32, 44)→rgb(0, 0, 0) | はい |
| pages/staff/StaffEditPage.tsx:219 | checkbox | definite | 11項目: width 375px→13px; font-size 14.4px→13.3333px; background-color rgb(255, 255, 255)→rgba(0, 0, 0, 0); color rgb(26, 32, 44)→rgb(0, 0, 0) | はい |
| pages/staff/StaffPage.tsx:292 | checkbox | definite | 11項目: width 327px→13px; font-size 14.4px→13.3333px; background-color rgb(255, 255, 255)→rgba(0, 0, 0, 0); color rgb(26, 32, 44)→rgb(0, 0, 0) | はい |
| pages/super-admin/LLMBudgetTab.tsx:202 | checkbox | unconfirmed-only(ancestor not resolved) | 差0 | はい |
| pages/super-admin/LLMBudgetTab.tsx:215 | checkbox | unconfirmed-only(ancestor not resolved) | 差0 | はい |
| pages/super-admin/components/StatusMasterPanel.tsx:352 | checkbox | unconfirmed-only(ancestor not resolved) | 差0 | はい |

注: 「差0」は、この静的な祖先連鎖の中に `.form-group` が無く規則が当たらなかった要素（祖先未確定のみで拾われたもの）。確定で当たる 9 件は上表のとおり変わる（checkbox の width:100% が 13px になる等）。

## 5. ログイン G11（3 件）

### 5-1. 現在 → 標準（TextFieldControl size=md）: §1 の G11 の表

幅 1280:

normal（差のある 3 / 測定 3 件）:

| 項目 | before → after | 件数 |
|---|---|---|
| padding-top | 12px → 8px | 3/3 |
| padding-right | 16px → 12px | 3/3 |
| padding-bottom | 12px → 8px | 3/3 |
| padding-left | 16px → 12px | 3/3 |
| font-size | 16px → 14.4px | 3/3 |
| font-family | Arial → システムフォント列(-apple-system,…) | 3/3 |
| line-height | normal → 21.6px | 3/3 |
| height | 44px → 39.6094px | 3/3 |
| transition-property | all → border-color, box-shadow | 3/3 |
| transition-duration | 0s → 0.1s, 0.1s | 3/3 |
| offsetHeight | 44 → 40 | 3/3 |

focus（差のある 3 / 測定 3 件）:

| 項目 | before → after | 件数 |
|---|---|---|
| padding-top | 12px → 8px | 3/3 |
| padding-right | 16px → 12px | 3/3 |
| padding-bottom | 12px → 8px | 3/3 |
| padding-left | 16px → 12px | 3/3 |
| font-size | 16px → 14.4px | 3/3 |
| font-family | Arial → システムフォント列(-apple-system,…) | 3/3 |
| line-height | normal → 21.6px | 3/3 |
| height | 44px → 39.6094px | 3/3 |
| transition-property | all → border-color, box-shadow | 3/3 |
| transition-duration | 0s → 0.1s, 0.1s | 3/3 |
| offsetHeight | 44 → 40 | 3/3 |

幅 375:

normal（差のある 3 / 測定 3 件）:

| 項目 | before → after | 件数 |
|---|---|---|
| padding-top | 12px → 8px | 3/3 |
| padding-right | 16px → 12px | 3/3 |
| padding-bottom | 12px → 8px | 3/3 |
| padding-left | 16px → 12px | 3/3 |
| font-size | 16px → 14.4px | 3/3 |
| font-family | Arial → システムフォント列(-apple-system,…) | 3/3 |
| line-height | normal → 21.6px | 3/3 |
| min-height | 0px → 44px | 3/3 |
| transition-property | all → border-color, box-shadow | 3/3 |
| transition-duration | 0s → 0.1s, 0.1s | 3/3 |

focus（差のある 3 / 測定 3 件）:

| 項目 | before → after | 件数 |
|---|---|---|
| padding-top | 12px → 8px | 3/3 |
| padding-right | 16px → 12px | 3/3 |
| padding-bottom | 12px → 8px | 3/3 |
| padding-left | 16px → 12px | 3/3 |
| font-size | 16px → 14.4px | 3/3 |
| font-family | Arial → システムフォント列(-apple-system,…) | 3/3 |
| line-height | normal → 21.6px | 3/3 |
| min-height | 0px → 44px | 3/3 |
| transition-property | all → border-color, box-shadow | 3/3 |
| transition-duration | 0s → 0.1s, 0.1s | 3/3 |

### 5-2. 種類(variant)として現在の見た目を保つ場合に必要な宣言

旧 2 規則（components.css:19 → pages-layout.css:246 の後勝ち合成）が決めている宣言:

- 基本: `width:100%; padding:var(--space-2) var(--space-3); border:1px solid var(--border); border-radius:var(--radius-sm); font-size:var(--font-base); color:var(--text-primary); background:var(--bg-surface); box-sizing:border-box` を `background:var(--bg-surface); color:var(--text-primary); border:1px solid var(--border); border-radius:var(--radius-md); padding:var(--space-3) var(--space-4); font-size:var(--font-md)` が上書き
- focus: `outline:none; border-color:var(--accent); box-shadow:var(--focus-ring-shadow)`（login 側も同値）

#### lg (size=lg 標準)

class: `comp-field__input comp-field__input--lg`

幅 1280（vs 現在, 3 件）: 

normal（差のある 3 / 測定 3 件）:

| 項目 | before → after | 件数 |
|---|---|---|
| font-family | Arial → システムフォント列(-apple-system,…) | 3/3 |
| line-height | normal → 24px | 3/3 |
| height | 44px → 50px | 3/3 |
| min-height | 0px → 44px | 3/3 |
| transition-property | all → border-color, box-shadow | 3/3 |
| transition-duration | 0s → 0.1s, 0.1s | 3/3 |
| offsetHeight | 44 → 50 | 3/3 |

focus（差のある 3 / 測定 3 件）:

| 項目 | before → after | 件数 |
|---|---|---|
| font-family | Arial → システムフォント列(-apple-system,…) | 3/3 |
| line-height | normal → 24px | 3/3 |
| height | 44px → 50px | 3/3 |
| min-height | 0px → 44px | 3/3 |
| transition-property | all → border-color, box-shadow | 3/3 |
| transition-duration | 0s → 0.1s, 0.1s | 3/3 |
| offsetHeight | 44 → 50 | 3/3 |

幅 375（vs 現在, 3 件）: 

normal（差のある 3 / 測定 3 件）:

| 項目 | before → after | 件数 |
|---|---|---|
| font-family | Arial → システムフォント列(-apple-system,…) | 3/3 |
| line-height | normal → 24px | 3/3 |
| height | 44px → 50px | 3/3 |
| min-height | 0px → 44px | 3/3 |
| transition-property | all → border-color, box-shadow | 3/3 |
| transition-duration | 0s → 0.1s, 0.1s | 3/3 |
| offsetHeight | 44 → 50 | 3/3 |

focus（差のある 3 / 測定 3 件）:

| 項目 | before → after | 件数 |
|---|---|---|
| font-family | Arial → システムフォント列(-apple-system,…) | 3/3 |
| line-height | normal → 24px | 3/3 |
| height | 44px → 50px | 3/3 |
| min-height | 0px → 44px | 3/3 |
| transition-property | all → border-color, box-shadow | 3/3 |
| transition-duration | 0s → 0.1s, 0.1s | 3/3 |
| offsetHeight | 44 → 50 | 3/3 |

#### variant候補A 旧2規則の宣言をそのまま写す

class: `comp-field__input comp-input--login`

```css
.comp-field__input.comp-input--login { width: 100%; padding: var(--space-3) var(--space-4); border: 1px solid var(--border); border-radius: var(--radius-md); font-size: var(--font-md); color: var(--text-primary); background: var(--bg-surface); box-sizing: border-box; }
.comp-field__input.comp-input--login:focus { outline: none; border-color: var(--accent); box-shadow: var(--focus-ring-shadow); }
```

幅 1280（vs 現在, 3 件）: 

normal（差のある 3 / 測定 3 件）:

| 項目 | before → after | 件数 |
|---|---|---|
| font-family | Arial → システムフォント列(-apple-system,…) | 3/3 |
| line-height | normal → 24px | 3/3 |
| height | 44px → 50px | 3/3 |
| transition-property | all → border-color, box-shadow | 3/3 |
| transition-duration | 0s → 0.1s, 0.1s | 3/3 |
| offsetHeight | 44 → 50 | 3/3 |

focus（差のある 3 / 測定 3 件）:

| 項目 | before → after | 件数 |
|---|---|---|
| font-family | Arial → システムフォント列(-apple-system,…) | 3/3 |
| line-height | normal → 24px | 3/3 |
| height | 44px → 50px | 3/3 |
| transition-property | all → border-color, box-shadow | 3/3 |
| transition-duration | 0s → 0.1s, 0.1s | 3/3 |
| offsetHeight | 44 → 50 | 3/3 |

幅 375（vs 現在, 3 件）: 

normal（差のある 3 / 測定 3 件）:

| 項目 | before → after | 件数 |
|---|---|---|
| font-family | Arial → システムフォント列(-apple-system,…) | 3/3 |
| line-height | normal → 24px | 3/3 |
| height | 44px → 50px | 3/3 |
| min-height | 0px → 44px | 3/3 |
| transition-property | all → border-color, box-shadow | 3/3 |
| transition-duration | 0s → 0.1s, 0.1s | 3/3 |
| offsetHeight | 44 → 50 | 3/3 |

focus（差のある 3 / 測定 3 件）:

| 項目 | before → after | 件数 |
|---|---|---|
| font-family | Arial → システムフォント列(-apple-system,…) | 3/3 |
| line-height | normal → 24px | 3/3 |
| height | 44px → 50px | 3/3 |
| min-height | 0px → 44px | 3/3 |
| transition-property | all → border-color, box-shadow | 3/3 |
| transition-duration | 0s → 0.1s, 0.1s | 3/3 |
| offsetHeight | 44 → 50 | 3/3 |

#### variant候補B A + font-family(revert)/line-height/transition/min-height を現行値へ戻す

class: `comp-field__input comp-input--login`

```css
.comp-field__input.comp-input--login { width: 100%; padding: var(--space-3) var(--space-4); border: 1px solid var(--border); border-radius: var(--radius-md); font-size: var(--font-md); color: var(--text-primary); background: var(--bg-surface); box-sizing: border-box; font-family: revert; line-height: normal; transition: all 0s; min-height: 0; }
.comp-field__input.comp-input--login:focus { outline: none; border-color: var(--accent); box-shadow: var(--focus-ring-shadow); }
```

幅 1280（vs 現在, 3 件）: 差分 0

幅 375（vs 現在, 3 件）: 差分 0

## 6. 非テキスト input を現状のまま保つ案（`.form-group input` を type 限定に絞る）

方法: ay2b-nontext-keep.cjs。before = 現行 CSS。after = components.css:19/30 の selector だけを下記に絞り（宣言と位置は不変）、pages-layout.css:246/255（login 規則）は撤去。要素・class・inline style・type は一切変えない。幅 1280/375、normal・focus（disabled 属性のある要素は disabled も）、43 プロパティ + offsetHeight/Width。

絞った規則（postcss が書き換えた結果。宣言は元の `.form-group input` / `:focus` と同一）:

```css
/* components.css:19 旧 .form-group input */
.form-group input[type="checkbox"],
.form-group input[type="radio"],
.form-group input[type="range"],
.form-group input[type="file"] {
  width: 100%;
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-size: var(--font-base);
  color: var(--text-primary);
  background: var(--bg-surface);
  box-sizing: border-box;
}

/* components.css:30 旧 .form-group input:focus */
.form-group input[type="checkbox"]:focus,
.form-group input[type="radio"]:focus,
.form-group input[type="range"]:focus,
.form-group input[type="file"]:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: var(--focus-ring-shadow);
}

```

宣言の中身は取り除く案と同じ（§1 表の規則 1・2）。type を足すので特異度は (0,1,1) → (0,2,1)（`:focus` は (0,2,1) → (0,3,1)）に上がる。型セレクタなしだった旧規則が当たっていた type のうち、確定で当たっていたのは checkbox・radio・range・file の 4 種（color・hidden・submit 等は `.form-group` 配下に無いため含めていない。これは TSX の静的 type 属性による。`dynamic` type は §1 で text/url/email の 2 件のみ）。

結果:

| 区分 | 測定数 | 差のあった数 |
|---|---|---|
| 確定で当たる 9 要素 | 58 測定（要素×祖先連鎖×幅2） | 0 |
| 祖先未確定だった 10 要素（§ ay2b-unresolved-trace.md で `.form-group` 祖先無しと確定） | 44 測定（要素×祖先連鎖×幅2） | 0 |

差分 0: 全 102 測定で normal・focus（disabled 属性があるものは disabled も）とも差なし。

確定 9 の内訳: components/PriorityScoreOverride.tsx:81[range], pages/contacts/ContactEditPage.tsx:170[checkbox], pages/integrations/FedexEtdSetupGuide.tsx:509[file], pages/integrations/FedexEtdSetupGuide.tsx:538[file], pages/roles/RolesPage.tsx:505[radio], pages/roles/RolesPage.tsx:521[radio], pages/roles/RolesPage.tsx:561[checkbox], pages/staff/StaffEditPage.tsx:219[checkbox], pages/staff/StaffPage.tsx:292[checkbox]。確定のうち祖先連鎖に `.form-group` を持つ測定: 58/58。
