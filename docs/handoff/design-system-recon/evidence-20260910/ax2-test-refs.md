# AX-2 テストからの参照（git grep -n、origin/main dfcd31c05）


## 要約（件数は下記 git grep 出力の行数）
- クラス `.inbox-textarea` を直接参照: frontend/tests-e2e の4ファイル計27行（inbox-header-ui-screenshots 3 / send-guard-phase-a 18 / send-guard-screenshots 4 / visual-language/inbox-baseline 2）（inbox-header-ui-screenshots.spec.ts, send-guard-phase-a.spec.ts, send-guard-screenshots.spec.ts, visual-language/inbox-baseline.spec.ts）。src/**/*.test.tsx からは0行。
- クラス `.right-panel-field` / `db-weekly-composer-input` / `schedule-textarea` / `outbound-translation-edit` / `manual-record-textarea` / `pmd-field` / `resize-y` を参照するテストと stories: 0行（上記の全パターン欄が空）。
- 属性経由: `getByPlaceholder(/メッセージを入力/)` で送信欄（InboxMessageThread.tsx:736）を取るもの = tests-e2e の error-scenarios-502-429 / scene4 / scene6 / scene7（いずれも placeholder 文字列）。ダッシュボードは scene1-dashboard.spec.ts:419,480 で `composer.locator("textarea")`（composer = testid `weekly-followup-composer`）。
- `querySelector('textarea')` / `getAllByRole('textbox')` 等で要素種別（TEXTAREA）に依存するもの: 下の「属性・role 経由」欄のとおり（src/components/*ButtonMigration.test.tsx 群が中心）。これらはクラス名に依存せず、`<textarea>` 要素であることと祖先 .form-group（LeadFormButtonMigration.test.tsx:159 の `closest('.form-group')`）に依存する。
- 金型自体の既存テスト: frontend/src/components/Textarea.test.tsx（comp-field__textarea の class 文字列固定）、Textarea.stories.tsx。

対象: frontend/src/**/*.test.tsx / *.test.ts / frontend/tests-e2e / *.stories.tsx。事実のみ。

