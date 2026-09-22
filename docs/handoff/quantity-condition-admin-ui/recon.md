# recon — quantity-condition-admin-ui

**仕事名**: quantity-condition-admin-ui
**日付**: 2026-09-22
**対象ADR**: ADR-027, ADR-144
**担当**: Hikky-dev

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `backend/app/routers/super_admin_condition_defs.py:1` | 状態定義マスタ CRUD ルーター実装済み |
| `backend/app/routers/super_admin_quantity_units.py:1` | 販売単位マスタ CRUD ルーター実装済み |
| `backend/app/schemas/quantity_unit.py:42` | QuantityUnitWithCountsResponse スキーマ定義済み |
| `backend/app/schemas/quantity_unit.py:75` | ConditionDefResponse スキーマ定義済み |
| `frontend/src/pages/super-admin/components/QuantityUnitsMasterPanel.tsx:52` | 既存パネルコンポーネント |
| `frontend/src/pages/super-admin/AnalysisRulesPage.tsx:33` | QuantityUnitsMasterPanel 既に組み込み済み |
| `frontend/src/pages/super-admin/components/AnalysisRulesSidebar.tsx:10` | サイドバーキー型定義 |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | ConditionDefsMasterPanel の新規作成が必要か | AnalysisRulesPage.tsx を確認→未組み込みのため作成必要 | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み
