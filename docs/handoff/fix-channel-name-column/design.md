# design: pipeline-summary API カラム名修正

## 対象ADR

既存機能のバグ修正のため新規ADRなし。関連: ADR-100（取り込み・解析パイプライン）

## 変更

| 修正箇所 | 変更前 | 変更後 |
|---------|--------|--------|
| SELECT 句 | `sc.channel_name` | `sc.channel AS channel_name` |
| GROUP BY 句 | `sc.channel_name` | `sc.channel` |

## 基準と検証方法

| 基準 | 検証方法 |
|------|---------|
| `GET /api/v1/tcg/analysis-dashboard/pipeline-summary` が 200 を返す | デプロイ後に curl で確認 |

## 外部・過去事例の参照と我々への応用

PostgreSQL では存在しないカラムを参照すると `ERROR: column "xxx" does not exist` で 500 になる（公式ドキュメント確認済み）。
migration ファイル（`20260921_110000_pipeline_tables_public.sql:11`）でカラム名 `channel` と定義済みだが、実装コードで `channel_name` と誤記したことで本障害が発生した。
今後: SQL クエリをコード内に直書きする場合は migration 定義との照合を PRレビュー時に行うことで再発防止できる。

## 維持の仕組み

守り手: PR レビュー時に migration ファイルとコードのカラム名を照合する（人的確認）。
将来的には SQLAlchemy ORM モデルを使えば型チェック時に検知可能。
