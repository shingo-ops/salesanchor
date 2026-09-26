# Recon: 状態マスタ tenant_id + CRUD

## 目的
public.conditions に tenant_id を追加し、SaaS管理者向けCRUDパネルを実装する。

## 現状確認

### public.conditions テーブル構造
- ファイル: `migrations/20260919_020000_master_ssot_public_tables.sql:85-104`
- 列: id, code, canonical, app_kubun, is_active, priority, search_kw, exclude_kw, created_at, updated_at
- 行数: 11行（Phase 3 PR #3583 で統合済み）
- tenant_id 列: なし（本PRで追加）

### FK依存
- `public.condition_aliases.condition_id → public.conditions.id`（`migrations/20260919_020000_master_ssot_public_tables.sql:113`）
- `tenant_NNN.deal_statuses.condition_id`（`migrations/20260906_120000_create_tcg_tables_t001.sql:276`）
- `tenant_NNN.work_items.condition_id`（`migrations/20260831_110000_create_tcg_analysis_tables_t004.sql:143`）

### 仕入元マスタ（参照パターン）
- tenant_id パターン: `migrations/20260918_030000_supplier_ssot_phase2.sql`
- 中央管理API: `backend/app/routers/super_admin_suppliers.py`
- テナントAPI: `backend/app/routers/suppliers.py`
- フロントエンド: `frontend/src/pages/super-admin/components/SupplierMasterPanel.tsx`

### 既存ADR
- ADR-155: shared master SSOT policy
- ADR-072: reset_tenant_context 必須
- ADR-027: i18n 強制
- ADR-144: UI governance

## 結論
suppliers と同じ tenant_id パターン（NULL=共用、N=テナント固有）を conditions に適用する。
