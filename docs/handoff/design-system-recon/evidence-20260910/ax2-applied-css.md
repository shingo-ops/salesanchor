# AX-2 適用CSS（静的解決。postcss + JSX 祖先連鎖。origin/main dfcd31c05）

手法: av2-select-mapping.cjs と同じ（ax2-applied.cjs / ax2-css.cjs / ax2-project.cjs）。対象 53 件（components/Textarea.tsx の金型内 textarea は除外）。

全画面共通で読み込まれる CSS（main.tsx / App.tsx の import、読込順）:
- frontend/src/index.css
- frontend/src/tokens.css
- frontend/src/components/field-size.css
- frontend/src/loading-animations.css
- frontend/src/sidebar.css
- frontend/src/topbar.css
- frontend/src/components.css
- frontend/src/pages-layout.css
- frontend/src/hub-shell.css
- frontend/src/company-forms.css
- frontend/src/responsive.css

凡例: loadedVia = global（共通）/ forward（textarea のあるファイルから import で辿れる CSS）/ reverse（そのファイルを import する側＝画面側が読む CSS）。
`applied` は祖先まで一致が確定した規則、`unconfirmed` は祖先の判定が静的に確定できなかった規則（理由付き）。

## components/MergeLeadModal.tsx:234

- 開始タグ: `<textarea rows={2} placeholder={t("mergeLead.reasonPlaceholder")} value={reason} onChange={(e) => setReason(e.target.value)} maxLength={500} />`
- className: (なし) / 静的トークン: [] / 条件付き: []
- 属性: {"rows":"{2}","placeholder":"{t(\"mergeLead.reasonPlaceholder\")}","maxLength":"{500}"}
- inline style: なし
- 祖先連鎖: 4 本（異なるシグネチャ 4）。先頭: div.form-row < div.modal-content-wide < div.comp-modal-body < div.comp-modal-dialog < div.comp-modal-overlay < div < div.page-layout < div.hub-content < div.hub-shell < div < div.page-layout < main.mobile-content < div.mobile-shell < main.mobile-content < div.mobile-shell
- 画面側CSS import: own=[] / forward(共通除く)=["components/Button.css","constants/platform-icon.css","components/Modal.css"] / reverse=[]

| file:line | selector | 特異度 | 状態 | 読込 | 宣言 |
|---|---|---|---|---|---|
| company-forms.css:154 | `.modal-content-wide .form-row textarea` | (0,2,1) | base | global | padding: var(--space-2) var(--space-3) (L158); border: 1px solid var(--border-strong) (L159); border-radius: var(--radius-md) (L160); font-size: var(--font-base) (L161); background: var(--bg-surface) (L162); color: var(--text-primary) (L163); width: 100% (L164); box-sizing: border-box (L165); font-family: inherit (L166) |
| company-forms.css:169 | `.modal-content-wide .form-row textarea` | (0,2,1) | base | global | min-height: var(--textarea-min-h) (L171); resize: vertical (L172) |
| company-forms.css:177 | `.modal-content-wide .form-row textarea:focus` | (0,3,1) | self:focus | global | outline: none (L181); border-color: var(--accent) (L182); box-shadow: var(--focus-ring-shadow) (L183) |

## components/OrderFinancialPanel.tsx:239

- 開始タグ: `<textarea value={notes} onChange={(e) => setNotes(e.target.value)} aria-label={t("financial.notesAriaLabel")} />`
- className: (なし) / 静的トークン: [] / 条件付き: []
- 属性: {}
- inline style: なし
- 祖先連鎖: 2 本（異なるシグネチャ 2）。先頭: div.form-group < form < div.comp-modal-body < div.comp-modal-dialog < div.comp-modal-overlay < div < div.page-layout < main.mobile-content < div.mobile-shell
- 画面側CSS import: own=[] / forward(共通除く)=["components/Button.css","constants/platform-icon.css","components/Modal.css"] / reverse=[]

| file:line | selector | 特異度 | 状態 | 読込 | 宣言 |
|---|---|---|---|---|---|
| components.css:19 | `.form-group textarea` | (0,1,1) | base | global | width: 100% (L21); padding: var(--space-2) var(--space-3) (L22); border: 1px solid var(--border) (L23); border-radius: var(--radius-sm) (L24); font-size: var(--font-base) (L25); color: var(--text-primary) (L26); background: var(--bg-surface) (L27); box-sizing: border-box (L28) |
| components.css:31 | `.form-group textarea:focus` | (0,2,1) | self:focus | global | outline: none (L33); border-color: var(--accent) (L34); box-shadow: var(--focus-ring-shadow) (L35) |
| components.css:39 | `.form-group textarea` | (0,1,1) | base | global | min-height: var(--textarea-min-h) (L40); resize: vertical (L41) |

## components/PriorityScoreOverride.tsx:91

- 開始タグ: `<textarea value={note} onChange={(e) => setNote(e.target.value)} maxLength={500} placeholder={t("priority.overrideNotePlaceholder")} />`
- className: (なし) / 静的トークン: [] / 条件付き: []
- 属性: {"maxLength":"{500}","placeholder":"{t(\"priority.overrideNotePlaceholder\")}"}
- inline style: なし
- 祖先連鎖: 1 本（異なるシグネチャ 1）。先頭: div.form-group < form < div.comp-modal-body < div.comp-modal-dialog < div.comp-modal-overlay
- 画面側CSS import: own=[] / forward(共通除く)=["components/Button.css","constants/platform-icon.css","components/Modal.css"] / reverse=[]

| file:line | selector | 特異度 | 状態 | 読込 | 宣言 |
|---|---|---|---|---|---|
| components.css:19 | `.form-group textarea` | (0,1,1) | base | global | width: 100% (L21); padding: var(--space-2) var(--space-3) (L22); border: 1px solid var(--border) (L23); border-radius: var(--radius-sm) (L24); font-size: var(--font-base) (L25); color: var(--text-primary) (L26); background: var(--bg-surface) (L27); box-sizing: border-box (L28) |
| components.css:31 | `.form-group textarea:focus` | (0,2,1) | self:focus | global | outline: none (L33); border-color: var(--accent) (L34); box-shadow: var(--focus-ring-shadow) (L35) |
| components.css:39 | `.form-group textarea` | (0,1,1) | base | global | min-height: var(--textarea-min-h) (L40); resize: vertical (L41) |

未確定（unconfirmed）:
- company-forms.css:254 `.product-edit-form .form-group textarea` — 静的判定理由: no JSX usage found for PriorityScoreOverride (frontend/src/components/PriorityScoreOverride.tsx)。**手動解決**: クラス product-edit-form が JSX に現れるのは pages/products/ProductEditPage.tsx:209 のみ（grep）→ この textarea には一致しない
- features/tcg-analysis-review/supplier-detail-view.css:244 `.pmd-field textarea` — 静的判定理由: no JSX usage found for PriorityScoreOverride (frontend/src/components/PriorityScoreOverride.tsx)。**手動解決**: クラス pmd-field が JSX に現れるのは features/tcg-analysis-review/ProductMasterDrawer.tsx のみ（grep）→ この textarea には一致しない
- features/tcg-analysis-review/supplier-detail-view.css:255 `.pmd-field textarea` — 静的判定理由: no JSX usage found for PriorityScoreOverride (frontend/src/components/PriorityScoreOverride.tsx)。**手動解決**: クラス pmd-field が JSX に現れるのは features/tcg-analysis-review/ProductMasterDrawer.tsx のみ（grep）→ この textarea には一致しない

## components/PurchaseDetailPanel.tsx:442

- 開始タグ: `<textarea value={form.purchase_note} onChange={(ev) => setField("purchase_note", ev.target.value)} data-testid="pur-input-purchase_note" />`
- className: (なし) / 静的トークン: [] / 条件付き: []
- 属性: {}
- inline style: なし
- 祖先連鎖: 2 本（異なるシグネチャ 2）。先頭: div.form-group < form < div.comp-modal-body < div.comp-modal-dialog < div.comp-modal-overlay < div < div.page-layout < main.mobile-content < div.mobile-shell
- 画面側CSS import: own=[] / forward(共通除く)=["components/Button.css","constants/platform-icon.css","components/Modal.css","components/FormField.css"] / reverse=[]

| file:line | selector | 特異度 | 状態 | 読込 | 宣言 |
|---|---|---|---|---|---|
| components.css:19 | `.form-group textarea` | (0,1,1) | base | global | width: 100% (L21); padding: var(--space-2) var(--space-3) (L22); border: 1px solid var(--border) (L23); border-radius: var(--radius-sm) (L24); font-size: var(--font-base) (L25); color: var(--text-primary) (L26); background: var(--bg-surface) (L27); box-sizing: border-box (L28) |
| components.css:31 | `.form-group textarea:focus` | (0,2,1) | self:focus | global | outline: none (L33); border-color: var(--accent) (L34); box-shadow: var(--focus-ring-shadow) (L35) |
| components.css:39 | `.form-group textarea` | (0,1,1) | base | global | min-height: var(--textarea-min-h) (L40); resize: vertical (L41) |

## components/ShippingDetailPanel.tsx:551

- 開始タグ: `<textarea value={form.ship_memo} onChange={(ev) => setField("ship_memo", ev.target.value)} data-testid="ship-input-ship_memo" />`
- className: (なし) / 静的トークン: [] / 条件付き: []
- 属性: {}
- inline style: なし
- 祖先連鎖: 2 本（異なるシグネチャ 2）。先頭: div.form-group < form < div.comp-modal-body < div.comp-modal-dialog < div.comp-modal-overlay < div < div.page-layout < main.mobile-content < div.mobile-shell
- 画面側CSS import: own=[] / forward(共通除く)=["components/Button.css","constants/platform-icon.css","components/Modal.css","components/FormField.css"] / reverse=[]

| file:line | selector | 特異度 | 状態 | 読込 | 宣言 |
|---|---|---|---|---|---|
| components.css:19 | `.form-group textarea` | (0,1,1) | base | global | width: 100% (L21); padding: var(--space-2) var(--space-3) (L22); border: 1px solid var(--border) (L23); border-radius: var(--radius-sm) (L24); font-size: var(--font-base) (L25); color: var(--text-primary) (L26); background: var(--bg-surface) (L27); box-sizing: border-box (L28) |
| components.css:31 | `.form-group textarea:focus` | (0,2,1) | self:focus | global | outline: none (L33); border-color: var(--accent) (L34); box-shadow: var(--focus-ring-shadow) (L35) |
| components.css:39 | `.form-group textarea` | (0,1,1) | base | global | min-height: var(--textarea-min-h) (L40); resize: vertical (L41) |

## features/tcg-analysis-review/ItemComparison.tsx:27

- 開始タグ: `<textarea value={values[key]} maxLength={2000} aria-label={t('tcgAnalysisReview.manualCorrection', { field: t(labelKey) })} onChange={(event) => onChange(key, event.target.value)} />`
- className: (なし) / 静的トークン: [] / 条件付き: []
- 属性: {"maxLength":"{2000}"}
- inline style: なし
- 祖先連鎖: 4 本（異なるシグネチャ 4）。先頭: div.comparison-field.manual-field < div.aligned-fields < article < div.supplier-detail-item-row < section.supplier-detail-items < div.supplier-detail-view-body < div.supplier-detail-view < div.analysis-panel-content < div.hub-content < div.hub-shell < div < div.page-layout < main.mobile-content < div.mobile-shell
- 画面側CSS import: own=["features/tcg-analysis-review/item-comparison-readonly.css"] / forward(共通除く)=["components/FormField.css","features/tcg-analysis-review/components/status-badge.css","features/tcg-analysis-review/item-comparison-readonly.css"] / reverse=["features/tcg-analysis-review/supplier-detail-view.css","pages/super-admin/AnalysisRulesPage.css"]

適用規則: **なし**（ブラウザ既定のまま）

## features/tcg-analysis-review/ItemComparison.tsx:34

