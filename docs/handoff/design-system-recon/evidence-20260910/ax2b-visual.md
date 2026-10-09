# AX-2b 外観の前後（Chromium 147.0.7727.15、幅1280・light。base = origin/main 9ab917748）

方法: ax2b-visual.cjs。before = 現行ソースの CSS と className/inline style。after = 旧規則を取り除いた CSS（ファイルは書き換えず postcss で変換）＋ TextareaControl 標準（class は `comp-field__textarea` だけ、rows/required は保持）。
取り除く規則: components.css の `.form-group textarea`（3規則）、company-forms.css の `.form-grid > .form-row textarea` と `.modal-content(-wide) .form-row textarea`（各 base と :focus）、InboxPage.css の `.outbound-translation-edit` と :focus、supplier-detail-view.css の `.pmd-field textarea`（共有規則からは textarea 側だけ外し、単独規則は resize を落として min-height だけ残す）。商品編集は company-forms.css に独立規則を追加（下記）。
祖先の外側（サイドバー等）は再現していないため width は合成コンテナ基準。before/after の比較にだけ使う。console 警告: なし

商品編集に追加する独立規則（旧 .form-group textarea の宣言を同値で写し、border は --border-strong、focus の枠色は現行の計算値 --border-strong）:

```css
.product-edit-form .form-group textarea { width: 100%; padding: var(--space-2) var(--space-3); border: 1px solid var(--border-strong); border-radius: var(--radius-sm); font-size: var(--font-base); color: var(--text-primary); background: var(--bg-surface); box-sizing: border-box; min-height: var(--textarea-min-h); resize: vertical; }
.product-edit-form .form-group textarea:focus { outline: none; border-color: var(--border-strong); box-shadow: var(--focus-ring-shadow); }
```

## 1. グループ別の前後（差のある項目だけ。同じ before→after を持つ textarea 件数つき。値は px と色）

### G1 .form-group（components.css）（26 件）

対象: components/OrderFinancialPanel.tsx:239, components/PriorityScoreOverride.tsx:91, components/PurchaseDetailPanel.tsx:442, components/ShippingDetailPanel.tsx:551, pages/admin/TenantProfilePage.tsx:170, pages/badges/BadgesPage.tsx:62, pages/buddy/BuddyPage.tsx:66, pages/companies/CompanyFormFields.tsx:64, pages/conditions/ConditionsPage.tsx:340, pages/conditions/ConditionsPage.tsx:350, pages/contacts/ContactEditPage.tsx:191, pages/leads/LeadEditPage.tsx:279, pages/leads/LeadFormFields.tsx:84, pages/leads/LeadFormFields.tsx:153, pages/leads/LeadsPage.tsx:429, pages/orders/OrdersFormModal.tsx:95, pages/purchase-orders/PurchaseOrdersFormModal.tsx:217, pages/roles/RolesPage.tsx:538, pages/staff-reports/StaffReportsPage.tsx:90, pages/staff-reports/StaffReportsPage.tsx:91, pages/staff-reports/StaffReportsPage.tsx:92, pages/super-admin/components/ConditionsMasterPanel.tsx:367, pages/super-admin/components/ConditionsMasterPanel.tsx:380, pages/suppliers/SupplierFormFields.tsx:61, pages/suppliers/SupplierFormFields.tsx:68, pages/teams/TeamFormFields.tsx:44

normal（26 件）: 

| 項目 | before | after | 件数 |
|---|---|---|---|
| border-radius | 4px | 6px | 26/26 |
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Fira | 26/26 |
| line-height | normal | 21.6px | 26/26 |
| transition-property | all | border-color, box-shadow | 26/26 |
| transition-duration | 0s | 0.1s, 0.1s | 26/26 |
| height | 80px | 82.8281px | 4/26 |
| offsetHeight | 80 | 83 | 4/26 |
| height | 120px | 80px | 1/26 |
| min-height | 120px | 80px | 1/26 |
| offsetHeight | 120 | 80 | 1/26 |

