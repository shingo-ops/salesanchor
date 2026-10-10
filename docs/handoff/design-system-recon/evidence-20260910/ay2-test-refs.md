# ay2-test-refs

base HEAD 08f59418c772fab0bed6137e818d5e87de5c91f2。走査対象テストファイル 127 本（`git ls-files` で __tests__ / *.test.* / *.spec.* の ts/tsx。frontend/src, frontend/tests-e2e, tests/qa-smoke）。

手法: (1) 対象 text-like input 360 件が持つ識別子（data-testid / id / className / placeholder・aria-label のリテラルと t("key") の ja/en 解決文言）をテストに文字列検索（380 識別子）。(2) セレクタ種別（input 要素セレクタ・getByPlaceholderText 等）の全体件数。(3) input を持つコンポーネント名を import/言及するテスト。

限界: 動的に組み立てた文字列・コンポーネントを介した間接参照は検出されない。文字列一致は「候補」であり、その input を指すとは限らない（例: 文言が同じ別要素）。

## A. 識別子一致（候補）

一致したテストファイル: 20 本 / 一致行 74

### frontend/src/components/AdminMasterSaveButtonMigration.test.tsx（8 行）

- L40 [placeholder-key: `superAdmin.dex.fields.nameJa`] → input pages/super-admin/DexTab.tsx:298(G02)
  - `render(wrap(<DexTab />)); await screen.findAllByText('Pikachu'); fireEvent.click(screen.getAllByRole('button', { name: tr('common.edit') })[0]); const name = screen.getByPlaceholderText(tr('superAdmin.dex.fields.nameJa')) as HTMLInputElement; fireEvent.change(`
- L44 [placeholder-key: `superAdmin.dex.fields.nameJa`] → input pages/super-admin/DexTab.tsx:298(G02)
  - `render(wrap(<DexTab />)); await screen.findAllByText('Pikachu'); fireEvent.click(screen.getAllByRole('button', { name: tr('common.edit') })[0]); const first = deferred(), second = deferred(); mock.patch.mockReturnValueOnce(first.promise).mockReturnValueOnce(se`
- L49 [placeholder-key: `superAdmin.dex.fields.era`] → input pages/super-admin/DexTab.tsx:315(G02)
  - `render(wrap(<DexTab />)); await screen.findAllByText('Pikachu'); fireEvent.change(screen.getByRole('combobox'), { target: { value: 'trainer' } }); await screen.findAllByText('Trainer'); fireEvent.click(screen.getAllByRole('button', { name: tr('common.edit') })`
- L63 [placeholder-key: `superAdmin.tcg.fields.nameJa`] → input pages/super-admin/TcgSeriesTab.tsx:230(G02), pages/super-admin/TcgSeriesTab.tsx:317(G02)
  - `render(wrap(<TcgSeriesTab />)); await screen.findByText('Series fixture'); const newSeries = screen.getByRole('button', { name: tr('superAdmin.tcg.newSeries') }); fireEvent.click(newSeries); expect(mock.post).not.toHaveBeenCalled(); fireEvent.change(screen.get`
- L54 [placeholder-key: `superAdmin.tcg.fields.seriesCode`] → input pages/super-admin/TcgSeriesTab.tsx:311(G02)
  - `expect(typeInputs[0].value).toBe(''); expect(typeInputs[1].value).toBe(''); fireEvent.click(screen.getByRole('button', { name: tr('common.edit') })); const code = screen.getByPlaceholderText(tr('superAdmin.tcg.fields.seriesCode')) as HTMLInputElement; fireEven`
- L58 [placeholder-key: `superAdmin.tcg.fields.seriesCode`] → input pages/super-admin/TcgSeriesTab.tsx:311(G02)
  - `render(wrap(<TcgSeriesTab />)); await screen.findByText('Series fixture'); fireEvent.click(screen.getByRole('button', { name: tr('common.edit') })); const code = screen.getByPlaceholderText(tr('superAdmin.tcg.fields.seriesCode')) as HTMLInputElement; fireEvent`
- L59 [placeholder-key: `superAdmin.tcg.fields.seriesCode`] → input pages/super-admin/TcgSeriesTab.tsx:311(G02)
  - `const first = deferred(), second = deferred(); mock.patch.mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise); const save = screen.getByRole('button', { name: tr('common.update') }) as HTMLButtonElement; const reads = mock.get.mock.calls.fil`
- L63 [placeholder-key: `superAdmin.tcg.fields.seriesCode`] → input pages/super-admin/TcgSeriesTab.tsx:311(G02)
  - `render(wrap(<TcgSeriesTab />)); await screen.findByText('Series fixture'); const newSeries = screen.getByRole('button', { name: tr('superAdmin.tcg.newSeries') }); fireEvent.click(newSeries); expect(mock.post).not.toHaveBeenCalled(); fireEvent.change(screen.get`

### frontend/src/components/PurchaseAdminEditorButtonMigration.test.tsx（7 行）

- L79 [placeholder-key: `common.search`] → input pages/inbox/InboxConversationList.tsx:62(G32), pages/orders/OrdersFilterBar.tsx:32(G12), pages/products/ProductsPage.tsx:219(G14), pages/super-admin/DexTab.tsx:200(G02) …+2
  - `const search = screen.getByPlaceholderText(tr('common.search')); fireEvent.change(search, { target: { value: 'target' } }); const before = mock.get.mock.calls.length; fireEvent.click(screen.getByRole('button', { name: tr('common.search') })); await waitFor(() `
- L84 [placeholder-key: `common.search`] → input pages/inbox/InboxConversationList.tsx:62(G32), pages/orders/OrdersFilterBar.tsx:32(G12), pages/products/ProductsPage.tsx:219(G14), pages/super-admin/DexTab.tsx:200(G02) …+2
  - `render(wrap(<DexTab />)); await screen.findAllByText('Pikachu'); const search = screen.getByPlaceholderText(tr('common.search')); fireEvent.change(search, { target: { value: 'retry' } });`
- L86 [placeholder-key: `common.search`] → input pages/inbox/InboxConversationList.tsx:62(G32), pages/orders/OrdersFilterBar.tsx:32(G12), pages/products/ProductsPage.tsx:219(G14), pages/super-admin/DexTab.tsx:200(G02) …+2
  - `mock.get.mockRejectedValueOnce(new Error('Dex failure')).mockResolvedValueOnce([retriedDex]); const button = screen.getByRole('button', { name: tr('common.search') }); fireEvent.click(button); expect(await screen.findByText('Dex failure')).toBeTruthy(); fireEv`
- L78 [placeholder-key: `superAdmin.dex.fields.nameJa`] → input pages/super-admin/DexTab.tsx:298(G02)
  - `const name = screen.getByPlaceholderText(tr('superAdmin.dex.fields.nameJa')) as HTMLInputElement; expect(name.value).toBe('Pikachu'); fireEvent.click(screen.getByRole('button', { name: tr('common.cancel') })); expect(screen.queryByPlaceholderText(tr('superAdmi`
- L91 [data-testid: `llm-budget-input-monthly-budget`] → input pages/super-admin/LLMBudgetTab.tsx:187(G02)
  - `render(wrap(<LLMBudgetTab />)); fireEvent.click(await screen.findByTestId('llm-budget-edit-3')); const form = screen.getByTestId('llm-budget-edit-form'); expect((within(form).getByTestId('llm-budget-input-monthly-budget') as HTMLInputElement).value).toBe('10.0`
- L96 [placeholder-key: `superAdmin.tcg.fields.nameJa`] → input pages/super-admin/TcgSeriesTab.tsx:230(G02), pages/super-admin/TcgSeriesTab.tsx:317(G02)
  - `fireEvent.click(screen.getByRole('button', { name: tr('common.edit') })); expect((screen.getByPlaceholderText(tr('superAdmin.tcg.fields.seriesCode')) as HTMLInputElement).value).toBe('S5'); expect((screen.getByPlaceholderText(tr('superAdmin.tcg.fields.nameJa')`
- L96 [placeholder-key: `superAdmin.tcg.fields.seriesCode`] → input pages/super-admin/TcgSeriesTab.tsx:311(G02)
  - `fireEvent.click(screen.getByRole('button', { name: tr('common.edit') })); expect((screen.getByPlaceholderText(tr('superAdmin.tcg.fields.seriesCode')) as HTMLInputElement).value).toBe('S5'); expect((screen.getByPlaceholderText(tr('superAdmin.tcg.fields.nameJa')`