- 開始タグ: `<textarea id={'note-${item.extraction_item_id}'} value={note} maxLength={2000} onChange={(event) => onNoteChange(event.target.value)} />`
- className: (なし) / 静的トークン: [] / 条件付き: []
- 属性: {"id":"{`note-${item.extraction_item_id}`}","maxLength":"{2000}"}
- inline style: なし
- 祖先連鎖: 4 本（異なるシグネチャ 4）。先頭: div.manual-actions < div.item-extra-grid < article < div.supplier-detail-item-row < section.supplier-detail-items < div.supplier-detail-view-body < div.supplier-detail-view < div.analysis-panel-content < div.hub-content < div.hub-shell < div < div.page-layout < main.mobile-content < div.mobile-shell
- 画面側CSS import: own=["features/tcg-analysis-review/item-comparison-readonly.css"] / forward(共通除く)=["components/FormField.css","features/tcg-analysis-review/components/status-badge.css","features/tcg-analysis-review/item-comparison-readonly.css"] / reverse=["features/tcg-analysis-review/supplier-detail-view.css","pages/super-admin/AnalysisRulesPage.css"]

適用規則: **なし**（ブラウザ既定のまま）

未確定（unconfirmed）:
- index.css:436 `#root` — 静的判定理由: id selector #root vs dynamic/forwarded id。**手動解決**: id が動的（テンプレート文字列）のため判定不能。セレクタ #root は textarea が #root でない限り一致しない（textarea は #root 自身ではない）

## features/tcg-analysis-review/ProductMasterDrawer.tsx:217

- 開始タグ: `<textarea value={values.search_keywords} onChange={(e) => setValue('search_keywords', e.target.value)} />`
- className: (なし) / 静的トークン: [] / 条件付き: []
- 属性: {}
- inline style: なし
- 祖先連鎖: 4 本（異なるシグネチャ 4）。先頭: label.pmd-field < div.pmd-fields < div.pmd-body < aside.pmd-drawer < div.analysis-panel-content < div.hub-content < div.hub-shell < div < div.page-layout < main.mobile-content < div.mobile-shell
- 画面側CSS import: own=[] / forward(共通除く)=["components/FormField.css","features/tcg-analysis-review/components/status-badge.css","features/tcg-analysis-review/item-comparison-readonly.css"] / reverse=["features/tcg-analysis-review/supplier-detail-view.css","pages/super-admin/AnalysisRulesPage.css"]

| file:line | selector | 特異度 | 状態 | 読込 | 宣言 |
|---|---|---|---|---|---|
| features/tcg-analysis-review/supplier-detail-view.css:244 | `.pmd-field textarea` | (0,1,1) | base | reverse | border: 1px solid var(--border) (L246); border-radius: var(--radius-md) (L247); background: var(--bg-surface) (L248); padding: var(--space-2) (L249); font: inherit (L250); width: 100% (L251); box-sizing: border-box (L252) |
| features/tcg-analysis-review/supplier-detail-view.css:255 | `.pmd-field textarea` | (0,1,1) | base | reverse | min-height: var(--pmd-textarea-min-h) (L256); resize: vertical (L257) |

## features/tcg-analysis-review/ProductMasterDrawer.tsx:221

- 開始タグ: `<textarea value={values.exclude_keywords} onChange={(e) => setValue('exclude_keywords', e.target.value)} />`
- className: (なし) / 静的トークン: [] / 条件付き: []
- 属性: {}
- inline style: なし
- 祖先連鎖: 4 本（異なるシグネチャ 4）。先頭: label.pmd-field < div.pmd-fields < div.pmd-body < aside.pmd-drawer < div.analysis-panel-content < div.hub-content < div.hub-shell < div < div.page-layout < main.mobile-content < div.mobile-shell
- 画面側CSS import: own=[] / forward(共通除く)=["components/FormField.css","features/tcg-analysis-review/components/status-badge.css","features/tcg-analysis-review/item-comparison-readonly.css"] / reverse=["features/tcg-analysis-review/supplier-detail-view.css","pages/super-admin/AnalysisRulesPage.css"]

| file:line | selector | 特異度 | 状態 | 読込 | 宣言 |
|---|---|---|---|---|---|
| features/tcg-analysis-review/supplier-detail-view.css:244 | `.pmd-field textarea` | (0,1,1) | base | reverse | border: 1px solid var(--border) (L246); border-radius: var(--radius-md) (L247); background: var(--bg-surface) (L248); padding: var(--space-2) (L249); font: inherit (L250); width: 100% (L251); box-sizing: border-box (L252) |
| features/tcg-analysis-review/supplier-detail-view.css:255 | `.pmd-field textarea` | (0,1,1) | base | reverse | min-height: var(--pmd-textarea-min-h) (L256); resize: vertical (L257) |

## pages/admin/DiscordAnnouncePage.tsx:98

- 開始タグ: `<textarea value={message} onChange={(e) => setMessage(e.target.value)} disabled={!canEdit} placeholder={t("discordAnnounce.messagePlaceholder")} maxLength={2000} rows={6} className="input w-full resize-y" />`
- className: "input w-full resize-y" / 静的トークン: ["input","w-full","resize-y"] / 条件付き: []
- 属性: {"disabled":"{!canEdit}","placeholder":"{t(\"discordAnnounce.messagePlaceholder\")}","maxLength":"{2000}","rows":"{6}"}
- inline style: なし
- 祖先連鎖: 8 本（異なるシグネチャ 8）。先頭: div.space-y-2 < div.max-w-lg.space-y-6 < div < div.page-layout < div.admin-hub-content < div.admin-hub < main.mobile-content < div.mobile-shell < main.mobile-content < div.mobile-shell
- 画面側CSS import: own=[] / forward(共通除く)=["components/Button.css"] / reverse=[]

適用規則: **なし**（ブラウザ既定のまま）

## pages/admin/TenantProfilePage.tsx:170

- 開始タグ: `<textarea id="tp-address" data-testid="tp-address" value={form.address} onChange={handleChange("address")} disabled={!canEdit} rows={3} />`
- className: (なし) / 静的トークン: [] / 条件付き: []
- 属性: {"id":"\"tp-address\"","disabled":"{!canEdit}","rows":"{3}"}
- inline style: なし
- 祖先連鎖: 8 本（異なるシグネチャ 8）。先頭: div.form-group < form.form < div < div.page-layout < div.admin-hub-content < div.admin-hub < main.mobile-content < div.mobile-shell < main.mobile-content < div.mobile-shell
- 画面側CSS import: own=[] / forward(共通除く)=["components/Button.css","components/FormField.css"] / reverse=[]

| file:line | selector | 特異度 | 状態 | 読込 | 宣言 |
|---|---|---|---|---|---|
| components.css:19 | `.form-group textarea` | (0,1,1) | base | global | width: 100% (L21); padding: var(--space-2) var(--space-3) (L22); border: 1px solid var(--border) (L23); border-radius: var(--radius-sm) (L24); font-size: var(--font-base) (L25); color: var(--text-primary) (L26); background: var(--bg-surface) (L27); box-sizing: border-box (L28) |
| components.css:31 | `.form-group textarea:focus` | (0,2,1) | self:focus | global | outline: none (L33); border-color: var(--accent) (L34); box-shadow: var(--focus-ring-shadow) (L35) |
| components.css:39 | `.form-group textarea` | (0,1,1) | base | global | min-height: var(--textarea-min-h) (L40); resize: vertical (L41) |

## pages/badges/BadgesPage.tsx:62

- 開始タグ: `<textarea value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} />`
- className: (なし) / 静的トークン: [] / 条件付き: []
- 属性: {}
- inline style: なし
- 祖先連鎖: 1 本（異なるシグネチャ 1）。先頭: div.form-group < form < div.comp-modal-body < div.comp-modal-dialog < div.comp-modal-overlay < div < div.page-layout
- 画面側CSS import: own=[] / forward(共通除く)=["components/ContentToolbar.css","components/Button.css","constants/platform-icon.css","components/Modal.css"] / reverse=[]

| file:line | selector | 特異度 | 状態 | 読込 | 宣言 |
|---|---|---|---|---|---|
| components.css:19 | `.form-group textarea` | (0,1,1) | base | global | width: 100% (L21); padding: var(--space-2) var(--space-3) (L22); border: 1px solid var(--border) (L23); border-radius: var(--radius-sm) (L24); font-size: var(--font-base) (L25); color: var(--text-primary) (L26); background: var(--bg-surface) (L27); box-sizing: border-box (L28) |
| components.css:31 | `.form-group textarea:focus` | (0,2,1) | self:focus | global | outline: none (L33); border-color: var(--accent) (L34); box-shadow: var(--focus-ring-shadow) (L35) |
| components.css:39 | `.form-group textarea` | (0,1,1) | base | global | min-height: var(--textarea-min-h) (L40); resize: vertical (L41) |

未確定（unconfirmed）:
- company-forms.css:254 `.product-edit-form .form-group textarea` — 静的判定理由: no JSX usage found for BadgesPage (frontend/src/pages/badges/BadgesPage.tsx)。**手動解決**: クラス product-edit-form が JSX に現れるのは pages/products/ProductEditPage.tsx:209 のみ（grep）→ この textarea には一致しない
- features/tcg-analysis-review/supplier-detail-view.css:244 `.pmd-field textarea` — 静的判定理由: no JSX usage found for BadgesPage (frontend/src/pages/badges/BadgesPage.tsx)。**手動解決**: クラス pmd-field が JSX に現れるのは features/tcg-analysis-review/ProductMasterDrawer.tsx のみ（grep）→ この textarea には一致しない
- features/tcg-analysis-review/supplier-detail-view.css:255 `.pmd-field textarea` — 静的判定理由: no JSX usage found for BadgesPage (frontend/src/pages/badges/BadgesPage.tsx)。**手動解決**: クラス pmd-field が JSX に現れるのは features/tcg-analysis-review/ProductMasterDrawer.tsx のみ（grep）→ この textarea には一致しない

## pages/buddy/BuddyPage.tsx:66

- 開始タグ: `<textarea value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} />`
- className: (なし) / 静的トークン: [] / 条件付き: []
- 属性: {}
- inline style: なし
- 祖先連鎖: 1 本（異なるシグネチャ 1）。先頭: div.form-group < form < div.comp-modal-body < div.comp-modal-dialog < div.comp-modal-overlay < div < div.page-layout
- 画面側CSS import: own=[] / forward(共通除く)=["components/ContentToolbar.css","components/Button.css","constants/platform-icon.css","components/Modal.css"] / reverse=[]

| file:line | selector | 特異度 | 状態 | 読込 | 宣言 |
|---|---|---|---|---|---|
| components.css:19 | `.form-group textarea` | (0,1,1) | base | global | width: 100% (L21); padding: var(--space-2) var(--space-3) (L22); border: 1px solid var(--border) (L23); border-radius: var(--radius-sm) (L24); font-size: var(--font-base) (L25); color: var(--text-primary) (L26); background: var(--bg-surface) (L27); box-sizing: border-box (L28) |
| components.css:31 | `.form-group textarea:focus` | (0,2,1) | self:focus | global | outline: none (L33); border-color: var(--accent) (L34); box-shadow: var(--focus-ring-shadow) (L35) |
| components.css:39 | `.form-group textarea` | (0,1,1) | base | global | min-height: var(--textarea-min-h) (L40); resize: vertical (L41) |

未確定（unconfirmed）:
- company-forms.css:254 `.product-edit-form .form-group textarea` — 静的判定理由: no JSX usage found for BuddyPage (frontend/src/pages/buddy/BuddyPage.tsx)。**手動解決**: クラス product-edit-form が JSX に現れるのは pages/products/ProductEditPage.tsx:209 のみ（grep）→ この textarea には一致しない
- features/tcg-analysis-review/supplier-detail-view.css:244 `.pmd-field textarea` — 静的判定理由: no JSX usage found for BuddyPage (frontend/src/pages/buddy/BuddyPage.tsx)。**手動解決**: クラス pmd-field が JSX に現れるのは features/tcg-analysis-review/ProductMasterDrawer.tsx のみ（grep）→ この textarea には一致しない
- features/tcg-analysis-review/supplier-detail-view.css:255 `.pmd-field textarea` — 静的判定理由: no JSX usage found for BuddyPage (frontend/src/pages/buddy/BuddyPage.tsx)。**手動解決**: クラス pmd-field が JSX に現れるのは features/tcg-analysis-review/ProductMasterDrawer.tsx のみ（grep）→ この textarea には一致しない

## pages/companies/CompaniesPage.tsx:499

