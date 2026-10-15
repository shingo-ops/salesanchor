# AY-4b チェック欄の現状調査（recon）

- 調査日: 2026-10-15 / 基点: origin/main 5b0486ad0（#4339 マージ後）/ ブランチ: release/checkbox-ay4b
- 範囲: frontend/src の生 checkbox。コードは変更していない。
- 生出力: /tmp/CC報告ファイル/ssot-checkbox/ay4b/recon/（preflight.txt, grep_all.txt, grep_other.txt, reach.txt, app_pages.txt, css_checkbox.txt, ay4b_targets.txt, ay4b_markup.txt, general_ay4c.txt）

## 既存 ADR 検索結果

- `git grep -il checkbox -- docs/adr/` の結果: `docs/adr/ADR-067-design-token-enforcement.md` の1件のみ。
- `docs/adr/FEATURE-INDEX.md` に checkbox を含む行: 0件（`git grep -n -i checkbox docs/adr/FEATURE-INDEX.md` が空）。
- 【事実】チェック欄の金型移管専用の ADR は無い。設計の正本は ADR-144 と各 design.md（Checkbox.tsx:2, CheckboxControl.tsx:2 のコメントが参照）。

## 件数表（`type="checkbox"` の出現。検索は `type="checkbox"` / `type='checkbox'` / `type={` の3系統）

| 区分 | 件数 | 内訳 |
|---|---|---|
| frontend/src 全体（tsx の生 `<input type="checkbox">` 行） | 60 | git grep（grep_all.txt の 65 行から CSS セレクタ 5 行を除く） |
| 金型・既製部品の中身（別枠） | 3 | Checkbox.tsx:50 / CheckboxControl.tsx:38 / Toggle.tsx:30 |
| 上記を除いた生 checkbox | 57 | |
| AY-4b 対象 | 24 | super-admin 専用 20 + どの画面からも未到達 4 |
| 一般画面（AY-4c） | 33 | 23 ファイル（末尾の一覧） |
| 試験（*.test.tsx）での `type="checkbox"` 直書き | 0 | getByRole("checkbox") の使用のみ |
| story（*.stories.tsx）での `type="checkbox"` 直書き | 0 | |
| `type={...}` 形式で checkbox になるもの | 0 | grep_other.txt に該当なし |
| CSS セレクタ（参考） | 5 | components.css:19,33 / pages-layout.css:623,647 / pages/inbox/InboxPage.css:1869 |

補足【事実】金型の既存使用: CheckboxControl は DataTable.tsx:314,347,427、Checkbox は pages/notifications/NotificationsPage.tsx:131,157 のみ。

## 到達する画面の調べ方と結果

方法: frontend/src の import を解析するスクリプト（テスト・story からの import は除外）で、各 checkbox を含むファイルから App.tsx（frontend/src/App.tsx）へ逆にたどった（reach.txt, app_pages.txt）。

【事実】
- super-admin 専用の判定: 到達する App.tsx 直下のページが下のいずれかで、各ページが `useSuperAdmin()` で非 super-admin を拒否している。
  - frontend/src/pages/super-admin/AnalysisRulesPage.tsx:18,100,124（ルート /super-admin/analysis-rules、frontend/src/App.tsx:313 付近の `<AnalysisRulesPage />`）
  - frontend/src/pages/super-admin/TcgDistributionPage.tsx:9,19,30（ルート /super-admin/tcg-distribution）
  - frontend/src/pages/super-admin/TcgLineImportPage.tsx:16（ルート /super-admin/tcg-line-import）。DistributionWorkspace を import（同:23）
- ProductMasterDrawer.tsx は SupplierDetailView.tsx 経由で AnalysisRulesPage のみ（app_pages.txt）。
- DistributionTargetForm.tsx は DistributionWorkspace / DistributionTargetList 経由で TcgDistributionPage と TcgLineImportPage のみ（どちらも super-admin 専用）。
- 未到達:
  - frontend/src/features/supplier-master/SupplierDetailDrawer.tsx は frontend/src/features/supplier-master/index.ts:1 でだけ export される。index.ts を import するファイルは frontend 全体で 0（`git grep SupplierDetailDrawer -- frontend` が index.ts と自身のみ）。
  - frontend/src/pages/integrations/FedexLabelValidationTab.tsx は import するファイル 0。`FedexEtdSetupGuide.tsx:9` は同名の CSS を読むだけ（`git grep FedexLabelValidationTab -- frontend`）。
