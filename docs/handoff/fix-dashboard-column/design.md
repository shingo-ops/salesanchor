# design: fix-dashboard-column

## 問題
`tcg_analysis_dashboard_svc.py` のSQL文字列内で存在しないカラム名を参照しており、本番APIが「データの取得に失敗しました」エラーを返す。

## 変更内容

| 箇所 | 変更前 | 変更後 | 根拠 |
|---|---|---|---|
| extraction_attempts ORDER BY | `created_at` | `started_at` | DB実測（recon.md）|
| analysis_results ORDER BY | `created_at` | `computed_at` | DB実測（recon.md）|

## 基準・検証方法

| 基準 | 検証方法 |
|---|---|
| API `/api/tcg/dashboard/pipeline-summary` が200を返す | 本番デプロイ後にcurlで確認 |
| `engine_version` フィールドが返却される | レスポンスJSONのengine.current_engine_versionが非null |

## 外部事例
SQLカラム名誤りはよくある実装バグ。DB DDL確認による修正が標準アプローチ。

## 影響範囲
- 呼び出し元: `backend/app/routers/tcg_analysis_dashboard.py`（router）
- 変更ファイル: `backend/app/services/tcg_analysis_dashboard_svc.py`（2行のみ）
- 触らない範囲: 他のサービス・テーブル・マイグレーション

## 戻し方
git revert で即時ロールバック可能（DDL変更なし）

## 守り手
ruff lint/format通過確認済み
