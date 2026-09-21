# Design: fix-migration-guards-v2

## 変更概要

PR #3641 が見落とした2マイグレーションファイルにテーブル存在ガードを追加する。

## 対象ADR
- ADR-082: `scripts/run_all_migrations.sh` 冪等性要件

## 変更内容

### migrations/20260901_120000_add_unit_inference_columns_t004.sql

**変更前**: スキーマガードのみ（テーブルは確認しない）
**変更後**: スキーマガード → テーブル存在チェック → 列存在チェック

```sql
IF NOT EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = _schema AND table_name = 'analysis_results'
) THEN
    RAISE NOTICE 'migration 20260901_120000: table %.analysis_results does not exist, skipping', _schema;
    RETURN;
END IF;
```

### migrations/20260913_150000_tcg_empty_box_condition.sql

**変更前**: table_count <> 6 で RAISE EXCEPTION（conditions=1のみ残存するため必ず失敗）
**変更後**: パイプラインテーブルが全削除済みの場合は RETURN

```sql
IF to_regclass('tenant_004.analysis_results') IS NULL
   AND to_regclass('tenant_004.extraction_items') IS NULL
   AND to_regclass('tenant_004.extraction_jobs') IS NULL
   AND to_regclass('tenant_004.source_messages') IS NULL
THEN
    RAISE NOTICE 'empty box: pipeline tables dropped (20260921_050000), skipping';
    RETURN;
END IF;
```

**部分削除の場合**: AND 条件が FALSE になるため `RAISE EXCEPTION 'incomplete TCG structure'` が維持される。
既存テスト `test_migration_partial_structure_rejects_before_import` の動作は変わらない。

## KGI/KPI

| 基準 | 検証方法 |
|------|----------|
| `run_all_migrations.sh` が最後まで完走する | deploy.yml の「Run database migrations」ステップが success になる |
| migration 191 でエラーが出ない | deploy ログに `20260901_120000` エラーなし |
| migration 20260913_150000 でエラーが出ない | deploy ログに `empty box: incomplete TCG structure` エラーなし |

## 外部・過去事例の参照と我々への応用

PostgreSQL 冪等マイグレーションの標準パターン（Flyway/Liquibase 等）では、DDL 実行前に対象オブジェクトの存在を確認してからスキップする設計を採用している。`IF EXISTS` / `IF NOT EXISTS` 修飾子や `to_regclass()` を使った事前確認がその実装例である。本修正はこのパターンを適用し、DROP 済みテーブルへの ALTER TABLE を安全にスキップさせる。

PR #3641 が同じ問題を修正した手法（`to_regclass` ガード）との一貫性を保ちつつ、`information_schema.tables` による確認を追加することでより明示的な実装にした。

## 維持の仕組み

- migration-test.yml が CI で冪等実行テストを行う（tenant_004 削除後の再実行シナリオ含む）
- 今後のマイグレーションで dropped テーブルを参照する場合は同様のテーブル存在ガードを必須とする（`docs/adr/ADR-082` 参照）

## 守り手
- to_regclass() / information_schema.tables によるテーブル存在確認
- 既存テスト: test_migration_partial_structure_rejects_before_import （部分削除は依然 EXCEPTION）
