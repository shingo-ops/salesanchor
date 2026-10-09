# ay2b-test-refs

base HEAD fb036a2388c2（origin/main, worktree release-frontend-textfield-ay2b）。走査: __tests__ / *.test.* / *.spec.* の ts/tsx と tests-e2e・e2e・.storybook・tests/ 配下の js/ts（計 139 ファイル）。
手法: 文字列検索。限界: 動的に組み立てた文字列・コンポーネント経由の間接参照・getByPlaceholderText/getByLabelText/getByRole 等の文言参照は検出対象外（この調査は「クラス名または input 要素セレクタで対象 input を指す参照」が主題）。

## .form-group / form-group (class selector or className in tests): 2 件

- frontend/src/components/LeadFormButtonMigration.test.tsx:159  `if (action === 'clear') { const group = input.closest('.form-group'); if (!group) throw new Error('Missing group'); fireEvent.click(within(group as HTMLElement).getByRole('button',`
- frontend/tests-e2e/super-admin-masters.spec.ts:124  `const textInputs = dialog.locator(".form-group input[type='text'], .form-group input:not([type])");`

## login-card: 0 件

## input element selector (querySelector/locator/closest/$ with input): 64 件

- frontend/src/components/AccountCompanySaveButtonMigration.test.tsx:61  `const field = (key: string) => screen.getByText(tr(key), { selector: 'label' }).parentElement!.querySelector('input,textarea,select') as HTMLInputElement;`
- frontend/src/components/CommerceNavigationButtonMigration.test.tsx:128  `await screen.findByTestId('product-edit-save'); fireEvent.change(document.querySelector('input[required]')!, { target: { value: 'Product' } });`
- frontend/src/components/CommerceSubmitButtonMigration.test.tsx:114  `fireEvent.change(screen.getByText(String(instance.t('quotes.tax'))).parentElement!.querySelector('input')!, { target: { value: '7' } }); fireEvent.change(screen.getByText(String(in`
- frontend/src/components/OrderLeadButtonMigration.test.tsx:62  `fireEvent.click(screen.getByRole('button', { name: tr('orders.newOrder') })); const reset = screen.getByRole('dialog', { name: tr('orders.newOrder') }); expect((reset.querySelector`
- frontend/src/components/OrderLeadButtonMigration.test.tsx:69  `fireEvent.change(dialog.querySelector('input[required]')!, { target: { value: 'ORD-EDIT' } }); fireEvent.click(within(dialog).getByRole('button', { name: tr('common.update') }));`
- frontend/src/components/OrderLeadButtonMigration.test.tsx:72  `const reopened = screen.getByRole('dialog', { name: tr('orders.editOrder') }); fireEvent.change(reopened.querySelector('input[required]')!, { target: { value: 'Cancel edit' } }); f`
- frontend/src/components/OrderLeadButtonMigration.test.tsx:78  `fireEvent.change(dialog.querySelector('input[required]')!, { target: { value: 'Guard order' } }); fireEvent.submit(dialog.querySelector('form')!); expect(await screen.findByText(tr`
- frontend/src/components/OrderLeadButtonMigration.test.tsx:91  `fireEvent.change(selects[0], { target: { value: '4' } }); await waitFor(() => expect(mock.get.mock.calls.filter(c => c[0] === '/contacts?company_id=4&per_page=100').length).toBeGre`
- frontend/src/components/OrderLeadButtonMigration.test.tsx:100  `fireEvent.click(screen.getByRole('button', { name: tr('common.edit') })); dialog = screen.getByRole('dialog', { name: tr('orders.editOrder') }); fireEvent.change(dialog.querySelect`
- frontend/src/components/OrderLeadButtonMigration.test.tsx:108  `fireEvent.change(dialog.querySelector('input[required]')!, { target: { value: 'Pending retained' } }); fireEvent.click(within(dialog).getByRole('button', { name: mode === 'edit' ? `
- frontend/src/components/OrderLeadButtonMigration.test.tsx:109  `if (reject) { pending.reject(new Error('Late failure')); await screen.findByText('Late failure'); fireEvent.click(screen.getByRole('button', { name: mode === 'edit' ? tr('common.ed`
- frontend/src/components/OrderLeadButtonMigration.test.tsx:110  `else { pending.resolve({}); await waitFor(() => expect(mode === 'edit' ? mock.patch : mock.post).toHaveBeenCalledTimes(1)); fireEvent.click(screen.getByRole('button', { name: mode `
- frontend/src/components/OrderLeadButtonMigration.test.tsx:116  `fireEvent.change(dialog.querySelector('input[required]')!, { target: { value: ' Deal title ' } });`
- frontend/src/components/OrderLeadButtonMigration.test.tsx:126  `fireEvent.click(screen.getByRole('button', { name: tr('leads.convert') })); const reset = screen.getByRole('dialog', { name: tr('leads.convertLead') }); expect((reset.querySelector`
- frontend/src/components/OrderLeadButtonMigration.test.tsx:134  `const selects = dialog.querySelectorAll<HTMLSelectElement>('select'); fireEvent.change(selects[0], { target: { value: '4' } }); await waitFor(() => expect(mock.get).toHaveBeenCalle`
- frontend/src/components/OrderLeadButtonMigration.test.tsx:135  `let save = within(dialog).getByRole('button', { name: tr('leads.convert') }) as HTMLButtonElement; fireEvent.click(save); expect(await screen.findByText('Convert failure')).toBeTru`
- frontend/src/components/OrderLeadButtonMigration.test.tsx:140  `fireEvent.click(within(dialog).getByRole('button', { name: tr('leads.convert') })); expect(mock.post).not.toHaveBeenCalled(); fireEvent.change(dialog.querySelector('input[required]`
- frontend/src/components/OrderLeadButtonMigration.test.tsx:144  `const pending = deferred(); mock.post.mockReturnValue(pending.promise); render(wrap(<LeadsPage />)); await screen.findByText('Fixture Lead'); fireEvent.click(screen.getByRole('butt`
- frontend/src/components/OrderLeadButtonMigration.test.tsx:148  `const pending = deferred(); mock.post.mockReturnValue(pending.promise); render(wrap(<LeadsPage />)); await screen.findByText('Fixture Lead'); const before = mock.get.mock.calls.fil`
- frontend/src/components/OrderLeadButtonMigration.test.tsx:150  `else { pending.resolve({}); await waitFor(() => expect(mock.get.mock.calls.filter(c => c[0] === '/leads')).toHaveLength(before + 1)); fireEvent.click(screen.getByRole('button', { n`
- frontend/src/components/PurchaseAdminEditorButtonMigration.test.tsx:67  `expect((dialog.querySelector('select') as HTMLSelectElement).value).toBe(''); expect((dialog.querySelector('input[readonly]') as HTMLInputElement).value).toBe(''); fireEvent.click(`
- frontend/src/components/RoleKnowledgeButtonMigration.test.tsx:43  `fireEvent.change(dialog.querySelector('input[required]')!, { target: { value: name } });`
- frontend/src/components/RoleKnowledgeButtonMigration.test.tsx:75  `({ dialog } = openRole()); fireEvent.change(dialog.querySelector('input[required]')!, { target: { value: 'Retained' } });`
- frontend/src/components/RoleKnowledgeButtonMigration.test.tsx:137  `fireEvent.change(dialog.querySelector('input[type="number"]')!, { target: { value: '77' } }); fireEvent.click(dialog.querySelector('input[type="checkbox"]')!); mock.put.mockResolve`
- frontend/src/components/RoleKnowledgeButtonMigration.test.tsx:139  `dialog = open(); expect(dialog.querySelector<HTMLInputElement>('input[type="number"]')!.value).toBe(''); fireEvent.change(dialog.querySelector('input[type="number"]')!, { target: {`
- frontend/src/components/RoleKnowledgeButtonMigration.test.tsx:140  `fireEvent.change(dialog.querySelector('input[type="number"]')!, { target: { value: '77' } }); mock.put.mockRejectedValueOnce(new Error('Assignment failure')).mockResolvedValueOnce(`
- frontend/src/components/RoleKnowledgeButtonMigration.test.tsx:141  `dialog = open(); fireEvent.change(dialog.querySelector('input[type="number"]')!, { target: { value: '77' } });`
- frontend/src/components/RoleKnowledgeButtonMigration.test.tsx:143  `dialog = open(); fireEvent.change(dialog.querySelector('input[type="number"]')!, { target: { value: '99' } });`
- frontend/src/components/RoleKnowledgeButtonMigration.test.tsx:145  `fireEvent.change(dialog.querySelector('input[type="number"]')!, { target: { value: '99' } }); fireEvent.keyDown(document, { key: 'Escape' });`
- frontend/src/components/RoleKnowledgeButtonMigration.test.tsx:147  `fireEvent.change(dialog.querySelector('input[type="number"]')!, { target: { value: '77' } });`
- frontend/src/components/TextField.test.tsx:105  `const cls = () => container.querySelector('input')?.className;`
- frontend/src/components/TextField.test.tsx:121  `expect(ref.current).toBe(container.querySelector('input'));`
- frontend/src/components/TextField.test.tsx:129  `expect(ref).toHaveBeenCalledWith(container.querySelector('input'));`
- frontend/src/components/TextField.test.tsx:152  `const el = container.querySelector('input') as HTMLInputElement;`
- frontend/src/components/TextField.test.tsx:179  `const el = container.querySelector('input') as HTMLInputElement;`
- frontend/src/components/TextField.test.tsx:194  `const el = container.querySelector('input') as HTMLInputElement;`
- frontend/src/components/TextField.test.tsx:206  `expect(container.querySelector('input')?.className).toBe('comp-field__input comp-input--${variant} x-layout');`
- frontend/src/components/TextField.test.tsx:211  `const cls = () => container.querySelector('input')?.className;`
- frontend/src/components/TextField.test.tsx:235  `const el = container.querySelector('input') as HTMLInputElement;`
- frontend/tests-e2e/goal-setting-advisor.spec.ts:103  `await expect(page.getByTestId("goal-advisor-weekly-leads").locator("input")).toHaveValue("40");`
- frontend/tests-e2e/goal-setting-advisor.spec.ts:104  `await expect(page.getByTestId("goal-advisor-weekly-deals").locator("input")).toHaveValue("16");`
- frontend/tests-e2e/goal-setting-advisor.spec.ts:105  `await expect(page.getByTestId("goal-advisor-weekly-wins").locator("input")).toHaveValue("8");`
- frontend/tests-e2e/goal-setting-advisor.spec.ts:108  `await page.getByTestId("goal-advisor-weekly-leads").locator("input").fill("44");`
- frontend/tests-e2e/goal-setting-advisor.spec.ts:109  `await expect(page.getByTestId("goal-advisor-weekly-leads").locator("input")).toHaveValue("44");`
- frontend/tests-e2e/goal-setting-advisor.spec.ts:182  `await expect(page.getByTestId("goal-advisor-weekly-leads").locator("input")).toHaveValue("");`
- frontend/tests-e2e/goal-setting-advisor.spec.ts:183  `await expect(page.getByTestId("goal-advisor-weekly-deals").locator("input")).toHaveValue("");`
- frontend/tests-e2e/goal-setting-advisor.spec.ts:184  `await expect(page.getByTestId("goal-advisor-weekly-wins").locator("input")).toHaveValue("");`
- frontend/tests-e2e/karte-visual-gate.spec.ts:331  `const urlInputs = page.locator('.right-panel-tab-content input[type="url"]');`
- frontend/tests-e2e/register-form-ux.spec.ts:97  `await contactFieldset.locator("label", { hasText: "担当者名" }).locator("input").fill("田中太郎");`
- frontend/tests-e2e/register-form-ux.spec.ts:107  `await contactFieldset.locator("label", { hasText: "担当者名" }).locator("input").fill("田中太郎");`
- frontend/tests-e2e/register-form-ux.spec.ts:108  `await contactFieldset.locator("input[type=email]").fill("tanaka@example.com");`
- frontend/tests-e2e/register-form-ux.spec.ts:116  `await contactFieldset.locator("label", { hasText: "担当者名" }).locator("input").fill("山田花子");`
- frontend/tests-e2e/register-form-ux.spec.ts:117  `await contactFieldset.locator("input[type=tel]").fill("09012345678");`
- frontend/tests-e2e/register-form-ux.spec.ts:126  `await contactFieldset.locator("label", { hasText: "担当者名" }).locator("input").fill("テスト");`
- frontend/tests-e2e/register-form-ux.spec.ts:127  `await contactFieldset.locator("input[type=email]").fill("t@example.com");`
- frontend/tests-e2e/register-form-ux.spec.ts:141  `await contactFieldset.locator("label", { hasText: "担当者名" }).locator("input").fill("テスト");`
- frontend/tests-e2e/register-form-ux.spec.ts:142  `await contactFieldset.locator("input[type=email]").fill("t@example.com");`
- frontend/tests-e2e/super-admin-masters.spec.ts:124  `const textInputs = dialog.locator(".form-group input[type='text'], .form-group input:not([type])");`
- frontend/tests-e2e/tcg-import-workflow.spec.ts:255  `const hours = uploadDetails.locator('input[type="number"]');`
- frontend/tests-e2e/tcg-product-import.spec.ts:50  `await page.locator('input[type="file"]').setInputFiles({ name: "update.csv", mimeType: "text/csv", buffer: raw });`
- …他 4 件