focus（26 件）: 

| 項目 | before | after | 件数 |
|---|---|---|---|
| border-radius | 4px | 6px | 26/26 |
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Fira | 26/26 |
| line-height | normal | 21.6px | 26/26 |
| transition-property | all | border-color, box-shadow | 26/26 |
| transition-duration | 0s | 0.1s, 0.1s | 26/26 |
| height | 80px | 82.8281px | 4/26 |
| offsetHeight | 80 | 83 | 4/26 |
| height | 120px | 80px | 1/26 |
| min-height | 120px | 80px | 1/26 |
| offsetHeight | 120 | 80 | 1/26 |

disabled（disabled 属性を持つ 1 件のみ）: 

| 項目 | before | after | 件数 |
|---|---|---|---|
| border-radius | 4px | 6px | 1/1 |
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Fira | 1/1 |
| line-height | normal | 21.6px | 1/1 |
| background-color | rgb(255, 255, 255) | rgb(226, 232, 240) | 1/1 |
| height | 80px | 82.8281px | 1/1 |
| cursor | default | not-allowed | 1/1 |
| opacity | 1 | 0.5 | 1/1 |
| transition-property | all | border-color, box-shadow | 1/1 |
| transition-duration | 0s | 0.1s, 0.1s | 1/1 |
| offsetHeight | 80 | 83 | 1/1 |

### G2 .form-row（company-forms.css）（6 件）

対象: components/MergeLeadModal.tsx:234, pages/companies/CompaniesPage.tsx:499, pages/companies/CompaniesPage.tsx:516, pages/company-detail/CompanyBasicTab.tsx:81, pages/company-detail/CompanyBasicTab.tsx:94, pages/contacts/ContactsPage.tsx:349

normal（6 件）: 

| 項目 | before | after | 件数 |
|---|---|---|---|
| border-color | rgb(203, 213, 224) | rgb(226, 232, 240) | 6/6 |
| line-height | normal | 21.6px | 6/6 |
| transition-property | all | border-color, box-shadow | 6/6 |
| transition-duration | 0s | 0.1s, 0.1s | 6/6 |

focus（6 件）: 

| 項目 | before | after | 件数 |
|---|---|---|---|
| line-height | normal | 21.6px | 6/6 |
| transition-property | all | border-color, box-shadow | 6/6 |
| transition-duration | 0s | 0.1s, 0.1s | 6/6 |

disabled（disabled 属性を持つ 2 件のみ）: 

| 項目 | before | after | 件数 |
|---|---|---|---|
| border-color | rgb(203, 213, 224) | rgb(226, 232, 240) | 2/2 |
| line-height | normal | 21.6px | 2/2 |
| background-color | rgb(255, 255, 255) | rgb(226, 232, 240) | 2/2 |
| cursor | default | not-allowed | 2/2 |
| opacity | 1 | 0.5 | 2/2 |
| transition-property | all | border-color, box-shadow | 2/2 |
| transition-duration | 0s | 0.1s, 0.1s | 2/2 |

### G3 送信下訳（.outbound-translation-edit）（1 件）

対象: pages/inbox/OutboundTranslationPreview.tsx:147

normal（1 件）: 

| 項目 | before | after | 件数 |
|---|---|---|---|
| padding | 12px | 8px / 12px / 8px / 12px | 1/1 |
| border-radius | 4px | 6px | 1/1 |
| font-size | 13.6px | 14.4px | 1/1 |
| line-height | 20.4px | 21.6px | 1/1 |
| background-color | rgba(0, 0, 0, 0) | rgb(255, 255, 255) | 1/1 |
| height | 107.562px | 104.438px | 1/1 |
| min-height | auto | 80px | 1/1 |
| transition-property | all | border-color, box-shadow | 1/1 |
| transition-duration | 0s | 0.1s, 0.1s | 1/1 |
| offsetHeight | 108 | 104 | 1/1 |

