# AX-2 現状外観（before）と標準金型との差（Chromium 147.0.7727.15、幅1280・light）

方法: ax2-baseline.cjs。textarea ごとに、ax2-applied-css.json の祖先連鎖（異なるシグネチャごと）から DOM を作り、その textarea に効く CSS を import 順に読み込んで computed style を実測。
- CSS 読込順: index.css(+tokens.css,field-size.css を展開) → 共通CSS(App.tsx 順) → forward/reverse の画面CSS → 最後に components/FormField.css（aw2b-visual.cjs と同じ展開方法）
- before: 現行の className / inline style / rows / required を再現。disabled を持つものは disabled 状態も実測
- afterMd / afterSm: 同じ祖先・同じ CSS の中に、`class="comp-field__textarea"`（sm は `comp-field__textarea comp-field__textarea--sm`）だけを持つ textarea を置いた実測（旧 className と inline style は外し、rows と required は残す。= TextareaControl に置換した場合の実際の見え方）
- 注意: 祖先の外側（サイドバー、PageLayout 等）は再現していない。width / offsetWidth の値は合成コンテナ（body 幅1280）基準で、実画面の値ではない。同一条件の before/after の比較にのみ使うこと
- 計測した条件: textarea 53 件 / 祖先シグネチャ 205 通り × (before・afterMd・afterSm) × (normal・focus・disabled)。console 警告: なし

## 標準金型 TextareaControl 単体（祖先なし、FormField.css のみ）

| 項目 | md normal | md focus | md disabled | sm normal | sm focus |
|---|---|---|---|---|---|
| padding | 8px / 12px / 8px / 12px | 8px / 12px / 8px / 12px | 8px / 12px / 8px / 12px | 4px / 8px / 4px / 8px | 4px / 8px / 4px / 8px |
| border-width | 1px | 1px | 1px | 1px | 1px |
| border-style | solid | solid | solid | solid | solid |
| border-color | rgb(226, 232, 240) | rgb(30, 58, 138) | rgb(226, 232, 240) | rgb(226, 232, 240) | rgb(30, 58, 138) |
| border-radius | 6px | 6px | 6px | 6px | 6px |
| font-size | 14.4px | 14.4px | 14.4px | 13.6px | 13.6px |
| font-family | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | 21.6px | 21.6px | 21.6px | 20.4px | 20.4px |
| color | rgb(26, 32, 44) | rgb(26, 32, 44) | rgb(26, 32, 44) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| background-color | rgb(255, 255, 255) | rgb(255, 255, 255) | rgb(226, 232, 240) | rgb(255, 255, 255) | rgb(255, 255, 255) |
| height | 80px | 80px | 80px | 80px | 80px |
| min-height | 80px | 80px | 80px | 80px | 80px |
| width | 1280px | 1280px | 1280px | 1280px | 1280px |
| max-width | none | none | none | none | none |
| resize | vertical | vertical | vertical | vertical | vertical |
| outline-style | none | none | none | none | none |
| outline-width | 3px | 3px | 3px | 3px | 3px |
| outline-color | rgb(26, 32, 44) | rgb(26, 32, 44) | rgb(26, 32, 44) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| outline-offset | 0px | 0px | 0px | 0px | 0px |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | none | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| box-sizing | border-box | border-box | border-box | border-box | border-box |
| cursor | text | text | not-allowed | text | text |
| opacity | 1 | 1 | 0.5 | 1 | 1 |
| offsetHeight | 80 | 80 | 80 | 80 | 80 |
| offsetWidth | 1280 | 1280 | 1280 | 1280 | 1280 |

(rows=3 の金型 offsetHeight: md 83px、sm 80px)

## 一覧（代表シグネチャ0 の normal を基準。差のある項目数）

| textarea | 現行 class | シグネチャ数(値が異なる組) | md との差 normal/focus/disabled(項目数) | sm との差 normal |
|---|---|---|---|---|
| components/MergeLeadModal.tsx:234 | (なし) | 4(1) | 1/1/- | 1 |
| components/OrderFinancialPanel.tsx:239 | (なし) | 2(1) | 2/2/- | 2 |
| components/PriorityScoreOverride.tsx:91 | (なし) | 1(1) | 2/2/- | 2 |
| components/PurchaseDetailPanel.tsx:442 | (なし) | 2(1) | 2/2/- | 2 |
| components/ShippingDetailPanel.tsx:551 | (なし) | 2(1) | 2/2/- | 2 |
| features/tcg-analysis-review/ItemComparison.tsx:27 | (なし) | 4(1) | 12/15/- | 12 |
| features/tcg-analysis-review/ItemComparison.tsx:34 | (なし) | 4(1) | 14/17/- | 14 |
| features/tcg-analysis-review/ProductMasterDrawer.tsx:217 | (なし) | 4(1) | 2/6/- | 2 |
| features/tcg-analysis-review/ProductMasterDrawer.tsx:221 | (なし) | 4(1) | 2/6/- | 2 |
| pages/admin/DiscordAnnouncePage.tsx:98 | input w-full resize-y | 8(3) | 14/17/17 | 14 |
| pages/admin/TenantProfilePage.tsx:170 | (なし) | 8(3) | 4/4/7 | 4 |
| pages/badges/BadgesPage.tsx:62 | (なし) | 1(1) | 2/2/- | 2 |
| pages/buddy/BuddyPage.tsx:66 | (なし) | 1(1) | 2/2/- | 2 |
| pages/companies/CompaniesPage.tsx:499 | (なし) | 4(1) | 1/1/- | 1 |
| pages/companies/CompaniesPage.tsx:516 | (なし) | 4(1) | 1/1/- | 1 |
| pages/companies/CompanyFormFields.tsx:64 | (なし) | 4(3) | 2/2/- | 2 |
| pages/company-detail/CompanyBasicTab.tsx:81 | (なし) | 4(3) | 1/1/3 | 1 |
| pages/company-detail/CompanyBasicTab.tsx:94 | (なし) | 4(3) | 1/1/3 | 1 |
| pages/conditions/ConditionsPage.tsx:340 | field field-h-md | 4(1) | 2/2/- | 2 |
| pages/conditions/ConditionsPage.tsx:350 | field field-h-md | 4(1) | 2/2/- | 2 |
| pages/contacts/ContactEditPage.tsx:191 | (なし) | 2(2) | 2/2/- | 2 |
| pages/contacts/ContactsPage.tsx:349 | (なし) | 4(1) | 1/1/- | 1 |
| pages/dashboard/PriorityProspectsSection.tsx:410 | db-weekly-composer-input | 2(2) | 9/14/- | 10 |
| pages/dashboard/WeeklyAdvisorSection.tsx:381 | db-weekly-composer-input | 2(2) | 9/14/- | 10 |
| pages/inbox/InboxKartePanel.tsx:484 | right-panel-field | 2(1) | 9/9/- | 8 |
| pages/inbox/InboxKartePanel.tsx:503 | right-panel-field | 2(1) | 9/9/- | 8 |
| pages/inbox/InboxKartePanel.tsx:537 | right-panel-field | 2(1) | 9/9/- | 8 |
| pages/inbox/InboxKartePanel.tsx:588 | right-panel-field | 2(1) | 9/9/- | 8 |
| pages/inbox/InboxMessageThread.tsx:736 | inbox-textarea | 2(2) | 11/12/12 | 12 |
| pages/inbox/InboxProfileModal.tsx:181 | right-panel-field | 2(1) | 9/9/- | 8 |
| pages/inbox/InboxProfileModal.tsx:191 | right-panel-field | 2(1) | 9/9/- | 8 |
| pages/inbox/InboxProfileModal.tsx:210 | right-panel-field | 2(1) | 9/9/- | 8 |
| pages/inbox/InboxProfileModal.tsx:265 | right-panel-field | 2(1) | 9/9/- | 8 |
| pages/inbox/ManualRecordSection.tsx:159 | manual-record-textarea | 2(2) | 14/17/17 | 14 |
| pages/inbox/OutboundTranslationPreview.tsx:147 | outbound-translation-edit | 2(1) | 8/9/10 | 6 |
| pages/leads/LeadEditPage.tsx:279 | (なし) | 2(2) | 2/2/- | 2 |
| pages/leads/LeadFormFields.tsx:84 | (なし) | 6(3) | 2/2/- | 2 |
| pages/leads/LeadFormFields.tsx:153 | (なし) | 4(3) | 2/2/- | 2 |
| pages/leads/LeadsPage.tsx:429 | (なし) | 4(1) | 2/2/- | 2 |
| pages/orders/OrdersFormModal.tsx:95 | (なし) | 2(1) | 2/2/- | 2 |
| pages/products/ProductEditPage.tsx:309 | (なし) | 2(2) | 2/2/- | 2 |
| pages/purchase-orders/PurchaseOrdersFormModal.tsx:217 | (なし) | 6(1) | 4/4/- | 4 |
| pages/roles/RolesPage.tsx:538 | (なし) | 6(1) | 2/2/- | 2 |
| pages/schedule/SchedulePageImpl.tsx:378 | schedule-textarea | 2(1) | 6/6/- | 6 |
| pages/staff-reports/StaffReportsPage.tsx:90 | (なし) | 6(1) | 5/5/- | 5 |
| pages/staff-reports/StaffReportsPage.tsx:91 | (なし) | 6(1) | 2/2/- | 2 |
| pages/staff-reports/StaffReportsPage.tsx:92 | (なし) | 6(1) | 2/2/- | 2 |
| pages/super-admin/ExtractionPromptConfigTab.tsx:222 | (なし) | 2(2) | 12/15/- | 11 |
| pages/super-admin/components/ConditionsMasterPanel.tsx:367 | (なし) | 2(1) | 4/4/- | 4 |
| pages/super-admin/components/ConditionsMasterPanel.tsx:380 | (なし) | 2(1) | 4/4/- | 4 |
| pages/suppliers/SupplierFormFields.tsx:61 | (なし) | 14(3) | 2/2/- | 2 |
| pages/suppliers/SupplierFormFields.tsx:68 | (なし) | 14(3) | 2/2/- | 2 |
| pages/teams/TeamFormFields.tsx:44 | (なし) | 14(3) | 2/2/- | 2 |

## 参考: 現行 → 「祖先の旧規則を除いた素の金型」(bare) との差（旧 .form-group textarea 等の規則を外した場合の到達点。width/offsetWidth は祖先が違うため除外）