- 開始タグ: `<textarea value={createForm.shipping_note} onChange={(e) => setCreateForm({ ...createForm, shipping_note: e.target.value })} />`
- className: (なし) / 静的トークン: [] / 条件付き: []
- 属性: {}
- inline style: なし
- 祖先連鎖: 4 本（異なるシグネチャ 4）。先頭: div.form-row < form.form-grid < div.modal-content-wide < div.comp-modal-body < div.comp-modal-dialog < div.comp-modal-overlay < div < div.page-layout < div.hub-content < div.hub-shell < div < div.page-layout < main.mobile-content < div.mobile-shell < main.mobile-content < div.mobile-shell
- 画面側CSS import: own=[] / forward(共通除く)=["components/Button.css","constants/platform-icon.css","components/Modal.css","components/FormField.css","components/Drawer.css","components/ContentToolbar.css","components/DataTable.css"] / reverse=[]

| file:line | selector | 特異度 | 状態 | 読込 | 宣言 |
|---|---|---|---|---|---|
| company-forms.css:100 | `.form-grid > .form-row textarea` | (0,2,1) | base | global | padding: var(--space-2) var(--space-3) (L102); border: 1px solid var(--border-strong) (L103); border-radius: var(--radius-md) (L104); font-size: var(--font-base) (L105); background: var(--bg-surface) (L106); color: var(--text-primary) (L107); width: 100% (L108); box-sizing: border-box (L109); font-family: inherit (L110) |
| company-forms.css:113 | `.form-grid > .form-row textarea` | (0,2,1) | base | global | min-height: var(--textarea-min-h) (L114); resize: vertical (L115) |
| company-forms.css:119 | `.form-grid > .form-row textarea:focus` | (0,3,1) | self:focus | global | outline: none (L121); border-color: var(--accent) (L122); box-shadow: var(--focus-ring-shadow) (L123) |
| company-forms.css:154 | `.modal-content-wide .form-row textarea` | (0,2,1) | base | global | padding: var(--space-2) var(--space-3) (L158); border: 1px solid var(--border-strong) (L159); border-radius: var(--radius-md) (L160); font-size: var(--font-base) (L161); background: var(--bg-surface) (L162); color: var(--text-primary) (L163); width: 100% (L164); box-sizing: border-box (L165); font-family: inherit (L166) |
| company-forms.css:169 | `.modal-content-wide .form-row textarea` | (0,2,1) | base | global | min-height: var(--textarea-min-h) (L171); resize: vertical (L172) |
| company-forms.css:177 | `.modal-content-wide .form-row textarea:focus` | (0,3,1) | self:focus | global | outline: none (L181); border-color: var(--accent) (L182); box-shadow: var(--focus-ring-shadow) (L183) |

## pages/companies/CompaniesPage.tsx:516

- 開始タグ: `<textarea value={createForm.notes} onChange={(e) => setCreateForm({ ...createForm, notes: e.target.value })} />`
- className: (なし) / 静的トークン: [] / 条件付き: []
- 属性: {}
- inline style: なし
- 祖先連鎖: 4 本（異なるシグネチャ 4）。先頭: div.form-row < form.form-grid < div.modal-content-wide < div.comp-modal-body < div.comp-modal-dialog < div.comp-modal-overlay < div < div.page-layout < div.hub-content < div.hub-shell < div < div.page-layout < main.mobile-content < div.mobile-shell < main.mobile-content < div.mobile-shell
- 画面側CSS import: own=[] / forward(共通除く)=["components/Button.css","constants/platform-icon.css","components/Modal.css","components/FormField.css","components/Drawer.css","components/ContentToolbar.css","components/DataTable.css"] / reverse=[]

| file:line | selector | 特異度 | 状態 | 読込 | 宣言 |
|---|---|---|---|---|---|
| company-forms.css:100 | `.form-grid > .form-row textarea` | (0,2,1) | base | global | padding: var(--space-2) var(--space-3) (L102); border: 1px solid var(--border-strong) (L103); border-radius: var(--radius-md) (L104); font-size: var(--font-base) (L105); background: var(--bg-surface) (L106); color: var(--text-primary) (L107); width: 100% (L108); box-sizing: border-box (L109); font-family: inherit (L110) |
| company-forms.css:113 | `.form-grid > .form-row textarea` | (0,2,1) | base | global | min-height: var(--textarea-min-h) (L114); resize: vertical (L115) |
| company-forms.css:119 | `.form-grid > .form-row textarea:focus` | (0,3,1) | self:focus | global | outline: none (L121); border-color: var(--accent) (L122); box-shadow: var(--focus-ring-shadow) (L123) |
| company-forms.css:154 | `.modal-content-wide .form-row textarea` | (0,2,1) | base | global | padding: var(--space-2) var(--space-3) (L158); border: 1px solid var(--border-strong) (L159); border-radius: var(--radius-md) (L160); font-size: var(--font-base) (L161); background: var(--bg-surface) (L162); color: var(--text-primary) (L163); width: 100% (L164); box-sizing: border-box (L165); font-family: inherit (L166) |
| company-forms.css:169 | `.modal-content-wide .form-row textarea` | (0,2,1) | base | global | min-height: var(--textarea-min-h) (L171); resize: vertical (L172) |
| company-forms.css:177 | `.modal-content-wide .form-row textarea:focus` | (0,3,1) | self:focus | global | outline: none (L181); border-color: var(--accent) (L182); box-shadow: var(--focus-ring-shadow) (L183) |

## pages/companies/CompanyFormFields.tsx:64

- 開始タグ: `<textarea value={form.notes} onChange={(e) => onChange("notes", e.target.value)} />`
- className: (なし) / 静的トークン: [] / 条件付き: []
- 属性: {}
- inline style: なし
- 祖先連鎖: 4 本（異なるシグネチャ 4）。先頭: div.form-group < form < div.comp-drawer-body < div.comp-drawer-panel < div < div.page-layout < div.hub-content < div.hub-shell < div < div.page-layout < main.mobile-content < div.mobile-shell < main.mobile-content < div.mobile-shell
- 画面側CSS import: own=[] / forward(共通除く)=["components/FormField.css"] / reverse=[]

| file:line | selector | 特異度 | 状態 | 読込 | 宣言 |
|---|---|---|---|---|---|
| components.css:19 | `.form-group textarea` | (0,1,1) | base | global | width: 100% (L21); padding: var(--space-2) var(--space-3) (L22); border: 1px solid var(--border) (L23); border-radius: var(--radius-sm) (L24); font-size: var(--font-base) (L25); color: var(--text-primary) (L26); background: var(--bg-surface) (L27); box-sizing: border-box (L28) |
| components.css:31 | `.form-group textarea:focus` | (0,2,1) | self:focus | global | outline: none (L33); border-color: var(--accent) (L34); box-shadow: var(--focus-ring-shadow) (L35) |
| components.css:39 | `.form-group textarea` | (0,1,1) | base | global | min-height: var(--textarea-min-h) (L40); resize: vertical (L41) |

## pages/company-detail/CompanyBasicTab.tsx:81

- 開始タグ: `<textarea disabled={!canEdit} value={basicForm.shipping_note} onChange={(e) => { setBasicForm({ ...basicForm, shipping_note: e.target.value }); setBasicDirty(true); }} />`
- className: (なし) / 静的トークン: [] / 条件付き: []
- 属性: {"disabled":"{!canEdit}"}
- inline style: なし
- 祖先連鎖: 4 本（異なるシグネチャ 4）。先頭: div.form-row < form.form-grid < div < div.page-layout < div.page-container-detail < div.hub-content < div.hub-shell < div < div.page-layout < main.mobile-content < div.mobile-shell < main.mobile-content < div.mobile-shell
- 画面側CSS import: own=[] / forward(共通除く)=["components/Button.css","components/FormField.css"] / reverse=[]

| file:line | selector | 特異度 | 状態 | 読込 | 宣言 |
|---|---|---|---|---|---|
| company-forms.css:100 | `.form-grid > .form-row textarea` | (0,2,1) | base | global | padding: var(--space-2) var(--space-3) (L102); border: 1px solid var(--border-strong) (L103); border-radius: var(--radius-md) (L104); font-size: var(--font-base) (L105); background: var(--bg-surface) (L106); color: var(--text-primary) (L107); width: 100% (L108); box-sizing: border-box (L109); font-family: inherit (L110) |
| company-forms.css:113 | `.form-grid > .form-row textarea` | (0,2,1) | base | global | min-height: var(--textarea-min-h) (L114); resize: vertical (L115) |
| company-forms.css:119 | `.form-grid > .form-row textarea:focus` | (0,3,1) | self:focus | global | outline: none (L121); border-color: var(--accent) (L122); box-shadow: var(--focus-ring-shadow) (L123) |

## pages/company-detail/CompanyBasicTab.tsx:94

- 開始タグ: `<textarea disabled={!canEdit} value={basicForm.notes} onChange={(e) => { setBasicForm({ ...basicForm, notes: e.target.value }); setBasicDirty(true); }} />`
- className: (なし) / 静的トークン: [] / 条件付き: []
- 属性: {"disabled":"{!canEdit}"}
- inline style: なし
- 祖先連鎖: 4 本（異なるシグネチャ 4）。先頭: div.form-row < form.form-grid < div < div.page-layout < div.page-container-detail < div.hub-content < div.hub-shell < div < div.page-layout < main.mobile-content < div.mobile-shell < main.mobile-content < div.mobile-shell
- 画面側CSS import: own=[] / forward(共通除く)=["components/Button.css","components/FormField.css"] / reverse=[]

| file:line | selector | 特異度 | 状態 | 読込 | 宣言 |
|---|---|---|---|---|---|
| company-forms.css:100 | `.form-grid > .form-row textarea` | (0,2,1) | base | global | padding: var(--space-2) var(--space-3) (L102); border: 1px solid var(--border-strong) (L103); border-radius: var(--radius-md) (L104); font-size: var(--font-base) (L105); background: var(--bg-surface) (L106); color: var(--text-primary) (L107); width: 100% (L108); box-sizing: border-box (L109); font-family: inherit (L110) |
| company-forms.css:113 | `.form-grid > .form-row textarea` | (0,2,1) | base | global | min-height: var(--textarea-min-h) (L114); resize: vertical (L115) |
| company-forms.css:119 | `.form-grid > .form-row textarea:focus` | (0,3,1) | self:focus | global | outline: none (L121); border-color: var(--accent) (L122); box-shadow: var(--focus-ring-shadow) (L123) |

## pages/conditions/ConditionsPage.tsx:340

- 開始タグ: `<textarea className="field field-h-md" style={{ height: "80px", resize: "vertical", width: "100%" }} value={form.search_kw} onChange={e => setForm({ ...form, search_kw: e.target.value })} />`
- className: "field field-h-md" / 静的トークン: ["field","field-h-md"] / 条件付き: []
- 属性: {}
- inline style: height: 80px; resize: vertical; width: 100%
- 祖先連鎖: 8 本（異なるシグネチャ 4）。先頭: div.form-group < div < form < div.comp-modal-body < div.comp-modal-dialog < div.comp-modal-overlay < div < div.page-layout < div.hub-content < div.hub-shell < div < div.page-layout < main.mobile-content < div.mobile-shell < main.mobile-content < div.mobile-shell
- 画面側CSS import: own=[] / forward(共通除く)=["components/Button.css","constants/platform-icon.css","components/Modal.css","components/ContentToolbar.css","components/DataTable.css","components/FormField.css"] / reverse=[]

| file:line | selector | 特異度 | 状態 | 読込 | 宣言 |
|---|---|---|---|---|---|
| components/field-size.css:8 | `.field-h-md` | (0,1,0) | base | global | min-height: var(--field-h-md, 36px) (L8); box-sizing: border-box (L8) |
| components.css:19 | `.form-group textarea` | (0,1,1) | base | global | width: 100% (L21); padding: var(--space-2) var(--space-3) (L22); border: 1px solid var(--border) (L23); border-radius: var(--radius-sm) (L24); font-size: var(--font-base) (L25); color: var(--text-primary) (L26); background: var(--bg-surface) (L27); box-sizing: border-box (L28) |
| components.css:31 | `.form-group textarea:focus` | (0,2,1) | self:focus | global | outline: none (L33); border-color: var(--accent) (L34); box-shadow: var(--focus-ring-shadow) (L35) |
| components.css:39 | `.form-group textarea` | (0,1,1) | base | global | min-height: var(--textarea-min-h) (L40); resize: vertical (L41) |

