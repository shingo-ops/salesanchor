# recon — DataTable 標準化 フェーズ2（管理系テーブルロールアウト）

**仕事名**: DataTable 標準化 フェーズ2  
**日付**: 2026-06-11  
**対象ADR**: ADR-067  
**担当**: architect

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `frontend/src/components/DataTable.tsx:85` | `rowClassName?: (row: T) => string` prop が定義済み |
| `frontend/src/components/DataTable.tsx:245` | `rowClassName(row)` が `<tr>` の className に適用済み |
| `frontend/src/components/DataTable.css:152` | `.comp-table__row--danger` / `.comp-table__row--warning` 追加済み（danger-bg/warning-bg 参照） |
| `frontend/src/index.css:45` | `--danger-bg: #fed7d7` CSS 変数定義済み |
| `frontend/src/index.css:47` | `--warning-bg: #fefcbf` CSS 変数定義済み |
| `frontend/src/pages/super-admin/SupplierParseStatsTab.tsx:9` | DataTable import 済み |
| `frontend/src/pages/super-admin/SupplierParseStatsTab.tsx:81` | `columns: DataTableColumn<ParseStatRow>[]` 定義済み |
| `frontend/src/pages/super-admin/SupplierParseStatsTab.tsx:130` | `<DataTable<ParseStatRow>` 使用済み（raw `<table>` 除去済み） |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | `rowClassName` prop が DataTable に存在するか | `DataTable.tsx:85` で確認 | ✅ 解消済み |
| 2 | `--danger-bg` / `--warning-bg` CSS 変数が定義済みか | `index.css:45,47` で確認 | ✅ 解消済み |
| 3 | パイロット対象以外で `rowClassName` 未対応テーブルがあるか | Batch 1〜3 は rowClassName 不要（ハイライトなし） | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み

---

## 補足

- フェーズ2 対象: 管理系テーブル 13件（例外 4件除く）
- 例外 4件（PO承認済み）: InventoryPage, ProductMastersTab, ParseReviewPage, InventoryVisibilityPage
- recon-phase1.md はフェーズ1（顧客向けページ）の調査として別途存在
