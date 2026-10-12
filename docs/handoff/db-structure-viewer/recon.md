# recon: DB構造ビューア追加

## 対象ADR
- ADR-144: UIガバナンス（生select/input禁止・CSS変数必須）
- ADR-027: UI国際化（i18n強制）

## 既存パターン調査

### 参照したコンポーネント（file:line）
- `frontend/src/pages/super-admin/components/SupplierMasterPanel.tsx:73` — サイドツリー+テーブル構成の参照実装（SupplierMasterPanel関数）
- `frontend/src/pages/super-admin/components/SupplierMasterPanel.tsx:14` — DataTable金型インポート（既存パターン）
- `frontend/src/components/DataTable.tsx:1` — スプレッドシート形式テーブル（既存金型）
- `frontend/src/pages/super-admin/components/AnalysisRulesSidebar.tsx:32` — AnalysisRulesSidebarKey型（db-viewer追加先）
- `frontend/src/pages/super-admin/components/AnalysisRulesSidebar.tsx:122` — サイドメニュー db-viewer 項目追加位置
- `frontend/src/pages/super-admin/AnalysisRulesPage.tsx:47` — DbViewerPanel インポート
- `frontend/src/pages/super-admin/AnalysisRulesPage.tsx:201` — db-viewer パネル配線位置
- `backend/app/routers/super_admin_db_schema.py:14` — list_tables エンドポイント（information_schema.tables）
- `backend/app/routers/super_admin_db_schema.py:46` — list_columns エンドポイント（information_schema.columns）
- `backend/app/routers/super_admin_db_schema.py:147` — list_references エンドポイント（FK情報）
- `backend/app/main.py:94` — super_admin_db_schema ルーターインポート
- `backend/app/main.py:721` — super_admin_db_schema.router 登録

### APIエンドポイント設計根拠
- `information_schema.tables` / `information_schema.columns` / `information_schema.table_constraints` / `information_schema.key_column_usage` — PostgreSQL標準スキーマ（SSOT、migration不要）

### 触らないファイル
- `migrations/` — information_schema動的取得のため不要
- `backend/app/models/` — 新規モデル定義不要
