# recon — ダッシュボードルーティング修正

**仕事名**: ダッシュボードデフォルトタブ変更＋セクション状態URL保持  
**日付**: 2026-09-25  
**対象ADR**: なし（UX改善・ロジック修正のみ）  
**担当**: Hikky-dev

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:300` | `activeTab` の初期値が `"extraction"` → `"import"` に変更 |
| `frontend/src/pages/super-admin/AnalysisRulesPage.tsx:14` | `useSearchParams` を `react-router-dom` から追加 import |
| `frontend/src/pages/super-admin/AnalysisRulesPage.tsx:117` | `initialSection` を URL searchParams から読み込み |
| `frontend/src/pages/super-admin/AnalysisRulesPage.tsx:122` | `handleSectionChange` でセクション変更時に URL を更新 |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | `useSearchParams` が既存コードで使われているか | grep 確認 → `useNavigate` のみ使用、競合なし | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み
