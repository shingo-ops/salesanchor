# Recon: 仕入元マスタ UI 分離

## 目的

仕入元マスタを2つの画面に分離表示する:
- **SaaS管理者メニュー**: LINE解析用の仕入元マスタ（運営者のみ閲覧・編集）
- **管理センター > データ管理**: テナントごとの仕入元マスタ（各テナントがCRUD）

テナントユーザーからはLINE解析用マスタは見えない・触れない。

## 現状（事実・file:line 引用）

### DB

- `public.suppliers`: 229行、全行 `tenant_id = NULL`（LINE解析用）
- `tenant_NNN.suppliers`: 全テナント DROP 済み（Sprint 1 完了 2026-09-18）
- `tenant_id` 列: INTEGER, nullable, インデックス有（`idx_suppliers_tenant_id`）
- 区別方法: `tenant_id = NULL` → LINE解析用 / `tenant_id = N` → テナント固有

### フロントエンド

| ファイル | 行 | 状態 |
|---------|-----|------|
| `frontend/src/pages/super-admin/ProductMastersTab.tsx` | 1-351 | `MasterListEditor` 金型を内包。**ルーティングなし（孤立）** |
| `frontend/src/pages/super-admin/SuppliersAdminTab.tsx` | 1-350+ | 独自レイアウト。**ルーティングなし（孤立）** |
| `frontend/src/pages/suppliers/SuppliersPage.tsx` | 1-150+ | テナント側。独自レイアウト。`/management-center/suppliers` でルーティング済み |
| `frontend/src/App.tsx` | 273-308 | `/super-admin/*` ルート定義。`/super-admin/masters` ルートなし |
| `frontend/src/App.tsx` | 334-356 | `/management-center/*` ルート定義。`suppliers` ルートあり |

### バックエンド

| ファイル | 内容 |
|---------|------|
| `backend/app/routers/suppliers.py` | テナント側 `/suppliers` API。`tenant_id` フィルタなし。search_path で `public.suppliers` を参照 |
| `backend/app/routers/super_admin_suppliers.py` | SaaS管理者 `/super-admin/suppliers` API。`public.suppliers` 全件対象。`tenant_id` フィルタなし |

### 金型（MasterListEditor）

- 場所: `ProductMastersTab.tsx:116-312`（内部コンポーネント）
- インターフェース `MasterDataSource`（`ProductMastersTab.tsx:27-33`）:
  - `list()`, `create()`, `update()`, `remove()`, `reorder()`
- 機能: 検索、追加、編集、削除、ドラッグ並び替え
- PO指示: この金型を仕入元マスタでも使用して統一感を出す

### 関連 ADR

- ADR-093: 在庫テーブル・商品マスタ再設計（SuppliersAdminTab のスコープ定義）
- ADR-072: テナントスキーマプレフィクス強制（write 後の `reset_tenant_context` 必須）
- ADR-027: i18n 強制（全 UI 文字列は `t("key")` 経由）
- ADR-144: UI ガバナンス（金型を先確認、生 select/生 input 禁止）

### 権限

- テナント側: `suppliers.view`, `suppliers.create`, `suppliers.update`, `suppliers.delete`（既存）
- SaaS管理者側: `require_super_admin()`（既存）
