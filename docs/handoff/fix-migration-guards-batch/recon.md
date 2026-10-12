# recon: fix-migration-guards-batch

## 問題
1. `migrations/20260910_200000_tcg_condition_note_delivery_t004.sql:15-18`: table_count=1 で RAISE EXCEPTION（tenant_004 テーブル一部削除済み）
2. `migrations/20260921_010000_drop_analysis_rule_tables.sql:22-34`: tenant_004 スキーマ不存在時に DROP TABLE IF EXISTS がエラー

## 修正
- 両ファイルにスキップガードを追加（テーブル/スキーマ不存在時は NOTICE + RETURN）
