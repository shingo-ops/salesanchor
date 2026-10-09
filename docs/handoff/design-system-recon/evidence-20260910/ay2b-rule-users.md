# ay2b-rule-users

base HEAD fb036a2388c2（origin/main = AY-2a #4067 merge fb036a238 を含む、worktree release-frontend-textfield-ay2b）。
手法: ay2-applied.cjs / ay2-css.cjs（postcss + JSX 祖先連鎖の静的解決）を全ページ側 <input> 415 件（type 不問、TextField.tsx 内の 1 件を除く）に適用。ay2b-members.cjs で取り除く 4 規則に当たる要素を抽出。既存 <TextField>/<TextFieldControl> 利用は ay2b-mold-users.cjs（同じ祖先連鎖）。

## 1. 取り除く規則

| 規則 | 宣言 |
|---|---|
| components.css:19 `.form-group input` | width:100%; padding:var(--space-2) var(--space-3); border:1px solid var(--border); border-radius:var(--radius-sm); font-size:var(--font-base); color:var(--text-primary); background:var(--bg-surface); box-sizing:border-box |
| components.css:30 `.form-group input:focus` | outline:none; border-color:var(--accent); box-shadow:var(--focus-ring-shadow) |
| pages-layout.css:246 `.login-card .form-group input` | background:var(--bg-surface); color:var(--text-primary); border:1px solid var(--border); border-radius:var(--radius-md); padding:var(--space-3) var(--space-4); font-size:var(--font-md) |
| pages-layout.css:255 `.login-card .form-group input:focus` | outline:none; border-color:var(--accent); box-shadow:var(--focus-ring-shadow) |

型セレクタなし（`input` 要素全般、type 不問）。いずれも単独セレクタの規則で、共有リストからの切り出しは不要（規則ごと削除できる）。

## 2. 件数（静的解決）

| 区分 | 確定（祖先まで一致が確定） | 祖先未確定のみ | 計 |
|---|---|---|---|
| 移管対象（text 系） | 143 | 18 | 161 |
| 商品編集 G06（保留） | 14 | 0 | 14 |
| 非テキスト type（checkbox/radio/file/range 等） | 9 | 10 | 19 |
| 既存 TextField/TextFieldControl（`.form-group` 配下、DOM 上の input が規則に当たる） | 99（利用 253 件中、`.login-card` 配下は 0） | 0 | 99 |

確定の対象 143 の内訳: G01 `.form-group input` 136（type: text:20 number:23 date:3 dynamic:2 tel:1 omitted:67 password:5 email:12 url:1 time:2）、G11 ログイン 3（email:2 password:1）、G28–G31 `.form-group input` + inline style 4（text:1 omitted:1 number:2）。
前回（base 08f59418c）の G01 136 + G11 3 + G28–G31 4 = 143、G06 14 と file×type 単位で全件一致（差分0）。AY-2a は G04/G38/G39/G32/G08/G15 を動かしただけで、この 4 規則の利用者は変わっていない。

祖先未確定とは、入力の属するコンポーネントの使用箇所が遅延ルート/タブ等で静的に辿れず、外側に `.form-group` があるか決められないもの。自ファイルに `form-group` の記述が無い（MasterListEditor, DexTab, TcgSeriesTab, LLMBudgetTab 等）ので、外側にあるとしても親コンポーネント側。【未確認】[?]（実 DOM での確認が必要）。
`.login-card` が TSX で使われるのは frontend/src/pages/login/LoginPage.tsx:77 の 1 箇所のみ（grep 結果）。他ファイルの「`.login-card .form-group input` 祖先未確定」は実際には当たらない。

## 3. 区分ごとに規則を取り除くとどうなるか

### 3-1. 移管対象 text 系（確定 143）
TextFieldControl 標準へ替える前提で、規則を外すだけでは ブラウザ既定（余白0・枠なし・13.33px）に戻る。標準へ替えたときの前後は ay2b-visual.md §1（1280/375）。

### 3-2. 商品編集 G06（14）
規則だけ外すと既定に戻り大きく崩れる（余白・枠線以外の宣言・focus リング消失、ay2b-visual.md §2）。company-forms.css:238 の独立規則（border のみ）に宣言を足せば差分0（§2）。

### 3-3. 非テキスト（確定 9・未確定のみ 10）
`.form-group input` は type を見ないので、確定の 9 件（checkbox/radio/file/range）にも width:100%・padding・border・background が当たっている。規則を外すと ブラウザ既定に戻る（実測 ay2b-visual.md §4）。

