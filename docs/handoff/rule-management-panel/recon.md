# ルール管理パネル — recon

## 目的
PR #3623 で削除されたルール管理UIを、tcg_status_master（SSOT）ベースで再構築する。
マスタ管理（データCRUD）とルール管理（ルール運用ビュー）を分離。

## 既存資産

### バックエンド（変更なし・既存API利用）
- `backend/app/routers/super_admin_status_master.py` — 7エンドポイント（GET/POST/PATCH/DELETE/export/import）
- `backend/app/services/super_admin_status_master_svc.py` — CRUD + CSV import/export

### フロントエンド（変更対象）
- `frontend/src/pages/super-admin/components/AnalysisRulesSidebar.tsx:10-23` — AnalysisRulesSidebarKey 型定義
- `frontend/src/pages/super-admin/AnalysisRulesPage.tsx:105-172` — パネル描画ロジック
- `frontend/src/pages/super-admin/components/StatusMasterPanel.tsx` — 既存マスタ管理パネル（パターン参照元）

### DB（SSOT・変更なし）
- `public.tcg_status_master` — 9件のシードデータ（完売5件、日付/予約3件、デフォルト1件）
- カラム: id, status_id, canonical, search_pattern, exclude_pattern, priority, enabled, note, match_type(REGEX/LITERAL/DEFAULT), effect(OUTPUT/EXCLUDE)

### ADR
- ADR-027: i18n 強制（全UI文字列 t() 経由）
- ADR-067: デザイントークン強制（色・サイズはCSS変数経由）
- ADR-144: UI金型（Card/Badge/DataTable/ContentToolbar のみ）

## PR #3623 の影響
- 13テーブルDROP、バックエンドルーター・サービス削除、フロントパネル削除
- tcg_status_master は public スキーマに SSOT 化済みで残存
- 既存 CRUD API（super_admin_status_master）も残存
- 削除されたのはフロントのルール管理UIのみ