- 一般画面（AY-4c）は全ページが App.tsx 直下のページ（InventoryPage, CompanyDetailPage, InboxPage など）に到達。一覧は末尾。

## AY-4b 対象 24 件

判断: ラベル文字と並ぶ（label で包み、同じ label 内に文字）→ Checkbox 候補。表のセル内で別セルに文字があるもの → CheckboxControl 候補。

| # | file:line | 到達 | 金型候補 | 判断の根拠 | 使っている属性 | かかっている CSS（規則: file:line） |
|---|---|---|---|---|---|---|
| 1 | frontend/src/features/supplier-master/SupplierDetailDrawer.tsx:414 | 未到達 | Checkbox | label 直下に文字 `{t(\`${f}.isActive\`)}`（:412-420） | checked, onChange, disabled | label のインライン style（flex, gap）のみ。クラス規則なし |
| 2 | frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:235 | super-admin | Checkbox | `label.pmd-confirm-check` 内に文字（:233-240） | checked, onChange | `.pmd-confirm-check` の規則は無い（全 CSS で 0 件）。親 `.pmd-warning`（supplier-detail-view.css:192）は背景・flex・gap のみ |
| 3 | frontend/src/features/tcg-distribution/DistributionTargetForm.tsx:240 | super-admin | Checkbox | `label.dist-checkbox-row` 内に文字（:238-245） | checked, onChange | `.dist-checkbox-row`（frontend/src/features/tcg-distribution/distribution.css:322-328: flex, align center, gap space-2, font-size sm, cursor pointer）。`.dist-field label`（同:306）は label が .dist-field の外なので非適用 |
| 4 | frontend/src/pages/integrations/FedexLabelValidationTab.tsx:290 | 未到達 | Checkbox | `label.lv-check-label` 内に文字（:288-295） | checked, onChange | `.lv-check-label`（frontend/src/pages/integrations/FedexLabelValidationTab.css:431-439: inline-flex, gap space-2, font-size sm, margin-top space-2） |
| 5 | frontend/src/pages/integrations/FedexLabelValidationTab.tsx:304 | 未到達 | Checkbox | 同上（:302-309） | checked, onChange | 同上 |
| 6 | frontend/src/pages/integrations/FedexLabelValidationTab.tsx:318 | 未到達 | Checkbox | 同上（:316-323） | checked, onChange | 同上 |
| 7 | frontend/src/pages/super-admin/ExtractionPromptConfigTab.tsx:210 | super-admin | 要判断 | label 内に文字（Checkbox 向き）だが、label のインライン style に marginBottom・color(text-secondary)・fontSize がある（:199-208）。Checkbox は root に style を渡せない | checked, onChange, data-testid(`prompt-active-${key}`) | label のインライン style のみ |
| 8 | frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:341 | super-admin | CheckboxControl | `table.data-table` の td 内で単独。文字は別セル。aria-label で名前付け（:339-347） | checked, onChange, aria-label, data-testid | td インライン style `textAlign:center` のみ。`.data-table` に input の規則なし |
| 9 | frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:417 | super-admin | CheckboxControl | 同上（:415-423） | checked, onChange, aria-label, data-testid | 同上 |
| 10 | frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:481 | super-admin | Checkbox | label 内に文字（:480-483） | checked, onChange | label インライン style（flex, gap）のみ。label は grid 直下で `.form-group` の外 |
| 11 | frontend/src/pages/super-admin/components/ConditionDefsMasterPanel.tsx:228 | super-admin | Checkbox | label 内に文字（:226-233） | checked, onChange | 同上（#10 と同じ形） |
| 12 | frontend/src/pages/super-admin/components/ConditionsMasterPanel.tsx:447 | super-admin | Checkbox | label 内に文字（:446-449） | checked, onChange | 同上 |
| 13 | frontend/src/pages/super-admin/components/NoteMasterPanel.tsx:302 | super-admin | Checkbox | label 内に文字（:300-307） | checked(form.enabled), onChange | 同上 |
| 14 | frontend/src/pages/super-admin/components/ProductCategoriesMasterPanel.tsx:282 | super-admin | Checkbox | label 内に文字（:280-287） | checked, onChange | 同上 |
| 15 | frontend/src/pages/super-admin/components/ProductFormatsMasterPanel.tsx:313 | super-admin | Checkbox | label 内に文字（:311-318） | checked, onChange | 同上 |
| 16 | frontend/src/pages/super-admin/components/ProductKindsMasterPanel.tsx:225 | super-admin | Checkbox | label 内に文字（:223-230） | checked, onChange | 同上 |
| 17 | frontend/src/pages/super-admin/components/ProductLinesMasterPanel.tsx:312 | super-admin | Checkbox | label 内に文字（:310-317） | checked, onChange | 同上 |
| 18 | frontend/src/pages/super-admin/components/QuantityUnitsMasterPanel.tsx:243 | super-admin | Checkbox | label 内に文字（:241-248） | checked, onChange | 同上 |
| 19 | frontend/src/pages/super-admin/components/RuleTestPanel.tsx:485 | super-admin | Checkbox | label 内の隣に `<span style={{fontSize: sm}}>` の文字（:483-490）。label style に cursor:pointer | checked, onChange | label インライン style（flex, gap, cursor） |
| 20 | frontend/src/pages/super-admin/components/SupplierMasterPanel.tsx:378 | super-admin | Checkbox | label 内に文字（:377-380） | checked, onChange | 同上（#10 形） |
| 21 | frontend/src/pages/super-admin/components/TypeMasterPanel.tsx:270 | super-admin | Checkbox | label 内に文字（:268-275） | checked, onChange | 同上 |
| 22 | frontend/src/pages/super-admin/components/UnitIgnorePhrasesPanel.tsx:170 | super-admin | Checkbox | label 内に文字（:167-175）。:168 に `ui-allow ... (#4032)` コメントあり | checked, onChange | 同上 |
| 23 | frontend/src/pages/super-admin/components/UnitMasterPanel.tsx:333 | super-admin | Checkbox | label 内に文字（:331-338） | checked, onChange | 同上 |
| 24 | frontend/src/pages/super-admin/components/WeightClassesMasterPanel.tsx:255 | super-admin | Checkbox | label 内に文字（:253-260） | checked, onChange | 同上 |

