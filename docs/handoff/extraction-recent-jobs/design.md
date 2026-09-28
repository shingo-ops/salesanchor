# design: extraction-recent-jobs

## KGI

抽出タブの段3テーブルが「直近10件の個別ジョブ」を新しい順で表示し、各行に提供者名・抽出数・ステータスバッジ・日時（時間含む）が表示される。

## KPI / 受入基準

| 基準 | 検証方法 |
|------|----------|
| pipeline-summary API が recent_extraction_jobs を返す | API レスポンスに `recent_extraction_jobs` 配列が存在する |
| 直近10件が created_at DESC 順 | テーブル先頭行が最新ジョブ |
| 日時が「2026年9月28日 14:30」形式 | ブラウザで JST 時間付きで表示される |
| ステータスBadgeが正しい色 | done=success(緑), error=danger(赤), empty=warning(黄) |
| 既存タブ（import/analysis/distribution）に影響なし | 他タブの表示が変わらない |

## 設計方針

### バックエンド

- `PipelineSummaryResponse` に `recent_extraction_jobs: list[RecentExtractionJobItem]` を追加（additive-only）
- SQL は extraction_jobs → extraction_items（COUNT） → source_messages → supplier_channels の LEFT JOIN
- ORDER BY ej.created_at DESC LIMIT 10

### フロントエンド

- `RecentExtractionJob` 型を追加、`PipelineSummary` に `recent_extraction_jobs` フィールドを追加
- 既存の `trendColumns`（TrendDay 用）を `recentJobColumns`（RecentExtractionJob 用）に置き換え
- 段3テーブルのデータソースを `trend` から `data.recent_extraction_jobs` に変更
- trend は段2の推移グラフで引き続き使用するため props から削除しない

## recon 参照

`docs/handoff/extraction-recent-jobs/recon.md`

## 外部事例

なし（既存 recent_imports パターン踏襲）

## 守り手

- ADR-027: i18n — 全文字列は t() 経由
- ADR-067: デザイントークン — 色は var(--color-*) のみ
- ADR-144: UI金型 — Card/Badge/DataTable のみ

## 弊害・リスク

- 既存の `extractionTrendDay`/`extractionTrendTotal`/`extractionTrendDone`/`extractionTrendError` i18n キーを削除するが、AnalysisDashboardPanel.tsx 以外でこれらキーを使用している箇所はなし（grep 確認済み）
- DB JOIN が増えるが LIMIT 10 のためパフォーマンス影響は軽微
