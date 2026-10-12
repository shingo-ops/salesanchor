# AY-2d 外観実測（Chromium 147.0.7727.15、幅 1280 / 375、light）

手法: snap(origin/main)の CSS を、代表 input の「読み込み対象 CSS」（groups.cjs が決めたもの、index.css は tokens/field-size を inline 展開、FormField.css を最後）として読み込み、JSX 祖先連鎖（最初の連鎖、静的 class のみ）を同じ tag/class で再構成した fixture に input を置いて computed style を取得。
before = 現行（own className・inline style をそのまま付与。動的な width:SEARCH_WIDTH は 30rem（KnowledgeAliasesTab.tsx:72 の定数値）で代用）。
after = TextFieldControl 標準（className="comp-field__input" のみ・md・inline style なし）、かつそのグループに当たる確定規則のセレクタを postcss で CSS から除去した模擬。type・disabled は維持。ファイルは書き換えていない。
代表 = グループ × type × disabled 属性の有無ごとに 1 件（45 件）。表は before と after で値が違うプロパティのみ。差がない状態は「差なし」。disabled は disabled 属性を持つ代表のみ測定（属性を動的に付与）。
after の標準 = FormField.css:47-62（padding space-2/space-3、border 1px solid var(--border)、radius、font-size、width:100% など）。height/offsetHeight は line-height 由来の実測値。

## 要約（通常状態 before → after の主要値。差分の全プロパティは下の詳細表）

### 幅 1280

| 代表（group|type|disabled / 件数 / file:line） | width | offsetHeight | padding(上右下左) | border(幅/style/色) | border-radius | font-size | font-family先頭 | color | background-color | focus時 outline-style/box-shadow/border-top-color |
|---|---|---|---|---|---|---|---|---|---|---|
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | 80 → 1200 | 29 → 40 | 6px 8px 6px 8px → 8px 12px 8px 12px | 1px/solid/rgb(226, 232, 240) (同) | 4px → 6px | 13px → 14.4px | Arial → -apple-system | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(226, 232, 240) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | 100 → 1200 | 29 → 40 | 6px 8px 6px 8px → 8px 12px 8px 12px | 1px/solid/rgb(226, 232, 240) (同) | 4px → 6px | 13px → 14.4px | Arial → -apple-system | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(226, 232, 240) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | 160 → 1200 | 29 → 40 | 6px 8px 6px 8px → 8px 12px 8px 12px | 1px/solid/rgb(226, 232, 240) (同) | 4px → 6px | 13px → 14.4px | Arial → -apple-system | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(226, 232, 240) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | 165 → 1280 | 31 → 40 | 6px 8px 6px 8px → 8px 12px 8px 12px | 2px/inset/rgb(118, 118, 118) → 1px/solid/rgb(226, 232, 240) | 0px → 6px | 13.3333px → 14.4px | Arial → -apple-system | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(118, 118, 118) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G09|text|en / 2件 / components/master-list-editor/MasterListEditor.tsx:135 | 280 → 192 | 36 → 40 | 8px 12px 8px 12px (同) | 1px/solid/rgb(226, 232, 240) (同) | 4px → 6px | 14.4px (同) | Arial → -apple-system | rgb(26, 32, 44) (同) | rgb(255, 255, 255) (同) | auto/none/rgb(226, 232, 240) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | 149 → 1280 | 19 → 40 | 0px 0px 0px 0px → 8px 12px 8px 12px | 2px/inset/rgb(118, 118, 118) → 1px/solid/rgb(226, 232, 240) | 0px → 6px | 13.3333px → 14.4px | Arial → -apple-system | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(118, 118, 118) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | 72 (同) | 23 → 40 | 0px 0px 0px 0px → 8px 12px 8px 12px | 2px/inset/rgb(118, 118, 118) → 1px/solid/rgb(226, 232, 240) | 0px → 6px | 13.3333px → 14.4px | Arial → -apple-system | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(118, 118, 118) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G03|omitted|en / 6件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:68 (保留) | 447 (同) | 40 (同) | 8px 8px 8px 8px → 8px 12px 8px 12px | 1px/solid/rgb(226, 232, 240) (同) | 6px (同) | 13.6px → 14.4px | -apple-system (同) | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(226, 232, 240) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G03|date|en / 1件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:213 (保留) | 447 (同) | 42 (同) | 8px 8px 8px 8px → 8px 12px 8px 12px | 1px/solid/rgb(226, 232, 240) (同) | 6px (同) | 13.6px → 14.4px | -apple-system (同) | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(226, 232, 240) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | 149 → 187 | 19 → 40 | 0px 0px 0px 0px → 8px 12px 8px 12px | 2px/inset/rgb(118, 118, 118) → 1px/solid/rgb(226, 232, 240) | 0px → 6px | 13.3333px → 14.4px | Arial → -apple-system | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(118, 118, 118) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G06|text|en / 3件 / features/tcg-distribution/DistributionTargetForm.tsx:182 | 447 (同) | 40 (同) | 8px 12px 8px 12px (同) | 1px/solid/rgb(226, 232, 240) (同) | 6px (同) | 13.6px → 14.4px | -apple-system (同) | rgb(26, 32, 44) (同) | rgb(255, 255, 255) (同) | solid/none/rgb(30, 58, 138) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | 1280 (同) | 30 → 40 | 6.4px 9.6px 6.4px 9.6px → 8px 12px 8px 12px | 1px/solid/rgb(204, 204, 204) → 1px/solid/rgb(226, 232, 240) | 4px → 6px | 13.6px → 14.4px | Arial → -apple-system | rgb(26, 32, 44) (同) | rgb(245, 247, 250) → rgb(255, 255, 255) | auto/none/rgb(204, 204, 204) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | 149 → 1280 | 19 → 40 | 0px 0px 0px 0px → 8px 12px 8px 12px | 2px/inset/rgb(118, 118, 118) → 1px/solid/rgb(226, 232, 240) | 0px → 6px | 13.3333px → 14.4px | Arial → -apple-system | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(118, 118, 118) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | 149 → 1244 | 19 → 40 | 0px 0px 0px 0px → 8px 12px 8px 12px | 2px/inset/rgb(118, 118, 118) → 1px/solid/rgb(226, 232, 240) | 0px → 6px | 13.3333px → 14.4px | Arial → -apple-system | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(118, 118, 118) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | 90 → 1276 | 19 → 40 | 0px 0px 0px 0px → 8px 12px 8px 12px | 2px/inset/rgb(118, 118, 118) → 1px/solid/rgb(226, 232, 240) | 0px → 6px | 13.3333px → 14.4px | Arial → -apple-system | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(118, 118, 118) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | 60 → 1276 | 19 → 40 | 0px 0px 0px 0px → 8px 12px 8px 12px | 2px/inset/rgb(118, 118, 118) → 1px/solid/rgb(226, 232, 240) | 0px → 6px | 13.3333px → 14.4px | Arial → -apple-system | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(118, 118, 118) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | 280 → 192 | 36 → 40 | 0px 0px 0px 0px → 8px 12px 8px 12px | 2px/inset/rgb(118, 118, 118) → 1px/solid/rgb(226, 232, 240) | 0px → 6px | 13.3333px → 14.4px | Arial → -apple-system | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(118, 118, 118) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | 160 → 192 | 36 → 40 | 0px 0px 0px 0px → 8px 12px 8px 12px | 2px/inset/rgb(118, 118, 118) → 1px/solid/rgb(226, 232, 240) | 0px → 6px | 13.3333px → 14.4px | Arial → -apple-system | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(118, 118, 118) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G26|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:157 | 596 (同) | 33 → 40 | 8px 12px 8px 12px (同) | 1px/solid/rgb(226, 232, 240) (同) | 6px (同) | 13.6px → 14.4px | Arial → -apple-system | rgb(26, 32, 44) (同) | rgb(245, 247, 250) → rgb(255, 255, 255) | none/none/rgb(30, 58, 138) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G27|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:230 | 218 (同) | 44 → 40 | 8px 12px 8px 12px (同) | 1px/solid/rgb(226, 232, 240) (同) | 6px (同) | 13.6px → 14.4px | Arial → -apple-system | rgb(26, 32, 44) (同) | rgb(245, 247, 250) → rgb(255, 255, 255) | none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G28|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:334 | 765 (同) | 44 → 40 | 8px 12px 8px 12px (同) | 1px/solid/rgb(226, 232, 240) (同) | 6px (同) | 13.6px → 14.4px | Arial → -apple-system | rgb(26, 32, 44) (同) | rgb(245, 247, 250) → rgb(255, 255, 255) | none/none/rgb(30, 58, 138) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | 209 → 1268 | 21 → 42 | 0px 0px 0px 0px → 8px 12px 8px 12px | 2px/inset/rgb(118, 118, 118) → 1px/solid/rgb(226, 232, 240) | 0px → 6px | 13.3333px → 14.4px | monospace → "SF Pro Text" | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(118, 118, 118) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | 96 → 1280 | 19 → 40 | 0px 0px 0px 0px → 8px 12px 8px 12px | 2px/inset/rgb(118, 118, 118) → 1px/solid/rgb(226, 232, 240) | 0px → 6px | 13.3333px → 14.4px | Arial → -apple-system | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(118, 118, 118) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | 112 → 1280 | 19 → 40 | 0px 0px 0px 0px → 8px 12px 8px 12px | 2px/inset/rgb(118, 118, 118) → 1px/solid/rgb(226, 232, 240) | 0px → 6px | 13.3333px → 14.4px | Arial → -apple-system | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(118, 118, 118) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | 280 → 192 | 36 → 40 | 0px 0px 0px 0px → 8px 12px 8px 12px | 2px/inset/rgb(118, 118, 118) → 1px/solid/rgb(226, 232, 240) | 0px → 6px | 13.3333px → 14.4px | Arial → -apple-system | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(118, 118, 118) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | 1248 (同) | 19 → 40 | 0px 0px 0px 0px → 8px 12px 8px 12px | 2px/inset/rgb(118, 118, 118) → 1px/solid/rgb(226, 232, 240) | 0px → 6px | 13.3333px → 14.4px | Arial → -apple-system | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(118, 118, 118) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | 1248 (同) | 19 → 40 | 0px 0px 0px 0px → 8px 12px 8px 12px | 2px/inset/rgb(118, 118, 118) → 1px/solid/rgb(226, 232, 240) | 0px → 6px | 13.6px → 14.4px | Arial → -apple-system | rgb(74, 85, 104) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(118, 118, 118) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | 80 → 1248 | 19 → 40 | 0px 0px 0px 0px → 8px 12px 8px 12px | 2px/inset/rgb(118, 118, 118) → 1px/solid/rgb(226, 232, 240) | 0px → 6px | 13.3333px → 14.4px | Arial → -apple-system | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(118, 118, 118) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | 70 → 1248 | 19 → 40 | 0px 0px 0px 0px → 8px 12px 8px 12px | 2px/inset/rgb(118, 118, 118) → 1px/solid/rgb(226, 232, 240) | 0px → 6px | 13.3333px → 14.4px | Arial → -apple-system | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(118, 118, 118) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | 90 → 1248 | 19 → 40 | 0px 0px 0px 0px → 8px 12px 8px 12px | 2px/inset/rgb(118, 118, 118) → 1px/solid/rgb(226, 232, 240) | 0px → 6px | 13.3333px → 14.4px | Arial → -apple-system | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(118, 118, 118) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | 80 → 1248 | 19 → 40 | 0px 0px 0px 0px → 8px 12px 8px 12px | 2px/inset/rgb(118, 118, 118) → 1px/solid/rgb(226, 232, 240) | 0px → 6px | 13.3333px → 14.4px | Arial → -apple-system | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(118, 118, 118) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | 163 → 1280 | 33 → 40 | 8px 8px 8px 8px → 8px 12px 8px 12px | 1px/solid/rgb(226, 232, 240) (同) | 4px → 6px | 13.6px → 14.4px | Arial → -apple-system | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(226, 232, 240) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G30|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:290 | 1280 (同) | 33 → 40 | 8px 8px 8px 8px → 8px 12px 8px 12px | 1px/solid/rgb(226, 232, 240) (同) | 4px → 6px | 13.3333px → 14.4px | Arial → -apple-system | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(226, 232, 240) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G02|omitted|en / 5件 / pages/products/ProductEditPage.tsx:215 (保留) | 1232 (同) | 34 → 40 | 8px 12px 8px 12px (同) | 1px/solid/rgb(203, 213, 224) → 1px/solid/rgb(226, 232, 240) | 4px → 6px | 14.4px (同) | Arial → -apple-system | rgb(26, 32, 44) (同) | rgb(255, 255, 255) (同) | none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(203, 213, 224) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G02|date|en / 1件 / pages/products/ProductEditPage.tsx:262 (保留) | 234 (同) | 37 → 42 | 8px 12px 8px 12px (同) | 1px/solid/rgb(203, 213, 224) → 1px/solid/rgb(226, 232, 240) | 4px → 6px | 14.4px (同) | monospace → -apple-system | rgb(26, 32, 44) (同) | rgb(255, 255, 255) (同) | none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(203, 213, 224) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G02|number|en / 7件 / pages/products/ProductEditPage.tsx:294 (保留) | 234 (同) | 34 → 40 | 8px 12px 8px 12px (同) | 1px/solid/rgb(203, 213, 224) → 1px/solid/rgb(226, 232, 240) | 4px → 6px | 14.4px (同) | Arial → -apple-system | rgb(26, 32, 44) (同) | rgb(255, 255, 255) (同) | none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(203, 213, 224) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G02|url|en / 1件 / pages/products/ProductEditPage.tsx:298 (保留) | 1232 (同) | 34 → 40 | 8px 12px 8px 12px (同) | 1px/solid/rgb(203, 213, 224) → 1px/solid/rgb(226, 232, 240) | 4px → 6px | 14.4px (同) | Arial → -apple-system | rgb(26, 32, 44) (同) | rgb(255, 255, 255) (同) | none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(203, 213, 224) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | 149 → 1132 | 19 → 40 | 0px 0px 0px 0px → 8px 12px 8px 12px | 2px/inset/rgb(118, 118, 118) → 1px/solid/rgb(226, 232, 240) | 0px → 6px | 13.3333px → 14.4px | Arial → -apple-system | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(118, 118, 118) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | 149 → 1132 | 19 → 40 | 0px 0px 0px 0px → 8px 12px 8px 12px | 2px/inset/rgb(118, 118, 118) → 1px/solid/rgb(226, 232, 240) | 0px → 6px | 13.3333px → 14.4px | Arial → -apple-system | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(118, 118, 118) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | 149 → 1132 | 19 → 40 | 0px 0px 0px 0px → 8px 12px 8px 12px | 2px/inset/rgb(118, 118, 118) → 1px/solid/rgb(226, 232, 240) | 0px → 6px | 13.3333px → 14.4px | Arial → -apple-system | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(118, 118, 118) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | 149 → 1132 | 19 → 40 | 0px 0px 0px 0px → 8px 12px 8px 12px | 2px/inset/rgb(118, 118, 118) → 1px/solid/rgb(226, 232, 240) | 0px → 6px | 13.3333px → 14.4px | Arial → -apple-system | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(118, 118, 118) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | 480 → 1232 | 19 → 40 | 0px 0px 0px 0px → 8px 12px 8px 12px | 2px/inset/rgb(118, 118, 118) → 1px/solid/rgb(226, 232, 240) | 0px → 6px | 13.3333px → 14.4px | Arial → -apple-system | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(118, 118, 118) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G32|number|en / 1件 / pages/super-admin/TcgLineImportPage.tsx:353 | 80 → 1280 | 30 → 40 | 6.4px 9.6px 6.4px 9.6px → 8px 12px 8px 12px | 1px/solid/rgb(204, 204, 204) → 1px/solid/rgb(226, 232, 240) | 4px → 6px | 13.6px → 14.4px | Arial → -apple-system | rgb(26, 32, 44) (同) | rgb(245, 247, 250) → rgb(255, 255, 255) | none/none/rgb(204, 204, 204) → none/none/rgb(226, 232, 240) |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | 200 → 1280 | 30 → 40 | 6.4px 9.6px 6.4px 9.6px → 8px 12px 8px 12px | 1px/solid/rgb(204, 204, 204) → 1px/solid/rgb(226, 232, 240) | 4px → 6px | 13.6px → 14.4px | Arial → -apple-system | rgb(26, 32, 44) (同) | rgb(245, 247, 250) → rgb(255, 255, 255) | none/none/rgb(204, 204, 204) → none/none/rgb(226, 232, 240) |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | 80 → 1232 | 25 → 40 | 4px 8px 4px 8px → 8px 12px 8px 12px | 1px/solid/rgb(226, 232, 240) (同) | 4px → 6px | 13.3333px → 14.4px | Arial → -apple-system | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(226, 232, 240) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |

### 幅 375