集計: Checkbox 候補 21（#1-6, #10-24）／CheckboxControl 候補 2（#8, #9）／要判断 1（#7）。合計 24。

### CSS の経由についての事実

- `.form-group input[type="checkbox"]`（frontend/src/components.css:19-31: width 100%, padding, border, radius, font-size, background）と `:focus` 版（同:33-42）は、AY-4b 対象 24 件のどれにも掛からない。理由: 対象の label / td は `.form-group` の子孫ではない（#10-24 は grid 直下で `.form-group` の兄弟。ソースで確認）。
- `.form-group label`（components.css:10-16: display block, font-size sm, weight medium, color text-secondary, margin-bottom）も同じ理由で非適用。
- `.form-row` 系（frontend/src/company-forms.css:94,102,128,137）は対象のどれも `.form-row` を使っていないので非適用。
- `.chk-label` / `.permission-item`（frontend/src/pages-layout.css:623,647）、`.sales-form-option`（frontend/src/pages/inbox/InboxPage.css:1869）は AY-4b 対象に使われていない（AY-4c 側）。
- 【未確認】ブラウザ上の実描画（Drawer / Modal 内での label の見た目）。今回は画面を開いていない。

## 金型の props（file:line）

### Checkbox（frontend/src/components/Checkbox.tsx）
- `CheckboxOwnProps`（:18-23）: `label: string`（必須）, `size?: "sm"|"md"|"lg"`, `error?: string`, `description?: string`
- `CheckboxProps`（:25-26）= OwnProps + `InputHTMLAttributes<HTMLInputElement>` から `label|size|error|description|type` を除いたもの
- 受ける: checked, onChange, disabled, name, value, id, aria-*, data-*, className, style など input の属性すべて。`className` は label（root）に付く（:29,36-43）。それ以外（style を含む）は `...rest` として input に付く（:54）。
- 受けない: `type`（固定 checkbox）、`children`（label は文字列のみ、:19）、label への style、`indeterminate`
- DOM: `label.comp-checkbox[htmlFor] > input.comp-checkbox__input + span.comp-checkbox__label`（:46-64）
- CSS: frontend/src/components/Checkbox.css:8-16（inline-flex, align flex-start, gap, font-size sm, color text-primary, cursor）、:35-46（input 1.1em, border, accent-color: var(--accent)）、:68-73（label span は flex column, font-weight medium）

