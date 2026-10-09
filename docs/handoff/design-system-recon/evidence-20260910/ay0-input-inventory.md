# ay-inventory

base HEAD f0f7ef8c7d89c97d42950e0ab111644b316dd99d (origin/main, worktree release-frontend-textfield-ay1)
TypeScript 5.9.3 AST、対象TSX 275（stories/test除外）、構文エラー 0

native input 総数 449（金型内部 TextField.tsx:64 の 1 を含む）、ページ側 448

## type別（ページ側）と design.md §AV(base 55d99a97e, input460) との比較

| type | 今回 | §AV | 差 |
|---|---|---|---|
| omitted | 150 | 150 | 0 |
| text | 87 | 97 | -10 |
| search | 2 | 2 | 0 |
| email | 23 | 23 | 0 |
| number | 63 | 65 | -2 |
| tel | 8 | 8 | 0 |
| url | 2 | 2 | 0 |
| password | 6 | 6 | 0 |
| date | 11 | 11 | 0 |
| time | 4 | 4 | 0 |
| datetime-local | 1 | 1 | 0 |
| checkbox | 72 | 72 | 0 |
| radio | 7 | 7 | 0 |
| file | 6 | 6 | 0 |
| color | 2 | 2 | 0 |
| range | 1 | 1 | 0 |
| hidden | 0 | 0 | 0 |
| dynamic | 3 | 3 | 0 |
| 合計 | 448 | 460 | -12 |

差の原因は調べていない（未確認）。

## text-like（checkbox/radio/file/color/range/hidden除く、ページ側）: 360

- ref: 2
- onKeyDown: 7
- autoFocus: 0
- spread: 0
- style: 43
- className: 96

ui-allow付き(ページ側全type): 10

## 既存金型利用

- <TextField>: 220、<TextFieldControl>: 0（未存在）
- 渡している属性(件数): onChange=207, label=200, value=200, type=63, required=61, fullWidth=48, disabled=47, placeholder=23, data-testid=19, size=14, accept=13, maxLength=9, onKeyDown=9, helperText=7, readOnly=6, aria-label=5, error=3, min=3, className=2, defaultValue=2, max=1, step=1

## ref・onKeyDown・dynamic の全行(file:line type)

- frontend/src/components/AvatarUpload.tsx:114 type=file ref=true onKeyDown=false textLike=false
- frontend/src/components/DataTable.tsx:174 type=checkbox ref=true onKeyDown=false textLike=false
- frontend/src/components/InventoryPicker.tsx:217 type=text ref=true onKeyDown=true textLike=true
- frontend/src/components/InventorySearchBar.tsx:272 type=text ref=true onKeyDown=true textLike=true
- frontend/src/components/PurchaseDetailPanel.tsx:361 type=dynamic ref=false onKeyDown=false textLike=true
- frontend/src/components/ShippingDetailPanel.tsx:401 type=dynamic ref=false onKeyDown=false textLike=true
- frontend/src/features/tcg-analysis-review/ItemComparison.tsx:28 type=dynamic ref=false onKeyDown=false textLike=true
- frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:470 type=omitted ref=false onKeyDown=true textLike=true
- frontend/src/pages/inbox/InboxMessageThread.tsx:755 type=file ref=true onKeyDown=false textLike=false
- frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:509 type=file ref=true onKeyDown=false textLike=false
- frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:538 type=file ref=true onKeyDown=false textLike=false
- frontend/src/pages/inventory/InventoryPage.tsx:384 type=search ref=false onKeyDown=true textLike=true
- frontend/src/pages/super-admin/DexTab.tsx:200 type=omitted ref=false onKeyDown=true textLike=true
- frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:295 type=omitted ref=false onKeyDown=true textLike=true
- frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:374 type=omitted ref=false onKeyDown=true textLike=true
- frontend/src/pages/super-admin/TcgLineImportPage.tsx:325 type=file ref=true onKeyDown=false textLike=false
- frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:770 type=file ref=true onKeyDown=false textLike=false

## text-like で ui-allow が付いた行

- frontend/src/features/tcg-import-review/ReviewSection.tsx:289 type=text :: {/* ui-allow: super-admin専用確認ページ、汎用コンポーネント対象外 (#3306) */}
- frontend/src/pages/integrations/CarrierCredentialForm.tsx:95 type=text :: {/* ui-allow: CarrierIntegrationPage から移動した既存 input のリファクタ（挙動不変） (#2601) */}
- frontend/src/pages/integrations/CarrierCredentialForm.tsx:121 type=text :: {/* ui-allow: CarrierIntegrationPage から移動した既存 input のリファクタ（挙動不変） (#2601) */}
- frontend/src/pages/super-admin/TcgLineImportPage.tsx:353 type=number :: {/* ui-allow: MIG-04 super-admin専用フォーム、汎用コンポーネント不要 (#3285) */}
- frontend/src/pages/super-admin/TcgLineImportPage.tsx:374 type=text :: {/* ui-allow: MIG-04 super-admin専用フォーム、汎用コンポーネント不要 (#3285) */}
- frontend/src/pages/super-admin/TcgLineImportPage.tsx:395 type=text :: {/* ui-allow: MIG-04 super-admin専用フォーム、汎用コンポーネント不要 (#3285) */}
- frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:803 type=number :: {/* ui-allow: MIG-04 super-admin専用フォーム、汎用コンポーネント不要 (#3285) */}

全行・全属性・祖先class(3段)・ui-allow・金型内判定は ay-inventory.json。
