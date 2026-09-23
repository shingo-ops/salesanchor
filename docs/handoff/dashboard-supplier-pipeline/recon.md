# recon: dashboard-supplier-pipeline

## 対象ADR
- ADR-067: UIガバナンス（デザイントークン・金型コンポーネント）
- ADR-027: i18n強制

## 既存実装の現在地

### バックエンド

- `backend/app/routers/tcg_analysis_dashboard.py` — 既存ルーター。`/tcg/analysis-dashboard/*` エンドポイント群
- `backend/app/services/tcg_analysis_dashboard_svc.py` — 既存サービス。KPIカード・トレンドデータ取得関数あり

### フロントエンド

- `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx` — 4タブ表示コンポーネント（約500行）
- `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.css` — 既存スタイル

### i18n

- `frontend/src/locales/ja.json` — `analysisDashboard` 配下にキーあり
- `frontend/src/locales/en.json` — 同上

## 問題の把握

現在のダッシュボードは全体平均値のみ表示（抽出成功率 88.5% 等）。
実際には 67% のデータが配信に届いていない問題を隠している。

提供者ごとの状況・脱落理由を可視化し、即座に対処できるようにする。