| textarea | bare md との差(normal 項目) | 項目名 | bare sm との差(normal 項目) |
|---|---|---|---|
| components/MergeLeadModal.tsx:234 | 2 | border-color,line-height | 4 |
| components/OrderFinancialPanel.tsx:239 | 3 | border-radius,font-family,line-height | 5 |
| components/PriorityScoreOverride.tsx:91 | 3 | border-radius,font-family,line-height | 5 |
| components/PurchaseDetailPanel.tsx:442 | 3 | border-radius,font-family,line-height | 5 |
| components/ShippingDetailPanel.tsx:551 | 3 | border-radius,font-family,line-height | 5 |
| features/tcg-analysis-review/ItemComparison.tsx:27 | 12 | padding,border-color,border-radius,font-size,font-family,line-height,color,height,min-height,resize,outline-color,offsetHeight | 12 |
| features/tcg-analysis-review/ItemComparison.tsx:34 | 12 | padding,border-color,border-radius,font-size,font-family,line-height,color,height,min-height,resize,outline-color,offsetHeight | 12 |
| features/tcg-analysis-review/ProductMasterDrawer.tsx:217 | 8 | padding,font-size,line-height,color,height,min-height,outline-color,offsetHeight | 7 |
| features/tcg-analysis-review/ProductMasterDrawer.tsx:221 | 8 | padding,font-size,line-height,color,height,min-height,outline-color,offsetHeight | 7 |
| pages/admin/DiscordAnnouncePage.tsx:98 | 12 | padding,border-color,border-radius,font-size,font-family,line-height,color,height,min-height,resize,outline-color,offsetHeight | 12 |
| pages/admin/TenantProfilePage.tsx:170 | 5 | border-radius,font-family,line-height,height,offsetHeight | 5 |
| pages/badges/BadgesPage.tsx:62 | 3 | border-radius,font-family,line-height | 5 |
| pages/buddy/BuddyPage.tsx:66 | 3 | border-radius,font-family,line-height | 5 |
| pages/companies/CompaniesPage.tsx:499 | 2 | border-color,line-height | 4 |
| pages/companies/CompaniesPage.tsx:516 | 2 | border-color,line-height | 4 |
| pages/companies/CompanyFormFields.tsx:64 | 3 | border-radius,font-family,line-height | 5 |
| pages/company-detail/CompanyBasicTab.tsx:81 | 2 | border-color,line-height | 4 |
| pages/company-detail/CompanyBasicTab.tsx:94 | 2 | border-color,line-height | 4 |
| pages/conditions/ConditionsPage.tsx:340 | 3 | border-radius,font-family,line-height | 5 |
| pages/conditions/ConditionsPage.tsx:350 | 3 | border-radius,font-family,line-height | 5 |
| pages/contacts/ContactEditPage.tsx:191 | 3 | border-radius,font-family,line-height | 5 |
| pages/contacts/ContactsPage.tsx:349 | 2 | border-color,line-height | 4 |
| pages/dashboard/PriorityProspectsSection.tsx:410 | 9 | border-width,border-style,border-color,font-size,line-height,background-color,height,min-height,offsetHeight | 10 |
| pages/dashboard/WeeklyAdvisorSection.tsx:381 | 9 | border-width,border-style,border-color,font-size,line-height,background-color,height,min-height,offsetHeight | 10 |
| pages/inbox/InboxKartePanel.tsx:484 | 10 | padding,border-color,font-size,font-family,line-height,background-color,height,min-height,resize,offsetHeight | 9 |
| pages/inbox/InboxKartePanel.tsx:503 | 10 | padding,border-color,font-size,font-family,line-height,background-color,height,min-height,resize,offsetHeight | 9 |
| pages/inbox/InboxKartePanel.tsx:537 | 10 | padding,border-color,font-size,font-family,line-height,background-color,height,min-height,resize,offsetHeight | 9 |
| pages/inbox/InboxKartePanel.tsx:588 | 10 | padding,border-color,font-size,font-family,line-height,background-color,height,min-height,resize,offsetHeight | 9 |
| pages/inbox/InboxMessageThread.tsx:736 | 12 | padding,border-width,border-style,border-color,border-radius,font-family,line-height,background-color,height,min-height,resize,offsetHeight | 13 |
| pages/inbox/InboxProfileModal.tsx:181 | 9 | padding,border-color,font-size,line-height,background-color,height,min-height,resize,offsetHeight | 8 |
| pages/inbox/InboxProfileModal.tsx:191 | 9 | padding,border-color,font-size,line-height,background-color,height,min-height,resize,offsetHeight | 8 |
| pages/inbox/InboxProfileModal.tsx:210 | 9 | padding,border-color,font-size,line-height,background-color,height,min-height,resize,offsetHeight | 8 |
| pages/inbox/InboxProfileModal.tsx:265 | 9 | padding,border-color,font-size,line-height,background-color,height,min-height,resize,offsetHeight | 8 |
| pages/inbox/ManualRecordSection.tsx:159 | 12 | padding,border-color,border-radius,font-size,font-family,line-height,color,height,min-height,resize,outline-color,offsetHeight | 12 |
| pages/inbox/OutboundTranslationPreview.tsx:147 | 9 | padding,border-radius,font-size,font-family,line-height,background-color,height,min-height,offsetHeight | 7 |
| pages/leads/LeadEditPage.tsx:279 | 3 | border-radius,font-family,line-height | 5 |
| pages/leads/LeadFormFields.tsx:84 | 3 | border-radius,font-family,line-height | 5 |
| pages/leads/LeadFormFields.tsx:153 | 3 | border-radius,font-family,line-height | 5 |
| pages/leads/LeadsPage.tsx:429 | 3 | border-radius,font-family,line-height | 5 |
| pages/orders/OrdersFormModal.tsx:95 | 3 | border-radius,font-family,line-height | 5 |
| pages/products/ProductEditPage.tsx:309 | 4 | border-color,border-radius,font-family,line-height | 6 |
| pages/purchase-orders/PurchaseOrdersFormModal.tsx:217 | 5 | border-radius,font-family,line-height,height,offsetHeight | 5 |
| pages/roles/RolesPage.tsx:538 | 3 | border-radius,font-family,line-height | 5 |
| pages/schedule/SchedulePageImpl.tsx:378 | 6 | font-size,font-family,line-height,height,min-height,offsetHeight | 6 |
| pages/staff-reports/StaffReportsPage.tsx:90 | 6 | border-radius,font-family,line-height,height,min-height,offsetHeight | 8 |
| pages/staff-reports/StaffReportsPage.tsx:91 | 3 | border-radius,font-family,line-height | 5 |
| pages/staff-reports/StaffReportsPage.tsx:92 | 3 | border-radius,font-family,line-height | 5 |
| pages/super-admin/ExtractionPromptConfigTab.tsx:222 | 12 | padding,border-color,border-radius,font-size,font-family,line-height,color,height,min-height,resize,outline-color,offsetHeight | 11 |
| pages/super-admin/components/ConditionsMasterPanel.tsx:367 | 5 | border-radius,font-family,line-height,height,offsetHeight | 5 |
| pages/super-admin/components/ConditionsMasterPanel.tsx:380 | 5 | border-radius,font-family,line-height,height,offsetHeight | 5 |
| pages/suppliers/SupplierFormFields.tsx:61 | 3 | border-radius,font-family,line-height | 5 |
| pages/suppliers/SupplierFormFields.tsx:68 | 3 | border-radius,font-family,line-height | 5 |
| pages/teams/TeamFormFields.tsx:44 | 3 | border-radius,font-family,line-height | 5 |

## textarea ごとの差分表（before → 標準に置換した場合。値の異なる項目のみ。差が 0 の状態は「差0」）

### components/MergeLeadModal.tsx:234（class: なし / rows=2 / disabled属性=なし）

祖先パターン1/1（4 シグネチャ）: div.form-row < div.modal-content-wide < div.comp-modal-body < div.comp-modal-dialog < div.comp-modal-overlay < div < div.page-layout < div.hub-content < div.hub-shell < div < div.page-layout < main.mobile-content < div.mobile-shell < main.mobile-content < div.mobile-shell ほか 3 通り（値は同一）

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| line-height | normal | 21.6px | 21.6px |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| line-height | normal | 21.6px | 21.6px |

### components/OrderFinancialPanel.tsx:239（class: なし / rows=未指定 / disabled属性=なし）

祖先パターン1/1（2 シグネチャ）: div.form-group < form < div.comp-modal-body < div.comp-modal-dialog < div.comp-modal-overlay < div < div.page-layout < main.mobile-content < div.mobile-shell ほか 1 通り（値は同一）

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

### components/PriorityScoreOverride.tsx:91（class: なし / rows=未指定 / disabled属性=なし）

祖先パターン1/1（1 シグネチャ）: div.form-group < form < div.comp-modal-body < div.comp-modal-dialog < div.comp-modal-overlay

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

### components/PurchaseDetailPanel.tsx:442（class: なし / rows=未指定 / disabled属性=なし）

祖先パターン1/1（2 シグネチャ）: div.form-group < form < div.comp-modal-body < div.comp-modal-dialog < div.comp-modal-overlay < div < div.page-layout < main.mobile-content < div.mobile-shell ほか 1 通り（値は同一）

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

### components/ShippingDetailPanel.tsx:551（class: なし / rows=未指定 / disabled属性=なし）

祖先パターン1/1（2 シグネチャ）: div.form-group < form < div.comp-modal-body < div.comp-modal-dialog < div.comp-modal-overlay < div < div.page-layout < main.mobile-content < div.mobile-shell ほか 1 通り（値は同一）

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

### features/tcg-analysis-review/ItemComparison.tsx:27（class: なし / rows=未指定 / disabled属性=なし）

祖先パターン1/1（4 シグネチャ）: div.comparison-field.manual-field < div.aligned-fields < article < div.supplier-detail-item-row < section.supplier-detail-items < div.supplier-detail-view-body < div.supplier-detail-view < div.analysis-panel-content < div.hub-content < div.hub-shell < div < div.page-layout < main.mobile-content < div.mobile-shell ほか 3 通り（値は同一）

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| padding | 0px | 8px / 12px / 8px / 12px | 4px / 8px / 4px / 8px |
| border-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 32px | 80px | 80px |
| min-height | auto | 80px | 80px |
| resize | both | vertical | vertical |
| outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| offsetHeight | 32 | 80 | 80 |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| padding | 0px | 8px / 12px / 8px / 12px | 4px / 8px / 4px / 8px |
| border-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 32px | 80px | 80px |
| min-height | auto | 80px | 80px |
| resize | both | vertical | vertical |
| outline-style | auto | none | none |
| outline-width | 1px | 3px | 3px |
| outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| offsetHeight | 32 | 80 | 80 |

### features/tcg-analysis-review/ItemComparison.tsx:34（class: なし / rows=未指定 / disabled属性=なし）

