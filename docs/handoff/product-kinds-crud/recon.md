# Recon: product_kinds CRUD API + 管理UI

## 調査日
2026-09-21

## 既存ADR確認

- `docs/adr/ADR-027-ui-internationalization.md` — i18n強制（全UI文字列 t() 経由）
- ADR-144 — UIガバナンス（金型コンポーネント遵守）
- ADR-025 — 本番手動INSERT原則禁止（開発フェーズは直接INSERT継続）

## 既存パターン調査結果

### バックエンドパターン（採用）

| ファイル | パターン |
|---------|---------|
| `backend/app/schemas/product_category.py` | Pydanticスキーマ（Base/Create/Update/Response分離） |
| `backend/app/routers/super_admin_product_categories.py` | soft delete、IntegrityError→409、生SQL+sqlalchemy.text() |
| `backend/app/routers/super_admin_tcg.py:39` | `_TYPE_COLS`/`_TYPE_UPDATABLE` パターン |

### フロントエンドパターン（採用）

| ファイル | パターン |
|---------|---------|
| `frontend/src/pages/super-admin/components/ProductCategoriesMasterPanel.tsx` | DataTable + Modal + ConfirmModal CRUD パネル |
| `frontend/src/pages/super-admin/components/AnalysisRulesSidebar.tsx` | hub-subnav サイドバーキー型 |
| `frontend/src/pages/super-admin/AnalysisRulesPage.tsx` | hub-shell + 条件レンダリング |

## 変更ファイル一覧

### 新規作成
- `backend/app/schemas/product_kind.py`
- `backend/app/routers/super_admin_product_kinds.py`
- `frontend/src/pages/super-admin/components/ProductKindsMasterPanel.tsx`
- `docs/handoff/product-kinds-crud/recon.md`（本ファイル）
- `docs/handoff/product-kinds-crud/design.md`

### 変更
- `backend/app/main.py` — ルーター import + include_router 追加
- `backend/app/schemas/central_masters.py` — TcgTypeUpdate/Response に kind_id 追加
- `backend/app/routers/super_admin_tcg.py` — _TYPE_COLS/_TYPE_UPDATABLE に kind_id 追加
- `frontend/src/locales/ja.json` — analysisRules.sidebar.productKindsMaster + productKindsMaster セクション追加
- `frontend/src/locales/en.json` — 同上（英語版）
- `frontend/src/pages/super-admin/components/AnalysisRulesSidebar.tsx` — product-kinds-master キー追加
- `frontend/src/pages/super-admin/AnalysisRulesPage.tsx` — ProductKindsMasterPanel import + 条件レンダリング追加

## DBテーブル確認

`public.product_kinds` テーブルは本番に存在（0行・DDL済み）。
カラム: id(serial PK), code(varchar50 unique), name(varchar100), name_en(varchar100), display_order(int), is_active(bool), created_at, updated_at