### CheckboxControl（frontend/src/components/CheckboxControl.tsx）
- `CheckboxControlProps`（:79-83）: input の属性から `type|className|style|size|role` を除いたもの + `size?: "md"|"sm"` + `indeterminate?: boolean`
- 受ける: checked, onChange, disabled, id, name, value, aria-*, data-*（`...rest` を同じ input へ、:107）、ref
- 受けない: className, style, type, role
- DOM: `input.comp-checkbox-control` 1つ（:103-108）
- CSS: frontend/src/components/CheckboxControl.css:2-4（width/height var(--size-checkbox)=16px, accent-color: var(--accent), disabled の cursor）

## 置き換え可否（そのまま置き換えられるか）

- #8, #9（CheckboxControl）: 使っている属性 checked, onChange, aria-label, data-testid はすべて受けられる。足りない props なし。data-testid（rule-select-*, alias-select-*, prompt-active-*）を参照するファイルは `git grep` で KnowledgeAliasesTab.tsx と ExtractionPromptConfigTab.tsx 自身のみ（テストからの参照は 0 件）。
- Checkbox 候補 21 件: checked, onChange, disabled は受けられる。`label` は文字列で必須。対象の label 文言はいずれも `t()` の文字列または文字列の三項（#7）で、文字列として渡せる。
  - 足りない props: なし（必須のもの）。ただし見た目が変わる点【事実】:
    1. label span が font-weight medium（Checkbox.css:68-73）。現状の label は通常の太さ（インライン style に weight なし）。
    2. root が inline-flex・align-items flex-start（Checkbox.css:9-11）。現状は display:flex・align-items:center。1行ラベルでは差は小さいが、grid 内での幅（現状は列幅いっぱいの flex）は変わる【未確認: 実描画】。
    3. input サイズが 1.1em（Checkbox.css:37-38）。生 checkbox はブラウザ既定（約 13px）。
  - #3 `.dist-checkbox-row`, #4-6 `.lv-check-label`: className を Checkbox に渡せば root に付く（Checkbox.tsx:36-43）。ただし同じ要素に `.comp-checkbox` の規則と重なる。【未確認】CSS の読み込み順による勝敗。
  - #7: Checkbox の root に style を渡せない。marginBottom・color・fontSize を保つには className + CSS を足すか、外側 div で包む必要がある。→「要判断」。
  - #19 RuleTestPanel: 隣の span（fontSize sm）は Checkbox の label span に統合できる（Checkbox.css:9 が font-size sm 既定）。
- indeterminate / name / value / id を使っている対象: 0 件（24 件すべて上表の属性のみ）。

## 一般画面（AY-4c）33 件の所在（参考）