祖先パターン1/1（4 シグネチャ）: div.manual-actions < div.item-extra-grid < article < div.supplier-detail-item-row < section.supplier-detail-items < div.supplier-detail-view-body < div.supplier-detail-view < div.analysis-panel-content < div.hub-content < div.hub-shell < div < div.page-layout < main.mobile-content < div.mobile-shell ほか 3 通り（値は同一）

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| padding | 0px | 8px / 12px / 8px / 12px | 4px / 8px / 4px / 8px |
| border-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 32px | 80px | 80px |
| min-height | 0px | 80px | 80px |
| width | 177px | 332.391px | 332.391px |
| resize | both | vertical | vertical |
| outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| offsetHeight | 32 | 80 | 80 |
| offsetWidth | 177 | 332 | 332 |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| padding | 0px | 8px / 12px / 8px / 12px | 4px / 8px / 4px / 8px |
| border-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 32px | 80px | 80px |
| min-height | 0px | 80px | 80px |
| width | 177px | 332.391px | 332.391px |
| resize | both | vertical | vertical |
| outline-style | auto | none | none |
| outline-width | 1px | 3px | 3px |
| outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| offsetHeight | 32 | 80 | 80 |
| offsetWidth | 177 | 332 | 332 |

### features/tcg-analysis-review/ProductMasterDrawer.tsx:217（class: なし / rows=未指定 / disabled属性=なし）

祖先パターン1/1（4 シグネチャ）: label.pmd-field < div.pmd-fields < div.pmd-body < aside.pmd-drawer < div.analysis-panel-content < div.hub-content < div.hub-shell < div < div.page-layout < main.mobile-content < div.mobile-shell ほか 3 通り（値は同一）

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| border-color | rgb(226, 232, 240) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| outline-style | auto | none | none |
| outline-width | 1px | 3px | 3px |
| outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |

### features/tcg-analysis-review/ProductMasterDrawer.tsx:221（class: なし / rows=未指定 / disabled属性=なし）

祖先パターン1/1（4 シグネチャ）: label.pmd-field < div.pmd-fields < div.pmd-body < aside.pmd-drawer < div.analysis-panel-content < div.hub-content < div.hub-shell < div < div.page-layout < main.mobile-content < div.mobile-shell ほか 3 通り（値は同一）

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| border-color | rgb(226, 232, 240) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| outline-style | auto | none | none |
| outline-width | 1px | 3px | 3px |
| outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |

### pages/admin/DiscordAnnouncePage.tsx:98（class: input w-full resize-y / rows=6 / disabled属性=あり）

祖先パターン1/3（2 シグネチャ）: div.space-y-2 < div.max-w-lg.space-y-6 < div < div.page-layout < div.admin-hub-content < div.admin-hub < main.mobile-content < div.mobile-shell < main.mobile-content < div.mobile-shell ほか 1 通り（値は同一）

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| padding | 0px | 8px / 12px / 8px / 12px | 4px / 8px / 4px / 8px |
| border-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 92px | 147.656px | 132.344px |
| min-height | 0px | 80px | 80px |
| width | 177px | 1280px | 1280px |
| resize | both | vertical | vertical |
| outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| offsetHeight | 92 | 148 | 132 |
| offsetWidth | 177 | 1280 | 1280 |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| padding | 0px | 8px / 12px / 8px / 12px | 4px / 8px / 4px / 8px |
| border-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 92px | 147.656px | 132.344px |
| min-height | 0px | 80px | 80px |
| width | 177px | 1280px | 1280px |
| resize | both | vertical | vertical |
| outline-style | auto | none | none |
| outline-width | 1px | 3px | 3px |
| outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| offsetHeight | 92 | 148 | 132 |
| offsetWidth | 177 | 1280 | 1280 |

disabled:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| padding | 0px | 8px / 12px / 8px / 12px | 4px / 8px / 4px / 8px |
| border-color | rgba(118, 118, 118, 0.3) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(84, 84, 84) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| background-color | rgba(239, 239, 239, 0.3) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| height | 92px | 147.656px | 132.344px |
| min-height | 0px | 80px | 80px |
| width | 177px | 1280px | 1280px |
| resize | both | vertical | vertical |
| outline-color | rgb(84, 84, 84) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| cursor | default | not-allowed | not-allowed |
| opacity | 1 | 0.5 | 0.5 |
| offsetHeight | 92 | 148 | 132 |
| offsetWidth | 177 | 1280 | 1280 |

祖先パターン2/3（4 シグネチャ）: div.space-y-2 < div.max-w-lg.space-y-6 < div < div.page-layout < div.admin-hub-content < div.admin-hub < main.mobile-content < div.mobile-shell < main.app-content < div.app-body < div.app-shell ほか 3 通り（値は同一）

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| padding | 0px | 8px / 12px / 8px / 12px | 4px / 8px / 4px / 8px |
| border-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 92px | 147.656px | 132.344px |
| min-height | 0px | 80px | 80px |
| width | 177px | 1226px | 1226px |
| resize | both | vertical | vertical |
| outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| offsetHeight | 92 | 148 | 132 |
| offsetWidth | 177 | 1226 | 1226 |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| padding | 0px | 8px / 12px / 8px / 12px | 4px / 8px / 4px / 8px |
| border-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 92px | 147.656px | 132.344px |
| min-height | 0px | 80px | 80px |
| width | 177px | 1226px | 1226px |
| resize | both | vertical | vertical |
| outline-style | auto | none | none |
| outline-width | 1px | 3px | 3px |
| outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| offsetHeight | 92 | 148 | 132 |
| offsetWidth | 177 | 1226 | 1226 |

disabled:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| padding | 0px | 8px / 12px / 8px / 12px | 4px / 8px / 4px / 8px |
| border-color | rgba(118, 118, 118, 0.3) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(84, 84, 84) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| background-color | rgba(239, 239, 239, 0.3) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| height | 92px | 147.656px | 132.344px |
| min-height | 0px | 80px | 80px |
| width | 177px | 1226px | 1226px |
| resize | both | vertical | vertical |
| outline-color | rgb(84, 84, 84) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| cursor | default | not-allowed | not-allowed |
| opacity | 1 | 0.5 | 0.5 |
| offsetHeight | 92 | 148 | 132 |
| offsetWidth | 177 | 1226 | 1226 |

祖先パターン3/3（2 シグネチャ）: div.space-y-2 < div.max-w-lg.space-y-6 < div < div.page-layout < div.admin-hub-content < div.admin-hub < main.app-content < div.app-body < div.app-shell < main.app-content < div.app-body < div.app-shell ほか 1 通り（値は同一）

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| padding | 0px | 8px / 12px / 8px / 12px | 4px / 8px / 4px / 8px |
| border-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 92px | 147.656px | 132.344px |
| min-height | 0px | 80px | 80px |
| width | 177px | 1172px | 1172px |
| resize | both | vertical | vertical |
| outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| offsetHeight | 92 | 148 | 132 |
| offsetWidth | 177 | 1172 | 1172 |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| padding | 0px | 8px / 12px / 8px / 12px | 4px / 8px / 4px / 8px |
| border-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 92px | 147.656px | 132.344px |
| min-height | 0px | 80px | 80px |
| width | 177px | 1172px | 1172px |
| resize | both | vertical | vertical |
| outline-style | auto | none | none |
| outline-width | 1px | 3px | 3px |
| outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| offsetHeight | 92 | 148 | 132 |
| offsetWidth | 177 | 1172 | 1172 |

disabled:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| padding | 0px | 8px / 12px / 8px / 12px | 4px / 8px / 4px / 8px |
| border-color | rgba(118, 118, 118, 0.3) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(84, 84, 84) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| background-color | rgba(239, 239, 239, 0.3) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| height | 92px | 147.656px | 132.344px |
| min-height | 0px | 80px | 80px |
| width | 177px | 1172px | 1172px |
| resize | both | vertical | vertical |
| outline-color | rgb(84, 84, 84) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| cursor | default | not-allowed | not-allowed |
| opacity | 1 | 0.5 | 0.5 |
| offsetHeight | 92 | 148 | 132 |
| offsetWidth | 177 | 1172 | 1172 |

### pages/admin/TenantProfilePage.tsx:170（class: なし / rows=3 / disabled属性=あり）

祖先パターン1/3（2 シグネチャ）: div.form-group < form.form < div < div.page-layout < div.admin-hub-content < div.admin-hub < main.mobile-content < div.mobile-shell < main.mobile-content < div.mobile-shell ほか 1 通り（値は同一）

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |
| height | 80px | 82.8281px | 82.8281px |
| offsetHeight | 80 | 83 | 83 |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |
| height | 80px | 82.8281px | 82.8281px |
| offsetHeight | 80 | 83 | 83 |

disabled:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |
| background-color | rgb(255, 255, 255) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| height | 80px | 82.8281px | 82.8281px |
| cursor | default | not-allowed | not-allowed |
| opacity | 1 | 0.5 | 0.5 |
| offsetHeight | 80 | 83 | 83 |

祖先パターン2/3（4 シグネチャ）: div.form-group < form.form < div < div.page-layout < div.admin-hub-content < div.admin-hub < main.mobile-content < div.mobile-shell < main.app-content < div.app-body < div.app-shell ほか 3 通り（値は同一）

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |
| height | 80px | 82.8281px | 82.8281px |
| offsetHeight | 80 | 83 | 83 |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |
| height | 80px | 82.8281px | 82.8281px |
| offsetHeight | 80 | 83 | 83 |

disabled:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |
| background-color | rgb(255, 255, 255) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| height | 80px | 82.8281px | 82.8281px |
| cursor | default | not-allowed | not-allowed |
| opacity | 1 | 0.5 | 0.5 |
| offsetHeight | 80 | 83 | 83 |

祖先パターン3/3（2 シグネチャ）: div.form-group < form.form < div < div.page-layout < div.admin-hub-content < div.admin-hub < main.app-content < div.app-body < div.app-shell < main.app-content < div.app-body < div.app-shell ほか 1 通り（値は同一）

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |
| height | 80px | 82.8281px | 82.8281px |
| offsetHeight | 80 | 83 | 83 |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |
| height | 80px | 82.8281px | 82.8281px |
| offsetHeight | 80 | 83 | 83 |

disabled:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |
| background-color | rgb(255, 255, 255) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| height | 80px | 82.8281px | 82.8281px |
| cursor | default | not-allowed | not-allowed |
| opacity | 1 | 0.5 | 0.5 |
| offsetHeight | 80 | 83 | 83 |

### pages/badges/BadgesPage.tsx:62（class: なし / rows=未指定 / disabled属性=なし）

祖先パターン1/1（1 シグネチャ）: div.form-group < form < div.comp-modal-body < div.comp-modal-dialog < div.comp-modal-overlay < div < div.page-layout

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

### pages/buddy/BuddyPage.tsx:66（class: なし / rows=未指定 / disabled属性=なし）