focus（1 件）: 

| 項目 | before | after | 件数 |
|---|---|---|---|
| padding | 12px | 8px / 12px / 8px / 12px | 1/1 |
| border-radius | 4px | 6px | 1/1 |
| font-size | 13.6px | 14.4px | 1/1 |
| line-height | 20.4px | 21.6px | 1/1 |
| background-color | rgba(0, 0, 0, 0) | rgb(255, 255, 255) | 1/1 |
| height | 107.562px | 104.438px | 1/1 |
| min-height | auto | 80px | 1/1 |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | 1/1 |
| transition-property | all | border-color, box-shadow | 1/1 |
| transition-duration | 0s | 0.1s, 0.1s | 1/1 |
| offsetHeight | 108 | 104 | 1/1 |

disabled（disabled 属性を持つ 1 件のみ）: 

| 項目 | before | after | 件数 |
|---|---|---|---|
| padding | 12px | 8px / 12px / 8px / 12px | 1/1 |
| border-radius | 4px | 6px | 1/1 |
| font-size | 13.6px | 14.4px | 1/1 |
| line-height | 20.4px | 21.6px | 1/1 |
| background-color | rgba(0, 0, 0, 0) | rgb(226, 232, 240) | 1/1 |
| height | 107.562px | 104.438px | 1/1 |
| min-height | auto | 80px | 1/1 |
| cursor | default | not-allowed | 1/1 |
| opacity | 1 | 0.5 | 1/1 |
| transition-property | all | border-color, box-shadow | 1/1 |
| transition-duration | 0s | 0.1s, 0.1s | 1/1 |
| offsetHeight | 108 | 104 | 1/1 |

### G4 商品マスタドロワー（.pmd-field）（2 件）

対象: features/tcg-analysis-review/ProductMasterDrawer.tsx:217, features/tcg-analysis-review/ProductMasterDrawer.tsx:221

normal（2 件）: 

| 項目 | before | after | 件数 |
|---|---|---|---|
| padding | 8px | 8px / 12px / 8px / 12px | 2/2 |
| font-size | 13.6px | 14.4px | 2/2 |
| font-weight | 500 | 400 | 2/2 |
| line-height | 21.76px | 21.6px | 2/2 |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | 2/2 |
| outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) | 2/2 |
| transition-property | all | border-color, box-shadow | 2/2 |
| transition-duration | 0s | 0.1s, 0.1s | 2/2 |

focus（2 件）: 

| 項目 | before | after | 件数 |
|---|---|---|---|
| padding | 8px | 8px / 12px / 8px / 12px | 2/2 |
| border-color | rgb(226, 232, 240) | rgb(30, 58, 138) | 2/2 |
| font-size | 13.6px | 14.4px | 2/2 |
| font-weight | 500 | 400 | 2/2 |
| line-height | 21.76px | 21.6px | 2/2 |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | 2/2 |
| outline-style | auto | none | 2/2 |
| outline-width | 1px | 3px | 2/2 |
| outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) | 2/2 |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | 2/2 |
| transition-property | all | border-color, box-shadow | 2/2 |
| transition-duration | 0s | 0.1s, 0.1s | 2/2 |

disabled: disabled 属性を持つ textarea なし（参考値は json に記録）

### G5 CSS規則なし（ブラウザ既定）（4 件）

対象: features/tcg-analysis-review/ItemComparison.tsx:27, features/tcg-analysis-review/ItemComparison.tsx:34, pages/admin/DiscordAnnouncePage.tsx:98, pages/inbox/ManualRecordSection.tsx:159

normal（4 件）: 

