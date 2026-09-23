# Design: pipeline-drop-tenant004 (Step 5/5)

## 概要
tenant_004スキーマのパイプラインテーブル17本 + バックアップ2本をDROP。
ADR-1002のtenant_004 → publicスキーマ移行の最終ステップ。

## KGI
Steps 1-4完了後に `migrations/20260921_050000_drop_tenant004_pipeline_tables.sql` を適用し、
tenant_004スキーマにパイプライン系テーブルが存在しなくなること。

## KPI / 検証方法
| 基準 | 検証方法 |
|------|---------|
| DROP後にtenant_004の対象テーブルが消えている | `SELECT table_name FROM information_schema.tables WHERE table_schema='tenant_004' AND table_name IN (...)` で0件 |
| public側テーブルにデータが存在する | 各publicテーブルのCOUNT確認 |
| アプリケーションエラーなし | ヘルスチェックエンドポイント200 |

## DROP順序の設計根拠
FK依存の逆順でDROP:
1. 子テーブル（extraction_attempts, analysis_run_snapshots 等）を先にDROP
2. 親テーブル（extraction_jobs, analysis_runs, supplier_channels 等）を後にDROP

## 弊害・リスク
- 不可逆操作: バックアップ(pg_dump)確認後にのみ適用すること
- Steps 1-4未完了状態での適用は絶対禁止
- IF EXISTS により存在しないテーブルのDROPは安全にスキップ

## 外部・過去事例の参照と我々への応用
- PostgreSQL公式: DROP TABLE IF EXISTS は対象テーブルが存在しない場合もエラーにならない（冪等性確保）
- ADR-1002 Phase B/C (PR #3625, #3627) の実績: 同様のスキーマ移行パターンを踏襲
- 過去事例(adr090-pr4): tenant_productsのdeprecation時も同様の段階的DROP方式を採用

## 維持の仕組み
守り手: Shingo（PO）— DROP適用前のGO確認必須
- migration-guard CIが実行される
- 適用前にpg_dumpによるバックアップ確認
- Steps 1-4の完了チェックリストをPR本文で確認