祖先パターン1/1（1 シグネチャ）: div.form-group < form < div.comp-modal-body < div.comp-modal-dialog < div.comp-modal-overlay < div < div.page-layout

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

### pages/companies/CompaniesPage.tsx:499（class: なし / rows=未指定 / disabled属性=なし）

祖先パターン1/1（4 シグネチャ）: div.form-row < form.form-grid < div.modal-content-wide < div.comp-modal-body < div.comp-modal-dialog < div.comp-modal-overlay < div < div.page-layout < div.hub-content < div.hub-shell < div < div.page-layout < main.mobile-content < div.mobile-shell < main.mobile-content < div.mobile-shell ほか 3 通り（値は同一）

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| line-height | normal | 21.6px | 21.6px |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| line-height | normal | 21.6px | 21.6px |

### pages/companies/CompaniesPage.tsx:516（class: なし / rows=未指定 / disabled属性=なし）

祖先パターン1/1（4 シグネチャ）: div.form-row < form.form-grid < div.modal-content-wide < div.comp-modal-body < div.comp-modal-dialog < div.comp-modal-overlay < div < div.page-layout < div.hub-content < div.hub-shell < div < div.page-layout < main.mobile-content < div.mobile-shell < main.mobile-content < div.mobile-shell ほか 3 通り（値は同一）

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| line-height | normal | 21.6px | 21.6px |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| line-height | normal | 21.6px | 21.6px |

### pages/companies/CompanyFormFields.tsx:64（class: なし / rows=未指定 / disabled属性=なし）

祖先パターン1/3（1 シグネチャ）: div.form-group < form < div.comp-drawer-body < div.comp-drawer-panel < div < div.page-layout < div.hub-content < div.hub-shell < div < div.page-layout < main.mobile-content < div.mobile-shell < main.mobile-content < div.mobile-shell

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

祖先パターン2/3（2 シグネチャ）: div.form-group < form < div.comp-drawer-body < div.comp-drawer-panel < div < div.page-layout < div.hub-content < div.hub-shell < div < div.page-layout < main.mobile-content < div.mobile-shell < main.app-content < div.app-body < div.app-shell ほか 1 通り（値は同一）

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

祖先パターン3/3（1 シグネチャ）: div.form-group < form < div.comp-drawer-body < div.comp-drawer-panel < div < div.page-layout < div.hub-content < div.hub-shell < div < div.page-layout < main.app-content < div.app-body < div.app-shell < main.app-content < div.app-body < div.app-shell

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

### pages/company-detail/CompanyBasicTab.tsx:81（class: なし / rows=未指定 / disabled属性=あり）

祖先パターン1/3（1 シグネチャ）: div.form-row < form.form-grid < div < div.page-layout < div.page-container-detail < div.hub-content < div.hub-shell < div < div.page-layout < main.mobile-content < div.mobile-shell < main.mobile-content < div.mobile-shell

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| line-height | normal | 21.6px | 21.6px |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| line-height | normal | 21.6px | 21.6px |

disabled:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| line-height | normal | 21.6px | 21.6px |
| cursor | default | not-allowed | not-allowed |
| opacity | 1 | 0.5 | 0.5 |

祖先パターン2/3（2 シグネチャ）: div.form-row < form.form-grid < div < div.page-layout < div.page-container-detail < div.hub-content < div.hub-shell < div < div.page-layout < main.mobile-content < div.mobile-shell < main.app-content < div.app-body < div.app-shell ほか 1 通り（値は同一）

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| line-height | normal | 21.6px | 21.6px |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| line-height | normal | 21.6px | 21.6px |

disabled:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| line-height | normal | 21.6px | 21.6px |
| cursor | default | not-allowed | not-allowed |
| opacity | 1 | 0.5 | 0.5 |

祖先パターン3/3（1 シグネチャ）: div.form-row < form.form-grid < div < div.page-layout < div.page-container-detail < div.hub-content < div.hub-shell < div < div.page-layout < main.app-content < div.app-body < div.app-shell < main.app-content < div.app-body < div.app-shell

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| line-height | normal | 21.6px | 21.6px |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| line-height | normal | 21.6px | 21.6px |

disabled:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| line-height | normal | 21.6px | 21.6px |
| cursor | default | not-allowed | not-allowed |
| opacity | 1 | 0.5 | 0.5 |

### pages/company-detail/CompanyBasicTab.tsx:94（class: なし / rows=未指定 / disabled属性=あり）

祖先パターン1/3（1 シグネチャ）: div.form-row < form.form-grid < div < div.page-layout < div.page-container-detail < div.hub-content < div.hub-shell < div < div.page-layout < main.mobile-content < div.mobile-shell < main.mobile-content < div.mobile-shell

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| line-height | normal | 21.6px | 21.6px |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| line-height | normal | 21.6px | 21.6px |

disabled:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| line-height | normal | 21.6px | 21.6px |
| cursor | default | not-allowed | not-allowed |
| opacity | 1 | 0.5 | 0.5 |

祖先パターン2/3（2 シグネチャ）: div.form-row < form.form-grid < div < div.page-layout < div.page-container-detail < div.hub-content < div.hub-shell < div < div.page-layout < main.mobile-content < div.mobile-shell < main.app-content < div.app-body < div.app-shell ほか 1 通り（値は同一）

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| line-height | normal | 21.6px | 21.6px |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| line-height | normal | 21.6px | 21.6px |

disabled:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| line-height | normal | 21.6px | 21.6px |
| cursor | default | not-allowed | not-allowed |
| opacity | 1 | 0.5 | 0.5 |

祖先パターン3/3（1 シグネチャ）: div.form-row < form.form-grid < div < div.page-layout < div.page-container-detail < div.hub-content < div.hub-shell < div < div.page-layout < main.app-content < div.app-body < div.app-shell < main.app-content < div.app-body < div.app-shell

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| line-height | normal | 21.6px | 21.6px |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| line-height | normal | 21.6px | 21.6px |

disabled:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| line-height | normal | 21.6px | 21.6px |
| cursor | default | not-allowed | not-allowed |
| opacity | 1 | 0.5 | 0.5 |

### pages/conditions/ConditionsPage.tsx:340（class: field field-h-md / inline: height:80px;resize:vertical;width:100% / rows=未指定 / disabled属性=なし）

祖先パターン1/1（4 シグネチャ）: div.form-group < div < form < div.comp-modal-body < div.comp-modal-dialog < div.comp-modal-overlay < div < div.page-layout < div.hub-content < div.hub-shell < div < div.page-layout < main.mobile-content < div.mobile-shell < main.mobile-content < div.mobile-shell ほか 3 通り（値は同一）

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

### pages/conditions/ConditionsPage.tsx:350（class: field field-h-md / inline: height:80px;resize:vertical;width:100% / rows=未指定 / disabled属性=なし）

祖先パターン1/1（4 シグネチャ）: div.form-group < div < form < div.comp-modal-body < div.comp-modal-dialog < div.comp-modal-overlay < div < div.page-layout < div.hub-content < div.hub-shell < div < div.page-layout < main.mobile-content < div.mobile-shell < main.mobile-content < div.mobile-shell ほか 3 通り（値は同一）

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

### pages/contacts/ContactEditPage.tsx:191（class: なし / rows=未指定 / disabled属性=なし）

祖先パターン1/2（1 シグネチャ）: div.form-group < form < div < div.page-layout < main.mobile-content < div.mobile-shell

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

祖先パターン2/2（1 シグネチャ）: div.form-group < form < div < div.page-layout < main.app-content < div.app-body < div.app-shell

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

### pages/contacts/ContactsPage.tsx:349（class: なし / rows=未指定 / disabled属性=なし）

祖先パターン1/1（4 シグネチャ）: div.form-row < form.form-grid < div.modal-content-wide < div.comp-modal-body < div.comp-modal-dialog < div.comp-modal-overlay < div < div.page-layout < div.hub-content < div.hub-shell < div < div.page-layout < main.mobile-content < div.mobile-shell < main.mobile-content < div.mobile-shell ほか 3 通り（値は同一）

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| line-height | normal | 21.6px | 21.6px |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| line-height | normal | 21.6px | 21.6px |

### pages/dashboard/PriorityProspectsSection.tsx:410（class: db-weekly-composer-input / rows=3 / disabled属性=なし）

祖先パターン1/2（1 シグネチャ）: div.db-weekly-composer-field < div.db-weekly-composer < li.db-priority-item < ul.db-priority-list < div.db-section-card.db-priority-card < div.db-content-stack < div < div.page-layout < main.mobile-content < div.mobile-shell

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| border-width | 0px | 1px | 1px |
| border-style | none | solid | solid |
| border-color | rgb(26, 32, 44) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| font-size | 16px | 14.4px | 13.6px |
| line-height | 25.6px | 21.6px | 20.4px |
| background-color | rgb(245, 247, 250) | rgb(255, 255, 255) | rgb(255, 255, 255) |
| height | 92.7812px | 82.8281px | 80px |
| min-height | auto | 80px | 80px |
| offsetHeight | 93 | 83 | 80 |
| padding | 8px / 12px / 8px / 12px | 8px / 12px / 8px / 12px (差なし) | 4px / 8px / 4px / 8px |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| border-width | 0px | 1px | 1px |
| border-style | none | solid | solid |
| border-color | rgb(26, 32, 44) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| font-size | 16px | 14.4px | 13.6px |
| line-height | 25.6px | 21.6px | 20.4px |
| background-color | rgb(245, 247, 250) | rgb(255, 255, 255) | rgb(255, 255, 255) |
| height | 92.7812px | 82.8281px | 80px |
| min-height | auto | 80px | 80px |
| outline-style | solid | none | none |
| outline-width | 2px | 3px | 3px |
| outline-color | rgb(30, 58, 138) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| outline-offset | 1px | 0px | 0px |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| offsetHeight | 93 | 83 | 80 |
| padding | 8px / 12px / 8px / 12px | 8px / 12px / 8px / 12px (差なし) | 4px / 8px / 4px / 8px |