## input[type=: 22 件

- frontend/src/components/OrderLeadButtonMigration.test.tsx:121  `const number = dialog.querySelector<HTMLInputElement>('input[type="number"]')!; fireEvent.change(number, { target: { value: '500' } });`
- frontend/src/components/RoleKnowledgeButtonMigration.test.tsx:137  `fireEvent.change(dialog.querySelector('input[type="number"]')!, { target: { value: '77' } }); fireEvent.click(dialog.querySelector('input[type="checkbox"]')!); mock.put.mockResolve`
- frontend/src/components/RoleKnowledgeButtonMigration.test.tsx:139  `dialog = open(); expect(dialog.querySelector<HTMLInputElement>('input[type="number"]')!.value).toBe(''); fireEvent.change(dialog.querySelector('input[type="number"]')!, { target: {`
- frontend/src/components/RoleKnowledgeButtonMigration.test.tsx:140  `fireEvent.change(dialog.querySelector('input[type="number"]')!, { target: { value: '77' } }); mock.put.mockRejectedValueOnce(new Error('Assignment failure')).mockResolvedValueOnce(`
- frontend/src/components/RoleKnowledgeButtonMigration.test.tsx:141  `dialog = open(); fireEvent.change(dialog.querySelector('input[type="number"]')!, { target: { value: '77' } });`
- frontend/src/components/RoleKnowledgeButtonMigration.test.tsx:143  `dialog = open(); fireEvent.change(dialog.querySelector('input[type="number"]')!, { target: { value: '99' } });`
- frontend/src/components/RoleKnowledgeButtonMigration.test.tsx:144  `fireEvent.click(within(dialog).getByRole('button', { name: tr('common.close') })); dialog = open(); expect(dialog.querySelector<HTMLInputElement>('input[type="number"]')!.value).to`
- frontend/src/components/RoleKnowledgeButtonMigration.test.tsx:145  `fireEvent.change(dialog.querySelector('input[type="number"]')!, { target: { value: '99' } }); fireEvent.keyDown(document, { key: 'Escape' });`
- frontend/src/components/RoleKnowledgeButtonMigration.test.tsx:146  `dialog = open(); expect(dialog.querySelector<HTMLInputElement>('input[type="number"]')!.value).toBe('');`
- frontend/src/components/RoleKnowledgeButtonMigration.test.tsx:147  `fireEvent.change(dialog.querySelector('input[type="number"]')!, { target: { value: '77' } });`
- frontend/tests-e2e/karte-visual-gate.spec.ts:330  `// No input[type="url"] should exist in the tab content`
- frontend/tests-e2e/karte-visual-gate.spec.ts:331  `const urlInputs = page.locator('.right-panel-tab-content input[type="url"]');`
- frontend/tests-e2e/register-form-ux.spec.ts:108  `await contactFieldset.locator("input[type=email]").fill("tanaka@example.com");`
- frontend/tests-e2e/register-form-ux.spec.ts:117  `await contactFieldset.locator("input[type=tel]").fill("09012345678");`
- frontend/tests-e2e/register-form-ux.spec.ts:127  `await contactFieldset.locator("input[type=email]").fill("t@example.com");`
- frontend/tests-e2e/register-form-ux.spec.ts:142  `await contactFieldset.locator("input[type=email]").fill("t@example.com");`
- frontend/tests-e2e/super-admin-masters.spec.ts:124  `const textInputs = dialog.locator(".form-group input[type='text'], .form-group input:not([type])");`
- frontend/tests-e2e/tcg-import-workflow.spec.ts:255  `const hours = uploadDetails.locator('input[type="number"]');`
- frontend/tests-e2e/tcg-product-import.spec.ts:50  `await page.locator('input[type="file"]').setInputFiles({ name: "update.csv", mimeType: "text/csv", buffer: raw });`
- frontend/tests-e2e/tcg-product-import.spec.ts:81  `await page.locator('input[type="file"]').setInputFiles({ name: "products.csv", mimeType: "text/csv", buffer: Buffer.from(csv) });`
- frontend/tests-e2e/tcg-product-import.spec.ts:165  `await expect(page.locator('input[type="file"]')).toHaveCount(0);`
- frontend/tests-e2e/tcg-product-import.spec.ts:219  `await page.locator('input[type="file"]').setInputFiles({`