| 項目 | before | after | 件数 |
|---|---|---|---|
| padding | 0px | 8px / 12px / 8px / 12px | 4/4 |
| border-color | rgb(118, 118, 118) | rgb(226, 232, 240) | 4/4 |
| border-radius | 0px | 6px | 4/4 |
| font-size | 13.3333px | 14.4px | 4/4 |
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Fira | 3/4 |
| line-height | normal | 21.6px | 4/4 |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | 4/4 |
| height | 32px | 80px | 2/4 |
| min-height | auto | 80px | 1/4 |
| resize | both | vertical | 4/4 |
| outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) | 4/4 |
| transition-property | all | border-color, box-shadow | 4/4 |
| transition-duration | 0s | 0.1s, 0.1s | 4/4 |
| offsetHeight | 32 | 80 | 2/4 |
| min-height | 0px | 80px | 3/4 |
| width | 177px | 332.391px | 1/4 |
| offsetWidth | 177 | 332 | 1/4 |
| height | 92px | 147.656px | 1/4 |
| width | 177px | 1280px | 1/4 |
| offsetHeight | 92 | 148 | 1/4 |
| offsetWidth | 177 | 1280 | 1/4 |
| width | 177px | 1226px | 1/4 |
| offsetWidth | 177 | 1226 | 1/4 |
| width | 177px | 1172px | 1/4 |
| offsetWidth | 177 | 1172 | 1/4 |
| font-family | monospace | 'SF Pro Text', 'Segoe UI', Roboto, Helvetica, Arial, sans-serif | 1/4 |
| height | 47px | 82.8281px | 1/4 |
| width | 177px | 1268px | 1/4 |
| offsetHeight | 47 | 83 | 1/4 |
| offsetWidth | 177 | 1268 | 1/4 |
| width | 177px | 1214px | 1/4 |
| offsetWidth | 177 | 1214 | 1/4 |

focus（4 件）: 

| 項目 | before | after | 件数 |
|---|---|---|---|
| padding | 0px | 8px / 12px / 8px / 12px | 4/4 |
| border-color | rgb(118, 118, 118) | rgb(30, 58, 138) | 4/4 |
| border-radius | 0px | 6px | 4/4 |
| font-size | 13.3333px | 14.4px | 4/4 |
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Fira | 3/4 |
| line-height | normal | 21.6px | 4/4 |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | 4/4 |
| height | 32px | 80px | 2/4 |
| min-height | auto | 80px | 1/4 |
| resize | both | vertical | 4/4 |
| outline-style | auto | none | 4/4 |
| outline-width | 1px | 3px | 4/4 |
| outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) | 4/4 |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | 4/4 |
| transition-property | all | border-color, box-shadow | 4/4 |
| transition-duration | 0s | 0.1s, 0.1s | 4/4 |
| offsetHeight | 32 | 80 | 2/4 |
| min-height | 0px | 80px | 3/4 |
| width | 177px | 332.391px | 1/4 |
| offsetWidth | 177 | 332 | 1/4 |
| height | 92px | 147.656px | 1/4 |
| width | 177px | 1280px | 1/4 |
| offsetHeight | 92 | 148 | 1/4 |
| offsetWidth | 177 | 1280 | 1/4 |
| width | 177px | 1226px | 1/4 |
| offsetWidth | 177 | 1226 | 1/4 |
| width | 177px | 1172px | 1/4 |
| offsetWidth | 177 | 1172 | 1/4 |
| font-family | monospace | 'SF Pro Text', 'Segoe UI', Roboto, Helvetica, Arial, sans-serif | 1/4 |
| height | 47px | 82.8281px | 1/4 |
| width | 177px | 1268px | 1/4 |
| offsetHeight | 47 | 83 | 1/4 |
| offsetWidth | 177 | 1268 | 1/4 |
| width | 177px | 1214px | 1/4 |
| offsetWidth | 177 | 1214 | 1/4 |

disabled（disabled 属性を持つ 2 件のみ）: 