## パターン: inbox-textarea
```
frontend/tests-e2e/inbox-header-ui-screenshots.spec.ts:55:  await expect(page.locator(".inbox-textarea")).toBeVisible({ timeout: 10_000 });
frontend/tests-e2e/inbox-header-ui-screenshots.spec.ts:85:    await page.locator(".inbox-textarea").fill("こんにちは");
frontend/tests-e2e/inbox-header-ui-screenshots.spec.ts:140:    await page.locator(".inbox-textarea").fill("こんにちは");
frontend/tests-e2e/send-guard-phase-a.spec.ts:50:  await expect(page.locator(".inbox-textarea")).toBeVisible({ timeout: 10_000 });
frontend/tests-e2e/send-guard-phase-a.spec.ts:63:  await expect(page.locator(".inbox-textarea")).toBeVisible({ timeout: 10_000 });
frontend/tests-e2e/send-guard-phase-a.spec.ts:75:  const textarea = page.locator(".inbox-textarea");
frontend/tests-e2e/send-guard-phase-a.spec.ts:103:    await expect(page.locator(".inbox-textarea")).toBeVisible({ timeout: 10_000 });
frontend/tests-e2e/send-guard-phase-a.spec.ts:124:    await expect(page.locator(".inbox-textarea")).toBeVisible({ timeout: 10_000 });
frontend/tests-e2e/send-guard-phase-a.spec.ts:145:    await expect(page.locator(".inbox-textarea")).toBeVisible({ timeout: 10_000 });
frontend/tests-e2e/send-guard-phase-a.spec.ts:173:    await expect(page.locator(".inbox-textarea")).toBeVisible({ timeout: 10_000 });
frontend/tests-e2e/send-guard-phase-a.spec.ts:188:    const textarea = page.locator(".inbox-textarea");
frontend/tests-e2e/send-guard-phase-a.spec.ts:193:      const ta = document.querySelector(".inbox-textarea") as HTMLTextAreaElement;
frontend/tests-e2e/send-guard-phase-a.spec.ts:199:      const ta = document.querySelector(".inbox-textarea") as HTMLTextAreaElement;
frontend/tests-e2e/send-guard-phase-a.spec.ts:212:      const ta = document.querySelector(".inbox-textarea") as HTMLTextAreaElement;
frontend/tests-e2e/send-guard-phase-a.spec.ts:219:    const textarea = page.locator(".inbox-textarea");
frontend/tests-e2e/send-guard-phase-a.spec.ts:292:    await expect(page.locator(".inbox-textarea")).toBeVisible({ timeout: 10_000 });
frontend/tests-e2e/send-guard-phase-a.spec.ts:313:    await expect(page.locator(".inbox-textarea")).toBeVisible({ timeout: 10_000 });
frontend/tests-e2e/send-guard-phase-a.spec.ts:319:    await expect(page.locator(".inbox-textarea")).toHaveValue("こんにちは");
frontend/tests-e2e/send-guard-phase-a.spec.ts:358:    await expect(page.locator(".inbox-textarea")).toBeVisible({ timeout: 10_000 });
frontend/tests-e2e/send-guard-phase-a.spec.ts:367:      await expect(page.locator(".inbox-textarea")).toBeVisible({ timeout: 10_000 });
frontend/tests-e2e/send-guard-phase-a.spec.ts:373:      await expect(page.locator(".inbox-textarea")).toBeVisible({ timeout: 10_000 });
frontend/tests-e2e/send-guard-screenshots.spec.ts:55:  await expect(page.locator(".inbox-textarea")).toBeVisible({ timeout: 10_000 });
frontend/tests-e2e/send-guard-screenshots.spec.ts:70:    const textarea = page.locator(".inbox-textarea");
frontend/tests-e2e/send-guard-screenshots.spec.ts:87:    const textarea = page.locator(".inbox-textarea");
frontend/tests-e2e/send-guard-screenshots.spec.ts:107:    await page.locator(".inbox-textarea").fill("テスト送信です");
frontend/tests-e2e/visual-language/inbox-baseline.spec.ts:63:  await expect(page.locator(".inbox-textarea")).toBeVisible({ timeout: 10_000 });
frontend/tests-e2e/visual-language/inbox-baseline.spec.ts:139:  await expect(page.locator(".inbox-textarea")).toBeVisible({ timeout: 10_000 });
```

## パターン: right-panel-field
```
```

## パターン: db-weekly-composer-input
```
```

## パターン: schedule-textarea
```
```

## パターン: outbound-translation-edit
```
```

## パターン: manual-record-textarea
```
```

## パターン: pmd-field
```
```

## パターン: pmd-fields
```
```

## パターン: resize-y
```
```

## パターン: input w-full
```
```

## パターン: prompt-textarea
```
```

## パターン: pur-input-purchase_note
```
```

## パターン: ship-input-ship_memo
```
```

## パターン: tp-address
```
```

## パターン: priority-action-
```
```

## パターン: weekly-action-
```
```

## パターン: composer
```
frontend/tests-e2e/scene1-dashboard.spec.ts:411:    const composerOpen = page.getByTestId("weekly-followup-open").first();
frontend/tests-e2e/scene1-dashboard.spec.ts:412:    await expect(composerOpen).toBeVisible();
frontend/tests-e2e/scene1-dashboard.spec.ts:413:    await composerOpen.click();
frontend/tests-e2e/scene1-dashboard.spec.ts:415:    const composer = page.getByTestId("weekly-followup-composer");
frontend/tests-e2e/scene1-dashboard.spec.ts:416:    await expect(composer).toBeVisible();
frontend/tests-e2e/scene1-dashboard.spec.ts:419:    const actionField = composer.locator("textarea");
frontend/tests-e2e/scene1-dashboard.spec.ts:478:    const composer = page.getByTestId("priority-followup-composer");
frontend/tests-e2e/scene1-dashboard.spec.ts:479:    await expect(composer).toBeVisible();
frontend/tests-e2e/scene1-dashboard.spec.ts:480:    await composer.locator("textarea").fill("今週中に連絡する");
```