## pages/conditions/ConditionsPage.tsx:350

- 開始タグ: `<textarea className="field field-h-md" style={{ height: "80px", resize: "vertical", width: "100%" }} value={form.exclude_kw} onChange={e => setForm({ ...form, exclude_kw: e.target.value })} />`
- className: "field field-h-md" / 静的トークン: ["field","field-h-md"] / 条件付き: []
- 属性: {}
- inline style: height: 80px; resize: vertical; width: 100%
- 祖先連鎖: 8 本（異なるシグネチャ 4）。先頭: div.form-group < div < form < div.comp-modal-body < div.comp-modal-dialog < div.comp-modal-overlay < div < div.page-layout < div.hub-content < div.hub-shell < div < div.page-layout < main.mobile-content < div.mobile-shell < main.mobile-content < div.mobile-shell
- 画面側CSS import: own=[] / forward(共通除く)=["components/Button.css","constants/platform-icon.css","components/Modal.css","components/ContentToolbar.css","components/DataTable.css","components/FormField.css"] / reverse=[]

| file:line | selector | 特異度 | 状態 | 読込 | 宣言 |
|---|---|---|---|---|---|
| components/field-size.css:8 | `.field-h-md` | (0,1,0) | base | global | min-height: var(--field-h-md, 36px) (L8); box-sizing: border-box (L8) |
| components.css:19 | `.form-group textarea` | (0,1,1) | base | global | width: 100% (L21); padding: var(--space-2) var(--space-3) (L22); border: 1px solid var(--border) (L23); border-radius: var(--radius-sm) (L24); font-size: var(--font-base) (L25); color: var(--text-primary) (L26); background: var(--bg-surface) (L27); box-sizing: border-box (L28) |
| components.css:31 | `.form-group textarea:focus` | (0,2,1) | self:focus | global | outline: none (L33); border-color: var(--accent) (L34); box-shadow: var(--focus-ring-shadow) (L35) |
| components.css:39 | `.form-group textarea` | (0,1,1) | base | global | min-height: var(--textarea-min-h) (L40); resize: vertical (L41) |

## pages/contacts/ContactEditPage.tsx:191

- 開始タグ: `<textarea value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />`
- className: (なし) / 静的トークン: [] / 条件付き: []
- 属性: {}
- inline style: なし
- 祖先連鎖: 2 本（異なるシグネチャ 2）。先頭: div.form-group < form < div < div.page-layout < main.mobile-content < div.mobile-shell
- 画面側CSS import: own=[] / forward(共通除く)=["components/Button.css","components/FormField.css"] / reverse=[]

| file:line | selector | 特異度 | 状態 | 読込 | 宣言 |
|---|---|---|---|---|---|
| components.css:19 | `.form-group textarea` | (0,1,1) | base | global | width: 100% (L21); padding: var(--space-2) var(--space-3) (L22); border: 1px solid var(--border) (L23); border-radius: var(--radius-sm) (L24); font-size: var(--font-base) (L25); color: var(--text-primary) (L26); background: var(--bg-surface) (L27); box-sizing: border-box (L28) |
| components.css:31 | `.form-group textarea:focus` | (0,2,1) | self:focus | global | outline: none (L33); border-color: var(--accent) (L34); box-shadow: var(--focus-ring-shadow) (L35) |
| components.css:39 | `.form-group textarea` | (0,1,1) | base | global | min-height: var(--textarea-min-h) (L40); resize: vertical (L41) |

## pages/contacts/ContactsPage.tsx:349

- 開始タグ: `<textarea value={createForm.notes} onChange={(e) => setCreateForm({ ...createForm, notes: e.target.value })} />`
- className: (なし) / 静的トークン: [] / 条件付き: []
- 属性: {}
- inline style: なし
- 祖先連鎖: 4 本（異なるシグネチャ 4）。先頭: div.form-row < form.form-grid < div.modal-content-wide < div.comp-modal-body < div.comp-modal-dialog < div.comp-modal-overlay < div < div.page-layout < div.hub-content < div.hub-shell < div < div.page-layout < main.mobile-content < div.mobile-shell < main.mobile-content < div.mobile-shell
- 画面側CSS import: own=[] / forward(共通除く)=["components/Button.css","constants/platform-icon.css","components/Modal.css","components/FormField.css","components/Drawer.css","components/ContentToolbar.css","components/DataTable.css"] / reverse=[]

| file:line | selector | 特異度 | 状態 | 読込 | 宣言 |
|---|---|---|---|---|---|
| company-forms.css:100 | `.form-grid > .form-row textarea` | (0,2,1) | base | global | padding: var(--space-2) var(--space-3) (L102); border: 1px solid var(--border-strong) (L103); border-radius: var(--radius-md) (L104); font-size: var(--font-base) (L105); background: var(--bg-surface) (L106); color: var(--text-primary) (L107); width: 100% (L108); box-sizing: border-box (L109); font-family: inherit (L110) |
| company-forms.css:113 | `.form-grid > .form-row textarea` | (0,2,1) | base | global | min-height: var(--textarea-min-h) (L114); resize: vertical (L115) |
| company-forms.css:119 | `.form-grid > .form-row textarea:focus` | (0,3,1) | self:focus | global | outline: none (L121); border-color: var(--accent) (L122); box-shadow: var(--focus-ring-shadow) (L123) |
| company-forms.css:154 | `.modal-content-wide .form-row textarea` | (0,2,1) | base | global | padding: var(--space-2) var(--space-3) (L158); border: 1px solid var(--border-strong) (L159); border-radius: var(--radius-md) (L160); font-size: var(--font-base) (L161); background: var(--bg-surface) (L162); color: var(--text-primary) (L163); width: 100% (L164); box-sizing: border-box (L165); font-family: inherit (L166) |
| company-forms.css:169 | `.modal-content-wide .form-row textarea` | (0,2,1) | base | global | min-height: var(--textarea-min-h) (L171); resize: vertical (L172) |
| company-forms.css:177 | `.modal-content-wide .form-row textarea:focus` | (0,3,1) | self:focus | global | outline: none (L181); border-color: var(--accent) (L182); box-shadow: var(--focus-ring-shadow) (L183) |

## pages/dashboard/PriorityProspectsSection.tsx:410

- 開始タグ: `<textarea id={'priority-action-${item.lead_id}'} className="db-weekly-composer-input" rows={3} value={composer.draftAction} onChange={(e) => updateComposer(item.lead_id, { draftAction: e.target.value })} />`
- className: "db-weekly-composer-input" / 静的トークン: ["db-weekly-composer-input"] / 条件付き: []
- 属性: {"id":"{`priority-action-${item.lead_id}`}","rows":"{3}"}
- inline style: なし
- 祖先連鎖: 2 本（異なるシグネチャ 2）。先頭: div.db-weekly-composer-field < div.db-weekly-composer < li.db-priority-item < ul.db-priority-list < div.db-section-card.db-priority-card < div.db-content-stack < div < div.page-layout < main.mobile-content < div.mobile-shell
- 画面側CSS import: own=["pages/dashboard/WeeklyAdvisorSection.css","pages/dashboard/PriorityProspectsSection.css"] / forward(共通除く)=["components/Button.css","constants/platform-icon.css","pages/dashboard/WeeklyAdvisorSection.css","pages/dashboard/PriorityProspectsSection.css"] / reverse=["pages/dashboard/DashboardPage.css"]

| file:line | selector | 特異度 | 状態 | 読込 | 宣言 |
|---|---|---|---|---|---|
| pages/dashboard/WeeklyAdvisorSection.css:205 | `.db-weekly-composer-input` | (0,1,0) | base | forward | width: 100% (L206); border-radius: var(--radius-md) (L207); border: 1px solid var(--border-subtle) (L208); background: var(--bg-primary) (L209); color: var(--text-primary) (L210); padding: var(--space-2) var(--space-3) (L211); font: inherit (L212); resize: vertical (L213) |
| pages/dashboard/WeeklyAdvisorSection.css:216 | `.db-weekly-composer-input:focus` | (0,2,0) | self:focus | forward | outline: 2px solid var(--accent) (L217); outline-offset: 1px (L218) |

未確定（unconfirmed）:
- index.css:436 `#root` — 静的判定理由: id selector #root vs dynamic/forwarded id。**手動解決**: id が動的（テンプレート文字列）のため判定不能。セレクタ #root は textarea が #root でない限り一致しない（textarea は #root 自身ではない）

## pages/dashboard/WeeklyAdvisorSection.tsx:381

- 開始タグ: `<textarea id={'weekly-action-${action.company_id}'} className="db-weekly-composer-input" rows={3} value={composer.draftAction} onChange={(e) => updateComposer(action.company_id, { draftAction: e.target.value })} />`
- className: "db-weekly-composer-input" / 静的トークン: ["db-weekly-composer-input"] / 条件付き: []
- 属性: {"id":"{`weekly-action-${action.company_id}`}","rows":"{3}"}
- inline style: なし
- 祖先連鎖: 2 本（異なるシグネチャ 2）。先頭: div.db-weekly-composer-field < div.db-weekly-composer < li.db-weekly-item < ul.db-weekly-list < div.db-section-card.db-weekly-card < div.db-content-stack < div < div.page-layout < main.mobile-content < div.mobile-shell
- 画面側CSS import: own=["pages/dashboard/WeeklyAdvisorSection.css"] / forward(共通除く)=["components/Button.css","constants/platform-icon.css","pages/dashboard/WeeklyAdvisorSection.css"] / reverse=["pages/dashboard/DashboardPage.css"]

| file:line | selector | 特異度 | 状態 | 読込 | 宣言 |
|---|---|---|---|---|---|
| pages/dashboard/WeeklyAdvisorSection.css:205 | `.db-weekly-composer-input` | (0,1,0) | base | forward | width: 100% (L206); border-radius: var(--radius-md) (L207); border: 1px solid var(--border-subtle) (L208); background: var(--bg-primary) (L209); color: var(--text-primary) (L210); padding: var(--space-2) var(--space-3) (L211); font: inherit (L212); resize: vertical (L213) |
| pages/dashboard/WeeklyAdvisorSection.css:216 | `.db-weekly-composer-input:focus` | (0,2,0) | self:focus | forward | outline: 2px solid var(--accent) (L217); outline-offset: 1px (L218) |

未確定（unconfirmed）:
- index.css:436 `#root` — 静的判定理由: id selector #root vs dynamic/forwarded id。**手動解決**: id が動的（テンプレート文字列）のため判定不能。セレクタ #root は textarea が #root でない限り一致しない（textarea は #root 自身ではない）

## pages/inbox/InboxKartePanel.tsx:484

- 開始タグ: `<textarea className="right-panel-field" rows={3} value={cardForm.cs_memo ?? ""} onChange={(e) => handleCardFieldChange("cs_memo", e.target.value)} onBlur={handleCardFieldBlur} placeholder={t("inbox.emptyField")} />`
- className: "right-panel-field" / 静的トークン: ["right-panel-field"] / 条件付き: []
- 属性: {"rows":"{3}","placeholder":"{t(\"inbox.emptyField\")}"}
- inline style: なし
- 祖先連鎖: 2 本（異なるシグネチャ 2）。先頭: div.right-panel-section < div.right-panel-tab-content < div.right-panel-card < aside.inbox-right-panel < div.inbox-wrapper < div < div.page-layout < main.mobile-content < div.mobile-shell
- 画面側CSS import: own=[] / forward(共通除く)=["constants/platform-icon.css","components/Button.css","components/FormField.css"] / reverse=["pages/inbox/InboxPage.css"]

| file:line | selector | 特異度 | 状態 | 読込 | 宣言 |
|---|---|---|---|---|---|
| pages/inbox/InboxPage.css:1171 | `.right-panel-field` | (0,1,0) | base | reverse | width: 100% (L1172); box-sizing: border-box (L1172); background: var(--karte-field-bg) (L1173); border: 0.5px solid var(--karte-field-bd) (L1173); border-radius: var(--radius-md) (L1174); padding: var(--karte-field-py) var(--karte-field-px) (L1174); font-size: var(--font-sm) (L1175); color: var(--text-primary) (L1175); font-family: inherit (L1176); transition: border-color var(--transition-micro) (L1177) |
| pages/inbox/InboxPage.css:1179 | `.right-panel-field::placeholder` | (0,1,1) | self::placeholder | reverse | color: var(--text-muted) (L1179) |
| pages/inbox/InboxPage.css:1180 | `.right-panel-field:focus` | (0,2,0) | self:focus | reverse | outline: none (L1180); border-color: var(--accent) (L1180) |
| pages/inbox/InboxPage.css:1181 | `textarea.right-panel-field` | (0,1,1) | base | reverse | resize: none (L1181); min-height: var(--inbox-textarea-min-h) (L1181) |