| 代表（group|type|disabled / 件数 / file:line） | width | offsetHeight | padding(上右下左) | border(幅/style/色) | border-radius | font-size | font-family先頭 | color | background-color | focus時 outline-style/box-shadow/border-top-color |
|---|---|---|---|---|---|---|---|---|---|---|
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | 80 → 327 | 29 → 44 | 6px 8px 6px 8px → 8px 12px 8px 12px | 1px/solid/rgb(226, 232, 240) (同) | 4px → 6px | 13px → 14.4px | Arial → -apple-system | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(226, 232, 240) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | 100 → 327 | 29 → 44 | 6px 8px 6px 8px → 8px 12px 8px 12px | 1px/solid/rgb(226, 232, 240) (同) | 4px → 6px | 13px → 14.4px | Arial → -apple-system | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(226, 232, 240) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | 160 → 327 | 29 → 44 | 6px 8px 6px 8px → 8px 12px 8px 12px | 1px/solid/rgb(226, 232, 240) (同) | 4px → 6px | 13px → 14.4px | Arial → -apple-system | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(226, 232, 240) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | 165 → 375 | 31 → 44 | 6px 8px 6px 8px → 8px 12px 8px 12px | 2px/inset/rgb(118, 118, 118) → 1px/solid/rgb(226, 232, 240) | 0px → 6px | 13.3333px → 14.4px | Arial → -apple-system | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(118, 118, 118) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G09|text|en / 2件 / components/master-list-editor/MasterListEditor.tsx:135 | 280 → 192 | 36 → 44 | 8px 12px 8px 12px (同) | 1px/solid/rgb(226, 232, 240) (同) | 4px → 6px | 14.4px (同) | Arial → -apple-system | rgb(26, 32, 44) (同) | rgb(255, 255, 255) (同) | auto/none/rgb(226, 232, 240) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | 149 → 375 | 19 → 44 | 0px 0px 0px 0px → 8px 12px 8px 12px | 2px/inset/rgb(118, 118, 118) → 1px/solid/rgb(226, 232, 240) | 0px → 6px | 13.3333px → 14.4px | Arial → -apple-system | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(118, 118, 118) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | 72 (同) | 23 → 44 | 0px 0px 0px 0px → 8px 12px 8px 12px | 2px/inset/rgb(118, 118, 118) → 1px/solid/rgb(226, 232, 240) | 0px → 6px | 13.3333px → 14.4px | Arial → -apple-system | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(118, 118, 118) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G03|omitted|en / 6件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:68 (保留) | 342 (同) | 40 → 44 | 8px 8px 8px 8px → 8px 12px 8px 12px | 1px/solid/rgb(226, 232, 240) (同) | 6px (同) | 13.6px → 14.4px | -apple-system (同) | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(226, 232, 240) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G03|date|en / 1件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:213 (保留) | 342 (同) | 42 → 44 | 8px 8px 8px 8px → 8px 12px 8px 12px | 1px/solid/rgb(226, 232, 240) (同) | 6px (同) | 13.6px → 14.4px | -apple-system (同) | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(226, 232, 240) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | 149 (同) | 19 → 44 | 0px 0px 0px 0px → 8px 12px 8px 12px | 2px/inset/rgb(118, 118, 118) → 1px/solid/rgb(226, 232, 240) | 0px → 6px | 13.3333px → 14.4px | Arial → -apple-system | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(118, 118, 118) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G06|text|en / 3件 / features/tcg-distribution/DistributionTargetForm.tsx:182 | 342 (同) | 40 → 44 | 8px 12px 8px 12px (同) | 1px/solid/rgb(226, 232, 240) (同) | 6px (同) | 13.6px → 14.4px | -apple-system (同) | rgb(26, 32, 44) (同) | rgb(255, 255, 255) (同) | solid/none/rgb(30, 58, 138) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | 375 (同) | 30 → 44 | 6.4px 9.6px 6.4px 9.6px → 8px 12px 8px 12px | 1px/solid/rgb(204, 204, 204) → 1px/solid/rgb(226, 232, 240) | 4px → 6px | 13.6px → 14.4px | Arial → -apple-system | rgb(26, 32, 44) (同) | rgb(245, 247, 250) → rgb(255, 255, 255) | auto/none/rgb(204, 204, 204) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | 149 → 375 | 19 → 44 | 0px 0px 0px 0px → 8px 12px 8px 12px | 2px/inset/rgb(118, 118, 118) → 1px/solid/rgb(226, 232, 240) | 0px → 6px | 13.3333px → 14.4px | Arial → -apple-system | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(118, 118, 118) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | 149 → 339 | 19 → 44 | 0px 0px 0px 0px → 8px 12px 8px 12px | 2px/inset/rgb(118, 118, 118) → 1px/solid/rgb(226, 232, 240) | 0px → 6px | 13.3333px → 14.4px | Arial → -apple-system | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(118, 118, 118) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | 90 → 371 | 19 → 44 | 0px 0px 0px 0px → 8px 12px 8px 12px | 2px/inset/rgb(118, 118, 118) → 1px/solid/rgb(226, 232, 240) | 0px → 6px | 13.3333px → 14.4px | Arial → -apple-system | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(118, 118, 118) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | 60 → 371 | 19 → 44 | 0px 0px 0px 0px → 8px 12px 8px 12px | 2px/inset/rgb(118, 118, 118) → 1px/solid/rgb(226, 232, 240) | 0px → 6px | 13.3333px → 14.4px | Arial → -apple-system | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(118, 118, 118) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | 280 → 192 | 36 → 44 | 0px 0px 0px 0px → 8px 12px 8px 12px | 2px/inset/rgb(118, 118, 118) → 1px/solid/rgb(226, 232, 240) | 0px → 6px | 13.3333px → 14.4px | Arial → -apple-system | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(118, 118, 118) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | 160 → 192 | 36 → 44 | 0px 0px 0px 0px → 8px 12px 8px 12px | 2px/inset/rgb(118, 118, 118) → 1px/solid/rgb(226, 232, 240) | 0px → 6px | 13.3333px → 14.4px | Arial → -apple-system | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(118, 118, 118) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G26|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:157 | 343 (同) | 33 → 44 | 8px 12px 8px 12px (同) | 1px/solid/rgb(226, 232, 240) (同) | 6px (同) | 13.6px → 14.4px | Arial → -apple-system | rgb(26, 32, 44) (同) | rgb(245, 247, 250) → rgb(255, 255, 255) | none/none/rgb(30, 58, 138) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G27|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:230 | 273 (同) | 44 (同) | 8px 12px 8px 12px (同) | 1px/solid/rgb(226, 232, 240) (同) | 6px (同) | 13.6px → 14.4px | Arial → -apple-system | rgb(26, 32, 44) (同) | rgb(245, 247, 250) → rgb(255, 255, 255) | none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G28|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:334 | 333 (同) | 44 (同) | 8px 12px 8px 12px (同) | 1px/solid/rgb(226, 232, 240) (同) | 6px (同) | 13.6px → 14.4px | Arial → -apple-system | rgb(26, 32, 44) (同) | rgb(245, 247, 250) → rgb(255, 255, 255) | none/none/rgb(30, 58, 138) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | 209 → 363 | 21 → 44 | 0px 0px 0px 0px → 8px 12px 8px 12px | 2px/inset/rgb(118, 118, 118) → 1px/solid/rgb(226, 232, 240) | 0px → 6px | 13.3333px → 14.4px | monospace → "SF Pro Text" | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(118, 118, 118) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | 96 → 375 | 19 → 44 | 0px 0px 0px 0px → 8px 12px 8px 12px | 2px/inset/rgb(118, 118, 118) → 1px/solid/rgb(226, 232, 240) | 0px → 6px | 13.3333px → 14.4px | Arial → -apple-system | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(118, 118, 118) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | 112 → 375 | 19 → 44 | 0px 0px 0px 0px → 8px 12px 8px 12px | 2px/inset/rgb(118, 118, 118) → 1px/solid/rgb(226, 232, 240) | 0px → 6px | 13.3333px → 14.4px | Arial → -apple-system | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(118, 118, 118) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | 280 → 192 | 36 → 44 | 0px 0px 0px 0px → 8px 12px 8px 12px | 2px/inset/rgb(118, 118, 118) → 1px/solid/rgb(226, 232, 240) | 0px → 6px | 13.3333px → 14.4px | Arial → -apple-system | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(118, 118, 118) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | 343 (同) | 19 → 44 | 0px 0px 0px 0px → 8px 12px 8px 12px | 2px/inset/rgb(118, 118, 118) → 1px/solid/rgb(226, 232, 240) | 0px → 6px | 13.3333px → 14.4px | Arial → -apple-system | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(118, 118, 118) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | 343 (同) | 19 → 44 | 0px 0px 0px 0px → 8px 12px 8px 12px | 2px/inset/rgb(118, 118, 118) → 1px/solid/rgb(226, 232, 240) | 0px → 6px | 13.6px → 14.4px | Arial → -apple-system | rgb(74, 85, 104) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(118, 118, 118) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | 80 → 343 | 19 → 44 | 0px 0px 0px 0px → 8px 12px 8px 12px | 2px/inset/rgb(118, 118, 118) → 1px/solid/rgb(226, 232, 240) | 0px → 6px | 13.3333px → 14.4px | Arial → -apple-system | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(118, 118, 118) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | 70 → 343 | 19 → 44 | 0px 0px 0px 0px → 8px 12px 8px 12px | 2px/inset/rgb(118, 118, 118) → 1px/solid/rgb(226, 232, 240) | 0px → 6px | 13.3333px → 14.4px | Arial → -apple-system | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(118, 118, 118) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | 90 → 343 | 19 → 44 | 0px 0px 0px 0px → 8px 12px 8px 12px | 2px/inset/rgb(118, 118, 118) → 1px/solid/rgb(226, 232, 240) | 0px → 6px | 13.3333px → 14.4px | Arial → -apple-system | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(118, 118, 118) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | 80 → 343 | 19 → 44 | 0px 0px 0px 0px → 8px 12px 8px 12px | 2px/inset/rgb(118, 118, 118) → 1px/solid/rgb(226, 232, 240) | 0px → 6px | 13.3333px → 14.4px | Arial → -apple-system | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(118, 118, 118) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | 163 → 375 | 33 → 44 | 8px 8px 8px 8px → 8px 12px 8px 12px | 1px/solid/rgb(226, 232, 240) (同) | 4px → 6px | 13.6px → 14.4px | Arial → -apple-system | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(226, 232, 240) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G30|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:290 | 375 (同) | 33 → 44 | 8px 8px 8px 8px → 8px 12px 8px 12px | 1px/solid/rgb(226, 232, 240) (同) | 4px → 6px | 13.3333px → 14.4px | Arial → -apple-system | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(226, 232, 240) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G02|omitted|en / 5件 / pages/products/ProductEditPage.tsx:215 (保留) | 343 (同) | 34 → 44 | 8px 12px 8px 12px (同) | 1px/solid/rgb(203, 213, 224) → 1px/solid/rgb(226, 232, 240) | 4px → 6px | 14.4px (同) | Arial → -apple-system | rgb(26, 32, 44) (同) | rgb(255, 255, 255) (同) | none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(203, 213, 224) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G02|date|en / 1件 / pages/products/ProductEditPage.tsx:262 (保留) | 343 (同) | 37 → 44 | 8px 12px 8px 12px (同) | 1px/solid/rgb(203, 213, 224) → 1px/solid/rgb(226, 232, 240) | 4px → 6px | 14.4px (同) | monospace → -apple-system | rgb(26, 32, 44) (同) | rgb(255, 255, 255) (同) | none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(203, 213, 224) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G02|number|en / 7件 / pages/products/ProductEditPage.tsx:294 (保留) | 343 (同) | 34 → 44 | 8px 12px 8px 12px (同) | 1px/solid/rgb(203, 213, 224) → 1px/solid/rgb(226, 232, 240) | 4px → 6px | 14.4px (同) | Arial → -apple-system | rgb(26, 32, 44) (同) | rgb(255, 255, 255) (同) | none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(203, 213, 224) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G02|url|en / 1件 / pages/products/ProductEditPage.tsx:298 (保留) | 343 (同) | 34 → 44 | 8px 12px 8px 12px (同) | 1px/solid/rgb(203, 213, 224) → 1px/solid/rgb(226, 232, 240) | 4px → 6px | 14.4px (同) | Arial → -apple-system | rgb(26, 32, 44) (同) | rgb(255, 255, 255) (同) | none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(203, 213, 224) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | 149 → 347 | 19 → 44 | 0px 0px 0px 0px → 8px 12px 8px 12px | 2px/inset/rgb(118, 118, 118) → 1px/solid/rgb(226, 232, 240) | 0px → 6px | 13.3333px → 14.4px | Arial → -apple-system | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(118, 118, 118) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | 149 → 347 | 19 → 44 | 0px 0px 0px 0px → 8px 12px 8px 12px | 2px/inset/rgb(118, 118, 118) → 1px/solid/rgb(226, 232, 240) | 0px → 6px | 13.3333px → 14.4px | Arial → -apple-system | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(118, 118, 118) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | 149 → 347 | 19 → 44 | 0px 0px 0px 0px → 8px 12px 8px 12px | 2px/inset/rgb(118, 118, 118) → 1px/solid/rgb(226, 232, 240) | 0px → 6px | 13.3333px → 14.4px | Arial → -apple-system | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(118, 118, 118) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | 149 → 347 | 19 → 44 | 0px 0px 0px 0px → 8px 12px 8px 12px | 2px/inset/rgb(118, 118, 118) → 1px/solid/rgb(226, 232, 240) | 0px → 6px | 13.3333px → 14.4px | Arial → -apple-system | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(118, 118, 118) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | 327 (同) | 19 → 44 | 0px 0px 0px 0px → 8px 12px 8px 12px | 2px/inset/rgb(118, 118, 118) → 1px/solid/rgb(226, 232, 240) | 0px → 6px | 13.3333px → 14.4px | Arial → -apple-system | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(118, 118, 118) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |
| G32|number|en / 1件 / pages/super-admin/TcgLineImportPage.tsx:353 | 80 → 375 | 30 → 44 | 6.4px 9.6px 6.4px 9.6px → 8px 12px 8px 12px | 1px/solid/rgb(204, 204, 204) → 1px/solid/rgb(226, 232, 240) | 4px → 6px | 13.6px → 14.4px | Arial → -apple-system | rgb(26, 32, 44) (同) | rgb(245, 247, 250) → rgb(255, 255, 255) | none/none/rgb(204, 204, 204) → none/none/rgb(226, 232, 240) |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | 200 → 375 | 30 → 44 | 6.4px 9.6px 6.4px 9.6px → 8px 12px 8px 12px | 1px/solid/rgb(204, 204, 204) → 1px/solid/rgb(226, 232, 240) | 4px → 6px | 13.6px → 14.4px | Arial → -apple-system | rgb(26, 32, 44) (同) | rgb(245, 247, 250) → rgb(255, 255, 255) | none/none/rgb(204, 204, 204) → none/none/rgb(226, 232, 240) |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | 80 → 327 | 25 → 44 | 4px 8px 4px 8px → 8px 12px 8px 12px | 1px/solid/rgb(226, 232, 240) (同) | 4px → 6px | 13.3333px → 14.4px | Arial → -apple-system | rgb(0, 0, 0) → rgb(26, 32, 44) | rgb(255, 255, 255) (同) | auto/none/rgb(226, 232, 240) → none/rgba(30, 58, 138, 0.15) 0px 0px 0px 3px/rgb(30, 58, 138) |

## 詳細（差のあるプロパティのみ）

### 幅 1280