| 項目 | before | after | 件数 |
|---|---|---|---|
| padding | 0px | 8px / 12px / 8px / 12px | 2/2 |
| border-color | rgba(118, 118, 118, 0.3) | rgb(226, 232, 240) | 2/2 |
| border-radius | 0px | 6px | 2/2 |
| font-size | 13.3333px | 14.4px | 2/2 |
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Fira | 1/2 |
| line-height | normal | 21.6px | 2/2 |
| color | rgb(84, 84, 84) | rgb(26, 32, 44) | 2/2 |
| background-color | rgba(239, 239, 239, 0.3) | rgb(226, 232, 240) | 2/2 |
| height | 92px | 147.656px | 1/2 |
| min-height | 0px | 80px | 2/2 |
| width | 177px | 1280px | 1/2 |
| resize | both | vertical | 2/2 |
| outline-color | rgb(84, 84, 84) | rgb(26, 32, 44) | 2/2 |
| cursor | default | not-allowed | 2/2 |
| opacity | 1 | 0.5 | 2/2 |
| transition-property | all | border-color, box-shadow | 2/2 |
| transition-duration | 0s | 0.1s, 0.1s | 2/2 |
| offsetHeight | 92 | 148 | 1/2 |
| offsetWidth | 177 | 1280 | 1/2 |
| width | 177px | 1226px | 1/2 |
| offsetWidth | 177 | 1226 | 1/2 |
| width | 177px | 1172px | 1/2 |
| offsetWidth | 177 | 1172 | 1/2 |
| font-family | monospace | 'SF Pro Text', 'Segoe UI', Roboto, Helvetica, Arial, sans-serif | 1/2 |
| height | 47px | 82.8281px | 1/2 |
| width | 177px | 1268px | 1/2 |
| offsetHeight | 47 | 83 | 1/2 |
| offsetWidth | 177 | 1268 | 1/2 |
| width | 177px | 1214px | 1/2 |
| offsetWidth | 177 | 1214 | 1/2 |

### G6 抽出プロンプト（inline のみ）（1 件）

対象: pages/super-admin/ExtractionPromptConfigTab.tsx:222

normal（1 件）: 

| 項目 | before | after | 件数 |
|---|---|---|---|
| padding | 0px | 8px / 12px / 8px / 12px | 1/1 |
| border-color | rgb(118, 118, 118) | rgb(226, 232, 240) | 1/1 |
| border-radius | 0px | 6px | 1/1 |
| font-size | 13.6px | 14.4px | 1/1 |
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Fira | 1/1 |
| line-height | normal | 21.6px | 1/1 |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | 1/1 |
| height | 242px | 363.75px | 1/1 |
| min-height | 0px | 80px | 1/1 |
| resize | both | vertical | 1/1 |
| outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) | 1/1 |
| transition-property | all | border-color, box-shadow | 1/1 |
| transition-duration | 0s | 0.1s, 0.1s | 1/1 |
| offsetHeight | 242 | 364 | 1/1 |

focus（1 件）: 

| 項目 | before | after | 件数 |
|---|---|---|---|
| padding | 0px | 8px / 12px / 8px / 12px | 1/1 |
| border-color | rgb(118, 118, 118) | rgb(30, 58, 138) | 1/1 |
| border-radius | 0px | 6px | 1/1 |
| font-size | 13.6px | 14.4px | 1/1 |
| font-family | monospace | -apple-system, 'system-ui', 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Fira | 1/1 |
| line-height | normal | 21.6px | 1/1 |
| color | rgb(0, 0, 0) | rgb(26, 32, 44) | 1/1 |
| height | 242px | 363.75px | 1/1 |
| min-height | 0px | 80px | 1/1 |
| resize | both | vertical | 1/1 |
| outline-style | auto | none | 1/1 |
| outline-width | 1px | 3px | 1/1 |
| outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) | 1/1 |
| box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px | 1/1 |
| transition-property | all | border-color, box-shadow | 1/1 |
| transition-duration | 0s | 0.1s, 0.1s | 1/1 |
| offsetHeight | 242 | 364 | 1/1 |

