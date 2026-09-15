# recon — ADR-1001 Phase 2b: Python API 配線変更

**仕事名**: ADR-1001 Phase 2b  
**日付**: 2026-09-14  
**対象ADR**: ADR-1001  
**担当**: architect

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `backend/app/services/tcg_product_master_svc.py:367` | create_product() の INSERT 先が tcg_products → public.products に変更対象 |
| `backend/app/services/tcg_product_detail_svc.py:43` | 商品詳細取得の JOIN 先テーブル確認 |
| `backend/app/services/tcg_product_import_svc.py:182` | CSV取込サービスの tcg_products 参照箇所 |
| `backend/app/services/tcg_analyzer_svc.py:80` | 分析サービスの商品コード→ID マッピング |
| `backend/app/services/tcg_product_roundtrip_svc.py:111` | ラウンドトリップの tcg_products 参照 |
| `backend/app/services/tcg_condition_review_svc.py:104` | コンディションレビューの商品参照 |
| `backend/app/services/tcg_parallel_report_svc.py:39` | 並列レポートの商品参照 |
| `backend/app/services/tcg_analysis_review_svc.py:39` | 分析レビューの商品参照 |
| `backend/app/services/tcg_unit_recovery_svc.py:263` | ユニット復旧の商品参照 |
| `backend/app/services/tcg_work_reference.py:52` | ワーク参照の商品参照 |
| `backend/app/services/tcg_distribution_svc.py:235` | 配分サービスの商品参照 |
| `backend/app/services/tcg_work_comparison_svc.py:126` | ワーク比較の商品参照 |
| `backend/app/routers/tcg_product_import.py:103` | ルーターの tcg_products SQL 参照 |
| `backend/app/tasks/tcg_mirror.py:123` | ミラータスクの tcg_products 参照 |
| `backend/app/tcg_config.py:20` | TCG_SCHEMA 定義元（tenant_004） |
| `migrations/20260914_140000_unify_tcg_products_to_public.sql:27` | Phase 2a: public.products への7カラム追加 |
| `migrations/062_create_inventory_movements_and_budget.sql:30` | public.products 元テーブル定義 |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | public.products の RLS が書込みをブロックするか | migration で SET LOCAL app.is_operator = 'true' を確認 | 解消済み |
| 2 | UUID→INTEGER の PK 型不一致 | tcg_uuid ブリッジカラムで解決（Phase 2a） | 解消済み |
| 3 | テスト環境で public.products が存在するか | test fixture の migrate() で作成を確認 | 解消済み |

**未解決ゼロ確認**: 全て解消済み
