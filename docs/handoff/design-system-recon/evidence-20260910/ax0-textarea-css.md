<!-- rules: 34 ; raw textareas matched by >=1 rule (approx): 49 of 54 -->
# av2-css-rules (origin/main; selectors containing "textarea" OR a class that is the own className of a raw textarea)

Match counts are APPROXIMATE: last compound must match own className tokens (or element textarea), preceding compounds must appear among the className tokens of up to 3 JSX ancestors (own file only; descendant combinator treated as ancestor-in-3). Rules reached through classes set at runtime/other files are not counted. Dynamic className expressions are tokenized by regex.

### frontend/src/company-forms.css:100
```css
.form-grid > .form-row input:not([type="checkbox"]):not([type="radio"]),
.form-grid > .form-row textarea {
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-md);
  font-size: var(--font-base);
  background: var(--bg-surface);
  color: var(--text-primary);
  width: 100%;
  box-sizing: border-box;
  font-family: inherit;
}
```
approx matching raw textareas: 5 -> frontend/src/pages/companies/CompaniesPage.tsx:499, frontend/src/pages/companies/CompaniesPage.tsx:516, frontend/src/pages/company-detail/CompanyBasicTab.tsx:81, frontend/src/pages/company-detail/CompanyBasicTab.tsx:94, frontend/src/pages/contacts/ContactsPage.tsx:349

### frontend/src/company-forms.css:113
```css
.form-grid > .form-row textarea {
  min-height: var(--textarea-min-h);
  resize: vertical;
}
```
approx matching raw textareas: 5 -> frontend/src/pages/companies/CompaniesPage.tsx:499, frontend/src/pages/companies/CompaniesPage.tsx:516, frontend/src/pages/company-detail/CompanyBasicTab.tsx:81, frontend/src/pages/company-detail/CompanyBasicTab.tsx:94, frontend/src/pages/contacts/ContactsPage.tsx:349

### frontend/src/company-forms.css:119
```css
.form-grid > .form-row input:focus,
.form-grid > .form-row textarea:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: var(--focus-ring-shadow);
}
```
approx matching raw textareas: 5 -> frontend/src/pages/companies/CompaniesPage.tsx:499, frontend/src/pages/companies/CompaniesPage.tsx:516, frontend/src/pages/company-detail/CompanyBasicTab.tsx:81, frontend/src/pages/company-detail/CompanyBasicTab.tsx:94, frontend/src/pages/contacts/ContactsPage.tsx:349

### frontend/src/company-forms.css:154
```css
.modal-content .form-row input:not([type="checkbox"]):not([type="radio"]),
.modal-content .form-row textarea,
.modal-content-wide .form-row input:not([type="checkbox"]):not([type="radio"]),
.modal-content-wide .form-row textarea {
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-md);
  font-size: var(--font-base);
  background: var(--bg-surface);
  color: var(--text-primary);
  width: 100%;
  box-sizing: border-box;
  font-family: inherit;
}
```
approx matching raw textareas: 4 -> frontend/src/components/MergeLeadModal.tsx:234, frontend/src/pages/companies/CompaniesPage.tsx:499, frontend/src/pages/companies/CompaniesPage.tsx:516, frontend/src/pages/contacts/ContactsPage.tsx:349

### frontend/src/company-forms.css:169
```css
.modal-content .form-row textarea,
.modal-content-wide .form-row textarea {
  min-height: var(--textarea-min-h);
  resize: vertical;
}
```
approx matching raw textareas: 4 -> frontend/src/components/MergeLeadModal.tsx:234, frontend/src/pages/companies/CompaniesPage.tsx:499, frontend/src/pages/companies/CompaniesPage.tsx:516, frontend/src/pages/contacts/ContactsPage.tsx:349