祖先パターン2/2（1 シグネチャ）: div.db-weekly-composer-field < div.db-weekly-composer < li.db-priority-item < ul.db-priority-list < div.db-section-card.db-priority-card < div.db-content-stack < div < div.page-layout < main.app-content < div.app-body < div.app-shell

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| border-width | 0px | 1px | 1px |
| border-style | none | solid | solid |
| border-color | rgb(26, 32, 44) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| font-size | 16px | 14.4px | 13.6px |
| line-height | 25.6px | 21.6px | 20.4px |
| background-color | rgb(245, 247, 250) | rgb(255, 255, 255) | rgb(255, 255, 255) |
| height | 92.7812px | 82.8281px | 80px |
| min-height | auto | 80px | 80px |
| offsetHeight | 93 | 83 | 80 |
| padding | 8px / 12px / 8px / 12px | 8px / 12px / 8px / 12px (差なし) | 4px / 8px / 4px / 8px |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| border-width | 0px | 1px | 1px |
| border-style | none | solid | solid |
| border-color | rgb(26, 32, 44) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| font-size | 16px | 14.4px | 13.6px |
| line-height | 25.6px | 21.6px | 20.4px |
| background-color | rgb(245, 247, 250) | rgb(255, 255, 255) | rgb(255, 255, 255) |
| height | 92.7812px | 82.8281px | 80px |
| min-height | auto | 80px | 80px |
| outline-style | solid | none | none |
| outline-width | 2px | 3px | 3px |
| outline-color | rgb(30, 58, 138) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| outline-offset | 1px | 0px | 0px |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| offsetHeight | 93 | 83 | 80 |
| padding | 8px / 12px / 8px / 12px | 8px / 12px / 8px / 12px (差なし) | 4px / 8px / 4px / 8px |

### pages/dashboard/WeeklyAdvisorSection.tsx:381（class: db-weekly-composer-input / rows=3 / disabled属性=なし）

祖先パターン1/2（1 シグネチャ）: div.db-weekly-composer-field < div.db-weekly-composer < li.db-weekly-item < ul.db-weekly-list < div.db-section-card.db-weekly-card < div.db-content-stack < div < div.page-layout < main.mobile-content < div.mobile-shell

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| border-width | 0px | 1px | 1px |
| border-style | none | solid | solid |
| border-color | rgb(26, 32, 44) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| font-size | 16px | 14.4px | 13.6px |
| line-height | 25.6px | 21.6px | 20.4px |
| background-color | rgb(245, 247, 250) | rgb(255, 255, 255) | rgb(255, 255, 255) |
| height | 92.7812px | 82.8281px | 80px |
| min-height | auto | 80px | 80px |
| offsetHeight | 93 | 83 | 80 |
| padding | 8px / 12px / 8px / 12px | 8px / 12px / 8px / 12px (差なし) | 4px / 8px / 4px / 8px |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| border-width | 0px | 1px | 1px |
| border-style | none | solid | solid |
| border-color | rgb(26, 32, 44) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| font-size | 16px | 14.4px | 13.6px |
| line-height | 25.6px | 21.6px | 20.4px |
| background-color | rgb(245, 247, 250) | rgb(255, 255, 255) | rgb(255, 255, 255) |
| height | 92.7812px | 82.8281px | 80px |
| min-height | auto | 80px | 80px |
| outline-style | solid | none | none |
| outline-width | 2px | 3px | 3px |
| outline-color | rgb(30, 58, 138) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| outline-offset | 1px | 0px | 0px |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| offsetHeight | 93 | 83 | 80 |
| padding | 8px / 12px / 8px / 12px | 8px / 12px / 8px / 12px (差なし) | 4px / 8px / 4px / 8px |

祖先パターン2/2（1 シグネチャ）: div.db-weekly-composer-field < div.db-weekly-composer < li.db-weekly-item < ul.db-weekly-list < div.db-section-card.db-weekly-card < div.db-content-stack < div < div.page-layout < main.app-content < div.app-body < div.app-shell

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| border-width | 0px | 1px | 1px |
| border-style | none | solid | solid |
| border-color | rgb(26, 32, 44) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| font-size | 16px | 14.4px | 13.6px |
| line-height | 25.6px | 21.6px | 20.4px |
| background-color | rgb(245, 247, 250) | rgb(255, 255, 255) | rgb(255, 255, 255) |
| height | 92.7812px | 82.8281px | 80px |
| min-height | auto | 80px | 80px |
| offsetHeight | 93 | 83 | 80 |
| padding | 8px / 12px / 8px / 12px | 8px / 12px / 8px / 12px (差なし) | 4px / 8px / 4px / 8px |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| border-width | 0px | 1px | 1px |
| border-style | none | solid | solid |
| border-color | rgb(26, 32, 44) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| font-size | 16px | 14.4px | 13.6px |
| line-height | 25.6px | 21.6px | 20.4px |
| background-color | rgb(245, 247, 250) | rgb(255, 255, 255) | rgb(255, 255, 255) |
| height | 92.7812px | 82.8281px | 80px |
| min-height | auto | 80px | 80px |
| outline-style | solid | none | none |
| outline-width | 2px | 3px | 3px |
| outline-color | rgb(30, 58, 138) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| outline-offset | 1px | 0px | 0px |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| offsetHeight | 93 | 83 | 80 |
| padding | 8px / 12px / 8px / 12px | 8px / 12px / 8px / 12px (差なし) | 4px / 8px / 4px / 8px |

### pages/inbox/InboxKartePanel.tsx:484（class: right-panel-field / rows=3 / disabled属性=なし）

祖先パターン1/1（2 シグネチャ）: div.right-panel-section < div.right-panel-tab-content < div.right-panel-card < aside.inbox-right-panel < div.inbox-wrapper < div < div.page-layout < main.mobile-content < div.mobile-shell ほか 1 通り（値は同一）

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| padding | 7px / 9px / 7px / 9px | 8px / 12px / 8px / 12px | 4px / 8px / 4px / 8px |
| border-color | rgb(221, 224, 228) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| font-size | 13.6px | 14.4px | 13.6px (差なし) |
| line-height | normal | 21.6px | 20.4px |
| background-color | rgb(250, 251, 252) | rgb(255, 255, 255) | rgb(255, 255, 255) |
| height | 61px | 82.8281px | 80px |
| min-height | 60px | 80px | 80px |
| resize | none | vertical | vertical |
| offsetHeight | 61 | 83 | 80 |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| padding | 7px / 9px / 7px / 9px | 8px / 12px / 8px / 12px | 4px / 8px / 4px / 8px |
| font-size | 13.6px | 14.4px | 13.6px (差なし) |
| line-height | normal | 21.6px | 20.4px |
| background-color | rgb(250, 251, 252) | rgb(255, 255, 255) | rgb(255, 255, 255) |
| height | 61px | 82.8281px | 80px |
| min-height | 60px | 80px | 80px |
| resize | none | vertical | vertical |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| offsetHeight | 61 | 83 | 80 |

### pages/inbox/InboxKartePanel.tsx:503（class: right-panel-field / rows=3 / disabled属性=なし）

祖先パターン1/1（2 シグネチャ）: div.right-panel-section < div.right-panel-tab-content < div.right-panel-card < aside.inbox-right-panel < div.inbox-wrapper < div < div.page-layout < main.mobile-content < div.mobile-shell ほか 1 通り（値は同一）

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| padding | 7px / 9px / 7px / 9px | 8px / 12px / 8px / 12px | 4px / 8px / 4px / 8px |
| border-color | rgb(221, 224, 228) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| font-size | 13.6px | 14.4px | 13.6px (差なし) |
| line-height | normal | 21.6px | 20.4px |
| background-color | rgb(250, 251, 252) | rgb(255, 255, 255) | rgb(255, 255, 255) |
| height | 61px | 82.8281px | 80px |
| min-height | 60px | 80px | 80px |
| resize | none | vertical | vertical |
| offsetHeight | 61 | 83 | 80 |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| padding | 7px / 9px / 7px / 9px | 8px / 12px / 8px / 12px | 4px / 8px / 4px / 8px |
| font-size | 13.6px | 14.4px | 13.6px (差なし) |
| line-height | normal | 21.6px | 20.4px |
| background-color | rgb(250, 251, 252) | rgb(255, 255, 255) | rgb(255, 255, 255) |
| height | 61px | 82.8281px | 80px |
| min-height | 60px | 80px | 80px |
| resize | none | vertical | vertical |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| offsetHeight | 61 | 83 | 80 |

### pages/inbox/InboxKartePanel.tsx:537（class: right-panel-field / rows=3 / disabled属性=なし）

祖先パターン1/1（2 シグネチャ）: div.right-panel-section < div.right-panel-tab-content < div.right-panel-card < aside.inbox-right-panel < div.inbox-wrapper < div < div.page-layout < main.mobile-content < div.mobile-shell ほか 1 通り（値は同一）

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| padding | 7px / 9px / 7px / 9px | 8px / 12px / 8px / 12px | 4px / 8px / 4px / 8px |
| border-color | rgb(221, 224, 228) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| font-size | 13.6px | 14.4px | 13.6px (差なし) |
| line-height | normal | 21.6px | 20.4px |
| background-color | rgb(250, 251, 252) | rgb(255, 255, 255) | rgb(255, 255, 255) |
| height | 61px | 82.8281px | 80px |
| min-height | 60px | 80px | 80px |
| resize | none | vertical | vertical |
| offsetHeight | 61 | 83 | 80 |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| padding | 7px / 9px / 7px / 9px | 8px / 12px / 8px / 12px | 4px / 8px / 4px / 8px |
| font-size | 13.6px | 14.4px | 13.6px (差なし) |
| line-height | normal | 21.6px | 20.4px |
| background-color | rgb(250, 251, 252) | rgb(255, 255, 255) | rgb(255, 255, 255) |
| height | 61px | 82.8281px | 80px |
| min-height | 60px | 80px | 80px |
| resize | none | vertical | vertical |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| offsetHeight | 61 | 83 | 80 |

### pages/inbox/InboxKartePanel.tsx:588（class: right-panel-field / rows=3 / disabled属性=なし）

祖先パターン1/1（2 シグネチャ）: div.right-panel-section < div.right-panel-tab-content < div.right-panel-card < aside.inbox-right-panel < div.inbox-wrapper < div < div.page-layout < main.mobile-content < div.mobile-shell ほか 1 通り（値は同一）

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| padding | 7px / 9px / 7px / 9px | 8px / 12px / 8px / 12px | 4px / 8px / 4px / 8px |
| border-color | rgb(221, 224, 228) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| font-size | 13.6px | 14.4px | 13.6px (差なし) |
| line-height | normal | 21.6px | 20.4px |
| background-color | rgb(250, 251, 252) | rgb(255, 255, 255) | rgb(255, 255, 255) |
| height | 61px | 82.8281px | 80px |
| min-height | 60px | 80px | 80px |
| resize | none | vertical | vertical |
| offsetHeight | 61 | 83 | 80 |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| padding | 7px / 9px / 7px / 9px | 8px / 12px / 8px / 12px | 4px / 8px / 4px / 8px |
| font-size | 13.6px | 14.4px | 13.6px (差なし) |
| line-height | normal | 21.6px | 20.4px |
| background-color | rgb(250, 251, 252) | rgb(255, 255, 255) | rgb(255, 255, 255) |
| height | 61px | 82.8281px | 80px |
| min-height | 60px | 80px | 80px |
| resize | none | vertical | vertical |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| offsetHeight | 61 | 83 | 80 |

