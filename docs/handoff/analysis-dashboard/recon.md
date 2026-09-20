# recon: 解析パイプラインダッシュボード (Phase A)

## 調査日
2026-09-20

## 対象ADR
- ADR-027: UI国際化（i18n強制）
- ADR-067: デザイントークン強制
- ADR-144: UIガバナンス

## 既存コード調査

### 既存テーブル（SELECT対象）
- `backend/app/services/tcg_analysis_dashboard_svc.py:30-40` — extraction_jobs ステータス別集計
- `backend/app/services/tcg_analysis_dashboard_svc.py:52-65` — analysis_results 集計
- TCGスキーマ: `backend/app/tcg_config.py` の `TCG_SCHEMA` 変数参照

### 既存ルーター登録パターン
- `backend/app/main.py:97-130` — インポートブロック
- `backend/app/main.py:622-626` — include_router ブロック

### 既存サイドバー型定義
- `frontend/src/pages/super-admin/components/AnalysisRulesSidebar.tsx:11-25` — AnalysisRulesSidebarKey union型
- `frontend/src/pages/super-admin/components/AnalysisRulesSidebar.tsx:65-70` — groupAnalysisStatus グループ

### 既存パネル表示ロジック
- `frontend/src/pages/super-admin/AnalysisRulesPage.tsx:145-155` — activeSection 条件分岐

### 金型コンポーネント確認
- `frontend/src/components/Card.tsx` — Card コンポーネント（metric variant あり）
- `frontend/src/components/Badge.tsx` — Badge コンポーネント
- `frontend/src/components/DataTable.tsx` — DataTable コンポーネント

### i18n キー既存状態
- `frontend/src/locales/ja.json:3849-3853` — analysisRules.sidebar.* キー群
- `frontend/src/locales/en.json:3849-3853` — 同上英語版

## ADR検索結果
- `docs/adr/` grep: ADR-027, ADR-067, ADR-144 確認済み
- ADR-100 (TCGパイプライン), ADR-138/139 (ダッシュボード系) 参照済み

## 触れないファイル
- migrations/ — DB変更なし（既存テーブルへのSELECTのみ）
- deploy.yml — 不要
