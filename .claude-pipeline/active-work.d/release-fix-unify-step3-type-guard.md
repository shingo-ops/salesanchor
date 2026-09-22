# release/fix-unify-step3-type-guard

## 目的
Phase 2a Step 3 の FK 張替え処理に `product_id` UUID 型チェックガードを追加。

## 対象ファイル
- `migrations/20260914_140000_unify_tcg_products_to_public.sql`（Step 3 に型ガード追加）

## 変更内容
- DECLARE に `_pid_type OID;` を追加
- 4テーブル（product_search_keywords / product_exclude_keywords / products_logistics / analysis_results）の新FK作成ブロック直前に `pg_attribute` 型チェックを追加
- UUID型でなければ `RAISE NOTICE` でスキップ（冪等）

## ステータス
IN_PROGRESS