### pages/inbox/InboxMessageThread.tsx:736（class: inbox-textarea / rows=2 / disabled属性=あり）

祖先パターン1/2（1 シグネチャ）: div.send-input-wrap < div.send-top-row < div.send-card < div.inbox-send-area.sticky-bottom-bar < main.inbox-center < div.inbox-columns < div.inbox-main-area < div.inbox-wrapper < div < div.page-layout < main.mobile-content < div.mobile-shell

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| padding | 0px | 8px / 12px / 8px / 12px | 4px / 8px / 4px / 8px |
| border-width | 0px | 1px | 1px |
| border-style | none | solid | solid |
| border-color | rgb(26, 32, 44) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-radius | 0px | 6px | 6px |
| line-height | 20.16px | 21.6px | 20.4px |
| background-color | rgba(0, 0, 0, 0) | rgb(255, 255, 255) | rgb(255, 255, 255) |
| height | 40.3125px | 80px | 80px |
| min-height | auto | 80px | 80px |
| resize | none | vertical | vertical |
| offsetHeight | 40 | 80 | 80 |
| font-size | 14.4px | 14.4px (差なし) | 13.6px |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| padding | 0px | 8px / 12px / 8px / 12px | 4px / 8px / 4px / 8px |
| border-width | 0px | 1px | 1px |
| border-style | none | solid | solid |
| border-color | rgb(26, 32, 44) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-radius | 0px | 6px | 6px |
| line-height | 20.16px | 21.6px | 20.4px |
| background-color | rgba(0, 0, 0, 0) | rgb(255, 255, 255) | rgb(255, 255, 255) |
| height | 40.3125px | 80px | 80px |
| min-height | auto | 80px | 80px |
| resize | none | vertical | vertical |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| offsetHeight | 40 | 80 | 80 |
| font-size | 14.4px | 14.4px (差なし) | 13.6px |

disabled:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| padding | 0px | 8px / 12px / 8px / 12px | 4px / 8px / 4px / 8px |
| border-width | 0px | 1px | 1px |
| border-style | none | solid | solid |
| border-color | rgb(26, 32, 44) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-radius | 0px | 6px | 6px |
| line-height | 20.16px | 21.6px | 20.4px |
| background-color | rgba(0, 0, 0, 0) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| height | 40.3125px | 80px | 80px |
| min-height | auto | 80px | 80px |
| resize | none | vertical | vertical |
| opacity | 0.6 | 0.5 | 0.5 |
| offsetHeight | 40 | 80 | 80 |
| font-size | 14.4px | 14.4px (差なし) | 13.6px |

祖先パターン2/2（1 シグネチャ）: div.send-input-wrap < div.send-top-row < div.send-card < div.inbox-send-area.sticky-bottom-bar < main.inbox-center < div.inbox-columns < div.inbox-main-area < div.inbox-wrapper < div < div.page-layout < main.app-content < div.app-body < div.app-shell

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| padding | 0px | 8px / 12px / 8px / 12px | 4px / 8px / 4px / 8px |
| border-width | 0px | 1px | 1px |
| border-style | none | solid | solid |
| border-color | rgb(26, 32, 44) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-radius | 0px | 6px | 6px |
| line-height | 20.16px | 21.6px | 20.4px |
| background-color | rgba(0, 0, 0, 0) | rgb(255, 255, 255) | rgb(255, 255, 255) |
| height | 40.3125px | 80px | 80px |
| min-height | auto | 80px | 80px |
| resize | none | vertical | vertical |
| offsetHeight | 40 | 80 | 80 |
| font-size | 14.4px | 14.4px (差なし) | 13.6px |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| padding | 0px | 8px / 12px / 8px / 12px | 4px / 8px / 4px / 8px |
| border-width | 0px | 1px | 1px |
| border-style | none | solid | solid |
| border-color | rgb(26, 32, 44) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-radius | 0px | 6px | 6px |
| line-height | 20.16px | 21.6px | 20.4px |
| background-color | rgba(0, 0, 0, 0) | rgb(255, 255, 255) | rgb(255, 255, 255) |
| height | 40.3125px | 80px | 80px |
| min-height | auto | 80px | 80px |
| resize | none | vertical | vertical |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| offsetHeight | 40 | 80 | 80 |
| font-size | 14.4px | 14.4px (差なし) | 13.6px |

disabled:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| padding | 0px | 8px / 12px / 8px / 12px | 4px / 8px / 4px / 8px |
| border-width | 0px | 1px | 1px |
| border-style | none | solid | solid |
| border-color | rgb(26, 32, 44) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-radius | 0px | 6px | 6px |
| line-height | 20.16px | 21.6px | 20.4px |
| background-color | rgba(0, 0, 0, 0) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| height | 40.3125px | 80px | 80px |
| min-height | auto | 80px | 80px |
| resize | none | vertical | vertical |
| opacity | 0.6 | 0.5 | 0.5 |
| offsetHeight | 40 | 80 | 80 |
| font-size | 14.4px | 14.4px (差なし) | 13.6px |

### pages/inbox/InboxProfileModal.tsx:181（class: right-panel-field / rows=3 / disabled属性=なし）

祖先パターン1/1（2 シグネチャ）: div.right-panel-section < div.right-panel-tab-content < div.inbox-profile-modal < div.modal-overlay < main.mobile-content < div.mobile-shell ほか 1 通り（値は同一）

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| padding | 7px / 9px / 7px / 9px | 8px / 12px / 8px / 12px | 4px / 8px / 4px / 8px |
| border-color | rgb(221, 224, 228) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| font-size | 13.6px | 14.4px | 13.6px (差なし) |
| line-height | normal | 21.6px | 20.4px |
| background-color | rgb(250, 251, 252) | rgb(255, 255, 255) | rgb(255, 255, 255) |
| height | 64px | 82.8281px | 80px |
| min-height | 60px | 80px | 80px |
| resize | none | vertical | vertical |
| offsetHeight | 64 | 83 | 80 |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| padding | 7px / 9px / 7px / 9px | 8px / 12px / 8px / 12px | 4px / 8px / 4px / 8px |
| font-size | 13.6px | 14.4px | 13.6px (差なし) |
| line-height | normal | 21.6px | 20.4px |
| background-color | rgb(250, 251, 252) | rgb(255, 255, 255) | rgb(255, 255, 255) |
| height | 64px | 82.8281px | 80px |
| min-height | 60px | 80px | 80px |
| resize | none | vertical | vertical |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| offsetHeight | 64 | 83 | 80 |

### pages/inbox/InboxProfileModal.tsx:191（class: right-panel-field / rows=3 / disabled属性=なし）

祖先パターン1/1（2 シグネチャ）: div.right-panel-section < div.right-panel-tab-content < div.inbox-profile-modal < div.modal-overlay < main.mobile-content < div.mobile-shell ほか 1 通り（値は同一）

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| padding | 7px / 9px / 7px / 9px | 8px / 12px / 8px / 12px | 4px / 8px / 4px / 8px |
| border-color | rgb(221, 224, 228) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| font-size | 13.6px | 14.4px | 13.6px (差なし) |
| line-height | normal | 21.6px | 20.4px |
| background-color | rgb(250, 251, 252) | rgb(255, 255, 255) | rgb(255, 255, 255) |
| height | 64px | 82.8281px | 80px |
| min-height | 60px | 80px | 80px |
| resize | none | vertical | vertical |
| offsetHeight | 64 | 83 | 80 |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| padding | 7px / 9px / 7px / 9px | 8px / 12px / 8px / 12px | 4px / 8px / 4px / 8px |
| font-size | 13.6px | 14.4px | 13.6px (差なし) |
| line-height | normal | 21.6px | 20.4px |
| background-color | rgb(250, 251, 252) | rgb(255, 255, 255) | rgb(255, 255, 255) |
| height | 64px | 82.8281px | 80px |
| min-height | 60px | 80px | 80px |
| resize | none | vertical | vertical |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| offsetHeight | 64 | 83 | 80 |

### pages/inbox/InboxProfileModal.tsx:210（class: right-panel-field / rows=3 / disabled属性=なし）

祖先パターン1/1（2 シグネチャ）: div.right-panel-section < div.right-panel-tab-content < div.inbox-profile-modal < div.modal-overlay < main.mobile-content < div.mobile-shell ほか 1 通り（値は同一）

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| padding | 7px / 9px / 7px / 9px | 8px / 12px / 8px / 12px | 4px / 8px / 4px / 8px |
| border-color | rgb(221, 224, 228) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| font-size | 13.6px | 14.4px | 13.6px (差なし) |
| line-height | normal | 21.6px | 20.4px |
| background-color | rgb(250, 251, 252) | rgb(255, 255, 255) | rgb(255, 255, 255) |
| height | 64px | 82.8281px | 80px |
| min-height | 60px | 80px | 80px |
| resize | none | vertical | vertical |
| offsetHeight | 64 | 83 | 80 |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| padding | 7px / 9px / 7px / 9px | 8px / 12px / 8px / 12px | 4px / 8px / 4px / 8px |
| font-size | 13.6px | 14.4px | 13.6px (差なし) |
| line-height | normal | 21.6px | 20.4px |
| background-color | rgb(250, 251, 252) | rgb(255, 255, 255) | rgb(255, 255, 255) |
| height | 64px | 82.8281px | 80px |
| min-height | 60px | 80px | 80px |
| resize | none | vertical | vertical |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| offsetHeight | 64 | 83 | 80 |

### pages/inbox/InboxProfileModal.tsx:265（class: right-panel-field / rows=3 / disabled属性=なし）

祖先パターン1/1（2 シグネチャ）: div.right-panel-section < div.right-panel-tab-content < div.inbox-profile-modal < div.modal-overlay < main.mobile-content < div.mobile-shell ほか 1 通り（値は同一）

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| padding | 7px / 9px / 7px / 9px | 8px / 12px / 8px / 12px | 4px / 8px / 4px / 8px |
| border-color | rgb(221, 224, 228) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| font-size | 13.6px | 14.4px | 13.6px (差なし) |
| line-height | normal | 21.6px | 20.4px |
| background-color | rgb(250, 251, 252) | rgb(255, 255, 255) | rgb(255, 255, 255) |
| height | 64px | 82.8281px | 80px |
| min-height | 60px | 80px | 80px |
| resize | none | vertical | vertical |
| offsetHeight | 64 | 83 | 80 |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| padding | 7px / 9px / 7px / 9px | 8px / 12px / 8px / 12px | 4px / 8px / 4px / 8px |
| font-size | 13.6px | 14.4px | 13.6px (差なし) |
| line-height | normal | 21.6px | 20.4px |
| background-color | rgb(250, 251, 252) | rgb(255, 255, 255) | rgb(255, 255, 255) |
| height | 64px | 82.8281px | 80px |
| min-height | 60px | 80px | 80px |
| resize | none | vertical | vertical |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| offsetHeight | 64 | 83 | 80 |

