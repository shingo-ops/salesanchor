# recon: extraction-recent-jobs

## 調査対象

LINE解析ダッシュボード抽出タブの総数テーブルを日別集計から個別ジョブリストに変更。

## 既存 ADR 検索結果

- ADR-027: UI国際化（i18n）— 全文字列は t() 経由必須
- ADR-067: デザイントークン強制 — 色は CSS 変数のみ
- ADR-144: UI金型遵守 — Card/Badge/DataTable のみ使用可

## 変更対象ファイル（フルパス:行番号）

- `backend/app/routers/tcg_analysis_dashboard.py:82` — ExtractionBySupplierItem 直後に RecentExtractionJobItem モデル追加
- `backend/app/routers/tcg_analysis_dashboard.py:91` — PipelineSummaryResponse に recent_extraction_jobs フィールド追加
- `backend/app/services/tcg_analysis_dashboard_svc.py:187` — return 文の前に SQL クエリ追加
- `backend/app/services/tcg_analysis_dashboard_svc.py:217` — return 文に recent_extraction_jobs キー追加
- `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:175` — RecentExtractionJob インターフェース追加
- `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:182` — PipelineSummary に recent_extraction_jobs フィールド追加
- `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:1044` — trendColumns を recentJobColumns に置き換え
- `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:1144` — 段3テーブルを recent_extraction_jobs データ表示に変更
- `frontend/src/locales/ja.json:4371` — 旧キー4件削除、新キー10件追加
- `frontend/src/locales/en.json:4371` — 旧キー4件削除、新キー10件追加

## DB テーブル確認

- `public.extraction_jobs` — id, status, created_at, source_message_id 確認済み（既存クエリで参照）
- `public.extraction_items` — id, extraction_job_id 確認済み（既存クエリで参照）
- `public.source_messages` — id, supplier_channel_id 確認済み（既存クエリで参照）
- `public.supplier_channels` — id, channel_name 確認済み（`get_supplier_pipeline` の SELECT に channel_name カラムあり）

## 既存パターン

- `get_import_summary` 内の `recent_imports` 実装（tcg_analysis_dashboard_svc.py:319-346）を踏襲
- ImportTabContent のテーブル実装（AnalysisDashboardPanel.tsx:681-727）をパターンとして採用