## pages/inbox/InboxKartePanel.tsx:503

- 開始タグ: `<textarea className="right-panel-field" rows={3} value={cardForm.next_action ?? ""} onChange={(e) => handleCardFieldChange("next_action", e.target.value)} onBlur={handleCardFieldBlur} placeholder={t("inbox.emptyField")} />`
- className: "right-panel-field" / 静的トークン: ["right-panel-field"] / 条件付き: []
- 属性: {"rows":"{3}","placeholder":"{t(\"inbox.emptyField\")}"}
- inline style: なし
- 祖先連鎖: 2 本（異なるシグネチャ 2）。先頭: div.right-panel-section < div.right-panel-tab-content < div.right-panel-card < aside.inbox-right-panel < div.inbox-wrapper < div < div.page-layout < main.mobile-content < div.mobile-shell
- 画面側CSS import: own=[] / forward(共通除く)=["constants/platform-icon.css","components/Button.css","components/FormField.css"] / reverse=["pages/inbox/InboxPage.css"]

| file:line | selector | 特異度 | 状態 | 読込 | 宣言 |
|---|---|---|---|---|---|
| pages/inbox/InboxPage.css:1171 | `.right-panel-field` | (0,1,0) | base | reverse | width: 100% (L1172); box-sizing: border-box (L1172); background: var(--karte-field-bg) (L1173); border: 0.5px solid var(--karte-field-bd) (L1173); border-radius: var(--radius-md) (L1174); padding: var(--karte-field-py) var(--karte-field-px) (L1174); font-size: var(--font-sm) (L1175); color: var(--text-primary) (L1175); font-family: inherit (L1176); transition: border-color var(--transition-micro) (L1177) |
| pages/inbox/InboxPage.css:1179 | `.right-panel-field::placeholder` | (0,1,1) | self::placeholder | reverse | color: var(--text-muted) (L1179) |
| pages/inbox/InboxPage.css:1180 | `.right-panel-field:focus` | (0,2,0) | self:focus | reverse | outline: none (L1180); border-color: var(--accent) (L1180) |
| pages/inbox/InboxPage.css:1181 | `textarea.right-panel-field` | (0,1,1) | base | reverse | resize: none (L1181); min-height: var(--inbox-textarea-min-h) (L1181) |

## pages/inbox/InboxKartePanel.tsx:537

- 開始タグ: `<textarea className="right-panel-field" rows={3} value={cardForm.challenge ?? ""} onChange={(e) => handleCardFieldChange("challenge", e.target.value)} onBlur={handleCardFieldBlur} placeholder={t("inbox.emptyField")} />`
- className: "right-panel-field" / 静的トークン: ["right-panel-field"] / 条件付き: []
- 属性: {"rows":"{3}","placeholder":"{t(\"inbox.emptyField\")}"}
- inline style: なし
- 祖先連鎖: 2 本（異なるシグネチャ 2）。先頭: div.right-panel-section < div.right-panel-tab-content < div.right-panel-card < aside.inbox-right-panel < div.inbox-wrapper < div < div.page-layout < main.mobile-content < div.mobile-shell
- 画面側CSS import: own=[] / forward(共通除く)=["constants/platform-icon.css","components/Button.css","components/FormField.css"] / reverse=["pages/inbox/InboxPage.css"]

| file:line | selector | 特異度 | 状態 | 読込 | 宣言 |
|---|---|---|---|---|---|
| pages/inbox/InboxPage.css:1171 | `.right-panel-field` | (0,1,0) | base | reverse | width: 100% (L1172); box-sizing: border-box (L1172); background: var(--karte-field-bg) (L1173); border: 0.5px solid var(--karte-field-bd) (L1173); border-radius: var(--radius-md) (L1174); padding: var(--karte-field-py) var(--karte-field-px) (L1174); font-size: var(--font-sm) (L1175); color: var(--text-primary) (L1175); font-family: inherit (L1176); transition: border-color var(--transition-micro) (L1177) |
| pages/inbox/InboxPage.css:1179 | `.right-panel-field::placeholder` | (0,1,1) | self::placeholder | reverse | color: var(--text-muted) (L1179) |
| pages/inbox/InboxPage.css:1180 | `.right-panel-field:focus` | (0,2,0) | self:focus | reverse | outline: none (L1180); border-color: var(--accent) (L1180) |
| pages/inbox/InboxPage.css:1181 | `textarea.right-panel-field` | (0,1,1) | base | reverse | resize: none (L1181); min-height: var(--inbox-textarea-min-h) (L1181) |

## pages/inbox/InboxKartePanel.tsx:588

- 開始タグ: `<textarea className="right-panel-field" rows={3} value={cardForm.meeting_memo ?? ""} onChange={(e) => handleCardFieldChange("meeting_memo", e.target.value)} onBlur={handleCardFieldBlur} placeholder={t("inbox.emptyField")} />`
- className: "right-panel-field" / 静的トークン: ["right-panel-field"] / 条件付き: []
- 属性: {"rows":"{3}","placeholder":"{t(\"inbox.emptyField\")}"}
- inline style: なし
- 祖先連鎖: 2 本（異なるシグネチャ 2）。先頭: div.right-panel-section < div.right-panel-tab-content < div.right-panel-card < aside.inbox-right-panel < div.inbox-wrapper < div < div.page-layout < main.mobile-content < div.mobile-shell
- 画面側CSS import: own=[] / forward(共通除く)=["constants/platform-icon.css","components/Button.css","components/FormField.css"] / reverse=["pages/inbox/InboxPage.css"]

| file:line | selector | 特異度 | 状態 | 読込 | 宣言 |
|---|---|---|---|---|---|
| pages/inbox/InboxPage.css:1171 | `.right-panel-field` | (0,1,0) | base | reverse | width: 100% (L1172); box-sizing: border-box (L1172); background: var(--karte-field-bg) (L1173); border: 0.5px solid var(--karte-field-bd) (L1173); border-radius: var(--radius-md) (L1174); padding: var(--karte-field-py) var(--karte-field-px) (L1174); font-size: var(--font-sm) (L1175); color: var(--text-primary) (L1175); font-family: inherit (L1176); transition: border-color var(--transition-micro) (L1177) |
| pages/inbox/InboxPage.css:1179 | `.right-panel-field::placeholder` | (0,1,1) | self::placeholder | reverse | color: var(--text-muted) (L1179) |
| pages/inbox/InboxPage.css:1180 | `.right-panel-field:focus` | (0,2,0) | self:focus | reverse | outline: none (L1180); border-color: var(--accent) (L1180) |
| pages/inbox/InboxPage.css:1181 | `textarea.right-panel-field` | (0,1,1) | base | reverse | resize: none (L1181); min-height: var(--inbox-textarea-min-h) (L1181) |

## pages/inbox/InboxMessageThread.tsx:736

- 開始タグ: `<textarea ref={textareaRef} className="inbox-textarea" value={draft} onChange={(e) => setDraft(e.target.value)} onKeyDown={handleKeyDownGuarded} placeholder={ discordChannelMissing ? t("inbox.discordChannelMissing") : canSend ? t("inbox.messagePlaceholder") : t("inbox.sendDisabled7d") } rows={2} dis`
- className: "inbox-textarea" / 静的トークン: ["inbox-textarea"] / 条件付き: []
- 属性: {"placeholder":"{\n                  discordChannelMissing\n                    ? t(\"inbox.discordChannelMissing\")\n                    : canSend\n                      ? t(\"inbox.messagePlaceholder\")\n                      : t(\"inbox.sendDisabled7d\")\n                }","rows":"{2}","disabled":"{!canSend || sending}"}
- inline style: なし
- 祖先連鎖: 2 本（異なるシグネチャ 2）。先頭: div.send-input-wrap < div.send-top-row < div.send-card < div.inbox-send-area.sticky-bottom-bar < main.inbox-center < div.inbox-columns < div.inbox-main-area < div.inbox-wrapper < div < div.page-layout < main.mobile-content < div.mobile-shell
- 画面側CSS import: own=[] / forward(共通除く)=["constants/platform-icon.css","components/FormField.css","components/Tooltip.css","components/IconToggleButton.css","components/Button.css"] / reverse=["pages/inbox/InboxPage.css"]

| file:line | selector | 特異度 | 状態 | 読込 | 宣言 |
|---|---|---|---|---|---|
| pages/inbox/InboxPage.css:633 | `.inbox-textarea` | (0,1,0) | base | reverse | flex: 1 (L634); min-width: 0 (L635); border: none (L636); padding: 0 (L637); font-size: var(--font-base) (L638); resize: none (L639); font-family: inherit (L640); outline: none (L641); background: transparent (L642); color: var(--text-primary) (L643); box-sizing: border-box (L644); line-height: 1.4 (L645) |
| pages/inbox/InboxPage.css:647 | `.inbox-textarea:disabled` | (0,2,0) | self:disabled | reverse | cursor: not-allowed (L647); opacity: var(--opacity-disabled) (L647) |

## pages/inbox/InboxProfileModal.tsx:181

- 開始タグ: `<textarea className="right-panel-field" rows={3} value={cardForm.cs_memo ?? ""} onChange={(e) => handleCardFieldChange("cs_memo", e.target.value)} onBlur={handleCardFieldBlur} placeholder={t("leads.csMemo")} />`
- className: "right-panel-field" / 静的トークン: ["right-panel-field"] / 条件付き: []
- 属性: {"rows":"{3}","placeholder":"{t(\"leads.csMemo\")}"}
- inline style: なし
- 祖先連鎖: 2 本（異なるシグネチャ 2）。先頭: div.right-panel-section < div.right-panel-tab-content < div.inbox-profile-modal < div.modal-overlay < main.mobile-content < div.mobile-shell
- 画面側CSS import: own=[] / forward(共通除く)=["constants/platform-icon.css","components/FormField.css"] / reverse=["pages/inbox/InboxPage.css"]

| file:line | selector | 特異度 | 状態 | 読込 | 宣言 |
|---|---|---|---|---|---|
| pages/inbox/InboxPage.css:1171 | `.right-panel-field` | (0,1,0) | base | reverse | width: 100% (L1172); box-sizing: border-box (L1172); background: var(--karte-field-bg) (L1173); border: 0.5px solid var(--karte-field-bd) (L1173); border-radius: var(--radius-md) (L1174); padding: var(--karte-field-py) var(--karte-field-px) (L1174); font-size: var(--font-sm) (L1175); color: var(--text-primary) (L1175); font-family: inherit (L1176); transition: border-color var(--transition-micro) (L1177) |
| pages/inbox/InboxPage.css:1179 | `.right-panel-field::placeholder` | (0,1,1) | self::placeholder | reverse | color: var(--text-muted) (L1179) |
| pages/inbox/InboxPage.css:1180 | `.right-panel-field:focus` | (0,2,0) | self:focus | reverse | outline: none (L1180); border-color: var(--accent) (L1180) |
| pages/inbox/InboxPage.css:1181 | `textarea.right-panel-field` | (0,1,1) | base | reverse | resize: none (L1181); min-height: var(--inbox-textarea-min-h) (L1181) |

## pages/inbox/InboxProfileModal.tsx:191

- 開始タグ: `<textarea className="right-panel-field" rows={3} value={cardForm.next_action ?? ""} onChange={(e) => handleCardFieldChange("next_action", e.target.value)} onBlur={handleCardFieldBlur} placeholder={t("leads.nextAction")} />`
- className: "right-panel-field" / 静的トークン: ["right-panel-field"] / 条件付き: []
- 属性: {"rows":"{3}","placeholder":"{t(\"leads.nextAction\")}"}
- inline style: なし
- 祖先連鎖: 2 本（異なるシグネチャ 2）。先頭: div.right-panel-section < div.right-panel-tab-content < div.inbox-profile-modal < div.modal-overlay < main.mobile-content < div.mobile-shell
- 画面側CSS import: own=[] / forward(共通除く)=["constants/platform-icon.css","components/FormField.css"] / reverse=["pages/inbox/InboxPage.css"]

