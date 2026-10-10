# 非 text input の祖先連鎖と競合規則クラス（字面ベース）

手法: frontend/src の非テスト TSX（277 ファイル）の JSX を TypeScript AST で走査し、type が checkbox/radio/range/file の <input> ごとに、同一ファイル内の JSX 祖先の className に form-group があるか、競合規則（nontext-competing-rules.md の範囲内規則）の祖先クラスがあるかを判定。部品経由（別ファイルから描画される場合）は字面では分からないため、ay2b-unresolved-trace.md（描画元の全洗い）と、nontext-after.md の網羅 fixture（競合クラス × .form-group の全組み合わせ）で補う。

## 競合規則の祖先クラス

| class | 規則 |
|---|---|
| search-bar | frontend/src/components.css:56 `.search-bar input` |
| toggle-switch | frontend/src/components.css:727 `.toggle-switch input`<br>frontend/src/pages/account-settings/account-settings.css:111 `.toggle-switch input` |
| source-search | frontend/src/features/tcg-analysis-review/source-raw-pane.css:48 `.source-search input` |
| pmd-field | frontend/src/features/tcg-analysis-review/supplier-detail-view.css:244 `.pmd-field input` |
| inbox-toggle | frontend/src/pages/inbox/InboxPage.css:1410 `.inbox-toggle input` |
| topbar-search | frontend/src/topbar.css:44 `.topbar-search input`<br>frontend/src/topbar.css:54 `.topbar-search input::placeholder` |
| color-swatch | frontend/src/pages-layout.css:340 `.color-swatch input[type="radio"]` |
| chk-label | frontend/src/pages-layout.css:595 `.chk-label input[type="checkbox"]` |
| permission-item | frontend/src/pages-layout.css:619 `.permission-item input[type="checkbox"]` |
| sales-form-option | frontend/src/pages/inbox/InboxPage.css:1619 `.sales-form-option input[type="checkbox"]` |
| form-grid | frontend/src/company-forms.css:113 `.form-grid > .form-row input:focus` |
| form-row | frontend/src/company-forms.css:113 `.form-grid > .form-row input:focus`<br>frontend/src/company-forms.css:163 `.modal-content .form-row input:focus`<br>frontend/src/company-forms.css:163 `.modal-content-wide .form-row input:focus` |
| modal-content | frontend/src/company-forms.css:163 `.modal-content .form-row input:focus` |
| modal-content-wide | frontend/src/company-forms.css:163 `.modal-content-wide .form-row input:focus` |

## 非 text input 全件（字面で .form-group の内側にあるもの、または競合クラスが祖先にあるもの）

