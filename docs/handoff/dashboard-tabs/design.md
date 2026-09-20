# Dashboard Tabs — Design

**対象ADR**: ADR-027, ADR-067, ADR-144
**recon**: docs/handoff/dashboard-tabs/recon.md

## 目的

パイプライン4工程（インポート・抽出・解析・配信）それぞれの数値をタブ切り替えで見える化する。
既存の単一パネルを4タブに分割し、各工程の健全性を独立して観察できるようにする。

## 変更概要

| 項目 | 変更前 | 変更後 |
|------|--------|--------|
| 画面構成 | 単一パネル（抽出+解析混在） | 4タブ（Import/Extraction/Analysis/Distribution） |
| API | /pipeline-summary, /trend の2エンドポイント | +/import-summary, +/distribution-summary を追加（計4本） |
| データ読み込み | 全データ一括 | タブ初回訪問時の遅延読み込み |
| 型安全 | 暗黙的 | DashboardTab 型で4タブを型安全に管理 |

## 実装済みファイル

### バックエンド

- `backend/app/services/tcg_analysis_dashboard_svc.py` — get_import_summary(), get_distribution_summary() 追加
- `backend/app/routers/tcg_analysis_dashboard.py` — /import-summary, /distribution-summary エンドポイント追加

### フロントエンド

- `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx` — 4タブ構成に再設計
- `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.css` — タブ対応スタイル追加
- `frontend/src/locales/ja.json` — Import/Distribution タブのi18nキー追加
- `frontend/src/locales/en.json` — 同上（ja.jsonと同一キー）

## 受入条件

| 基準 | 検証方法 |
|------|---------|
| 4タブが表示される | 画面上部にImport/Extraction/Analysis/Distributionタブが見える |
| タブ切り替えで内容が変わる | 各タブクリックでKPIカード・テーブルの内容が変わる |
| Import タブにインポート履歴が表示 | import_jobs の件数・未解決率・最近のインポート一覧が表示される |
| Distribution タブに配信先が表示 | tcg_distribution_targets の名前・最終配信日・件数が表示される |
| 既存の信号灯・CTA・トレンドグラフが維持 | Extraction/Analysis タブで従来の機能が使える |
| i18nキー完全一致 | ja.json と en.json の追加キーが一致する |

## 外部事例

該当なし（既存ダッシュボードのタブ分割のみ、新しい技術選定なし）

## 守り手

- `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:47` — DashboardTab 型で4タブを型安全に管理（文字列リテラル型）
- `backend/app/services/tcg_analysis_dashboard_svc.py:1` — SELECT のみ制約（INSERT/UPDATE/DELETE/DDL 実行しない）
- `backend/app/routers/tcg_analysis_dashboard.py:91` — require_super_admin で全エンドポイントを保護
- 遅延読み込みにより、Import/Distribution は初回タブ訪問時のみAPIコール（パフォーマンス影響を最小化）
