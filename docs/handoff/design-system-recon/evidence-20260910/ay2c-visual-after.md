# AY-2c 外観実測（Chromium 147.0.7727.15、幅1280/375、light）

手法: before=snap(origin/main c6c4fdc51)の CSS、after=実装後 worktree の実 CSS 実ファイル（postcss 除去の模擬ではない）。祖先連鎖を同じクラスで再構成した fixture に input を置き computed style を取得。旧記述: snap の CSS を読み込み、祖先連鎖を同じクラスで再構成した fixture に input を置き computed style を取得。before=現行 CSS（text系は class 無し、既存金型は comp-field__input）。after=company-forms.css の4規則群（:100 / :113 / :147-148 / :163-164、計 0 セレクタ）を postcss で除去、text系は class=comp-field__input のみ（type/disabled 保持）、checkbox は規則除去のみ。ファイルは書き換えていない。disabled は属性を持つ代表のみ disabled 状態を測定。

## 幅 1280

| 代表 | 状態 | プロパティ | before | after |
|---|---|---|---|---|
| T1 text  modal-content-wide<form-row (MergeLeadModal:146) | normal | border-top-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T1 text  modal-content-wide<form-row (MergeLeadModal:146) | normal | border-right-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T1 text  modal-content-wide<form-row (MergeLeadModal:146) | normal | border-bottom-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T1 text  modal-content-wide<form-row (MergeLeadModal:146) | normal | border-left-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T1 text  modal-content-wide<form-row (MergeLeadModal:146) | normal | line-height | normal | 21.6px |
| T1 text  modal-content-wide<form-row (MergeLeadModal:146) | normal | height | 35px | 39.6094px |
| T1 text  modal-content-wide<form-row (MergeLeadModal:146) | normal | transition-property | all | border-color, box-shadow |
| T1 text  modal-content-wide<form-row (MergeLeadModal:146) | normal | transition-duration | 0s | 0.1s, 0.1s |
| T1 text  modal-content-wide<form-row (MergeLeadModal:146) | normal | offsetHeight | 35 | 40 |
| T1 text  modal-content-wide<form-row (MergeLeadModal:146) | focus | border-top-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| T1 text  modal-content-wide<form-row (MergeLeadModal:146) | focus | border-right-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| T1 text  modal-content-wide<form-row (MergeLeadModal:146) | focus | border-bottom-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| T1 text  modal-content-wide<form-row (MergeLeadModal:146) | focus | border-left-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| T1 text  modal-content-wide<form-row (MergeLeadModal:146) | focus | line-height | normal | 21.6px |
| T1 text  modal-content-wide<form-row (MergeLeadModal:146) | focus | height | 35px | 39.6094px |
| T1 text  modal-content-wide<form-row (MergeLeadModal:146) | focus | transition-property | all | border-color, box-shadow |
| T1 text  modal-content-wide<form-row (MergeLeadModal:146) | focus | transition-duration | 0s | 0.1s, 0.1s |
| T1 text  modal-content-wide<form-row (MergeLeadModal:146) | focus | offsetHeight | 35 | 40 |
| T2 omitted modal-wide<form-grid<form-row (CompaniesPage:452) | normal | border-top-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T2 omitted modal-wide<form-grid<form-row (CompaniesPage:452) | normal | border-right-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T2 omitted modal-wide<form-grid<form-row (CompaniesPage:452) | normal | border-bottom-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T2 omitted modal-wide<form-grid<form-row (CompaniesPage:452) | normal | border-left-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T2 omitted modal-wide<form-grid<form-row (CompaniesPage:452) | normal | line-height | normal | 21.6px |
| T2 omitted modal-wide<form-grid<form-row (CompaniesPage:452) | normal | height | 35px | 39.6094px |
| T2 omitted modal-wide<form-grid<form-row (CompaniesPage:452) | normal | transition-property | all | border-color, box-shadow |
| T2 omitted modal-wide<form-grid<form-row (CompaniesPage:452) | normal | transition-duration | 0s | 0.1s, 0.1s |
| T2 omitted modal-wide<form-grid<form-row (CompaniesPage:452) | normal | offsetHeight | 35 | 40 |
| T2 omitted modal-wide<form-grid<form-row (CompaniesPage:452) | focus | border-top-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| T2 omitted modal-wide<form-grid<form-row (CompaniesPage:452) | focus | border-right-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| T2 omitted modal-wide<form-grid<form-row (CompaniesPage:452) | focus | border-bottom-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| T2 omitted modal-wide<form-grid<form-row (CompaniesPage:452) | focus | border-left-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| T2 omitted modal-wide<form-grid<form-row (CompaniesPage:452) | focus | line-height | normal | 21.6px |
| T2 omitted modal-wide<form-grid<form-row (CompaniesPage:452) | focus | height | 35px | 39.6094px |
| T2 omitted modal-wide<form-grid<form-row (CompaniesPage:452) | focus | transition-property | all | border-color, box-shadow |
| T2 omitted modal-wide<form-grid<form-row (CompaniesPage:452) | focus | transition-duration | 0s | 0.1s, 0.1s |
| T2 omitted modal-wide<form-grid<form-row (CompaniesPage:452) | focus | offsetHeight | 35 | 40 |
| T3 number modal-wide<form-grid<form-row (CompaniesPage:480) | normal | border-top-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T3 number modal-wide<form-grid<form-row (CompaniesPage:480) | normal | border-right-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T3 number modal-wide<form-grid<form-row (CompaniesPage:480) | normal | border-bottom-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T3 number modal-wide<form-grid<form-row (CompaniesPage:480) | normal | border-left-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T3 number modal-wide<form-grid<form-row (CompaniesPage:480) | normal | line-height | normal | 21.6px |
| T3 number modal-wide<form-grid<form-row (CompaniesPage:480) | normal | height | 35px | 39.6094px |
| T3 number modal-wide<form-grid<form-row (CompaniesPage:480) | normal | transition-property | all | border-color, box-shadow |
| T3 number modal-wide<form-grid<form-row (CompaniesPage:480) | normal | transition-duration | 0s | 0.1s, 0.1s |
| T3 number modal-wide<form-grid<form-row (CompaniesPage:480) | normal | offsetHeight | 35 | 40 |
| T3 number modal-wide<form-grid<form-row (CompaniesPage:480) | focus | border-top-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| T3 number modal-wide<form-grid<form-row (CompaniesPage:480) | focus | border-right-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| T3 number modal-wide<form-grid<form-row (CompaniesPage:480) | focus | border-bottom-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| T3 number modal-wide<form-grid<form-row (CompaniesPage:480) | focus | border-left-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| T3 number modal-wide<form-grid<form-row (CompaniesPage:480) | focus | line-height | normal | 21.6px |
| T3 number modal-wide<form-grid<form-row (CompaniesPage:480) | focus | height | 35px | 39.6094px |
| T3 number modal-wide<form-grid<form-row (CompaniesPage:480) | focus | transition-property | all | border-color, box-shadow |
| T3 number modal-wide<form-grid<form-row (CompaniesPage:480) | focus | transition-duration | 0s | 0.1s, 0.1s |
| T3 number modal-wide<form-grid<form-row (CompaniesPage:480) | focus | offsetHeight | 35 | 40 |
| T4 email modal-wide<form-grid<form-row (CompaniesPage:536) | normal | border-top-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T4 email modal-wide<form-grid<form-row (CompaniesPage:536) | normal | border-right-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T4 email modal-wide<form-grid<form-row (CompaniesPage:536) | normal | border-bottom-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T4 email modal-wide<form-grid<form-row (CompaniesPage:536) | normal | border-left-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T4 email modal-wide<form-grid<form-row (CompaniesPage:536) | normal | line-height | normal | 21.6px |
| T4 email modal-wide<form-grid<form-row (CompaniesPage:536) | normal | height | 35px | 39.6094px |
| T4 email modal-wide<form-grid<form-row (CompaniesPage:536) | normal | transition-property | all | border-color, box-shadow |
| T4 email modal-wide<form-grid<form-row (CompaniesPage:536) | normal | transition-duration | 0s | 0.1s, 0.1s |
| T4 email modal-wide<form-grid<form-row (CompaniesPage:536) | normal | offsetHeight | 35 | 40 |
| T4 email modal-wide<form-grid<form-row (CompaniesPage:536) | focus | border-top-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| T4 email modal-wide<form-grid<form-row (CompaniesPage:536) | focus | border-right-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| T4 email modal-wide<form-grid<form-row (CompaniesPage:536) | focus | border-bottom-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| T4 email modal-wide<form-grid<form-row (CompaniesPage:536) | focus | border-left-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| T4 email modal-wide<form-grid<form-row (CompaniesPage:536) | focus | line-height | normal | 21.6px |
| T4 email modal-wide<form-grid<form-row (CompaniesPage:536) | focus | height | 35px | 39.6094px |
| T4 email modal-wide<form-grid<form-row (CompaniesPage:536) | focus | transition-property | all | border-color, box-shadow |
| T4 email modal-wide<form-grid<form-row (CompaniesPage:536) | focus | transition-duration | 0s | 0.1s, 0.1s |
| T4 email modal-wide<form-grid<form-row (CompaniesPage:536) | focus | offsetHeight | 35 | 40 |
| T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38) | normal | border-top-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38) | normal | border-right-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38) | normal | border-bottom-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38) | normal | border-left-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38) | normal | line-height | normal | 21.6px |
| T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38) | normal | height | 35px | 39.6094px |
| T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38) | normal | transition-property | all | border-color, box-shadow |
| T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38) | normal | transition-duration | 0s | 0.1s, 0.1s |
| T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38) | normal | offsetHeight | 35 | 40 |
| T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38) | focus | border-top-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38) | focus | border-right-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38) | focus | border-bottom-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38) | focus | border-left-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38) | focus | line-height | normal | 21.6px |
| T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38) | focus | height | 35px | 39.6094px |
| T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38) | focus | transition-property | all | border-color, box-shadow |
| T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38) | focus | transition-duration | 0s | 0.1s, 0.1s |
| T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38) | focus | offsetHeight | 35 | 40 |
| T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38) | disabled | border-top-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38) | disabled | border-right-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38) | disabled | border-bottom-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38) | disabled | border-left-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38) | disabled | line-height | normal | 21.6px |
| T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38) | disabled | background-color | rgb(255, 255, 255) | rgb(226, 232, 240) |
| T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38) | disabled | height | 35px | 39.6094px |
| T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38) | disabled | cursor | default | not-allowed |
| T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38) | disabled | opacity | 1 | 0.5 |
| T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38) | disabled | transition-property | all | border-color, box-shadow |
| T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38) | disabled | transition-duration | 0s | 0.1s, 0.1s |
| T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38) | disabled | offsetHeight | 35 | 40 |
| T6 number+disabled form-grid<form-row (CompanyBasicTab:62) | normal | border-top-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T6 number+disabled form-grid<form-row (CompanyBasicTab:62) | normal | border-right-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T6 number+disabled form-grid<form-row (CompanyBasicTab:62) | normal | border-bottom-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T6 number+disabled form-grid<form-row (CompanyBasicTab:62) | normal | border-left-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T6 number+disabled form-grid<form-row (CompanyBasicTab:62) | normal | line-height | normal | 21.6px |
| T6 number+disabled form-grid<form-row (CompanyBasicTab:62) | normal | height | 35px | 39.6094px |
| T6 number+disabled form-grid<form-row (CompanyBasicTab:62) | normal | transition-property | all | border-color, box-shadow |
| T6 number+disabled form-grid<form-row (CompanyBasicTab:62) | normal | transition-duration | 0s | 0.1s, 0.1s |
| T6 number+disabled form-grid<form-row (CompanyBasicTab:62) | normal | offsetHeight | 35 | 40 |
| T6 number+disabled form-grid<form-row (CompanyBasicTab:62) | focus | border-top-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| T6 number+disabled form-grid<form-row (CompanyBasicTab:62) | focus | border-right-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| T6 number+disabled form-grid<form-row (CompanyBasicTab:62) | focus | border-bottom-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| T6 number+disabled form-grid<form-row (CompanyBasicTab:62) | focus | border-left-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| T6 number+disabled form-grid<form-row (CompanyBasicTab:62) | focus | line-height | normal | 21.6px |
| T6 number+disabled form-grid<form-row (CompanyBasicTab:62) | focus | height | 35px | 39.6094px |
| T6 number+disabled form-grid<form-row (CompanyBasicTab:62) | focus | transition-property | all | border-color, box-shadow |
| T6 number+disabled form-grid<form-row (CompanyBasicTab:62) | focus | transition-duration | 0s | 0.1s, 0.1s |
| T6 number+disabled form-grid<form-row (CompanyBasicTab:62) | focus | offsetHeight | 35 | 40 |
| T6 number+disabled form-grid<form-row (CompanyBasicTab:62) | disabled | border-top-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T6 number+disabled form-grid<form-row (CompanyBasicTab:62) | disabled | border-right-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T6 number+disabled form-grid<form-row (CompanyBasicTab:62) | disabled | border-bottom-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T6 number+disabled form-grid<form-row (CompanyBasicTab:62) | disabled | border-left-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T6 number+disabled form-grid<form-row (CompanyBasicTab:62) | disabled | line-height | normal | 21.6px |
| T6 number+disabled form-grid<form-row (CompanyBasicTab:62) | disabled | background-color | rgb(255, 255, 255) | rgb(226, 232, 240) |
| T6 number+disabled form-grid<form-row (CompanyBasicTab:62) | disabled | height | 35px | 39.6094px |
| T6 number+disabled form-grid<form-row (CompanyBasicTab:62) | disabled | cursor | default | not-allowed |
| T6 number+disabled form-grid<form-row (CompanyBasicTab:62) | disabled | opacity | 1 | 0.5 |
| T6 number+disabled form-grid<form-row (CompanyBasicTab:62) | disabled | transition-property | all | border-color, box-shadow |
| T6 number+disabled form-grid<form-row (CompanyBasicTab:62) | disabled | transition-duration | 0s | 0.1s, 0.1s |
| T6 number+disabled form-grid<form-row (CompanyBasicTab:62) | disabled | offsetHeight | 35 | 40 |
| T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53) | normal | border-top-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53) | normal | border-right-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53) | normal | border-bottom-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53) | normal | border-left-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53) | normal | line-height | normal | 21.6px |
| T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53) | normal | height | 35px | 39.6094px |
| T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53) | normal | transition-property | all | border-color, box-shadow |
| T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53) | normal | transition-duration | 0s | 0.1s, 0.1s |
| T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53) | normal | offsetHeight | 35 | 40 |
| T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53) | focus | border-top-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53) | focus | border-right-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53) | focus | border-bottom-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53) | focus | border-left-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53) | focus | line-height | normal | 21.6px |
| T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53) | focus | height | 35px | 39.6094px |
| T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53) | focus | transition-property | all | border-color, box-shadow |
| T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53) | focus | transition-duration | 0s | 0.1s, 0.1s |
| T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53) | focus | offsetHeight | 35 | 40 |
| T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53) | disabled | border-top-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53) | disabled | border-right-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53) | disabled | border-bottom-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53) | disabled | border-left-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53) | disabled | line-height | normal | 21.6px |
| T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53) | disabled | background-color | rgb(255, 255, 255) | rgb(226, 232, 240) |
| T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53) | disabled | height | 35px | 39.6094px |
| T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53) | disabled | cursor | default | not-allowed |
| T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53) | disabled | opacity | 1 | 0.5 |
| T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53) | disabled | transition-property | all | border-color, box-shadow |
| T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53) | disabled | transition-duration | 0s | 0.1s, 0.1s |
| T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53) | disabled | offsetHeight | 35 | 40 |
| C1 checkbox form-grid<form-row<label (ContactChannelForm:227) | normal | (差なし) | | |
| C1 checkbox form-grid<form-row<label (ContactChannelForm:227) | focus | (差なし) | | |
| C2 checkbox+disabled modal-wide<form-grid<form-row<label (CompanyAddressModal:147) | normal | (差なし) | | |
| C2 checkbox+disabled modal-wide<form-grid<form-row<label (CompanyAddressModal:147) | focus | (差なし) | | |
| C2 checkbox+disabled modal-wide<form-grid<form-row<label (CompanyAddressModal:147) | disabled | (差なし) | | |
| C3 checkbox+disabled div<form-grid<form-row<label (CompanyDiscordTab:42) | normal | (差なし) | | |
| C3 checkbox+disabled div<form-grid<form-row<label (CompanyDiscordTab:42) | focus | (差なし) | | |
| C3 checkbox+disabled div<form-grid<form-row<label (CompanyDiscordTab:42) | disabled | (差なし) | | |
| C4 checkbox div<form.form-grid<form-row<label (CompanyContactsTab:206) | normal | (差なし) | | |
| C4 checkbox div<form.form-grid<form-row<label (CompanyContactsTab:206) | focus | (差なし) | | |
| C5 checkbox modal-wide<form-grid<form-row<label (ContactsPage:332) | normal | (差なし) | | |
| C5 checkbox modal-wide<form-grid<form-row<label (ContactsPage:332) | focus | (差なし) | | |
| M1 existing TextField modal-wide<form-row (MergeCompanyModal:158) | normal | border-top-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| M1 existing TextField modal-wide<form-row (MergeCompanyModal:158) | normal | border-right-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| M1 existing TextField modal-wide<form-row (MergeCompanyModal:158) | normal | border-bottom-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| M1 existing TextField modal-wide<form-row (MergeCompanyModal:158) | normal | border-left-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| M1 existing TextField modal-wide<form-row (MergeCompanyModal:158) | focus | border-top-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| M1 existing TextField modal-wide<form-row (MergeCompanyModal:158) | focus | border-right-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| M1 existing TextField modal-wide<form-row (MergeCompanyModal:158) | focus | border-bottom-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| M1 existing TextField modal-wide<form-row (MergeCompanyModal:158) | focus | border-left-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| M2 existing TextField+disabled modal-wide<form-grid<form-row (CompanyAddressModal:96) | normal | border-top-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| M2 existing TextField+disabled modal-wide<form-grid<form-row (CompanyAddressModal:96) | normal | border-right-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| M2 existing TextField+disabled modal-wide<form-grid<form-row (CompanyAddressModal:96) | normal | border-bottom-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| M2 existing TextField+disabled modal-wide<form-grid<form-row (CompanyAddressModal:96) | normal | border-left-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| M2 existing TextField+disabled modal-wide<form-grid<form-row (CompanyAddressModal:96) | focus | border-top-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| M2 existing TextField+disabled modal-wide<form-grid<form-row (CompanyAddressModal:96) | focus | border-right-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| M2 existing TextField+disabled modal-wide<form-grid<form-row (CompanyAddressModal:96) | focus | border-bottom-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| M2 existing TextField+disabled modal-wide<form-grid<form-row (CompanyAddressModal:96) | focus | border-left-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| M2 existing TextField+disabled modal-wide<form-grid<form-row (CompanyAddressModal:96) | disabled | border-top-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| M2 existing TextField+disabled modal-wide<form-grid<form-row (CompanyAddressModal:96) | disabled | border-right-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| M2 existing TextField+disabled modal-wide<form-grid<form-row (CompanyAddressModal:96) | disabled | border-bottom-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| M2 existing TextField+disabled modal-wide<form-grid<form-row (CompanyAddressModal:96) | disabled | border-left-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| M2 existing TextField+disabled modal-wide<form-grid<form-row (CompanyAddressModal:96) | disabled | background-color | rgb(255, 255, 255) | rgb(226, 232, 240) |

