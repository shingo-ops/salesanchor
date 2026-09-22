# recon — fix-unify-step3-type-guard

**仕事名**: fix-unify-step3-type-guard  
**日付**: 2026-09-22  
**対象ADR**: ADR-1002  
**担当**: Planner

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `migrations/20260914_140000_unify_tcg_products_to_public.sql:272` | Step 3 DO $step3$ ブロック開始 |
| `migrations/20260914_140000_unify_tcg_products_to_public.sql:273` | DECLARE ブロック — _pid_type OID 追加対象 |
| `migrations/20260914_140000_unify_tcg_products_to_public.sql:332` | 3-1 product_search_keywords の新FK作成ブロック（型ガード追加箇所） |
| `migrations/20260914_140000_unify_tcg_products_to_public.sql:390` | 3-2 product_exclude_keywords の新FK作成ブロック（型ガード追加箇所） |
| `migrations/20260914_140000_unify_tcg_products_to_public.sql:447` | 3-3 products_logistics の新FK作成ブロック（型ガード追加箇所） |
| `migrations/20260914_140000_unify_tcg_products_to_public.sql:504` | 3-4 analysis_results の新FK作成ブロック（型ガード追加箇所） |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | products_logistics.product_id は既にINTEGERか | ADR-1002 §Phase B 記述＋PR #3672 で確認 | ✅ 解消済み |
| 2 | analysis_results.product_id は既にINTEGERか | ADR-1002 §Phase B 記述で確認 | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み

---

## 補足

Step 2 の work_id に適用した型チェックパターン（PR #3672）と同一の pg_attribute 経由ガードを
Step 3 の4テーブル全てに適用する。冪等性のため、UUID型テーブルでもガードを通過してFK作成を実行する。
