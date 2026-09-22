# 単位マスタ実装 recon

## 対象テーブル

- `public.units`: 8行（Case, Box, Pack, Piece, Set, 本, 点, 個）
- `public.unit_aliases`: 39行

## 既存DDL確認

DDL: `migrations/20260919_020000_master_ssot_public_tables.sql`

tenant_id カラムは存在しない。NULL=共用/LINE解析用、数値=テナント個別とする設計。

## パターン元確認

- 共用マスタCRUD: `backend/app/routers/super_admin_suppliers.py`
- テナント用CRUD: `backend/app/routers/suppliers.py`
- フロントパネル: `frontend/src/pages/super-admin/components/SupplierMasterPanel.tsx`
- テナント用フロント: `frontend/src/pages/suppliers/SuppliersPage.tsx`
- Pydanticスキーマ: `backend/app/schemas/central_masters.py`

## 確認済み事項

- 既存データ: public.units に8行、public.unit_aliases に39行あることを確認
- tenant_id カラム: 存在しないことを確認（migration で追加）
- AnalysisRulesSidebar: supplier-master の後に追加するパターン
- ManagementCenterPage: data セクションに suppliers と同パターンで追加
