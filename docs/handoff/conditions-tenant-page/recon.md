# Recon: テナント管理センター状態マスタページ

## 目的
管理センター（/management-center）にテナント固有の状態マスタ管理ページを追加する。

## 現状確認

### バックエンドAPI（実装済み・PR #3590）
- `backend/app/routers/conditions.py` — テナントスコープCRUD全5エンドポイント
- GET /conditions — テナント固有状態一覧
- GET /conditions/catalog — 共有状態カタログ（tenant_id IS NULL）
- POST/PATCH/DELETE /conditions — CRUD操作

### 参照パターン
- `frontend/src/pages/status-master/StatusMasterPage.tsx` — 最も近い既存パターン
- `frontend/src/pages/management-center/ManagementCenterPage.tsx:rawSections` — ナビゲーション追加先
- `frontend/src/App.tsx:348-375` — ルート定義

### 既存ADR
- ADR-155: shared master SSOT policy
- ADR-027: i18n強制
- ADR-144: UIガバナンス

## 結論
StatusMasterPageパターンを横展開し、管理センターにconditionsページを追加する。