| file:line | selector | 特異度 | 状態 | 読込 | 宣言 |
|---|---|---|---|---|---|
| pages/inbox/InboxPage.css:1171 | `.right-panel-field` | (0,1,0) | base | reverse | width: 100% (L1172); box-sizing: border-box (L1172); background: var(--karte-field-bg) (L1173); border: 0.5px solid var(--karte-field-bd) (L1173); border-radius: var(--radius-md) (L1174); padding: var(--karte-field-py) var(--karte-field-px) (L1174); font-size: var(--font-sm) (L1175); color: var(--text-primary) (L1175); font-family: inherit (L1176); transition: border-color var(--transition-micro) (L1177) |
| pages/inbox/InboxPage.css:1179 | `.right-panel-field::placeholder` | (0,1,1) | self::placeholder | reverse | color: var(--text-muted) (L1179) |
| pages/inbox/InboxPage.css:1180 | `.right-panel-field:focus` | (0,2,0) | self:focus | reverse | outline: none (L1180); border-color: var(--accent) (L1180) |
| pages/inbox/InboxPage.css:1181 | `textarea.right-panel-field` | (0,1,1) | base | reverse | resize: none (L1181); min-height: var(--inbox-textarea-min-h) (L1181) |

## pages/inbox/InboxProfileModal.tsx:210

- 開始タグ: `<textarea className="right-panel-field" rows={3} value={cardForm.challenge ?? ""} onChange={(e) => handleCardFieldChange("challenge", e.target.value)} onBlur={handleCardFieldBlur} placeholder={t("leads.challenge")} />`
- className: "right-panel-field" / 静的トークン: ["right-panel-field"] / 条件付き: []
- 属性: {"rows":"{3}","placeholder":"{t(\"leads.challenge\")}"}
- inline style: なし
- 祖先連鎖: 2 本（異なるシグネチャ 2）。先頭: div.right-panel-section < div.right-panel-tab-content < div.inbox-profile-modal < div.modal-overlay < main.mobile-content < div.mobile-shell
- 画面側CSS import: own=[] / forward(共通除く)=["constants/platform-icon.css","components/FormField.css"] / reverse=["pages/inbox/InboxPage.css"]

| file:line | selector | 特異度 | 状態 | 読込 | 宣言 |
|---|---|---|---|---|---|
| pages/inbox/InboxPage.css:1171 | `.right-panel-field` | (0,1,0) | base | reverse | width: 100% (L1172); box-sizing: border-box (L1172); background: var(--karte-field-bg) (L1173); border: 0.5px solid var(--karte-field-bd) (L1173); border-radius: var(--radius-md) (L1174); padding: var(--karte-field-py) var(--karte-field-px) (L1174); font-size: var(--font-sm) (L1175); color: var(--text-primary) (L1175); font-family: inherit (L1176); transition: border-color var(--transition-micro) (L1177) |
| pages/inbox/InboxPage.css:1179 | `.right-panel-field::placeholder` | (0,1,1) | self::placeholder | reverse | color: var(--text-muted) (L1179) |
| pages/inbox/InboxPage.css:1180 | `.right-panel-field:focus` | (0,2,0) | self:focus | reverse | outline: none (L1180); border-color: var(--accent) (L1180) |
| pages/inbox/InboxPage.css:1181 | `textarea.right-panel-field` | (0,1,1) | base | reverse | resize: none (L1181); min-height: var(--inbox-textarea-min-h) (L1181) |

## pages/inbox/InboxProfileModal.tsx:265

- 開始タグ: `<textarea className="right-panel-field" rows={3} value={cardForm.meeting_memo ?? ""} onChange={(e) => handleCardFieldChange("meeting_memo", e.target.value)} onBlur={handleCardFieldBlur} placeholder={t("leads.meetingMemo")} />`
- className: "right-panel-field" / 静的トークン: ["right-panel-field"] / 条件付き: []
- 属性: {"rows":"{3}","placeholder":"{t(\"leads.meetingMemo\")}"}
- inline style: なし
- 祖先連鎖: 2 本（異なるシグネチャ 2）。先頭: div.right-panel-section < div.right-panel-tab-content < div.inbox-profile-modal < div.modal-overlay < main.mobile-content < div.mobile-shell
- 画面側CSS import: own=[] / forward(共通除く)=["constants/platform-icon.css","components/FormField.css"] / reverse=["pages/inbox/InboxPage.css"]

| file:line | selector | 特異度 | 状態 | 読込 | 宣言 |
|---|---|---|---|---|---|
| pages/inbox/InboxPage.css:1171 | `.right-panel-field` | (0,1,0) | base | reverse | width: 100% (L1172); box-sizing: border-box (L1172); background: var(--karte-field-bg) (L1173); border: 0.5px solid var(--karte-field-bd) (L1173); border-radius: var(--radius-md) (L1174); padding: var(--karte-field-py) var(--karte-field-px) (L1174); font-size: var(--font-sm) (L1175); color: var(--text-primary) (L1175); font-family: inherit (L1176); transition: border-color var(--transition-micro) (L1177) |
| pages/inbox/InboxPage.css:1179 | `.right-panel-field::placeholder` | (0,1,1) | self::placeholder | reverse | color: var(--text-muted) (L1179) |
| pages/inbox/InboxPage.css:1180 | `.right-panel-field:focus` | (0,2,0) | self:focus | reverse | outline: none (L1180); border-color: var(--accent) (L1180) |
| pages/inbox/InboxPage.css:1181 | `textarea.right-panel-field` | (0,1,1) | base | reverse | resize: none (L1181); min-height: var(--inbox-textarea-min-h) (L1181) |

## pages/inbox/ManualRecordSection.tsx:159

- 開始タグ: `<textarea className="manual-record-textarea" value={contentText} onChange={(e) => setContentText(e.target.value)} onKeyDown={handleKeyDown} placeholder={t("inbox.manualRecord.contentPlaceholder")} rows={3} disabled={saving} aria-label={t("inbox.manualRecord.contentPlaceholder")} />`
- className: "manual-record-textarea" / 静的トークン: ["manual-record-textarea"] / 条件付き: []
- 属性: {"placeholder":"{t(\"inbox.manualRecord.contentPlaceholder\")}","rows":"{3}","disabled":"{saving}"}
- inline style: なし
- 祖先連鎖: 2 本（異なるシグネチャ 2）。先頭: div.manual-record-section < main.inbox-center < div.inbox-columns < div.inbox-main-area < div.inbox-wrapper < div < div.page-layout < main.mobile-content < div.mobile-shell
- 画面側CSS import: own=[] / forward(共通除く)=["components/FormField.css"] / reverse=["pages/inbox/InboxPage.css"]

適用規則: **なし**（ブラウザ既定のまま）

## pages/inbox/OutboundTranslationPreview.tsx:147

- 開始タグ: `<textarea className="outbound-translation-edit" value={editedText} onChange={(e) => setEditedText(e.target.value)} rows={4} disabled={confirming} aria-label={t("translation.outbound.editAriaLabel")} />`
- className: "outbound-translation-edit" / 静的トークン: ["outbound-translation-edit"] / 条件付き: []
- 属性: {"rows":"{4}","disabled":"{confirming}"}
- inline style: なし
- 祖先連鎖: 2 本（異なるシグネチャ 2）。先頭: div.outbound-translation-section < div.outbound-translation-modal < div.outbound-translation-overlay < main.inbox-center < div.inbox-columns < div.inbox-main-area < div.inbox-wrapper < div < div.page-layout < main.mobile-content < div.mobile-shell
- 画面側CSS import: own=[] / forward(共通除く)=[] / reverse=["pages/inbox/InboxPage.css"]

| file:line | selector | 特異度 | 状態 | 読込 | 宣言 |
|---|---|---|---|---|---|
| pages/inbox/InboxPage.css:1529 | `.outbound-translation-edit` | (0,1,0) | base | reverse | width: 100% (L1530); padding: var(--space-3) (L1530); resize: vertical (L1530); border: 1px solid var(--border) (L1531); border-radius: var(--radius-sm) (L1531); background: var(--bg-input) (L1532); color: var(--text) (L1532); font-size: var(--font-sm) (L1532); line-height: 1.5 (L1533); font-family: inherit (L1533) |
| pages/inbox/InboxPage.css:1535 | `.outbound-translation-edit:focus` | (0,2,0) | self:focus | reverse | outline: none (L1535); border-color: var(--accent) (L1535) |

## pages/leads/LeadEditPage.tsx:279

- 開始タグ: `<textarea value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />`
- className: (なし) / 静的トークン: [] / 条件付き: []
- 属性: {}
- inline style: なし
- 祖先連鎖: 2 本（異なるシグネチャ 2）。先頭: div.form-group < form < div < div.page-layout < main.mobile-content < div.mobile-shell
- 画面側CSS import: own=[] / forward(共通除く)=["components/Button.css","components/FormField.css"] / reverse=[]

| file:line | selector | 特異度 | 状態 | 読込 | 宣言 |
|---|---|---|---|---|---|
| components.css:19 | `.form-group textarea` | (0,1,1) | base | global | width: 100% (L21); padding: var(--space-2) var(--space-3) (L22); border: 1px solid var(--border) (L23); border-radius: var(--radius-sm) (L24); font-size: var(--font-base) (L25); color: var(--text-primary) (L26); background: var(--bg-surface) (L27); box-sizing: border-box (L28) |
| components.css:31 | `.form-group textarea:focus` | (0,2,1) | self:focus | global | outline: none (L33); border-color: var(--accent) (L34); box-shadow: var(--focus-ring-shadow) (L35) |
| components.css:39 | `.form-group textarea` | (0,1,1) | base | global | min-height: var(--textarea-min-h) (L40); resize: vertical (L41) |

## pages/leads/LeadFormFields.tsx:84

- 開始タグ: `<textarea id={memoId} value={closeReasonMemo} onChange={(e) => onCloseReasonMemoChange(e.target.value)} placeholder={t("leads.lostReasonPlaceholder")} />`
- className: (なし) / 静的トークン: [] / 条件付き: []
- 属性: {"id":"{memoId}","placeholder":"{t(\"leads.lostReasonPlaceholder\")}"}
- inline style: なし
- 祖先連鎖: 6 本（異なるシグネチャ 6）。先頭: div.form-group < form < div < div.page-layout < main.mobile-content < div.mobile-shell
- 画面側CSS import: own=[] / forward(共通除く)=["components/FormField.css"] / reverse=[]

| file:line | selector | 特異度 | 状態 | 読込 | 宣言 |
|---|---|---|---|---|---|
| components.css:19 | `.form-group textarea` | (0,1,1) | base | global | width: 100% (L21); padding: var(--space-2) var(--space-3) (L22); border: 1px solid var(--border) (L23); border-radius: var(--radius-sm) (L24); font-size: var(--font-base) (L25); color: var(--text-primary) (L26); background: var(--bg-surface) (L27); box-sizing: border-box (L28) |
| components.css:31 | `.form-group textarea:focus` | (0,2,1) | self:focus | global | outline: none (L33); border-color: var(--accent) (L34); box-shadow: var(--focus-ring-shadow) (L35) |
| components.css:39 | `.form-group textarea` | (0,1,1) | base | global | min-height: var(--textarea-min-h) (L40); resize: vertical (L41) |

未確定（unconfirmed）:
- index.css:436 `#root` — 静的判定理由: id selector #root vs dynamic/forwarded id。**手動解決**: id が動的（テンプレート文字列）のため判定不能。セレクタ #root は textarea が #root でない限り一致しない（textarea は #root 自身ではない）

## pages/leads/LeadFormFields.tsx:153

- 開始タグ: `<textarea value={form.notes} onChange={(e) => onChange("notes", e.target.value)} />`
- className: (なし) / 静的トークン: [] / 条件付き: []
- 属性: {}
- inline style: なし
- 祖先連鎖: 4 本（異なるシグネチャ 4）。先頭: div.form-group < form < div.comp-drawer-body < div.comp-drawer-panel < div < div.page-layout < div.hub-content < div.hub-shell < div < div.page-layout < main.mobile-content < div.mobile-shell < main.mobile-content < div.mobile-shell
- 画面側CSS import: own=[] / forward(共通除く)=["components/FormField.css"] / reverse=[]