## comp-field__input: 13 件

- frontend/src/components/TextField.test.tsx:10  `const INPUT = '<input id="t" class="comp-field__input">';`
- frontend/src/components/TextField.test.tsx:23  `'<input id="t" class="comp-field__input" required=""></div>',`
- frontend/src/components/TextField.test.tsx:78  `'<input id="t" class="comp-field__input" type="email" placeholder="ph" maxlength="10" disabled="" aria-label="al" data-testid="tid" value="v"></div>',`
- frontend/src/components/TextField.test.tsx:86  `'<input id="t" class="comp-field__input" type="number" min="1" max="9" step="2" readonly=""></div>',`
- frontend/src/components/TextField.test.tsx:106  `expect(cls()).toBe('comp-field__input');`
- frontend/src/components/TextField.test.tsx:108  `expect(cls()).toBe('comp-field__input comp-field__input--sm');`
- frontend/src/components/TextField.test.tsx:110  `expect(cls()).toBe('comp-field__input comp-field__input--lg');`
- frontend/src/components/TextField.test.tsx:112  `expect(cls()).toBe('comp-field__input x');`
- frontend/src/components/TextField.test.tsx:114  `expect(cls()).toBe('comp-field__input comp-field__input--sm x');`
- frontend/src/components/TextField.test.tsx:206  `expect(container.querySelector('input')?.className).toBe('comp-field__input comp-input--${variant} x-layout');`
- frontend/src/components/TextField.test.tsx:212  `expect(cls()).toBe('comp-field__input comp-field__input--sm');`
- frontend/src/components/TextField.test.tsx:214  `expect(cls()).toBe('comp-field__input');`
- frontend/src/components/TextField.test.tsx:219  `expect(container.innerHTML).toBe('<input id="v" class="comp-field__input comp-input--karte">');`