### 3-4. 既存 TextField 利用（99）
`.form-group input`（特異度 (0,1,1)）が `.comp-field__input`（(0,1,0)）に勝っているため、金型の見た目になっていない。規則を外すと金型標準に戻る（実測差: 角丸 4px→6px のみ、ay2b-visual.md §3）。

## 4. 一覧

### 4-1. 商品編集 G06（保留、14）
- pages/products/ProductEditPage.tsx:215 [omitted]
- pages/products/ProductEditPage.tsx:224 [omitted]
- pages/products/ProductEditPage.tsx:251 [omitted]
- pages/products/ProductEditPage.tsx:262 [date]
- pages/products/ProductEditPage.tsx:270 [omitted]
- pages/products/ProductEditPage.tsx:274 [omitted]
- pages/products/ProductEditPage.tsx:294 [number]
- pages/products/ProductEditPage.tsx:298 [url]
- pages/products/ProductEditPage.tsx:317 [number]
- pages/products/ProductEditPage.tsx:321 [number]
- pages/products/ProductEditPage.tsx:325 [number]
- pages/products/ProductEditPage.tsx:329 [number]
- pages/products/ProductEditPage.tsx:333 [number]
- pages/products/ProductEditPage.tsx:337 [number]

### 4-2. 非テキスト（確定）
- components/PriorityScoreOverride.tsx:81 [range] components.css:19 .form-group input / components.css:30 .form-group input:focus
- pages/contacts/ContactEditPage.tsx:170 [checkbox] components.css:19 .form-group input / components.css:30 .form-group input:focus
- pages/integrations/FedexEtdSetupGuide.tsx:509 [file] components.css:19 .form-group input / components.css:30 .form-group input:focus
- pages/integrations/FedexEtdSetupGuide.tsx:538 [file] components.css:19 .form-group input / components.css:30 .form-group input:focus
- pages/roles/RolesPage.tsx:505 [radio] components.css:19 .form-group input / components.css:30 .form-group input:focus
- pages/roles/RolesPage.tsx:521 [radio] components.css:19 .form-group input / components.css:30 .form-group input:focus
- pages/roles/RolesPage.tsx:561 [checkbox] components.css:19 .form-group input / components.css:30 .form-group input:focus
- pages/staff/StaffEditPage.tsx:219 [checkbox] components.css:19 .form-group input / components.css:30 .form-group input:focus
- pages/staff/StaffPage.tsx:292 [checkbox] components.css:19 .form-group input / components.css:30 .form-group input:focus

### 4-3. 非テキスト（祖先未確定のみ）
- components/DataTable.tsx:174 [checkbox] components.css:19 .form-group input / components.css:30 .form-group input:focus
- components/DataTable.tsx:262 [checkbox] components.css:19 .form-group input / components.css:30 .form-group input:focus / pages-layout.css:246 .login-card .form-group input / pages-layout.css:255 .login-card .form-group input:focus
- features/supplier-master/SupplierDetailDrawer.tsx:413 [checkbox] components.css:19 .form-group input / components.css:30 .form-group input:focus
- features/tcg-distribution/DistributionTargetForm.tsx:238 [checkbox] components.css:19 .form-group input / components.css:30 .form-group input:focus
- pages/integrations/FedexLabelValidationTab.tsx:288 [checkbox] components.css:19 .form-group input / components.css:30 .form-group input:focus
- pages/integrations/FedexLabelValidationTab.tsx:302 [checkbox] components.css:19 .form-group input / components.css:30 .form-group input:focus
- pages/integrations/FedexLabelValidationTab.tsx:316 [checkbox] components.css:19 .form-group input / components.css:30 .form-group input:focus
- pages/super-admin/LLMBudgetTab.tsx:202 [checkbox] components.css:19 .form-group input / components.css:30 .form-group input:focus
- pages/super-admin/LLMBudgetTab.tsx:215 [checkbox] components.css:19 .form-group input / components.css:30 .form-group input:focus
- pages/super-admin/components/StatusMasterPanel.tsx:352 [checkbox] components.css:19 .form-group input / components.css:30 .form-group input:focus

