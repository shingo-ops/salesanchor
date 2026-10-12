# design: fix-dashboard-column

**対象ADR**: ADR-100（sa-ingestion-analysis-pipeline — 解析パイプライン管理）  
**recon**: docs/handoff/fix-dashboard-column/recon.md  

## 問題
tcg_analysis_dashboard_svc.py のSQL文字列内で存在しないカラム名を参照しており、本番APIが「データの取得に失敗しました」エラーを返す。

## 変更内容

| 箇所 | 変更前 | 変更後 | 根拠 |
|---|---|---|---|
| extraction_attempts ORDER BY | `created_at` | `started_at` | DB実測（docs/handoff/fix-dashboard-column/recon.md）|
| analysis_results ORDER BY | `created_at` | `computed_at` | DB実測（docs/handoff/fix-dashboard-column/recon.md）|

## 基準・検証方法

| 基準 | 検証方法 |
|---|---|
| API `/api/tcg/dashboard/pipeline-summary` が200を返す | 本番デプロイ後にcurlで確認 |
| engine_version フィールドが返却される | レスポンスJSONのengine.current_engine_versionが非null |

## 外部・過去事例の参照と我々への応用
SQLカラム名誤りはよくある実装バグ。PostgreSQL `information_schema.columns` でDB DDLを直接確認するアプローチが標準的な解決策。本件もVPS本番DBに対して実測確認を行い、正しいカラム名を特定した。

## 影響範囲
- 呼び出し元: backend/app/routers/tcg_analysis_dashboard.py（router）
- 変更ファイル: backend/app/services/tcg_analysis_dashboard_svc.py（2行のみ）
- 触らない範囲: 他のサービス・テーブル・マイグレーション

## 戻し方
git revert で即時ロールバック可能（DDL変更なし）

## 維持の仕組み
守り手: ruff lint/format通過確認済み。本番DBのカラム定義がマイグレーションで変更される際は、同ファイルのSQL文字列も合わせて変更すること。
