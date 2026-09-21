# recon: analysis panel layout fix

## 調査日
2026-09-21

## 問題

解析管理ページ（/super-admin/analysis-rules）のサブメニューパネルで2つのUIバグを確認。

1. ダッシュボード以外のパネルで左パディングがない（コンテンツが左端に貼り付く）
2. ダッシュボード・インポート以外のパネルでスクロールできない（コンテンツがクリップされる）

## 根拠ファイル

### ダッシュボードパネル（正常動作）

`frontend/src/pages/super-admin/components/AnalysisDashboardPanel.css:11-14`
```css
.analysis-dashboard {
  padding: var(--space-6);
  overflow-y: auto;
  height: 100%;
}
```
→ 自前で padding / overflow-y:auto / height:100% を持つ。

### hub-content（問題の原因）

`frontend/src/hub-shell.css:81-85`
```css
.hub-content {
  ...
  overflow: hidden;
}
```
→ `overflow: hidden` かつパディングなし。非ダッシュボードパネルは直接マウントされるため、スクロール不可・パディングなし。

### AnalysisRulesPage.tsx（レンダリングパターン確認）

`frontend/src/pages/super-admin/AnalysisRulesPage.tsx:149-165`
```tsx
<div className="hub-content">
  {activeSection === "dashboard" && <AnalysisDashboardPanel ... />}
  {activeSection === "accuracy-management" && <AccuracyManagementPanel />}
  {activeSection === "needs-review" && <NeedsReviewPanel />}
  {activeSection === "product-master" && <ProductMasterPanel />}
  {activeSection === "product-categories-master" && <ProductCategoriesMasterPanel />}
  {activeSection === "product-kinds-master" && <ProductKindsMasterPanel />}
  {activeSection === "status-master" && <StatusMasterPanel />}
  {activeSection === "supplier-master" && <SupplierMasterPanel />}
  {activeSection === "conditions-master" && <ConditionsMasterPanel />}
  {activeSection === "unit-master" && <UnitMasterPanel />}
  {activeSection === "note-master" && <NoteMasterPanel />}
</div>
```

### CSS import なし
`frontend/src/pages/super-admin/AnalysisRulesPage.tsx` に CSS import なし（grep 結果: 0件）。

## 関連ADR

- ADR-067: デザイントークン強制（px直書き禁止）
- ADR-144: hub-shell.css の金型クラスのみ使用（直接変更禁止）

## 変更しないファイル

- `frontend/src/hub-shell.css`: 他ページと共有。変更すると全 hub-shell ページに影響（ADR-144）
- `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.css`: ダッシュボードは既存動作維持
- 各パネルコンポーネント: 再利用可能性を損なわないようパネル側には手を加えない