disabled: disabled 属性を持つ textarea なし（参考値は json に記録）

### H 商品編集（保留）（1 件）

対象: pages/products/ProductEditPage.tsx:309

normal（1 件）: 差0

focus（1 件）: 差0

disabled: disabled 属性を持つ textarea なし（参考値は json に記録）

## 2. textarea ごとの差分（normal。代表の祖先シグネチャ0。全シグネチャ・全状態は ax2b-visual.json）

| textarea | グループ | 差のある項目数 | 項目 |
|---|---|---|---|
| components/MergeLeadModal.tsx:234 | G2 | 4 | border-color, line-height, transition-property, transition-duration |
| components/OrderFinancialPanel.tsx:239 | G1 | 5 | border-radius, font-family, line-height, transition-property, transition-duration |
| components/PriorityScoreOverride.tsx:91 | G1 | 5 | border-radius, font-family, line-height, transition-property, transition-duration |
| components/PurchaseDetailPanel.tsx:442 | G1 | 5 | border-radius, font-family, line-height, transition-property, transition-duration |
| components/ShippingDetailPanel.tsx:551 | G1 | 5 | border-radius, font-family, line-height, transition-property, transition-duration |
| features/tcg-analysis-review/ItemComparison.tsx:27 | G5 | 14 | padding, border-color, border-radius, font-size, font-family, line-height, color, height, min-height, resize, outline-color, transition-property, transition-duration, offsetHeight |
| features/tcg-analysis-review/ItemComparison.tsx:34 | G5 | 16 | padding, border-color, border-radius, font-size, font-family, line-height, color, height, min-height, width, resize, outline-color, transition-property, transition-duration, offsetHeight, offsetWidth |
| features/tcg-analysis-review/ProductMasterDrawer.tsx:217 | G4 | 8 | padding, font-size, font-weight, line-height, color, outline-color, transition-property, transition-duration |
| features/tcg-analysis-review/ProductMasterDrawer.tsx:221 | G4 | 8 | padding, font-size, font-weight, line-height, color, outline-color, transition-property, transition-duration |
| pages/admin/DiscordAnnouncePage.tsx:98 | G5 | 16 | padding, border-color, border-radius, font-size, font-family, line-height, color, height, min-height, width, resize, outline-color, transition-property, transition-duration, offsetHeight, offsetWidth |
| pages/admin/TenantProfilePage.tsx:170 | G1 | 7 | border-radius, font-family, line-height, height, transition-property, transition-duration, offsetHeight |
| pages/badges/BadgesPage.tsx:62 | G1 | 5 | border-radius, font-family, line-height, transition-property, transition-duration |
| pages/buddy/BuddyPage.tsx:66 | G1 | 5 | border-radius, font-family, line-height, transition-property, transition-duration |
| pages/companies/CompaniesPage.tsx:499 | G2 | 4 | border-color, line-height, transition-property, transition-duration |
| pages/companies/CompaniesPage.tsx:516 | G2 | 4 | border-color, line-height, transition-property, transition-duration |
| pages/companies/CompanyFormFields.tsx:64 | G1 | 5 | border-radius, font-family, line-height, transition-property, transition-duration |
| pages/company-detail/CompanyBasicTab.tsx:81 | G2 | 4 | border-color, line-height, transition-property, transition-duration |
| pages/company-detail/CompanyBasicTab.tsx:94 | G2 | 4 | border-color, line-height, transition-property, transition-duration |
| pages/conditions/ConditionsPage.tsx:340 | G1 | 5 | border-radius, font-family, line-height, transition-property, transition-duration |
| pages/conditions/ConditionsPage.tsx:350 | G1 | 5 | border-radius, font-family, line-height, transition-property, transition-duration |
| pages/contacts/ContactEditPage.tsx:191 | G1 | 5 | border-radius, font-family, line-height, transition-property, transition-duration |
| pages/contacts/ContactsPage.tsx:349 | G2 | 4 | border-color, line-height, transition-property, transition-duration |
| pages/inbox/ManualRecordSection.tsx:159 | G5 | 16 | padding, border-color, border-radius, font-size, font-family, line-height, color, height, min-height, width, resize, outline-color, transition-property, transition-duration, offsetHeight, offsetWidth |
| pages/inbox/OutboundTranslationPreview.tsx:147 | G3 | 10 | padding, border-radius, font-size, line-height, background-color, height, min-height, transition-property, transition-duration, offsetHeight |
| pages/leads/LeadEditPage.tsx:279 | G1 | 5 | border-radius, font-family, line-height, transition-property, transition-duration |
| pages/leads/LeadFormFields.tsx:84 | G1 | 5 | border-radius, font-family, line-height, transition-property, transition-duration |
| pages/leads/LeadFormFields.tsx:153 | G1 | 5 | border-radius, font-family, line-height, transition-property, transition-duration |
| pages/leads/LeadsPage.tsx:429 | G1 | 5 | border-radius, font-family, line-height, transition-property, transition-duration |
| pages/orders/OrdersFormModal.tsx:95 | G1 | 5 | border-radius, font-family, line-height, transition-property, transition-duration |
| pages/products/ProductEditPage.tsx:309 | H | 0 |  |
| pages/purchase-orders/PurchaseOrdersFormModal.tsx:217 | G1 | 7 | border-radius, font-family, line-height, height, transition-property, transition-duration, offsetHeight |
| pages/roles/RolesPage.tsx:538 | G1 | 5 | border-radius, font-family, line-height, transition-property, transition-duration |
| pages/staff-reports/StaffReportsPage.tsx:90 | G1 | 8 | border-radius, font-family, line-height, height, min-height, transition-property, transition-duration, offsetHeight |
| pages/staff-reports/StaffReportsPage.tsx:91 | G1 | 5 | border-radius, font-family, line-height, transition-property, transition-duration |
| pages/staff-reports/StaffReportsPage.tsx:92 | G1 | 5 | border-radius, font-family, line-height, transition-property, transition-duration |
| pages/super-admin/ExtractionPromptConfigTab.tsx:222 | G6 | 14 | padding, border-color, border-radius, font-size, font-family, line-height, color, height, min-height, resize, outline-color, transition-property, transition-duration, offsetHeight |
| pages/super-admin/components/ConditionsMasterPanel.tsx:367 | G1 | 7 | border-radius, font-family, line-height, height, transition-property, transition-duration, offsetHeight |
| pages/super-admin/components/ConditionsMasterPanel.tsx:380 | G1 | 7 | border-radius, font-family, line-height, height, transition-property, transition-duration, offsetHeight |
| pages/suppliers/SupplierFormFields.tsx:61 | G1 | 5 | border-radius, font-family, line-height, transition-property, transition-duration |
| pages/suppliers/SupplierFormFields.tsx:68 | G1 | 5 | border-radius, font-family, line-height, transition-property, transition-duration |
| pages/teams/TeamFormFields.tsx:44 | G1 | 5 | border-radius, font-family, line-height, transition-property, transition-duration |

