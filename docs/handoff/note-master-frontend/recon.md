# recon: note-master-frontend

## 目的
tcg_note_master テーブルに対する super-admin CRUD とテナント CRUD を追加する。
サイドバー・管理センターへの導線も整備する。

## 既存 ADR
- ADR-027: i18n 強制（全 UI 文字列 t("key") 経由）
- ADR-072: write endpoint 後の reset_tenant_context() 必須
- ADR-144: UI ガバナンス（金型コンポーネントのみ）

## 参照ファイル（現状把握）

### バックエンド
- `backend/app/routers/super_admin_suppliers.py:1-30` — super-admin パターン参照
- `backend/app/routers/suppliers.py:1-30` — tenant CRUD パターン参照
- `backend/app/schemas/central_masters.py:1-20` — import ヘッダ・既存スキーマ構造
- `backend/app/main.py:86-99` — ルーター import 箇所
- `backend/app/main.py:497-501` — super_admin ルーター登録箇所

### フロントエンド
- `frontend/src/pages/super-admin/components/SupplierMasterPanel.tsx:1-50` — Panel パターン
- `frontend/src/pages/super-admin/components/AnalysisRulesSidebar.tsx:10-21` — 型定義
- `frontend/src/pages/super-admin/AnalysisRulesPage.tsx:28-30` — 既存パネル import
- `frontend/src/pages/management-center/ManagementCenterPage.tsx:46-54` — data セクション
- `frontend/src/App.tsx:348-372` — management-center ルート
- `frontend/src/pages/units/UnitsPage.tsx:1-50` — テナント側ページパターン

### i18n
- `frontend/src/locales/ja.json:3839-3855` — analysisRules.sidebar セクション
- `frontend/src/locales/en.json:3839-3855` — analysisRules.sidebar セクション

### マイグレーション
- `migrations/20260920_050000_status_master_add_tenant_id.sql` — 直前の類似マイグレーション
- `scripts/run_all_migrations.sh:704-708` — 末尾登録済みマイグレーション
- `.github/workflows/migration-test.yml:481-495` — tcg_status_master CREATE TABLE パターン

## 既存 note_master テーブル確認
- テーブル名: `public.tcg_note_master`
- tenant_id カラム: 未存在（本 PR で追加）
- 既存マイグレーション: `20260903_130000_tcg_note_master_t004.sql`（seed データ）

## migration ファイル名衝突
- 仕様書指定 `20260920_040000` は `20260920_040000_conditions_ssot_phase1.sql` と衝突
- 解決: `20260920_060000_note_master_tenant_id.sql` を使用