### frontend/src/company-forms.css:177
```css
.modal-content .form-row input:focus,
.modal-content .form-row textarea:focus,
.modal-content-wide .form-row input:focus,
.modal-content-wide .form-row textarea:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: var(--focus-ring-shadow);
}
```
approx matching raw textareas: 4 -> frontend/src/components/MergeLeadModal.tsx:234, frontend/src/pages/companies/CompaniesPage.tsx:499, frontend/src/pages/companies/CompaniesPage.tsx:516, frontend/src/pages/contacts/ContactsPage.tsx:349

### frontend/src/company-forms.css:254
```css
.product-edit-form .form-group input:not([type="checkbox"]):not([type="radio"]),
.product-edit-form .form-group textarea {
  border: 1px solid var(--border-strong);
}
```
approx matching raw textareas: 1 -> frontend/src/pages/products/ProductEditPage.tsx:309

### frontend/src/components.css:19
```css
.form-group input,
.form-group textarea {
  width: 100%;
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-size: var(--font-base);
  color: var(--text-primary);
  background: var(--bg-surface);
  box-sizing: border-box;
}
```
approx matching raw textareas: 27 -> frontend/src/components/OrderFinancialPanel.tsx:239, frontend/src/components/PriorityScoreOverride.tsx:91, frontend/src/components/PurchaseDetailPanel.tsx:442, frontend/src/components/ShippingDetailPanel.tsx:551, frontend/src/pages/admin/TenantProfilePage.tsx:170, frontend/src/pages/badges/BadgesPage.tsx:62, frontend/src/pages/buddy/BuddyPage.tsx:66, frontend/src/pages/companies/CompanyFormFields.tsx:64, frontend/src/pages/conditions/ConditionsPage.tsx:340, frontend/src/pages/conditions/ConditionsPage.tsx:350, frontend/src/pages/contacts/ContactEditPage.tsx:191, frontend/src/pages/leads/LeadEditPage.tsx:279, frontend/src/pages/leads/LeadFormFields.tsx:84, frontend/src/pages/leads/LeadFormFields.tsx:153, frontend/src/pages/leads/LeadsPage.tsx:429, frontend/src/pages/orders/OrdersFormModal.tsx:95, frontend/src/pages/products/ProductEditPage.tsx:309, frontend/src/pages/purchase-orders/PurchaseOrdersFormModal.tsx:217, frontend/src/pages/roles/RolesPage.tsx:538, frontend/src/pages/staff-reports/StaffReportsPage.tsx:90, frontend/src/pages/staff-reports/StaffReportsPage.tsx:91, frontend/src/pages/staff-reports/StaffReportsPage.tsx:92, frontend/src/pages/super-admin/components/ConditionsMasterPanel.tsx:367, frontend/src/pages/super-admin/components/ConditionsMasterPanel.tsx:380, frontend/src/pages/suppliers/SupplierFormFields.tsx:61, frontend/src/pages/suppliers/SupplierFormFields.tsx:68, frontend/src/pages/teams/TeamFormFields.tsx:44