### frontend/tests-e2e/orders-list.spec.ts（7 行）

- L153 [placeholder-key: `common.search`] → input pages/inbox/InboxConversationList.tsx:62(G32), pages/orders/OrdersFilterBar.tsx:32(G12), pages/products/ProductsPage.tsx:219(G14), pages/super-admin/DexTab.tsx:200(G02) …+2
  - `// testid で指定する。placeholder は t("common.search") = "検索"）`
- L154 [data-testid: `orders-search-input`] → input pages/orders/OrdersFilterBar.tsx:32(G12)
  - `const searchBox = page.getByTestId("orders-search-input");`
- L222 [data-testid: `orders-search-input`] → input pages/orders/OrdersFilterBar.tsx:32(G12)
  - `const searchBox = page.getByTestId("orders-search-input");`
- L148 [aria-label-ja: `受注管理`] → input pages/orders/OrdersFilterBar.tsx:32(G12)
  - `await expect(page.getByRole("heading", { name: /受注管理/ })).toBeVisible({`
- L192 [aria-label-ja: `受注管理`] → input pages/orders/OrdersFilterBar.tsx:32(G12)
  - `await expect(page.getByRole("heading", { name: /受注管理/ })).toBeVisible({`
- L214 [aria-label-ja: `受注管理`] → input pages/orders/OrdersFilterBar.tsx:32(G12)
  - `await expect(page.getByRole("heading", { name: /受注管理/ })).toBeVisible({`
- L276 [aria-label-ja: `受注管理`] → input pages/orders/OrdersFilterBar.tsx:32(G12)
  - `await expect(page.getByRole("heading", { name: /受注管理/ })).toBeVisible({`

### frontend/src/components/MasterSearchButtonMigration.test.tsx（6 行）

- L69 [placeholder-key: `superAdmin.attrMasters.searchPlaceholder`] → input components/master-list-editor/MasterListEditor.tsx:135(G14)
  - `const field = screen.getByPlaceholderText(tr('superAdmin.attrMasters.searchPlaceholder')) as HTMLInputElement;`
- L85 [placeholder-key/aria-label-key: `superAdmin.attrMasters.col.labelJa`] → input components/master-list-editor/MasterListEditor.tsx:157(G02)
  - `const ja = screen.getByLabelText(tr('superAdmin.attrMasters.col.labelJa')) as HTMLInputElement;`
- L104 [placeholder-key/aria-label-key: `superAdmin.attrMasters.col.labelJa`] → input components/master-list-editor/MasterListEditor.tsx:157(G02)
  - `const ja = screen.getByLabelText(tr('superAdmin.attrMasters.col.labelJa')) as HTMLInputElement;`
- L116 [placeholder-key/aria-label-key: `superAdmin.attrMasters.col.labelJa`] → input components/master-list-editor/MasterListEditor.tsx:157(G02)
  - `const ja = screen.getByLabelText(tr('superAdmin.attrMasters.col.labelJa')) as HTMLInputElement; fireEvent.change(ja, { target: { value: ' Pending ' } });`
- L86 [placeholder-key/aria-label-key: `superAdmin.attrMasters.col.labelEn`] → input components/master-list-editor/MasterListEditor.tsx:164(G02)
  - `const enField = screen.getByLabelText(tr('superAdmin.attrMasters.col.labelEn')) as HTMLInputElement;`
- L71 [placeholder-key: `common.search`] → input pages/inbox/InboxConversationList.tsx:62(G32), pages/orders/OrdersFilterBar.tsx:32(G12), pages/products/ProductsPage.tsx:219(G14), pages/super-admin/DexTab.tsx:200(G02) …+2
  - `if (input === 'click') fireEvent.click(screen.getByRole('button', { name: tr('common.search') }));`

### frontend/tests-e2e/order-purchase.spec.ts（6 行）

- L326 [data-testid: `orders-search-input`] → input pages/orders/OrdersFilterBar.tsx:32(G12)
  - `await expect(page.getByTestId("orders-search-input")).toBeVisible();`
- L202 [aria-label-ja: `受注管理`] → input pages/orders/OrdersFilterBar.tsx:32(G12)
  - `await expect(page.getByRole("heading", { name: /受注管理/ })).toBeVisible({`
- L224 [aria-label-ja: `受注管理`] → input pages/orders/OrdersFilterBar.tsx:32(G12)
  - `await expect(page.getByRole("heading", { name: /受注管理/ })).toBeVisible({`
- L258 [aria-label-ja: `受注管理`] → input pages/orders/OrdersFilterBar.tsx:32(G12)
  - `await expect(page.getByRole("heading", { name: /受注管理/ })).toBeVisible({`
- L288 [aria-label-ja: `受注管理`] → input pages/orders/OrdersFilterBar.tsx:32(G12)
  - `await expect(page.getByRole("heading", { name: /受注管理/ })).toBeVisible({`
- L321 [aria-label-ja: `受注管理`] → input pages/orders/OrdersFilterBar.tsx:32(G12)
  - `await expect(page.getByRole("heading", { name: /受注管理/ })).toBeVisible({`

### frontend/tests-e2e/order-shipping.spec.ts（6 行）

- L358 [data-testid: `orders-search-input`] → input pages/orders/OrdersFilterBar.tsx:32(G12)
  - `await expect(page.getByTestId("orders-search-input")).toBeVisible();`
- L239 [aria-label-ja: `受注管理`] → input pages/orders/OrdersFilterBar.tsx:32(G12)
  - `await expect(page.getByRole("heading", { name: /受注管理/ })).toBeVisible({`
- L261 [aria-label-ja: `受注管理`] → input pages/orders/OrdersFilterBar.tsx:32(G12)
  - `await expect(page.getByRole("heading", { name: /受注管理/ })).toBeVisible({`
- L295 [aria-label-ja: `受注管理`] → input pages/orders/OrdersFilterBar.tsx:32(G12)
  - `await expect(page.getByRole("heading", { name: /受注管理/ })).toBeVisible({`
- L327 [aria-label-ja: `受注管理`] → input pages/orders/OrdersFilterBar.tsx:32(G12)
  - `await expect(page.getByRole("heading", { name: /受注管理/ })).toBeVisible({`
- L353 [aria-label-ja: `受注管理`] → input pages/orders/OrdersFilterBar.tsx:32(G12)
  - `await expect(page.getByRole("heading", { name: /受注管理/ })).toBeVisible({`

### frontend/tests-e2e/order-commission.spec.ts（5 行）

- L374 [data-testid: `orders-search-input`] → input pages/orders/OrdersFilterBar.tsx:32(G12)
  - `await expect(page.getByTestId("orders-search-input")).toBeVisible();`
- L283 [aria-label-ja: `受注管理`] → input pages/orders/OrdersFilterBar.tsx:32(G12)
  - `await expect(page.getByRole("heading", { name: /受注管理/ })).toBeVisible({`
- L304 [aria-label-ja: `受注管理`] → input pages/orders/OrdersFilterBar.tsx:32(G12)
  - `await expect(page.getByRole("heading", { name: /受注管理/ })).toBeVisible({`
- L325 [aria-label-ja: `受注管理`] → input pages/orders/OrdersFilterBar.tsx:32(G12)
  - `await expect(page.getByRole("heading", { name: /受注管理/ })).toBeVisible({`
- L369 [aria-label-ja: `受注管理`] → input pages/orders/OrdersFilterBar.tsx:32(G12)
  - `await expect(page.getByRole("heading", { name: /受注管理/ })).toBeVisible({`

### frontend/tests-e2e/order-financial.spec.ts（5 行）

- L297 [data-testid: `orders-search-input`] → input pages/orders/OrdersFilterBar.tsx:32(G12)
  - `await expect(page.getByTestId("orders-search-input")).toBeVisible();`
- L198 [aria-label-ja: `受注管理`] → input pages/orders/OrdersFilterBar.tsx:32(G12)
  - `await expect(page.getByRole("heading", { name: /受注管理/ })).toBeVisible({`