| 代表（group|type|disabled / 件数 / file:line） | 状態 | プロパティ | before | after |
|---|---|---|---|---|
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | normal | padding-top | 6px | 8px |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | normal | padding-right | 8px | 12px |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | normal | padding-bottom | 6px | 8px |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | normal | padding-left | 8px | 12px |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | normal | border-top-left-radius | 4px | 6px |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | normal | font-size | 13px | 14.4px |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | normal | line-height | normal | 21.6px |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | normal | height | 29px | 39.6094px |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | normal | width | 80px | 1200px |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | normal | offsetHeight | 29 | 40 |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | normal | offsetWidth | 80 | 1200 |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | focus | padding-top | 6px | 8px |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | focus | padding-right | 8px | 12px |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | focus | padding-bottom | 6px | 8px |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | focus | padding-left | 8px | 12px |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | focus | border-top-color | rgb(226, 232, 240) | rgb(30, 58, 138) |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | focus | border-top-left-radius | 4px | 6px |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | focus | font-size | 13px | 14.4px |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | focus | line-height | normal | 21.6px |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | focus | height | 29px | 39.6094px |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | focus | width | 80px | 1200px |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | focus | outline-style | auto | none |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | focus | outline-width | 1px | 3px |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | focus | offsetHeight | 29 | 40 |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | focus | offsetWidth | 80 | 1200 |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | normal | padding-top | 6px | 8px |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | normal | padding-right | 8px | 12px |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | normal | padding-bottom | 6px | 8px |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | normal | padding-left | 8px | 12px |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | normal | border-top-left-radius | 4px | 6px |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | normal | font-size | 13px | 14.4px |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | normal | line-height | normal | 21.6px |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | normal | height | 29px | 39.6094px |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | normal | width | 100px | 1200px |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | normal | offsetHeight | 29 | 40 |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | normal | offsetWidth | 100 | 1200 |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | focus | padding-top | 6px | 8px |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | focus | padding-right | 8px | 12px |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | focus | padding-bottom | 6px | 8px |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | focus | padding-left | 8px | 12px |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | focus | border-top-color | rgb(226, 232, 240) | rgb(30, 58, 138) |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | focus | border-top-left-radius | 4px | 6px |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | focus | font-size | 13px | 14.4px |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | focus | line-height | normal | 21.6px |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | focus | height | 29px | 39.6094px |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | focus | width | 100px | 1200px |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | focus | outline-style | auto | none |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | focus | outline-width | 1px | 3px |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | focus | offsetHeight | 29 | 40 |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | focus | offsetWidth | 100 | 1200 |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | normal | padding-top | 6px | 8px |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | normal | padding-right | 8px | 12px |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | normal | padding-bottom | 6px | 8px |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | normal | padding-left | 8px | 12px |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | normal | border-top-left-radius | 4px | 6px |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | normal | font-size | 13px | 14.4px |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | normal | line-height | normal | 21.6px |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | normal | height | 29px | 39.6094px |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | normal | width | 160px | 1200px |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | normal | offsetHeight | 29 | 40 |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | normal | offsetWidth | 160 | 1200 |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | focus | padding-top | 6px | 8px |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | focus | padding-right | 8px | 12px |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | focus | padding-bottom | 6px | 8px |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | focus | padding-left | 8px | 12px |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | focus | border-top-color | rgb(226, 232, 240) | rgb(30, 58, 138) |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | focus | border-top-left-radius | 4px | 6px |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | focus | font-size | 13px | 14.4px |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | focus | line-height | normal | 21.6px |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | focus | height | 29px | 39.6094px |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | focus | width | 160px | 1200px |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | focus | outline-style | auto | none |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | focus | outline-width | 1px | 3px |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | focus | offsetHeight | 29 | 40 |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | focus | offsetWidth | 160 | 1200 |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | normal | padding-top | 6px | 8px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | normal | padding-right | 8px | 12px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | normal | padding-bottom | 6px | 8px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | normal | padding-left | 8px | 12px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | normal | border-top-width | 2px | 1px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | normal | border-top-style | inset | solid |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | normal | border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | normal | border-right-width | 2px | 1px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | normal | border-bottom-width | 2px | 1px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | normal | border-left-width | 2px | 1px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | normal | border-top-left-radius | 0px | 6px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | normal | font-size | 13.3333px | 14.4px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | normal | line-height | normal | 21.6px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | normal | height | 31px | 39.6094px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | normal | width | 165px | 1280px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | normal | min-width | 120px | 0px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | normal | flex-grow | 1 | 0 |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | normal | offsetHeight | 31 | 40 |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | normal | offsetWidth | 165 | 1280 |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | focus | padding-top | 6px | 8px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | focus | padding-right | 8px | 12px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | focus | padding-bottom | 6px | 8px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | focus | padding-left | 8px | 12px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | focus | border-top-width | 2px | 1px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | focus | border-top-style | inset | solid |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | focus | border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | focus | border-right-width | 2px | 1px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | focus | border-bottom-width | 2px | 1px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | focus | border-left-width | 2px | 1px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | focus | border-top-left-radius | 0px | 6px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | focus | font-size | 13.3333px | 14.4px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | focus | line-height | normal | 21.6px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | focus | height | 31px | 39.6094px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | focus | width | 165px | 1280px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | focus | min-width | 120px | 0px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | focus | flex-grow | 1 | 0 |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | focus | outline-style | auto | none |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | focus | outline-width | 1px | 3px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | focus | offsetHeight | 31 | 40 |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | focus | offsetWidth | 165 | 1280 |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | disabled | padding-top | 6px | 8px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | disabled | padding-right | 8px | 12px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | disabled | padding-bottom | 6px | 8px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | disabled | padding-left | 8px | 12px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | disabled | border-top-width | 2px | 1px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | disabled | border-top-style | inset | solid |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | disabled | border-top-color | rgba(118, 118, 118, 0.3) | rgb(226, 232, 240) |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | disabled | border-right-width | 2px | 1px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | disabled | border-bottom-width | 2px | 1px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | disabled | border-left-width | 2px | 1px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | disabled | border-top-left-radius | 0px | 6px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | disabled | font-size | 13.3333px | 14.4px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | disabled | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | disabled | line-height | normal | 21.6px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | disabled | color | rgb(84, 84, 84) | rgb(26, 32, 44) |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | disabled | background-color | rgba(239, 239, 239, 0.3) | rgb(226, 232, 240) |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | disabled | height | 31px | 39.6094px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | disabled | width | 165px | 1280px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | disabled | min-width | 120px | 0px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | disabled | flex-grow | 1 | 0 |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | disabled | outline-color | rgb(84, 84, 84) | rgb(26, 32, 44) |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | disabled | cursor | default | not-allowed |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | disabled | opacity | 1 | 0.5 |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | disabled | offsetHeight | 31 | 40 |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | disabled | offsetWidth | 165 | 1280 |
| G09|text|en / 2件 / components/master-list-editor/MasterListEditor.tsx:135 | normal | border-top-left-radius | 4px | 6px |
| G09|text|en / 2件 / components/master-list-editor/MasterListEditor.tsx:135 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G09|text|en / 2件 / components/master-list-editor/MasterListEditor.tsx:135 | normal | line-height | normal | 21.6px |
| G09|text|en / 2件 / components/master-list-editor/MasterListEditor.tsx:135 | normal | height | 36px | 39.6094px |
| G09|text|en / 2件 / components/master-list-editor/MasterListEditor.tsx:135 | normal | min-height | 36px | 0px |
| G09|text|en / 2件 / components/master-list-editor/MasterListEditor.tsx:135 | normal | width | 280px | 192px |
| G09|text|en / 2件 / components/master-list-editor/MasterListEditor.tsx:135 | normal | min-width | 280px | 0px |
| G09|text|en / 2件 / components/master-list-editor/MasterListEditor.tsx:135 | normal | offsetHeight | 36 | 40 |
| G09|text|en / 2件 / components/master-list-editor/MasterListEditor.tsx:135 | normal | offsetWidth | 280 | 192 |
| G09|text|en / 2件 / components/master-list-editor/MasterListEditor.tsx:135 | focus | border-top-color | rgb(226, 232, 240) | rgb(30, 58, 138) |
| G09|text|en / 2件 / components/master-list-editor/MasterListEditor.tsx:135 | focus | border-top-left-radius | 4px | 6px |
| G09|text|en / 2件 / components/master-list-editor/MasterListEditor.tsx:135 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G09|text|en / 2件 / components/master-list-editor/MasterListEditor.tsx:135 | focus | line-height | normal | 21.6px |
| G09|text|en / 2件 / components/master-list-editor/MasterListEditor.tsx:135 | focus | height | 36px | 39.6094px |
| G09|text|en / 2件 / components/master-list-editor/MasterListEditor.tsx:135 | focus | min-height | 36px | 0px |
| G09|text|en / 2件 / components/master-list-editor/MasterListEditor.tsx:135 | focus | width | 280px | 192px |
| G09|text|en / 2件 / components/master-list-editor/MasterListEditor.tsx:135 | focus | min-width | 280px | 0px |
| G09|text|en / 2件 / components/master-list-editor/MasterListEditor.tsx:135 | focus | outline-style | auto | none |
| G09|text|en / 2件 / components/master-list-editor/MasterListEditor.tsx:135 | focus | outline-width | 1px | 3px |
| G09|text|en / 2件 / components/master-list-editor/MasterListEditor.tsx:135 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G09|text|en / 2件 / components/master-list-editor/MasterListEditor.tsx:135 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G09|text|en / 2件 / components/master-list-editor/MasterListEditor.tsx:135 | focus | offsetHeight | 36 | 40 |
| G09|text|en / 2件 / components/master-list-editor/MasterListEditor.tsx:135 | focus | offsetWidth | 280 | 192 |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | normal | padding-top | 0px | 8px |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | normal | padding-right | 0px | 12px |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | normal | padding-bottom | 0px | 8px |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | normal | padding-left | 0px | 12px |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | normal | border-top-width | 2px | 1px |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | normal | border-top-style | inset | solid |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | normal | border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | normal | border-right-width | 2px | 1px |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | normal | border-bottom-width | 2px | 1px |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | normal | border-left-width | 2px | 1px |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | normal | border-top-left-radius | 0px | 6px |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | normal | font-size | 13.3333px | 14.4px |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | normal | line-height | normal | 21.6px |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | normal | height | 19px | 39.6094px |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | normal | width | 149px | 1280px |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | normal | offsetHeight | 19 | 40 |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | normal | offsetWidth | 149 | 1280 |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | focus | padding-top | 0px | 8px |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | focus | padding-right | 0px | 12px |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | focus | padding-bottom | 0px | 8px |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | focus | padding-left | 0px | 12px |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | focus | border-top-width | 2px | 1px |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | focus | border-top-style | inset | solid |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | focus | border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | focus | border-right-width | 2px | 1px |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | focus | border-bottom-width | 2px | 1px |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | focus | border-left-width | 2px | 1px |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | focus | border-top-left-radius | 0px | 6px |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | focus | font-size | 13.3333px | 14.4px |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | focus | line-height | normal | 21.6px |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | focus | height | 19px | 39.6094px |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | focus | width | 149px | 1280px |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | focus | outline-style | auto | none |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | focus | outline-width | 1px | 3px |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | focus | offsetHeight | 19 | 40 |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | focus | offsetWidth | 149 | 1280 |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | normal | padding-top | 0px | 8px |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | normal | padding-right | 0px | 12px |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | normal | padding-bottom | 0px | 8px |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | normal | padding-left | 0px | 12px |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | normal | border-top-width | 2px | 1px |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | normal | border-top-style | inset | solid |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | normal | border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | normal | border-right-width | 2px | 1px |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | normal | border-bottom-width | 2px | 1px |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | normal | border-left-width | 2px | 1px |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | normal | border-top-left-radius | 0px | 6px |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | normal | font-size | 13.3333px | 14.4px |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | normal | line-height | normal | 21.6px |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | normal | height | 23px | 39.6094px |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | normal | offsetHeight | 23 | 40 |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | focus | padding-top | 0px | 8px |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | focus | padding-right | 0px | 12px |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | focus | padding-bottom | 0px | 8px |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | focus | padding-left | 0px | 12px |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | focus | border-top-width | 2px | 1px |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | focus | border-top-style | inset | solid |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | focus | border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | focus | border-right-width | 2px | 1px |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | focus | border-bottom-width | 2px | 1px |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | focus | border-left-width | 2px | 1px |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | focus | border-top-left-radius | 0px | 6px |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | focus | font-size | 13.3333px | 14.4px |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | focus | line-height | normal | 21.6px |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | focus | height | 23px | 39.6094px |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | focus | outline-style | auto | none |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | focus | outline-width | 1px | 3px |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | focus | offsetHeight | 23 | 40 |
| G03|omitted|en / 6件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:68 (保留) | normal | padding-right | 8px | 12px |
| G03|omitted|en / 6件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:68 (保留) | normal | padding-left | 8px | 12px |
| G03|omitted|en / 6件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:68 (保留) | normal | font-size | 13.6px | 14.4px |
| G03|omitted|en / 6件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:68 (保留) | normal | font-weight | 500 | 400 |
| G03|omitted|en / 6件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:68 (保留) | normal | line-height | 21.76px | 21.6px |
| G03|omitted|en / 6件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:68 (保留) | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G03|omitted|en / 6件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:68 (保留) | normal | height | 39.75px | 39.6094px |
| G03|omitted|en / 6件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:68 (保留) | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G03|omitted|en / 6件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:68 (保留) | focus | padding-right | 8px | 12px |
| G03|omitted|en / 6件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:68 (保留) | focus | padding-left | 8px | 12px |
| G03|omitted|en / 6件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:68 (保留) | focus | border-top-color | rgb(226, 232, 240) | rgb(30, 58, 138) |
| G03|omitted|en / 6件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:68 (保留) | focus | font-size | 13.6px | 14.4px |
| G03|omitted|en / 6件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:68 (保留) | focus | font-weight | 500 | 400 |
| G03|omitted|en / 6件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:68 (保留) | focus | line-height | 21.76px | 21.6px |
| G03|omitted|en / 6件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:68 (保留) | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G03|omitted|en / 6件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:68 (保留) | focus | height | 39.75px | 39.6094px |
| G03|omitted|en / 6件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:68 (保留) | focus | outline-style | auto | none |
| G03|omitted|en / 6件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:68 (保留) | focus | outline-width | 1px | 3px |
| G03|omitted|en / 6件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:68 (保留) | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G03|omitted|en / 6件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:68 (保留) | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G03|date|en / 1件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:213 (保留) | normal | padding-right | 8px | 12px |
| G03|date|en / 1件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:213 (保留) | normal | padding-left | 8px | 12px |
| G03|date|en / 1件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:213 (保留) | normal | font-size | 13.6px | 14.4px |
| G03|date|en / 1件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:213 (保留) | normal | font-weight | 500 | 400 |
| G03|date|en / 1件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:213 (保留) | normal | line-height | 21.76px | 21.6px |
| G03|date|en / 1件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:213 (保留) | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G03|date|en / 1件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:213 (保留) | normal | height | 41.75px | 41.6094px |
| G03|date|en / 1件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:213 (保留) | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G03|date|en / 1件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:213 (保留) | focus | padding-right | 8px | 12px |
| G03|date|en / 1件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:213 (保留) | focus | padding-left | 8px | 12px |
| G03|date|en / 1件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:213 (保留) | focus | border-top-color | rgb(226, 232, 240) | rgb(30, 58, 138) |
| G03|date|en / 1件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:213 (保留) | focus | font-size | 13.6px | 14.4px |
| G03|date|en / 1件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:213 (保留) | focus | font-weight | 500 | 400 |
| G03|date|en / 1件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:213 (保留) | focus | line-height | 21.76px | 21.6px |
| G03|date|en / 1件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:213 (保留) | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G03|date|en / 1件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:213 (保留) | focus | height | 41.75px | 41.6094px |
| G03|date|en / 1件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:213 (保留) | focus | outline-style | auto | none |
| G03|date|en / 1件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:213 (保留) | focus | outline-width | 1px | 3px |
| G03|date|en / 1件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:213 (保留) | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G03|date|en / 1件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:213 (保留) | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | normal | padding-top | 0px | 8px |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | normal | padding-right | 0px | 12px |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | normal | padding-bottom | 0px | 8px |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | normal | padding-left | 0px | 12px |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | normal | border-top-width | 2px | 1px |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | normal | border-top-style | inset | solid |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | normal | border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | normal | border-right-width | 2px | 1px |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | normal | border-bottom-width | 2px | 1px |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | normal | border-left-width | 2px | 1px |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | normal | border-top-left-radius | 0px | 6px |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | normal | font-size | 13.3333px | 14.4px |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | normal | line-height | normal | 21.6px |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | normal | height | 19px | 39.6094px |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | normal | width | 149px | 187.391px |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | normal | min-width | 0px | auto |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | normal | offsetHeight | 19 | 40 |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | normal | offsetWidth | 149 | 187 |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | focus | padding-top | 0px | 8px |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | focus | padding-right | 0px | 12px |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | focus | padding-bottom | 0px | 8px |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | focus | padding-left | 0px | 12px |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | focus | border-top-width | 2px | 1px |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | focus | border-top-style | inset | solid |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | focus | border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | focus | border-right-width | 2px | 1px |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | focus | border-bottom-width | 2px | 1px |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | focus | border-left-width | 2px | 1px |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | focus | border-top-left-radius | 0px | 6px |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | focus | font-size | 13.3333px | 14.4px |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | focus | line-height | normal | 21.6px |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | focus | height | 19px | 39.6094px |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | focus | width | 149px | 187.391px |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | focus | min-width | 0px | auto |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | focus | outline-style | auto | none |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | focus | outline-width | 1px | 3px |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | focus | offsetHeight | 19 | 40 |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | focus | offsetWidth | 149 | 187 |
| G06|text|en / 3件 / features/tcg-distribution/DistributionTargetForm.tsx:182 | normal | font-size | 13.6px | 14.4px |
| G06|text|en / 3件 / features/tcg-distribution/DistributionTargetForm.tsx:182 | normal | line-height | 21.76px | 21.6px |
| G06|text|en / 3件 / features/tcg-distribution/DistributionTargetForm.tsx:182 | normal | height | 39.75px | 39.6094px |
| G06|text|en / 3件 / features/tcg-distribution/DistributionTargetForm.tsx:182 | focus | font-size | 13.6px | 14.4px |
| G06|text|en / 3件 / features/tcg-distribution/DistributionTargetForm.tsx:182 | focus | line-height | 21.76px | 21.6px |
| G06|text|en / 3件 / features/tcg-distribution/DistributionTargetForm.tsx:182 | focus | height | 39.75px | 39.6094px |
| G06|text|en / 3件 / features/tcg-distribution/DistributionTargetForm.tsx:182 | focus | outline-style | solid | none |
| G06|text|en / 3件 / features/tcg-distribution/DistributionTargetForm.tsx:182 | focus | outline-width | 2px | 3px |
| G06|text|en / 3件 / features/tcg-distribution/DistributionTargetForm.tsx:182 | focus | outline-color | rgb(30, 58, 138) | rgb(26, 32, 44) |
| G06|text|en / 3件 / features/tcg-distribution/DistributionTargetForm.tsx:182 | focus | outline-offset | -1px | 0px |
| G06|text|en / 3件 / features/tcg-distribution/DistributionTargetForm.tsx:182 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | normal | padding-top | 6.4px | 8px |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | normal | padding-right | 9.6px | 12px |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | normal | padding-bottom | 6.4px | 8px |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | normal | padding-left | 9.6px | 12px |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | normal | border-top-color | rgb(204, 204, 204) | rgb(226, 232, 240) |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | normal | border-top-left-radius | 4px | 6px |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | normal | font-size | 13.6px | 14.4px |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | normal | line-height | normal | 21.6px |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | normal | background-color | rgb(245, 247, 250) | rgb(255, 255, 255) |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | normal | height | 29.7812px | 39.6094px |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | normal | margin-bottom | 8px | 0px |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | normal | offsetHeight | 30 | 40 |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | focus | padding-top | 6.4px | 8px |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | focus | padding-right | 9.6px | 12px |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | focus | padding-bottom | 6.4px | 8px |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | focus | padding-left | 9.6px | 12px |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | focus | border-top-color | rgb(204, 204, 204) | rgb(30, 58, 138) |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | focus | border-top-left-radius | 4px | 6px |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | focus | font-size | 13.6px | 14.4px |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | focus | line-height | normal | 21.6px |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | focus | background-color | rgb(245, 247, 250) | rgb(255, 255, 255) |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | focus | height | 29.7812px | 39.6094px |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | focus | margin-bottom | 8px | 0px |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | focus | outline-style | auto | none |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | focus | outline-width | 1px | 3px |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | focus | offsetHeight | 30 | 40 |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | normal | padding-top | 0px | 8px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | normal | padding-right | 0px | 12px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | normal | padding-bottom | 0px | 8px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | normal | padding-left | 0px | 12px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | normal | border-top-width | 2px | 1px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | normal | border-top-style | inset | solid |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | normal | border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | normal | border-right-width | 2px | 1px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | normal | border-bottom-width | 2px | 1px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | normal | border-left-width | 2px | 1px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | normal | border-top-left-radius | 0px | 6px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | normal | font-size | 13.3333px | 14.4px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | normal | line-height | normal | 21.6px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | normal | height | 19px | 39.6094px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | normal | width | 149px | 1280px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | normal | offsetHeight | 19 | 40 |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | normal | offsetWidth | 149 | 1280 |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | focus | padding-top | 0px | 8px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | focus | padding-right | 0px | 12px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | focus | padding-bottom | 0px | 8px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | focus | padding-left | 0px | 12px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | focus | border-top-width | 2px | 1px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | focus | border-top-style | inset | solid |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | focus | border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | focus | border-right-width | 2px | 1px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | focus | border-bottom-width | 2px | 1px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | focus | border-left-width | 2px | 1px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | focus | border-top-left-radius | 0px | 6px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | focus | font-size | 13.3333px | 14.4px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | focus | line-height | normal | 21.6px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | focus | height | 19px | 39.6094px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | focus | width | 149px | 1280px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | focus | outline-style | auto | none |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | focus | outline-width | 1px | 3px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | focus | offsetHeight | 19 | 40 |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | focus | offsetWidth | 149 | 1280 |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | disabled | padding-top | 0px | 8px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | disabled | padding-right | 0px | 12px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | disabled | padding-bottom | 0px | 8px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | disabled | padding-left | 0px | 12px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | disabled | border-top-width | 2px | 1px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | disabled | border-top-style | inset | solid |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | disabled | border-top-color | rgba(118, 118, 118, 0.3) | rgb(226, 232, 240) |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | disabled | border-right-width | 2px | 1px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | disabled | border-bottom-width | 2px | 1px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | disabled | border-left-width | 2px | 1px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | disabled | border-top-left-radius | 0px | 6px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | disabled | font-size | 13.3333px | 14.4px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | disabled | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | disabled | line-height | normal | 21.6px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | disabled | color | rgb(84, 84, 84) | rgb(26, 32, 44) |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | disabled | background-color | rgba(239, 239, 239, 0.3) | rgb(226, 232, 240) |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | disabled | height | 19px | 39.6094px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | disabled | width | 149px | 1280px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | disabled | outline-color | rgb(84, 84, 84) | rgb(26, 32, 44) |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | disabled | cursor | default | not-allowed |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | disabled | opacity | 1 | 0.5 |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | disabled | offsetHeight | 19 | 40 |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | disabled | offsetWidth | 149 | 1280 |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | normal | padding-top | 0px | 8px |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | normal | padding-right | 0px | 12px |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | normal | padding-bottom | 0px | 8px |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | normal | padding-left | 0px | 12px |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | normal | border-top-width | 2px | 1px |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | normal | border-top-style | inset | solid |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | normal | border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | normal | border-right-width | 2px | 1px |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | normal | border-bottom-width | 2px | 1px |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | normal | border-left-width | 2px | 1px |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | normal | border-top-left-radius | 0px | 6px |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | normal | font-size | 13.3333px | 14.4px |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | normal | line-height | normal | 21.6px |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | normal | height | 19px | 39.6094px |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | normal | width | 149px | 1244px |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | normal | offsetHeight | 19 | 40 |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | normal | offsetWidth | 149 | 1244 |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | focus | padding-top | 0px | 8px |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | focus | padding-right | 0px | 12px |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | focus | padding-bottom | 0px | 8px |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | focus | padding-left | 0px | 12px |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | focus | border-top-width | 2px | 1px |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | focus | border-top-style | inset | solid |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | focus | border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | focus | border-right-width | 2px | 1px |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | focus | border-bottom-width | 2px | 1px |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | focus | border-left-width | 2px | 1px |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | focus | border-top-left-radius | 0px | 6px |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | focus | font-size | 13.3333px | 14.4px |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | focus | line-height | normal | 21.6px |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | focus | height | 19px | 39.6094px |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | focus | width | 149px | 1244px |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | focus | outline-style | auto | none |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | focus | outline-width | 1px | 3px |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | focus | offsetHeight | 19 | 40 |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | focus | offsetWidth | 149 | 1244 |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | normal | padding-top | 0px | 8px |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | normal | padding-right | 0px | 12px |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | normal | padding-bottom | 0px | 8px |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | normal | padding-left | 0px | 12px |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | normal | border-top-width | 2px | 1px |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | normal | border-top-style | inset | solid |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | normal | border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | normal | border-right-width | 2px | 1px |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | normal | border-bottom-width | 2px | 1px |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | normal | border-left-width | 2px | 1px |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | normal | border-top-left-radius | 0px | 6px |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | normal | font-size | 13.3333px | 14.4px |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | normal | line-height | normal | 21.6px |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | normal | height | 19px | 39.6094px |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | normal | width | 90px | 1276px |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | normal | margin-left | 8px | 0px |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | normal | offsetHeight | 19 | 40 |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | normal | offsetWidth | 90 | 1276 |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | focus | padding-top | 0px | 8px |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | focus | padding-right | 0px | 12px |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | focus | padding-bottom | 0px | 8px |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | focus | padding-left | 0px | 12px |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | focus | border-top-width | 2px | 1px |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | focus | border-top-style | inset | solid |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | focus | border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | focus | border-right-width | 2px | 1px |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | focus | border-bottom-width | 2px | 1px |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | focus | border-left-width | 2px | 1px |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | focus | border-top-left-radius | 0px | 6px |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | focus | font-size | 13.3333px | 14.4px |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | focus | line-height | normal | 21.6px |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | focus | height | 19px | 39.6094px |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | focus | width | 90px | 1276px |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | focus | margin-left | 8px | 0px |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | focus | outline-style | auto | none |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | focus | outline-width | 1px | 3px |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | focus | offsetHeight | 19 | 40 |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | focus | offsetWidth | 90 | 1276 |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | normal | padding-top | 0px | 8px |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | normal | padding-right | 0px | 12px |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | normal | padding-bottom | 0px | 8px |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | normal | padding-left | 0px | 12px |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | normal | border-top-width | 2px | 1px |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | normal | border-top-style | inset | solid |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | normal | border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | normal | border-right-width | 2px | 1px |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | normal | border-bottom-width | 2px | 1px |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | normal | border-left-width | 2px | 1px |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | normal | border-top-left-radius | 0px | 6px |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | normal | font-size | 13.3333px | 14.4px |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | normal | line-height | normal | 21.6px |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | normal | height | 19px | 39.6094px |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | normal | width | 60px | 1276px |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | normal | margin-left | 8px | 0px |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | normal | offsetHeight | 19 | 40 |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | normal | offsetWidth | 60 | 1276 |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | focus | padding-top | 0px | 8px |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | focus | padding-right | 0px | 12px |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | focus | padding-bottom | 0px | 8px |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | focus | padding-left | 0px | 12px |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | focus | border-top-width | 2px | 1px |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | focus | border-top-style | inset | solid |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | focus | border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | focus | border-right-width | 2px | 1px |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | focus | border-bottom-width | 2px | 1px |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | focus | border-left-width | 2px | 1px |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | focus | border-top-left-radius | 0px | 6px |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | focus | font-size | 13.3333px | 14.4px |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | focus | line-height | normal | 21.6px |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | focus | height | 19px | 39.6094px |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | focus | width | 60px | 1276px |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | focus | margin-left | 8px | 0px |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | focus | outline-style | auto | none |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | focus | outline-width | 1px | 3px |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | focus | offsetHeight | 19 | 40 |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | focus | offsetWidth | 60 | 1276 |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | normal | padding-top | 0px | 8px |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | normal | padding-right | 0px | 12px |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | normal | padding-bottom | 0px | 8px |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | normal | padding-left | 0px | 12px |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | normal | border-top-width | 2px | 1px |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | normal | border-top-style | inset | solid |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | normal | border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | normal | border-right-width | 2px | 1px |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | normal | border-bottom-width | 2px | 1px |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | normal | border-left-width | 2px | 1px |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | normal | border-top-left-radius | 0px | 6px |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | normal | font-size | 13.3333px | 14.4px |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | normal | line-height | normal | 21.6px |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | normal | height | 36px | 39.6094px |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | normal | min-height | 36px | auto |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | normal | width | 280px | 192px |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | normal | offsetHeight | 36 | 40 |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | normal | offsetWidth | 280 | 192 |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | focus | padding-top | 0px | 8px |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | focus | padding-right | 0px | 12px |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | focus | padding-bottom | 0px | 8px |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | focus | padding-left | 0px | 12px |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | focus | border-top-width | 2px | 1px |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | focus | border-top-style | inset | solid |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | focus | border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | focus | border-right-width | 2px | 1px |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | focus | border-bottom-width | 2px | 1px |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | focus | border-left-width | 2px | 1px |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | focus | border-top-left-radius | 0px | 6px |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | focus | font-size | 13.3333px | 14.4px |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | focus | line-height | normal | 21.6px |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | focus | height | 36px | 39.6094px |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | focus | min-height | 36px | auto |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | focus | width | 280px | 192px |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | focus | outline-style | auto | none |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | focus | outline-width | 1px | 3px |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | focus | offsetHeight | 36 | 40 |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | focus | offsetWidth | 280 | 192 |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | normal | padding-top | 0px | 8px |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | normal | padding-right | 0px | 12px |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | normal | padding-bottom | 0px | 8px |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | normal | padding-left | 0px | 12px |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | normal | border-top-width | 2px | 1px |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | normal | border-top-style | inset | solid |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | normal | border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | normal | border-right-width | 2px | 1px |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | normal | border-bottom-width | 2px | 1px |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | normal | border-left-width | 2px | 1px |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | normal | border-top-left-radius | 0px | 6px |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | normal | font-size | 13.3333px | 14.4px |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | normal | line-height | normal | 21.6px |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | normal | height | 36px | 39.6094px |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | normal | min-height | 36px | auto |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | normal | width | 160px | 192px |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | normal | offsetHeight | 36 | 40 |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | normal | offsetWidth | 160 | 192 |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | focus | padding-top | 0px | 8px |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | focus | padding-right | 0px | 12px |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | focus | padding-bottom | 0px | 8px |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | focus | padding-left | 0px | 12px |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | focus | border-top-width | 2px | 1px |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | focus | border-top-style | inset | solid |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | focus | border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | focus | border-right-width | 2px | 1px |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | focus | border-bottom-width | 2px | 1px |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | focus | border-left-width | 2px | 1px |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | focus | border-top-left-radius | 0px | 6px |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | focus | font-size | 13.3333px | 14.4px |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | focus | line-height | normal | 21.6px |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | focus | height | 36px | 39.6094px |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | focus | min-height | 36px | auto |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | focus | width | 160px | 192px |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | focus | outline-style | auto | none |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | focus | outline-width | 1px | 3px |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | focus | offsetHeight | 36 | 40 |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | focus | offsetWidth | 160 | 192 |
| G26|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:157 | normal | font-size | 13.6px | 14.4px |
| G26|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:157 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G26|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:157 | normal | line-height | normal | 21.6px |
| G26|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:157 | normal | background-color | rgb(245, 247, 250) | rgb(255, 255, 255) |
| G26|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:157 | normal | height | 33px | 39.6094px |
| G26|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:157 | normal | offsetHeight | 33 | 40 |
| G26|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:157 | focus | font-size | 13.6px | 14.4px |
| G26|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:157 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G26|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:157 | focus | line-height | normal | 21.6px |
| G26|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:157 | focus | background-color | rgb(245, 247, 250) | rgb(255, 255, 255) |
| G26|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:157 | focus | height | 33px | 39.6094px |
| G26|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:157 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G26|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:157 | focus | offsetHeight | 33 | 40 |
| G27|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:230 | normal | font-size | 13.6px | 14.4px |
| G27|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:230 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G27|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:230 | normal | line-height | normal | 21.6px |
| G27|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:230 | normal | background-color | rgb(245, 247, 250) | rgb(255, 255, 255) |
| G27|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:230 | normal | height | 44px | 39.6094px |
| G27|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:230 | normal | min-height | 44px | auto |
| G27|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:230 | normal | offsetHeight | 44 | 40 |
| G27|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:230 | focus | font-size | 13.6px | 14.4px |
| G27|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:230 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G27|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:230 | focus | line-height | normal | 21.6px |
| G27|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:230 | focus | background-color | rgb(245, 247, 250) | rgb(255, 255, 255) |
| G27|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:230 | focus | height | 44px | 39.6094px |
| G27|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:230 | focus | min-height | 44px | auto |
| G27|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:230 | focus | offsetHeight | 44 | 40 |
| G28|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:334 | normal | font-size | 13.6px | 14.4px |
| G28|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:334 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G28|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:334 | normal | line-height | normal | 21.6px |
| G28|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:334 | normal | background-color | rgb(245, 247, 250) | rgb(255, 255, 255) |
| G28|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:334 | normal | height | 44px | 39.6094px |
| G28|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:334 | normal | min-height | 44px | auto |
| G28|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:334 | normal | offsetHeight | 44 | 40 |
| G28|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:334 | focus | font-size | 13.6px | 14.4px |
| G28|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:334 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G28|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:334 | focus | line-height | normal | 21.6px |
| G28|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:334 | focus | background-color | rgb(245, 247, 250) | rgb(255, 255, 255) |
| G28|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:334 | focus | height | 44px | 39.6094px |
| G28|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:334 | focus | min-height | 44px | auto |
| G28|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:334 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G28|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:334 | focus | offsetHeight | 44 | 40 |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | normal | padding-top | 0px | 8px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | normal | padding-right | 0px | 12px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | normal | padding-bottom | 0px | 8px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | normal | padding-left | 0px | 12px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | normal | border-top-width | 2px | 1px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | normal | border-top-style | inset | solid |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | normal | border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | normal | border-right-width | 2px | 1px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | normal | border-bottom-width | 2px | 1px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | normal | border-left-width | 2px | 1px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | normal | border-top-left-radius | 0px | 6px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | normal | font-size | 13.3333px | 14.4px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | normal | font-family | monospace | "SF Pro Text", "Segoe UI", Roboto, Helvetica, Arial, sans-serif |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | normal | line-height | normal | 21.6px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | normal | height | 21.3281px | 41.6094px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | normal | width | 209.328px | 1268px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | normal | offsetHeight | 21 | 42 |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | normal | offsetWidth | 209 | 1268 |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | focus | padding-top | 0px | 8px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | focus | padding-right | 0px | 12px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | focus | padding-bottom | 0px | 8px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | focus | padding-left | 0px | 12px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | focus | border-top-width | 2px | 1px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | focus | border-top-style | inset | solid |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | focus | border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | focus | border-right-width | 2px | 1px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | focus | border-bottom-width | 2px | 1px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | focus | border-left-width | 2px | 1px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | focus | border-top-left-radius | 0px | 6px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | focus | font-size | 13.3333px | 14.4px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | focus | font-family | monospace | "SF Pro Text", "Segoe UI", Roboto, Helvetica, Arial, sans-serif |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | focus | line-height | normal | 21.6px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | focus | height | 21.3281px | 41.6094px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | focus | width | 209.328px | 1268px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | focus | outline-style | auto | none |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | focus | outline-width | 1px | 3px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | focus | offsetHeight | 21 | 42 |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | focus | offsetWidth | 209 | 1268 |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | disabled | padding-top | 0px | 8px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | disabled | padding-right | 0px | 12px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | disabled | padding-bottom | 0px | 8px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | disabled | padding-left | 0px | 12px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | disabled | border-top-width | 2px | 1px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | disabled | border-top-style | inset | solid |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | disabled | border-top-color | rgba(118, 118, 118, 0.3) | rgb(226, 232, 240) |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | disabled | border-right-width | 2px | 1px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | disabled | border-bottom-width | 2px | 1px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | disabled | border-left-width | 2px | 1px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | disabled | border-top-left-radius | 0px | 6px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | disabled | font-size | 13.3333px | 14.4px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | disabled | font-family | monospace | "SF Pro Text", "Segoe UI", Roboto, Helvetica, Arial, sans-serif |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | disabled | line-height | normal | 21.6px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | disabled | color | rgb(84, 84, 84) | rgb(26, 32, 44) |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | disabled | background-color | rgba(239, 239, 239, 0.3) | rgb(226, 232, 240) |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | disabled | height | 21.3281px | 41.6094px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | disabled | width | 209.328px | 1268px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | disabled | outline-color | rgb(84, 84, 84) | rgb(26, 32, 44) |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | disabled | cursor | default | not-allowed |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | disabled | opacity | 1 | 0.5 |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | disabled | offsetHeight | 21 | 42 |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | disabled | offsetWidth | 209 | 1268 |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | normal | padding-top | 0px | 8px |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | normal | padding-right | 0px | 12px |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | normal | padding-bottom | 0px | 8px |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | normal | padding-left | 0px | 12px |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | normal | border-top-width | 2px | 1px |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | normal | border-top-style | inset | solid |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | normal | border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | normal | border-right-width | 2px | 1px |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | normal | border-bottom-width | 2px | 1px |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | normal | border-left-width | 2px | 1px |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | normal | border-top-left-radius | 0px | 6px |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | normal | font-size | 13.3333px | 14.4px |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | normal | line-height | normal | 21.6px |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | normal | height | 19px | 39.6094px |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | normal | width | 96px | 1280px |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | normal | offsetHeight | 19 | 40 |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | normal | offsetWidth | 96 | 1280 |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | focus | padding-top | 0px | 8px |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | focus | padding-right | 0px | 12px |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | focus | padding-bottom | 0px | 8px |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | focus | padding-left | 0px | 12px |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | focus | border-top-width | 2px | 1px |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | focus | border-top-style | inset | solid |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | focus | border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | focus | border-right-width | 2px | 1px |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | focus | border-bottom-width | 2px | 1px |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | focus | border-left-width | 2px | 1px |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | focus | border-top-left-radius | 0px | 6px |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | focus | font-size | 13.3333px | 14.4px |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | focus | line-height | normal | 21.6px |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | focus | height | 19px | 39.6094px |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | focus | width | 96px | 1280px |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | focus | outline-style | auto | none |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | focus | outline-width | 1px | 3px |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | focus | offsetHeight | 19 | 40 |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | focus | offsetWidth | 96 | 1280 |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | normal | padding-top | 0px | 8px |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | normal | padding-right | 0px | 12px |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | normal | padding-bottom | 0px | 8px |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | normal | padding-left | 0px | 12px |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | normal | border-top-width | 2px | 1px |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | normal | border-top-style | inset | solid |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | normal | border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | normal | border-right-width | 2px | 1px |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | normal | border-bottom-width | 2px | 1px |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | normal | border-left-width | 2px | 1px |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | normal | border-top-left-radius | 0px | 6px |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | normal | font-size | 13.3333px | 14.4px |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | normal | line-height | normal | 21.6px |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | normal | height | 19px | 39.6094px |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | normal | width | 112px | 1280px |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | normal | offsetHeight | 19 | 40 |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | normal | offsetWidth | 112 | 1280 |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | focus | padding-top | 0px | 8px |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | focus | padding-right | 0px | 12px |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | focus | padding-bottom | 0px | 8px |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | focus | padding-left | 0px | 12px |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | focus | border-top-width | 2px | 1px |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | focus | border-top-style | inset | solid |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | focus | border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | focus | border-right-width | 2px | 1px |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | focus | border-bottom-width | 2px | 1px |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | focus | border-left-width | 2px | 1px |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | focus | border-top-left-radius | 0px | 6px |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | focus | font-size | 13.3333px | 14.4px |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | focus | line-height | normal | 21.6px |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | focus | height | 19px | 39.6094px |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | focus | width | 112px | 1280px |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | focus | outline-style | auto | none |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | focus | outline-width | 1px | 3px |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | focus | offsetHeight | 19 | 40 |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | focus | offsetWidth | 112 | 1280 |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | normal | padding-top | 0px | 8px |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | normal | padding-right | 0px | 12px |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | normal | padding-bottom | 0px | 8px |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | normal | padding-left | 0px | 12px |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | normal | border-top-width | 2px | 1px |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | normal | border-top-style | inset | solid |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | normal | border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | normal | border-right-width | 2px | 1px |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | normal | border-bottom-width | 2px | 1px |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | normal | border-left-width | 2px | 1px |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | normal | border-top-left-radius | 0px | 6px |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | normal | font-size | 13.3333px | 14.4px |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | normal | line-height | normal | 21.6px |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | normal | height | 36px | 39.6094px |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | normal | min-height | 36px | auto |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | normal | width | 280px | 192px |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | normal | offsetHeight | 36 | 40 |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | normal | offsetWidth | 280 | 192 |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | focus | padding-top | 0px | 8px |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | focus | padding-right | 0px | 12px |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | focus | padding-bottom | 0px | 8px |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | focus | padding-left | 0px | 12px |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | focus | border-top-width | 2px | 1px |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | focus | border-top-style | inset | solid |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | focus | border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | focus | border-right-width | 2px | 1px |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | focus | border-bottom-width | 2px | 1px |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | focus | border-left-width | 2px | 1px |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | focus | border-top-left-radius | 0px | 6px |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | focus | font-size | 13.3333px | 14.4px |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | focus | line-height | normal | 21.6px |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | focus | height | 36px | 39.6094px |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | focus | min-height | 36px | auto |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | focus | width | 280px | 192px |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | focus | outline-style | auto | none |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | focus | outline-width | 1px | 3px |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | focus | offsetHeight | 36 | 40 |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | focus | offsetWidth | 280 | 192 |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | normal | padding-top | 0px | 8px |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | normal | padding-right | 0px | 12px |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | normal | padding-bottom | 0px | 8px |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | normal | padding-left | 0px | 12px |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | normal | border-top-width | 2px | 1px |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | normal | border-top-style | inset | solid |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | normal | border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | normal | border-right-width | 2px | 1px |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | normal | border-bottom-width | 2px | 1px |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | normal | border-left-width | 2px | 1px |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | normal | border-top-left-radius | 0px | 6px |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | normal | font-size | 13.3333px | 14.4px |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | normal | font-weight | 600 | 400 |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | normal | line-height | normal | 21.6px |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | normal | height | 19px | 39.6094px |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | normal | min-width | 280px | 0px |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | normal | offsetHeight | 19 | 40 |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | focus | padding-top | 0px | 8px |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | focus | padding-right | 0px | 12px |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | focus | padding-bottom | 0px | 8px |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | focus | padding-left | 0px | 12px |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | focus | border-top-width | 2px | 1px |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | focus | border-top-style | inset | solid |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | focus | border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | focus | border-right-width | 2px | 1px |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | focus | border-bottom-width | 2px | 1px |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | focus | border-left-width | 2px | 1px |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | focus | border-top-left-radius | 0px | 6px |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | focus | font-size | 13.3333px | 14.4px |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | focus | font-weight | 600 | 400 |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | focus | line-height | normal | 21.6px |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | focus | height | 19px | 39.6094px |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | focus | min-width | 280px | 0px |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | focus | outline-style | auto | none |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | focus | outline-width | 1px | 3px |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | focus | offsetHeight | 19 | 40 |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | normal | padding-top | 0px | 8px |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | normal | padding-right | 0px | 12px |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | normal | padding-bottom | 0px | 8px |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | normal | padding-left | 0px | 12px |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | normal | border-top-width | 2px | 1px |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | normal | border-top-style | inset | solid |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | normal | border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | normal | border-right-width | 2px | 1px |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | normal | border-bottom-width | 2px | 1px |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | normal | border-left-width | 2px | 1px |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | normal | border-top-left-radius | 0px | 6px |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | normal | font-size | 13.6px | 14.4px |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | normal | line-height | normal | 21.6px |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | normal | color | rgb(74, 85, 104) | rgb(26, 32, 44) |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | normal | height | 19px | 39.6094px |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | normal | min-width | 280px | 0px |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | normal | margin-top | 4px | 0px |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | normal | outline-color | rgb(74, 85, 104) | rgb(26, 32, 44) |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | normal | offsetHeight | 19 | 40 |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | focus | padding-top | 0px | 8px |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | focus | padding-right | 0px | 12px |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | focus | padding-bottom | 0px | 8px |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | focus | padding-left | 0px | 12px |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | focus | border-top-width | 2px | 1px |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | focus | border-top-style | inset | solid |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | focus | border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | focus | border-right-width | 2px | 1px |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | focus | border-bottom-width | 2px | 1px |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | focus | border-left-width | 2px | 1px |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | focus | border-top-left-radius | 0px | 6px |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | focus | font-size | 13.6px | 14.4px |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | focus | line-height | normal | 21.6px |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | focus | color | rgb(74, 85, 104) | rgb(26, 32, 44) |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | focus | height | 19px | 39.6094px |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | focus | min-width | 280px | 0px |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | focus | margin-top | 4px | 0px |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | focus | outline-style | auto | none |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | focus | outline-width | 1px | 3px |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | focus | offsetHeight | 19 | 40 |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | normal | padding-top | 0px | 8px |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | normal | padding-right | 0px | 12px |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | normal | padding-bottom | 0px | 8px |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | normal | padding-left | 0px | 12px |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | normal | border-top-width | 2px | 1px |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | normal | border-top-style | inset | solid |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | normal | border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | normal | border-right-width | 2px | 1px |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | normal | border-bottom-width | 2px | 1px |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | normal | border-left-width | 2px | 1px |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | normal | border-top-left-radius | 0px | 6px |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | normal | font-size | 13.3333px | 14.4px |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | normal | line-height | normal | 21.6px |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | normal | height | 19px | 39.6094px |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | normal | width | 80px | 1248px |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | normal | offsetHeight | 19 | 40 |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | normal | offsetWidth | 80 | 1248 |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | focus | padding-top | 0px | 8px |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | focus | padding-right | 0px | 12px |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | focus | padding-bottom | 0px | 8px |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | focus | padding-left | 0px | 12px |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | focus | border-top-width | 2px | 1px |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | focus | border-top-style | inset | solid |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | focus | border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | focus | border-right-width | 2px | 1px |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | focus | border-bottom-width | 2px | 1px |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | focus | border-left-width | 2px | 1px |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | focus | border-top-left-radius | 0px | 6px |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | focus | font-size | 13.3333px | 14.4px |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | focus | line-height | normal | 21.6px |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | focus | height | 19px | 39.6094px |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | focus | width | 80px | 1248px |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | focus | outline-style | auto | none |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | focus | outline-width | 1px | 3px |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | focus | offsetHeight | 19 | 40 |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | focus | offsetWidth | 80 | 1248 |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | normal | padding-top | 0px | 8px |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | normal | padding-right | 0px | 12px |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | normal | padding-bottom | 0px | 8px |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | normal | padding-left | 0px | 12px |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | normal | border-top-width | 2px | 1px |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | normal | border-top-style | inset | solid |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | normal | border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | normal | border-right-width | 2px | 1px |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | normal | border-bottom-width | 2px | 1px |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | normal | border-left-width | 2px | 1px |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | normal | border-top-left-radius | 0px | 6px |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | normal | font-size | 13.3333px | 14.4px |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | normal | line-height | normal | 21.6px |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | normal | height | 19px | 39.6094px |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | normal | width | 70px | 1248px |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | normal | offsetHeight | 19 | 40 |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | normal | offsetWidth | 70 | 1248 |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | focus | padding-top | 0px | 8px |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | focus | padding-right | 0px | 12px |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | focus | padding-bottom | 0px | 8px |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | focus | padding-left | 0px | 12px |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | focus | border-top-width | 2px | 1px |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | focus | border-top-style | inset | solid |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | focus | border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | focus | border-right-width | 2px | 1px |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | focus | border-bottom-width | 2px | 1px |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | focus | border-left-width | 2px | 1px |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | focus | border-top-left-radius | 0px | 6px |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | focus | font-size | 13.3333px | 14.4px |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | focus | line-height | normal | 21.6px |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | focus | height | 19px | 39.6094px |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | focus | width | 70px | 1248px |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | focus | outline-style | auto | none |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | focus | outline-width | 1px | 3px |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | focus | offsetHeight | 19 | 40 |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | focus | offsetWidth | 70 | 1248 |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | normal | padding-top | 0px | 8px |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | normal | padding-right | 0px | 12px |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | normal | padding-bottom | 0px | 8px |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | normal | padding-left | 0px | 12px |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | normal | border-top-width | 2px | 1px |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | normal | border-top-style | inset | solid |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | normal | border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | normal | border-right-width | 2px | 1px |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | normal | border-bottom-width | 2px | 1px |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | normal | border-left-width | 2px | 1px |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | normal | border-top-left-radius | 0px | 6px |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | normal | font-size | 13.3333px | 14.4px |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | normal | line-height | normal | 21.6px |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | normal | height | 19px | 39.6094px |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | normal | width | 90px | 1248px |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | normal | offsetHeight | 19 | 40 |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | normal | offsetWidth | 90 | 1248 |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | focus | padding-top | 0px | 8px |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | focus | padding-right | 0px | 12px |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | focus | padding-bottom | 0px | 8px |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | focus | padding-left | 0px | 12px |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | focus | border-top-width | 2px | 1px |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | focus | border-top-style | inset | solid |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | focus | border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | focus | border-right-width | 2px | 1px |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | focus | border-bottom-width | 2px | 1px |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | focus | border-left-width | 2px | 1px |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | focus | border-top-left-radius | 0px | 6px |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | focus | font-size | 13.3333px | 14.4px |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | focus | line-height | normal | 21.6px |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | focus | height | 19px | 39.6094px |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | focus | width | 90px | 1248px |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | focus | outline-style | auto | none |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | focus | outline-width | 1px | 3px |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | focus | offsetHeight | 19 | 40 |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | focus | offsetWidth | 90 | 1248 |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | normal | padding-top | 0px | 8px |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | normal | padding-right | 0px | 12px |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | normal | padding-bottom | 0px | 8px |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | normal | padding-left | 0px | 12px |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | normal | border-top-width | 2px | 1px |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | normal | border-top-style | inset | solid |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | normal | border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | normal | border-right-width | 2px | 1px |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | normal | border-bottom-width | 2px | 1px |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | normal | border-left-width | 2px | 1px |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | normal | border-top-left-radius | 0px | 6px |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | normal | font-size | 13.3333px | 14.4px |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | normal | line-height | normal | 21.6px |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | normal | height | 19px | 39.6094px |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | normal | width | 80px | 1248px |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | normal | offsetHeight | 19 | 40 |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | normal | offsetWidth | 80 | 1248 |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | focus | padding-top | 0px | 8px |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | focus | padding-right | 0px | 12px |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | focus | padding-bottom | 0px | 8px |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | focus | padding-left | 0px | 12px |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | focus | border-top-width | 2px | 1px |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | focus | border-top-style | inset | solid |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | focus | border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | focus | border-right-width | 2px | 1px |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | focus | border-bottom-width | 2px | 1px |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | focus | border-left-width | 2px | 1px |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | focus | border-top-left-radius | 0px | 6px |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | focus | font-size | 13.3333px | 14.4px |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | focus | line-height | normal | 21.6px |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | focus | height | 19px | 39.6094px |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | focus | width | 80px | 1248px |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | focus | outline-style | auto | none |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | focus | outline-width | 1px | 3px |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | focus | offsetHeight | 19 | 40 |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | focus | offsetWidth | 80 | 1248 |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | normal | padding-right | 8px | 12px |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | normal | padding-left | 8px | 12px |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | normal | border-top-left-radius | 4px | 6px |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | normal | font-size | 13.6px | 14.4px |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | normal | line-height | normal | 21.6px |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | normal | height | 33px | 39.6094px |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | normal | width | 163px | 1280px |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | normal | flex-grow | 1 | 0 |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | normal | offsetHeight | 33 | 40 |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | normal | offsetWidth | 163 | 1280 |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | focus | padding-right | 8px | 12px |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | focus | padding-left | 8px | 12px |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | focus | border-top-color | rgb(226, 232, 240) | rgb(30, 58, 138) |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | focus | border-top-left-radius | 4px | 6px |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | focus | font-size | 13.6px | 14.4px |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | focus | line-height | normal | 21.6px |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | focus | height | 33px | 39.6094px |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | focus | width | 163px | 1280px |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | focus | flex-grow | 1 | 0 |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | focus | outline-style | auto | none |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | focus | outline-width | 1px | 3px |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | focus | offsetHeight | 33 | 40 |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | focus | offsetWidth | 163 | 1280 |
| G30|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:290 | normal | padding-right | 8px | 12px |
| G30|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:290 | normal | padding-left | 8px | 12px |
| G30|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:290 | normal | border-top-left-radius | 4px | 6px |
| G30|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:290 | normal | font-size | 13.3333px | 14.4px |
| G30|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:290 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G30|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:290 | normal | line-height | normal | 21.6px |
| G30|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:290 | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G30|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:290 | normal | height | 33px | 39.6094px |
| G30|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:290 | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G30|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:290 | normal | offsetHeight | 33 | 40 |
| G30|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:290 | focus | padding-right | 8px | 12px |
| G30|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:290 | focus | padding-left | 8px | 12px |
| G30|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:290 | focus | border-top-color | rgb(226, 232, 240) | rgb(30, 58, 138) |
| G30|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:290 | focus | border-top-left-radius | 4px | 6px |
| G30|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:290 | focus | font-size | 13.3333px | 14.4px |
| G30|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:290 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G30|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:290 | focus | line-height | normal | 21.6px |
| G30|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:290 | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G30|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:290 | focus | height | 33px | 39.6094px |
| G30|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:290 | focus | outline-style | auto | none |
| G30|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:290 | focus | outline-width | 1px | 3px |
| G30|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:290 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G30|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:290 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G30|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:290 | focus | offsetHeight | 33 | 40 |
| G02|omitted|en / 5件 / pages/products/ProductEditPage.tsx:215 (保留) | normal | border-top-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| G02|omitted|en / 5件 / pages/products/ProductEditPage.tsx:215 (保留) | normal | border-top-left-radius | 4px | 6px |
| G02|omitted|en / 5件 / pages/products/ProductEditPage.tsx:215 (保留) | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G02|omitted|en / 5件 / pages/products/ProductEditPage.tsx:215 (保留) | normal | line-height | normal | 21.6px |
| G02|omitted|en / 5件 / pages/products/ProductEditPage.tsx:215 (保留) | normal | height | 34px | 39.6094px |
| G02|omitted|en / 5件 / pages/products/ProductEditPage.tsx:215 (保留) | normal | offsetHeight | 34 | 40 |
| G02|omitted|en / 5件 / pages/products/ProductEditPage.tsx:215 (保留) | focus | border-top-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| G02|omitted|en / 5件 / pages/products/ProductEditPage.tsx:215 (保留) | focus | border-top-left-radius | 4px | 6px |
| G02|omitted|en / 5件 / pages/products/ProductEditPage.tsx:215 (保留) | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G02|omitted|en / 5件 / pages/products/ProductEditPage.tsx:215 (保留) | focus | line-height | normal | 21.6px |
| G02|omitted|en / 5件 / pages/products/ProductEditPage.tsx:215 (保留) | focus | height | 34px | 39.6094px |
| G02|omitted|en / 5件 / pages/products/ProductEditPage.tsx:215 (保留) | focus | offsetHeight | 34 | 40 |
| G02|date|en / 1件 / pages/products/ProductEditPage.tsx:262 (保留) | normal | border-top-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| G02|date|en / 1件 / pages/products/ProductEditPage.tsx:262 (保留) | normal | border-top-left-radius | 4px | 6px |
| G02|date|en / 1件 / pages/products/ProductEditPage.tsx:262 (保留) | normal | font-family | monospace | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G02|date|en / 1件 / pages/products/ProductEditPage.tsx:262 (保留) | normal | line-height | normal | 21.6px |
| G02|date|en / 1件 / pages/products/ProductEditPage.tsx:262 (保留) | normal | height | 37px | 41.6094px |
| G02|date|en / 1件 / pages/products/ProductEditPage.tsx:262 (保留) | normal | offsetHeight | 37 | 42 |
| G02|date|en / 1件 / pages/products/ProductEditPage.tsx:262 (保留) | focus | border-top-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| G02|date|en / 1件 / pages/products/ProductEditPage.tsx:262 (保留) | focus | border-top-left-radius | 4px | 6px |
| G02|date|en / 1件 / pages/products/ProductEditPage.tsx:262 (保留) | focus | font-family | monospace | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G02|date|en / 1件 / pages/products/ProductEditPage.tsx:262 (保留) | focus | line-height | normal | 21.6px |
| G02|date|en / 1件 / pages/products/ProductEditPage.tsx:262 (保留) | focus | height | 37px | 41.6094px |
| G02|date|en / 1件 / pages/products/ProductEditPage.tsx:262 (保留) | focus | offsetHeight | 37 | 42 |
| G02|number|en / 7件 / pages/products/ProductEditPage.tsx:294 (保留) | normal | border-top-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| G02|number|en / 7件 / pages/products/ProductEditPage.tsx:294 (保留) | normal | border-top-left-radius | 4px | 6px |
| G02|number|en / 7件 / pages/products/ProductEditPage.tsx:294 (保留) | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G02|number|en / 7件 / pages/products/ProductEditPage.tsx:294 (保留) | normal | line-height | normal | 21.6px |
| G02|number|en / 7件 / pages/products/ProductEditPage.tsx:294 (保留) | normal | height | 34px | 39.6094px |
| G02|number|en / 7件 / pages/products/ProductEditPage.tsx:294 (保留) | normal | offsetHeight | 34 | 40 |
| G02|number|en / 7件 / pages/products/ProductEditPage.tsx:294 (保留) | focus | border-top-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| G02|number|en / 7件 / pages/products/ProductEditPage.tsx:294 (保留) | focus | border-top-left-radius | 4px | 6px |
| G02|number|en / 7件 / pages/products/ProductEditPage.tsx:294 (保留) | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G02|number|en / 7件 / pages/products/ProductEditPage.tsx:294 (保留) | focus | line-height | normal | 21.6px |
| G02|number|en / 7件 / pages/products/ProductEditPage.tsx:294 (保留) | focus | height | 34px | 39.6094px |
| G02|number|en / 7件 / pages/products/ProductEditPage.tsx:294 (保留) | focus | offsetHeight | 34 | 40 |
| G02|url|en / 1件 / pages/products/ProductEditPage.tsx:298 (保留) | normal | border-top-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| G02|url|en / 1件 / pages/products/ProductEditPage.tsx:298 (保留) | normal | border-top-left-radius | 4px | 6px |
| G02|url|en / 1件 / pages/products/ProductEditPage.tsx:298 (保留) | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G02|url|en / 1件 / pages/products/ProductEditPage.tsx:298 (保留) | normal | line-height | normal | 21.6px |
| G02|url|en / 1件 / pages/products/ProductEditPage.tsx:298 (保留) | normal | height | 34px | 39.6094px |
| G02|url|en / 1件 / pages/products/ProductEditPage.tsx:298 (保留) | normal | offsetHeight | 34 | 40 |
| G02|url|en / 1件 / pages/products/ProductEditPage.tsx:298 (保留) | focus | border-top-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| G02|url|en / 1件 / pages/products/ProductEditPage.tsx:298 (保留) | focus | border-top-left-radius | 4px | 6px |
| G02|url|en / 1件 / pages/products/ProductEditPage.tsx:298 (保留) | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G02|url|en / 1件 / pages/products/ProductEditPage.tsx:298 (保留) | focus | line-height | normal | 21.6px |
| G02|url|en / 1件 / pages/products/ProductEditPage.tsx:298 (保留) | focus | height | 34px | 39.6094px |
| G02|url|en / 1件 / pages/products/ProductEditPage.tsx:298 (保留) | focus | offsetHeight | 34 | 40 |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | normal | padding-top | 0px | 8px |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | normal | padding-right | 0px | 12px |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | normal | padding-bottom | 0px | 8px |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | normal | padding-left | 0px | 12px |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | normal | border-top-width | 2px | 1px |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | normal | border-top-style | inset | solid |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | normal | border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | normal | border-right-width | 2px | 1px |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | normal | border-bottom-width | 2px | 1px |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | normal | border-left-width | 2px | 1px |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | normal | border-top-left-radius | 0px | 6px |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | normal | font-size | 13.3333px | 14.4px |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | normal | line-height | normal | 21.6px |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | normal | height | 19px | 39.6094px |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | normal | width | 149px | 1132px |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | normal | offsetHeight | 19 | 40 |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | normal | offsetWidth | 149 | 1132 |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | focus | padding-top | 0px | 8px |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | focus | padding-right | 0px | 12px |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | focus | padding-bottom | 0px | 8px |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | focus | padding-left | 0px | 12px |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | focus | border-top-width | 2px | 1px |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | focus | border-top-style | inset | solid |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | focus | border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | focus | border-right-width | 2px | 1px |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | focus | border-bottom-width | 2px | 1px |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | focus | border-left-width | 2px | 1px |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | focus | border-top-left-radius | 0px | 6px |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | focus | font-size | 13.3333px | 14.4px |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | focus | line-height | normal | 21.6px |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | focus | height | 19px | 39.6094px |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | focus | width | 149px | 1132px |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | focus | outline-style | auto | none |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | focus | outline-width | 1px | 3px |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | focus | offsetHeight | 19 | 40 |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | focus | offsetWidth | 149 | 1132 |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | normal | padding-top | 0px | 8px |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | normal | padding-right | 0px | 12px |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | normal | padding-bottom | 0px | 8px |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | normal | padding-left | 0px | 12px |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | normal | border-top-width | 2px | 1px |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | normal | border-top-style | inset | solid |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | normal | border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | normal | border-right-width | 2px | 1px |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | normal | border-bottom-width | 2px | 1px |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | normal | border-left-width | 2px | 1px |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | normal | border-top-left-radius | 0px | 6px |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | normal | font-size | 13.3333px | 14.4px |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | normal | line-height | normal | 21.6px |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | normal | height | 19px | 39.6094px |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | normal | width | 149px | 1132px |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | normal | flex-grow | 1 | 0 |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | normal | offsetHeight | 19 | 40 |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | normal | offsetWidth | 149 | 1132 |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | focus | padding-top | 0px | 8px |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | focus | padding-right | 0px | 12px |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | focus | padding-bottom | 0px | 8px |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | focus | padding-left | 0px | 12px |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | focus | border-top-width | 2px | 1px |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | focus | border-top-style | inset | solid |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | focus | border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | focus | border-right-width | 2px | 1px |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | focus | border-bottom-width | 2px | 1px |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | focus | border-left-width | 2px | 1px |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | focus | border-top-left-radius | 0px | 6px |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | focus | font-size | 13.3333px | 14.4px |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | focus | line-height | normal | 21.6px |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | focus | height | 19px | 39.6094px |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | focus | width | 149px | 1132px |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | focus | flex-grow | 1 | 0 |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | focus | outline-style | auto | none |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | focus | outline-width | 1px | 3px |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | focus | offsetHeight | 19 | 40 |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | focus | offsetWidth | 149 | 1132 |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | normal | padding-top | 0px | 8px |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | normal | padding-right | 0px | 12px |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | normal | padding-bottom | 0px | 8px |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | normal | padding-left | 0px | 12px |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | normal | border-top-width | 2px | 1px |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | normal | border-top-style | inset | solid |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | normal | border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | normal | border-right-width | 2px | 1px |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | normal | border-bottom-width | 2px | 1px |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | normal | border-left-width | 2px | 1px |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | normal | border-top-left-radius | 0px | 6px |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | normal | font-size | 13.3333px | 14.4px |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | normal | line-height | normal | 21.6px |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | normal | height | 19px | 39.6094px |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | normal | width | 149px | 1132px |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | normal | offsetHeight | 19 | 40 |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | normal | offsetWidth | 149 | 1132 |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | focus | padding-top | 0px | 8px |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | focus | padding-right | 0px | 12px |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | focus | padding-bottom | 0px | 8px |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | focus | padding-left | 0px | 12px |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | focus | border-top-width | 2px | 1px |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | focus | border-top-style | inset | solid |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | focus | border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | focus | border-right-width | 2px | 1px |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | focus | border-bottom-width | 2px | 1px |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | focus | border-left-width | 2px | 1px |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | focus | border-top-left-radius | 0px | 6px |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | focus | font-size | 13.3333px | 14.4px |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | focus | line-height | normal | 21.6px |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | focus | height | 19px | 39.6094px |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | focus | width | 149px | 1132px |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | focus | outline-style | auto | none |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | focus | outline-width | 1px | 3px |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | focus | offsetHeight | 19 | 40 |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | focus | offsetWidth | 149 | 1132 |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | normal | padding-top | 0px | 8px |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | normal | padding-right | 0px | 12px |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | normal | padding-bottom | 0px | 8px |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | normal | padding-left | 0px | 12px |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | normal | border-top-width | 2px | 1px |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | normal | border-top-style | inset | solid |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | normal | border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | normal | border-right-width | 2px | 1px |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | normal | border-bottom-width | 2px | 1px |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | normal | border-left-width | 2px | 1px |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | normal | border-top-left-radius | 0px | 6px |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | normal | font-size | 13.3333px | 14.4px |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | normal | line-height | normal | 21.6px |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | normal | height | 19px | 39.6094px |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | normal | width | 149px | 1132px |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | normal | offsetHeight | 19 | 40 |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | normal | offsetWidth | 149 | 1132 |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | focus | padding-top | 0px | 8px |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | focus | padding-right | 0px | 12px |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | focus | padding-bottom | 0px | 8px |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | focus | padding-left | 0px | 12px |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | focus | border-top-width | 2px | 1px |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | focus | border-top-style | inset | solid |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | focus | border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | focus | border-right-width | 2px | 1px |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | focus | border-bottom-width | 2px | 1px |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | focus | border-left-width | 2px | 1px |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | focus | border-top-left-radius | 0px | 6px |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | focus | font-size | 13.3333px | 14.4px |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | focus | line-height | normal | 21.6px |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | focus | height | 19px | 39.6094px |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | focus | width | 149px | 1132px |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | focus | outline-style | auto | none |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | focus | outline-width | 1px | 3px |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | focus | offsetHeight | 19 | 40 |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | focus | offsetWidth | 149 | 1132 |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | normal | padding-top | 0px | 8px |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | normal | padding-right | 0px | 12px |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | normal | padding-bottom | 0px | 8px |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | normal | padding-left | 0px | 12px |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | normal | border-top-width | 2px | 1px |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | normal | border-top-style | inset | solid |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | normal | border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | normal | border-right-width | 2px | 1px |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | normal | border-bottom-width | 2px | 1px |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | normal | border-left-width | 2px | 1px |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | normal | border-top-left-radius | 0px | 6px |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | normal | font-size | 13.3333px | 14.4px |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | normal | line-height | normal | 21.6px |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | normal | height | 19px | 39.6094px |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | normal | width | 480px | 1232px |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | normal | max-width | 100% | none |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | normal | offsetHeight | 19 | 40 |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | normal | offsetWidth | 480 | 1232 |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | focus | padding-top | 0px | 8px |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | focus | padding-right | 0px | 12px |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | focus | padding-bottom | 0px | 8px |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | focus | padding-left | 0px | 12px |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | focus | border-top-width | 2px | 1px |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | focus | border-top-style | inset | solid |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | focus | border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | focus | border-right-width | 2px | 1px |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | focus | border-bottom-width | 2px | 1px |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | focus | border-left-width | 2px | 1px |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | focus | border-top-left-radius | 0px | 6px |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | focus | font-size | 13.3333px | 14.4px |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | focus | line-height | normal | 21.6px |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | focus | height | 19px | 39.6094px |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | focus | width | 480px | 1232px |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | focus | max-width | 100% | none |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | focus | outline-style | auto | none |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | focus | outline-width | 1px | 3px |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | focus | offsetHeight | 19 | 40 |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | focus | offsetWidth | 480 | 1232 |
| G32|number|en / 1件 / pages/super-admin/TcgLineImportPage.tsx:353 | normal | padding-top | 6.4px | 8px |
| G32|number|en / 1件 / pages/super-admin/TcgLineImportPage.tsx:353 | normal | padding-right | 9.6px | 12px |
| G32|number|en / 1件 / pages/super-admin/TcgLineImportPage.tsx:353 | normal | padding-bottom | 6.4px | 8px |
| G32|number|en / 1件 / pages/super-admin/TcgLineImportPage.tsx:353 | normal | padding-left | 9.6px | 12px |
| G32|number|en / 1件 / pages/super-admin/TcgLineImportPage.tsx:353 | normal | border-top-color | rgb(204, 204, 204) | rgb(226, 232, 240) |
| G32|number|en / 1件 / pages/super-admin/TcgLineImportPage.tsx:353 | normal | border-top-left-radius | 4px | 6px |
| G32|number|en / 1件 / pages/super-admin/TcgLineImportPage.tsx:353 | normal | font-size | 13.6px | 14.4px |
| G32|number|en / 1件 / pages/super-admin/TcgLineImportPage.tsx:353 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G32|number|en / 1件 / pages/super-admin/TcgLineImportPage.tsx:353 | normal | line-height | normal | 21.6px |
| G32|number|en / 1件 / pages/super-admin/TcgLineImportPage.tsx:353 | normal | background-color | rgb(245, 247, 250) | rgb(255, 255, 255) |
| G32|number|en / 1件 / pages/super-admin/TcgLineImportPage.tsx:353 | normal | height | 29.7812px | 39.6094px |
| G32|number|en / 1件 / pages/super-admin/TcgLineImportPage.tsx:353 | normal | width | 80px | 1280px |
| G32|number|en / 1件 / pages/super-admin/TcgLineImportPage.tsx:353 | normal | offsetHeight | 30 | 40 |
| G32|number|en / 1件 / pages/super-admin/TcgLineImportPage.tsx:353 | normal | offsetWidth | 80 | 1280 |
| G32|number|en / 1件 / pages/super-admin/TcgLineImportPage.tsx:353 | focus | padding-top | 6.4px | 8px |
| G32|number|en / 1件 / pages/super-admin/TcgLineImportPage.tsx:353 | focus | padding-right | 9.6px | 12px |
| G32|number|en / 1件 / pages/super-admin/TcgLineImportPage.tsx:353 | focus | padding-bottom | 6.4px | 8px |
| G32|number|en / 1件 / pages/super-admin/TcgLineImportPage.tsx:353 | focus | padding-left | 9.6px | 12px |
| G32|number|en / 1件 / pages/super-admin/TcgLineImportPage.tsx:353 | focus | border-top-color | rgb(204, 204, 204) | rgb(226, 232, 240) |
| G32|number|en / 1件 / pages/super-admin/TcgLineImportPage.tsx:353 | focus | border-top-left-radius | 4px | 6px |
| G32|number|en / 1件 / pages/super-admin/TcgLineImportPage.tsx:353 | focus | font-size | 13.6px | 14.4px |
| G32|number|en / 1件 / pages/super-admin/TcgLineImportPage.tsx:353 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G32|number|en / 1件 / pages/super-admin/TcgLineImportPage.tsx:353 | focus | line-height | normal | 21.6px |
| G32|number|en / 1件 / pages/super-admin/TcgLineImportPage.tsx:353 | focus | background-color | rgb(245, 247, 250) | rgb(255, 255, 255) |
| G32|number|en / 1件 / pages/super-admin/TcgLineImportPage.tsx:353 | focus | height | 29.7812px | 39.6094px |
| G32|number|en / 1件 / pages/super-admin/TcgLineImportPage.tsx:353 | focus | width | 80px | 1280px |
| G32|number|en / 1件 / pages/super-admin/TcgLineImportPage.tsx:353 | focus | offsetHeight | 30 | 40 |
| G32|number|en / 1件 / pages/super-admin/TcgLineImportPage.tsx:353 | focus | offsetWidth | 80 | 1280 |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | normal | padding-top | 6.4px | 8px |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | normal | padding-right | 9.6px | 12px |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | normal | padding-bottom | 6.4px | 8px |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | normal | padding-left | 9.6px | 12px |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | normal | border-top-color | rgb(204, 204, 204) | rgb(226, 232, 240) |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | normal | border-top-left-radius | 4px | 6px |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | normal | font-size | 13.6px | 14.4px |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | normal | line-height | normal | 21.6px |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | normal | background-color | rgb(245, 247, 250) | rgb(255, 255, 255) |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | normal | height | 29.7812px | 39.6094px |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | normal | width | 200px | 1280px |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | normal | min-width | 200px | 0px |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | normal | offsetHeight | 30 | 40 |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | normal | offsetWidth | 200 | 1280 |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | focus | padding-top | 6.4px | 8px |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | focus | padding-right | 9.6px | 12px |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | focus | padding-bottom | 6.4px | 8px |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | focus | padding-left | 9.6px | 12px |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | focus | border-top-color | rgb(204, 204, 204) | rgb(226, 232, 240) |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | focus | border-top-left-radius | 4px | 6px |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | focus | font-size | 13.6px | 14.4px |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | focus | line-height | normal | 21.6px |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | focus | background-color | rgb(245, 247, 250) | rgb(255, 255, 255) |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | focus | height | 29.7812px | 39.6094px |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | focus | width | 200px | 1280px |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | focus | min-width | 200px | 0px |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | focus | offsetHeight | 30 | 40 |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | focus | offsetWidth | 200 | 1280 |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | normal | padding-top | 4px | 8px |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | normal | padding-right | 8px | 12px |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | normal | padding-bottom | 4px | 8px |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | normal | padding-left | 8px | 12px |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | normal | border-top-left-radius | 4px | 6px |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | normal | font-size | 13.3333px | 14.4px |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | normal | line-height | normal | 21.6px |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | normal | height | 25px | 39.6094px |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | normal | width | 80px | 1232px |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | normal | offsetHeight | 25 | 40 |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | normal | offsetWidth | 80 | 1232 |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | focus | padding-top | 4px | 8px |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | focus | padding-right | 8px | 12px |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | focus | padding-bottom | 4px | 8px |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | focus | padding-left | 8px | 12px |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | focus | border-top-color | rgb(226, 232, 240) | rgb(30, 58, 138) |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | focus | border-top-left-radius | 4px | 6px |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | focus | font-size | 13.3333px | 14.4px |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | focus | line-height | normal | 21.6px |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | focus | height | 25px | 39.6094px |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | focus | width | 80px | 1232px |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | focus | outline-style | auto | none |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | focus | outline-width | 1px | 3px |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | focus | offsetHeight | 25 | 40 |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | focus | offsetWidth | 80 | 1232 |