## 幅 375

| 代表 | 状態 | プロパティ | before | after |
|---|---|---|---|---|
| T1 text  modal-content-wide<form-row (MergeLeadModal:146) | normal | border-top-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T1 text  modal-content-wide<form-row (MergeLeadModal:146) | normal | border-right-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T1 text  modal-content-wide<form-row (MergeLeadModal:146) | normal | border-bottom-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T1 text  modal-content-wide<form-row (MergeLeadModal:146) | normal | border-left-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T1 text  modal-content-wide<form-row (MergeLeadModal:146) | normal | line-height | normal | 21.6px |
| T1 text  modal-content-wide<form-row (MergeLeadModal:146) | normal | height | 35px | 44px |
| T1 text  modal-content-wide<form-row (MergeLeadModal:146) | normal | min-height | auto | 44px |
| T1 text  modal-content-wide<form-row (MergeLeadModal:146) | normal | transition-property | all | border-color, box-shadow |
| T1 text  modal-content-wide<form-row (MergeLeadModal:146) | normal | transition-duration | 0s | 0.1s, 0.1s |
| T1 text  modal-content-wide<form-row (MergeLeadModal:146) | normal | offsetHeight | 35 | 44 |
| T1 text  modal-content-wide<form-row (MergeLeadModal:146) | focus | border-top-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| T1 text  modal-content-wide<form-row (MergeLeadModal:146) | focus | border-right-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| T1 text  modal-content-wide<form-row (MergeLeadModal:146) | focus | border-bottom-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| T1 text  modal-content-wide<form-row (MergeLeadModal:146) | focus | border-left-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| T1 text  modal-content-wide<form-row (MergeLeadModal:146) | focus | line-height | normal | 21.6px |
| T1 text  modal-content-wide<form-row (MergeLeadModal:146) | focus | height | 35px | 44px |
| T1 text  modal-content-wide<form-row (MergeLeadModal:146) | focus | min-height | auto | 44px |
| T1 text  modal-content-wide<form-row (MergeLeadModal:146) | focus | transition-property | all | border-color, box-shadow |
| T1 text  modal-content-wide<form-row (MergeLeadModal:146) | focus | transition-duration | 0s | 0.1s, 0.1s |
| T1 text  modal-content-wide<form-row (MergeLeadModal:146) | focus | offsetHeight | 35 | 44 |
| T2 omitted modal-wide<form-grid<form-row (CompaniesPage:452) | normal | border-top-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T2 omitted modal-wide<form-grid<form-row (CompaniesPage:452) | normal | border-right-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T2 omitted modal-wide<form-grid<form-row (CompaniesPage:452) | normal | border-bottom-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T2 omitted modal-wide<form-grid<form-row (CompaniesPage:452) | normal | border-left-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T2 omitted modal-wide<form-grid<form-row (CompaniesPage:452) | normal | line-height | normal | 21.6px |
| T2 omitted modal-wide<form-grid<form-row (CompaniesPage:452) | normal | height | 35px | 44px |
| T2 omitted modal-wide<form-grid<form-row (CompaniesPage:452) | normal | min-height | auto | 44px |
| T2 omitted modal-wide<form-grid<form-row (CompaniesPage:452) | normal | transition-property | all | border-color, box-shadow |
| T2 omitted modal-wide<form-grid<form-row (CompaniesPage:452) | normal | transition-duration | 0s | 0.1s, 0.1s |
| T2 omitted modal-wide<form-grid<form-row (CompaniesPage:452) | normal | offsetHeight | 35 | 44 |
| T2 omitted modal-wide<form-grid<form-row (CompaniesPage:452) | focus | border-top-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| T2 omitted modal-wide<form-grid<form-row (CompaniesPage:452) | focus | border-right-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| T2 omitted modal-wide<form-grid<form-row (CompaniesPage:452) | focus | border-bottom-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| T2 omitted modal-wide<form-grid<form-row (CompaniesPage:452) | focus | border-left-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| T2 omitted modal-wide<form-grid<form-row (CompaniesPage:452) | focus | line-height | normal | 21.6px |
| T2 omitted modal-wide<form-grid<form-row (CompaniesPage:452) | focus | height | 35px | 44px |
| T2 omitted modal-wide<form-grid<form-row (CompaniesPage:452) | focus | min-height | auto | 44px |
| T2 omitted modal-wide<form-grid<form-row (CompaniesPage:452) | focus | transition-property | all | border-color, box-shadow |
| T2 omitted modal-wide<form-grid<form-row (CompaniesPage:452) | focus | transition-duration | 0s | 0.1s, 0.1s |
| T2 omitted modal-wide<form-grid<form-row (CompaniesPage:452) | focus | offsetHeight | 35 | 44 |
| T3 number modal-wide<form-grid<form-row (CompaniesPage:480) | normal | border-top-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T3 number modal-wide<form-grid<form-row (CompaniesPage:480) | normal | border-right-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T3 number modal-wide<form-grid<form-row (CompaniesPage:480) | normal | border-bottom-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T3 number modal-wide<form-grid<form-row (CompaniesPage:480) | normal | border-left-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T3 number modal-wide<form-grid<form-row (CompaniesPage:480) | normal | line-height | normal | 21.6px |
| T3 number modal-wide<form-grid<form-row (CompaniesPage:480) | normal | height | 35px | 44px |
| T3 number modal-wide<form-grid<form-row (CompaniesPage:480) | normal | min-height | auto | 44px |
| T3 number modal-wide<form-grid<form-row (CompaniesPage:480) | normal | transition-property | all | border-color, box-shadow |
| T3 number modal-wide<form-grid<form-row (CompaniesPage:480) | normal | transition-duration | 0s | 0.1s, 0.1s |
| T3 number modal-wide<form-grid<form-row (CompaniesPage:480) | normal | offsetHeight | 35 | 44 |
| T3 number modal-wide<form-grid<form-row (CompaniesPage:480) | focus | border-top-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| T3 number modal-wide<form-grid<form-row (CompaniesPage:480) | focus | border-right-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| T3 number modal-wide<form-grid<form-row (CompaniesPage:480) | focus | border-bottom-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| T3 number modal-wide<form-grid<form-row (CompaniesPage:480) | focus | border-left-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| T3 number modal-wide<form-grid<form-row (CompaniesPage:480) | focus | line-height | normal | 21.6px |
| T3 number modal-wide<form-grid<form-row (CompaniesPage:480) | focus | height | 35px | 44px |
| T3 number modal-wide<form-grid<form-row (CompaniesPage:480) | focus | min-height | auto | 44px |
| T3 number modal-wide<form-grid<form-row (CompaniesPage:480) | focus | transition-property | all | border-color, box-shadow |
| T3 number modal-wide<form-grid<form-row (CompaniesPage:480) | focus | transition-duration | 0s | 0.1s, 0.1s |
| T3 number modal-wide<form-grid<form-row (CompaniesPage:480) | focus | offsetHeight | 35 | 44 |
| T4 email modal-wide<form-grid<form-row (CompaniesPage:536) | normal | border-top-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T4 email modal-wide<form-grid<form-row (CompaniesPage:536) | normal | border-right-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T4 email modal-wide<form-grid<form-row (CompaniesPage:536) | normal | border-bottom-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T4 email modal-wide<form-grid<form-row (CompaniesPage:536) | normal | border-left-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T4 email modal-wide<form-grid<form-row (CompaniesPage:536) | normal | line-height | normal | 21.6px |
| T4 email modal-wide<form-grid<form-row (CompaniesPage:536) | normal | height | 35px | 44px |
| T4 email modal-wide<form-grid<form-row (CompaniesPage:536) | normal | min-height | auto | 44px |
| T4 email modal-wide<form-grid<form-row (CompaniesPage:536) | normal | transition-property | all | border-color, box-shadow |
| T4 email modal-wide<form-grid<form-row (CompaniesPage:536) | normal | transition-duration | 0s | 0.1s, 0.1s |
| T4 email modal-wide<form-grid<form-row (CompaniesPage:536) | normal | offsetHeight | 35 | 44 |
| T4 email modal-wide<form-grid<form-row (CompaniesPage:536) | focus | border-top-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| T4 email modal-wide<form-grid<form-row (CompaniesPage:536) | focus | border-right-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| T4 email modal-wide<form-grid<form-row (CompaniesPage:536) | focus | border-bottom-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| T4 email modal-wide<form-grid<form-row (CompaniesPage:536) | focus | border-left-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| T4 email modal-wide<form-grid<form-row (CompaniesPage:536) | focus | line-height | normal | 21.6px |
| T4 email modal-wide<form-grid<form-row (CompaniesPage:536) | focus | height | 35px | 44px |
| T4 email modal-wide<form-grid<form-row (CompaniesPage:536) | focus | min-height | auto | 44px |
| T4 email modal-wide<form-grid<form-row (CompaniesPage:536) | focus | transition-property | all | border-color, box-shadow |
| T4 email modal-wide<form-grid<form-row (CompaniesPage:536) | focus | transition-duration | 0s | 0.1s, 0.1s |
| T4 email modal-wide<form-grid<form-row (CompaniesPage:536) | focus | offsetHeight | 35 | 44 |
| T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38) | normal | border-top-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38) | normal | border-right-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38) | normal | border-bottom-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38) | normal | border-left-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38) | normal | line-height | normal | 21.6px |
| T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38) | normal | height | 35px | 44px |
| T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38) | normal | min-height | auto | 44px |
| T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38) | normal | transition-property | all | border-color, box-shadow |
| T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38) | normal | transition-duration | 0s | 0.1s, 0.1s |
| T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38) | normal | offsetHeight | 35 | 44 |
| T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38) | focus | border-top-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38) | focus | border-right-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38) | focus | border-bottom-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38) | focus | border-left-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38) | focus | line-height | normal | 21.6px |
| T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38) | focus | height | 35px | 44px |
| T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38) | focus | min-height | auto | 44px |
| T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38) | focus | transition-property | all | border-color, box-shadow |
| T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38) | focus | transition-duration | 0s | 0.1s, 0.1s |
| T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38) | focus | offsetHeight | 35 | 44 |
| T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38) | disabled | border-top-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38) | disabled | border-right-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38) | disabled | border-bottom-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38) | disabled | border-left-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38) | disabled | line-height | normal | 21.6px |
| T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38) | disabled | background-color | rgb(255, 255, 255) | rgb(226, 232, 240) |
| T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38) | disabled | height | 35px | 44px |
| T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38) | disabled | min-height | auto | 44px |
| T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38) | disabled | cursor | default | not-allowed |
| T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38) | disabled | opacity | 1 | 0.5 |
| T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38) | disabled | transition-property | all | border-color, box-shadow |
| T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38) | disabled | transition-duration | 0s | 0.1s, 0.1s |
| T5 omitted+disabled form-grid<form-row (CompanyBasicTab:38) | disabled | offsetHeight | 35 | 44 |
| T6 number+disabled form-grid<form-row (CompanyBasicTab:62) | normal | border-top-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T6 number+disabled form-grid<form-row (CompanyBasicTab:62) | normal | border-right-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T6 number+disabled form-grid<form-row (CompanyBasicTab:62) | normal | border-bottom-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T6 number+disabled form-grid<form-row (CompanyBasicTab:62) | normal | border-left-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T6 number+disabled form-grid<form-row (CompanyBasicTab:62) | normal | line-height | normal | 21.6px |
| T6 number+disabled form-grid<form-row (CompanyBasicTab:62) | normal | height | 35px | 44px |
| T6 number+disabled form-grid<form-row (CompanyBasicTab:62) | normal | min-height | auto | 44px |
| T6 number+disabled form-grid<form-row (CompanyBasicTab:62) | normal | transition-property | all | border-color, box-shadow |
| T6 number+disabled form-grid<form-row (CompanyBasicTab:62) | normal | transition-duration | 0s | 0.1s, 0.1s |
| T6 number+disabled form-grid<form-row (CompanyBasicTab:62) | normal | offsetHeight | 35 | 44 |
| T6 number+disabled form-grid<form-row (CompanyBasicTab:62) | focus | border-top-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| T6 number+disabled form-grid<form-row (CompanyBasicTab:62) | focus | border-right-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| T6 number+disabled form-grid<form-row (CompanyBasicTab:62) | focus | border-bottom-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| T6 number+disabled form-grid<form-row (CompanyBasicTab:62) | focus | border-left-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| T6 number+disabled form-grid<form-row (CompanyBasicTab:62) | focus | line-height | normal | 21.6px |
| T6 number+disabled form-grid<form-row (CompanyBasicTab:62) | focus | height | 35px | 44px |
| T6 number+disabled form-grid<form-row (CompanyBasicTab:62) | focus | min-height | auto | 44px |
| T6 number+disabled form-grid<form-row (CompanyBasicTab:62) | focus | transition-property | all | border-color, box-shadow |
| T6 number+disabled form-grid<form-row (CompanyBasicTab:62) | focus | transition-duration | 0s | 0.1s, 0.1s |
| T6 number+disabled form-grid<form-row (CompanyBasicTab:62) | focus | offsetHeight | 35 | 44 |
| T6 number+disabled form-grid<form-row (CompanyBasicTab:62) | disabled | border-top-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T6 number+disabled form-grid<form-row (CompanyBasicTab:62) | disabled | border-right-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T6 number+disabled form-grid<form-row (CompanyBasicTab:62) | disabled | border-bottom-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T6 number+disabled form-grid<form-row (CompanyBasicTab:62) | disabled | border-left-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T6 number+disabled form-grid<form-row (CompanyBasicTab:62) | disabled | line-height | normal | 21.6px |
| T6 number+disabled form-grid<form-row (CompanyBasicTab:62) | disabled | background-color | rgb(255, 255, 255) | rgb(226, 232, 240) |
| T6 number+disabled form-grid<form-row (CompanyBasicTab:62) | disabled | height | 35px | 44px |
| T6 number+disabled form-grid<form-row (CompanyBasicTab:62) | disabled | min-height | auto | 44px |
| T6 number+disabled form-grid<form-row (CompanyBasicTab:62) | disabled | cursor | default | not-allowed |
| T6 number+disabled form-grid<form-row (CompanyBasicTab:62) | disabled | opacity | 1 | 0.5 |
| T6 number+disabled form-grid<form-row (CompanyBasicTab:62) | disabled | transition-property | all | border-color, box-shadow |
| T6 number+disabled form-grid<form-row (CompanyBasicTab:62) | disabled | transition-duration | 0s | 0.1s, 0.1s |
| T6 number+disabled form-grid<form-row (CompanyBasicTab:62) | disabled | offsetHeight | 35 | 44 |
| T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53) | normal | border-top-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53) | normal | border-right-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53) | normal | border-bottom-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53) | normal | border-left-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53) | normal | line-height | normal | 21.6px |
| T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53) | normal | height | 35px | 44px |
| T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53) | normal | min-height | auto | 44px |
| T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53) | normal | transition-property | all | border-color, box-shadow |
| T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53) | normal | transition-duration | 0s | 0.1s, 0.1s |
| T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53) | normal | offsetHeight | 35 | 44 |
| T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53) | focus | border-top-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53) | focus | border-right-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53) | focus | border-bottom-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53) | focus | border-left-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53) | focus | line-height | normal | 21.6px |
| T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53) | focus | height | 35px | 44px |
| T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53) | focus | min-height | auto | 44px |
| T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53) | focus | transition-property | all | border-color, box-shadow |
| T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53) | focus | transition-duration | 0s | 0.1s, 0.1s |
| T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53) | focus | offsetHeight | 35 | 44 |
| T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53) | disabled | border-top-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53) | disabled | border-right-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53) | disabled | border-bottom-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53) | disabled | border-left-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53) | disabled | line-height | normal | 21.6px |
| T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53) | disabled | background-color | rgb(255, 255, 255) | rgb(226, 232, 240) |
| T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53) | disabled | height | 35px | 44px |
| T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53) | disabled | min-height | auto | 44px |
| T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53) | disabled | cursor | default | not-allowed |
| T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53) | disabled | opacity | 1 | 0.5 |
| T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53) | disabled | transition-property | all | border-color, box-shadow |
| T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53) | disabled | transition-duration | 0s | 0.1s, 0.1s |
| T7 omitted+disabled div<form.form-grid<form-row (CompanyDiscordTab:53) | disabled | offsetHeight | 35 | 44 |
| C1 checkbox form-grid<form-row<label (ContactChannelForm:227) | normal | (差なし) | | |
| C1 checkbox form-grid<form-row<label (ContactChannelForm:227) | focus | (差なし) | | |
| C2 checkbox+disabled modal-wide<form-grid<form-row<label (CompanyAddressModal:147) | normal | (差なし) | | |
| C2 checkbox+disabled modal-wide<form-grid<form-row<label (CompanyAddressModal:147) | focus | (差なし) | | |
| C2 checkbox+disabled modal-wide<form-grid<form-row<label (CompanyAddressModal:147) | disabled | (差なし) | | |
| C3 checkbox+disabled div<form-grid<form-row<label (CompanyDiscordTab:42) | normal | (差なし) | | |
| C3 checkbox+disabled div<form-grid<form-row<label (CompanyDiscordTab:42) | focus | (差なし) | | |
| C3 checkbox+disabled div<form-grid<form-row<label (CompanyDiscordTab:42) | disabled | (差なし) | | |
| C4 checkbox div<form.form-grid<form-row<label (CompanyContactsTab:206) | normal | (差なし) | | |
| C4 checkbox div<form.form-grid<form-row<label (CompanyContactsTab:206) | focus | (差なし) | | |
| C5 checkbox modal-wide<form-grid<form-row<label (ContactsPage:332) | normal | (差なし) | | |
| C5 checkbox modal-wide<form-grid<form-row<label (ContactsPage:332) | focus | (差なし) | | |
| M1 existing TextField modal-wide<form-row (MergeCompanyModal:158) | normal | border-top-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| M1 existing TextField modal-wide<form-row (MergeCompanyModal:158) | normal | border-right-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| M1 existing TextField modal-wide<form-row (MergeCompanyModal:158) | normal | border-bottom-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| M1 existing TextField modal-wide<form-row (MergeCompanyModal:158) | normal | border-left-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| M1 existing TextField modal-wide<form-row (MergeCompanyModal:158) | focus | border-top-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| M1 existing TextField modal-wide<form-row (MergeCompanyModal:158) | focus | border-right-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| M1 existing TextField modal-wide<form-row (MergeCompanyModal:158) | focus | border-bottom-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| M1 existing TextField modal-wide<form-row (MergeCompanyModal:158) | focus | border-left-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| M2 existing TextField+disabled modal-wide<form-grid<form-row (CompanyAddressModal:96) | normal | border-top-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| M2 existing TextField+disabled modal-wide<form-grid<form-row (CompanyAddressModal:96) | normal | border-right-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| M2 existing TextField+disabled modal-wide<form-grid<form-row (CompanyAddressModal:96) | normal | border-bottom-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| M2 existing TextField+disabled modal-wide<form-grid<form-row (CompanyAddressModal:96) | normal | border-left-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| M2 existing TextField+disabled modal-wide<form-grid<form-row (CompanyAddressModal:96) | focus | border-top-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| M2 existing TextField+disabled modal-wide<form-grid<form-row (CompanyAddressModal:96) | focus | border-right-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| M2 existing TextField+disabled modal-wide<form-grid<form-row (CompanyAddressModal:96) | focus | border-bottom-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| M2 existing TextField+disabled modal-wide<form-grid<form-row (CompanyAddressModal:96) | focus | border-left-color | rgb(203, 213, 224) | rgb(30, 58, 138) |
| M2 existing TextField+disabled modal-wide<form-grid<form-row (CompanyAddressModal:96) | disabled | border-top-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| M2 existing TextField+disabled modal-wide<form-grid<form-row (CompanyAddressModal:96) | disabled | border-right-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| M2 existing TextField+disabled modal-wide<form-grid<form-row (CompanyAddressModal:96) | disabled | border-bottom-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| M2 existing TextField+disabled modal-wide<form-grid<form-row (CompanyAddressModal:96) | disabled | border-left-color | rgb(203, 213, 224) | rgb(226, 232, 240) |
| M2 existing TextField+disabled modal-wide<form-grid<form-row (CompanyAddressModal:96) | disabled | background-color | rgb(255, 255, 255) | rgb(226, 232, 240) |


## 判定

PASS。実装後の worktree の実 CSS（company-forms.css は規則削除済みの実ファイル）で計測した。
- 移管（T1〜T7）と既存 TextField（M1・M2）: 差分は設計の前後表の項目（枠色、focus 枠色、line-height、高さ、transition、disabled の背景・不透明度・cursor、幅375の min-height 44px）だけで、表に無い項目の差は 0。
- checkbox（C1〜C5、5 件全件の祖先連鎖）: normal・focus・disabled の全項目で差分 0。
- 事前模擬（ay2c-visual.md）との差: 事前模擬は focus 規則 4 つまで除去していたため checkbox の focus に差が出ていた。実装は focus 規則を残すため実ファイルでは差 0。それ以外の行は事前模擬と完全一致。
- 限界: fixture は祖先連鎖を同じ class で再構成した近似。dark テーマは未測定。