## .product-edit-form: 2 件

- frontend/src/components/CommerceSubmitButtonMigration.test.tsx:42  `const form = screen.getByTestId('product-edit-form');`
- frontend/src/components/CommerceSubmitButtonMigration.test.tsx:148  `const form = screen.getByTestId('product-edit-form'); const controls = Array.from(form.querySelectorAll<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>('input, select, `

## getComputedStyle / toHaveStyle (style assertions): 25 件

- frontend/tests-e2e/analysis-rules-line-guide.spec.ts:119  `await expect(page.locator("html")).toHaveClass(configuration.theme === "dark" ? /force-dark/ : /^(?!.*force-dark)/);`
- frontend/tests-e2e/desktop-shell.spec.ts:75  `await expect(sidebar).toHaveClass(/sidebar-expanded/, { timeout: 3_000 });`
- frontend/tests-e2e/funnel-dashboard.spec.ts:155  `await expect(mgmtTab).toHaveClass(/active/);`
- frontend/tests-e2e/funnel-dashboard.spec.ts:160  `await expect(playerTab).toHaveClass(/active/);`
- frontend/tests-e2e/karte-visual-gate.spec.ts:296  `await expect(dealTab).toHaveClass(/active/);`
- frontend/tests-e2e/karte-visual-gate.spec.ts:303  `await expect(dealTab).toHaveClass(/active/);`
- frontend/tests-e2e/karte-visual-gate.spec.ts:310  `await expect(companyTab).toHaveClass(/active/);`
- frontend/tests-e2e/karte-visual-gate.spec.ts:317  `await expect(companyTab).toHaveClass(/active/);`
- frontend/tests-e2e/lead-channel-control.spec.ts:109  `await expect(page.locator("html")).toHaveClass(/force-dark/);`
- frontend/tests-e2e/lead-country-control.spec.ts:100  `await expect(page.locator("html")).toHaveClass(/force-dark/);`
- frontend/tests-e2e/mobile-shell.spec.ts:289  `(el) => getComputedStyle(el).textDecorationLine,`
- frontend/tests-e2e/mobile-shell.spec.ts:299  `(el) => getComputedStyle(el).display,`
- frontend/tests-e2e/product-edit-tcg-type.spec.ts:113  `await expect(page.locator("html")).toHaveClass(/force-dark/);`
- frontend/tests-e2e/scene1-dashboard.spec.ts:470  `await expect(page.locator("html")).toHaveClass(/force-dark/);`
- frontend/tests-e2e/scene3-receive-messenger.spec.ts:114  `await expect(unreadBtn).toHaveClass(/active/);`
- frontend/tests-e2e/scene3-receive-messenger.spec.ts:118  `await expect(unreadBtn).not.toHaveClass(/active/);`
- frontend/tests-e2e/send-guard-phase-a.spec.ts:70  `await expect(btn).toHaveClass(/active/);`
- frontend/tests-e2e/tcg-import-workflow.spec.ts:229  `await expect(page.locator("html")).toHaveClass(/force-dark/);`
- frontend/tests-e2e/tcg-import-workflow.spec.ts:307  `const color = getComputedStyle(element).color;`
- frontend/tests-e2e/tcg-import-workflow.spec.ts:308  `const primary = getComputedStyle(reference).color;`
- frontend/tests-e2e/tcg-import-workflow.spec.ts:314  `const background = getComputedStyle(element).backgroundColor;`
- frontend/tests-e2e/tcg-import-workflow.spec.ts:338  `await expect(darkPage.locator("html")).toHaveClass(/force-dark/);`
- frontend/tests-e2e/tcg-import-workflow.spec.ts:343  `return { color: getComputedStyle(element).color, primary: getComputedStyle(reference).color };`
- frontend/tests-e2e/tcg-product-detail.spec.ts:63  `return { ja: parseFloat(getComputedStyle(ja).fontSize), en: parseFloat(getComputedStyle(en).fontSize), below: en.getBoundingClientRect().top >= ja.getBoundingClientRect().bottom };`
- frontend/tests-e2e/visual-language/inbox-baseline.spec.ts:86  `const style = window.getComputedStyle(el);`

