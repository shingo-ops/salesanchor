# recon: DB構造ビューア追加

## 対象ADR
- ADR-144: UIガバナンス（生select/input禁止・CSS変数必須）
- ADR-027: UI国際化（i18n強制）

## 既存パターン調査

### 参照したコンポーネント
- frontend/src/pages/super-admin/components/SupplierMasterPanel.tsx — サイドツリー+テーブル構成の参照実装
- frontend/src/components/DataTable.tsx — スプレッドシート形式テーブル（既存金型）
- frontend/src/pages/super-admin/components/AnalysisRulesSidebar.tsx — サイドメニュー追加先
- frontend/src/pages/super-admin/AnalysisRulesPage.tsx — パネル配線先
- backend/app/routers/super_admin_tcg.py — super_adminルーターの参照実装

### APIエンドポイント設計根拠
- `information_schema.tables` / `information_schema.columns` / `information_schema.table_constraints` / `information_schema.key_column_usage` — PostgreSQL標準スキーマ（SSOT、migration不要）

### 触らないファイル
- `migrations/` — information_schema動的取得のため不要
- `backend/app/models/` — 新規モデル定義不要