| file:line | selector | 特異度 | 状態 | 読込 | 宣言 |
|---|---|---|---|---|---|
| components.css:19 | `.form-group textarea` | (0,1,1) | base | global | width: 100% (L21); padding: var(--space-2) var(--space-3) (L22); border: 1px solid var(--border) (L23); border-radius: var(--radius-sm) (L24); font-size: var(--font-base) (L25); color: var(--text-primary) (L26); background: var(--bg-surface) (L27); box-sizing: border-box (L28) |
| components.css:31 | `.form-group textarea:focus` | (0,2,1) | self:focus | global | outline: none (L33); border-color: var(--accent) (L34); box-shadow: var(--focus-ring-shadow) (L35) |
| components.css:39 | `.form-group textarea` | (0,1,1) | base | global | min-height: var(--textarea-min-h) (L40); resize: vertical (L41) |

## pages/leads/LeadsPage.tsx:429

- 開始タグ: `<textarea value={createForm.notes} onChange={(e) => setCreateForm({ ...createForm, notes: e.target.value })} />`
- className: (なし) / 静的トークン: [] / 条件付き: []
- 属性: {}
- inline style: なし
- 祖先連鎖: 4 本（異なるシグネチャ 4）。先頭: div.form-group < form < div.comp-modal-body < div.comp-modal-dialog < div.comp-modal-overlay < div < div.page-layout < div.hub-content < div.hub-shell < div < div.page-layout < main.mobile-content < div.mobile-shell < main.mobile-content < div.mobile-shell
- 画面側CSS import: own=[] / forward(共通除く)=["components/Button.css","constants/platform-icon.css","components/Modal.css","components/Drawer.css","components/FormField.css","components/ContentToolbar.css","components/DataTable.css"] / reverse=[]

| file:line | selector | 特異度 | 状態 | 読込 | 宣言 |
|---|---|---|---|---|---|
| components.css:19 | `.form-group textarea` | (0,1,1) | base | global | width: 100% (L21); padding: var(--space-2) var(--space-3) (L22); border: 1px solid var(--border) (L23); border-radius: var(--radius-sm) (L24); font-size: var(--font-base) (L25); color: var(--text-primary) (L26); background: var(--bg-surface) (L27); box-sizing: border-box (L28) |
| components.css:31 | `.form-group textarea:focus` | (0,2,1) | self:focus | global | outline: none (L33); border-color: var(--accent) (L34); box-shadow: var(--focus-ring-shadow) (L35) |
| components.css:39 | `.form-group textarea` | (0,1,1) | base | global | min-height: var(--textarea-min-h) (L40); resize: vertical (L41) |

## pages/orders/OrdersFormModal.tsx:95

- 開始タグ: `<textarea value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />`
- className: (なし) / 静的トークン: [] / 条件付き: []
- 属性: {}
- inline style: なし
- 祖先連鎖: 2 本（異なるシグネチャ 2）。先頭: div.form-group < form < div.comp-modal-body < div.comp-modal-dialog < div.comp-modal-overlay < div < div.page-layout < main.mobile-content < div.mobile-shell
- 画面側CSS import: own=[] / forward(共通除く)=["components/FormField.css","components/Button.css","constants/platform-icon.css","components/Modal.css"] / reverse=[]

| file:line | selector | 特異度 | 状態 | 読込 | 宣言 |
|---|---|---|---|---|---|
| components.css:19 | `.form-group textarea` | (0,1,1) | base | global | width: 100% (L21); padding: var(--space-2) var(--space-3) (L22); border: 1px solid var(--border) (L23); border-radius: var(--radius-sm) (L24); font-size: var(--font-base) (L25); color: var(--text-primary) (L26); background: var(--bg-surface) (L27); box-sizing: border-box (L28) |
| components.css:31 | `.form-group textarea:focus` | (0,2,1) | self:focus | global | outline: none (L33); border-color: var(--accent) (L34); box-shadow: var(--focus-ring-shadow) (L35) |
| components.css:39 | `.form-group textarea` | (0,1,1) | base | global | min-height: var(--textarea-min-h) (L40); resize: vertical (L41) |

## pages/products/ProductEditPage.tsx:309

- 開始タグ: `<textarea value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />`
- className: (なし) / 静的トークン: [] / 条件付き: []
- 属性: {}
- inline style: なし
- 祖先連鎖: 4 本（異なるシグネチャ 2）。先頭: div.form-group.form-group-full < form.product-edit-form < div.page.page--full < div < div.page-layout < main.mobile-content < div.mobile-shell
- 画面側CSS import: own=[] / forward(共通除く)=["components/ContentToolbar.css","components/Button.css"] / reverse=[]

| file:line | selector | 特異度 | 状態 | 読込 | 宣言 |
|---|---|---|---|---|---|
| company-forms.css:254 | `.product-edit-form .form-group textarea` | (0,2,1) | base | global | border: 1px solid var(--border-strong) (L256) |
| components.css:19 | `.form-group textarea` | (0,1,1) | base | global | width: 100% (L21); padding: var(--space-2) var(--space-3) (L22); border: 1px solid var(--border) (L23); border-radius: var(--radius-sm) (L24); font-size: var(--font-base) (L25); color: var(--text-primary) (L26); background: var(--bg-surface) (L27); box-sizing: border-box (L28) |
| components.css:31 | `.form-group textarea:focus` | (0,2,1) | self:focus | global | outline: none (L33); border-color: var(--accent) (L34); box-shadow: var(--focus-ring-shadow) (L35) |
| components.css:39 | `.form-group textarea` | (0,1,1) | base | global | min-height: var(--textarea-min-h) (L40); resize: vertical (L41) |

## pages/purchase-orders/PurchaseOrdersFormModal.tsx:217

- 開始タグ: `<textarea rows={3} value={notes} onChange={(e) => setNotes(e.target.value)} />`
- className: (なし) / 静的トークン: [] / 条件付き: []
- 属性: {"rows":"{3}"}
- inline style: なし
- 祖先連鎖: 6 本（異なるシグネチャ 6）。先頭: div.form-group < form < div.comp-modal-body < div.comp-modal-dialog < div.comp-modal-overlay < div < div.page-layout < main.mobile-content < div.mobile-shell
- 画面側CSS import: own=[] / forward(共通除く)=["components/Button.css","components/FormField.css","constants/platform-icon.css","components/Modal.css"] / reverse=[]

| file:line | selector | 特異度 | 状態 | 読込 | 宣言 |
|---|---|---|---|---|---|
| components.css:19 | `.form-group textarea` | (0,1,1) | base | global | width: 100% (L21); padding: var(--space-2) var(--space-3) (L22); border: 1px solid var(--border) (L23); border-radius: var(--radius-sm) (L24); font-size: var(--font-base) (L25); color: var(--text-primary) (L26); background: var(--bg-surface) (L27); box-sizing: border-box (L28) |
| components.css:31 | `.form-group textarea:focus` | (0,2,1) | self:focus | global | outline: none (L33); border-color: var(--accent) (L34); box-shadow: var(--focus-ring-shadow) (L35) |
| components.css:39 | `.form-group textarea` | (0,1,1) | base | global | min-height: var(--textarea-min-h) (L40); resize: vertical (L41) |

## pages/roles/RolesPage.tsx:538

- 開始タグ: `<textarea value={roleForm.description} onChange={(e) => setRoleForm({ ...roleForm, description: e.target.value })} />`
- className: (なし) / 静的トークン: [] / 条件付き: []
- 属性: {}
- inline style: なし
- 祖先連鎖: 6 本（異なるシグネチャ 6）。先頭: div.form-group < form < div.comp-modal-body < div.comp-modal-dialog < div.comp-modal-overlay < div.page.roles-page < main.mobile-content < div.mobile-shell
- 画面側CSS import: own=[] / forward(共通除く)=["constants/platform-icon.css","components/Button.css","components/Modal.css","components/FormField.css"] / reverse=[]

| file:line | selector | 特異度 | 状態 | 読込 | 宣言 |
|---|---|---|---|---|---|
| components.css:19 | `.form-group textarea` | (0,1,1) | base | global | width: 100% (L21); padding: var(--space-2) var(--space-3) (L22); border: 1px solid var(--border) (L23); border-radius: var(--radius-sm) (L24); font-size: var(--font-base) (L25); color: var(--text-primary) (L26); background: var(--bg-surface) (L27); box-sizing: border-box (L28) |
| components.css:31 | `.form-group textarea:focus` | (0,2,1) | self:focus | global | outline: none (L33); border-color: var(--accent) (L34); box-shadow: var(--focus-ring-shadow) (L35) |
| components.css:39 | `.form-group textarea` | (0,1,1) | base | global | min-height: var(--textarea-min-h) (L40); resize: vertical (L41) |

## pages/schedule/SchedulePageImpl.tsx:378

- 開始タグ: `<textarea className="schedule-textarea" rows={4} value={draft.description} onChange={(event) => onDraftChange({ ...draft, description: event.target.value })} placeholder={t("schedule.descriptionPlaceholder")} />`
- className: "schedule-textarea" / 静的トークン: ["schedule-textarea"] / 条件付き: []
- 属性: {"rows":"{4}","placeholder":"{t(\"schedule.descriptionPlaceholder\")}"}
- inline style: なし
- 祖先連鎖: 2 本（異なるシグネチャ 2）。先頭: label.schedule-field < div.schedule-popover__body.schedule-popover__body--form < div.schedule-popover < div.schedule-page < main.mobile-content < div.mobile-shell
- 画面側CSS import: own=["pages/schedule.css"] / forward(共通除く)=["components/Button.css","components/FormField.css","constants/platform-icon.css","pages/schedule.css"] / reverse=[]

| file:line | selector | 特異度 | 状態 | 読込 | 宣言 |
|---|---|---|---|---|---|
| pages/schedule.css:813 | `.schedule-textarea` | (0,1,0) | base | forward | width: 100% (L815); border: 1px solid var(--border) (L816); border-radius: var(--radius-md) (L817); background: var(--bg-surface) (L818); color: var(--text-primary) (L819); font-size: var(--font-sm) (L820) |
| pages/schedule.css:828 | `.schedule-textarea` | (0,1,0) | base | forward | padding: var(--space-2) var(--space-3) (L829); resize: vertical (L830) |
| pages/schedule.css:833 | `.schedule-textarea:focus` | (0,2,0) | self:focus | forward | outline: none (L835); border-color: var(--accent) (L836); box-shadow: var(--focus-ring-shadow) (L837) |

## pages/staff-reports/StaffReportsPage.tsx:90

- 開始タグ: `<textarea required value={form.review} onChange={e => setForm({ ...form, review: e.target.value })} style={{ minHeight: 'var(--textarea-min-h-lg)' }} />`
- className: (なし) / 静的トークン: [] / 条件付き: []
- 属性: {"required":"true"}
- inline style: min-height: var(--textarea-min-h-lg)
- 祖先連鎖: 6 本（異なるシグネチャ 6）。先頭: div.form-group < form < div.comp-modal-body < div.comp-modal-dialog < div.comp-modal-overlay < div < div.page-layout < main.mobile-content < div.mobile-shell
- 画面側CSS import: own=[] / forward(共通除く)=["components/ContentToolbar.css","components/Button.css","constants/platform-icon.css","components/Modal.css","components/FormField.css"] / reverse=[]

| file:line | selector | 特異度 | 状態 | 読込 | 宣言 |
|---|---|---|---|---|---|
| components.css:19 | `.form-group textarea` | (0,1,1) | base | global | width: 100% (L21); padding: var(--space-2) var(--space-3) (L22); border: 1px solid var(--border) (L23); border-radius: var(--radius-sm) (L24); font-size: var(--font-base) (L25); color: var(--text-primary) (L26); background: var(--bg-surface) (L27); box-sizing: border-box (L28) |
| components.css:31 | `.form-group textarea:focus` | (0,2,1) | self:focus | global | outline: none (L33); border-color: var(--accent) (L34); box-shadow: var(--focus-ring-shadow) (L35) |
| components.css:39 | `.form-group textarea` | (0,1,1) | base | global | min-height: var(--textarea-min-h) (L40); resize: vertical (L41) |