## data-testid / id リテラルでの一致（対象 input が持つ識別子 44 種）: 14 件

- frontend/tests-e2e/po-pdf-mail.spec.ts:169 [tp-company-name] → pages/admin/TenantProfilePage.tsx:145(target), pages/admin/TenantProfilePage.tsx:145(target)  `await expect(page.getByTestId("tp-company-name")).toHaveValue("QA テナント株式会社");`
- frontend/tests-e2e/po-pdf-mail.spec.ts:172 [tp-phone] → pages/admin/TenantProfilePage.tsx:183(target), pages/admin/TenantProfilePage.tsx:183(target)  `await page.getByTestId("tp-phone").fill("06-9999-0000");`
- frontend/src/components/CommerceSubmitButtonMigration.test.tsx:134 [product-edit-name-ja] → pages/products/ProductEditPage.tsx:215(product-edit(hold))  `await act(async () => first.reject(new Error('Product save failed'))); expect(await screen.findByText('Product save failed')).toBeTruthy(); expect((screen.getBy`
- frontend/src/components/CommerceSubmitButtonMigration.test.tsx:147 [product-edit-name-ja] → pages/products/ProductEditPage.tsx:215(product-edit(hold))  `render(routed(<ProductEditPage />, '/admin/products/:id/edit', ['/before', '/admin/products/9/edit'])); await waitFor(() => expect((screen.getByTestId('product-`
- frontend/src/components/CommerceSubmitButtonMigration.test.tsx:150 [product-edit-name-ja] → pages/products/ProductEditPage.tsx:215(product-edit(hold))  `await act(async () => first.reject(new Error('Edit save failed'))); expect(await screen.findByText('Edit save failed')).toBeTruthy(); expect((screen.getByTestId`
- frontend/src/components/CommerceSubmitButtonMigration.test.tsx:113 [shipping-fee-input] → pages/quote-create/QuoteCreatePage.tsx:268(target)  `fireEvent.change(screen.getByTestId('shipping-fee-input'), { target: { value: '3' } });`
- frontend/src/components/RoleKnowledgeButtonMigration.test.tsx:59 [alias-text-input] → pages/super-admin/KnowledgeAliasesTab.tsx:516(target)  `fireEvent.change(screen.getByTestId('alias-supplier-select'), { target: { value: '7' } }); fireEvent.change(screen.getByTestId('alias-text-input'), { target: { `
- frontend/src/components/RoleKnowledgeButtonMigration.test.tsx:169 [alias-text-input] → pages/super-admin/KnowledgeAliasesTab.tsx:516(target)  `({ dialog } = openKnowledge('alias')); fireEvent.change(screen.getByTestId('alias-text-input'), { target: { value: 'alias without supplier' } }); fireEvent.subm`
- frontend/src/components/RoleKnowledgeButtonMigration.test.tsx:179 [alias-text-input] → pages/super-admin/KnowledgeAliasesTab.tsx:516(target)  `expect(kind === 'rule' ? dialog.querySelector<HTMLInputElement>('input')!.value : (screen.getByTestId('alias-text-input') as HTMLInputElement).value).toBe(''); `
- frontend/src/components/PurchaseAdminEditorButtonMigration.test.tsx:91 [llm-budget-input-monthly-budget] → pages/super-admin/LLMBudgetTab.tsx:187(target)  `render(wrap(<LLMBudgetTab />)); fireEvent.click(await screen.findByTestId('llm-budget-edit-3')); const form = screen.getByTestId('llm-budget-edit-form'); expect`
- frontend/tests-e2e/super-admin-llm-budget.spec.ts:172 [llm-budget-input-monthly-budget] → pages/super-admin/LLMBudgetTab.tsx:187(target)  `const budgetInput = page.getByTestId("llm-budget-input-monthly-budget");`
- frontend/src/components/PurchaseAdminEditorButtonMigration.test.tsx:91 [llm-budget-input-hard-stop] → pages/super-admin/LLMBudgetTab.tsx:202(non-text)  `render(wrap(<LLMBudgetTab />)); fireEvent.click(await screen.findByTestId('llm-budget-edit-3')); const form = screen.getByTestId('llm-budget-edit-form'); expect`
- frontend/tests-e2e/super-admin-llm-budget.spec.ts:175 [llm-budget-input-hard-stop] → pages/super-admin/LLMBudgetTab.tsx:202(non-text)  `await page.getByTestId("llm-budget-input-hard-stop").uncheck();`
- frontend/tests-e2e/super-admin-llm-budget.spec.ts:176 [llm-budget-input-notify-admin] → pages/super-admin/LLMBudgetTab.tsx:215(non-text)  `await page.getByTestId("llm-budget-input-notify-admin").uncheck();`
