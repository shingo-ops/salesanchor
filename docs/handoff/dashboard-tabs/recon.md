# Dashboard Tabs — Recon

## 調査日: 2026-09-20

### パイプライン4工程のテーブル

| 工程 | テーブル | 主要カラム |
|------|---------|-----------|
| Import | import_jobs, source_messages | status, review_status, message_count, unresolved_count |
| Extraction | extraction_jobs, extraction_items, extraction_attempts | status, error_message, started_at |
| Analysis | analysis_results, analysis_runs | pid_resolved, unit_resolved, needs_review |
| Distribution | tcg_distribution_targets, tcg_distribution_settings | is_active, last_distributed_at, last_distributed_count |

### 既存コード

- `backend/app/services/tcg_analysis_dashboard_svc.py:15` — get_pipeline_summary()
- `backend/app/services/tcg_analysis_dashboard_svc.py:183` — get_pipeline_trend()
- `backend/app/services/tcg_analysis_dashboard_svc.py` (新規) — get_import_summary(), get_distribution_summary()
- `backend/app/routers/tcg_analysis_dashboard.py:85` — /pipeline-summary エンドポイント
- `backend/app/routers/tcg_analysis_dashboard.py:109` — /trend エンドポイント
- `backend/app/routers/tcg_analysis_dashboard.py:169` (新規) — /import-summary エンドポイント
- `backend/app/routers/tcg_analysis_dashboard.py:182` (新規) — /distribution-summary エンドポイント
- `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:47` — DashboardTab 型定義
- `frontend/src/components/Tabs.tsx:48` — Tabs 金型コンポーネント

### ADR検索結果

- ADR-027: i18n強制 — 全UI文字列は t("key") 経由
- ADR-067: デザイントークン強制 — 全色・サイズはCSS変数経由
- ADR-144: UIガバナンス — Tabs / Card / Badge / DataTable / recharts 金型のみ

### 変更前後の構成

| 項目 | 変更前 | 変更後 |
|------|--------|--------|
| 画面構成 | 単一パネル（抽出+解析混在） | 4タブ（Import/Extraction/Analysis/Distribution） |
| APIエンドポイント | /pipeline-summary, /trend | +/import-summary, +/distribution-summary |
| データ読み込み | 全データ一括 | タブ初回訪問時の遅延読み込み |
| 型安全 | 暗黙的 | DashboardTab 型で4タブを型安全に管理 |
