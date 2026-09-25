# Recon: Dashboard Chart Period Selector

recon: docs/handoff/dashboard-chart-period/recon.md
作業日: 2026-09-25

## 現在地把握

### 課題

LINE解析ダッシュボードのチャートが7日間にハードコードされており、ユーザーが期間を変更できない。

### 調査結果（事実）

#### バックエンド

- `backend/app/services/tcg_analysis_dashboard_svc.py:221` — `if not (1 <= days <= 90)` → days上限が90に制限（pipeline_trend）
- `backend/app/services/tcg_analysis_dashboard_svc.py:366` — `min(int(days), 90)` → import_trendも90上限にclamp
- `backend/app/routers/tcg_analysis_dashboard.py:200` — `Query(default=7, ge=1, le=90)` → import-trendエンドポイントのQuery制約が90まで

#### フロントエンド

- `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:321` — `trend?days=7` ハードコード（pipeline-trend呼び出し）
- `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:345` — `import-trend?days=7` ハードコード（import-trend呼び出し）
- `frontend/src/locales/ja.json:4028` — `"trendTitle": "7日間のトレンド"` → 動的な期間表示が必要

#### デザインシステム

- `frontend/src/components/Select.tsx:34` — `SelectControl` (bare select, size="sm") 利用可能 ✅
- ADR-144 UIガバナンス: 生select禁止 → SelectControl使用が必須

#### 既存ADR

- ADR-027: i18n強制（全UI文字列はt()経由必須）
- ADR-144: UIガバナンス（生select禁止・SelectControl使用必須）
- 期間セレクタ専用ADRなし

## まとめ

- チャート期間はバックエンドもフロントエンドも7日固定
- バックエンドAPIはdaysパラメータを受け付けるが上限90
- フロントエンドはdaysをハードコードしてAPIを呼ぶ
- SelectControlコンポーネントは利用可能
