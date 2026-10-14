# AY-2t recon（要約）: 目標設定ページの生 input 3種

- 基準: origin/main 0661b6e5f（AY-2s 反映後）。詳細な調査は設計時 recon（社内作業ファイル）から要約。引用は変更前のコード位置。
- 既存 ADR 検索: docs/adr/ADR-027-ui-internationalization.md（i18n）、docs/adr/ADR-067-design-token-enforcement.md（トークン）、docs/adr/ADR-144-ui-component-governance.md（金型）。該当機能の新規 ADR なし。

## 1. 生 input（変更前）
- `frontend/src/pages/goal-setting/GoalSettingPage.tsx:162-170` GoalInputRow（最大16個。個人月次3・個人週次3・チーム月次5・チーム週次5）: `className={`gs-input${saved ? " gs-input-saved" : ""}`}`
- `frontend/src/pages/goal-setting/GoalSettingPage.tsx:235-243` AdvisorMetricRow（3個）: `gs-input gs-advisor__metric-input`、aria-label
- `frontend/src/pages/goal-setting/GoalSettingPage.tsx:339-348` 月次 KGI（1個）: id・data-testid 自身、`gs-input gs-advisor__monthly-input`

## 2. CSS（変更前）
- `frontend/src/pages/goal-setting/GoalSettingPage.css:510-520` `.gs-input`（背景 --bg-primary、文字 --font-sm、line-height 未指定）
- `frontend/src/pages/goal-setting/GoalSettingPage.css:522-525` `.gs-input:focus`（枠 accent のみ）
- `frontend/src/pages/goal-setting/GoalSettingPage.css:527-530` `.gs-input.gs-input-saved`（枠 --success、背景 --success-bg-subtle）
- `frontend/src/pages/goal-setting/GoalSettingPage.css:119-121, 277-286` 月次/週次の min-height 44px（変更しない）

## 3. 金型
- `frontend/src/components/TextField.tsx:41-54` TextFieldControl（className は input 自身に付く。id・testid 等は rest で素通し）
- `frontend/src/components/FormField.css:46-62` `.comp-field__input`（背景 --bg-surface、文字 --font-base、line-height 1.5）、`:94-102` focus（リング）、`:443-449` ≤767px で min-height 44px
- radius/border/padding/color/width/box-sizing は `.gs-input` と同値。差は 背景・文字・line-height・focus リング・transition。
- `.gs-input` 基底を残すと同詳細度・後読みで金型値を上書きする → 基底は削除し、saved のみ modifier として残す。

## 4. 試験
- `frontend/tests-e2e/goal-setting-advisor.spec.ts`: testid と子孫 `input` の要素型のみで class 非依存。単体試験の参照なし。
- `frontend/src/pages/goal-setting/GoalSettingPage.stories.tsx:23-40` SavedInputState が生 input に `gs-input gs-input-saved` を使用。