| file:line | type | 字面上 .form-group の内側 | 祖先にある競合クラス | 祖先連鎖（近い6段） |
|---|---|---|---|---|
| frontend/src/components/ContactChannelForm.tsx:227 | checkbox | いいえ | form-grid, form-row | Modal > form > div["form-grid"] > div["form-row"] > label |
| frontend/src/components/MergeCompanyModal.tsx:220 | radio | いいえ | modal-content-wide | div["modal-content-wide"] > div > table["data-table"] > tbody > tr > td |
| frontend/src/components/MergeContactModal.tsx:219 | radio | いいえ | modal-content-wide | div["modal-content-wide"] > div > table["data-table"] > tbody > tr > td |
| frontend/src/components/MergeLeadModal.tsx:209 | radio | いいえ | modal-content-wide | div["modal-content-wide"] > div > table["data-table"] > tbody > tr > td |
| frontend/src/components/PriorityScoreOverride.tsx:81 | range | はい | - | Modal > form > div["form-group"] |
| frontend/src/pages/account-settings/PreferencesSection.tsx:25 | checkbox | いいえ | toggle-switch | section["account-settings-section"] > div["account-settings-pref-row"] > label["toggle-switch"] |
| frontend/src/pages/company-detail/CompanyAddressModal.tsx:147 | checkbox | いいえ | form-grid, form-row, modal-content-wide | Modal > div["modal-content-wide"] > form["form-grid"] > div["form-row"] > label |
| frontend/src/pages/company-detail/CompanyContactsTab.tsx:206 | checkbox | いいえ | form-grid, form-row | div > Modal > form > div["form-grid"] > div["form-row"] > label |
| frontend/src/pages/company-detail/CompanyDiscordTab.tsx:42 | checkbox | いいえ | form-grid, form-row | div > form > div["form-grid"] > div["form-row"] > label |
| frontend/src/pages/contacts/ContactEditPage.tsx:171 | checkbox | はい | - | PageLayout > form > div["form-group"] > label |
| frontend/src/pages/contacts/ContactsPage.tsx:332 | checkbox | いいえ | form-grid, form-row, modal-content-wide | PageLayout > Modal > div["modal-content-wide"] > form["form-grid"] > div["form-row"] > label |
| frontend/src/pages/inbox/InboxSettingsModal.tsx:30 | checkbox | いいえ | toggle-switch | Modal > div["inbox-settings-row"] > label["toggle-switch"] |
| frontend/src/pages/inbox/InboxSettingsModal.tsx:53 | checkbox | いいえ | toggle-switch | Modal > div["inbox-settings-row"] > label["toggle-switch"] |
| frontend/src/pages/inbox/InboxSettingsModal.tsx:66 | checkbox | いいえ | toggle-switch | Modal > div["inbox-settings-row"] > label["toggle-switch"] |
| frontend/src/pages/inbox/InboxSettingsModal.tsx:84 | checkbox | いいえ | toggle-switch | Modal > div["inbox-settings-row"] > label["toggle-switch"] |
| frontend/src/pages/inbox/SalesFormMultiSelect.tsx:134 | checkbox | いいえ | sales-form-option | div["sales-form-multi-select"] > div["sales-form-dropdown"] > label[{`sales-form-option${checked ? " sales-form-option--checked"] |
| frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:509 | file | はい | - | section["etd-guide"] > StepCard > div["etd-upload"] > div["etd-upload__grid"] > div["form-group"] |
| frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:538 | file | はい | - | section["etd-guide"] > StepCard > div["etd-upload"] > div["etd-upload__grid"] > div["form-group"] |
| frontend/src/pages/roles/RolesPage.tsx:432 | checkbox | いいえ | chk-label | main["roles-main"] > div["permission-groups"] > section["permission-group"] > header["permission-group-header"] > div["permission-group-toggles"] > label["chk-label"] |
| frontend/src/pages/roles/RolesPage.tsx:442 | checkbox | いいえ | chk-label | main["roles-main"] > div["permission-groups"] > section["permission-group"] > header["permission-group-header"] > div["permission-group-toggles"] > label["chk-label"] |
| frontend/src/pages/roles/RolesPage.tsx:456 | checkbox | いいえ | permission-item | div["roles-layout"] > main["roles-main"] > div["permission-groups"] > section["permission-group"] > div["permission-group-body"] > label["permission-item"] |
| frontend/src/pages/roles/RolesPage.tsx:506 | radio | はい | color-swatch | div["page roles-page"] > Modal > form > div["form-group"] > div["color-picker"] > label["color-swatch selected color-swatch-legacy"] |
| frontend/src/pages/roles/RolesPage.tsx:522 | radio | はい | color-swatch | div["page roles-page"] > Modal > form > div["form-group"] > div["color-picker"] > label[{`color-swatch ${roleForm.color === c ? "selected" : ""}`}] |
| frontend/src/pages/roles/RolesPage.tsx:562 | checkbox | はい | - | div["page roles-page"] > Modal > div["form-group"] > label |
| frontend/src/pages/schedule/SchedulePageImpl.tsx:308 | checkbox | いいえ | toggle-switch | div["schedule-popover"] > div["schedule-popover__body schedule-popover__body--form"] > div["schedule-field schedule-field--inline"] > label["toggle-switch"] |
| frontend/src/pages/schedule/ScheduleSettingsPage.tsx:164 | checkbox | いいえ | toggle-switch | div["schedule-settings__content"] > section["schedule-settings__card schedule-settings__section-anchor"] > div["schedule-settings__card-body"] > div["schedule-settings__calendar-row"] > div["schedule-settings__calendar-actions"] > label["toggle-switch"] |
| frontend/src/pages/schedule/ScheduleSettingsPage.tsx:220 | checkbox | いいえ | toggle-switch | div["schedule-settings__content"] > section["schedule-settings__card schedule-settings__section-anchor"] > div["schedule-settings__card-body"] > div["schedule-settings__calendar-row"] > div["schedule-settings__calendar-actions"] > label["toggle-switch"] |
| frontend/src/pages/staff/StaffEditPage.tsx:220 | checkbox | はい | - | PageLayout > form > div["form-group"] > label |
| frontend/src/pages/staff/StaffPage.tsx:293 | checkbox | はい | - | PageLayout > Modal > form > div["form-group"] > label |

非 text input 全 86 件のうち、字面で .form-group の内側: 9 件、競合クラスが祖先: 22 件、両方: 2 件。
