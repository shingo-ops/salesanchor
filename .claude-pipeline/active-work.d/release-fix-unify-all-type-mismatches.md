# release-fix-unify-all-type-mismatches

**ブランチ**: release/fix-unify-type-mismatch-v2
**PR**: #3674
**状態**: OPEN (Ready for review)
**作成日**: 2026-09-22

## 目的

Phase 2a マイグレーション (`20260914_140000_unify_tcg_products_to_public.sql`) の UUID→INTEGER 型不整合を修正する。

## 調査結果

| カラム | tenant_004.tcg_products 型 | public.products 型 | 変換 migration | 対応 |
|--------|---------------------------|-------------------|----------------|------|
| `work_id` | UUID | INTEGER | 20260919_010000 | PR #3672 で NULL::INTEGER ガード済み |
| `product_category_id` | UUID | INTEGER | 20260920_010000 | PR #3674 で NULL::INTEGER ガード追加 |
| `division_id` | UUID | UUID | なし（product_kind_id が別途追加） | 対応不要 |
| `manufacturer_id` | UUID | UUID | なし | 対応不要 |

## 変更内容

- `migrations/20260914_140000_unify_tcg_products_to_public.sql`: `_product_category_id_is_uuid` ガードを追加し、3分岐に拡張

## GO 記録

- GO発行者: Shingo (shingo-ops)
- GO日時: 2026-09-22
- GO原文: GO #3674