components/ContactChannelForm.tsx:228 / components/MultiSelect.tsx:79 / pages/admin/InventoryVisibilityPage.tsx:153 / pages/company-detail/CompanyAddressModal.tsx:147, CompanyContactsTab.tsx:207, CompanyDiscordTab.tsx:44 / pages/conditions/ConditionsPage.tsx:254,354 / pages/contacts/ContactEditPage.tsx:171, ContactsPage.tsx:333 / pages/inbox/InboxConversationList.tsx:121, InboxConversationListMobile.tsx:144, InboxProfileModal.tsx:255, SalesFormMultiSelect.tsx:135 / pages/inventory/InventoryFilterPanel.tsx:132,152,183,220,242,261 / pages/note-master/NoteMasterPage.tsx:315 / pages/product-categories/ProductCategoriesPage.tsx:225 / pages/products/ProductsPage.tsx:356 / pages/roles/RolesPage.tsx:398,408,422 / pages/schedule/SchedulePageImpl.tsx:523,554 / pages/staff/StaffEditPage.tsx:213, StaffPage.tsx:289 / pages/status-master/StatusMasterPage.tsx:302 / pages/units/UnitsPage.tsx:301,353（すべて frontend/src/ 配下。general_ay4c.txt に生出力）

## 未確認

- 実画面での見た目（Drawer / Modal 内）。置き換え後の比較は未実施。
- `.dist-checkbox-row` / `.lv-check-label` を Checkbox の className に渡したときの CSS 競合。
- 試験で getByRole("checkbox") を使う ProductMasterDrawer.test.tsx:119 と UnitIgnorePhrasesPanel.test.tsx:65 は、Checkbox / CheckboxControl でも role は checkbox のままだが、置き換え後の実行は未実施。

## 付録: AY-4b 対象 24 件の現在のマークアップ（ソースそのまま）

### frontend/src/features/supplier-master/SupplierDetailDrawer.tsx:414
```tsx
411:                 {/* ui-allow: single boolean toggle (#3564) */}
412:                 <label style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
413:                   <input
414:                     type="checkbox"
415:                     checked={draft.is_active}
416:                     onChange={e => change("is_active", e.target.checked)}
417:                     disabled={saving}
418:                   />
419:                   {t(`${f}.isActive`)}
420:                 </label>
```

### frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:235
```tsx
232:               ))}
233:               <label className="pmd-confirm-check">
234:                 <input
235:                   type="checkbox"
236:                   checked={confirmed}
237:                   onChange={(e) => setConfirmed(e.target.checked)}
238:                 />
239:                 {t('tcgAnalysisReview.productMasterDrawer.duplicateConfirmed')}
240:               </label>
241:             </section>
```

### frontend/src/features/tcg-distribution/DistributionTargetForm.tsx:240
```tsx
237:           {/* 有効フラグ */}
238:           <label className="dist-checkbox-row">
239:             <input
240:               type="checkbox"
241:               checked={values.is_active}
242:               onChange={(e) => set("is_active", e.target.checked)}
243:             />
244:             {t("distributionTarget.form.isActive")}
245:           </label>
246:         </div>
```

### frontend/src/pages/integrations/FedexLabelValidationTab.tsx:290
```tsx
287:         <p className="form-hint">{t("carrierIntegration.lvStep3Desc")}</p>
288:         <label className="lv-check-label">
289:           <input
290:             type="checkbox"
291:             checked={step3Done}
292:             onChange={(e) => setStep3Done(e.target.checked)}
293:           />
294:           {t("carrierIntegration.lvCheckDone")}
295:         </label>
296:       </section>
```

### frontend/src/pages/integrations/FedexLabelValidationTab.tsx:304
```tsx
301:         <p className="form-hint">{t("carrierIntegration.lvStep4Desc")}</p>
302:         <label className="lv-check-label">
303:           <input
304:             type="checkbox"
305:             checked={step4Done}
306:             onChange={(e) => setStep4Done(e.target.checked)}
307:           />
308:           {t("carrierIntegration.lvCheckDone")}
309:         </label>
310:       </section>
```

### frontend/src/pages/integrations/FedexLabelValidationTab.tsx:318
```tsx
315:         <p className="form-hint">{t("carrierIntegration.lvStep5Desc")}</p>
316:         <label className="lv-check-label">
317:           <input
318:             type="checkbox"
319:             checked={step5Done}
320:             onChange={(e) => setStep5Done(e.target.checked)}
321:           />
322:           {t("carrierIntegration.lvCheckDone")}
323:         </label>
324:       </section>
```

