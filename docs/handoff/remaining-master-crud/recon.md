# Recon: remaining-master-crud

## 対象テーブル
1. `public.tcg_product_categories` — カテゴリマスタ (2件)
2. `public.condition_aliases` — 状態マスタの別名テーブル (31件)

## 既存 ADR 検索結果
- `docs/adr/` 内に product_categories・condition_aliases 専用 ADR なし
- conditions SSOT 関連: `docs/handoff/conditions-master-tenant-id/design.md`（2026-09-20実装）

## 参照先ファイル: ファイル:行番号
- `backend/app/routers/super_admin_units.py` — alias sub-routes パターン
- `backend/app/routers/units.py` — tenant CRUD パターン（ADR-072）
- `backend/app/routers/super_admin_conditions.py` — extend 対象
- `backend/app/routers/conditions.py` — extend 対象
- `frontend/src/pages/super-admin/components/UnitMasterPanel.tsx` — alias UI パターン
- `frontend/src/pages/super-admin/components/ConditionsMasterPanel.tsx` — extend 対象
- `frontend/src/pages/conditions/ConditionsPage.tsx` — extend 対象
- `frontend/src/pages/status-master/StatusMasterPage.tsx` — standalone page パターン
- `frontend/src/App.tsx:363` — management-center ルート登録済み
- `frontend/src/pages/management-center/ManagementCenterPage.tsx:51` — nav items
- `frontend/src/config/routeTitles.ts:43` — routeTitles 末尾
- `frontend/src/locales/ja.json:4082` — ja.json 末尾
- `frontend/src/locales/en.json:4082` — en.json 末尾
- `migrations/20260920_060000_note_master_tenant_id.sql` — 直前 migration

## スキーマ確認
- `tcg_product_categories`: id, code, display_name, kubun_type, is_active, created_at, updated_at — tenant_id 列なし
- `condition_aliases`: id, condition_id FK→conditions(id) CASCADE, alias_text, lang, updated_at