### frontend/src/components.css:31
```css
.form-group input:focus,
.form-group textarea:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: var(--focus-ring-shadow);
}
```
approx matching raw textareas: 27 -> frontend/src/components/OrderFinancialPanel.tsx:239, frontend/src/components/PriorityScoreOverride.tsx:91, frontend/src/components/PurchaseDetailPanel.tsx:442, frontend/src/components/ShippingDetailPanel.tsx:551, frontend/src/pages/admin/TenantProfilePage.tsx:170, frontend/src/pages/badges/BadgesPage.tsx:62, frontend/src/pages/buddy/BuddyPage.tsx:66, frontend/src/pages/companies/CompanyFormFields.tsx:64, frontend/src/pages/conditions/ConditionsPage.tsx:340, frontend/src/pages/conditions/ConditionsPage.tsx:350, frontend/src/pages/contacts/ContactEditPage.tsx:191, frontend/src/pages/leads/LeadEditPage.tsx:279, frontend/src/pages/leads/LeadFormFields.tsx:84, frontend/src/pages/leads/LeadFormFields.tsx:153, frontend/src/pages/leads/LeadsPage.tsx:429, frontend/src/pages/orders/OrdersFormModal.tsx:95, frontend/src/pages/products/ProductEditPage.tsx:309, frontend/src/pages/purchase-orders/PurchaseOrdersFormModal.tsx:217, frontend/src/pages/roles/RolesPage.tsx:538, frontend/src/pages/staff-reports/StaffReportsPage.tsx:90, frontend/src/pages/staff-reports/StaffReportsPage.tsx:91, frontend/src/pages/staff-reports/StaffReportsPage.tsx:92, frontend/src/pages/super-admin/components/ConditionsMasterPanel.tsx:367, frontend/src/pages/super-admin/components/ConditionsMasterPanel.tsx:380, frontend/src/pages/suppliers/SupplierFormFields.tsx:61, frontend/src/pages/suppliers/SupplierFormFields.tsx:68, frontend/src/pages/teams/TeamFormFields.tsx:44

### frontend/src/components.css:39
```css
.form-group textarea {
  min-height: var(--textarea-min-h);
  resize: vertical;
}
```
approx matching raw textareas: 27 -> frontend/src/components/OrderFinancialPanel.tsx:239, frontend/src/components/PriorityScoreOverride.tsx:91, frontend/src/components/PurchaseDetailPanel.tsx:442, frontend/src/components/ShippingDetailPanel.tsx:551, frontend/src/pages/admin/TenantProfilePage.tsx:170, frontend/src/pages/badges/BadgesPage.tsx:62, frontend/src/pages/buddy/BuddyPage.tsx:66, frontend/src/pages/companies/CompanyFormFields.tsx:64, frontend/src/pages/conditions/ConditionsPage.tsx:340, frontend/src/pages/conditions/ConditionsPage.tsx:350, frontend/src/pages/contacts/ContactEditPage.tsx:191, frontend/src/pages/leads/LeadEditPage.tsx:279, frontend/src/pages/leads/LeadFormFields.tsx:84, frontend/src/pages/leads/LeadFormFields.tsx:153, frontend/src/pages/leads/LeadsPage.tsx:429, frontend/src/pages/orders/OrdersFormModal.tsx:95, frontend/src/pages/products/ProductEditPage.tsx:309, frontend/src/pages/purchase-orders/PurchaseOrdersFormModal.tsx:217, frontend/src/pages/roles/RolesPage.tsx:538, frontend/src/pages/staff-reports/StaffReportsPage.tsx:90, frontend/src/pages/staff-reports/StaffReportsPage.tsx:91, frontend/src/pages/staff-reports/StaffReportsPage.tsx:92, frontend/src/pages/super-admin/components/ConditionsMasterPanel.tsx:367, frontend/src/pages/super-admin/components/ConditionsMasterPanel.tsx:380, frontend/src/pages/suppliers/SupplierFormFields.tsx:61, frontend/src/pages/suppliers/SupplierFormFields.tsx:68, frontend/src/pages/teams/TeamFormFields.tsx:44

### frontend/src/components/FormField.css:47
```css
.comp-field__input,
.comp-field__select,
.comp-select__control,
.comp-field__textarea {
  width: 100%;
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border);
  border-radius: var(--comp-input-radius);
  font-size: var(--font-base);
  color: var(--text-primary);
  background: var(--bg-surface);
  box-sizing: border-box;
  font-family: inherit;
  line-height: var(--line-height-base);
  transition: border-color var(--transition-micro), box-shadow var(--transition-micro);
}
```
approx matching raw textareas: 1 -> frontend/src/components/Textarea.tsx:63

### frontend/src/components/FormField.css:65
```css
.comp-field__textarea {
  min-height: var(--textarea-min-h);
  resize: vertical;
}
```
approx matching raw textareas: 1 -> frontend/src/components/Textarea.tsx:63

