# design: pipeline-data-migrate (Step 3/5)

## 参照ADR
- ADR-100: `docs/adr/ADR-100-sa-ingestion-analysis-pipeline.md`

## あるべき姿
tenant_004 スキーマのパイプラインデータを public スキーマへ冪等にコピーし、
以降のアプリコードが public スキーマを参照できる状態にする。

## KGI / KPI

| 基準 | 検証方法 |
|------|---------|
| 17テーブル全ての行数が tenant_004 と public で一致する | スクリプト内の DO $$ ... $$ ブロックが RAISE NOTICE で全テーブルの行数を出力し、不一致があれば RAISE EXCEPTION でロールバック |
| 冪等（2回実行しても行数が変わらない） | ON CONFLICT DO NOTHING により重複行は無視される |
| 失敗時にデータが壊れない | 単一トランザクション（BEGIN/COMMIT）内で全INSERT。エラー時は自動ロールバック |

## 外部事例
PostgreSQL INSERT ... ON CONFLICT DO NOTHING を用いた冪等マイグレーションは公式ドキュメントで推奨されるパターン。
BIGSERIAL sequence のリセットには setval(seq, MAX(id)) を使用（PostgreSQL標準手順）。

## 弊害・リスク
- 実行時に tenant_004 への SELECT ロックが短時間発生するが、本番トラフィックへの影響は軽微
- public 側の FK 制約（conditions, products 等）が未充足の場合、analysis_results のINSERTが失敗する可能性。Step 1 DDL で constraints を確認済み前提

## 守り手
- ON_ERROR_STOP=1: 最初のエラーでpsqlが停止
- BEGIN/COMMIT: 全テーブルのINSERTが単一トランザクション
- DO $$ ... $$ 事前チェック: publicテーブルが存在しない場合は即RAISE EXCEPTION
- DO $$ ... $$ 事後検証: 行数不一致は RAISE EXCEPTION でロールバック

## 計画
1. `bash scripts/migrate-pipeline-data-to-public.sh --dry-run` でSQL確認
2. Step 1 DDL デプロイ済みを確認
3. `bash scripts/migrate-pipeline-data-to-public.sh` で実行
4. RAISE NOTICEの出力で17テーブル全件一致を確認
