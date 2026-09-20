# design: 解析パイプラインダッシュボード (Phase A)

recon: docs/handoff/analysis-dashboard/recon.md

## KGI
解析管理ページを開いた際、デフォルト画面として抽出/解析パイプラインの健全性KPIが表示される。

| 基準 | 検証方法 |
|------|----------|
| ダッシュボードがサイドバー先頭に表示 | ブラウザで /super-admin/analysis-rules を開き「ダッシュボード」が先頭に見える |
| KPI 5枚のカードに数値が表示 | 0件でもエラーにならない（APIが200を返す） |
| アラートバッジが正しく表示 | stale/missing/pending が 0 の場合は非表示 |
| エラーテーブルにデータが表示 | 直近10件のエラーリスト。エラーなし時は「エラーはありません」 |

## 変更ファイル一覧

### 新規作成
- `backend/app/routers/tcg_analysis_dashboard.py` — GET /api/v1/tcg/analysis-dashboard/pipeline-summary
- `backend/app/services/tcg_analysis_dashboard_svc.py` — SELECT only 集計サービス
- `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx` — ダッシュボードパネル
- `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.css` — スタイル（全デザイントークン使用）

### 変更
- `backend/app/main.py` — ルーター import + include_router 追加
- `frontend/src/pages/super-admin/components/AnalysisRulesSidebar.tsx` — "dashboard" キー追加
- `frontend/src/pages/super-admin/AnalysisRulesPage.tsx` — import + 表示条件 + defaultActiveSection変更
- `frontend/src/locales/ja.json` — i18nキー25件追加
- `frontend/src/locales/en.json` — i18nキー25件追加

### 削除するファイル
なし

## 設計方針
- DB変更なし（既存テーブルへの SELECT のみ・SSOT遵守）
- ADR-027(i18n) / ADR-067(デザイントークン) / ADR-144(UIガバナンス) 準拠
- 金型: Card(metric) / Badge / DataTable 使用
- Phase B(仕入元別) / Phase C(時系列) は後続PRで対応

## 外部・過去事例の参照と我々への応用
- Grafana Dashboard パターン（KPIカード + アラート + テーブル構成）を参照
- 我々への応用: 既存の Card(metric)/Badge/DataTable 金型をそのまま使用し、パターン踏襲しながらデザインシステム準拠を維持する

## 維持の仕組み

守り手: backend/app/routers/tcg_analysis_dashboard.py（require_super_admin 依存注入で super-admin のみアクセス可。DBスキーマ変更時はサービス層 backend/app/services/tcg_analysis_dashboard_svc.py のSQLを追従要）