### frontend/src/components/FormField.css:95
```css
.comp-field__input:focus,
.comp-field__select:focus,
.comp-select__control:focus,
.comp-field__textarea:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: var(--focus-ring-shadow);
}
```
approx matching raw textareas: 1 -> frontend/src/components/Textarea.tsx:63

### frontend/src/components/FormField.css:105
```css
.comp-field__input:disabled,
.comp-field__select:disabled,
.comp-select__control:disabled,
.comp-field__textarea:disabled {
  opacity: var(--opacity-archived);
  cursor: not-allowed;
  background: var(--bg-hover);
}
```
approx matching raw textareas: 1 -> frontend/src/components/Textarea.tsx:63

### frontend/src/components/FormField.css:115
```css
.comp-field--error .comp-field__input,
.comp-field--error .comp-field__select,
.comp-field--error .comp-field__textarea {
  border-color: var(--danger);
}
```
approx matching raw textareas: 0

### frontend/src/components/FormField.css:148
```css
.comp-field--sm .comp-field__textarea {
  padding: var(--space-1) var(--space-2);
  font-size: var(--font-sm);
}
```
approx matching raw textareas: 0

### frontend/src/components/FormField.css:158
```css
.comp-field--lg .comp-field__input,
.comp-field--lg .comp-field__select,
.comp-select__control--lg,
.comp-field--lg .comp-field__textarea {
  padding: var(--space-3) var(--space-4);
  font-size: var(--font-md);
  min-height: var(--comp-input-height-mobile);
}
```
approx matching raw textareas: 0

### frontend/src/components/FormField.css:262
```css
.comp-field--error .comp-field__input:focus,
.comp-field--error .comp-field__select:focus,
.comp-field--error .comp-field__textarea:focus {
  border-color: var(--danger);
  box-shadow: 0 0 0 3px var(--danger-bg-subtle);
}
```
approx matching raw textareas: 0

### frontend/src/components/field-size.css:8
```css
.field-h-md { min-height: var(--field-h-md, 36px); box-sizing: border-box; }
```
approx matching raw textareas: 2 -> frontend/src/pages/conditions/ConditionsPage.tsx:340, frontend/src/pages/conditions/ConditionsPage.tsx:350

### frontend/src/features/tcg-analysis-review/supplier-detail-view.css:244
```css
.pmd-field input,
.pmd-field textarea {
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--bg-surface);
  padding: var(--space-2);
  font: inherit;
  width: 100%;
  box-sizing: border-box;
}
```
approx matching raw textareas: 2 -> frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:217, frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:221

### frontend/src/features/tcg-analysis-review/supplier-detail-view.css:255
```css
.pmd-field textarea {
  min-height: var(--pmd-textarea-min-h);
  resize: vertical;
}
```
approx matching raw textareas: 2 -> frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:217, frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:221

### frontend/src/pages/dashboard/WeeklyAdvisorSection.css:205
```css
.db-weekly-composer-input {
  width: 100%;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-subtle);
  background: var(--bg-primary);
  color: var(--text-primary);
  padding: var(--space-2) var(--space-3);
  font: inherit;
  resize: vertical;
}
```
approx matching raw textareas: 2 -> frontend/src/pages/dashboard/PriorityProspectsSection.tsx:410, frontend/src/pages/dashboard/WeeklyAdvisorSection.tsx:381

### frontend/src/pages/dashboard/WeeklyAdvisorSection.css:216
```css
.db-weekly-composer-input:focus {
  outline: 2px solid var(--accent);
  outline-offset: 1px;
}
```
approx matching raw textareas: 2 -> frontend/src/pages/dashboard/PriorityProspectsSection.tsx:410, frontend/src/pages/dashboard/WeeklyAdvisorSection.tsx:381

