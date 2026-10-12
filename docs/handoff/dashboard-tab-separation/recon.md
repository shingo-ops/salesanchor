---
title: "LINE解析ダッシュボード タブ分離"
---

## 調査結果

### 問題
4タブのダッシュボードで、インポートタブに抽出・解析の問題が混在表示されていた。
各タブが自分の担当工程の問題だけを表示すべき。

### 現状確認
- `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:2` — 4タブ構成（Import/Extraction/Analysis/Distribution）
- `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:100` — Import tab: extraction_error フィールド参照（越権）
- `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:208` — orphan_count フィールド（Import tab用）
- `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:617` — orphanCount > 0 警告表示ロジック
- `backend/app/routers/tcg_analysis_dashboard.py:5` — GET /api/v1/tcg/analysis-dashboard/pipeline-summary
- `backend/app/routers/tcg_analysis_dashboard.py:94` — extraction_by_supplier フィールド定義
- `backend/app/routers/tcg_supplier_quality.py:65` — GET /tcg/supplier-quality-summaries

### FK chain（extraction → supplier）
extraction_jobs.source_message_id → source_messages.supplier_channel_id → supplier_channels.supplier_id → suppliers
全リンク `migrations/20260921_110000_pipeline_tables_public.sql:79` で確認済み（extraction_jobs テーブル定義）

### 既存API
- `backend/app/routers/tcg_supplier_quality.py:65` — GET /tcg/supplier-quality-summaries — 提供者別の解析品質データ（SSOT、再利用）
- `backend/app/routers/tcg_analysis_dashboard.py:103` — GET /tcg/analysis-dashboard/pipeline-summary（拡張対象）

### 期間セレクタ追加 (2026-09-25)

- `backend/app/services/tcg_analysis_dashboard_svc.py:221` — `if not (1 <= days <= 90)` → days上限が90に制限されていた
- `backend/app/services/tcg_analysis_dashboard_svc.py:366` — `min(int(days), 90)` → import_trendも90上限
- `backend/app/routers/tcg_analysis_dashboard.py:200` — `Query(default=7, ge=1, le=90)` → import-trendエンドポイントのQuery制約
- `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:321` — `trend?days=7` ハードコード
- `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:345` — `import-trend?days=7` ハードコード
- `frontend/src/components/Select.tsx:34` — `SelectControl` (bare select, size="sm") 利用可能 ✅
- `frontend/src/locales/ja.json:4028` — `"trendTitle": "7日間のトレンド"` → suffix化対象