### 4-4. 移管対象（祖先未確定のみ、18）
- components/master-list-editor/MasterListEditor.tsx:135 [text] components.css:19 .form-group input / components.css:30 .form-group input:focus
- components/master-list-editor/MasterListEditor.tsx:157 [omitted] components.css:19 .form-group input / components.css:30 .form-group input:focus
- components/master-list-editor/MasterListEditor.tsx:164 [omitted] components.css:19 .form-group input / components.css:30 .form-group input:focus
- features/tcg-analysis-review/ProductMasterDrawer.tsx:68 [omitted] components.css:19 .form-group input / components.css:30 .form-group input:focus
- features/tcg-distribution/DistributionTargetForm.tsx:182 [text] components.css:19 .form-group input / components.css:30 .form-group input:focus
- features/tcg-distribution/DistributionTargetForm.tsx:199 [text] components.css:19 .form-group input / components.css:30 .form-group input:focus
- features/tcg-distribution/DistributionTargetForm.tsx:223 [text] components.css:19 .form-group input / components.css:30 .form-group input:focus
- pages/super-admin/DexTab.tsx:200 [omitted] components.css:19 .form-group input / components.css:30 .form-group input:focus
- pages/super-admin/DexTab.tsx:298 [omitted] components.css:19 .form-group input / components.css:30 .form-group input:focus
- pages/super-admin/DexTab.tsx:303 [omitted] components.css:19 .form-group input / components.css:30 .form-group input:focus
- pages/super-admin/DexTab.tsx:309 [omitted] components.css:19 .form-group input / components.css:30 .form-group input:focus
- pages/super-admin/DexTab.tsx:315 [omitted] components.css:19 .form-group input / components.css:30 .form-group input:focus
- pages/super-admin/LLMBudgetTab.tsx:187 [number] components.css:19 .form-group input / components.css:30 .form-group input:focus
- pages/super-admin/TcgSeriesTab.tsx:230 [omitted] components.css:19 .form-group input / components.css:30 .form-group input:focus
- pages/super-admin/TcgSeriesTab.tsx:238 [omitted] components.css:19 .form-group input / components.css:30 .form-group input:focus
- pages/super-admin/TcgSeriesTab.tsx:311 [omitted] components.css:19 .form-group input / components.css:30 .form-group input:focus
- pages/super-admin/TcgSeriesTab.tsx:317 [omitted] components.css:19 .form-group input / components.css:30 .form-group input:focus
- pages/super-admin/TcgSeriesTab.tsx:323 [omitted] components.css:19 .form-group input / components.css:30 .form-group input:focus

### 4-5. 移管対象（確定）のファイル別件数
- pages/staff/StaffEditPage.tsx: 9（omitted:8 email:1）
- pages/staff/StaffPage.tsx: 8（omitted:7 email:1）
- components/ShippingDetailPanel.tsx: 7（dynamic:1 text:3 number:2 date:1）
- pages/account-settings/ProfileSection.tsx: 7（tel:1 omitted:6）
- pages/contacts/ContactEditPage.tsx: 7（omitted:6 email:1）
- pages/leads/LeadsPage.tsx: 7（omitted:4 email:1 number:2）
- pages/admin/TenantProfilePage.tsx: 6（text:5 email:1）
- components/PurchaseDetailPanel.tsx: 5（text:2 date:1 dynamic:1 number:1）
- pages/admin/TenantPolicyPage.tsx: 5（number:3 text:2）
- pages/leads/LeadEditPage.tsx: 5（omitted:3 email:1 number:1）
- pages/badges/BadgesPage.tsx: 4（omitted:3 number:1）
- pages/bots/BotsPage.tsx: 4（omitted:3 email:1）
- pages/contacts/ContactFormFields.tsx: 4（omitted:3 email:1）
- pages/shifts/ShiftsPage.tsx: 4（number:1 date:1 time:2）
- pages/staff/StaffFormFields.tsx: 4（omitted:3 email:1）
- pages/super-admin/KnowledgeAliasesTab.tsx: 4（omitted:3 number:1）
- pages/suppliers/SupplierFormFields.tsx: 4（omitted:3 email:1）
- pages/account-settings/SecuritySection.tsx: 3（password:3）
- pages/bots/BotFormFields.tsx: 3（omitted:2 email:1）
- pages/companies/CompanyFormFields.tsx: 3（omitted:3）
- pages/integrations/CarrierCredentialForm.tsx: 3（text:2 password:1）
- pages/integrations/FedexLabelValidationTab.tsx: 3（text:3）
- pages/invoice-create/InvoiceCreatePage.tsx: 3（omitted:1 number:2）
- pages/leads/LeadFormFields.tsx: 3（omitted:2 email:1）
- pages/login/LoginPage.tsx: 3（email:2 password:1）
- pages/purchase-orders/PurchaseOrdersFormModal.tsx: 3（omitted:1 number:2）
- pages/quote-create/QuoteCreatePage.tsx: 3（omitted:1 number:2）
- pages/buddy/BuddyPage.tsx: 2（number:2）
- pages/integrations/PaypalIntegrationPage.tsx: 2（text:1 password:1）
- pages/notifications/NotificationsPage.tsx: 2（omitted:2）
- pages/orders/OrdersFormModal.tsx: 2（omitted:1 number:1）
- pages/roles/RolesPage.tsx: 2（omitted:1 number:1）
- pages/teams/TeamFormFields.tsx: 2（omitted:1 number:1）
- components/ChannelTypeCombobox.tsx: 1（text:1）
- components/CountryCombobox.tsx: 1（text:1）
- components/InventoryPicker.tsx: 1（text:1）
- components/OrderFinancialPanel.tsx: 1（number:1）
- pages/integrations/GoogleDriveIntegrationPage.tsx: 1（url:1）
- pages/staff-reports/StaffReportsPage.tsx: 1（omitted:1）
- pages/teams/TeamsPage.tsx: 1（number:1）