### frontend/src/pages/inbox/InboxPage.css:633
```css
.inbox-textarea {
  flex: 1;
  min-width: 0;
  border: none;
  padding: 0;
  font-size: var(--font-base);
  resize: none;
  font-family: inherit;
  outline: none;
  background: transparent;
  color: var(--text-primary);
  box-sizing: border-box;
  line-height: 1.4;
}
```
approx matching raw textareas: 1 -> frontend/src/pages/inbox/InboxMessageThread.tsx:736

### frontend/src/pages/inbox/InboxPage.css:647
```css
.inbox-textarea:disabled { cursor: not-allowed; opacity: var(--opacity-disabled); }
```
approx matching raw textareas: 1 -> frontend/src/pages/inbox/InboxMessageThread.tsx:736

### frontend/src/pages/inbox/InboxPage.css:1171
```css
.right-panel-field {
  width: 100%; box-sizing: border-box;
  background: var(--karte-field-bg); border: 0.5px solid var(--karte-field-bd); /* 見本 .fbox: tokens にて定義 */
  border-radius: var(--radius-md); padding: var(--karte-field-py) var(--karte-field-px); /* 見本 .fbox: 7px 9px, radius 6px */
  font-size: var(--font-sm); color: var(--text-primary);
  font-family: inherit;
  transition: border-color var(--transition-micro);
}
```
approx matching raw textareas: 8 -> frontend/src/pages/inbox/InboxKartePanel.tsx:484, frontend/src/pages/inbox/InboxKartePanel.tsx:503, frontend/src/pages/inbox/InboxKartePanel.tsx:537, frontend/src/pages/inbox/InboxKartePanel.tsx:588, frontend/src/pages/inbox/InboxProfileModal.tsx:181, frontend/src/pages/inbox/InboxProfileModal.tsx:191, frontend/src/pages/inbox/InboxProfileModal.tsx:210, frontend/src/pages/inbox/InboxProfileModal.tsx:265

### frontend/src/pages/inbox/InboxPage.css:1179
```css
.right-panel-field::placeholder { color: var(--text-muted); }
```
approx matching raw textareas: 8 -> frontend/src/pages/inbox/InboxKartePanel.tsx:484, frontend/src/pages/inbox/InboxKartePanel.tsx:503, frontend/src/pages/inbox/InboxKartePanel.tsx:537, frontend/src/pages/inbox/InboxKartePanel.tsx:588, frontend/src/pages/inbox/InboxProfileModal.tsx:181, frontend/src/pages/inbox/InboxProfileModal.tsx:191, frontend/src/pages/inbox/InboxProfileModal.tsx:210, frontend/src/pages/inbox/InboxProfileModal.tsx:265

### frontend/src/pages/inbox/InboxPage.css:1180
```css
.right-panel-field:focus { outline: none; border-color: var(--accent); }
```
approx matching raw textareas: 8 -> frontend/src/pages/inbox/InboxKartePanel.tsx:484, frontend/src/pages/inbox/InboxKartePanel.tsx:503, frontend/src/pages/inbox/InboxKartePanel.tsx:537, frontend/src/pages/inbox/InboxKartePanel.tsx:588, frontend/src/pages/inbox/InboxProfileModal.tsx:181, frontend/src/pages/inbox/InboxProfileModal.tsx:191, frontend/src/pages/inbox/InboxProfileModal.tsx:210, frontend/src/pages/inbox/InboxProfileModal.tsx:265

### frontend/src/pages/inbox/InboxPage.css:1181
```css
textarea.right-panel-field { resize: none; min-height: var(--inbox-textarea-min-h); }
```
approx matching raw textareas: 8 -> frontend/src/pages/inbox/InboxKartePanel.tsx:484, frontend/src/pages/inbox/InboxKartePanel.tsx:503, frontend/src/pages/inbox/InboxKartePanel.tsx:537, frontend/src/pages/inbox/InboxKartePanel.tsx:588, frontend/src/pages/inbox/InboxProfileModal.tsx:181, frontend/src/pages/inbox/InboxProfileModal.tsx:191, frontend/src/pages/inbox/InboxProfileModal.tsx:210, frontend/src/pages/inbox/InboxProfileModal.tsx:265

