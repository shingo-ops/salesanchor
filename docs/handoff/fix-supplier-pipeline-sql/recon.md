# recon — fix-supplier-pipeline-sql

**仕事名**: fix-supplier-pipeline-sql  
**日付**: 2026-09-23  
**対象ADR**: ADR-138  
**担当**: architect

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `backend/app/services/tcg_analysis_dashboard_svc.py:362` | `get_supplier_pipeline()` 関数が定義済み |
| `backend/app/services/tcg_analysis_dashboard_svc.py:404` | LEFT JOIN extraction_jobs — source_message_id で結合 |
| `backend/app/services/tcg_analysis_dashboard_svc.py:406` | LEFT JOIN analysis_results — extraction_item_id で結合 |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | analysis_results に source_message_id カラムが存在するか | ログ確認: asyncpg.exceptions.UndefinedColumnError | ✅ 解消済み（存在しない） |
| 2 | 正しい結合パスは何か | ERを確認: extraction_jobs → extraction_items → analysis_results | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み

---

## 補足

#3710 デプロイ後に `/api/tcg/analysis-dashboard/supplier-pipeline` が 500 エラーを返した。
ログに `asyncpg.exceptions.UndefinedColumnError: column ar.source_message_id does not exist` が記録されていた。
analysis_results テーブルには source_message_id カラムは存在せず、
extraction_items を経由する JOIN が必要。