## パターン: karte-field
```
```

## パターン: send-input-wrap
```
```

## パターン: field-h-md
```
```

## パターン: form-group
```
frontend/src/components/LeadFormButtonMigration.test.tsx:159:    if (action === 'clear') { const group = input.closest('.form-group'); if (!group) throw new Error('Missing group'); fireEvent.click(within(group as HTMLElement).getByRole('but
frontend/tests-e2e/super-admin-masters.spec.ts:124:    const textInputs = dialog.locator(".form-group input[type='text'], .form-group input:not([type])");
```

## パターン: form-row
```
frontend/tests-e2e/ui-companies-edit-modal-i18n.spec.ts:95:    // form-row labels の存在確認 (i18n key 経由)
```

## 属性・role 経由（textarea 要素を直接触るもの）
```
frontend/src/components/AccountCompanySaveButtonMigration.test.tsx:39:    fireEvent.change(screen.getByLabelText(tr('accountSettings.surnameJp')), { target: { value: ' New ' } });
frontend/src/components/AccountCompanySaveButtonMigration.test.tsx:40:    fireEvent.change(screen.getByLabelText(tr('accountSettings.givenNameJp')), { target: { value: ' Person ' } });
frontend/src/components/AccountCompanySaveButtonMigration.test.tsx:41:    fireEvent.change(screen.getByLabelText(tr('staff.surnameKana')), { target: { value: ' kana ' } });
frontend/src/components/AccountCompanySaveButtonMigration.test.tsx:42:    fireEvent.change(screen.getByLabelText(tr('staff.givenNameKana')), { target: { value: ' given ' } });
frontend/src/components/AccountCompanySaveButtonMigration.test.tsx:43:    fireEvent.change(screen.getByLabelText(tr('accountSettings.surnameEn') + ' *'), { target: { value: ' Last ' } });
frontend/src/components/AccountCompanySaveButtonMigration.test.tsx:44:    fireEvent.change(screen.getByLabelText(tr('accountSettings.givenNameEn') + ' *'), { target: { value: ' First ' } });
frontend/src/components/AccountCompanySaveButtonMigration.test.tsx:45:    fireEvent.change(screen.getByLabelText(tr('accountSettings.phoneLabel')), { target: { value: '' } });
frontend/src/components/AccountCompanySaveButtonMigration.test.tsx:54:    render(provider(<UiPrefsProvider><ProfileSection /></UiPrefsProvider>)); await screen.findByText('me@example.com'); const surname = screen.getByLabelText(tr('accountSettings.surnameJp'))
frontend/src/components/AccountCompanySaveButtonMigration.test.tsx:60:    renderCompany(); await screen.findByText('Old Co'); const name = screen.getByDisplayValue('Old Co'); const saveInitially = screen.getByRole('button', { name: tr('companies.saveBasicInfo'
frontend/src/components/AccountCompanySaveButtonMigration.test.tsx:61:    const field = (key: string) => screen.getByText(tr(key), { selector: 'label' }).parentElement!.querySelector('input,textarea,select') as HTMLInputElement;
frontend/src/components/AccountCompanySaveButtonMigration.test.tsx:65:    await act(async () => pending.resolve({})); await waitFor(() => expect(mock.get.mock.calls.filter(c => c[0] === '/companies/41')).toHaveLength(companyReads + 1)); expect(mock.get.mock.ca
frontend/src/components/AccountCompanySaveButtonMigration.test.tsx:69:    renderCompany(); await screen.findByText('Old Co'); const name = screen.getByDisplayValue('Old Co') as HTMLInputElement; fireEvent.change(name, { target: { value: 'Retained Co' } }); moc
frontend/src/components/AccountCompanySaveButtonMigration.test.tsx:77:    const failedPayload = mock.patch.mock.calls[0]; const contactReads = mock.get.mock.calls.filter(c => c[0] === '/companies/41/contacts').length; const pending = deferred(); mock.patch.moc
frontend/src/components/AdminMasterSaveButtonMigration.test.tsx:29:    const events: string[] = [], pending = deferred(); mock.post.mockReturnValue(pending.promise); render(wrap(<PurchaseOrdersFormModal open onCreated={() => events.push('created')} onClose={()
frontend/src/components/AdminMasterSaveButtonMigration.test.tsx:36:    cleanup(); const events: string[] = []; mock.post.mockRejectedValueOnce(new Error('PO failed')).mockResolvedValueOnce({}); render(wrap(<PurchaseOrdersFormModal open onCreated={() => events.
frontend/src/components/AdminMasterSaveButtonMigration.test.tsx:40:    render(wrap(<DexTab />)); await screen.findAllByText('Pikachu'); fireEvent.click(screen.getAllByRole('button', { name: tr('common.edit') })[0]); const name = screen.getByPlaceholderText(tr(
frontend/src/components/AdminMasterSaveButtonMigration.test.tsx:49:    render(wrap(<DexTab />)); await screen.findAllByText('Pikachu'); fireEvent.change(screen.getByRole('combobox'), { target: { value: 'trainer' } }); await screen.findAllByText('Trainer'); fir
frontend/src/components/AdminMasterSaveButtonMigration.test.tsx:54:    expect(typeInputs[0].value).toBe(''); expect(typeInputs[1].value).toBe(''); fireEvent.click(screen.getByRole('button', { name: tr('common.edit') })); const code = screen.getByPlaceholderTex
frontend/src/components/AdminMasterSaveButtonMigration.test.tsx:58:    render(wrap(<TcgSeriesTab />)); await screen.findByText('Series fixture'); fireEvent.click(screen.getByRole('button', { name: tr('common.edit') })); const code = screen.getByPlaceholderText
frontend/src/components/AdminMasterSaveButtonMigration.test.tsx:59:    const first = deferred(), second = deferred(); mock.patch.mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise); const save = screen.getByRole('button', { name: tr('common.
frontend/src/components/AdminMasterSaveButtonMigration.test.tsx:63:    render(wrap(<TcgSeriesTab />)); await screen.findByText('Series fixture'); const newSeries = screen.getByRole('button', { name: tr('superAdmin.tcg.newSeries') }); fireEvent.click(newSeries)
frontend/src/components/AllLegacyButtonOperationMigration.test.tsx:43:    fireEvent.change(screen.getByLabelText(String(instance.t('login.email'))), { target: { value: 'person@example.com' } });
frontend/src/components/AllLegacyButtonOperationMigration.test.tsx:44:    fireEvent.change(screen.getByLabelText(String(instance.t('login.password'))), { target: { value: 'secret' } });
frontend/src/components/AllLegacyButtonOperationMigration.test.tsx:56:    fireEvent.change(screen.getByLabelText(String(instance.t('login.email'))), { target: { value: 'missing@example.com' } });
frontend/src/components/CommerceNavigationButtonMigration.test.tsx:100:    expect(screen.getByPlaceholderText(tr('invoices.voidReasonPlaceholder'))).toBeTruthy();
frontend/src/components/CommerceSubmitButtonMigration.test.tsx:43:  const controls = Array.from(form.querySelectorAll<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>('input, select, textarea'));
frontend/src/components/CommerceSubmitButtonMigration.test.tsx:148:    const form = screen.getByTestId('product-edit-form'); const controls = Array.from(form.querySelectorAll<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>('input, select, textarea'
frontend/src/components/FedExRateModal.test.tsx:73:    expect(screen.getByLabelText("Destination country code")).toBeTruthy();
frontend/src/components/FedExRateModal.test.tsx:78:    const input = screen.getByDisplayValue("US") as HTMLInputElement;
frontend/src/components/FedExRateModal.test.tsx:124:    const input = screen.getByLabelText("Weight (kg)") as HTMLInputElement;
frontend/src/components/FedExRateModal.test.tsx:134:    const weightInput = screen.getByLabelText("Weight (kg)");
frontend/src/components/FormActionButtonMigration.test.tsx:35:  const textareas = Array.from(dialog.querySelectorAll<HTMLTextAreaElement>('textarea'));
frontend/src/components/FormActionButtonMigration.test.tsx:55:function values(dialog: HTMLElement) { return Array.from(dialog.querySelectorAll<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>('input,textarea,select')).map(x => x.value); }
frontend/src/components/FormActionButtonMigration.test.tsx:100:    const values = Array.from(reopened.dialog.querySelectorAll<HTMLInputElement | HTMLTextAreaElement>('input,textarea')).map(x => x.value);
frontend/src/components/FullPageFormButtonMigration.test.tsx:34:  const input = node.parentElement?.querySelector<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>('input,select,textarea');
frontend/src/components/IntegrationLaunchButtonMigration.test.tsx:39:    fireEvent.change(screen.getByLabelText(tr('carrierIntegration.labelFedExApiKey')), { target: { value: 'id' } });
frontend/src/components/IntegrationLaunchButtonMigration.test.tsx:40:    fireEvent.change(screen.getByLabelText(tr('carrierIntegration.labelFedExSecretKey')), { target: { value: 'secret' } });
frontend/src/components/IntegrationLaunchButtonMigration.test.tsx:81:    fireEvent.change(screen.getByLabelText(tr('carrierIntegration.labelFedExApiKey')), { target: { value: 'id' } });
frontend/src/components/IntegrationLaunchButtonMigration.test.tsx:82:    fireEvent.change(screen.getByLabelText(tr('carrierIntegration.labelFedExSecretKey')), { target: { value: 'secret' } });
frontend/src/components/LeadFormButtonMigration.test.tsx:33:  const input = label.parentElement?.querySelector<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>('input,textarea,select');
frontend/src/components/MasterSearchButtonMigration.test.tsx:69:    const field = screen.getByPlaceholderText(tr('superAdmin.attrMasters.searchPlaceholder')) as HTMLInputElement;
frontend/src/components/MasterSearchButtonMigration.test.tsx:85:    const ja = screen.getByLabelText(tr('superAdmin.attrMasters.col.labelJa')) as HTMLInputElement;
frontend/src/components/MasterSearchButtonMigration.test.tsx:86:    const enField = screen.getByLabelText(tr('superAdmin.attrMasters.col.labelEn')) as HTMLInputElement;
frontend/src/components/MasterSearchButtonMigration.test.tsx:104:    const ja = screen.getByLabelText(tr('superAdmin.attrMasters.col.labelJa')) as HTMLInputElement;
frontend/src/components/MasterSearchButtonMigration.test.tsx:116:    const ja = screen.getByLabelText(tr('superAdmin.attrMasters.col.labelJa')) as HTMLInputElement; fireEvent.change(ja, { target: { value: ' Pending ' } });
frontend/src/components/OrderLeadButtonMigration.test.tsx:55:    fireEvent.change(dialog.querySelector('textarea')!, { target: { value: ' note ' } });
frontend/src/components/PageFormButtonMigration.test.tsx:28:  const input = node.parentElement?.querySelector<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>('input,select,textarea');
frontend/src/components/PurchaseAdminEditorButtonMigration.test.tsx:63:    expect((dialog.querySelector('select') as HTMLSelectElement).value).toBe('7'); expect((within(dialog).getByDisplayValue('Inventory product') as HTMLInputElement).value).toBe('Inventory 
frontend/src/components/PurchaseAdminEditorButtonMigration.test.tsx:78:    const name = screen.getByPlaceholderText(tr('superAdmin.dex.fields.nameJa')) as HTMLInputElement; expect(name.value).toBe('Pikachu'); fireEvent.click(screen.getByRole('button', { name: 
frontend/src/components/PurchaseAdminEditorButtonMigration.test.tsx:79:    const search = screen.getByPlaceholderText(tr('common.search')); fireEvent.change(search, { target: { value: 'target' } }); const before = mock.get.mock.calls.length; fireEvent.click(sc
frontend/src/components/PurchaseAdminEditorButtonMigration.test.tsx:84:    render(wrap(<DexTab />)); await screen.findAllByText('Pikachu'); const search = screen.getByPlaceholderText(tr('common.search')); fireEvent.change(search, { target: { value: 'retry' } }
frontend/src/components/PurchaseAdminEditorButtonMigration.test.tsx:96:    fireEvent.click(screen.getByRole('button', { name: tr('common.edit') })); expect((screen.getByPlaceholderText(tr('superAdmin.tcg.fields.seriesCode')) as HTMLInputElement).value).toBe('S
frontend/src/components/RoleKnowledgeButtonMigration.test.tsx:45:  fireEvent.change(dialog.querySelector('textarea')!, { target: { value: ' desc ' } });
frontend/src/components/SharedButtonMigration.test.tsx:82:    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'manual note' } });
frontend/src/components/StaffReportFormButtonMigration.test.tsx:38:  const textareas = within(dialog).getAllByRole('textbox').filter(node => node.tagName === 'TEXTAREA') as HTMLTextAreaElement[];
frontend/src/components/TeamFormButtonMigration.test.tsx:30:  const input = label.parentElement?.querySelector<HTMLInputElement | HTMLTextAreaElement>('input,textarea');
frontend/src/components/TeamFormButtonMigration.test.tsx:140:    expect(input).toBeInstanceOf(HTMLTextAreaElement); await user.click(input); await user.keyboard('Line one{Enter}Line two');
frontend/src/components/Textarea.test.tsx:92:    const cls = () => container.querySelector('textarea')?.className;
frontend/src/components/Textarea.test.tsx:105:    const ref = createRef<HTMLTextAreaElement>();
frontend/src/components/Textarea.test.tsx:107:    expect(ref.current).toBeInstanceOf(HTMLTextAreaElement);
frontend/src/components/Textarea.test.tsx:108:    expect(ref.current).toBe(container.querySelector('textarea'));
frontend/src/components/Textarea.test.tsx:114:    expect(ref).toHaveBeenCalledWith(container.querySelector('textarea'));
frontend/src/components/Textarea.test.tsx:132:    const el = container.querySelector('textarea') as HTMLTextAreaElement;
frontend/src/components/Textarea.test.tsx:154:    const el = container.querySelector('textarea') as HTMLTextAreaElement;
frontend/src/components/Textarea.test.tsx:169:    const el = container.querySelector('textarea') as HTMLTextAreaElement;
frontend/src/components/Textarea.test.tsx:178:    expect(container.querySelector('textarea')?.getAttribute('id')).toBe('abc');
frontend/src/features/tcg-product-import/TcgProductImportPanel.test.tsx:14:  fireEvent.change(screen.getByLabelText("CSV file"), { target: { files: [sample()] } });
frontend/src/features/tcg-product-import/TcgProductImportPanel.test.tsx:46:  if (status < 500) expect(screen.getByLabelText("CSV file")).toBeTruthy();
frontend/src/features/tcg-product-import/TcgProductImportPanel.test.tsx:96:      fireEvent.change(screen.getByLabelText("CSV file"), { target: { files: [file] } });
frontend/src/features/tcg-product-import/TcgProductImportPanel.test.tsx:117:    fireEvent.change(screen.getByLabelText("CSV file"), { target: { files: [sample()] } });
frontend/src/features/tcg-product-import/TcgProductImportPanel.test.tsx:146:    fireEvent.change(screen.getByLabelText("CSV file"), { target: { files: [selected] } });
frontend/src/features/tcg-product-import/TcgProductImportPanel.test.tsx:163:    fireEvent.change(screen.getByLabelText("CSV file"), { target: { files: [new File(["x"], "a.txt")] } });
frontend/src/features/tcg-product-import/TcgProductImportPanel.test.tsx:175:    fireEvent.change(screen.getByLabelText("CSV file"), { target: { files: [sample()] } });
frontend/src/pages/account-settings/ProfileSectionAvatar.test.tsx:101:    expect(screen.getByLabelText(`${tr('accountSettings.surnameEn')} *`).getAttribute('aria-required')).toBe('true');
frontend/src/pages/account-settings/ProfileSectionAvatar.test.tsx:102:    expect(screen.getByLabelText(`${tr('accountSettings.givenNameEn')} *`).getAttribute('aria-required')).toBe('true');
frontend/src/pages/account-settings/ProfileSectionAvatar.test.tsx:107:    fireEvent.change(screen.getByLabelText(`${tr(`accountSettings.${field}`)} *`), { target: { value: '  ' } });
frontend/src/pages/admin/DiscordConfigPage.test.tsx:52:  expect((screen.getByLabelText("Server ID") as HTMLInputElement).value).toBe(GUILD);
frontend/src/pages/admin/DiscordConfigPage.test.tsx:60:  expect(screen.getByLabelText("Server ID")).toBeTruthy();
frontend/src/pages/admin/DiscordConfigPage.test.tsx:133:    expect(screen.getByLabelText(label)).toBeTruthy();
frontend/src/pages/inbox/InboxMessageThread.discordSendError.test.tsx:131:    expect((screen.getByDisplayValue("入力中の文") as HTMLTextAreaElement).value).toBe("入力中の文");
frontend/src/pages/leads/LeadFormFields.test.tsx:69:    const select = screen.getByLabelText("leads.lostReasonCode");
frontend/src/pages/leads/LeadFormFields.test.tsx:73:    const memo = screen.getByLabelText("leads.lostReason");
frontend/src/pages/super-admin/TcgProductMasterPage.test.tsx:30:  fireEvent.change(screen.getByLabelText("Search by name, model number or product ID"), { target: { value: "A & B" } });
frontend/src/pages/super-admin/TcgProductMasterPage.test.tsx:61:  fireEvent.change(screen.getByLabelText("Search by name, model number or product ID"), { target: { value: "A & B" } });
frontend/src/pages/super-admin/TcgProductMasterPage.test.tsx:67:  fireEvent.change(screen.getByLabelText("Search by name, model number or product ID"), { target: { value: "new" } });
frontend/src/pages/super-admin/TcgProductMasterPage.test.tsx:81:  fireEvent.change(screen.getByLabelText("Search by name, model number or product ID"), { target: { value: "Shared" } });
frontend/src/pages/super-admin/TcgProductMasterPage.test.tsx:154:  fireEvent.change(screen.getByLabelText("Search by name, model number or product ID"), { target: { value: "absent" } });
frontend/src/pages/super-admin/TcgSoldOutPage.test.tsx:54:  fireEvent.change(screen.getByLabelText("Search product or supplier name"), { target: { value: "  %_\\  " } });
frontend/src/pages/super-admin/TcgSoldOutPage.test.tsx:59:  fireEvent.change(screen.getByLabelText("Source scope"), { target: { value: "history" } });
frontend/src/pages/super-admin/TcgSoldOutPage.test.tsx:66:  fireEvent.change(screen.getByLabelText("Search product or supplier name"), { target: { value: "new" } });
frontend/src/pages/super-admin/components/ShadowAccuracyPanel.test.tsx:148:  fireEvent.change(screen.getByLabelText("Period"), { target: { value: "0" } });
frontend/src/pages/super-admin/components/ShadowAccuracyPanel.test.tsx:155:  fireEvent.change(screen.getByLabelText("Supplier"), { target: { value: "5" } });
frontend/src/pages/super-admin/components/ShadowAccuracyPanel.test.tsx:157:  expect(within(screen.getByLabelText("Supplier")).getByText("Supplier A")).toBeTruthy();
frontend/src/pages/super-admin/components/ShadowAccuracyPanel.test.tsx:167:  expect((screen.getByLabelText("Signal") as HTMLSelectElement).value).toBe("S4");
frontend/src/pages/super-admin/components/UnitIgnorePhrasesPanel.test.tsx:45:  fireEvent.change(screen.getByLabelText(/Reason/), { target: { value: "why" } });
frontend/tests-e2e/error-scenarios-502-429.spec.ts:112:    const textarea = page.getByPlaceholder(/メッセージを入力/);
frontend/tests-e2e/error-scenarios-502-429.spec.ts:147:    const textarea = page.getByPlaceholder(/メッセージを入力/);
frontend/tests-e2e/scene1-dashboard.spec.ts:419:    const actionField = composer.locator("textarea");
frontend/tests-e2e/scene1-dashboard.spec.ts:480:    await composer.locator("textarea").fill("今週中に連絡する");
frontend/tests-e2e/scene3-receive-messenger.spec.ts:85:      page.getByPlaceholder(/メッセージを入力/),
frontend/tests-e2e/scene4-reply-messenger.spec.ts:80:    const textarea = page.getByPlaceholder(/メッセージを入力/);
frontend/tests-e2e/scene6-instagram-dm.spec.ts:101:    const textarea = page.getByPlaceholder(/メッセージを入力/);
frontend/tests-e2e/scene7-human-agent-tag.spec.ts:41:    const textarea = page.getByPlaceholder(/メッセージを入力/);
frontend/tests-e2e/scene7-human-agent-tag.spec.ts:94:    const textarea = page.getByPlaceholder(/メッセージを入力/);
frontend/tests-e2e/scene7-human-agent-tag.spec.ts:132:    const textarea = page.getByPlaceholder(/メッセージを入力/);
frontend/tests-e2e/send-guard-phase-a.spec.ts:193:      const ta = document.querySelector(".inbox-textarea") as HTMLTextAreaElement;
frontend/tests-e2e/send-guard-phase-a.spec.ts:199:      const ta = document.querySelector(".inbox-textarea") as HTMLTextAreaElement;
frontend/tests-e2e/send-guard-phase-a.spec.ts:212:      const ta = document.querySelector(".inbox-textarea") as HTMLTextAreaElement;
frontend/tests-e2e/tcg-product-detail.spec.ts:70:      await expect(dialog.getByRole("textbox", { name: locale === "ja" ? "日本語名" : "Japanese name", exact: true })).toHaveValue(product.japanese_title);
frontend/tests-e2e/tcg-product-detail.spec.ts:97:    await dialog.getByRole("textbox", { name: "日本語名", exact: true }).fill("未保存の商品名");
frontend/tests-e2e/tcg-product-detail.spec.ts:106:    await expect(dialog.getByRole("textbox", { name: "日本語名", exact: true })).toHaveValue("未保存の商品名");
frontend/tests-e2e/tcg-product-detail.spec.ts:110:    await expect(dialog.getByRole("textbox", { name: "日本語名", exact: true })).toHaveValue(product.japanese_title);
frontend/tests-e2e/tcg-product-detail.spec.ts:120:    await dialog.getByRole("textbox", { name: "日本語名", exact: true }).fill("保持する入力");
frontend/tests-e2e/tcg-product-detail.spec.ts:123:    await expect(dialog.getByRole("textbox", { name: "日本語名", exact: true })).toHaveValue("保持する入力");
frontend/tests-e2e/tcg-product-detail.spec.ts:129:      await expect(dialog.getByRole("textbox", { name: "日本語名", exact: true })).toHaveValue("保持する入力");
frontend/tests-e2e/tcg-product-detail.spec.ts:141:  await expect(dialog.getByRole("textbox", { name: "日本語名", exact: true })).toHaveValue(product.japanese_title);
```