### frontend/src/pages/inbox/InboxPage.css:1529
```css
.outbound-translation-edit {
  width: 100%; padding: var(--space-3); resize: vertical;
  border: 1px solid var(--border); border-radius: var(--radius-sm);
  background: var(--bg-input); color: var(--text); font-size: var(--font-sm);
  line-height: 1.5; font-family: inherit;
}
```
approx matching raw textareas: 1 -> frontend/src/pages/inbox/OutboundTranslationPreview.tsx:147

### frontend/src/pages/inbox/InboxPage.css:1535
```css
.outbound-translation-edit:focus { outline: none; border-color: var(--accent); }
```
approx matching raw textareas: 1 -> frontend/src/pages/inbox/OutboundTranslationPreview.tsx:147

### frontend/src/pages/schedule.css:813
```css
.schedule-input,
.schedule-textarea {
  width: 100%;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--bg-surface);
  color: var(--text-primary);
  font-size: var(--font-sm);
}
```
approx matching raw textareas: 1 -> frontend/src/pages/schedule/SchedulePageImpl.tsx:378

### frontend/src/pages/schedule.css:828
```css
.schedule-textarea {
  padding: var(--space-2) var(--space-3);
  resize: vertical;
}
```
approx matching raw textareas: 1 -> frontend/src/pages/schedule/SchedulePageImpl.tsx:378

### frontend/src/pages/schedule.css:833
```css
.schedule-input:focus,
.schedule-textarea:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: var(--focus-ring-shadow);
}
```
approx matching raw textareas: 1 -> frontend/src/pages/schedule/SchedulePageImpl.tsx:378


## raw textareas matched by NO listed rule (approx): 5
frontend/src/features/tcg-analysis-review/ItemComparison.tsx:27
frontend/src/features/tcg-analysis-review/ItemComparison.tsx:34
frontend/src/pages/admin/DiscordAnnouncePage.tsx:98
frontend/src/pages/inbox/ManualRecordSection.tsx:159
frontend/src/pages/super-admin/ExtractionPromptConfigTab.tsx:222

## NOTE: raw textareas with no matching rule (approx) use classes with no CSS definition anywhere in frontend/src css: 'input', 'w-full', 'resize-y' (DiscordAnnouncePage:98), 'manual-record-textarea' (ManualRecordSection:159); ItemComparison:27/34 and ExtractionPromptConfigTab:222 have no className/ancestor-matching rule.

