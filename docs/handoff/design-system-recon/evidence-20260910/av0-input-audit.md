# AV-0 入力要素 再棚卸し

基準 SHA: 55d99a97e441b4c0604f2b8f42418d2a7bc8ffab / TypeScript 5.9.3

TypeScript 5.9.3 AST。対象TSX 275ファイル（stories/test 103件除外）、構文エラー0。合計 599。

## タグ別
|tag|n|
|---|---:|
|input|461|
|select|81|
|textarea|57|

## タグ/type別
|tag/type|n|
|---|---:|
|input/omitted|150|
|input/text|97|
|select/-|81|
|input/checkbox|72|
|input/number|65|
|textarea/-|57|
|input/email|23|
|input/date|11|
|input/tel|8|
|input/radio|7|
|input/file|6|
|input/password|6|
|input/time|4|
|input/dynamic|3|
|input/url|2|
|input/search|2|
|input/color|2|
|input/range|1|
|input/omitted+spread|1|
|input/datetime-local|1|

## ui-allow
|ui-allow|n|
|---|---:|
|none|578|
|ui-allow|21|

## 金型ファイル内 / ページ側
|scope:tag|n|
|---|---:|
|page:input|460|
|page:select|80|
|page:textarea|56|
|mold:select|1|
|mold:input|1|
|mold:textarea|1|

## 上位20ファイル
|file|n|
|---|---:|
|frontend/src/pages/companies/CompaniesPage.tsx|28|
|frontend/src/pages/register/RegisterPage.tsx|25|
|frontend/src/pages/products/ProductEditPage.tsx|24|
|frontend/src/pages/inbox/InboxProfileModal.tsx|21|
|frontend/src/pages/inbox/InboxKartePanel.tsx|20|
|frontend/src/pages/company-detail/CompanyBasicTab.tsx|14|
|frontend/src/pages/contacts/ContactsPage.tsx|14|
|frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx|14|
|frontend/src/pages/inventory/InventoryFilterPanel.tsx|11|
|frontend/src/pages/invoice-create/InvoiceCreatePage.tsx|11|
|frontend/src/pages/quote-create/QuoteCreatePage.tsx|11|
|frontend/src/pages/register/RegisterAddressPage.tsx|11|
|frontend/src/pages/schedule/SchedulePageImpl.tsx|11|
|frontend/src/pages/super-admin/ParseReviewPage.tsx|11|
|frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx|10|
|frontend/src/pages/register/RegisterChangeBillingPage.tsx|10|
|frontend/src/pages/staff/StaffEditPage.tsx|10|
|frontend/src/components/ShippingDetailPanel.tsx|9|
|frontend/src/pages/admin/DiscordConfigPage.tsx|9|
|frontend/src/pages/contacts/ContactEditPage.tsx|9|

## spread属性あり
- frontend/src/components/Select.tsx:53 <select> type=null spread=rest
- frontend/src/components/TextField.tsx:64 <input> type=omitted+spread spread=rest
- frontend/src/components/Textarea.tsx:63 <textarea> type=null spread=rest

## type動的
- frontend/src/components/PurchaseDetailPanel.tsx:359 dynamic:{f.key === "supplier_url" ? "url" : "text"}
- frontend/src/components/ShippingDetailPanel.tsx:399 dynamic:{f.key === "email" ? "email" : "text"}
- frontend/src/features/tcg-analysis-review/ItemComparison.tsx:26 dynamic:{kind}

## ui-allow付き
- frontend/src/features/tcg-import-review/ReviewSection.tsx:289 <input>
- frontend/src/pages/conditions/ConditionsPage.tsx:340 <textarea>
- frontend/src/pages/conditions/ConditionsPage.tsx:350 <textarea>
- frontend/src/pages/inbox/InboxMessageThread.tsx:409 <select>
- frontend/src/pages/integrations/CarrierCredentialForm.tsx:95 <input>
- frontend/src/pages/integrations/CarrierCredentialForm.tsx:121 <input>
- frontend/src/pages/inventory/InventoryPage.tsx:477 <select>
- frontend/src/pages/status-master/StatusMasterPage.tsx:260 <select>
- frontend/src/pages/status-master/StatusMasterPage.tsx:274 <select>
- frontend/src/pages/super-admin/TcgLineImportPage.tsx:325 <input>
- frontend/src/pages/super-admin/TcgLineImportPage.tsx:353 <input>
- frontend/src/pages/super-admin/TcgLineImportPage.tsx:374 <input>
- frontend/src/pages/super-admin/TcgLineImportPage.tsx:395 <input>
- frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:770 <input>
- frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:803 <input>
- frontend/src/pages/super-admin/components/ConditionsMasterPanel.tsx:322 <select>
- frontend/src/pages/super-admin/components/ConditionsMasterPanel.tsx:338 <select>
- frontend/src/pages/super-admin/components/ConditionsMasterPanel.tsx:393 <select>
- frontend/src/pages/super-admin/components/ConditionsMasterPanel.tsx:409 <select>
- frontend/src/pages/super-admin/components/StatusMasterPanel.tsx:311 <select>
- frontend/src/pages/super-admin/components/StatusMasterPanel.tsx:325 <select>

