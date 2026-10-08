# av2-inventory (origin/main 0f5d7e537, TS 5.9.3, tsx scanned 275, syntax-error files 0)

total raw textarea 54 / inside mold 1 / page-side 53 / with ui-allow 2 / Textarea mold usages 13

## Raw <textarea>
| file:line | className | attrs (raw text, style/ref/key attrs shown) | ui-allow | ancestors (tag@line class, up to 3) |
|---|---|---|---|---|
| frontend/src/components/MergeLeadModal.tsx:234 | - | rows={2}; placeholder={t("mergeLead.reasonPlaceholder")}; value; onChange; maxLength={500} |  | div@232 "form-row" > div@134 "modal-content-wide" > Modal@133 - |
| frontend/src/components/OrderFinancialPanel.tsx:239 | - | value; onChange; aria-label={t("financial.notesAriaLabel")} |  | div@237 "form-group" > form@210 - > Modal@206 - |
| frontend/src/components/PriorityScoreOverride.tsx:91 | - | value; onChange; maxLength={500}; placeholder={t("priority.overrideNotePlaceholder")} |  | div@89 "form-group" > form@74 - > Modal@71 - |
| frontend/src/components/PurchaseDetailPanel.tsx:442 | - | value; onChange; data-testid="pur-input-purchase_note" |  | div@440 "form-group" > form@311 - > Modal@301 - |
| frontend/src/components/ShippingDetailPanel.tsx:551 | - | value; onChange; data-testid="ship-input-ship_memo" |  | div@549 "form-group" > form@384 - > Modal@374 - |
| frontend/src/components/Textarea.tsx:63 (MOLD) | "comp-field__textarea" | id={fieldId}; ...spread={...rest} |  | div@52 {containerClass} |
| frontend/src/features/tcg-analysis-review/ItemComparison.tsx:27 | - | value; maxLength={2000}; aria-label={t('tcgAnalysisReview.manualCorrection', { field: t(labelKey) })}; onChange |  |  |
| frontend/src/features/tcg-analysis-review/ItemComparison.tsx:34 | - | id={`note-${item.extraction_item_id}`}; value; maxLength={2000}; onChange |  | div@34 "manual-actions" > div@34 "item-extra-grid" > article@34 {readOnly ? 'item-comparison item-comparison--readonly' : 'item-comparison'} |
| frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:217 | - | value; onChange |  | label@215 "pmd-field" > div@194 "pmd-fields" |
| frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:221 | - | value; onChange |  | label@219 "pmd-field" > div@194 "pmd-fields" |
| frontend/src/pages/admin/DiscordAnnouncePage.tsx:98 | "input w-full resize-y" | value; onChange; disabled={!canEdit}; placeholder={t("discordAnnounce.messagePlaceholder")}; maxLength={2000}; rows={6} |  | div@94 "space-y-2" > div@70 "max-w-lg space-y-6" > PageLayout@69 - |
| frontend/src/pages/admin/TenantProfilePage.tsx:170 | - | id="tp-address"; data-testid="tp-address"; value; onChange; disabled={!canEdit}; rows={3} |  | div@168 "form-group" > form@138 "form" > PageLayout@134 - |
| frontend/src/pages/badges/BadgesPage.tsx:62 | - | value; onChange |  | div@62 "form-group" > form@58 - > Modal@52 - |
| frontend/src/pages/buddy/BuddyPage.tsx:66 | - | value; onChange |  | div@66 "form-group" > form@63 - > Modal@57 - |
| frontend/src/pages/companies/CompaniesPage.tsx:499 | - | value; onChange |  | div@497 "form-row" > form@446 "form-grid" > div@439 "modal-content-wide" |
| frontend/src/pages/companies/CompaniesPage.tsx:516 | - | value; onChange |  | div@514 "form-row" > form@446 "form-grid" > div@439 "modal-content-wide" |
| frontend/src/pages/companies/CompanyFormFields.tsx:64 | - | value; onChange |  | div@62 "form-group" |
| frontend/src/pages/company-detail/CompanyBasicTab.tsx:81 | - | disabled={!canEdit}; value; onChange |  | div@80 "form-row" > form@35 "form-grid" |
| frontend/src/pages/company-detail/CompanyBasicTab.tsx:94 | - | disabled={!canEdit}; value; onChange |  | div@93 "form-row" > form@35 "form-grid" |
| frontend/src/pages/conditions/ConditionsPage.tsx:340 | "field field-h-md" | style={{ height: "80px", resize: "vertical", width: "100%" }}; value; onChange | 339: {/* ui-allow: multi-line keyword input; TextField does not support textarea variant (#3594) */} | div@337 "form-group" > div@304 - |
| frontend/src/pages/conditions/ConditionsPage.tsx:350 | "field field-h-md" | style={{ height: "80px", resize: "vertical", width: "100%" }}; value; onChange | 349: {/* ui-allow: multi-line keyword input; TextField does not support textarea variant (#3594) */} | div@347 "form-group" > div@304 - |
| frontend/src/pages/contacts/ContactEditPage.tsx:191 | - | value; onChange |  | div@190 "form-group" > form@140 - > PageLayout@135 - |
| frontend/src/pages/contacts/ContactsPage.tsx:349 | - | value; onChange |  | div@348 "form-row" > form@302 "form-grid" > div@301 "modal-content-wide" |
| frontend/src/pages/dashboard/PriorityProspectsSection.tsx:410 | "db-weekly-composer-input" | id={`priority-action-${item.lead_id}`}; rows={3}; value; onChange |  | div@406 "db-weekly-composer-field" > div@391 "db-weekly-composer" > li@342 {`db-priority-item${hasAxisLowSample ? " db-priority-item--no-sample" : ""}`} |
| frontend/src/pages/dashboard/WeeklyAdvisorSection.tsx:381 | "db-weekly-composer-input" | id={`weekly-action-${action.company_id}`}; rows={3}; value; onChange |  | div@377 "db-weekly-composer-field" > div@362 "db-weekly-composer" > li@302 {`db-weekly-item db-weekly-item--${action.type}`} |
| frontend/src/pages/inbox/InboxKartePanel.tsx:484 | "right-panel-field" | rows={3}; value; onChange; onBlur; placeholder={t("inbox.emptyField")} |  | div@431 "right-panel-section" |
| frontend/src/pages/inbox/InboxKartePanel.tsx:503 | "right-panel-field" | rows={3}; value; onChange; onBlur; placeholder={t("inbox.emptyField")} |  | div@499 "right-panel-section" |
| frontend/src/pages/inbox/InboxKartePanel.tsx:537 | "right-panel-field" | rows={3}; value; onChange; onBlur; placeholder={t("inbox.emptyField")} |  | div@499 "right-panel-section" |
| frontend/src/pages/inbox/InboxKartePanel.tsx:588 | "right-panel-field" | rows={3}; value; onChange; onBlur; placeholder={t("inbox.emptyField")} |  | div@499 "right-panel-section" |
| frontend/src/pages/inbox/InboxMessageThread.tsx:736 | "inbox-textarea" | ref={textareaRef}; value; onChange; onKeyDown; placeholder={                   discordChannelMissing                     ? t("inbox.discordChannelMissing")                     : canSend                      ; rows={2}; disabled={!canSend \|\| sending} |  | div@735 "send-input-wrap" > div@731 "send-top-row" > div@715 "send-card" |
| frontend/src/pages/inbox/InboxProfileModal.tsx:181 | "right-panel-field" | rows={3}; value; onChange; onBlur; placeholder={t("leads.csMemo")} |  | div@144 "right-panel-section" > div@110 "right-panel-tab-content" > div@65 "inbox-profile-modal" |
| frontend/src/pages/inbox/InboxProfileModal.tsx:191 | "right-panel-field" | rows={3}; value; onChange; onBlur; placeholder={t("leads.nextAction")} |  | div@189 "right-panel-section" > div@110 "right-panel-tab-content" > div@65 "inbox-profile-modal" |
| frontend/src/pages/inbox/InboxProfileModal.tsx:210 | "right-panel-field" | rows={3}; value; onChange; onBlur; placeholder={t("leads.challenge")} |  | div@189 "right-panel-section" > div@110 "right-panel-tab-content" > div@65 "inbox-profile-modal" |
| frontend/src/pages/inbox/InboxProfileModal.tsx:265 | "right-panel-field" | rows={3}; value; onChange; onBlur; placeholder={t("leads.meetingMemo")} |  | div@189 "right-panel-section" > div@110 "right-panel-tab-content" > div@65 "inbox-profile-modal" |
| frontend/src/pages/inbox/ManualRecordSection.tsx:159 | "manual-record-textarea" | value; onChange; onKeyDown; placeholder={t("inbox.manualRecord.contentPlaceholder")}; rows={3}; disabled={saving}; aria-label={t("inbox.manualRecord.contentPlaceholder")} |  | div@110 "manual-record-section" |
| frontend/src/pages/inbox/OutboundTranslationPreview.tsx:147 | "outbound-translation-edit" | value; onChange; rows={4}; disabled={confirming}; aria-label={t("translation.outbound.editAriaLabel")} |  | div@119 "outbound-translation-section" > div@83 "outbound-translation-modal" > div@82 "outbound-translation-overlay" |
| frontend/src/pages/leads/LeadEditPage.tsx:279 | - | value; onChange |  | div@278 "form-group" > form@169 - > PageLayout@164 - |
| frontend/src/pages/leads/LeadFormFields.tsx:84 | - | id={memoId}; value; onChange; placeholder={t("leads.lostReasonPlaceholder")} |  | div@82 "form-group" |
| frontend/src/pages/leads/LeadFormFields.tsx:153 | - | value; onChange |  | div@151 "form-group" |
| frontend/src/pages/leads/LeadsPage.tsx:429 | - | value; onChange |  | div@428 "form-group" > form@327 - > Modal@321 - |
| frontend/src/pages/orders/OrdersFormModal.tsx:95 | - | value; onChange |  | div@93 "form-group" > form@52 - > Modal@46 - |
| frontend/src/pages/products/ProductEditPage.tsx:309 | - | value; onChange |  | div@307 "form-group form-group-full" > form@207 "product-edit-form" > div@206 "page page--full" |
| frontend/src/pages/purchase-orders/PurchaseOrdersFormModal.tsx:217 | - | rows={3}; value; onChange |  | div@215 "form-group" > form@154 - > Modal@146 - |
| frontend/src/pages/roles/RolesPage.tsx:538 | - | value; onChange |  | div@537 "form-group" > form@491 - > Modal@485 - |
| frontend/src/pages/schedule/SchedulePageImpl.tsx:378 | "schedule-textarea" | rows={4}; value; onChange; placeholder={t("schedule.descriptionPlaceholder")} |  | label@376 "schedule-field" > div@276 "schedule-popover__body schedule-popover__body--form" > div@204 "schedule-popover" |
| frontend/src/pages/staff-reports/StaffReportsPage.tsx:90 | - | required=(true); value; onChange; style={{ minHeight: 'var(--textarea-min-h-lg)' }} |  | div@90 "form-group" > form@79 - > Modal@73 - |
| frontend/src/pages/staff-reports/StaffReportsPage.tsx:91 | - | value; onChange |  | div@91 "form-group" > form@79 - > Modal@73 - |
| frontend/src/pages/staff-reports/StaffReportsPage.tsx:92 | - | value; onChange |  | div@92 "form-group" > form@79 - > Modal@73 - |
| frontend/src/pages/super-admin/ExtractionPromptConfigTab.tsx:222 | - | value; data-testid={`prompt-textarea-${key}`}; onChange; placeholder={t(`${p}.placeholder`)}; rows={16}; style={{               width: "100%",               fontFamily: "var(--font-mono, monospace)",               fontSize: "var(--font-sm)",               boxSizing |  | section@137 - > div@118 - |
| frontend/src/pages/super-admin/components/ConditionsMasterPanel.tsx:367 | - | value; onChange; rows={3}; style={{ width: "100%", resize: "vertical" }} |  | div@363 "form-group" > div@317 - > form@316 - |
| frontend/src/pages/super-admin/components/ConditionsMasterPanel.tsx:380 | - | value; onChange; rows={3}; style={{ width: "100%", resize: "vertical" }} |  | div@376 "form-group" > div@317 - > form@316 - |
| frontend/src/pages/suppliers/SupplierFormFields.tsx:61 | - | value; onChange |  | div@59 "form-group" |
| frontend/src/pages/suppliers/SupplierFormFields.tsx:68 | - | value; onChange |  | div@66 "form-group" |
| frontend/src/pages/teams/TeamFormFields.tsx:44 | - | value; onChange |  | div@42 "form-group" |

## Textarea mold usages
| file:line | attrs (raw) |
|---|---|
| frontend/src/components/MergeCompanyModal.tsx:246 | rows={2}; placeholder={t("mergeCompany.reasonPlaceholder")}; value={reason}; onChange={(e) => setReason(e.target.value)}; maxLength={500} |
| frontend/src/components/MergeContactModal.tsx:244 | label={t("mergeContact.reasonLabel")}; rows={2}; placeholder={t("mergeContact.reasonPlaceholder")}; value={reason}; onChange={(e) => setReason(e.target.value)}; maxLength={500} |
| frontend/src/features/tcg-product-import/TcgProductDetailDrawer.tsx:238 | label={t("productDetail.search_keywords")}; helperText={t("productDetail.wordsHint")}; value={draft.search_keywords}; onChange={e => change("search_keywords", e.target.value)}; rows={5}; disabled={saving}; fullWidth |
| frontend/src/features/tcg-product-import/TcgProductDetailDrawer.tsx:240 | label={t("productDetail.exclude_keywords")}; helperText={t("productDetail.wordsHint")}; value={draft.exclude_keywords}; onChange={e => change("exclude_keywords", e.target.value)}; rows={4}; disabled={saving}; fullWidth |
| frontend/src/pages/admin/DiscordConfigPage.tsx:419 | value={welcomeTemplate}; onChange={(e) => setWelcomeTemplate(e.target.value)}; disabled={!canEdit}; placeholder={t("discordTicketConfig.welcomePlaceholder")}; helperText={t("discordTicketConfig.welcomeHint", {               count: welcomeTemplate.length,               max: WELCOME_MAX_LENGTH,             })}; maxLength={WELCOME_MAX_LENGTH}; rows={4}; aria-label={t("discordTicketConfig.welcomeTitle")}; fullWidth |
| frontend/src/pages/design-preview/sections/FormSection.tsx:71 | label="メモ"; placeholder="メモを入力してください..."; helperText="チーム全員に表示されます。" |
| frontend/src/pages/design-preview/sections/FormSection.tsx:75 | label="メッセージ"; placeholder="メッセージを入力..."; error="メッセージを入力してください。"; required |
| frontend/src/pages/design-preview/sections/FormSection.tsx:79 | label="テンプレート本文"; defaultValue="このテンプレートはロックされています。"; disabled; helperText="変更できません。" |
| frontend/src/pages/super-admin/SupplierExtractionRulesPage.tsx:784 | label={t("supplierExtractionRules.extractionInstruction")}; value={form.extraction_notes}; onChange={(e) =>                 setForm((prev) => ({ ...prev, extraction_notes: e.target.value }))               }; rows={10}; placeholder={t("supplierExtractionRules.extractionInstructionPlaceholder")}; fullWidth |
| frontend/src/pages/super-admin/SupplierExtractionRulesPage.tsx:795 | label={t("supplierExtractionRules.exampleText")}; value={form.extraction_example_text}; onChange={(e) =>                 setForm((prev) => ({ ...prev, extraction_example_text: e.target.value }))               }; rows={8}; placeholder={t("supplierExtractionRules.exampleTextPlaceholder")}; fullWidth |
| frontend/src/pages/super-admin/SupplierExtractionRulesPage.tsx:806 | label={t("supplierExtractionRules.shipFormat")}; helperText={t("supplierExtractionRules.shipFormatHelper")}; value={form.extraction_ship_format}; onChange={(e) =>                 setForm((prev) => ({ ...prev, extraction_ship_format: e.target.value }))               }; rows={4}; fullWidth |
| frontend/src/pages/super-admin/SupplierExtractionRulesPage.tsx:817 | label={t("supplierExtractionRules.layoutRules")}; helperText={t("supplierExtractionRules.layoutRulesHelper")}; value={form.extraction_layout_rules}; onChange={(e) =>                 setForm((prev) => ({ ...prev, extraction_layout_rules: e.target.value }))               }; rows={8}; fullWidth |
| frontend/src/pages/super-admin/SupplierExtractionRulesPage.tsx:828 | label={t("supplierExtractionRules.hardCases")}; helperText={t("supplierExtractionRules.hardCasesHelper")}; value={form.extraction_hard_cases}; onChange={(e) =>                 setForm((prev) => ({ ...prev, extraction_hard_cases: e.target.value }))               }; rows={8}; fullWidth |

## raw attr-name counts (all 54 incl. mold)
{"rows":21,"placeholder":16,"value":53,"onChange":53,"maxLength":5,"aria-label":4,"data-testid":4,"id":6,"className":18,"...spread":1,"disabled":7,"style":6,"onBlur":8,"ref":1,"onKeyDown":2,"required":1}

## mold-usage attr-name counts (13)
{"rows":10,"placeholder":7,"value":10,"onChange":10,"maxLength":3,"label":11,"helperText":8,"disabled":4,"fullWidth":8,"aria-label":1,"error":1,"required":1,"defaultValue":1}