## pages/staff-reports/StaffReportsPage.tsx:91

- 開始タグ: `<textarea value={form.goals} onChange={e => setForm({ ...form, goals: e.target.value })} />`
- className: (なし) / 静的トークン: [] / 条件付き: []
- 属性: {}
- inline style: なし
- 祖先連鎖: 6 本（異なるシグネチャ 6）。先頭: div.form-group < form < div.comp-modal-body < div.comp-modal-dialog < div.comp-modal-overlay < div < div.page-layout < main.mobile-content < div.mobile-shell
- 画面側CSS import: own=[] / forward(共通除く)=["components/ContentToolbar.css","components/Button.css","constants/platform-icon.css","components/Modal.css","components/FormField.css"] / reverse=[]

| file:line | selector | 特異度 | 状態 | 読込 | 宣言 |
|---|---|---|---|---|---|
| components.css:19 | `.form-group textarea` | (0,1,1) | base | global | width: 100% (L21); padding: var(--space-2) var(--space-3) (L22); border: 1px solid var(--border) (L23); border-radius: var(--radius-sm) (L24); font-size: var(--font-base) (L25); color: var(--text-primary) (L26); background: var(--bg-surface) (L27); box-sizing: border-box (L28) |
| components.css:31 | `.form-group textarea:focus` | (0,2,1) | self:focus | global | outline: none (L33); border-color: var(--accent) (L34); box-shadow: var(--focus-ring-shadow) (L35) |
| components.css:39 | `.form-group textarea` | (0,1,1) | base | global | min-height: var(--textarea-min-h) (L40); resize: vertical (L41) |

## pages/staff-reports/StaffReportsPage.tsx:92

- 開始タグ: `<textarea value={form.challenges} onChange={e => setForm({ ...form, challenges: e.target.value })} />`
- className: (なし) / 静的トークン: [] / 条件付き: []
- 属性: {}
- inline style: なし
- 祖先連鎖: 6 本（異なるシグネチャ 6）。先頭: div.form-group < form < div.comp-modal-body < div.comp-modal-dialog < div.comp-modal-overlay < div < div.page-layout < main.mobile-content < div.mobile-shell
- 画面側CSS import: own=[] / forward(共通除く)=["components/ContentToolbar.css","components/Button.css","constants/platform-icon.css","components/Modal.css","components/FormField.css"] / reverse=[]

| file:line | selector | 特異度 | 状態 | 読込 | 宣言 |
|---|---|---|---|---|---|
| components.css:19 | `.form-group textarea` | (0,1,1) | base | global | width: 100% (L21); padding: var(--space-2) var(--space-3) (L22); border: 1px solid var(--border) (L23); border-radius: var(--radius-sm) (L24); font-size: var(--font-base) (L25); color: var(--text-primary) (L26); background: var(--bg-surface) (L27); box-sizing: border-box (L28) |
| components.css:31 | `.form-group textarea:focus` | (0,2,1) | self:focus | global | outline: none (L33); border-color: var(--accent) (L34); box-shadow: var(--focus-ring-shadow) (L35) |
| components.css:39 | `.form-group textarea` | (0,1,1) | base | global | min-height: var(--textarea-min-h) (L40); resize: vertical (L41) |

## pages/super-admin/ExtractionPromptConfigTab.tsx:222

- 開始タグ: `<textarea value={configs[key].prompt_text} data-testid={'prompt-textarea-${key}'} onChange={(e) => setConfigs((prev) => ({ ...prev, [key]: { ...prev[key], prompt_text: e.target.value }, })) } placeholder={t('${p}.placeholder')} rows={16} style={{ width: "100%", fontFamily: "var(--font-mono, monospac`
- className: (なし) / 静的トークン: [] / 条件付き: []
- 属性: {"placeholder":"{t(`${p}.placeholder`)}","rows":"{16}"}
- inline style: width: 100%; font-family: var(--font-mono, monospace); font-size: var(--font-sm); box-sizing: border-box
- 祖先連鎖: 2 本（異なるシグネチャ 2）。先頭: section < div < div.analysis-panel-content < div.hub-content < div.hub-shell < div < div.page-layout < main.mobile-content < div.mobile-shell
- 画面側CSS import: own=[] / forward(共通除く)=["components/Button.css"] / reverse=["pages/super-admin/AnalysisRulesPage.css"]

## pages/super-admin/components/ConditionsMasterPanel.tsx:367

- 開始タグ: `<textarea value={form.search_kw} onChange={e => setForm({ ...form, search_kw: e.target.value })} rows={3} style={{ width: "100%", resize: "vertical" }} />`
- className: (なし) / 静的トークン: [] / 条件付き: []
- 属性: {"rows":"{3}"}
- inline style: width: 100%; resize: vertical
- 祖先連鎖: 2 本（異なるシグネチャ 2）。先頭: div.form-group < div < form < div.comp-drawer-body < div.comp-drawer-panel < div.analysis-panel-content < div.hub-content < div.hub-shell < div < div.page-layout < main.mobile-content < div.mobile-shell
- 画面側CSS import: own=[] / forward(共通除く)=["components/ContentToolbar.css","components/Button.css","constants/platform-icon.css","components/DataTable.css","components/EmptyState.css","components/FormField.css","components/Drawer.css","components/Modal.css"] / reverse=["pages/super-admin/AnalysisRulesPage.css"]

| file:line | selector | 特異度 | 状態 | 読込 | 宣言 |
|---|---|---|---|---|---|
| components.css:19 | `.form-group textarea` | (0,1,1) | base | global | width: 100% (L21); padding: var(--space-2) var(--space-3) (L22); border: 1px solid var(--border) (L23); border-radius: var(--radius-sm) (L24); font-size: var(--font-base) (L25); color: var(--text-primary) (L26); background: var(--bg-surface) (L27); box-sizing: border-box (L28) |
| components.css:31 | `.form-group textarea:focus` | (0,2,1) | self:focus | global | outline: none (L33); border-color: var(--accent) (L34); box-shadow: var(--focus-ring-shadow) (L35) |
| components.css:39 | `.form-group textarea` | (0,1,1) | base | global | min-height: var(--textarea-min-h) (L40); resize: vertical (L41) |

## pages/super-admin/components/ConditionsMasterPanel.tsx:380

- 開始タグ: `<textarea value={form.exclude_kw} onChange={e => setForm({ ...form, exclude_kw: e.target.value })} rows={3} style={{ width: "100%", resize: "vertical" }} />`
- className: (なし) / 静的トークン: [] / 条件付き: []
- 属性: {"rows":"{3}"}
- inline style: width: 100%; resize: vertical
- 祖先連鎖: 2 本（異なるシグネチャ 2）。先頭: div.form-group < div < form < div.comp-drawer-body < div.comp-drawer-panel < div.analysis-panel-content < div.hub-content < div.hub-shell < div < div.page-layout < main.mobile-content < div.mobile-shell
- 画面側CSS import: own=[] / forward(共通除く)=["components/ContentToolbar.css","components/Button.css","constants/platform-icon.css","components/DataTable.css","components/EmptyState.css","components/FormField.css","components/Drawer.css","components/Modal.css"] / reverse=["pages/super-admin/AnalysisRulesPage.css"]

| file:line | selector | 特異度 | 状態 | 読込 | 宣言 |
|---|---|---|---|---|---|
| components.css:19 | `.form-group textarea` | (0,1,1) | base | global | width: 100% (L21); padding: var(--space-2) var(--space-3) (L22); border: 1px solid var(--border) (L23); border-radius: var(--radius-sm) (L24); font-size: var(--font-base) (L25); color: var(--text-primary) (L26); background: var(--bg-surface) (L27); box-sizing: border-box (L28) |
| components.css:31 | `.form-group textarea:focus` | (0,2,1) | self:focus | global | outline: none (L33); border-color: var(--accent) (L34); box-shadow: var(--focus-ring-shadow) (L35) |
| components.css:39 | `.form-group textarea` | (0,1,1) | base | global | min-height: var(--textarea-min-h) (L40); resize: vertical (L41) |

## pages/suppliers/SupplierFormFields.tsx:61

- 開始タグ: `<textarea value={form.address} onChange={e => onChange("address", e.target.value)} />`
- className: (なし) / 静的トークン: [] / 条件付き: []
- 属性: {}
- inline style: なし
- 祖先連鎖: 14 本（異なるシグネチャ 14）。先頭: div.form-group < form < div < div.page-layout < main.mobile-content < div.mobile-shell
- 画面側CSS import: own=[] / forward(共通除く)=[] / reverse=[]

| file:line | selector | 特異度 | 状態 | 読込 | 宣言 |
|---|---|---|---|---|---|
| components.css:19 | `.form-group textarea` | (0,1,1) | base | global | width: 100% (L21); padding: var(--space-2) var(--space-3) (L22); border: 1px solid var(--border) (L23); border-radius: var(--radius-sm) (L24); font-size: var(--font-base) (L25); color: var(--text-primary) (L26); background: var(--bg-surface) (L27); box-sizing: border-box (L28) |
| components.css:31 | `.form-group textarea:focus` | (0,2,1) | self:focus | global | outline: none (L33); border-color: var(--accent) (L34); box-shadow: var(--focus-ring-shadow) (L35) |
| components.css:39 | `.form-group textarea` | (0,1,1) | base | global | min-height: var(--textarea-min-h) (L40); resize: vertical (L41) |

## pages/suppliers/SupplierFormFields.tsx:68

- 開始タグ: `<textarea value={form.notes} onChange={e => onChange("notes", e.target.value)} />`
- className: (なし) / 静的トークン: [] / 条件付き: []
- 属性: {}
- inline style: なし
- 祖先連鎖: 14 本（異なるシグネチャ 14）。先頭: div.form-group < form < div < div.page-layout < main.mobile-content < div.mobile-shell
- 画面側CSS import: own=[] / forward(共通除く)=[] / reverse=[]

| file:line | selector | 特異度 | 状態 | 読込 | 宣言 |
|---|---|---|---|---|---|
| components.css:19 | `.form-group textarea` | (0,1,1) | base | global | width: 100% (L21); padding: var(--space-2) var(--space-3) (L22); border: 1px solid var(--border) (L23); border-radius: var(--radius-sm) (L24); font-size: var(--font-base) (L25); color: var(--text-primary) (L26); background: var(--bg-surface) (L27); box-sizing: border-box (L28) |
| components.css:31 | `.form-group textarea:focus` | (0,2,1) | self:focus | global | outline: none (L33); border-color: var(--accent) (L34); box-shadow: var(--focus-ring-shadow) (L35) |
| components.css:39 | `.form-group textarea` | (0,1,1) | base | global | min-height: var(--textarea-min-h) (L40); resize: vertical (L41) |

## pages/teams/TeamFormFields.tsx:44

- 開始タグ: `<textarea value={form.description} onChange={(e) => onChange("description", e.target.value)} />`
- className: (なし) / 静的トークン: [] / 条件付き: []
- 属性: {}
- inline style: なし
- 祖先連鎖: 14 本（異なるシグネチャ 14）。先頭: div.form-group < form < div < div.page-layout < main.mobile-content < div.mobile-shell
- 画面側CSS import: own=[] / forward(共通除く)=[] / reverse=["pages/teams/TeamsPage.css"]

| file:line | selector | 特異度 | 状態 | 読込 | 宣言 |
|---|---|---|---|---|---|
| components.css:19 | `.form-group textarea` | (0,1,1) | base | global | width: 100% (L21); padding: var(--space-2) var(--space-3) (L22); border: 1px solid var(--border) (L23); border-radius: var(--radius-sm) (L24); font-size: var(--font-base) (L25); color: var(--text-primary) (L26); background: var(--bg-surface) (L27); box-sizing: border-box (L28) |
| components.css:31 | `.form-group textarea:focus` | (0,2,1) | self:focus | global | outline: none (L33); border-color: var(--accent) (L34); box-shadow: var(--focus-ring-shadow) (L35) |
| components.css:39 | `.form-group textarea` | (0,1,1) | base | global | min-height: var(--textarea-min-h) (L40); resize: vertical (L41) |

## 全規則共通メモ
- ユニバーサル基底規則（* 等、全要素に効く）: index.css:419 *
- CSS ネスト未評価: 0 件
- textarea 要素セレクタの全体 grep は ax2-shared-rules.md を参照