## Mold full text (Textarea.tsx / Textarea.stories.tsx; no Textarea.test.* exists at origin/main)
```
=== frontend/src/components/Textarea.stories.tsx
     1	/**
     2	 * Textarea — デザイントークンカタログ (ADR-067 / Task 2C)
     3	 *
     4	 * 標準テキストエリアの全バリアント・状態確認。
     5	 */
     6	import type { Meta, StoryObj } from '@storybook/react-vite'
     7	import { Textarea } from './Textarea'
     8	
     9	const meta: Meta<typeof Textarea> = {
    10	  title: 'Components/Textarea',
    11	  component: Textarea,
    12	  parameters: { layout: 'padded' },
    13	  tags: ['autodocs'],
    14	}
    15	export default meta
    16	
    17	type Story = StoryObj<typeof Textarea>
    18	
    19	export const Default: Story = {
    20	  name: '通常状態',
    21	  args: {
    22	    label: 'Notes',
    23	    placeholder: 'Enter notes...',
    24	    helperText: 'Visible to all team members.',
    25	  },
    26	}
    27	
    28	export const Required: Story = {
    29	  name: '必須フィールド',
    30	  args: {
    31	    label: 'Description',
    32	    placeholder: 'Describe the issue...',
    33	    required: true,
    34	  },
    35	}
    36	
    37	export const WithError: Story = {
    38	  name: 'エラー状態',
    39	  args: {
    40	    label: 'Message',
    41	    placeholder: 'Enter message...',
    42	    error: 'Message is required.',
    43	    required: true,
    44	  },
    45	}
    46	
    47	export const Disabled: Story = {
    48	  name: '無効状態',
    49	  args: {
    50	    label: 'Template body',
    51	    defaultValue: 'This template is locked and cannot be edited.',
    52	    disabled: true,
    53	    helperText: 'Contact admin to edit.',
    54	  },
    55	}
    56	
    57	export const WithRows: Story = {
    58	  name: 'rows 指定 (rows=6)',
    59	  args: {
    60	    label: 'Detailed notes',
    61	    placeholder: 'Enter detailed notes...',
    62	    rows: 6,
    63	    helperText: 'Up to 1000 characters.',
    64	  },
    65	}
    66	
    67	export const Sizes: Story = {
    68	  name: 'サイズ比較 (sm / md / lg)',
    69	  render: () => (
    70	    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
    71	      <Textarea label="Small" placeholder="sm textarea" size="sm" />
    72	      <Textarea label="Medium (default)" placeholder="md textarea" size="md" />
    73	      <Textarea label="Large" placeholder="lg textarea" size="lg" />
    74	    </div>
    75	  ),
    76	}
=== frontend/src/components/Textarea.tsx
     1	/**
     2	 * Textarea — 標準テキストエリア金型（Task 2C）
     3	 *
     4	 * size: sm / md(default) / lg
     5	 * 状態: 通常・focus（CSS）・error・disabled
     6	 *
     7	 * TypeScript の型で規格外 size をコンパイルエラーにする。
     8	 * 実画面への展開は Task 2E で行う。
     9	 */
    10	
    11	import { useId } from "react";
    12	import type { TextareaHTMLAttributes } from "react";
    13	import "./FormField.css";
    14	
    15	export type TextareaSize = "sm" | "md" | "lg";
    16	
    17	interface TextareaOwnProps {
    18	  label?: string;
    19	  helperText?: string;
    20	  error?: string;
    21	  size?: TextareaSize;
    22	  fullWidth?: boolean;
    23	}
    24	
    25	export type TextareaProps = TextareaOwnProps &
    26	  Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, keyof TextareaOwnProps>;
    27	
    28	export function Textarea({
    29	  label,
    30	  helperText,
    31	  error,
    32	  size = "md",
    33	  fullWidth = false,
    34	  className,
    35	  id,
    36	  ...rest
    37	}: TextareaProps) {
    38	  const generatedId = useId();
    39	  const fieldId = id ?? generatedId;
    40	
    41	  const containerClass = [
    42	    "comp-field",
    43	    size !== "md" ? `comp-field--${size}` : "",
    44	    fullWidth ? "comp-field--full" : "",
    45	    error ? "comp-field--error" : "",
    46	    className ?? "",
    47	  ]
    48	    .filter(Boolean)
    49	    .join(" ");
    50	
    51	  return (
    52	    <div className={containerClass}>
    53	      {label != null && (
    54	        <label htmlFor={fieldId} className="comp-field__label">
    55	          {label}
    56	          {rest.required && (
    57	            <span className="comp-field__required" aria-hidden="true">
    58	              *
    59	            </span>
    60	          )}
    61	        </label>
    62	      )}
    63	      <textarea id={fieldId} className="comp-field__textarea" {...rest} />
    64	      {(error != null || helperText != null) && (
    65	        <p
    66	          className={`comp-field__hint${error != null ? " comp-field__hint--error" : ""}`}
    67	          role={error != null ? "alert" : undefined}
    68	        >
    69	          {error ?? helperText}
    70	        </p>
    71	      )}
    72	    </div>
    73	  );
    74	}
```