### 4-6. G11 ログイン
- pages/login/LoginPage.tsx:93 [email]
- pages/login/LoginPage.tsx:104 [password]
- pages/login/LoginPage.tsx:136 [email]

### 4-7. G28–G31 inline style
- components/InventoryPicker.tsx:217 [text] style{min-width:var(--min-width-input-sm);padding:var(--space-6px) var(--space-2);width:100%}
- pages/purchase-orders/PurchaseOrdersFormModal.tsx:191 [omitted] style{min-width:var(--min-width-input-sm)}
- pages/purchase-orders/PurchaseOrdersFormModal.tsx:194 [number] style{width:var(--input-width-qty)}
- pages/purchase-orders/PurchaseOrdersFormModal.tsx:197 [number] style{width:var(--input-width-year)}

### 4-8. 既存 TextField/TextFieldControl で `.form-group` 配下（99）のファイル別件数
- pages/super-admin/components/SupplierMasterPanel.tsx: 9（TextField、行 313,321,328,335,343,350,357,364,371）
- pages/super-admin/SupplierMasterPage.tsx: 9（TextField、行 317,325,332,339,347,354,361,368,375）
- pages/note-master/NoteMasterPage.tsx: 8（TextField、行 267,275,283,299,316,323,330,337）
- pages/super-admin/components/NoteMasterPanel.tsx: 8（TextField、行 255,263,271,287,304,311,318,325）
- pages/status-master/StatusMasterPage.tsx: 6（TextField、行 229,237,245,252,285,294）
- pages/super-admin/components/StatusMasterPanel.tsx: 6（TextField、行 280,288,296,303,336,345）
- pages/super-admin/components/WeightClassesMasterPanel.tsx: 6（TextField、行 207,215,223,230,238,246）
- pages/units/UnitsPage.tsx: 6（TextField、行 276,284,292,328,336,344）
- pages/super-admin/components/QuantityUnitsMasterPanel.tsx: 5（TextField、行 203,211,219,226,234）
- pages/conditions/ConditionsPage.tsx: 4（TextField、行 307,315,323,330）
- pages/super-admin/components/ConditionDefsMasterPanel.tsx: 4（TextField、行 196,204,212,219）
- pages/super-admin/components/ProductFormatsMasterPanel.tsx: 4（TextField、行 253,261,269,304）
- pages/super-admin/components/ProductKindsMasterPanel.tsx: 4（TextField、行 193,201,209,216）
- pages/super-admin/components/ProductLinesMasterPanel.tsx: 4（TextField、行 252,260,268,303）
- pages/super-admin/components/TypeMasterPanel.tsx: 4（TextField、行 227,235,243,261）
- pages/product-categories/ProductCategoriesPage.tsx: 3（TextField、行 201,209,217）
- pages/super-admin/components/ConditionsMasterPanel.tsx: 3（TextField、行 419,428,438）
- pages/super-admin/components/ProductCategoriesMasterPanel.tsx: 3（TextField、行 258,266,274）
- pages/super-admin/components/UnitMasterPanel.tsx: 3（TextField、行 309,317,325）

全メンバーの属性（className・inline style・disabled・ref・onKeyDown・ヒットした規則・他に当たる規則）は ay2b-members.json の all[]。グループ別（シグネチャ別）は targetGroups[]。
