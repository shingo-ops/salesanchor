# recon: status-master-frontend

## 調査対象

ステータスマスタ（public.tcg_status_master）のフロントエンド・バックエンド新規実装。
単位マスタ（PR #3588）と同じパターンで実装する。

## 既存パターン元

- `backend/app/routers/super_admin_units.py`: 共用マスタ（tenant_id IS NULL）CRUD パターン
- `backend/app/routers/units.py`: テナント用 CRUD パターン（ADR-072 reset_tenant_context 含む）
- `backend/app/schemas/central_masters.py`: UnitBase/Create/Update/Response の Pydantic スキーマ
- `frontend/src/pages/super-admin/components/UnitMasterPanel.tsx`: 解析管理 hub-content パネル
- `frontend/src/pages/units/UnitsPage.tsx`: 管理センター テナント用ページ
- `frontend/src/pages/super-admin/components/AnalysisRulesSidebar.tsx`: サイドバー型定義
- `frontend/src/pages/super-admin/AnalysisRulesPage.tsx`: hub-content 振り分け
- `frontend/src/pages/management-center/ManagementCenterPage.tsx`: rawSections data グループ
- `frontend/src/App.tsx`: /management-center/units ルート（line 359）
- `frontend/src/locales/ja.json`: unitMaster セクション（line 1704-1722）
- `frontend/src/locales/en.json`: unitMaster セクション（line 1704-1722）

## 既存 DDL

`migrations/20260919_020000_master_ssot_public_tables.sql` に tcg_status_master DDL あり。
tenant_id カラムが存在しないことを確認。

## migration タイムスタンプ

20260920_040000 は `migrations/20260920_040000_conditions_ssot_phase1.sql` に使用済み。
20260920_050000 を使用（衝突なし）。

## ADR 確認

- ADR-027: i18n 強制（全 UI 文字列 t() 経由）
- ADR-144: UI 金型ガバナンス（既存金型コンポーネントのみ）
- ADR-072: write endpoint の db.commit() 直後に reset_tenant_context() 必須
