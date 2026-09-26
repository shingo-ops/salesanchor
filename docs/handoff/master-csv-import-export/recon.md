# recon: master-csv-import-export

## 調査日
2026-09-20

## 既存パターン調査

### SupplierImport パターン（踏襲元）
- `backend/app/routers/super_admin_suppliers.py` — `GET /super-admin/suppliers/export`, `POST /super-admin/suppliers/import/preview`, `POST /super-admin/suppliers/import/commit`
- `backend/app/routers/suppliers.py` — テナント側同様の3エンドポイント
- `frontend/src/pages/super-admin/SupplierImportPage.tsx` — preview/commit フロー、SHA-256 digest
- `frontend/src/pages/suppliers/SupplierImportPage.tsx` — テナント側

### 対象テーブルと既存ルーター

| テーブル | super-admin router | tenant router |
|---------|-------------------|---------------|
| units | `backend/app/routers/super_admin_units.py` | `backend/app/routers/units.py` |
| conditions | `backend/app/routers/super_admin_conditions.py` | `backend/app/routers/conditions.py` |
| tcg_status_master | `backend/app/routers/super_admin_status_master.py` | `backend/app/routers/status_master.py` |
| tcg_note_master | `backend/app/routers/super_admin_note_master.py` | `backend/app/routers/note_master.py` |

### マッチキー
- units, conditions: `code` (WHERE `tenant_id IS NULL` for super-admin)
- tcg_status_master: `status_id`
- tcg_note_master: `label_ja`

### ADR確認
- ADR-027: 全UI文字列は `t("key")` 経由 — `docs/adr/ADR-027-ui-internationalization.md`
- ADR-072: write endpoint 後に `reset_tenant_context` 必須 — `docs/adr/ADR-072-tenant-schema-prefix-enforcement.md`
- ADR-144: デザインシステムコンポーネントのみ使用 — `docs/adr/ADR-144-ui-component-governance.md`

### 既存フロントエンドページ確認
- `frontend/src/pages/units/UnitsPage.tsx:53` — UnitsPage コンポーネント（export ボタン追加対象）
- `frontend/src/pages/conditions/ConditionsPage.tsx` — ConditionsPage（export ボタン追加対象）
- `frontend/src/pages/status-master/StatusMasterPage.tsx:73` — StatusMasterPage（export ボタン追加対象）
- `frontend/src/pages/note-master/NoteMasterPage.tsx:85` — NoteMasterPage（export ボタン追加対象）
- `frontend/src/pages/super-admin/components/UnitMasterPanel.tsx` — super-admin パネル
- `frontend/src/pages/super-admin/components/ConditionsMasterPanel.tsx` — super-admin パネル
- `frontend/src/pages/super-admin/components/StatusMasterPanel.tsx` — super-admin パネル
- `frontend/src/pages/super-admin/components/NoteMasterPanel.tsx` — super-admin パネル

### App.tsx 既存ルート
- `frontend/src/App.tsx:322` — `/super-admin/masters/suppliers/import` 追加済み
- `frontend/src/App.tsx:245` — `/suppliers/import` 追加済み
- management-center 以下にネストされた routes: status-master, conditions, units, note-master (L362-365)
