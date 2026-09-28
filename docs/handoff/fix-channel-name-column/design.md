# design: pipeline-summary API カラム名修正

## 対象ADR

なし（migration 定義との整合修正のみ）

## 変更

| 修正箇所 | 変更前 | 変更後 |
|---------|--------|--------|
| SELECT 句 | `sc.channel_name` | `sc.channel AS channel_name` |
| GROUP BY 句 | `sc.channel_name` | `sc.channel` |

## 基準と検証方法

| 基準 | 検証方法 |
|------|---------|
| `GET /api/v1/tcg/analysis-dashboard/pipeline-summary` が 200 を返す | デプロイ後に curl で確認 |

## 外部事例

PostgreSQL では存在しないカラムを参照すると `ERROR: column "xxx" does not exist` で 500 になる。

## 維持の仕組み

migration ファイルとサービスコードのカラム名照合は CI での自動チェックなし。
将来的には SQLAlchemy ORM モデルを使えば型チェック時に検知可能。
