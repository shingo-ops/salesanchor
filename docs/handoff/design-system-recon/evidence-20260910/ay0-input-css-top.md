# ay-css-top

base HEAD: f0f7ef8c7d89c97d42950e0ab111644b316dd99d

判定: CSSコメント除去後、各selectorの末尾compound(subject)が (a)タグ input を含む、(b) .comp-field__input を含む、(c) text-like生inputがclassNameに静的に持つclass(25種)を含む、のいずれか。textareaのみ・[type=checkbox|radio|file|color|range|hidden]肯定指定は除外。@keyframes内割合は除外。
該当selector総数(重複含む): 59 / 異なるselector文字列: 56 / CSSファイル: 67（うち該当あり 15）

## selector文字列 上位15（出現回数）

| 回数 | selector |
|---|---|
| 2 | `.comp-field__input` |
| 2 | `.schedule-input` |
| 2 | `.toggle-switch input` |
| 1 | `.analysis-dashboard-window-input` |
| 1 | `.comp-field__input:disabled` |
| 1 | `.comp-field__input:focus` |
| 1 | `.comp-field--error .comp-field__input` |
| 1 | `.comp-field--error .comp-field__input:focus` |
| 1 | `.comp-field--lg .comp-field__input` |
| 1 | `.comp-field--sm .comp-field__input` |
| 1 | `.comp-select__control.field-w-md` |
| 1 | `.comp-select__control.field-w-sm` |
| 1 | `.content-toolbar .field-w-md` |
| 1 | `.content-toolbar .field-w-sm` |
| 1 | `.db-weekly-composer-input` |

## CSSファイル別 上位15（該当selector数）

| 件数 | file |
|---|---|
| 8 | src/components/FormField.css |
| 8 | src/pages/inbox/InboxPage.css |
| 7 | src/company-forms.css |
| 7 | src/components.css |
| 7 | src/components/field-size.css |
| 6 | src/pages/goal-setting/GoalSettingPage.css |
| 3 | src/features/tcg-distribution/distribution.css |
| 3 | src/pages/schedule.css |
| 2 | src/pages-layout.css |
| 2 | src/pages/dashboard/WeeklyAdvisorSection.css |
| 2 | src/topbar.css |
| 1 | src/features/tcg-analysis-review/source-raw-pane.css |
| 1 | src/features/tcg-analysis-review/supplier-detail-view.css |
| 1 | src/pages/account-settings/account-settings.css |
| 1 | src/pages/super-admin/components/AnalysisDashboardPanel.css |
