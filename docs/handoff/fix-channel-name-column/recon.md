# recon: pipeline-summary API 本番障害（sc.channel_name カラム名誤り）

## 現象

PR #3818 マージ直後に本番で「データの取得に失敗しました」エラーが発生。

## 根拠コード

- `backend/app/services/tcg_analysis_dashboard_svc.py:199` — `sc.channel_name` を参照
- `migrations/20260921_110000_pipeline_tables_public.sql:11` — `channel VARCHAR(50)` と定義

## 不一致

| コード参照 | テーブル定義 |
|-----------|------------|
| `sc.channel_name` | `channel` |
| `GROUP BY sc.channel_name` | `GROUP BY sc.channel` |

## 対象ADR

なし（migration 定義との整合修正のみ）

## 影響範囲

`get_pipeline_summary()` の section 9（直近抽出ジョブ10件）のみ。
他の API エンドポイント・テーブル・ビジネスロジックへの影響なし。