### frontend/src/pages/super-admin/ExtractionPromptConfigTab.tsx:210
```tsx
207:             }}
208:           >
209:             <input
210:               type="checkbox"
211:               checked={configs[key].is_active}
212:               data-testid={`prompt-active-${key}`}
213:               onChange={(e) =>
214:                 setConfigs((prev) => ({
215:                   ...prev,
216:                   [key]: { ...prev[key], is_active: e.target.checked },
```

### frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:341
```tsx
338:                 <tr key={r.id} data-testid={`rule-row-${r.id}`}>
339:                   <td style={{ textAlign: "center" }}>
340:                     <input
341:                       type="checkbox"
342:                       checked={ruleSelected.has(r.id)}
343:                       onChange={() => toggleRule(r.id)}
344:                       aria-label={r.pattern}
345:                       data-testid={`rule-select-${r.id}`}
346:                     />
347:                   </td>
```

### frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:417
```tsx
414:                 <tr key={a.id} data-testid={`alias-row-${a.id}`}>
415:                   <td style={{ textAlign: "center" }}>
416:                     <input
417:                       type="checkbox"
418:                       checked={aliasSelected.has(a.id)}
419:                       onChange={() => toggleAlias(a.id)}
420:                       aria-label={a.alias_text}
421:                       data-testid={`alias-select-${a.id}`}
422:                     />
423:                   </td>
```

### frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:481
```tsx
478:                   </SelectControl>
479:                 </div>
480:                 <label style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
481:                   <input type="checkbox" checked={ruleForm.is_active} onChange={(e) => setRuleForm({ ...ruleForm, is_active: e.target.checked })} />
482:                   {t(`${f}.isActive`)}
483:                 </label>
484:               </div>
485:               <div className="form-actions">
486:                 <Button type="button" variant="secondary" size="md" onClick={() => setShowRuleForm(false)}>{t("common.cancel")}</Button>
487:                 <Button type="submit" variant="primary" size="md" data-testid="rule-save">{ruleEditId !== null ? t("common.update") : t("common.create")}</Button>
```

### frontend/src/pages/super-admin/components/ConditionDefsMasterPanel.tsx:228
```tsx
225:             </div>
226:             <label style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
227:               <input
228:                 type="checkbox"
229:                 checked={form.is_active}
230:                 onChange={e => setForm({ ...form, is_active: e.target.checked })}
231:               />
232:               {t(`${f}.isActive`)}
233:             </label>
234:           </div>
```

### frontend/src/pages/super-admin/components/ConditionsMasterPanel.tsx:447
```tsx
444: 
445:             {/* 11. 有効にしますか？ */}
446:             <label style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
447:               <input type="checkbox" checked={form.is_active} onChange={e => setForm({ ...form, is_active: e.target.checked })} />
448:               {t(`${f}.isActive`)}
449:             </label>
450: 
451:           </div>
452:         </form>
453:       </Drawer>
```

### frontend/src/pages/super-admin/components/NoteMasterPanel.tsx:302
```tsx
299:             </div>
300:             <label style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
301:               <input
302:                 type="checkbox"
303:                 checked={form.enabled}
304:                 onChange={e => setForm({ ...form, enabled: e.target.checked })}
305:               />
306:               {t(`${f}.enabled`)}
307:             </label>
308:             <div className="form-group" style={{ gridColumn: "1 / -1" }}>
```

### frontend/src/pages/super-admin/components/ProductCategoriesMasterPanel.tsx:282
```tsx
279:             </div>
280:             <label style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
281:               <input
282:                 type="checkbox"
283:                 checked={form.is_active}
284:                 onChange={e => setForm({ ...form, is_active: e.target.checked })}
285:               />
286:               {t(`${f}.isActive`)}
287:             </label>
288:           </div>
```

### frontend/src/pages/super-admin/components/ProductFormatsMasterPanel.tsx:313
```tsx
310:             </div>
311:             <label style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
312:               <input
313:                 type="checkbox"
314:                 checked={form.is_active}
315:                 onChange={e => setForm({ ...form, is_active: e.target.checked })}
316:               />
317:               {t(`${f}.isActive`)}
318:             </label>
319:           </div>
```

