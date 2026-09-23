# 設計 — fix-supplier-pipeline-sql

**対象ADR**: ADR-138  
**recon**: docs/handoff/fix-supplier-pipeline-sql/recon.md  
**日付**: 2026-09-23  
**担当**: Planner

---

## 外部・過去事例の参照と我々への応用

- 該当なし：今回は既存SQLのJOINパス修正のみ。ERに従いカラム名を修正するだけであり、外部事例を参照する必要はないと判断。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| `GET /api/tcg/analysis-dashboard/supplier-pipeline` が 200 を返す | 本番API動作確認（curlまたはPython asyncio） |
| `UndefinedColumnError` が発生しない | 本番ログ確認 |
| 提供者別の analysis 集計値が返る | APIレスポンスのJSON確認 |

---

## 技術 How・KPI

- KPI: supplier-pipeline エンドポイントの 500 エラー率 = 0%（修正前 100%）
- 技術選択: SQLのJOINパスを `extraction_jobs → extraction_items → analysis_results` に修正
  - `extraction_items` テーブルを経由する LEFT JOIN を追加
  - `ar.extraction_item_id = ei.id` で結合（analysis_results の正しい外部キー）

---

## 弊害・トレードオフ

- リスクなし：SELECT専用クエリのJOINパス修正のみ。データ書き込みなし。

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | `tcg_analysis_dashboard_svc.py` の SQL を修正 | Generator |
| 2 | CI 通過確認 | Generator |
| 3 | 本番デプロイ後の API 動作確認 | Generator |

---

## 継続

- 完了後の監視: 本番ログで UndefinedColumnError が再発しないことを確認
- 次フェーズへの引き継ぎ: なし（一度限りの修正）