- L224 [aria-label-ja: `受注管理`] → input pages/orders/OrdersFilterBar.tsx:32(G12)
  - `await expect(page.getByRole("heading", { name: /受注管理/ })).toBeVisible({`
- L262 [aria-label-ja: `受注管理`] → input pages/orders/OrdersFilterBar.tsx:32(G12)
  - `await expect(page.getByRole("heading", { name: /受注管理/ })).toBeVisible({`
- L292 [aria-label-ja: `受注管理`] → input pages/orders/OrdersFilterBar.tsx:32(G12)
  - `await expect(page.getByRole("heading", { name: /受注管理/ })).toBeVisible({`

### frontend/src/components/CommerceSubmitButtonMigration.test.tsx（4 行）

- L134 [data-testid: `product-edit-name-ja`] → input pages/products/ProductEditPage.tsx:215(G06)
  - `await act(async () => first.reject(new Error('Product save failed'))); expect(await screen.findByText('Product save failed')).toBeTruthy(); expect((screen.getByTestId('product-edit-name-ja') as HTMLInputElement).value).toBe('Product'); expect(save.disabled).to`
- L147 [data-testid: `product-edit-name-ja`] → input pages/products/ProductEditPage.tsx:215(G06)
  - `render(routed(<ProductEditPage />, '/admin/products/:id/edit', ['/before', '/admin/products/9/edit'])); await waitFor(() => expect((screen.getByTestId('product-edit-name-ja') as HTMLInputElement).value).toBe('Existing'));`
- L150 [data-testid: `product-edit-name-ja`] → input pages/products/ProductEditPage.tsx:215(G06)
  - `await act(async () => first.reject(new Error('Edit save failed'))); expect(await screen.findByText('Edit save failed')).toBeTruthy(); expect((screen.getByTestId('product-edit-name-ja') as HTMLInputElement).value).toBe('Edited'); expect(save.disabled).toBe(fals`
- L113 [data-testid: `shipping-fee-input`] → input pages/quote-create/QuoteCreatePage.tsx:268(G01)
  - `fireEvent.change(screen.getByTestId('shipping-fee-input'), { target: { value: '3' } });`

### frontend/src/components/FedExRateModal.test.tsx（3 行）

- L22 [placeholder-key: `fedexRateModal.originPlaceholder`] → input components/FedExRateModal.tsx:176(G17)
  - `"fedexRateModal.originPlaceholder": "JP",`
- L24 [placeholder-key: `fedexRateModal.destinationPlaceholder`] → input components/FedExRateModal.tsx:193(G17)
  - `"fedexRateModal.destinationPlaceholder": "e.g. US",`
- L43 [placeholder-key: `fedexRateModal.postalCodePlaceholder`] → input components/FedExRateModal.tsx:239(G44)
  - `"fedexRateModal.postalCodePlaceholder": "e.g. 10001",`

### frontend/src/pages/super-admin/TcgSoldOutPage.test.tsx（3 行）

- L30 [placeholder-en: `Search`] → input pages/inbox/InboxConversationList.tsx:62(G32), pages/orders/OrdersFilterBar.tsx:32(G12), pages/products/ProductsPage.tsx:219(G14), pages/super-admin/DexTab.tsx:200(G02) …+2
  - `expect(api.get).not.toHaveBeenCalled(); expect(screen.queryByRole("button", { name: "Search" })).toBeNull(); cleanup();`
- L56 [placeholder-en: `Search`] → input pages/inbox/InboxConversationList.tsx:62(G32), pages/orders/OrdersFilterBar.tsx:32(G12), pages/products/ProductsPage.tsx:219(G14), pages/super-admin/DexTab.tsx:200(G02) …+2
  - `fireEvent.click(screen.getByRole("button", { name: "Search" }));`
- L67 [placeholder-en: `Search`] → input pages/inbox/InboxConversationList.tsx:62(G32), pages/orders/OrdersFilterBar.tsx:32(G12), pages/products/ProductsPage.tsx:219(G14), pages/super-admin/DexTab.tsx:200(G02) …+2
  - `fireEvent.click(screen.getByRole("button", { name: "Search" }));`

### frontend/src/components/RoleKnowledgeButtonMigration.test.tsx（3 行）

- L59 [data-testid: `alias-text-input`] → input pages/super-admin/KnowledgeAliasesTab.tsx:516(G01)
  - `fireEvent.change(screen.getByTestId('alias-supplier-select'), { target: { value: '7' } }); fireEvent.change(screen.getByTestId('alias-text-input'), { target: { value: 'alias value' } }); fireEvent.change(screen.getByTestId('alias-product-select'), { target: { `
- L169 [data-testid: `alias-text-input`] → input pages/super-admin/KnowledgeAliasesTab.tsx:516(G01)
  - `({ dialog } = openKnowledge('alias')); fireEvent.change(screen.getByTestId('alias-text-input'), { target: { value: 'alias without supplier' } }); fireEvent.submit(dialog.querySelector('form')!); expect(mock.post).not.toHaveBeenCalled();`
- L179 [data-testid: `alias-text-input`] → input pages/super-admin/KnowledgeAliasesTab.tsx:516(G01)
  - `expect(kind === 'rule' ? dialog.querySelector<HTMLInputElement>('input')!.value : (screen.getByTestId('alias-text-input') as HTMLInputElement).value).toBe(''); fillKnowledge(kind, dialog);`

### frontend/tests-e2e/po-pdf-mail.spec.ts（2 行）

- L169 [data-testid/id: `tp-company-name`] → input pages/admin/TenantProfilePage.tsx:145(G01)
  - `await expect(page.getByTestId("tp-company-name")).toHaveValue("QA テナント株式会社");`
- L172 [data-testid/id: `tp-phone`] → input pages/admin/TenantProfilePage.tsx:183(G01)
  - `await page.getByTestId("tp-phone").fill("06-9999-0000");`

### frontend/tests-e2e/goal-setting-advisor.spec.ts（2 行）

- L97 [data-testid: `goal-advisor-monthly-kgi`] → input pages/goal-setting/GoalSettingPage.tsx:334(G35)
  - `await page.getByTestId("goal-advisor-monthly-kgi").fill("3000000");`
- L175 [data-testid: `goal-advisor-monthly-kgi`] → input pages/goal-setting/GoalSettingPage.tsx:334(G35)
  - `await page.getByTestId("goal-advisor-monthly-kgi").fill("8");`

### frontend/src/components/CommerceNavigationButtonMigration.test.tsx（2 行）

- L100 [placeholder-key: `invoices.voidReasonPlaceholder`] → input pages/invoice-detail/InvoiceDetailPage.tsx:271(G46)
  - `expect(screen.getByPlaceholderText(tr('invoices.voidReasonPlaceholder'))).toBeTruthy();`
- L102 [placeholder-key: `invoices.voidReasonPlaceholder`] → input pages/invoice-detail/InvoiceDetailPage.tsx:271(G46)
  - `expect(screen.queryByPlaceholderText(tr('invoices.voidReasonPlaceholder'))).toBeNull(); expect(mock.post).not.toHaveBeenCalled();`

### frontend/tests-e2e/lead-channel-control.spec.ts（1 行）

- L62 [placeholder-ja/placeholder-en: `JP`] → input components/FedExRateModal.tsx:176(G17)
  - `{ code: "JP", name: "Japan", dial_code: "+81", is_active: true },`

### frontend/tests-e2e/lead-country-control.spec.ts（1 行）

- L78 [placeholder-ja/placeholder-en: `JP`] → input components/FedExRateModal.tsx:176(G17)
  - `{ code: "JP", name: "Japan", dial_code: "+81", is_active: true },`

### frontend/src/pages/super-admin/TcgProductMasterPage.test.tsx（1 行）

- L56 [placeholder-en: `Search`] → input pages/inbox/InboxConversationList.tsx:62(G32), pages/orders/OrdersFilterBar.tsx:32(G12), pages/products/ProductsPage.tsx:219(G14), pages/super-admin/DexTab.tsx:200(G02) …+2
  - `expect(screen.getAllByRole("columnheader").map(cell => cell.textContent)).toEqual(["Mark", "Product name", "Release date", "Search", "Exclude"]);`

### tests/qa-smoke/scene-09.spec.ts（1 行）