### frontend/src/pages/super-admin/components/ProductKindsMasterPanel.tsx:225
```tsx
222:             </div>
223:             <label style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
224:               <input
225:                 type="checkbox"
226:                 checked={form.is_active}
227:                 onChange={e => setForm({ ...form, is_active: e.target.checked })}
228:               />
229:               {t(`${f}.isActive`)}
230:             </label>
231:           </div>
```

### frontend/src/pages/super-admin/components/ProductLinesMasterPanel.tsx:312
```tsx
309:             </div>
310:             <label style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
311:               <input
312:                 type="checkbox"
313:                 checked={form.is_active}
314:                 onChange={e => setForm({ ...form, is_active: e.target.checked })}
315:               />
316:               {t(`${f}.isActive`)}
317:             </label>
318:           </div>
```

### frontend/src/pages/super-admin/components/QuantityUnitsMasterPanel.tsx:243
```tsx
240:             </div>
241:             <label style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
242:               <input
243:                 type="checkbox"
244:                 checked={form.is_active}
245:                 onChange={e => setForm({ ...form, is_active: e.target.checked })}
246:               />
247:               {t(`${f}.isActive`)}
248:             </label>
249:           </div>
```

### frontend/src/pages/super-admin/components/RuleTestPanel.tsx:485
```tsx
482:           )}
483:           <label style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", cursor: "pointer" }}>
484:             <input
485:               type="checkbox"
486:               checked={addEffectExcluded}
487:               onChange={(e) => setAddEffectExcluded(e.target.checked)}
488:             />
489:             <span style={{ fontSize: "var(--font-sm)" }}>{t(`${f}.expectedEffectExcluded`)}</span>
490:           </label>
491:           <TextField
```

### frontend/src/pages/super-admin/components/SupplierMasterPanel.tsx:378
```tsx
375:               />
376:             </div>
377:             <label style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
378:               <input type="checkbox" checked={form.is_active} onChange={e => setForm({ ...form, is_active: e.target.checked })} />
379:               {t(`${f}.isActive`)}
380:             </label>
381:             {editId !== null && (
382:               <div style={{ gridColumn: "1 / -1" }}>
383:                 <HeaderButton variant="secondary" data-testid="supplier-open-routing" onClick={() => { void openRouting(); }}>
384:                   {t("superAdmin.suppliersAdmin.discordRouting")}
```

### frontend/src/pages/super-admin/components/TypeMasterPanel.tsx:270
```tsx
267:             </div>
268:             <label style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
269:               <input
270:                 type="checkbox"
271:                 checked={form.is_active}
272:                 onChange={e => setForm({ ...form, is_active: e.target.checked })}
273:               />
274:               {t(`${f}.isActive`)}
275:             </label>
276:           </div>
```

### frontend/src/pages/super-admin/components/UnitIgnorePhrasesPanel.tsx:170
```tsx
167:             <label style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
168:               {/* ui-allow: チェックボックスの金型が未登録のため（手本 UnitMasterPanel.tsx:332 と同じ書き方） (#4032) */}
169:               <input
170:                 type="checkbox"
171:                 checked={form.is_active}
172:                 onChange={e => setForm({ ...form, is_active: e.target.checked })}
173:               />
174:               {t(`${I18N}.isActive`)}
175:             </label>
176:           </div>
```

### frontend/src/pages/super-admin/components/UnitMasterPanel.tsx:333
```tsx
330:             </div>
331:             <label style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
332:               <input
333:                 type="checkbox"
334:                 checked={form.is_active}
335:                 onChange={e => setForm({ ...form, is_active: e.target.checked })}
336:               />
337:               {t(`${f}.isActive`)}
338:             </label>
339:             {editId !== null && (
```

### frontend/src/pages/super-admin/components/WeightClassesMasterPanel.tsx:255
```tsx
252:             </div>
253:             <label style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
254:               <input
255:                 type="checkbox"
256:                 checked={form.is_active}
257:                 onChange={e => setForm({ ...form, is_active: e.target.checked })}
258:               />
259:               {t(`${f}.isActive`)}
260:             </label>
261:           </div>
```

