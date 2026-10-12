# recon: note-master-frontend

## 目的
tcg_note_master テーブルに対する super-admin CRUD とテナント CRUD を追加する。
サイドバー・管理センターへの導線も整備する。

## 既存 ADR
- ADR-027: i18n 強制（全 UI 文字列 t("key") 経由）
- ADR-072: write endpoint 後の reset_tenant_context() 必須
- ADR-144: UI ガバナンス（金型コンポーネントのみ）

## 参照ファイル（現状把握）

### バックエンド（参照元コード）
- `backend/app/routers/super_admin_suppliers.py` — super-admin パターン参照
- `backend/app/routers/suppliers.py` — tenant CRUD パターン参照
- `backend/app/schemas/central_masters.py` — import ヘッダ・既存スキーマ構造
- `backend/app/main.py` — ルーター import / 登録箇所

### フロントエンド（参照元コード）
- `frontend/src/pages/super-admin/components/SupplierMasterPanel.tsx` — Panel パターン
- `frontend/src/pages/super-admin/components/AnalysisRulesSidebar.tsx` — 型定義
- `frontend/src/pages/super-admin/AnalysisRulesPage.tsx` — 既存パネル import
- `frontend/src/pages/management-center/ManagementCenterPage.tsx` — data セクション
- `frontend/src/App.tsx` — management-center ルート
- `frontend/src/pages/units/UnitsPage.tsx` — テナント側ページパターン

### i18n
- `frontend/src/locales/ja.json` — analysisRules.sidebar セクション
- `frontend/src/locales/en.json` — analysisRules.sidebar セクション

### マイグレーション
- `scripts/run_all_migrations.sh` — 末尾登録済みマイグレーション
- `.github/workflows/migration-test.yml` — tcg_status_master CREATE TABLE パターン

## 既存 note_master テーブル確認
- テーブル名: public.tcg_note_master
- tenant_id カラム: 未存在（本 PR で追加）
- 既存マイグレーション: 20260903_130000_tcg_note_master_t004.sql（seed データ）

## migration ファイル名衝突
- 仕様書指定 20260920_040000 は 20260920_040000_conditions_ssot_phase1.sql と衝突
- 解決: `migrations/20260920_060000_note_master_tenant_id.sql` を使用
