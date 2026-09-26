# Design: merge-status-panels

- recon: docs/handoff/merge-status-panels/recon.md
- 対象ADR: ADR-027, ADR-144

## 概要
StatusMasterPanel の3機能（CSVエクスポート・CSVインポートナビ・一括削除）を RuleManagementPanel に移行し、サイドバーから "status-master" エントリを除去する。合わせて "抽出ルール設定" を "仕入元別ルール" に改名。

## 変更内容

### 1. RuleManagementPanel.tsx に追加する機能

**Feature 1: CSV Export**
- `useRef<boolean>` exportLock + `useState` exporting を追加
- `downloadExport()`: `api.getBlob("/super-admin/status-master/export")` → blob URL → `<a download="status-master-export.csv">` click
- ContentToolbar right に HeaderButton variant="secondary" を追加
- i18n: `ruleManagement.export` / `ruleManagement.exporting`

**Feature 2: CSV Import ナビ**
- `useNavigate` を追加（react-router-dom）
- HeaderButton variant="primary" → `/super-admin/masters/status-master/import` に遷移
- i18n: `ruleManagement.import`

**Feature 3: 一括削除**
- DataTable に `selectable`, `selectedKeys`, `onSelectChange` props を追加
- `bulkDelete()`: `Promise.allSettled(selectedIds.map(id => api.delete(...)))`
- ConfirmModal で確認
- HeaderButton variant="secondary"（selectedKeys.size > 0 のときのみ表示）
- i18n: `ruleManagement.bulkDelete`, `ruleManagement.bulkDeleteConfirm`

**ボタン配置（ContentToolbar right）:**
検索 → エクスポート → インポート → 新規作成 → 一括削除（選択時のみ）

### 2. AnalysisRulesSidebar.tsx
- `AnalysisRulesSidebarKey` から `"status-master"` を除去（`frontend/src/pages/super-admin/components/AnalysisRulesSidebar.tsx:20`）
- `{navItem("status-master", ...)}` を削除（`frontend/src/pages/super-admin/components/AnalysisRulesSidebar.tsx:91`）

### 3. AnalysisRulesPage.tsx
- `import { StatusMasterPanel }` を削除（`frontend/src/pages/super-admin/AnalysisRulesPage.tsx:27`）
- `{activeSection === "status-master" && <StatusMasterPanel />}` を削除（`frontend/src/pages/super-admin/AnalysisRulesPage.tsx:173`）

### 4. i18n
追加キー（ja.json / en.json）:
- `ruleManagement.export`
- `ruleManagement.exporting`
- `ruleManagement.import`
- `ruleManagement.bulkDelete`
- `ruleManagement.bulkDeleteConfirm`
- `ruleManagement.bulkDeleting`
- `ruleManagement.bulkDeleted`

変更キー:
- `analysisRules.sidebar.extractionRules`: "抽出ルール設定" → "仕入元別ルール" / "Supplier Rules"

## 検証基準

| 基準 | 検証方法 |
|------|---------|
| サイドバーに "ステータスルール（旧StatusMaster）" エントリが表示されない | ブラウザ目視確認 |
| RuleManagementPanel にエクスポートボタンが表示される | ブラウザ目視確認 |
| RuleManagementPanel にインポートボタンが表示され、クリックで遷移 | ブラウザ操作確認 |
| チェックボックスで行選択後に一括削除ボタンが現れる | ブラウザ操作確認 |
| TypeScriptコンパイルエラーが新規ゼロ | `./node_modules/.bin/tsc --noEmit` |
| ja.json と en.json で同一キーが存在する | python3 diff確認 |
| "抽出ルール設定" が "仕入元別ルール" に変わっている | サイドバー目視確認 |

## 外部・過去事例の参照と我々への応用

同リポジトリ内の `frontend/src/pages/super-admin/components/StatusMasterPanel.tsx` がCSVエクスポート・インポートナビ・一括削除の完成形実装として存在する。exportLock/exporting パターン、bulkDelete の `Promise.allSettled` パターン、DataTable の `selectable` props をそのまま移植した。

## 維持の仕組み

守り手: .github/workflows/ui-governance-gate.yml

- ADR-027: i18n強制 — 全文字列 t("key")経由。`frontend/CLAUDE.md` の grep セルフチェックで強制
- ADR-144: UIガバナンス — HeaderButton/ConfirmModal/DataTable の金型のみ使用
- StatusMasterPanel.tsx は削除せず残置することで、将来の参照・差分確認が可能