- L164 [data-testid/class: `sales-form-other-input`] → input pages/inbox/SalesFormMultiSelect.tsx:148(G39)
  - `const otherInput = page.locator("[data-testid='sales-form-other-input']");`

### frontend/tests-e2e/super-admin-llm-budget.spec.ts（1 行）

- L172 [data-testid: `llm-budget-input-monthly-budget`] → input pages/super-admin/LLMBudgetTab.tsx:187(G02)
  - `const budgetInput = page.getByTestId("llm-budget-input-monthly-budget");`

## B. セレクタ種別の全体件数（テスト全体、対象 input に限定しない）

| 種別 | 行数 | ファイル数 |
|---|---|---|
| css-selector input | 61 | 14 |
| css-selector comp-field__input | 9 | 1 |
| getByPlaceholderText | 14 | 4 |
| getByLabelText | 61 | 13 |
| getByRole textbox/spinbutton/searchbox | 18 | 7 |
| getByDisplayValue | 16 | 11 |
| getByTestId | 451 | 51 |
| input[type= | 22 | 7 |
| HTMLInputElement | 74 | 18 |
| fireEvent.change/userEvent.type/fill | 244 | 59 |

### B-1. input 要素セレクタ・comp-field__input・input[type= の該当行

#### css-selector input（61 行）

- frontend/src/components/AccountCompanySaveButtonMigration.test.tsx:61 `const field = (key: string) => screen.getByText(tr(key), { selector: 'label' }).parentElement!.querySelector('input,textarea,select') as HTMLInputElement;`
- frontend/src/components/CommerceNavigationButtonMigration.test.tsx:128 `await screen.findByTestId('product-edit-save'); fireEvent.change(document.querySelector('input[required]')!, { target: { value: 'Product' } });`
- frontend/src/components/CommerceSubmitButtonMigration.test.tsx:114 `fireEvent.change(screen.getByText(String(instance.t('quotes.tax'))).parentElement!.querySelector('input')!, { target: { value: '7' } }); fireEvent.change(screen.getByText(String(instance.t('common.not`
- frontend/src/components/OrderLeadButtonMigration.test.tsx:62 `fireEvent.click(screen.getByRole('button', { name: tr('orders.newOrder') })); const reset = screen.getByRole('dialog', { name: tr('orders.newOrder') }); expect((reset.querySelector('input[required]') `
- frontend/src/components/OrderLeadButtonMigration.test.tsx:69 `fireEvent.change(dialog.querySelector('input[required]')!, { target: { value: 'ORD-EDIT' } }); fireEvent.click(within(dialog).getByRole('button', { name: tr('common.update') }));`
- frontend/src/components/OrderLeadButtonMigration.test.tsx:72 `const reopened = screen.getByRole('dialog', { name: tr('orders.editOrder') }); fireEvent.change(reopened.querySelector('input[required]')!, { target: { value: 'Cancel edit' } }); fireEvent.click(withi`
- frontend/src/components/OrderLeadButtonMigration.test.tsx:78 `fireEvent.change(dialog.querySelector('input[required]')!, { target: { value: 'Guard order' } }); fireEvent.submit(dialog.querySelector('form')!); expect(await screen.findByText(tr('companyContactSele`
- frontend/src/components/OrderLeadButtonMigration.test.tsx:91 `fireEvent.change(selects[0], { target: { value: '4' } }); await waitFor(() => expect(mock.get.mock.calls.filter(c => c[0] === '/contacts?company_id=4&per_page=100').length).toBeGreaterThan(1)); fireEv`
- frontend/src/components/OrderLeadButtonMigration.test.tsx:100 `fireEvent.click(screen.getByRole('button', { name: tr('common.edit') })); dialog = screen.getByRole('dialog', { name: tr('orders.editOrder') }); fireEvent.change(dialog.querySelector('input[required]'`
- frontend/src/components/OrderLeadButtonMigration.test.tsx:108 `fireEvent.change(dialog.querySelector('input[required]')!, { target: { value: 'Pending retained' } }); fireEvent.click(within(dialog).getByRole('button', { name: mode === 'edit' ? tr('common.update') `
- frontend/src/components/OrderLeadButtonMigration.test.tsx:109 `if (reject) { pending.reject(new Error('Late failure')); await screen.findByText('Late failure'); fireEvent.click(screen.getByRole('button', { name: mode === 'edit' ? tr('common.edit') : tr('orders.ne`
- frontend/src/components/OrderLeadButtonMigration.test.tsx:110 `else { pending.resolve({}); await waitFor(() => expect(mode === 'edit' ? mock.patch : mock.post).toHaveBeenCalledTimes(1)); fireEvent.click(screen.getByRole('button', { name: mode === 'edit' ? tr('com`
- frontend/src/components/OrderLeadButtonMigration.test.tsx:116 `fireEvent.change(dialog.querySelector('input[required]')!, { target: { value: ' Deal title ' } });`
- frontend/src/components/OrderLeadButtonMigration.test.tsx:126 `fireEvent.click(screen.getByRole('button', { name: tr('leads.convert') })); const reset = screen.getByRole('dialog', { name: tr('leads.convertLead') }); expect((reset.querySelector('input[required]') `
- frontend/src/components/OrderLeadButtonMigration.test.tsx:134 `const selects = dialog.querySelectorAll<HTMLSelectElement>('select'); fireEvent.change(selects[0], { target: { value: '4' } }); await waitFor(() => expect(mock.get).toHaveBeenCalledWith('/contacts?com`
- frontend/src/components/OrderLeadButtonMigration.test.tsx:135 `let save = within(dialog).getByRole('button', { name: tr('leads.convert') }) as HTMLButtonElement; fireEvent.click(save); expect(await screen.findByText('Convert failure')).toBeTruthy(); expect((dialo`
- frontend/src/components/OrderLeadButtonMigration.test.tsx:140 `fireEvent.click(within(dialog).getByRole('button', { name: tr('leads.convert') })); expect(mock.post).not.toHaveBeenCalled(); fireEvent.change(dialog.querySelector('input[required]')!, { target: { val`
- frontend/src/components/OrderLeadButtonMigration.test.tsx:144 `const pending = deferred(); mock.post.mockReturnValue(pending.promise); render(wrap(<LeadsPage />)); await screen.findByText('Fixture Lead'); fireEvent.click(screen.getByRole('button', { name: tr('lea`
- frontend/src/components/OrderLeadButtonMigration.test.tsx:148 `const pending = deferred(); mock.post.mockReturnValue(pending.promise); render(wrap(<LeadsPage />)); await screen.findByText('Fixture Lead'); const before = mock.get.mock.calls.filter(c => c[0] === '/`
- frontend/src/components/OrderLeadButtonMigration.test.tsx:150 `else { pending.resolve({}); await waitFor(() => expect(mock.get.mock.calls.filter(c => c[0] === '/leads')).toHaveLength(before + 1)); fireEvent.click(screen.getByRole('button', { name: tr('leads.conve`
- frontend/src/components/PurchaseAdminEditorButtonMigration.test.tsx:67 `expect((dialog.querySelector('select') as HTMLSelectElement).value).toBe(''); expect((dialog.querySelector('input[readonly]') as HTMLInputElement).value).toBe(''); fireEvent.click(within(dialog).getBy`
- frontend/src/components/RoleKnowledgeButtonMigration.test.tsx:43 `fireEvent.change(dialog.querySelector('input[required]')!, { target: { value: name } });`
- frontend/src/components/RoleKnowledgeButtonMigration.test.tsx:75 `({ dialog } = openRole()); fireEvent.change(dialog.querySelector('input[required]')!, { target: { value: 'Retained' } });`
- frontend/src/components/RoleKnowledgeButtonMigration.test.tsx:137 `fireEvent.change(dialog.querySelector('input[type="number"]')!, { target: { value: '77' } }); fireEvent.click(dialog.querySelector('input[type="checkbox"]')!); mock.put.mockResolvedValue({}); fireEven`
- frontend/src/components/RoleKnowledgeButtonMigration.test.tsx:139 `dialog = open(); expect(dialog.querySelector<HTMLInputElement>('input[type="number"]')!.value).toBe(''); fireEvent.change(dialog.querySelector('input[type="number"]')!, { target: { value: '88' } }); f`
- frontend/src/components/RoleKnowledgeButtonMigration.test.tsx:140 `fireEvent.change(dialog.querySelector('input[type="number"]')!, { target: { value: '77' } }); mock.put.mockRejectedValueOnce(new Error('Assignment failure')).mockResolvedValueOnce({}); fireEvent.click`
- frontend/src/components/RoleKnowledgeButtonMigration.test.tsx:141 `dialog = open(); fireEvent.change(dialog.querySelector('input[type="number"]')!, { target: { value: '77' } });`
- frontend/src/components/RoleKnowledgeButtonMigration.test.tsx:143 `dialog = open(); fireEvent.change(dialog.querySelector('input[type="number"]')!, { target: { value: '99' } });`
- frontend/src/components/RoleKnowledgeButtonMigration.test.tsx:145 `fireEvent.change(dialog.querySelector('input[type="number"]')!, { target: { value: '99' } }); fireEvent.keyDown(document, { key: 'Escape' });`
- frontend/src/components/RoleKnowledgeButtonMigration.test.tsx:147 `fireEvent.change(dialog.querySelector('input[type="number"]')!, { target: { value: '77' } });`
- frontend/src/components/TextField.test.tsx:105 `const cls = () => container.querySelector('input')?.className;`
- frontend/src/components/TextField.test.tsx:121 `expect(ref.current).toBe(container.querySelector('input'));`
- frontend/src/components/TextField.test.tsx:129 `expect(ref).toHaveBeenCalledWith(container.querySelector('input'));`
- frontend/src/components/TextField.test.tsx:152 `const el = container.querySelector('input') as HTMLInputElement;`
- frontend/src/components/TextField.test.tsx:179 `const el = container.querySelector('input') as HTMLInputElement;`
- frontend/src/components/TextField.test.tsx:194 `const el = container.querySelector('input') as HTMLInputElement;`
- frontend/tests-e2e/goal-setting-advisor.spec.ts:103 `await expect(page.getByTestId("goal-advisor-weekly-leads").locator("input")).toHaveValue("40");`
- frontend/tests-e2e/goal-setting-advisor.spec.ts:104 `await expect(page.getByTestId("goal-advisor-weekly-deals").locator("input")).toHaveValue("16");`
- frontend/tests-e2e/goal-setting-advisor.spec.ts:105 `await expect(page.getByTestId("goal-advisor-weekly-wins").locator("input")).toHaveValue("8");`
- frontend/tests-e2e/goal-setting-advisor.spec.ts:108 `await page.getByTestId("goal-advisor-weekly-leads").locator("input").fill("44");`
- frontend/tests-e2e/goal-setting-advisor.spec.ts:109 `await expect(page.getByTestId("goal-advisor-weekly-leads").locator("input")).toHaveValue("44");`
- frontend/tests-e2e/goal-setting-advisor.spec.ts:182 `await expect(page.getByTestId("goal-advisor-weekly-leads").locator("input")).toHaveValue("");`
- frontend/tests-e2e/goal-setting-advisor.spec.ts:183 `await expect(page.getByTestId("goal-advisor-weekly-deals").locator("input")).toHaveValue("");`
- frontend/tests-e2e/goal-setting-advisor.spec.ts:184 `await expect(page.getByTestId("goal-advisor-weekly-wins").locator("input")).toHaveValue("");`
- frontend/tests-e2e/karte-visual-gate.spec.ts:331 `const urlInputs = page.locator('.right-panel-tab-content input[type="url"]');`
- frontend/tests-e2e/register-form-ux.spec.ts:97 `await contactFieldset.locator("label", { hasText: "担当者名" }).locator("input").fill("田中太郎");`
- frontend/tests-e2e/register-form-ux.spec.ts:107 `await contactFieldset.locator("label", { hasText: "担当者名" }).locator("input").fill("田中太郎");`
- frontend/tests-e2e/register-form-ux.spec.ts:108 `await contactFieldset.locator("input[type=email]").fill("tanaka@example.com");`
- frontend/tests-e2e/register-form-ux.spec.ts:116 `await contactFieldset.locator("label", { hasText: "担当者名" }).locator("input").fill("山田花子");`
- frontend/tests-e2e/register-form-ux.spec.ts:117 `await contactFieldset.locator("input[type=tel]").fill("09012345678");`
- frontend/tests-e2e/register-form-ux.spec.ts:126 `await contactFieldset.locator("label", { hasText: "担当者名" }).locator("input").fill("テスト");`
- frontend/tests-e2e/register-form-ux.spec.ts:127 `await contactFieldset.locator("input[type=email]").fill("t@example.com");`
- frontend/tests-e2e/register-form-ux.spec.ts:141 `await contactFieldset.locator("label", { hasText: "担当者名" }).locator("input").fill("テスト");`
- frontend/tests-e2e/register-form-ux.spec.ts:142 `await contactFieldset.locator("input[type=email]").fill("t@example.com");`
- frontend/tests-e2e/super-admin-masters.spec.ts:124 `const textInputs = dialog.locator(".form-group input[type='text'], .form-group input:not([type])");`
- frontend/tests-e2e/tcg-import-workflow.spec.ts:255 `const hours = uploadDetails.locator('input[type="number"]');`
- frontend/tests-e2e/tcg-product-import.spec.ts:50 `await page.locator('input[type="file"]').setInputFiles({ name: "update.csv", mimeType: "text/csv", buffer: raw });`
- frontend/tests-e2e/tcg-product-import.spec.ts:81 `await page.locator('input[type="file"]').setInputFiles({ name: "products.csv", mimeType: "text/csv", buffer: Buffer.from(csv) });`
- frontend/tests-e2e/tcg-product-import.spec.ts:165 `await expect(page.locator('input[type="file"]')).toHaveCount(0);`
- frontend/tests-e2e/tcg-product-import.spec.ts:219 `await page.locator('input[type="file"]').setInputFiles({`
- frontend/tests-e2e/ui-companies-edit-modal-i18n.spec.ts:97 `await expect(page.locator(".modal-content-wide").locator("input").first()).toBeVisible();`

#### css-selector comp-field__input（9 行）

- frontend/src/components/TextField.test.tsx:10 `const INPUT = '<input id="t" class="comp-field__input">';`
- frontend/src/components/TextField.test.tsx:23 `'<input id="t" class="comp-field__input" required=""></div>',`
- frontend/src/components/TextField.test.tsx:78 `'<input id="t" class="comp-field__input" type="email" placeholder="ph" maxlength="10" disabled="" aria-label="al" data-testid="tid" value="v"></div>',`
- frontend/src/components/TextField.test.tsx:86 `'<input id="t" class="comp-field__input" type="number" min="1" max="9" step="2" readonly=""></div>',`
- frontend/src/components/TextField.test.tsx:106 `expect(cls()).toBe('comp-field__input');`
- frontend/src/components/TextField.test.tsx:108 `expect(cls()).toBe('comp-field__input comp-field__input--sm');`
- frontend/src/components/TextField.test.tsx:110 `expect(cls()).toBe('comp-field__input comp-field__input--lg');`
- frontend/src/components/TextField.test.tsx:112 `expect(cls()).toBe('comp-field__input x');`
- frontend/src/components/TextField.test.tsx:114 `expect(cls()).toBe('comp-field__input comp-field__input--sm x');`

#### input[type=（22 行）

- frontend/src/components/OrderLeadButtonMigration.test.tsx:121 `const number = dialog.querySelector<HTMLInputElement>('input[type="number"]')!; fireEvent.change(number, { target: { value: '500' } });`
- frontend/src/components/RoleKnowledgeButtonMigration.test.tsx:137 `fireEvent.change(dialog.querySelector('input[type="number"]')!, { target: { value: '77' } }); fireEvent.click(dialog.querySelector('input[type="checkbox"]')!); mock.put.mockResolvedValue({}); fireEven`
- frontend/src/components/RoleKnowledgeButtonMigration.test.tsx:139 `dialog = open(); expect(dialog.querySelector<HTMLInputElement>('input[type="number"]')!.value).toBe(''); fireEvent.change(dialog.querySelector('input[type="number"]')!, { target: { value: '88' } }); f`
- frontend/src/components/RoleKnowledgeButtonMigration.test.tsx:140 `fireEvent.change(dialog.querySelector('input[type="number"]')!, { target: { value: '77' } }); mock.put.mockRejectedValueOnce(new Error('Assignment failure')).mockResolvedValueOnce({}); fireEvent.click`
- frontend/src/components/RoleKnowledgeButtonMigration.test.tsx:141 `dialog = open(); fireEvent.change(dialog.querySelector('input[type="number"]')!, { target: { value: '77' } });`
- frontend/src/components/RoleKnowledgeButtonMigration.test.tsx:143 `dialog = open(); fireEvent.change(dialog.querySelector('input[type="number"]')!, { target: { value: '99' } });`
- frontend/src/components/RoleKnowledgeButtonMigration.test.tsx:144 `fireEvent.click(within(dialog).getByRole('button', { name: tr('common.close') })); dialog = open(); expect(dialog.querySelector<HTMLInputElement>('input[type="number"]')!.value).toBe('');`
- frontend/src/components/RoleKnowledgeButtonMigration.test.tsx:145 `fireEvent.change(dialog.querySelector('input[type="number"]')!, { target: { value: '99' } }); fireEvent.keyDown(document, { key: 'Escape' });`
- frontend/src/components/RoleKnowledgeButtonMigration.test.tsx:146 `dialog = open(); expect(dialog.querySelector<HTMLInputElement>('input[type="number"]')!.value).toBe('');`
- frontend/src/components/RoleKnowledgeButtonMigration.test.tsx:147 `fireEvent.change(dialog.querySelector('input[type="number"]')!, { target: { value: '77' } });`
- frontend/tests-e2e/karte-visual-gate.spec.ts:330 `// No input[type="url"] should exist in the tab content`
- frontend/tests-e2e/karte-visual-gate.spec.ts:331 `const urlInputs = page.locator('.right-panel-tab-content input[type="url"]');`
- frontend/tests-e2e/register-form-ux.spec.ts:108 `await contactFieldset.locator("input[type=email]").fill("tanaka@example.com");`
- frontend/tests-e2e/register-form-ux.spec.ts:117 `await contactFieldset.locator("input[type=tel]").fill("09012345678");`
- frontend/tests-e2e/register-form-ux.spec.ts:127 `await contactFieldset.locator("input[type=email]").fill("t@example.com");`
- frontend/tests-e2e/register-form-ux.spec.ts:142 `await contactFieldset.locator("input[type=email]").fill("t@example.com");`
- frontend/tests-e2e/super-admin-masters.spec.ts:124 `const textInputs = dialog.locator(".form-group input[type='text'], .form-group input:not([type])");`
- frontend/tests-e2e/tcg-import-workflow.spec.ts:255 `const hours = uploadDetails.locator('input[type="number"]');`
- frontend/tests-e2e/tcg-product-import.spec.ts:50 `await page.locator('input[type="file"]').setInputFiles({ name: "update.csv", mimeType: "text/csv", buffer: raw });`
- frontend/tests-e2e/tcg-product-import.spec.ts:81 `await page.locator('input[type="file"]').setInputFiles({ name: "products.csv", mimeType: "text/csv", buffer: Buffer.from(csv) });`
- frontend/tests-e2e/tcg-product-import.spec.ts:165 `await expect(page.locator('input[type="file"]')).toHaveCount(0);`
- frontend/tests-e2e/tcg-product-import.spec.ts:219 `await page.locator('input[type="file"]').setInputFiles({`

#### HTMLInputElement（74 行）

- frontend/src/components/AccountCompanySaveButtonMigration.test.tsx:54 `render(provider(<UiPrefsProvider><ProfileSection /></UiPrefsProvider>)); await screen.findByText('me@example.com'); const surname = screen.getByLabelText(tr('accountSettings.surnameJp')) as HTMLInputE`
- frontend/src/components/AccountCompanySaveButtonMigration.test.tsx:61 `const field = (key: string) => screen.getByText(tr(key), { selector: 'label' }).parentElement!.querySelector('input,textarea,select') as HTMLInputElement;`
- frontend/src/components/AccountCompanySaveButtonMigration.test.tsx:65 `await act(async () => pending.resolve({})); await waitFor(() => expect(mock.get.mock.calls.filter(c => c[0] === '/companies/41')).toHaveLength(companyReads + 1)); expect(mock.get.mock.calls.filter(c =`
- frontend/src/components/AccountCompanySaveButtonMigration.test.tsx:69 `renderCompany(); await screen.findByText('Old Co'); const name = screen.getByDisplayValue('Old Co') as HTMLInputElement; fireEvent.change(name, { target: { value: 'Retained Co' } }); mock.patch.mockRe`
- frontend/src/components/AccountCompanySaveButtonMigration.test.tsx:75 `renderCompany(); await screen.findByText('Old Co'); fireEvent.click(screen.getByRole('button', { name: /Channels/ })); const input = await screen.findByDisplayValue('old') as HTMLInputElement; fireEve`
- frontend/src/components/AccountCompanySaveButtonMigration.test.tsx:77 `const failedPayload = mock.patch.mock.calls[0]; const contactReads = mock.get.mock.calls.filter(c => c[0] === '/companies/41/contacts').length; const pending = deferred(); mock.patch.mockReturnValueOn`
- frontend/src/components/AdminMasterSaveButtonMigration.test.tsx:36 `cleanup(); const events: string[] = []; mock.post.mockRejectedValueOnce(new Error('PO failed')).mockResolvedValueOnce({}); render(wrap(<PurchaseOrdersFormModal open onCreated={() => events.push('creat`
- frontend/src/components/AdminMasterSaveButtonMigration.test.tsx:40 `render(wrap(<DexTab />)); await screen.findAllByText('Pikachu'); fireEvent.click(screen.getAllByRole('button', { name: tr('common.edit') })[0]); const name = screen.getByPlaceholderText(tr('superAdmin`
- frontend/src/components/AdminMasterSaveButtonMigration.test.tsx:53 `mock.post.mockResolvedValue({}); mock.patch.mockResolvedValue({}); render(wrap(<TcgSeriesTab />)); await screen.findByText('Series fixture'); fireEvent.click(screen.getByRole('button', { name: tr('sup`
- frontend/src/components/AdminMasterSaveButtonMigration.test.tsx:54 `expect(typeInputs[0].value).toBe(''); expect(typeInputs[1].value).toBe(''); fireEvent.click(screen.getByRole('button', { name: tr('common.edit') })); const code = screen.getByPlaceholderText(tr('super`
- frontend/src/components/AdminMasterSaveButtonMigration.test.tsx:58 `render(wrap(<TcgSeriesTab />)); await screen.findByText('Series fixture'); fireEvent.click(screen.getByRole('button', { name: tr('common.edit') })); const code = screen.getByPlaceholderText(tr('superA`
- frontend/src/components/AdminMasterSaveButtonMigration.test.tsx:59 `const first = deferred(), second = deferred(); mock.patch.mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise); const save = screen.getByRole('button', { name: tr('common.update') })`
- frontend/src/components/AdminMasterSaveButtonMigration.test.tsx:67 `render(wrap(<TcgSeriesTab />)); await screen.findByText('Series fixture'); fireEvent.click(screen.getByRole('button', { name: tr('superAdmin.tcg.typeManager.title') })); const manager = screen.getByTe`
- frontend/src/components/BotFormButtonMigration.test.tsx:32 `const input = label.parentElement?.querySelector<HTMLInputElement | HTMLSelectElement>('input,select');`
- frontend/src/components/CommerceSubmitButtonMigration.test.tsx:43 `const controls = Array.from(form.querySelectorAll<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>('input, select, textarea'));`
- frontend/src/components/CommerceSubmitButtonMigration.test.tsx:77 `expect(inputs.map(input => (input as HTMLInputElement).value)).toEqual(['', '', '', '']); expect(numbers.map(input => (input as HTMLInputElement).value)).toEqual(['1', '0', '']);`
- frontend/src/components/CommerceSubmitButtonMigration.test.tsx:120 `expect((screen.getByTestId('quote-item-row-0-name') as HTMLInputElement).value).toBe('Card'); expect(submit.disabled).toBe(false);`
- frontend/src/components/CommerceSubmitButtonMigration.test.tsx:134 `await act(async () => first.reject(new Error('Product save failed'))); expect(await screen.findByText('Product save failed')).toBeTruthy(); expect((screen.getByTestId('product-edit-name-ja') as HTMLIn`
- frontend/src/components/CommerceSubmitButtonMigration.test.tsx:147 `render(routed(<ProductEditPage />, '/admin/products/:id/edit', ['/before', '/admin/products/9/edit'])); await waitFor(() => expect((screen.getByTestId('product-edit-name-ja') as HTMLInputElement).valu`
- frontend/src/components/CommerceSubmitButtonMigration.test.tsx:148 `const form = screen.getByTestId('product-edit-form'); const controls = Array.from(form.querySelectorAll<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>('input, select, textarea')); fireEve`
- frontend/src/components/CommerceSubmitButtonMigration.test.tsx:150 `await act(async () => first.reject(new Error('Edit save failed'))); expect(await screen.findByText('Edit save failed')).toBeTruthy(); expect((screen.getByTestId('product-edit-name-ja') as HTMLInputEle`
- frontend/src/components/FedExRateModal.test.tsx:78 `const input = screen.getByDisplayValue("US") as HTMLInputElement;`
- frontend/src/components/FedExRateModal.test.tsx:124 `const input = screen.getByLabelText("Weight (kg)") as HTMLInputElement;`
- frontend/src/components/FormActionButtonMigration.test.tsx:34 `const inputs = Array.from(dialog.querySelectorAll<HTMLInputElement>('input'));`
- frontend/src/components/FormActionButtonMigration.test.tsx:55 `function values(dialog: HTMLElement) { return Array.from(dialog.querySelectorAll<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>('input,textarea,select')).map(x => x.value); }`
- frontend/src/components/FormActionButtonMigration.test.tsx:100 `const values = Array.from(reopened.dialog.querySelectorAll<HTMLInputElement | HTMLTextAreaElement>('input,textarea')).map(x => x.value);`
- frontend/src/components/FormActionButtonMigration.test.tsx:126 `const required = Array.from(dialog.querySelectorAll<HTMLInputElement>('input[required]'));`
- frontend/src/components/FullPageFormButtonMigration.test.tsx:34 `const input = node.parentElement?.querySelector<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>('input,select,textarea');`
- frontend/src/components/LeadFormButtonMigration.test.tsx:33 `const input = label.parentElement?.querySelector<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>('input,textarea,select');`
- frontend/src/components/MasterSearchButtonMigration.test.tsx:48 `const field = screen.getByTestId(c.input) as HTMLInputElement;`
- frontend/src/components/MasterSearchButtonMigration.test.tsx:69 `const field = screen.getByPlaceholderText(tr('superAdmin.attrMasters.searchPlaceholder')) as HTMLInputElement;`
- frontend/src/components/MasterSearchButtonMigration.test.tsx:85 `const ja = screen.getByLabelText(tr('superAdmin.attrMasters.col.labelJa')) as HTMLInputElement;`
- frontend/src/components/MasterSearchButtonMigration.test.tsx:86 `const enField = screen.getByLabelText(tr('superAdmin.attrMasters.col.labelEn')) as HTMLInputElement;`
- frontend/src/components/MasterSearchButtonMigration.test.tsx:104 `const ja = screen.getByLabelText(tr('superAdmin.attrMasters.col.labelJa')) as HTMLInputElement;`
- frontend/src/components/MasterSearchButtonMigration.test.tsx:116 `const ja = screen.getByLabelText(tr('superAdmin.attrMasters.col.labelJa')) as HTMLInputElement; fireEvent.change(ja, { target: { value: ' Pending ' } });`
- frontend/src/components/OrderLeadButtonMigration.test.tsx:54 `const inputs = dialog.querySelectorAll<HTMLInputElement>('input'); fireEvent.change(inputs[0], { target: { value: ' ORD-X ' } }); fireEvent.change(inputs[1], { target: { value: '250' } });`
- frontend/src/components/OrderLeadButtonMigration.test.tsx:62 `fireEvent.click(screen.getByRole('button', { name: tr('orders.newOrder') })); const reset = screen.getByRole('dialog', { name: tr('orders.newOrder') }); expect((reset.querySelector('input[required]') `
- frontend/src/components/OrderLeadButtonMigration.test.tsx:88 `const number = dialog.querySelectorAll<HTMLInputElement>('input'); fireEvent.change(number[0], { target: { value: 'Retry order' } }); const save = within(dialog).getByRole('button', { name: tr('common`
- frontend/src/components/OrderLeadButtonMigration.test.tsx:98 `fireEvent.click(await screen.findByRole('button', { name: tr('common.edit') })); let dialog = screen.getByRole('dialog', { name: tr('orders.editOrder') }); const number = dialog.querySelector<HTMLInpu`
- frontend/src/components/OrderLeadButtonMigration.test.tsx:109 `if (reject) { pending.reject(new Error('Late failure')); await screen.findByText('Late failure'); fireEvent.click(screen.getByRole('button', { name: mode === 'edit' ? tr('common.edit') : tr('orders.ne`
- frontend/src/components/OrderLeadButtonMigration.test.tsx:110 `else { pending.resolve({}); await waitFor(() => expect(mode === 'edit' ? mock.patch : mock.post).toHaveBeenCalledTimes(1)); fireEvent.click(screen.getByRole('button', { name: mode === 'edit' ? tr('com`
- frontend/src/components/OrderLeadButtonMigration.test.tsx:121 `const number = dialog.querySelector<HTMLInputElement>('input[type="number"]')!; fireEvent.change(number, { target: { value: '500' } });`
- frontend/src/components/OrderLeadButtonMigration.test.tsx:126 `fireEvent.click(screen.getByRole('button', { name: tr('leads.convert') })); const reset = screen.getByRole('dialog', { name: tr('leads.convertLead') }); expect((reset.querySelector('input[required]') `
- frontend/src/components/OrderLeadButtonMigration.test.tsx:135 `let save = within(dialog).getByRole('button', { name: tr('leads.convert') }) as HTMLButtonElement; fireEvent.click(save); expect(await screen.findByText('Convert failure')).toBeTruthy(); expect((dialo`
- frontend/src/components/OrderLeadButtonMigration.test.tsx:150 `else { pending.resolve({}); await waitFor(() => expect(mock.get.mock.calls.filter(c => c[0] === '/leads')).toHaveLength(before + 1)); fireEvent.click(screen.getByRole('button', { name: tr('leads.conve`
- frontend/src/components/PageFormButtonMigration.test.tsx:28 `const input = node.parentElement?.querySelector<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>('input,select,textarea');`
- frontend/src/components/PurchaseAdminEditorButtonMigration.test.tsx:63 `expect((dialog.querySelector('select') as HTMLSelectElement).value).toBe('7'); expect((within(dialog).getByDisplayValue('Inventory product') as HTMLInputElement).value).toBe('Inventory product');`
- frontend/src/components/PurchaseAdminEditorButtonMigration.test.tsx:67 `expect((dialog.querySelector('select') as HTMLSelectElement).value).toBe(''); expect((dialog.querySelector('input[readonly]') as HTMLInputElement).value).toBe(''); fireEvent.click(within(dialog).getBy`
- frontend/src/components/PurchaseAdminEditorButtonMigration.test.tsx:71 `render(wrap(<RolesPage />)); await screen.findAllByText('Role fixture'); const checkbox = await screen.findByRole('checkbox', { name: /View customers/ }) as HTMLInputElement; await waitFor(() => expec`
- frontend/src/components/PurchaseAdminEditorButtonMigration.test.tsx:78 `const name = screen.getByPlaceholderText(tr('superAdmin.dex.fields.nameJa')) as HTMLInputElement; expect(name.value).toBe('Pikachu'); fireEvent.click(screen.getByRole('button', { name: tr('common.canc`
- frontend/src/components/PurchaseAdminEditorButtonMigration.test.tsx:91 `render(wrap(<LLMBudgetTab />)); fireEvent.click(await screen.findByTestId('llm-budget-edit-3')); const form = screen.getByTestId('llm-budget-edit-form'); expect((within(form).getByTestId('llm-budget-i`
- frontend/src/components/PurchaseAdminEditorButtonMigration.test.tsx:96 `fireEvent.click(screen.getByRole('button', { name: tr('common.edit') })); expect((screen.getByPlaceholderText(tr('superAdmin.tcg.fields.seriesCode')) as HTMLInputElement).value).toBe('S5'); expect((sc`
- frontend/src/components/RoleKnowledgeButtonMigration.test.tsx:56 `const inputs = dialog.querySelectorAll<HTMLInputElement>('input');`
- frontend/src/components/RoleKnowledgeButtonMigration.test.tsx:67 `const createColors = [...dialog.querySelectorAll<HTMLInputElement>('input[name="role-color"]')];`
- frontend/src/components/RoleKnowledgeButtonMigration.test.tsx:81 `const editChecked = [...dialog.querySelectorAll<HTMLInputElement>('input[name="role-color"]')].filter(input => input.checked);`
- frontend/src/components/RoleKnowledgeButtonMigration.test.tsx:90 `const palette = [...dialog.querySelectorAll<HTMLInputElement>('input[name="role-color"]')];`
- frontend/src/components/RoleKnowledgeButtonMigration.test.tsx:97 `let checked = [...dialog.querySelectorAll<HTMLInputElement>('input[name="role-color"]')].filter(input => input.checked);`
- frontend/src/components/RoleKnowledgeButtonMigration.test.tsx:103 `const changed = [...dialog.querySelectorAll<HTMLInputElement>('input[name="role-color"]')].find(input => input.value === changedColor)!;`
- frontend/src/components/RoleKnowledgeButtonMigration.test.tsx:104 `fireEvent.click(changed); checked = [...dialog.querySelectorAll<HTMLInputElement>('input[name="role-color"]')].filter(input => input.checked);`
- frontend/src/components/RoleKnowledgeButtonMigration.test.tsx:116 `expect(dialog.querySelector<HTMLInputElement>('input[required]')!.value).toBe(' New role '); fireEvent.click(within(dialog).getByRole('button', { name: label })); await waitFor(() => expect(screen.que`
- frontend/src/components/RoleKnowledgeButtonMigration.test.tsx:139 `dialog = open(); expect(dialog.querySelector<HTMLInputElement>('input[type="number"]')!.value).toBe(''); fireEvent.change(dialog.querySelector('input[type="number"]')!, { target: { value: '88' } }); f`
- frontend/src/components/RoleKnowledgeButtonMigration.test.tsx:144 `fireEvent.click(within(dialog).getByRole('button', { name: tr('common.close') })); dialog = open(); expect(dialog.querySelector<HTMLInputElement>('input[type="number"]')!.value).toBe('');`
- frontend/src/components/RoleKnowledgeButtonMigration.test.tsx:146 `dialog = open(); expect(dialog.querySelector<HTMLInputElement>('input[type="number"]')!.value).toBe('');`
- frontend/src/components/RoleKnowledgeButtonMigration.test.tsx:179 `expect(kind === 'rule' ? dialog.querySelector<HTMLInputElement>('input')!.value : (screen.getByTestId('alias-text-input') as HTMLInputElement).value).toBe(''); fillKnowledge(kind, dialog);`
- frontend/src/components/StaffFormButtonMigration.test.tsx:46 `const target = label.parentElement?.querySelector<HTMLInputElement | HTMLSelectElement>('input,select');`
- frontend/src/components/StaffReportFormButtonMigration.test.tsx:36 `const period = periodLabel.parentElement?.querySelector<HTMLInputElement>('input');`
- frontend/src/components/TeamFormButtonMigration.test.tsx:30 `const input = label.parentElement?.querySelector<HTMLInputElement | HTMLTextAreaElement>('input,textarea');`
- frontend/src/components/TeamFormButtonMigration.test.tsx:135 `else { expect((input as HTMLInputElement).type).toBe('number'); expect((input as HTMLInputElement).min).toBe('1'); }`
- frontend/src/components/TextField.test.tsx:118 `const ref = createRef<HTMLInputElement>();`
- frontend/src/components/TextField.test.tsx:120 `expect(ref.current).toBeInstanceOf(HTMLInputElement);`
- frontend/src/components/TextField.test.tsx:152 `const el = container.querySelector('input') as HTMLInputElement;`
- frontend/src/components/TextField.test.tsx:179 `const el = container.querySelector('input') as HTMLInputElement;`
- frontend/src/components/TextField.test.tsx:194 `const el = container.querySelector('input') as HTMLInputElement;`
- frontend/src/pages/admin/DiscordConfigPage.test.tsx:52 `expect((screen.getByLabelText("Server ID") as HTMLInputElement).value).toBe(GUILD);`

## C. input を持つコンポーネント名を import/言及するテスト（31 本）

| テスト | 言及コンポーネント |
|---|---|
| frontend/src/components/AccountCompanySaveButtonMigration.test.tsx | ProfileSection |
| frontend/src/components/AdminMasterSaveButtonMigration.test.tsx | PurchaseOrdersFormModal, DexTab, TcgSeriesTab |
| frontend/src/components/AllLegacyButtonDynamicMigration.test.tsx | InventoryPage, InvoiceCreatePage, ProductsPage |
| frontend/src/components/AllLegacyButtonOperationMigration.test.tsx | InvoiceDetailPage, LoginPage |
| frontend/src/components/BotFormButtonMigration.test.tsx | BotsPage |
| frontend/src/components/CommerceNavigationButtonMigration.test.tsx | InventoryPage, InvoiceCreatePage, InvoiceDetailPage, ProductEditPage, ProductsPage, QuoteCreatePage |
| frontend/src/components/CommerceSubmitButtonMigration.test.tsx | InvoiceCreatePage, ProductEditPage, QuoteCreatePage |
| frontend/src/components/FedExRateModal.test.tsx | FedExRateModal |
| frontend/src/components/FormActionButtonMigration.test.tsx | BadgesPage, BuddyPage, NotificationsPage, ShiftsPage |
| frontend/src/components/FullPageFormButtonMigration.test.tsx | ContactEditPage |
| frontend/src/components/IntegrationLaunchButtonMigration.test.tsx | CarrierCredentialForm |
| frontend/src/components/LeadFormButtonMigration.test.tsx | LeadEditPage, LeadsPage |
| frontend/src/components/MasterSearchButtonMigration.test.tsx | MasterListEditor |
| frontend/src/components/OrderLeadButtonMigration.test.tsx | LeadsPage |
| frontend/src/components/PageFormButtonMigration.test.tsx | CompaniesPage, ContactsPage |
| frontend/src/components/PurchaseAdminEditorButtonMigration.test.tsx | PurchaseOrdersFormModal, RolesPage, DexTab, LLMBudgetTab, TcgSeriesTab |
| frontend/src/components/RoleKnowledgeButtonMigration.test.tsx | RolesPage, KnowledgeAliasesTab |
| frontend/src/components/SharedButtonMigration.test.tsx | OrderFinancialPanel, PurchaseDetailPanel, ShippingDetailPanel |
| frontend/src/components/StaffFormButtonMigration.test.tsx | StaffEditPage, StaffPage |
| frontend/src/components/StaffReportFormButtonMigration.test.tsx | StaffReportsPage |
| frontend/src/components/TeamFormButtonMigration.test.tsx | TeamsPage |
| frontend/src/features/tcg-analysis-review/ConditionReviewPanel.test.tsx | ItemComparison |
| frontend/src/pages/account-settings/ProfileSectionAvatar.test.tsx | ProfileSection |
| frontend/src/pages/leads/LeadFormFields.test.tsx | CountryCombobox, LeadFormFields |
| frontend/tests-e2e/login.spec.ts | LoginPage |
| frontend/tests-e2e/order-commission.spec.ts | CommissionSettingsPage |
| frontend/tests-e2e/product-edit-tcg-type.spec.ts | ProductEditPage |
| frontend/tests-e2e/quote-create-inventory-search.spec.ts | QuoteCreatePage |
| frontend/tests-e2e/scene1-dashboard.spec.ts | LoginPage |
| frontend/tests-e2e/ui-companies-edit-modal-i18n.spec.ts | CompaniesPage |
| tests/qa-smoke/scene-09.spec.ts | SalesFormMultiSelect |
