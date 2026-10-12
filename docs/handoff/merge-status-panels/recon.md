# Recon: merge-status-panels

## 対象ファイル（file:line）

### 変更ファイル
- `frontend/src/pages/super-admin/components/RuleManagementPanel.tsx:1-180` — 移行先パネル
- `frontend/src/pages/super-admin/components/AnalysisRulesSidebar.tsx:10-30` — サイドバー型定義・`"status-master"` navItem
- `frontend/src/pages/super-admin/AnalysisRulesPage.tsx:27` — `StatusMasterPanel` import
- `frontend/src/pages/super-admin/AnalysisRulesPage.tsx:173` — `status-master` conditional render
- `frontend/src/locales/ja.json` — ruleManagement 追加キー、extractionRules 名称変更
- `frontend/src/locales/en.json` — ruleManagement 追加キー、extractionRules 名称変更

### 参照ファイル（変更なし）
- `frontend/src/pages/super-admin/components/StatusMasterPanel.tsx` — 移行元（削除しない）
- `frontend/src/components/ConfirmModal.tsx` — 金型コンポーネント（bulkDelete確認用）
- `frontend/src/components/HeaderButton.tsx` — 金型コンポーネント（ボタン）

## 既存ADR確認
- ADR-027: i18n強制 — 対応済み（全文字列 t("key")経由）
- ADR-144: UIガバナンス — 対応済み（金型コンポーネントのみ）

## 触らないファイル
- `frontend/src/pages/super-admin/components/StatusMasterPanel.tsx` — 参照用として残置
- backend API — 変更なし（/super-admin/status-master/* エンドポイントはそのまま利用）