## 2026-09-10 監査との比較

旧: input-semantic-audit.json（origin/main 3bdf33d55、stories/test除外後 577件）。新: 本スキャン 599件。旧 text-default は新 omitted と対応づけ。

|tag/type|旧|新|差|
|---|---:|---:|---:|
|input/checkbox|51|72|21|
|input/color|2|2|0|
|input/date|11|11|0|
|input/datetime-local|1|1|0|
|input/dynamic|3|3|0|
|input/email|24|23|-1|
|input/file|4|6|2|
|input/number|64|65|1|
|input/omitted|162|151|-11|
|input/password|6|6|0|
|input/radio|7|7|0|
|input/range|1|1|0|
|input/search|3|2|-1|
|input/tel|8|8|0|
|input/text|97|97|0|
|input/time|4|4|0|
|input/url|2|2|0|
|select/-|74|81|7|
|textarea/-|53|57|4|

### 照合結果
照合方法: file+tag+type が一致するもの同士を、(1)属性名集合+className一致 (2)属性名集合一致 (3)なし の順に、行番号が近い順に1対1で対応づけ。
- 対応づけ成功: 556（段階別 {"1":550,"3":6}）
- 旧のみ（削除候補）: 21
- 新のみ（追加候補）: 43
- 段階3で対応づけたもの（属性が変化）: 6

### 旧のみ（削除側）ファイル別
- frontend/src/pages/staff/StaffPage.tsx  259:input/omitted
- frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx  519:textarea/- 573:input/checkbox 617:select/-
- frontend/src/pages/super-admin/ProductMastersTab.tsx  221:input/text 243:input/omitted 250:input/omitted
- frontend/src/pages/super-admin/SuppliersAdminTab.tsx  226:input/search 257:input/checkbox 290:input/omitted 293:input/omitted 296:input/omitted 299:input/email 302:input/omitted 305:input/omitted 308:input/omitted 311:input/omitted 314:input/omitted 317:input/checkbox 344:input/omitted 345:input/omitted

### 新のみ（追加側）ファイル別
- frontend/src/components/AvatarUpload.tsx  114:input/file
- frontend/src/components/master-list-editor/MasterListEditor.tsx  135:input/text 157:input/omitted 164:input/omitted
- frontend/src/features/supplier-master/SupplierDetailDrawer.tsx  413:input/checkbox
- frontend/src/pages/conditions/ConditionsPage.tsx  252:input/checkbox 340:textarea/- 350:textarea/- 358:input/checkbox
- frontend/src/pages/note-master/NoteMasterPage.tsx  308:input/checkbox
- frontend/src/pages/product-categories/ProductCategoriesPage.tsx  224:input/checkbox
- frontend/src/pages/status-master/StatusMasterPage.tsx  260:select/- 274:select/- 302:input/checkbox
- frontend/src/pages/super-admin/ExtractionPromptConfigTab.tsx  208:input/checkbox 222:textarea/-
- frontend/src/pages/super-admin/SupplierMasterPage.tsx  382:input/checkbox
- frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx  770:input/file 803:input/number
- frontend/src/pages/super-admin/components/ConditionDefsMasterPanel.tsx  227:input/checkbox
- frontend/src/pages/super-admin/components/ConditionsMasterPanel.tsx  322:select/- 338:select/- 368:textarea/- 381:textarea/- 393:select/- 409:select/- 451:input/checkbox
- frontend/src/pages/super-admin/components/NoteMasterPanel.tsx  296:input/checkbox
- frontend/src/pages/super-admin/components/ProductCategoriesMasterPanel.tsx  281:input/checkbox
- frontend/src/pages/super-admin/components/ProductFormatsMasterPanel.tsx  312:input/checkbox
- frontend/src/pages/super-admin/components/ProductKindsMasterPanel.tsx  224:input/checkbox
- frontend/src/pages/super-admin/components/ProductLinesMasterPanel.tsx  311:input/checkbox
- frontend/src/pages/super-admin/components/QuantityUnitsMasterPanel.tsx  242:input/checkbox
- frontend/src/pages/super-admin/components/RuleTestPanel.tsx  484:input/checkbox
- frontend/src/pages/super-admin/components/StatusMasterPanel.tsx  311:select/- 325:select/- 353:input/checkbox
- frontend/src/pages/super-admin/components/SupplierMasterPanel.tsx  378:input/checkbox
- frontend/src/pages/super-admin/components/TypeMasterPanel.tsx  269:input/checkbox
- frontend/src/pages/super-admin/components/UnitMasterPanel.tsx  332:input/checkbox
- frontend/src/pages/super-admin/components/WeightClassesMasterPanel.tsx  254:input/checkbox
- frontend/src/pages/units/UnitsPage.tsx  299:input/checkbox 351:input/checkbox

### 段階3対応（属性変化・参考）
- frontend/src/pages/account-settings/ProfileSection.tsx  112->191:input/omitted 116->195:input/omitted
- frontend/src/pages/staff/StaffEditPage.tsx  176->176:input/omitted 197->173:input/omitted
- frontend/src/pages/staff/StaffPage.tsx  235->250:input/omitted 253->253:input/omitted