## 3. 商品編集 ProductEditPage.tsx:309（保留）

祖先シグネチャ 2 通り × normal・focus・disabled の全 45 項目で before と after の差: **0 件**（差0）。

## 4. 既存 <Textarea> 金型利用（13 件）への影響

祖先は各利用箇所の JSX から静的に解決（ax2b-mold-users.cjs）。金型の DOM は `div.comp-field > [label] + textarea.comp-field__textarea`。旧規則を取り除いた前後を比較。

| 利用箇所 | props | 祖先（先頭シグネチャ） | normal/focus/disabled の差の項目数 |
|---|---|---|---|
| components/MergeCompanyModal.tsx:246 | ['rows'] | div.form-row < div.modal-content-wide < div.comp-modal-body < div.comp-modal-dialog | 1/0/2 |
| components/MergeContactModal.tsx:244 | ['label','rows'] | div < div.modal-content-wide < div.comp-modal-body < div.comp-modal-dialog | 0/0/0 |
| features/tcg-product-import/TcgProductDetailDrawer.tsx:238 | ['label','helperText','rows','disabled','fullWidth'] | form.product-detail__form < div.comp-drawer-body < div.comp-drawer-panel < div | 0/0/0 |
| features/tcg-product-import/TcgProductDetailDrawer.tsx:240 | ['label','helperText','rows','disabled','fullWidth'] | form.product-detail__form < div.comp-drawer-body < div.comp-drawer-panel < div | 0/0/0 |
| pages/admin/DiscordConfigPage.tsx:419 | ['disabled','helperText','rows','fullWidth'] | div.comp-card < div.dc-page < div < div.page-layout | 0/0/0 |
| pages/design-preview/sections/FormSection.tsx:71 | ['label','helperText'] | div < div.dp-form-grid < section.dp-section ?(no JSX usage found for FormSection (frontend/src/pages/design-preview/sections/F) | 0/0/0 |
| pages/design-preview/sections/FormSection.tsx:75 | ['label','error','required'] | div < div.dp-form-grid < section.dp-section ?(no JSX usage found for FormSection (frontend/src/pages/design-preview/sections/F) | 0/0/0 |
| pages/design-preview/sections/FormSection.tsx:79 | ['label','disabled','helperText'] | div < div.dp-form-grid < section.dp-section ?(no JSX usage found for FormSection (frontend/src/pages/design-preview/sections/F) | 0/0/0 |
| pages/super-admin/SupplierExtractionRulesPage.tsx:784 | ['label','rows','fullWidth'] | div.supplier-rules-form < div.supplier-rules-split < div < main.mobile-content | 0/0/0 |
| pages/super-admin/SupplierExtractionRulesPage.tsx:795 | ['label','rows','fullWidth'] | div.supplier-rules-form < div.supplier-rules-split < div < main.mobile-content | 0/0/0 |
| pages/super-admin/SupplierExtractionRulesPage.tsx:806 | ['label','helperText','rows','fullWidth'] | div.supplier-rules-form < div.supplier-rules-split < div < main.mobile-content | 0/0/0 |
| pages/super-admin/SupplierExtractionRulesPage.tsx:817 | ['label','helperText','rows','fullWidth'] | div.supplier-rules-form < div.supplier-rules-split < div < main.mobile-content | 0/0/0 |
| pages/super-admin/SupplierExtractionRulesPage.tsx:828 | ['label','helperText','rows','fullWidth'] | div.supplier-rules-form < div.supplier-rules-split < div < main.mobile-content | 0/0/0 |

差が出る利用箇所: 1 件（components/MergeCompanyModal.tsx:246）。

### components/MergeCompanyModal.tsx:246（旧 `.modal-content-wide .form-row textarea` が当たっていた金型）

normal: 

| 項目 | before | after |
|---|---|---|
| border-color | rgb(203, 213, 224) | rgb(226, 232, 240) |

focus: 差0

disabled: 

| 項目 | before | after |
|---|---|---|
| border-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| background-color | rgb(255, 255, 255) | rgb(226, 232, 240) |

前回の静的判定（ax2-shared-rules.md）の「definite 1 / unconfirmed 3」の解決: definite 1 = MergeCompanyModal.tsx:246（祖先 div.form-row < div.modal-content-wide）。unconfirmed 3 = pages/design-preview/sections/FormSection.tsx:71/75/79。FormSection は registry.ts（`component: FormSection` の値参照）経由で描画され JSX 用法が静的に見つからなかっただけで、design-preview 配下のファイルに `form-group` `form-row` `form-grid` `modal-content` の語は 0 件（grep）→ 旧規則は当たらない。実測でも差0。