### pages/inbox/ManualRecordSection.tsx:159（class: manual-record-textarea / rows=3 / disabled属性=あり）

祖先パターン1/2（1 シグネチャ）: div.manual-record-section < main.inbox-center < div.inbox-columns < div.inbox-main-area < div.inbox-wrapper < div < div.page-layout < main.mobile-content < div.mobile-shell

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| padding | 0px | 8px / 12px / 8px / 12px | 4px / 8px / 4px / 8px |
| border-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | monospace | 'SF Pro Text', 'Segoe UI', Roboto, Helvetica, Arial, sans-serif | 'SF Pro Text', 'Segoe UI', Roboto, Helvetica, Arial, sans-serif |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 47px | 82.8281px | 80px |
| min-height | 0px | 80px | 80px |
| width | 177px | 1268px | 1268px |
| resize | both | vertical | vertical |
| outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| offsetHeight | 47 | 83 | 80 |
| offsetWidth | 177 | 1268 | 1268 |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| padding | 0px | 8px / 12px / 8px / 12px | 4px / 8px / 4px / 8px |
| border-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | monospace | 'SF Pro Text', 'Segoe UI', Roboto, Helvetica, Arial, sans-serif | 'SF Pro Text', 'Segoe UI', Roboto, Helvetica, Arial, sans-serif |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 47px | 82.8281px | 80px |
| min-height | 0px | 80px | 80px |
| width | 177px | 1268px | 1268px |
| resize | both | vertical | vertical |
| outline-style | auto | none | none |
| outline-width | 1px | 3px | 3px |
| outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| offsetHeight | 47 | 83 | 80 |
| offsetWidth | 177 | 1268 | 1268 |

disabled:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| padding | 0px | 8px / 12px / 8px / 12px | 4px / 8px / 4px / 8px |
| border-color | rgba(118, 118, 118, 0.3) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | monospace | 'SF Pro Text', 'Segoe UI', Roboto, Helvetica, Arial, sans-serif | 'SF Pro Text', 'Segoe UI', Roboto, Helvetica, Arial, sans-serif |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(84, 84, 84) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| background-color | rgba(239, 239, 239, 0.3) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| height | 47px | 82.8281px | 80px |
| min-height | 0px | 80px | 80px |
| width | 177px | 1268px | 1268px |
| resize | both | vertical | vertical |
| outline-color | rgb(84, 84, 84) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| cursor | default | not-allowed | not-allowed |
| opacity | 1 | 0.5 | 0.5 |
| offsetHeight | 47 | 83 | 80 |
| offsetWidth | 177 | 1268 | 1268 |

祖先パターン2/2（1 シグネチャ）: div.manual-record-section < main.inbox-center < div.inbox-columns < div.inbox-main-area < div.inbox-wrapper < div < div.page-layout < main.app-content < div.app-body < div.app-shell

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| padding | 0px | 8px / 12px / 8px / 12px | 4px / 8px / 4px / 8px |
| border-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | monospace | 'SF Pro Text', 'Segoe UI', Roboto, Helvetica, Arial, sans-serif | 'SF Pro Text', 'Segoe UI', Roboto, Helvetica, Arial, sans-serif |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 47px | 82.8281px | 80px |
| min-height | 0px | 80px | 80px |
| width | 177px | 1214px | 1214px |
| resize | both | vertical | vertical |
| outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| offsetHeight | 47 | 83 | 80 |
| offsetWidth | 177 | 1214 | 1214 |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| padding | 0px | 8px / 12px / 8px / 12px | 4px / 8px / 4px / 8px |
| border-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | monospace | 'SF Pro Text', 'Segoe UI', Roboto, Helvetica, Arial, sans-serif | 'SF Pro Text', 'Segoe UI', Roboto, Helvetica, Arial, sans-serif |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 47px | 82.8281px | 80px |
| min-height | 0px | 80px | 80px |
| width | 177px | 1214px | 1214px |
| resize | both | vertical | vertical |
| outline-style | auto | none | none |
| outline-width | 1px | 3px | 3px |
| outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| offsetHeight | 47 | 83 | 80 |
| offsetWidth | 177 | 1214 | 1214 |

disabled:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| padding | 0px | 8px / 12px / 8px / 12px | 4px / 8px / 4px / 8px |
| border-color | rgba(118, 118, 118, 0.3) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-radius | 0px | 6px | 6px |
| font-size | 13.3333px | 14.4px | 13.6px |
| font-family | monospace | 'SF Pro Text', 'Segoe UI', Roboto, Helvetica, Arial, sans-serif | 'SF Pro Text', 'Segoe UI', Roboto, Helvetica, Arial, sans-serif |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(84, 84, 84) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| background-color | rgba(239, 239, 239, 0.3) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| height | 47px | 82.8281px | 80px |
| min-height | 0px | 80px | 80px |
| width | 177px | 1214px | 1214px |
| resize | both | vertical | vertical |
| outline-color | rgb(84, 84, 84) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| cursor | default | not-allowed | not-allowed |
| opacity | 1 | 0.5 | 0.5 |
| offsetHeight | 47 | 83 | 80 |
| offsetWidth | 177 | 1214 | 1214 |

### pages/inbox/OutboundTranslationPreview.tsx:147（class: outbound-translation-edit / rows=4 / disabled属性=あり）

祖先パターン1/1（2 シグネチャ）: div.outbound-translation-section < div.outbound-translation-modal < div.outbound-translation-overlay < main.inbox-center < div.inbox-columns < div.inbox-main-area < div.inbox-wrapper < div < div.page-layout < main.mobile-content < div.mobile-shell ほか 1 通り（値は同一）

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| padding | 12px | 8px / 12px / 8px / 12px | 4px / 8px / 4px / 8px |
| border-radius | 4px | 6px | 6px |
| font-size | 13.6px | 14.4px | 13.6px (差なし) |
| line-height | 20.4px | 21.6px | 20.4px (差なし) |
| background-color | rgba(0, 0, 0, 0) | rgb(255, 255, 255) | rgb(255, 255, 255) |
| height | 107.562px | 104.438px | 91.5625px |
| min-height | auto | 80px | 80px |
| offsetHeight | 108 | 104 | 92 |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| padding | 12px | 8px / 12px / 8px / 12px | 4px / 8px / 4px / 8px |
| border-radius | 4px | 6px | 6px |
| font-size | 13.6px | 14.4px | 13.6px (差なし) |
| line-height | 20.4px | 21.6px | 20.4px (差なし) |
| background-color | rgba(0, 0, 0, 0) | rgb(255, 255, 255) | rgb(255, 255, 255) |
| height | 107.562px | 104.438px | 91.5625px |
| min-height | auto | 80px | 80px |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| offsetHeight | 108 | 104 | 92 |

disabled:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| padding | 12px | 8px / 12px / 8px / 12px | 4px / 8px / 4px / 8px |
| border-radius | 4px | 6px | 6px |
| font-size | 13.6px | 14.4px | 13.6px (差なし) |
| line-height | 20.4px | 21.6px | 20.4px (差なし) |
| background-color | rgba(0, 0, 0, 0) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| height | 107.562px | 104.438px | 91.5625px |
| min-height | auto | 80px | 80px |
| cursor | default | not-allowed | not-allowed |
| opacity | 1 | 0.5 | 0.5 |
| offsetHeight | 108 | 104 | 92 |

### pages/leads/LeadEditPage.tsx:279（class: なし / rows=未指定 / disabled属性=なし）

祖先パターン1/2（1 シグネチャ）: div.form-group < form < div < div.page-layout < main.mobile-content < div.mobile-shell

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

祖先パターン2/2（1 シグネチャ）: div.form-group < form < div < div.page-layout < main.app-content < div.app-body < div.app-shell

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

### pages/leads/LeadFormFields.tsx:84（class: なし / rows=未指定 / disabled属性=なし）

祖先パターン1/3（2 シグネチャ）: div.form-group < form < div < div.page-layout < main.mobile-content < div.mobile-shell ほか 1 通り（値は同一）

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

祖先パターン2/3（3 シグネチャ）: div.form-group < form < div < div.page-layout < main.app-content < div.app-body < div.app-shell ほか 2 通り（値は同一）

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

祖先パターン3/3（1 シグネチャ）: div.form-group < form < div.comp-drawer-body < div.comp-drawer-panel < div < div.page-layout < div.hub-content < div.hub-shell < div < div.page-layout < main.app-content < div.app-body < div.app-shell < main.app-content < div.app-body < div.app-shell

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

### pages/leads/LeadFormFields.tsx:153（class: なし / rows=未指定 / disabled属性=なし）

祖先パターン1/3（1 シグネチャ）: div.form-group < form < div.comp-drawer-body < div.comp-drawer-panel < div < div.page-layout < div.hub-content < div.hub-shell < div < div.page-layout < main.mobile-content < div.mobile-shell < main.mobile-content < div.mobile-shell

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

祖先パターン2/3（2 シグネチャ）: div.form-group < form < div.comp-drawer-body < div.comp-drawer-panel < div < div.page-layout < div.hub-content < div.hub-shell < div < div.page-layout < main.mobile-content < div.mobile-shell < main.app-content < div.app-body < div.app-shell ほか 1 通り（値は同一）

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

祖先パターン3/3（1 シグネチャ）: div.form-group < form < div.comp-drawer-body < div.comp-drawer-panel < div < div.page-layout < div.hub-content < div.hub-shell < div < div.page-layout < main.app-content < div.app-body < div.app-shell < main.app-content < div.app-body < div.app-shell

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

### pages/leads/LeadsPage.tsx:429（class: なし / rows=未指定 / disabled属性=なし）

祖先パターン1/1（4 シグネチャ）: div.form-group < form < div.comp-modal-body < div.comp-modal-dialog < div.comp-modal-overlay < div < div.page-layout < div.hub-content < div.hub-shell < div < div.page-layout < main.mobile-content < div.mobile-shell < main.mobile-content < div.mobile-shell ほか 3 通り（値は同一）

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

### pages/orders/OrdersFormModal.tsx:95（class: なし / rows=未指定 / disabled属性=なし）

祖先パターン1/1（2 シグネチャ）: div.form-group < form < div.comp-modal-body < div.comp-modal-dialog < div.comp-modal-overlay < div < div.page-layout < main.mobile-content < div.mobile-shell ほか 1 通り（値は同一）

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

### pages/products/ProductEditPage.tsx:309（class: なし / rows=未指定 / disabled属性=なし）

