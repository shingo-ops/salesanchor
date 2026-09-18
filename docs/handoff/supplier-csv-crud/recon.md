# recon — 仕入元マスタ CSV エクスポート・インポート

**仕事名**: 仕入元マスタ CSV エクスポート・インポート
**日付**: 2026-09-19（再調査: Phase 2 統合後）
**対象ADR**: ADR-155
**担当**: architect

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `backend/app/routers/super_admin_suppliers.py:1` | 中央管理用仕入元ルーター（tenant_id IS NULL フィルタ）CSV未実装 |
| `backend/app/routers/suppliers.py:1` | テナント用仕入元ルーター（tenant_id = :tenant_id フィルタ）CSV未実装 |
| `backend/app/routers/super_admin_aliases.py:213` | supplier_aliases CSV export 実装（参考パターン） |
| `backend/app/routers/tcg_product_import.py:1` | 商品マスタCSV import backend（preview/commit 4エンドポイント — 最も近い参考） |
| `backend/app/routers/tcg_product_import.py:169` | CSV検証ロジック（.csv, UTF-8+BOM, ≤2MB） |
| `frontend/src/pages/super-admin/SuppliersAdminTab.tsx:1` | 中央管理仕入元UI（SuperAdminMastersPageタブ内、CSVボタンなし） |
| `frontend/src/pages/suppliers/SuppliersPage.tsx:1` | テナント用仕入元UI（CSVボタンなし） |
| `frontend/src/pages/super-admin/TcgProductMasterPage.tsx:1` | 商品マスタUI（Export/Importボタンあり — 目標UI） |
| `frontend/src/pages/super-admin/TcgProductImportPanel.tsx:1` | 商品CSV import パネル（ファイル選択→プレビュー→確定） |
| `migrations/20260918_030000_supplier_ssot_phase2.sql:1` | Phase 2 統合migration（tenant_id列追加、FK張り替え） |

---

## 現状確認（2026-09-19 再調査）

### public.suppliers テーブル（SSOT Phase 2 統合後）

カラム: id (SERIAL PK), supplier_code (VARCHAR UNIQUE), name, supplier_type, default_language, contact_name, email, phone, address, line_name, postal_code, prefecture, city, address1, address2, notes, is_active, tenant_id (INTEGER NULL), created_at, updated_at

**データ分離ルール:**
- tenant_id IS NULL → LINE解析用中央マスタ（SaaS管理者が管理）
- tenant_id = N → テナントN固有の仕入元（テナント側が管理）

### 中央管理用エンドポイント（super_admin_suppliers.py）
- GET /super-admin/suppliers — 一覧（WHERE tenant_id IS NULL）
- POST /super-admin/suppliers — 新規（tenant_id = NULL 固定）
- PATCH /super-admin/suppliers/{id} — 更新
- DELETE /super-admin/suppliers/{id} — soft delete
- GET /super-admin/suppliers/{id}/discord-routing — Discord連携
- GET /super-admin/suppliers/{supplier_id}/parse-stats — 解析統計
- **CSV export/import: なし**

### テナント用エンドポイント（suppliers.py）
- GET /suppliers — 一覧（WHERE tenant_id = :tenant_id）
- GET /suppliers/{supplier_id} — 詳細
- POST /suppliers — 新規（tenant_id = 自テナント）
- PATCH /suppliers/{supplier_id} — 更新
- DELETE /suppliers/{supplier_id} — soft delete
- GET /suppliers/catalog — 全public.suppliers（発注プルダウン用）
- **CSV export/import: なし**

### FK統合状況（Phase 2完了）
- supplier_channels.supplier_id → public.suppliers(id) ✅
- purchase_orders.supplier_id → public.suppliers(id) ✅
- products.supplier_default_id → public.suppliers(id) ✅

### UI部品（使用予定・存在確認済み）
- Button, HeaderButton, ContentToolbar, Modal, ConfirmModal, PageLayout, DataTable
- api.getBlob() — CSVダウンロード
- api.postForm() — ファイルアップロード

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | tenant_id の扱い: CSVにtenant_id列を含めるか | テナント用は自動設定のため不要。中央管理用もNULL固定のため不要 | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み