### 幅 375

| 代表（group|type|disabled / 件数 / file:line） | 状態 | プロパティ | before | after |
|---|---|---|---|---|
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | normal | padding-top | 6px | 8px |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | normal | padding-right | 8px | 12px |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | normal | padding-bottom | 6px | 8px |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | normal | padding-left | 8px | 12px |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | normal | border-top-left-radius | 4px | 6px |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | normal | font-size | 13px | 14.4px |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | normal | line-height | normal | 21.6px |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | normal | height | 29px | 44px |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | normal | min-height | 0px | 44px |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | normal | width | 80px | 327px |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | normal | offsetHeight | 29 | 44 |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | normal | offsetWidth | 80 | 327 |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | focus | padding-top | 6px | 8px |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | focus | padding-right | 8px | 12px |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | focus | padding-bottom | 6px | 8px |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | focus | padding-left | 8px | 12px |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | focus | border-top-color | rgb(226, 232, 240) | rgb(30, 58, 138) |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | focus | border-top-left-radius | 4px | 6px |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | focus | font-size | 13px | 14.4px |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | focus | line-height | normal | 21.6px |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | focus | height | 29px | 44px |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | focus | min-height | 0px | 44px |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | focus | width | 80px | 327px |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | focus | outline-style | auto | none |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | focus | outline-width | 1px | 3px |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | focus | offsetHeight | 29 | 44 |
| G08|text|en / 2件 / components/FedExRateModal.tsx:176 | focus | offsetWidth | 80 | 327 |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | normal | padding-top | 6px | 8px |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | normal | padding-right | 8px | 12px |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | normal | padding-bottom | 6px | 8px |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | normal | padding-left | 8px | 12px |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | normal | border-top-left-radius | 4px | 6px |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | normal | font-size | 13px | 14.4px |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | normal | line-height | normal | 21.6px |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | normal | height | 29px | 44px |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | normal | min-height | 0px | 44px |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | normal | width | 100px | 327px |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | normal | offsetHeight | 29 | 44 |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | normal | offsetWidth | 100 | 327 |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | focus | padding-top | 6px | 8px |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | focus | padding-right | 8px | 12px |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | focus | padding-bottom | 6px | 8px |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | focus | padding-left | 8px | 12px |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | focus | border-top-color | rgb(226, 232, 240) | rgb(30, 58, 138) |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | focus | border-top-left-radius | 4px | 6px |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | focus | font-size | 13px | 14.4px |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | focus | line-height | normal | 21.6px |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | focus | height | 29px | 44px |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | focus | min-height | 0px | 44px |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | focus | width | 100px | 327px |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | focus | outline-style | auto | none |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | focus | outline-width | 1px | 3px |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | focus | offsetHeight | 29 | 44 |
| G20|number|en / 1件 / components/FedExRateModal.tsx:210 | focus | offsetWidth | 100 | 327 |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | normal | padding-top | 6px | 8px |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | normal | padding-right | 8px | 12px |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | normal | padding-bottom | 6px | 8px |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | normal | padding-left | 8px | 12px |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | normal | border-top-left-radius | 4px | 6px |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | normal | font-size | 13px | 14.4px |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | normal | line-height | normal | 21.6px |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | normal | height | 29px | 44px |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | normal | min-height | 0px | 44px |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | normal | width | 160px | 327px |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | normal | offsetHeight | 29 | 44 |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | normal | offsetWidth | 160 | 327 |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | focus | padding-top | 6px | 8px |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | focus | padding-right | 8px | 12px |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | focus | padding-bottom | 6px | 8px |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | focus | padding-left | 8px | 12px |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | focus | border-top-color | rgb(226, 232, 240) | rgb(30, 58, 138) |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | focus | border-top-left-radius | 4px | 6px |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | focus | font-size | 13px | 14.4px |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | focus | line-height | normal | 21.6px |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | focus | height | 29px | 44px |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | focus | min-height | 0px | 44px |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | focus | width | 160px | 327px |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | focus | outline-style | auto | none |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | focus | outline-width | 1px | 3px |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | focus | offsetHeight | 29 | 44 |
| G21|text|en / 1件 / components/FedExRateModal.tsx:239 | focus | offsetWidth | 160 | 327 |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | normal | padding-top | 6px | 8px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | normal | padding-right | 8px | 12px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | normal | padding-bottom | 6px | 8px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | normal | padding-left | 8px | 12px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | normal | border-top-width | 2px | 1px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | normal | border-top-style | inset | solid |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | normal | border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | normal | border-right-width | 2px | 1px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | normal | border-bottom-width | 2px | 1px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | normal | border-left-width | 2px | 1px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | normal | border-top-left-radius | 0px | 6px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | normal | font-size | 13.3333px | 14.4px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | normal | line-height | normal | 21.6px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | normal | height | 31px | 44px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | normal | min-height | 0px | 44px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | normal | width | 165px | 375px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | normal | min-width | 120px | 0px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | normal | flex-grow | 1 | 0 |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | normal | offsetHeight | 31 | 44 |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | normal | offsetWidth | 165 | 375 |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | focus | padding-top | 6px | 8px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | focus | padding-right | 8px | 12px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | focus | padding-bottom | 6px | 8px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | focus | padding-left | 8px | 12px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | focus | border-top-width | 2px | 1px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | focus | border-top-style | inset | solid |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | focus | border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | focus | border-right-width | 2px | 1px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | focus | border-bottom-width | 2px | 1px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | focus | border-left-width | 2px | 1px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | focus | border-top-left-radius | 0px | 6px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | focus | font-size | 13.3333px | 14.4px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | focus | line-height | normal | 21.6px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | focus | height | 31px | 44px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | focus | min-height | 0px | 44px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | focus | width | 165px | 375px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | focus | min-width | 120px | 0px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | focus | flex-grow | 1 | 0 |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | focus | outline-style | auto | none |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | focus | outline-width | 1px | 3px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | focus | offsetHeight | 31 | 44 |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | focus | offsetWidth | 165 | 375 |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | disabled | padding-top | 6px | 8px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | disabled | padding-right | 8px | 12px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | disabled | padding-bottom | 6px | 8px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | disabled | padding-left | 8px | 12px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | disabled | border-top-width | 2px | 1px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | disabled | border-top-style | inset | solid |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | disabled | border-top-color | rgba(118, 118, 118, 0.3) | rgb(226, 232, 240) |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | disabled | border-right-width | 2px | 1px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | disabled | border-bottom-width | 2px | 1px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | disabled | border-left-width | 2px | 1px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | disabled | border-top-left-radius | 0px | 6px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | disabled | font-size | 13.3333px | 14.4px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | disabled | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | disabled | line-height | normal | 21.6px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | disabled | color | rgb(84, 84, 84) | rgb(26, 32, 44) |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | disabled | background-color | rgba(239, 239, 239, 0.3) | rgb(226, 232, 240) |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | disabled | height | 31px | 44px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | disabled | min-height | 0px | 44px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | disabled | width | 165px | 375px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | disabled | min-width | 120px | 0px |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | disabled | flex-grow | 1 | 0 |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | disabled | outline-color | rgb(84, 84, 84) | rgb(26, 32, 44) |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | disabled | cursor | default | not-allowed |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | disabled | opacity | 1 | 0.5 |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | disabled | offsetHeight | 31 | 44 |
| G22|text|dis / 1件 / components/InventorySearchBar.tsx:272 | disabled | offsetWidth | 165 | 375 |
| G09|text|en / 2件 / components/master-list-editor/MasterListEditor.tsx:135 | normal | border-top-left-radius | 4px | 6px |
| G09|text|en / 2件 / components/master-list-editor/MasterListEditor.tsx:135 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G09|text|en / 2件 / components/master-list-editor/MasterListEditor.tsx:135 | normal | line-height | normal | 21.6px |
| G09|text|en / 2件 / components/master-list-editor/MasterListEditor.tsx:135 | normal | height | 36px | 44px |
| G09|text|en / 2件 / components/master-list-editor/MasterListEditor.tsx:135 | normal | min-height | 36px | 44px |
| G09|text|en / 2件 / components/master-list-editor/MasterListEditor.tsx:135 | normal | width | 280px | 192px |
| G09|text|en / 2件 / components/master-list-editor/MasterListEditor.tsx:135 | normal | min-width | 280px | 0px |
| G09|text|en / 2件 / components/master-list-editor/MasterListEditor.tsx:135 | normal | offsetHeight | 36 | 44 |
| G09|text|en / 2件 / components/master-list-editor/MasterListEditor.tsx:135 | normal | offsetWidth | 280 | 192 |
| G09|text|en / 2件 / components/master-list-editor/MasterListEditor.tsx:135 | focus | border-top-color | rgb(226, 232, 240) | rgb(30, 58, 138) |
| G09|text|en / 2件 / components/master-list-editor/MasterListEditor.tsx:135 | focus | border-top-left-radius | 4px | 6px |
| G09|text|en / 2件 / components/master-list-editor/MasterListEditor.tsx:135 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G09|text|en / 2件 / components/master-list-editor/MasterListEditor.tsx:135 | focus | line-height | normal | 21.6px |
| G09|text|en / 2件 / components/master-list-editor/MasterListEditor.tsx:135 | focus | height | 36px | 44px |
| G09|text|en / 2件 / components/master-list-editor/MasterListEditor.tsx:135 | focus | min-height | 36px | 44px |
| G09|text|en / 2件 / components/master-list-editor/MasterListEditor.tsx:135 | focus | width | 280px | 192px |
| G09|text|en / 2件 / components/master-list-editor/MasterListEditor.tsx:135 | focus | min-width | 280px | 0px |
| G09|text|en / 2件 / components/master-list-editor/MasterListEditor.tsx:135 | focus | outline-style | auto | none |
| G09|text|en / 2件 / components/master-list-editor/MasterListEditor.tsx:135 | focus | outline-width | 1px | 3px |
| G09|text|en / 2件 / components/master-list-editor/MasterListEditor.tsx:135 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G09|text|en / 2件 / components/master-list-editor/MasterListEditor.tsx:135 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G09|text|en / 2件 / components/master-list-editor/MasterListEditor.tsx:135 | focus | offsetHeight | 36 | 44 |
| G09|text|en / 2件 / components/master-list-editor/MasterListEditor.tsx:135 | focus | offsetWidth | 280 | 192 |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | normal | padding-top | 0px | 8px |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | normal | padding-right | 0px | 12px |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | normal | padding-bottom | 0px | 8px |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | normal | padding-left | 0px | 12px |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | normal | border-top-width | 2px | 1px |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | normal | border-top-style | inset | solid |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | normal | border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | normal | border-right-width | 2px | 1px |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | normal | border-bottom-width | 2px | 1px |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | normal | border-left-width | 2px | 1px |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | normal | border-top-left-radius | 0px | 6px |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | normal | font-size | 13.3333px | 14.4px |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | normal | line-height | normal | 21.6px |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | normal | height | 19px | 44px |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | normal | min-height | 0px | 44px |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | normal | width | 149px | 375px |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | normal | offsetHeight | 19 | 44 |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | normal | offsetWidth | 149 | 375 |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | focus | padding-top | 0px | 8px |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | focus | padding-right | 0px | 12px |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | focus | padding-bottom | 0px | 8px |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | focus | padding-left | 0px | 12px |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | focus | border-top-width | 2px | 1px |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | focus | border-top-style | inset | solid |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | focus | border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | focus | border-right-width | 2px | 1px |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | focus | border-bottom-width | 2px | 1px |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | focus | border-left-width | 2px | 1px |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | focus | border-top-left-radius | 0px | 6px |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | focus | font-size | 13.3333px | 14.4px |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | focus | line-height | normal | 21.6px |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | focus | height | 19px | 44px |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | focus | min-height | 0px | 44px |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | focus | width | 149px | 375px |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | focus | outline-style | auto | none |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | focus | outline-width | 1px | 3px |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | focus | offsetHeight | 19 | 44 |
| G01|omitted|en / 12件 / components/master-list-editor/MasterListEditor.tsx:157 | focus | offsetWidth | 149 | 375 |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | normal | padding-top | 0px | 8px |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | normal | padding-right | 0px | 12px |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | normal | padding-bottom | 0px | 8px |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | normal | padding-left | 0px | 12px |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | normal | border-top-width | 2px | 1px |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | normal | border-top-style | inset | solid |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | normal | border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | normal | border-right-width | 2px | 1px |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | normal | border-bottom-width | 2px | 1px |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | normal | border-left-width | 2px | 1px |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | normal | border-top-left-radius | 0px | 6px |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | normal | font-size | 13.3333px | 14.4px |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | normal | line-height | normal | 21.6px |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | normal | height | 23px | 44px |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | normal | min-height | auto | 44px |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | normal | offsetHeight | 23 | 44 |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | focus | padding-top | 0px | 8px |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | focus | padding-right | 0px | 12px |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | focus | padding-bottom | 0px | 8px |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | focus | padding-left | 0px | 12px |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | focus | border-top-width | 2px | 1px |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | focus | border-top-style | inset | solid |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | focus | border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | focus | border-right-width | 2px | 1px |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | focus | border-bottom-width | 2px | 1px |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | focus | border-left-width | 2px | 1px |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | focus | border-top-left-radius | 0px | 6px |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | focus | font-size | 13.3333px | 14.4px |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | focus | line-height | normal | 21.6px |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | focus | height | 23px | 44px |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | focus | min-height | auto | 44px |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | focus | outline-style | auto | none |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | focus | outline-width | 1px | 3px |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G01|dynamic|en / 1件 / features/tcg-analysis-review/ItemComparison.tsx:29 | focus | offsetHeight | 23 | 44 |
| G03|omitted|en / 6件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:68 (保留) | normal | padding-right | 8px | 12px |
| G03|omitted|en / 6件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:68 (保留) | normal | padding-left | 8px | 12px |
| G03|omitted|en / 6件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:68 (保留) | normal | font-size | 13.6px | 14.4px |
| G03|omitted|en / 6件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:68 (保留) | normal | font-weight | 500 | 400 |
| G03|omitted|en / 6件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:68 (保留) | normal | line-height | 21.76px | 21.6px |
| G03|omitted|en / 6件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:68 (保留) | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G03|omitted|en / 6件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:68 (保留) | normal | height | 39.75px | 44px |
| G03|omitted|en / 6件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:68 (保留) | normal | min-height | auto | 44px |
| G03|omitted|en / 6件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:68 (保留) | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G03|omitted|en / 6件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:68 (保留) | normal | offsetHeight | 40 | 44 |
| G03|omitted|en / 6件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:68 (保留) | focus | padding-right | 8px | 12px |
| G03|omitted|en / 6件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:68 (保留) | focus | padding-left | 8px | 12px |
| G03|omitted|en / 6件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:68 (保留) | focus | border-top-color | rgb(226, 232, 240) | rgb(30, 58, 138) |
| G03|omitted|en / 6件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:68 (保留) | focus | font-size | 13.6px | 14.4px |
| G03|omitted|en / 6件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:68 (保留) | focus | font-weight | 500 | 400 |
| G03|omitted|en / 6件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:68 (保留) | focus | line-height | 21.76px | 21.6px |
| G03|omitted|en / 6件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:68 (保留) | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G03|omitted|en / 6件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:68 (保留) | focus | height | 39.75px | 44px |
| G03|omitted|en / 6件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:68 (保留) | focus | min-height | auto | 44px |
| G03|omitted|en / 6件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:68 (保留) | focus | outline-style | auto | none |
| G03|omitted|en / 6件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:68 (保留) | focus | outline-width | 1px | 3px |
| G03|omitted|en / 6件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:68 (保留) | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G03|omitted|en / 6件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:68 (保留) | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G03|omitted|en / 6件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:68 (保留) | focus | offsetHeight | 40 | 44 |
| G03|date|en / 1件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:213 (保留) | normal | padding-right | 8px | 12px |
| G03|date|en / 1件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:213 (保留) | normal | padding-left | 8px | 12px |
| G03|date|en / 1件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:213 (保留) | normal | font-size | 13.6px | 14.4px |
| G03|date|en / 1件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:213 (保留) | normal | font-weight | 500 | 400 |
| G03|date|en / 1件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:213 (保留) | normal | line-height | 21.76px | 21.6px |
| G03|date|en / 1件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:213 (保留) | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G03|date|en / 1件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:213 (保留) | normal | height | 41.75px | 44px |
| G03|date|en / 1件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:213 (保留) | normal | min-height | auto | 44px |
| G03|date|en / 1件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:213 (保留) | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G03|date|en / 1件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:213 (保留) | normal | offsetHeight | 42 | 44 |
| G03|date|en / 1件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:213 (保留) | focus | padding-right | 8px | 12px |
| G03|date|en / 1件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:213 (保留) | focus | padding-left | 8px | 12px |
| G03|date|en / 1件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:213 (保留) | focus | border-top-color | rgb(226, 232, 240) | rgb(30, 58, 138) |
| G03|date|en / 1件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:213 (保留) | focus | font-size | 13.6px | 14.4px |
| G03|date|en / 1件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:213 (保留) | focus | font-weight | 500 | 400 |
| G03|date|en / 1件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:213 (保留) | focus | line-height | 21.76px | 21.6px |
| G03|date|en / 1件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:213 (保留) | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G03|date|en / 1件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:213 (保留) | focus | height | 41.75px | 44px |
| G03|date|en / 1件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:213 (保留) | focus | min-height | auto | 44px |
| G03|date|en / 1件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:213 (保留) | focus | outline-style | auto | none |
| G03|date|en / 1件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:213 (保留) | focus | outline-width | 1px | 3px |
| G03|date|en / 1件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:213 (保留) | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G03|date|en / 1件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:213 (保留) | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G03|date|en / 1件 / features/tcg-analysis-review/ProductMasterDrawer.tsx:213 (保留) | focus | offsetHeight | 42 | 44 |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | normal | padding-top | 0px | 8px |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | normal | padding-right | 0px | 12px |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | normal | padding-bottom | 0px | 8px |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | normal | padding-left | 0px | 12px |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | normal | border-top-width | 2px | 1px |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | normal | border-top-style | inset | solid |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | normal | border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | normal | border-right-width | 2px | 1px |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | normal | border-bottom-width | 2px | 1px |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | normal | border-left-width | 2px | 1px |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | normal | border-top-left-radius | 0px | 6px |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | normal | font-size | 13.3333px | 14.4px |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | normal | line-height | normal | 21.6px |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | normal | height | 19px | 44px |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | normal | min-height | auto | 44px |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | normal | min-width | 0px | auto |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | normal | offsetHeight | 19 | 44 |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | focus | padding-top | 0px | 8px |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | focus | padding-right | 0px | 12px |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | focus | padding-bottom | 0px | 8px |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | focus | padding-left | 0px | 12px |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | focus | border-top-width | 2px | 1px |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | focus | border-top-style | inset | solid |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | focus | border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | focus | border-right-width | 2px | 1px |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | focus | border-bottom-width | 2px | 1px |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | focus | border-left-width | 2px | 1px |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | focus | border-top-left-radius | 0px | 6px |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | focus | font-size | 13.3333px | 14.4px |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | focus | line-height | normal | 21.6px |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | focus | height | 19px | 44px |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | focus | min-height | auto | 44px |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | focus | min-width | 0px | auto |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | focus | outline-style | auto | none |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | focus | outline-width | 1px | 3px |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G23|omitted|en / 1件 / features/tcg-analysis-review/SourceRawPane.tsx:30 (保留) | focus | offsetHeight | 19 | 44 |
| G06|text|en / 3件 / features/tcg-distribution/DistributionTargetForm.tsx:182 | normal | font-size | 13.6px | 14.4px |
| G06|text|en / 3件 / features/tcg-distribution/DistributionTargetForm.tsx:182 | normal | line-height | 21.76px | 21.6px |
| G06|text|en / 3件 / features/tcg-distribution/DistributionTargetForm.tsx:182 | normal | height | 39.75px | 44px |
| G06|text|en / 3件 / features/tcg-distribution/DistributionTargetForm.tsx:182 | normal | min-height | auto | 44px |
| G06|text|en / 3件 / features/tcg-distribution/DistributionTargetForm.tsx:182 | normal | offsetHeight | 40 | 44 |
| G06|text|en / 3件 / features/tcg-distribution/DistributionTargetForm.tsx:182 | focus | font-size | 13.6px | 14.4px |
| G06|text|en / 3件 / features/tcg-distribution/DistributionTargetForm.tsx:182 | focus | line-height | 21.76px | 21.6px |
| G06|text|en / 3件 / features/tcg-distribution/DistributionTargetForm.tsx:182 | focus | height | 39.75px | 44px |
| G06|text|en / 3件 / features/tcg-distribution/DistributionTargetForm.tsx:182 | focus | min-height | auto | 44px |
| G06|text|en / 3件 / features/tcg-distribution/DistributionTargetForm.tsx:182 | focus | outline-style | solid | none |
| G06|text|en / 3件 / features/tcg-distribution/DistributionTargetForm.tsx:182 | focus | outline-width | 2px | 3px |
| G06|text|en / 3件 / features/tcg-distribution/DistributionTargetForm.tsx:182 | focus | outline-color | rgb(30, 58, 138) | rgb(26, 32, 44) |
| G06|text|en / 3件 / features/tcg-distribution/DistributionTargetForm.tsx:182 | focus | outline-offset | -1px | 0px |
| G06|text|en / 3件 / features/tcg-distribution/DistributionTargetForm.tsx:182 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G06|text|en / 3件 / features/tcg-distribution/DistributionTargetForm.tsx:182 | focus | offsetHeight | 40 | 44 |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | normal | padding-top | 6.4px | 8px |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | normal | padding-right | 9.6px | 12px |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | normal | padding-bottom | 6.4px | 8px |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | normal | padding-left | 9.6px | 12px |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | normal | border-top-color | rgb(204, 204, 204) | rgb(226, 232, 240) |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | normal | border-top-left-radius | 4px | 6px |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | normal | font-size | 13.6px | 14.4px |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | normal | line-height | normal | 21.6px |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | normal | background-color | rgb(245, 247, 250) | rgb(255, 255, 255) |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | normal | height | 29.7812px | 44px |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | normal | min-height | 0px | 44px |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | normal | margin-bottom | 8px | 0px |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | normal | offsetHeight | 30 | 44 |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | focus | padding-top | 6.4px | 8px |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | focus | padding-right | 9.6px | 12px |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | focus | padding-bottom | 6.4px | 8px |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | focus | padding-left | 9.6px | 12px |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | focus | border-top-color | rgb(204, 204, 204) | rgb(30, 58, 138) |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | focus | border-top-left-radius | 4px | 6px |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | focus | font-size | 13.6px | 14.4px |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | focus | line-height | normal | 21.6px |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | focus | background-color | rgb(245, 247, 250) | rgb(255, 255, 255) |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | focus | height | 29.7812px | 44px |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | focus | min-height | 0px | 44px |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | focus | margin-bottom | 8px | 0px |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | focus | outline-style | auto | none |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | focus | outline-width | 1px | 3px |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G24|text|en / 1件 / features/tcg-import-review/ReviewSection.tsx:289 | focus | offsetHeight | 30 | 44 |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | normal | padding-top | 0px | 8px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | normal | padding-right | 0px | 12px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | normal | padding-bottom | 0px | 8px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | normal | padding-left | 0px | 12px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | normal | border-top-width | 2px | 1px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | normal | border-top-style | inset | solid |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | normal | border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | normal | border-right-width | 2px | 1px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | normal | border-bottom-width | 2px | 1px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | normal | border-left-width | 2px | 1px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | normal | border-top-left-radius | 0px | 6px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | normal | font-size | 13.3333px | 14.4px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | normal | line-height | normal | 21.6px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | normal | height | 19px | 44px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | normal | min-height | 0px | 44px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | normal | width | 149px | 375px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | normal | offsetHeight | 19 | 44 |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | normal | offsetWidth | 149 | 375 |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | focus | padding-top | 0px | 8px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | focus | padding-right | 0px | 12px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | focus | padding-bottom | 0px | 8px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | focus | padding-left | 0px | 12px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | focus | border-top-width | 2px | 1px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | focus | border-top-style | inset | solid |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | focus | border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | focus | border-right-width | 2px | 1px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | focus | border-bottom-width | 2px | 1px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | focus | border-left-width | 2px | 1px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | focus | border-top-left-radius | 0px | 6px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | focus | font-size | 13.3333px | 14.4px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | focus | line-height | normal | 21.6px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | focus | height | 19px | 44px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | focus | min-height | 0px | 44px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | focus | width | 149px | 375px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | focus | outline-style | auto | none |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | focus | outline-width | 1px | 3px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | focus | offsetHeight | 19 | 44 |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | focus | offsetWidth | 149 | 375 |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | disabled | padding-top | 0px | 8px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | disabled | padding-right | 0px | 12px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | disabled | padding-bottom | 0px | 8px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | disabled | padding-left | 0px | 12px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | disabled | border-top-width | 2px | 1px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | disabled | border-top-style | inset | solid |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | disabled | border-top-color | rgba(118, 118, 118, 0.3) | rgb(226, 232, 240) |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | disabled | border-right-width | 2px | 1px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | disabled | border-bottom-width | 2px | 1px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | disabled | border-left-width | 2px | 1px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | disabled | border-top-left-radius | 0px | 6px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | disabled | font-size | 13.3333px | 14.4px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | disabled | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | disabled | line-height | normal | 21.6px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | disabled | color | rgb(84, 84, 84) | rgb(26, 32, 44) |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | disabled | background-color | rgba(239, 239, 239, 0.3) | rgb(226, 232, 240) |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | disabled | height | 19px | 44px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | disabled | min-height | 0px | 44px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | disabled | width | 149px | 375px |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | disabled | outline-color | rgb(84, 84, 84) | rgb(26, 32, 44) |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | disabled | cursor | default | not-allowed |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | disabled | opacity | 1 | 0.5 |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | disabled | offsetHeight | 19 | 44 |
| G01|text|dis / 3件 / pages/admin/ChannelMastersPage.tsx:115 | disabled | offsetWidth | 149 | 375 |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | normal | padding-top | 0px | 8px |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | normal | padding-right | 0px | 12px |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | normal | padding-bottom | 0px | 8px |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | normal | padding-left | 0px | 12px |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | normal | border-top-width | 2px | 1px |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | normal | border-top-style | inset | solid |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | normal | border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | normal | border-right-width | 2px | 1px |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | normal | border-bottom-width | 2px | 1px |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | normal | border-left-width | 2px | 1px |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | normal | border-top-left-radius | 0px | 6px |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | normal | font-size | 13.3333px | 14.4px |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | normal | line-height | normal | 21.6px |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | normal | height | 19px | 44px |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | normal | min-height | 0px | 44px |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | normal | width | 149px | 339px |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | normal | offsetHeight | 19 | 44 |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | normal | offsetWidth | 149 | 339 |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | focus | padding-top | 0px | 8px |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | focus | padding-right | 0px | 12px |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | focus | padding-bottom | 0px | 8px |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | focus | padding-left | 0px | 12px |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | focus | border-top-width | 2px | 1px |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | focus | border-top-style | inset | solid |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | focus | border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | focus | border-right-width | 2px | 1px |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | focus | border-bottom-width | 2px | 1px |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | focus | border-left-width | 2px | 1px |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | focus | border-top-left-radius | 0px | 6px |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | focus | font-size | 13.3333px | 14.4px |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | focus | line-height | normal | 21.6px |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | focus | height | 19px | 44px |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | focus | min-height | 0px | 44px |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | focus | width | 149px | 339px |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | focus | outline-style | auto | none |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | focus | outline-width | 1px | 3px |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | focus | offsetHeight | 19 | 44 |
| G01|number|en / 3件 / pages/commission-settings/CommissionSettingsPage.tsx:220 | focus | offsetWidth | 149 | 339 |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | normal | padding-top | 0px | 8px |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | normal | padding-right | 0px | 12px |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | normal | padding-bottom | 0px | 8px |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | normal | padding-left | 0px | 12px |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | normal | border-top-width | 2px | 1px |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | normal | border-top-style | inset | solid |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | normal | border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | normal | border-right-width | 2px | 1px |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | normal | border-bottom-width | 2px | 1px |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | normal | border-left-width | 2px | 1px |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | normal | border-top-left-radius | 0px | 6px |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | normal | font-size | 13.3333px | 14.4px |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | normal | line-height | normal | 21.6px |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | normal | height | 19px | 44px |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | normal | min-height | 0px | 44px |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | normal | width | 90px | 371px |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | normal | margin-left | 8px | 0px |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | normal | offsetHeight | 19 | 44 |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | normal | offsetWidth | 90 | 371 |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | focus | padding-top | 0px | 8px |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | focus | padding-right | 0px | 12px |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | focus | padding-bottom | 0px | 8px |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | focus | padding-left | 0px | 12px |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | focus | border-top-width | 2px | 1px |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | focus | border-top-style | inset | solid |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | focus | border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | focus | border-right-width | 2px | 1px |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | focus | border-bottom-width | 2px | 1px |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | focus | border-left-width | 2px | 1px |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | focus | border-top-left-radius | 0px | 6px |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | focus | font-size | 13.3333px | 14.4px |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | focus | line-height | normal | 21.6px |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | focus | height | 19px | 44px |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | focus | min-height | 0px | 44px |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | focus | width | 90px | 371px |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | focus | margin-left | 8px | 0px |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | focus | outline-style | auto | none |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | focus | outline-width | 1px | 3px |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | focus | offsetHeight | 19 | 44 |
| G10|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:275 | focus | offsetWidth | 90 | 371 |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | normal | padding-top | 0px | 8px |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | normal | padding-right | 0px | 12px |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | normal | padding-bottom | 0px | 8px |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | normal | padding-left | 0px | 12px |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | normal | border-top-width | 2px | 1px |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | normal | border-top-style | inset | solid |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | normal | border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | normal | border-right-width | 2px | 1px |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | normal | border-bottom-width | 2px | 1px |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | normal | border-left-width | 2px | 1px |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | normal | border-top-left-radius | 0px | 6px |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | normal | font-size | 13.3333px | 14.4px |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | normal | line-height | normal | 21.6px |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | normal | height | 19px | 44px |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | normal | min-height | 0px | 44px |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | normal | width | 60px | 371px |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | normal | margin-left | 8px | 0px |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | normal | offsetHeight | 19 | 44 |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | normal | offsetWidth | 60 | 371 |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | focus | padding-top | 0px | 8px |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | focus | padding-right | 0px | 12px |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | focus | padding-bottom | 0px | 8px |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | focus | padding-left | 0px | 12px |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | focus | border-top-width | 2px | 1px |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | focus | border-top-style | inset | solid |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | focus | border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | focus | border-right-width | 2px | 1px |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | focus | border-bottom-width | 2px | 1px |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | focus | border-left-width | 2px | 1px |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | focus | border-top-left-radius | 0px | 6px |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | focus | font-size | 13.3333px | 14.4px |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | focus | line-height | normal | 21.6px |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | focus | height | 19px | 44px |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | focus | min-height | 0px | 44px |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | focus | width | 60px | 371px |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | focus | margin-left | 8px | 0px |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | focus | outline-style | auto | none |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | focus | outline-width | 1px | 3px |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | focus | offsetHeight | 19 | 44 |
| G11|number|en / 2件 / pages/commission-settings/CommissionSettingsPage.tsx:287 | focus | offsetWidth | 60 | 371 |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | normal | padding-top | 0px | 8px |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | normal | padding-right | 0px | 12px |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | normal | padding-bottom | 0px | 8px |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | normal | padding-left | 0px | 12px |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | normal | border-top-width | 2px | 1px |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | normal | border-top-style | inset | solid |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | normal | border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | normal | border-right-width | 2px | 1px |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | normal | border-bottom-width | 2px | 1px |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | normal | border-left-width | 2px | 1px |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | normal | border-top-left-radius | 0px | 6px |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | normal | font-size | 13.3333px | 14.4px |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | normal | line-height | normal | 21.6px |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | normal | height | 36px | 44px |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | normal | min-height | 36px | 44px |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | normal | width | 280px | 192px |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | normal | offsetHeight | 36 | 44 |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | normal | offsetWidth | 280 | 192 |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | focus | padding-top | 0px | 8px |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | focus | padding-right | 0px | 12px |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | focus | padding-bottom | 0px | 8px |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | focus | padding-left | 0px | 12px |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | focus | border-top-width | 2px | 1px |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | focus | border-top-style | inset | solid |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | focus | border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | focus | border-right-width | 2px | 1px |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | focus | border-bottom-width | 2px | 1px |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | focus | border-left-width | 2px | 1px |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | focus | border-top-left-radius | 0px | 6px |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | focus | font-size | 13.3333px | 14.4px |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | focus | line-height | normal | 21.6px |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | focus | height | 36px | 44px |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | focus | min-height | 36px | 44px |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | focus | width | 280px | 192px |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | focus | outline-style | auto | none |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | focus | outline-width | 1px | 3px |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | focus | offsetHeight | 36 | 44 |
| G07|text|en / 1件 / pages/companies/CompaniesPage.tsx:387 | focus | offsetWidth | 280 | 192 |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | normal | padding-top | 0px | 8px |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | normal | padding-right | 0px | 12px |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | normal | padding-bottom | 0px | 8px |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | normal | padding-left | 0px | 12px |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | normal | border-top-width | 2px | 1px |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | normal | border-top-style | inset | solid |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | normal | border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | normal | border-right-width | 2px | 1px |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | normal | border-bottom-width | 2px | 1px |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | normal | border-left-width | 2px | 1px |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | normal | border-top-left-radius | 0px | 6px |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | normal | font-size | 13.3333px | 14.4px |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | normal | line-height | normal | 21.6px |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | normal | height | 36px | 44px |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | normal | min-height | 36px | 44px |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | normal | width | 160px | 192px |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | normal | offsetHeight | 36 | 44 |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | normal | offsetWidth | 160 | 192 |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | focus | padding-top | 0px | 8px |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | focus | padding-right | 0px | 12px |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | focus | padding-bottom | 0px | 8px |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | focus | padding-left | 0px | 12px |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | focus | border-top-width | 2px | 1px |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | focus | border-top-style | inset | solid |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | focus | border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | focus | border-right-width | 2px | 1px |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | focus | border-bottom-width | 2px | 1px |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | focus | border-left-width | 2px | 1px |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | focus | border-top-left-radius | 0px | 6px |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | focus | font-size | 13.3333px | 14.4px |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | focus | line-height | normal | 21.6px |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | focus | height | 36px | 44px |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | focus | min-height | 36px | 44px |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | focus | width | 160px | 192px |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | focus | outline-style | auto | none |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | focus | outline-width | 1px | 3px |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | focus | offsetHeight | 36 | 44 |
| G25|text|en / 1件 / pages/contacts/ContactsPage.tsx:282 | focus | offsetWidth | 160 | 192 |
| G26|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:157 | normal | font-size | 13.6px | 14.4px |
| G26|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:157 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G26|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:157 | normal | line-height | normal | 21.6px |
| G26|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:157 | normal | background-color | rgb(245, 247, 250) | rgb(255, 255, 255) |
| G26|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:157 | normal | height | 33px | 44px |
| G26|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:157 | normal | min-height | 0px | 44px |
| G26|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:157 | normal | offsetHeight | 33 | 44 |
| G26|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:157 | focus | font-size | 13.6px | 14.4px |
| G26|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:157 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G26|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:157 | focus | line-height | normal | 21.6px |
| G26|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:157 | focus | background-color | rgb(245, 247, 250) | rgb(255, 255, 255) |
| G26|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:157 | focus | height | 33px | 44px |
| G26|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:157 | focus | min-height | 0px | 44px |
| G26|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:157 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G26|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:157 | focus | offsetHeight | 33 | 44 |
| G27|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:230 | normal | font-size | 13.6px | 14.4px |
| G27|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:230 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G27|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:230 | normal | line-height | normal | 21.6px |
| G27|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:230 | normal | background-color | rgb(245, 247, 250) | rgb(255, 255, 255) |
| G27|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:230 | focus | font-size | 13.6px | 14.4px |
| G27|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:230 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G27|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:230 | focus | line-height | normal | 21.6px |
| G27|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:230 | focus | background-color | rgb(245, 247, 250) | rgb(255, 255, 255) |
| G28|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:334 | normal | font-size | 13.6px | 14.4px |
| G28|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:334 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G28|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:334 | normal | line-height | normal | 21.6px |
| G28|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:334 | normal | background-color | rgb(245, 247, 250) | rgb(255, 255, 255) |
| G28|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:334 | focus | font-size | 13.6px | 14.4px |
| G28|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:334 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G28|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:334 | focus | line-height | normal | 21.6px |
| G28|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:334 | focus | background-color | rgb(245, 247, 250) | rgb(255, 255, 255) |
| G28|number|en / 1件 / pages/goal-setting/GoalSettingPage.tsx:334 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | normal | padding-top | 0px | 8px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | normal | padding-right | 0px | 12px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | normal | padding-bottom | 0px | 8px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | normal | padding-left | 0px | 12px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | normal | border-top-width | 2px | 1px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | normal | border-top-style | inset | solid |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | normal | border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | normal | border-right-width | 2px | 1px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | normal | border-bottom-width | 2px | 1px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | normal | border-left-width | 2px | 1px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | normal | border-top-left-radius | 0px | 6px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | normal | font-size | 13.3333px | 14.4px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | normal | font-family | monospace | "SF Pro Text", "Segoe UI", Roboto, Helvetica, Arial, sans-serif |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | normal | line-height | normal | 21.6px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | normal | height | 21.3281px | 44px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | normal | min-height | 0px | 44px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | normal | width | 209.328px | 363px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | normal | offsetHeight | 21 | 44 |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | normal | offsetWidth | 209 | 363 |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | focus | padding-top | 0px | 8px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | focus | padding-right | 0px | 12px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | focus | padding-bottom | 0px | 8px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | focus | padding-left | 0px | 12px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | focus | border-top-width | 2px | 1px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | focus | border-top-style | inset | solid |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | focus | border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | focus | border-right-width | 2px | 1px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | focus | border-bottom-width | 2px | 1px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | focus | border-left-width | 2px | 1px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | focus | border-top-left-radius | 0px | 6px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | focus | font-size | 13.3333px | 14.4px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | focus | font-family | monospace | "SF Pro Text", "Segoe UI", Roboto, Helvetica, Arial, sans-serif |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | focus | line-height | normal | 21.6px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | focus | height | 21.3281px | 44px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | focus | min-height | 0px | 44px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | focus | width | 209.328px | 363px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | focus | outline-style | auto | none |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | focus | outline-width | 1px | 3px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | focus | offsetHeight | 21 | 44 |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | focus | offsetWidth | 209 | 363 |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | disabled | padding-top | 0px | 8px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | disabled | padding-right | 0px | 12px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | disabled | padding-bottom | 0px | 8px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | disabled | padding-left | 0px | 12px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | disabled | border-top-width | 2px | 1px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | disabled | border-top-style | inset | solid |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | disabled | border-top-color | rgba(118, 118, 118, 0.3) | rgb(226, 232, 240) |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | disabled | border-right-width | 2px | 1px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | disabled | border-bottom-width | 2px | 1px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | disabled | border-left-width | 2px | 1px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | disabled | border-top-left-radius | 0px | 6px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | disabled | font-size | 13.3333px | 14.4px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | disabled | font-family | monospace | "SF Pro Text", "Segoe UI", Roboto, Helvetica, Arial, sans-serif |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | disabled | line-height | normal | 21.6px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | disabled | color | rgb(84, 84, 84) | rgb(26, 32, 44) |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | disabled | background-color | rgba(239, 239, 239, 0.3) | rgb(226, 232, 240) |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | disabled | height | 21.3281px | 44px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | disabled | min-height | 0px | 44px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | disabled | width | 209.328px | 363px |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | disabled | outline-color | rgb(84, 84, 84) | rgb(26, 32, 44) |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | disabled | cursor | default | not-allowed |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | disabled | opacity | 1 | 0.5 |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | disabled | offsetHeight | 21 | 44 |
| G01|datetime-local|dis / 1件 / pages/inbox/ManualRecordSection.tsx:148 | disabled | offsetWidth | 209 | 363 |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | normal | padding-top | 0px | 8px |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | normal | padding-right | 0px | 12px |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | normal | padding-bottom | 0px | 8px |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | normal | padding-left | 0px | 12px |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | normal | border-top-width | 2px | 1px |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | normal | border-top-style | inset | solid |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | normal | border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | normal | border-right-width | 2px | 1px |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | normal | border-bottom-width | 2px | 1px |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | normal | border-left-width | 2px | 1px |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | normal | border-top-left-radius | 0px | 6px |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | normal | font-size | 13.3333px | 14.4px |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | normal | line-height | normal | 21.6px |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | normal | height | 19px | 44px |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | normal | min-height | 0px | 44px |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | normal | width | 96px | 375px |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | normal | offsetHeight | 19 | 44 |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | normal | offsetWidth | 96 | 375 |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | focus | padding-top | 0px | 8px |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | focus | padding-right | 0px | 12px |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | focus | padding-bottom | 0px | 8px |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | focus | padding-left | 0px | 12px |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | focus | border-top-width | 2px | 1px |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | focus | border-top-style | inset | solid |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | focus | border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | focus | border-right-width | 2px | 1px |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | focus | border-bottom-width | 2px | 1px |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | focus | border-left-width | 2px | 1px |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | focus | border-top-left-radius | 0px | 6px |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | focus | font-size | 13.3333px | 14.4px |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | focus | line-height | normal | 21.6px |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | focus | height | 19px | 44px |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | focus | min-height | 0px | 44px |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | focus | width | 96px | 375px |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | focus | outline-style | auto | none |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | focus | outline-width | 1px | 3px |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | focus | offsetHeight | 19 | 44 |
| G12|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:287 | focus | offsetWidth | 96 | 375 |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | normal | padding-top | 0px | 8px |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | normal | padding-right | 0px | 12px |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | normal | padding-bottom | 0px | 8px |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | normal | padding-left | 0px | 12px |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | normal | border-top-width | 2px | 1px |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | normal | border-top-style | inset | solid |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | normal | border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | normal | border-right-width | 2px | 1px |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | normal | border-bottom-width | 2px | 1px |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | normal | border-left-width | 2px | 1px |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | normal | border-top-left-radius | 0px | 6px |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | normal | font-size | 13.3333px | 14.4px |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | normal | line-height | normal | 21.6px |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | normal | height | 19px | 44px |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | normal | min-height | 0px | 44px |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | normal | width | 112px | 375px |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | normal | offsetHeight | 19 | 44 |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | normal | offsetWidth | 112 | 375 |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | focus | padding-top | 0px | 8px |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | focus | padding-right | 0px | 12px |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | focus | padding-bottom | 0px | 8px |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | focus | padding-left | 0px | 12px |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | focus | border-top-width | 2px | 1px |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | focus | border-top-style | inset | solid |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | focus | border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | focus | border-right-width | 2px | 1px |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | focus | border-bottom-width | 2px | 1px |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | focus | border-left-width | 2px | 1px |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | focus | border-top-left-radius | 0px | 6px |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | focus | font-size | 13.3333px | 14.4px |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | focus | line-height | normal | 21.6px |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | focus | height | 19px | 44px |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | focus | min-height | 0px | 44px |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | focus | width | 112px | 375px |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | focus | outline-style | auto | none |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | focus | outline-width | 1px | 3px |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | focus | offsetHeight | 19 | 44 |
| G13|number|en / 2件 / pages/inventory/InventoryFilterPanel.tsx:295 | focus | offsetWidth | 112 | 375 |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | normal | padding-top | 0px | 8px |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | normal | padding-right | 0px | 12px |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | normal | padding-bottom | 0px | 8px |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | normal | padding-left | 0px | 12px |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | normal | border-top-width | 2px | 1px |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | normal | border-top-style | inset | solid |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | normal | border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | normal | border-right-width | 2px | 1px |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | normal | border-bottom-width | 2px | 1px |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | normal | border-left-width | 2px | 1px |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | normal | border-top-left-radius | 0px | 6px |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | normal | font-size | 13.3333px | 14.4px |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | normal | line-height | normal | 21.6px |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | normal | height | 36px | 44px |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | normal | min-height | 36px | 44px |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | normal | width | 280px | 192px |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | normal | offsetHeight | 36 | 44 |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | normal | offsetWidth | 280 | 192 |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | focus | padding-top | 0px | 8px |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | focus | padding-right | 0px | 12px |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | focus | padding-bottom | 0px | 8px |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | focus | padding-left | 0px | 12px |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | focus | border-top-width | 2px | 1px |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | focus | border-top-style | inset | solid |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | focus | border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | focus | border-right-width | 2px | 1px |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | focus | border-bottom-width | 2px | 1px |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | focus | border-left-width | 2px | 1px |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | focus | border-top-left-radius | 0px | 6px |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | focus | font-size | 13.3333px | 14.4px |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | focus | line-height | normal | 21.6px |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | focus | height | 36px | 44px |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | focus | min-height | 36px | 44px |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | focus | width | 280px | 192px |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | focus | outline-style | auto | none |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | focus | outline-width | 1px | 3px |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | focus | offsetHeight | 36 | 44 |
| G07|search|en / 2件 / pages/inventory/InventoryPage.tsx:384 | focus | offsetWidth | 280 | 192 |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | normal | padding-top | 0px | 8px |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | normal | padding-right | 0px | 12px |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | normal | padding-bottom | 0px | 8px |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | normal | padding-left | 0px | 12px |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | normal | border-top-width | 2px | 1px |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | normal | border-top-style | inset | solid |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | normal | border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | normal | border-right-width | 2px | 1px |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | normal | border-bottom-width | 2px | 1px |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | normal | border-left-width | 2px | 1px |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | normal | border-top-left-radius | 0px | 6px |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | normal | font-size | 13.3333px | 14.4px |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | normal | font-weight | 600 | 400 |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | normal | line-height | normal | 21.6px |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | normal | height | 19px | 44px |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | normal | min-height | 0px | 44px |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | normal | min-width | 280px | 0px |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | normal | offsetHeight | 19 | 44 |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | focus | padding-top | 0px | 8px |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | focus | padding-right | 0px | 12px |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | focus | padding-bottom | 0px | 8px |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | focus | padding-left | 0px | 12px |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | focus | border-top-width | 2px | 1px |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | focus | border-top-style | inset | solid |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | focus | border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | focus | border-right-width | 2px | 1px |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | focus | border-bottom-width | 2px | 1px |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | focus | border-left-width | 2px | 1px |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | focus | border-top-left-radius | 0px | 6px |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | focus | font-size | 13.3333px | 14.4px |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | focus | font-weight | 600 | 400 |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | focus | line-height | normal | 21.6px |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | focus | height | 19px | 44px |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | focus | min-height | 0px | 44px |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | focus | min-width | 280px | 0px |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | focus | outline-style | auto | none |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | focus | outline-width | 1px | 3px |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G14|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:343 | focus | offsetHeight | 19 | 44 |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | normal | padding-top | 0px | 8px |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | normal | padding-right | 0px | 12px |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | normal | padding-bottom | 0px | 8px |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | normal | padding-left | 0px | 12px |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | normal | border-top-width | 2px | 1px |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | normal | border-top-style | inset | solid |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | normal | border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | normal | border-right-width | 2px | 1px |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | normal | border-bottom-width | 2px | 1px |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | normal | border-left-width | 2px | 1px |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | normal | border-top-left-radius | 0px | 6px |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | normal | font-size | 13.6px | 14.4px |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | normal | line-height | normal | 21.6px |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | normal | color | rgb(74, 85, 104) | rgb(26, 32, 44) |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | normal | height | 19px | 44px |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | normal | min-height | 0px | 44px |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | normal | min-width | 280px | 0px |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | normal | margin-top | 4px | 0px |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | normal | outline-color | rgb(74, 85, 104) | rgb(26, 32, 44) |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | normal | offsetHeight | 19 | 44 |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | focus | padding-top | 0px | 8px |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | focus | padding-right | 0px | 12px |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | focus | padding-bottom | 0px | 8px |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | focus | padding-left | 0px | 12px |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | focus | border-top-width | 2px | 1px |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | focus | border-top-style | inset | solid |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | focus | border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | focus | border-right-width | 2px | 1px |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | focus | border-bottom-width | 2px | 1px |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | focus | border-left-width | 2px | 1px |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | focus | border-top-left-radius | 0px | 6px |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | focus | font-size | 13.6px | 14.4px |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | focus | line-height | normal | 21.6px |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | focus | color | rgb(74, 85, 104) | rgb(26, 32, 44) |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | focus | height | 19px | 44px |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | focus | min-height | 0px | 44px |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | focus | min-width | 280px | 0px |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | focus | margin-top | 4px | 0px |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | focus | outline-style | auto | none |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | focus | outline-width | 1px | 3px |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G15|omitted|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:350 | focus | offsetHeight | 19 | 44 |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | normal | padding-top | 0px | 8px |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | normal | padding-right | 0px | 12px |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | normal | padding-bottom | 0px | 8px |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | normal | padding-left | 0px | 12px |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | normal | border-top-width | 2px | 1px |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | normal | border-top-style | inset | solid |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | normal | border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | normal | border-right-width | 2px | 1px |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | normal | border-bottom-width | 2px | 1px |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | normal | border-left-width | 2px | 1px |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | normal | border-top-left-radius | 0px | 6px |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | normal | font-size | 13.3333px | 14.4px |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | normal | line-height | normal | 21.6px |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | normal | height | 19px | 44px |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | normal | min-height | 0px | 44px |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | normal | width | 80px | 343px |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | normal | offsetHeight | 19 | 44 |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | normal | offsetWidth | 80 | 343 |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | focus | padding-top | 0px | 8px |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | focus | padding-right | 0px | 12px |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | focus | padding-bottom | 0px | 8px |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | focus | padding-left | 0px | 12px |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | focus | border-top-width | 2px | 1px |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | focus | border-top-style | inset | solid |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | focus | border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | focus | border-right-width | 2px | 1px |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | focus | border-bottom-width | 2px | 1px |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | focus | border-left-width | 2px | 1px |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | focus | border-top-left-radius | 0px | 6px |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | focus | font-size | 13.3333px | 14.4px |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | focus | line-height | normal | 21.6px |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | focus | height | 19px | 44px |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | focus | min-height | 0px | 44px |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | focus | width | 80px | 343px |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | focus | outline-style | auto | none |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | focus | outline-width | 1px | 3px |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | focus | offsetHeight | 19 | 44 |
| G04|omitted|en / 4件 / pages/invoice-create/InvoiceCreatePage.tsx:368 | focus | offsetWidth | 80 | 343 |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | normal | padding-top | 0px | 8px |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | normal | padding-right | 0px | 12px |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | normal | padding-bottom | 0px | 8px |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | normal | padding-left | 0px | 12px |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | normal | border-top-width | 2px | 1px |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | normal | border-top-style | inset | solid |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | normal | border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | normal | border-right-width | 2px | 1px |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | normal | border-bottom-width | 2px | 1px |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | normal | border-left-width | 2px | 1px |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | normal | border-top-left-radius | 0px | 6px |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | normal | font-size | 13.3333px | 14.4px |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | normal | line-height | normal | 21.6px |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | normal | height | 19px | 44px |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | normal | min-height | 0px | 44px |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | normal | width | 70px | 343px |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | normal | offsetHeight | 19 | 44 |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | normal | offsetWidth | 70 | 343 |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | focus | padding-top | 0px | 8px |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | focus | padding-right | 0px | 12px |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | focus | padding-bottom | 0px | 8px |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | focus | padding-left | 0px | 12px |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | focus | border-top-width | 2px | 1px |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | focus | border-top-style | inset | solid |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | focus | border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | focus | border-right-width | 2px | 1px |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | focus | border-bottom-width | 2px | 1px |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | focus | border-left-width | 2px | 1px |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | focus | border-top-left-radius | 0px | 6px |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | focus | font-size | 13.3333px | 14.4px |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | focus | line-height | normal | 21.6px |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | focus | height | 19px | 44px |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | focus | min-height | 0px | 44px |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | focus | width | 70px | 343px |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | focus | outline-style | auto | none |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | focus | outline-width | 1px | 3px |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | focus | offsetHeight | 19 | 44 |
| G16|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:385 | focus | offsetWidth | 70 | 343 |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | normal | padding-top | 0px | 8px |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | normal | padding-right | 0px | 12px |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | normal | padding-bottom | 0px | 8px |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | normal | padding-left | 0px | 12px |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | normal | border-top-width | 2px | 1px |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | normal | border-top-style | inset | solid |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | normal | border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | normal | border-right-width | 2px | 1px |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | normal | border-bottom-width | 2px | 1px |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | normal | border-left-width | 2px | 1px |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | normal | border-top-left-radius | 0px | 6px |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | normal | font-size | 13.3333px | 14.4px |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | normal | line-height | normal | 21.6px |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | normal | height | 19px | 44px |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | normal | min-height | 0px | 44px |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | normal | width | 90px | 343px |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | normal | offsetHeight | 19 | 44 |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | normal | offsetWidth | 90 | 343 |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | focus | padding-top | 0px | 8px |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | focus | padding-right | 0px | 12px |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | focus | padding-bottom | 0px | 8px |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | focus | padding-left | 0px | 12px |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | focus | border-top-width | 2px | 1px |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | focus | border-top-style | inset | solid |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | focus | border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | focus | border-right-width | 2px | 1px |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | focus | border-bottom-width | 2px | 1px |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | focus | border-left-width | 2px | 1px |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | focus | border-top-left-radius | 0px | 6px |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | focus | font-size | 13.3333px | 14.4px |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | focus | line-height | normal | 21.6px |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | focus | height | 19px | 44px |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | focus | min-height | 0px | 44px |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | focus | width | 90px | 343px |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | focus | outline-style | auto | none |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | focus | outline-width | 1px | 3px |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | focus | offsetHeight | 19 | 44 |
| G17|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:388 | focus | offsetWidth | 90 | 343 |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | normal | padding-top | 0px | 8px |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | normal | padding-right | 0px | 12px |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | normal | padding-bottom | 0px | 8px |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | normal | padding-left | 0px | 12px |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | normal | border-top-width | 2px | 1px |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | normal | border-top-style | inset | solid |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | normal | border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | normal | border-right-width | 2px | 1px |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | normal | border-bottom-width | 2px | 1px |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | normal | border-left-width | 2px | 1px |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | normal | border-top-left-radius | 0px | 6px |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | normal | font-size | 13.3333px | 14.4px |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | normal | line-height | normal | 21.6px |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | normal | height | 19px | 44px |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | normal | min-height | 0px | 44px |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | normal | width | 80px | 343px |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | normal | offsetHeight | 19 | 44 |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | normal | offsetWidth | 80 | 343 |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | focus | padding-top | 0px | 8px |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | focus | padding-right | 0px | 12px |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | focus | padding-bottom | 0px | 8px |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | focus | padding-left | 0px | 12px |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | focus | border-top-width | 2px | 1px |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | focus | border-top-style | inset | solid |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | focus | border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | focus | border-right-width | 2px | 1px |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | focus | border-bottom-width | 2px | 1px |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | focus | border-left-width | 2px | 1px |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | focus | border-top-left-radius | 0px | 6px |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | focus | font-size | 13.3333px | 14.4px |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | focus | line-height | normal | 21.6px |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | focus | height | 19px | 44px |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | focus | min-height | 0px | 44px |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | focus | width | 80px | 343px |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | focus | outline-style | auto | none |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | focus | outline-width | 1px | 3px |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | focus | offsetHeight | 19 | 44 |
| G04|number|en / 2件 / pages/invoice-create/InvoiceCreatePage.tsx:391 | focus | offsetWidth | 80 | 343 |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | normal | padding-right | 8px | 12px |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | normal | padding-left | 8px | 12px |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | normal | border-top-left-radius | 4px | 6px |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | normal | font-size | 13.6px | 14.4px |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | normal | line-height | normal | 21.6px |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | normal | height | 33px | 44px |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | normal | min-height | 0px | 44px |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | normal | width | 163px | 375px |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | normal | flex-grow | 1 | 0 |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | normal | offsetHeight | 33 | 44 |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | normal | offsetWidth | 163 | 375 |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | focus | padding-right | 8px | 12px |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | focus | padding-left | 8px | 12px |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | focus | border-top-color | rgb(226, 232, 240) | rgb(30, 58, 138) |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | focus | border-top-left-radius | 4px | 6px |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | focus | font-size | 13.6px | 14.4px |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | focus | line-height | normal | 21.6px |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | focus | height | 33px | 44px |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | focus | min-height | 0px | 44px |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | focus | width | 163px | 375px |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | focus | flex-grow | 1 | 0 |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | focus | outline-style | auto | none |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | focus | outline-width | 1px | 3px |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | focus | offsetHeight | 33 | 44 |
| G29|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:241 | focus | offsetWidth | 163 | 375 |
| G30|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:290 | normal | padding-right | 8px | 12px |
| G30|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:290 | normal | padding-left | 8px | 12px |
| G30|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:290 | normal | border-top-left-radius | 4px | 6px |
| G30|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:290 | normal | font-size | 13.3333px | 14.4px |
| G30|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:290 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G30|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:290 | normal | line-height | normal | 21.6px |
| G30|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:290 | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G30|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:290 | normal | height | 33px | 44px |
| G30|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:290 | normal | min-height | 0px | 44px |
| G30|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:290 | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G30|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:290 | normal | offsetHeight | 33 | 44 |
| G30|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:290 | focus | padding-right | 8px | 12px |
| G30|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:290 | focus | padding-left | 8px | 12px |
| G30|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:290 | focus | border-top-color | rgb(226, 232, 240) | rgb(30, 58, 138) |
| G30|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:290 | focus | border-top-left-radius | 4px | 6px |
| G30|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:290 | focus | font-size | 13.3333px | 14.4px |
| G30|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:290 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G30|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:290 | focus | line-height | normal | 21.6px |
| G30|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:290 | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G30|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:290 | focus | height | 33px | 44px |
| G30|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:290 | focus | min-height | 0px | 44px |
| G30|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:290 | focus | outline-style | auto | none |
| G30|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:290 | focus | outline-width | 1px | 3px |
| G30|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:290 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G30|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:290 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G30|omitted|en / 1件 / pages/invoice-detail/InvoiceDetailPage.tsx:290 | focus | offsetHeight | 33 | 44 |
| G02|omitted|en / 5件 / pages/products/ProductEditPage.tsx:215 (保留) | normal | border-top-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| G02|omitted|en / 5件 / pages/products/ProductEditPage.tsx:215 (保留) | normal | border-top-left-radius | 4px | 6px |
| G02|omitted|en / 5件 / pages/products/ProductEditPage.tsx:215 (保留) | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G02|omitted|en / 5件 / pages/products/ProductEditPage.tsx:215 (保留) | normal | line-height | normal | 21.6px |
| G02|omitted|en / 5件 / pages/products/ProductEditPage.tsx:215 (保留) | normal | height | 34px | 44px |
| G02|omitted|en / 5件 / pages/products/ProductEditPage.tsx:215 (保留) | normal | min-height | 0px | 44px |
| G02|omitted|en / 5件 / pages/products/ProductEditPage.tsx:215 (保留) | normal | offsetHeight | 34 | 44 |
| G02|omitted|en / 5件 / pages/products/ProductEditPage.tsx:215 (保留) | focus | border-top-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| G02|omitted|en / 5件 / pages/products/ProductEditPage.tsx:215 (保留) | focus | border-top-left-radius | 4px | 6px |
| G02|omitted|en / 5件 / pages/products/ProductEditPage.tsx:215 (保留) | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G02|omitted|en / 5件 / pages/products/ProductEditPage.tsx:215 (保留) | focus | line-height | normal | 21.6px |
| G02|omitted|en / 5件 / pages/products/ProductEditPage.tsx:215 (保留) | focus | height | 34px | 44px |
| G02|omitted|en / 5件 / pages/products/ProductEditPage.tsx:215 (保留) | focus | min-height | 0px | 44px |
| G02|omitted|en / 5件 / pages/products/ProductEditPage.tsx:215 (保留) | focus | offsetHeight | 34 | 44 |
| G02|date|en / 1件 / pages/products/ProductEditPage.tsx:262 (保留) | normal | border-top-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| G02|date|en / 1件 / pages/products/ProductEditPage.tsx:262 (保留) | normal | border-top-left-radius | 4px | 6px |
| G02|date|en / 1件 / pages/products/ProductEditPage.tsx:262 (保留) | normal | font-family | monospace | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G02|date|en / 1件 / pages/products/ProductEditPage.tsx:262 (保留) | normal | line-height | normal | 21.6px |
| G02|date|en / 1件 / pages/products/ProductEditPage.tsx:262 (保留) | normal | height | 37px | 44px |
| G02|date|en / 1件 / pages/products/ProductEditPage.tsx:262 (保留) | normal | min-height | 0px | 44px |
| G02|date|en / 1件 / pages/products/ProductEditPage.tsx:262 (保留) | normal | offsetHeight | 37 | 44 |
| G02|date|en / 1件 / pages/products/ProductEditPage.tsx:262 (保留) | focus | border-top-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| G02|date|en / 1件 / pages/products/ProductEditPage.tsx:262 (保留) | focus | border-top-left-radius | 4px | 6px |
| G02|date|en / 1件 / pages/products/ProductEditPage.tsx:262 (保留) | focus | font-family | monospace | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G02|date|en / 1件 / pages/products/ProductEditPage.tsx:262 (保留) | focus | line-height | normal | 21.6px |
| G02|date|en / 1件 / pages/products/ProductEditPage.tsx:262 (保留) | focus | height | 37px | 44px |
| G02|date|en / 1件 / pages/products/ProductEditPage.tsx:262 (保留) | focus | min-height | 0px | 44px |
| G02|date|en / 1件 / pages/products/ProductEditPage.tsx:262 (保留) | focus | offsetHeight | 37 | 44 |
| G02|number|en / 7件 / pages/products/ProductEditPage.tsx:294 (保留) | normal | border-top-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| G02|number|en / 7件 / pages/products/ProductEditPage.tsx:294 (保留) | normal | border-top-left-radius | 4px | 6px |
| G02|number|en / 7件 / pages/products/ProductEditPage.tsx:294 (保留) | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G02|number|en / 7件 / pages/products/ProductEditPage.tsx:294 (保留) | normal | line-height | normal | 21.6px |
| G02|number|en / 7件 / pages/products/ProductEditPage.tsx:294 (保留) | normal | height | 34px | 44px |
| G02|number|en / 7件 / pages/products/ProductEditPage.tsx:294 (保留) | normal | min-height | 0px | 44px |
| G02|number|en / 7件 / pages/products/ProductEditPage.tsx:294 (保留) | normal | offsetHeight | 34 | 44 |
| G02|number|en / 7件 / pages/products/ProductEditPage.tsx:294 (保留) | focus | border-top-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| G02|number|en / 7件 / pages/products/ProductEditPage.tsx:294 (保留) | focus | border-top-left-radius | 4px | 6px |
| G02|number|en / 7件 / pages/products/ProductEditPage.tsx:294 (保留) | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G02|number|en / 7件 / pages/products/ProductEditPage.tsx:294 (保留) | focus | line-height | normal | 21.6px |
| G02|number|en / 7件 / pages/products/ProductEditPage.tsx:294 (保留) | focus | height | 34px | 44px |
| G02|number|en / 7件 / pages/products/ProductEditPage.tsx:294 (保留) | focus | min-height | 0px | 44px |
| G02|number|en / 7件 / pages/products/ProductEditPage.tsx:294 (保留) | focus | offsetHeight | 34 | 44 |
| G02|url|en / 1件 / pages/products/ProductEditPage.tsx:298 (保留) | normal | border-top-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| G02|url|en / 1件 / pages/products/ProductEditPage.tsx:298 (保留) | normal | border-top-left-radius | 4px | 6px |
| G02|url|en / 1件 / pages/products/ProductEditPage.tsx:298 (保留) | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G02|url|en / 1件 / pages/products/ProductEditPage.tsx:298 (保留) | normal | line-height | normal | 21.6px |
| G02|url|en / 1件 / pages/products/ProductEditPage.tsx:298 (保留) | normal | height | 34px | 44px |
| G02|url|en / 1件 / pages/products/ProductEditPage.tsx:298 (保留) | normal | min-height | 0px | 44px |
| G02|url|en / 1件 / pages/products/ProductEditPage.tsx:298 (保留) | normal | offsetHeight | 34 | 44 |
| G02|url|en / 1件 / pages/products/ProductEditPage.tsx:298 (保留) | focus | border-top-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| G02|url|en / 1件 / pages/products/ProductEditPage.tsx:298 (保留) | focus | border-top-left-radius | 4px | 6px |
| G02|url|en / 1件 / pages/products/ProductEditPage.tsx:298 (保留) | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G02|url|en / 1件 / pages/products/ProductEditPage.tsx:298 (保留) | focus | line-height | normal | 21.6px |
| G02|url|en / 1件 / pages/products/ProductEditPage.tsx:298 (保留) | focus | height | 34px | 44px |
| G02|url|en / 1件 / pages/products/ProductEditPage.tsx:298 (保留) | focus | min-height | 0px | 44px |
| G02|url|en / 1件 / pages/products/ProductEditPage.tsx:298 (保留) | focus | offsetHeight | 34 | 44 |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | normal | padding-top | 0px | 8px |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | normal | padding-right | 0px | 12px |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | normal | padding-bottom | 0px | 8px |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | normal | padding-left | 0px | 12px |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | normal | border-top-width | 2px | 1px |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | normal | border-top-style | inset | solid |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | normal | border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | normal | border-right-width | 2px | 1px |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | normal | border-bottom-width | 2px | 1px |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | normal | border-left-width | 2px | 1px |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | normal | border-top-left-radius | 0px | 6px |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | normal | font-size | 13.3333px | 14.4px |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | normal | line-height | normal | 21.6px |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | normal | height | 19px | 44px |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | normal | min-height | 0px | 44px |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | normal | width | 149px | 347px |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | normal | offsetHeight | 19 | 44 |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | normal | offsetWidth | 149 | 347 |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | focus | padding-top | 0px | 8px |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | focus | padding-right | 0px | 12px |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | focus | padding-bottom | 0px | 8px |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | focus | padding-left | 0px | 12px |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | focus | border-top-width | 2px | 1px |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | focus | border-top-style | inset | solid |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | focus | border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | focus | border-right-width | 2px | 1px |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | focus | border-bottom-width | 2px | 1px |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | focus | border-left-width | 2px | 1px |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | focus | border-top-left-radius | 0px | 6px |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | focus | font-size | 13.3333px | 14.4px |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | focus | line-height | normal | 21.6px |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | focus | height | 19px | 44px |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | focus | min-height | 0px | 44px |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | focus | width | 149px | 347px |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | focus | outline-style | auto | none |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | focus | outline-width | 1px | 3px |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | focus | offsetHeight | 19 | 44 |
| G01|text|en / 35件 / pages/register/CountryCombobox.tsx:46 | focus | offsetWidth | 149 | 347 |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | normal | padding-top | 0px | 8px |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | normal | padding-right | 0px | 12px |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | normal | padding-bottom | 0px | 8px |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | normal | padding-left | 0px | 12px |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | normal | border-top-width | 2px | 1px |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | normal | border-top-style | inset | solid |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | normal | border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | normal | border-right-width | 2px | 1px |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | normal | border-bottom-width | 2px | 1px |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | normal | border-left-width | 2px | 1px |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | normal | border-top-left-radius | 0px | 6px |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | normal | font-size | 13.3333px | 14.4px |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | normal | line-height | normal | 21.6px |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | normal | height | 19px | 44px |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | normal | min-height | 0px | 44px |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | normal | width | 149px | 347px |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | normal | flex-grow | 1 | 0 |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | normal | offsetHeight | 19 | 44 |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | normal | offsetWidth | 149 | 347 |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | focus | padding-top | 0px | 8px |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | focus | padding-right | 0px | 12px |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | focus | padding-bottom | 0px | 8px |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | focus | padding-left | 0px | 12px |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | focus | border-top-width | 2px | 1px |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | focus | border-top-style | inset | solid |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | focus | border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | focus | border-right-width | 2px | 1px |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | focus | border-bottom-width | 2px | 1px |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | focus | border-left-width | 2px | 1px |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | focus | border-top-left-radius | 0px | 6px |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | focus | font-size | 13.3333px | 14.4px |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | focus | line-height | normal | 21.6px |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | focus | height | 19px | 44px |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | focus | min-height | 0px | 44px |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | focus | width | 149px | 347px |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | focus | flex-grow | 1 | 0 |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | focus | outline-style | auto | none |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | focus | outline-width | 1px | 3px |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | focus | offsetHeight | 19 | 44 |
| G05|tel|en / 4件 / pages/register/RegisterAddressPage.tsx:344 | focus | offsetWidth | 149 | 347 |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | normal | padding-top | 0px | 8px |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | normal | padding-right | 0px | 12px |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | normal | padding-bottom | 0px | 8px |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | normal | padding-left | 0px | 12px |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | normal | border-top-width | 2px | 1px |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | normal | border-top-style | inset | solid |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | normal | border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | normal | border-right-width | 2px | 1px |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | normal | border-bottom-width | 2px | 1px |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | normal | border-left-width | 2px | 1px |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | normal | border-top-left-radius | 0px | 6px |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | normal | font-size | 13.3333px | 14.4px |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | normal | line-height | normal | 21.6px |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | normal | height | 19px | 44px |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | normal | min-height | 0px | 44px |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | normal | width | 149px | 347px |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | normal | offsetHeight | 19 | 44 |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | normal | offsetWidth | 149 | 347 |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | focus | padding-top | 0px | 8px |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | focus | padding-right | 0px | 12px |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | focus | padding-bottom | 0px | 8px |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | focus | padding-left | 0px | 12px |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | focus | border-top-width | 2px | 1px |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | focus | border-top-style | inset | solid |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | focus | border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | focus | border-right-width | 2px | 1px |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | focus | border-bottom-width | 2px | 1px |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | focus | border-left-width | 2px | 1px |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | focus | border-top-left-radius | 0px | 6px |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | focus | font-size | 13.3333px | 14.4px |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | focus | line-height | normal | 21.6px |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | focus | height | 19px | 44px |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | focus | min-height | 0px | 44px |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | focus | width | 149px | 347px |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | focus | outline-style | auto | none |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | focus | outline-width | 1px | 3px |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | focus | offsetHeight | 19 | 44 |
| G01|email|en / 5件 / pages/register/RegisterAddressPage.tsx:357 | focus | offsetWidth | 149 | 347 |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | normal | padding-top | 0px | 8px |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | normal | padding-right | 0px | 12px |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | normal | padding-bottom | 0px | 8px |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | normal | padding-left | 0px | 12px |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | normal | border-top-width | 2px | 1px |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | normal | border-top-style | inset | solid |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | normal | border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | normal | border-right-width | 2px | 1px |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | normal | border-bottom-width | 2px | 1px |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | normal | border-left-width | 2px | 1px |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | normal | border-top-left-radius | 0px | 6px |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | normal | font-size | 13.3333px | 14.4px |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | normal | line-height | normal | 21.6px |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | normal | height | 19px | 44px |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | normal | min-height | 0px | 44px |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | normal | width | 149px | 347px |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | normal | offsetHeight | 19 | 44 |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | normal | offsetWidth | 149 | 347 |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | focus | padding-top | 0px | 8px |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | focus | padding-right | 0px | 12px |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | focus | padding-bottom | 0px | 8px |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | focus | padding-left | 0px | 12px |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | focus | border-top-width | 2px | 1px |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | focus | border-top-style | inset | solid |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | focus | border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | focus | border-right-width | 2px | 1px |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | focus | border-bottom-width | 2px | 1px |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | focus | border-left-width | 2px | 1px |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | focus | border-top-left-radius | 0px | 6px |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | focus | font-size | 13.3333px | 14.4px |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | focus | line-height | normal | 21.6px |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | focus | height | 19px | 44px |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | focus | min-height | 0px | 44px |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | focus | width | 149px | 347px |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | focus | outline-style | auto | none |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | focus | outline-width | 1px | 3px |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | focus | offsetHeight | 19 | 44 |
| G01|tel|en / 1件 / pages/register/RegisterPage.tsx:529 | focus | offsetWidth | 149 | 347 |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | normal | padding-top | 0px | 8px |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | normal | padding-right | 0px | 12px |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | normal | padding-bottom | 0px | 8px |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | normal | padding-left | 0px | 12px |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | normal | border-top-width | 2px | 1px |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | normal | border-top-style | inset | solid |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | normal | border-top-color | rgb(118, 118, 118) | rgb(226, 232, 240) |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | normal | border-right-width | 2px | 1px |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | normal | border-bottom-width | 2px | 1px |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | normal | border-left-width | 2px | 1px |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | normal | border-top-left-radius | 0px | 6px |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | normal | font-size | 13.3333px | 14.4px |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | normal | line-height | normal | 21.6px |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | normal | height | 19px | 44px |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | normal | min-height | 0px | 44px |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | normal | max-width | 100% | none |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | normal | offsetHeight | 19 | 44 |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | focus | padding-top | 0px | 8px |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | focus | padding-right | 0px | 12px |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | focus | padding-bottom | 0px | 8px |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | focus | padding-left | 0px | 12px |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | focus | border-top-width | 2px | 1px |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | focus | border-top-style | inset | solid |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | focus | border-top-color | rgb(118, 118, 118) | rgb(30, 58, 138) |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | focus | border-right-width | 2px | 1px |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | focus | border-bottom-width | 2px | 1px |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | focus | border-left-width | 2px | 1px |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | focus | border-top-left-radius | 0px | 6px |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | focus | font-size | 13.3333px | 14.4px |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | focus | line-height | normal | 21.6px |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | focus | height | 19px | 44px |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | focus | min-height | 0px | 44px |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | focus | max-width | 100% | none |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | focus | outline-style | auto | none |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | focus | outline-width | 1px | 3px |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G18|omitted|en / 2件 / pages/super-admin/KnowledgeAliasesTab.tsx:296 | focus | offsetHeight | 19 | 44 |
| G32|number|en / 1件 / pages/super-admin/TcgLineImportPage.tsx:353 | normal | padding-top | 6.4px | 8px |
| G32|number|en / 1件 / pages/super-admin/TcgLineImportPage.tsx:353 | normal | padding-right | 9.6px | 12px |
| G32|number|en / 1件 / pages/super-admin/TcgLineImportPage.tsx:353 | normal | padding-bottom | 6.4px | 8px |
| G32|number|en / 1件 / pages/super-admin/TcgLineImportPage.tsx:353 | normal | padding-left | 9.6px | 12px |
| G32|number|en / 1件 / pages/super-admin/TcgLineImportPage.tsx:353 | normal | border-top-color | rgb(204, 204, 204) | rgb(226, 232, 240) |
| G32|number|en / 1件 / pages/super-admin/TcgLineImportPage.tsx:353 | normal | border-top-left-radius | 4px | 6px |
| G32|number|en / 1件 / pages/super-admin/TcgLineImportPage.tsx:353 | normal | font-size | 13.6px | 14.4px |
| G32|number|en / 1件 / pages/super-admin/TcgLineImportPage.tsx:353 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G32|number|en / 1件 / pages/super-admin/TcgLineImportPage.tsx:353 | normal | line-height | normal | 21.6px |
| G32|number|en / 1件 / pages/super-admin/TcgLineImportPage.tsx:353 | normal | background-color | rgb(245, 247, 250) | rgb(255, 255, 255) |
| G32|number|en / 1件 / pages/super-admin/TcgLineImportPage.tsx:353 | normal | height | 29.7812px | 44px |
| G32|number|en / 1件 / pages/super-admin/TcgLineImportPage.tsx:353 | normal | min-height | 0px | 44px |
| G32|number|en / 1件 / pages/super-admin/TcgLineImportPage.tsx:353 | normal | width | 80px | 375px |
| G32|number|en / 1件 / pages/super-admin/TcgLineImportPage.tsx:353 | normal | offsetHeight | 30 | 44 |
| G32|number|en / 1件 / pages/super-admin/TcgLineImportPage.tsx:353 | normal | offsetWidth | 80 | 375 |
| G32|number|en / 1件 / pages/super-admin/TcgLineImportPage.tsx:353 | focus | padding-top | 6.4px | 8px |
| G32|number|en / 1件 / pages/super-admin/TcgLineImportPage.tsx:353 | focus | padding-right | 9.6px | 12px |
| G32|number|en / 1件 / pages/super-admin/TcgLineImportPage.tsx:353 | focus | padding-bottom | 6.4px | 8px |
| G32|number|en / 1件 / pages/super-admin/TcgLineImportPage.tsx:353 | focus | padding-left | 9.6px | 12px |
| G32|number|en / 1件 / pages/super-admin/TcgLineImportPage.tsx:353 | focus | border-top-color | rgb(204, 204, 204) | rgb(226, 232, 240) |
| G32|number|en / 1件 / pages/super-admin/TcgLineImportPage.tsx:353 | focus | border-top-left-radius | 4px | 6px |
| G32|number|en / 1件 / pages/super-admin/TcgLineImportPage.tsx:353 | focus | font-size | 13.6px | 14.4px |
| G32|number|en / 1件 / pages/super-admin/TcgLineImportPage.tsx:353 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G32|number|en / 1件 / pages/super-admin/TcgLineImportPage.tsx:353 | focus | line-height | normal | 21.6px |
| G32|number|en / 1件 / pages/super-admin/TcgLineImportPage.tsx:353 | focus | background-color | rgb(245, 247, 250) | rgb(255, 255, 255) |
| G32|number|en / 1件 / pages/super-admin/TcgLineImportPage.tsx:353 | focus | height | 29.7812px | 44px |
| G32|number|en / 1件 / pages/super-admin/TcgLineImportPage.tsx:353 | focus | min-height | 0px | 44px |
| G32|number|en / 1件 / pages/super-admin/TcgLineImportPage.tsx:353 | focus | width | 80px | 375px |
| G32|number|en / 1件 / pages/super-admin/TcgLineImportPage.tsx:353 | focus | offsetHeight | 30 | 44 |
| G32|number|en / 1件 / pages/super-admin/TcgLineImportPage.tsx:353 | focus | offsetWidth | 80 | 375 |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | normal | padding-top | 6.4px | 8px |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | normal | padding-right | 9.6px | 12px |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | normal | padding-bottom | 6.4px | 8px |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | normal | padding-left | 9.6px | 12px |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | normal | border-top-color | rgb(204, 204, 204) | rgb(226, 232, 240) |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | normal | border-top-left-radius | 4px | 6px |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | normal | font-size | 13.6px | 14.4px |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | normal | line-height | normal | 21.6px |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | normal | background-color | rgb(245, 247, 250) | rgb(255, 255, 255) |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | normal | height | 29.7812px | 44px |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | normal | min-height | 0px | 44px |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | normal | width | 200px | 375px |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | normal | min-width | 200px | 0px |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | normal | offsetHeight | 30 | 44 |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | normal | offsetWidth | 200 | 375 |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | focus | padding-top | 6.4px | 8px |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | focus | padding-right | 9.6px | 12px |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | focus | padding-bottom | 6.4px | 8px |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | focus | padding-left | 9.6px | 12px |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | focus | border-top-color | rgb(204, 204, 204) | rgb(226, 232, 240) |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | focus | border-top-left-radius | 4px | 6px |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | focus | font-size | 13.6px | 14.4px |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | focus | line-height | normal | 21.6px |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | focus | background-color | rgb(245, 247, 250) | rgb(255, 255, 255) |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | focus | height | 29.7812px | 44px |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | focus | min-height | 0px | 44px |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | focus | width | 200px | 375px |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | focus | min-width | 200px | 0px |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | focus | offsetHeight | 30 | 44 |
| G19|text|en / 2件 / pages/super-admin/TcgLineImportPage.tsx:374 | focus | offsetWidth | 200 | 375 |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | normal | padding-top | 4px | 8px |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | normal | padding-right | 8px | 12px |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | normal | padding-bottom | 4px | 8px |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | normal | padding-left | 8px | 12px |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | normal | border-top-left-radius | 4px | 6px |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | normal | font-size | 13.3333px | 14.4px |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | normal | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | normal | line-height | normal | 21.6px |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | normal | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | normal | height | 25px | 44px |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | normal | min-height | auto | 44px |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | normal | width | 80px | 327px |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | normal | outline-color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | normal | offsetHeight | 25 | 44 |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | normal | offsetWidth | 80 | 327 |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | focus | padding-top | 4px | 8px |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | focus | padding-right | 8px | 12px |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | focus | padding-bottom | 4px | 8px |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | focus | padding-left | 8px | 12px |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | focus | border-top-color | rgb(226, 232, 240) | rgb(30, 58, 138) |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | focus | border-top-left-radius | 4px | 6px |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | focus | font-size | 13.3333px | 14.4px |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | focus | font-family | Arial | -apple-system, "system-ui", "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | focus | line-height | normal | 21.6px |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | focus | color | rgb(0, 0, 0) | rgb(26, 32, 44) |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | focus | height | 25px | 44px |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | focus | min-height | auto | 44px |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | focus | width | 80px | 327px |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | focus | outline-style | auto | none |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | focus | outline-width | 1px | 3px |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | focus | outline-color | rgb(0, 95, 204) | rgb(26, 32, 44) |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | focus | box-shadow | none | rgba(30, 58, 138, 0.15) 0px 0px 0px 3px |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | focus | offsetHeight | 25 | 44 |
| G31|number|en / 1件 / pages/super-admin/components/AnalysisDashboardPanel.tsx:804 | focus | offsetWidth | 80 | 327 |