祖先パターン1/2（1 シグネチャ）: div.form-group.form-group-full < form.product-edit-form < div.page.page--full < div < div.page-layout < main.mobile-content < div.mobile-shell

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

祖先パターン2/2（1 シグネチャ）: div.form-group.form-group-full < form.product-edit-form < div.page.page--full < div < div.page-layout < main.app-content < div.app-body < div.app-shell

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

### pages/purchase-orders/PurchaseOrdersFormModal.tsx:217（class: なし / rows=3 / disabled属性=なし）

祖先パターン1/1（6 シグネチャ）: div.form-group < form < div.comp-modal-body < div.comp-modal-dialog < div.comp-modal-overlay < div < div.page-layout < main.mobile-content < div.mobile-shell ほか 5 通り（値は同一）

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |
| height | 80px | 82.8281px | 82.8281px |
| offsetHeight | 80 | 83 | 83 |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |
| height | 80px | 82.8281px | 82.8281px |
| offsetHeight | 80 | 83 | 83 |

### pages/roles/RolesPage.tsx:538（class: なし / rows=未指定 / disabled属性=なし）

祖先パターン1/1（6 シグネチャ）: div.form-group < form < div.comp-modal-body < div.comp-modal-dialog < div.comp-modal-overlay < div.page.roles-page < main.mobile-content < div.mobile-shell ほか 5 通り（値は同一）

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

### pages/schedule/SchedulePageImpl.tsx:378（class: schedule-textarea / rows=4 / disabled属性=なし）

祖先パターン1/1（2 シグネチャ）: label.schedule-field < div.schedule-popover__body.schedule-popover__body--form < div.schedule-popover < div.schedule-page < main.mobile-content < div.mobile-shell ほか 1 通り（値は同一）

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-size | 13.6px | 14.4px | 13.6px (差なし) |
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 20.4px |
| height | 78px | 104.438px | 91.5625px |
| min-height | auto | 80px | 80px |
| offsetHeight | 78 | 104 | 92 |
| padding | 8px / 12px / 8px / 12px | 8px / 12px / 8px / 12px (差なし) | 4px / 8px / 4px / 8px |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-size | 13.6px | 14.4px | 13.6px (差なし) |
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 20.4px |
| height | 78px | 104.438px | 91.5625px |
| min-height | auto | 80px | 80px |
| offsetHeight | 78 | 104 | 92 |
| padding | 8px / 12px / 8px / 12px | 8px / 12px / 8px / 12px (差なし) | 4px / 8px / 4px / 8px |

### pages/staff-reports/StaffReportsPage.tsx:90（class: なし / inline: min-height:var(--textarea-min-h-lg) / rows=未指定 / disabled属性=なし）

祖先パターン1/1（6 シグネチャ）: div.form-group < form < div.comp-modal-body < div.comp-modal-dialog < div.comp-modal-overlay < div < div.page-layout < main.mobile-content < div.mobile-shell ほか 5 通り（値は同一）

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |
| height | 120px | 80px | 80px |
| min-height | 120px | 80px | 80px |
| offsetHeight | 120 | 80 | 80 |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |
| height | 120px | 80px | 80px |
| min-height | 120px | 80px | 80px |
| offsetHeight | 120 | 80 | 80 |

### pages/staff-reports/StaffReportsPage.tsx:91（class: なし / rows=未指定 / disabled属性=なし）

祖先パターン1/1（6 シグネチャ）: div.form-group < form < div.comp-modal-body < div.comp-modal-dialog < div.comp-modal-overlay < div < div.page-layout < main.mobile-content < div.mobile-shell ほか 5 通り（値は同一）

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

### pages/staff-reports/StaffReportsPage.tsx:92（class: なし / rows=未指定 / disabled属性=なし）

祖先パターン1/1（6 シグネチャ）: div.form-group < form < div.comp-modal-body < div.comp-modal-dialog < div.comp-modal-overlay < div < div.page-layout < main.mobile-content < div.mobile-shell ほか 5 通り（値は同一）

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

### pages/super-admin/ExtractionPromptConfigTab.tsx:222（class: なし / inline: width:100%;font-family:var(--font-mono, monospace);font-size:var(--font-sm);box-sizing:border-box / rows=16 / disabled属性=なし）

祖先パターン1/2（1 シグネチャ）: section < div < div.analysis-panel-content < div.hub-content < div.hub-shell < div < div.page-layout < main.mobile-content < div.mobile-shell

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| padding | 0px | 8px / 12px / 8px / 12px | 4px / 8px / 4px / 8px |
| border-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-radius | 0px | 6px | 6px |
| font-size | 13.6px | 14.4px | 13.6px (差なし) |
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 242px | 363.75px | 336.25px |
| min-height | 0px | 80px | 80px |
| resize | both | vertical | vertical |
| outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| offsetHeight | 242 | 364 | 336 |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| padding | 0px | 8px / 12px / 8px / 12px | 4px / 8px / 4px / 8px |
| border-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-radius | 0px | 6px | 6px |
| font-size | 13.6px | 14.4px | 13.6px (差なし) |
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 242px | 363.75px | 336.25px |
| min-height | 0px | 80px | 80px |
| resize | both | vertical | vertical |
| outline-style | auto | none | none |
| outline-width | 1px | 3px | 3px |
| outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| offsetHeight | 242 | 364 | 336 |

祖先パターン2/2（1 シグネチャ）: section < div < div.analysis-panel-content < div.hub-content < div.hub-shell < div < div.page-layout < main.app-content < div.app-body < div.app-shell

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| padding | 0px | 8px / 12px / 8px / 12px | 4px / 8px / 4px / 8px |
| border-color | rgb(118, 118, 118) | rgb(226, 232, 240) | rgb(226, 232, 240) |
| border-radius | 0px | 6px | 6px |
| font-size | 13.6px | 14.4px | 13.6px (差なし) |
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 242px | 363.75px | 336.25px |
| min-height | 0px | 80px | 80px |
| resize | both | vertical | vertical |
| outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| offsetHeight | 242 | 364 | 336 |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| padding | 0px | 8px / 12px / 8px / 12px | 4px / 8px / 4px / 8px |
| border-color | rgb(118, 118, 118) | rgb(30, 58, 138) | rgb(30, 58, 138) |
| border-radius | 0px | 6px | 6px |
| font-size | 13.6px | 14.4px | 13.6px (差なし) |
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 20.4px |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| height | 242px | 363.75px | 336.25px |
| min-height | 0px | 80px | 80px |
| resize | both | vertical | vertical |
| outline-style | auto | none | none |
| outline-width | 1px | 3px | 3px |
| outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) | rgb(26, 32, 44) |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| offsetHeight | 242 | 364 | 336 |

### pages/super-admin/components/ConditionsMasterPanel.tsx:367（class: なし / inline: width:100%;resize:vertical / rows=3 / disabled属性=なし）

祖先パターン1/1（2 シグネチャ）: div.form-group < div < form < div.comp-drawer-body < div.comp-drawer-panel < div.analysis-panel-content < div.hub-content < div.hub-shell < div < div.page-layout < main.mobile-content < div.mobile-shell ほか 1 通り（値は同一）

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |
| height | 80px | 82.8281px | 82.8281px |
| offsetHeight | 80 | 83 | 83 |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |
| height | 80px | 82.8281px | 82.8281px |
| offsetHeight | 80 | 83 | 83 |

### pages/super-admin/components/ConditionsMasterPanel.tsx:380（class: なし / inline: width:100%;resize:vertical / rows=3 / disabled属性=なし）

祖先パターン1/1（2 シグネチャ）: div.form-group < div < form < div.comp-drawer-body < div.comp-drawer-panel < div.analysis-panel-content < div.hub-content < div.hub-shell < div < div.page-layout < main.mobile-content < div.mobile-shell ほか 1 通り（値は同一）

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |
| height | 80px | 82.8281px | 82.8281px |
| offsetHeight | 80 | 83 | 83 |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |
| height | 80px | 82.8281px | 82.8281px |
| offsetHeight | 80 | 83 | 83 |

### pages/suppliers/SupplierFormFields.tsx:61（class: なし / rows=未指定 / disabled属性=なし）

祖先パターン1/3（5 シグネチャ）: div.form-group < form < div < div.page-layout < main.mobile-content < div.mobile-shell ほか 4 通り（値は同一）

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

祖先パターン2/3（7 シグネチャ）: div.form-group < form < div < div.page-layout < main.app-content < div.app-body < div.app-shell ほか 6 通り（値は同一）

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

祖先パターン3/3（2 シグネチャ）: div.form-group < form < div.comp-modal-body < div.comp-modal-dialog < div.comp-modal-overlay < div < div.page-layout < div.hub-content < div.hub-shell < div < div.page-layout < main.app-content < div.app-body < div.app-shell < main.app-content < div.app-body < div.app-shell ほか 1 通り（値は同一）

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

### pages/suppliers/SupplierFormFields.tsx:68（class: なし / rows=未指定 / disabled属性=なし）

祖先パターン1/3（5 シグネチャ）: div.form-group < form < div < div.page-layout < main.mobile-content < div.mobile-shell ほか 4 通り（値は同一）

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

祖先パターン2/3（7 シグネチャ）: div.form-group < form < div < div.page-layout < main.app-content < div.app-body < div.app-shell ほか 6 通り（値は同一）

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

祖先パターン3/3（2 シグネチャ）: div.form-group < form < div.comp-modal-body < div.comp-modal-dialog < div.comp-modal-overlay < div < div.page-layout < div.hub-content < div.hub-shell < div < div.page-layout < main.app-content < div.app-body < div.app-shell < main.app-content < div.app-body < div.app-shell ほか 1 通り（値は同一）

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

### pages/teams/TeamFormFields.tsx:44（class: なし / rows=未指定 / disabled属性=なし）

祖先パターン1/3（5 シグネチャ）: div.form-group < form < div < div.page-layout < main.mobile-content < div.mobile-shell ほか 4 通り（値は同一）

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

祖先パターン2/3（7 シグネチャ）: div.form-group < form < div < div.page-layout < main.app-content < div.app-body < div.app-shell ほか 6 通り（値は同一）

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

祖先パターン3/3（2 シグネチャ）: div.form-group < form < div.comp-modal-body < div.comp-modal-dialog < div.comp-modal-overlay < div < div.page-layout < div.hub-content < div.hub-shell < div < div.page-layout < main.app-content < div.app-body < div.app-shell < main.app-content < div.app-body < div.app-shell ほか 1 通り（値は同一）

normal:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |

focus:

| 項目 | before(現行) | after md | after sm |
|---|---|---|---|
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantar |
| line-height | normal | 21.6px | 21.6px |
