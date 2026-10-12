# Recon: product-categories-csv

## 目的

`tcg_product_categories` テーブルに対して CSV エクスポート / インポート機能を追加する。

## 既存 ADR 検索結果

| ADR | 内容 | 適用箇所 |
|-----|------|---------|
| ADR-027 | UI 文字列は t("key") 経由（ハードコード日本語禁止） | 新規 TSX ファイル全体 |
| ADR-072 | write endpoint の db.commit() 直後に reset_tenant_context() 必須 | product_categories.py import/commit |
| ADR-144 | UI 部品は金型クラスのみ使用 | 新規 TSX ファイル全体 |

ADR 検索: `git grep -i "product.categor" docs/adr/` → 該当なし。`docs/adr/FEATURE-INDEX.md` に csv/import 項目なし。

## 既存実装の確認

### バックエンド

- backend/app/routers/super_admin_product_categories.py:1-152 — 中央管理 CRUD ルーター（CSV 未実装）
- backend/app/routers/product_categories.py:1-150 — テナント CRUD ルーター（CSV 未実装）
- backend/app/routers/super_admin_units.py:44-420 — CSV パターンの参照実装（_compute_digest, _read_unit_upload, _parse_units, export, preview, commit）

### フロントエンド

- frontend/src/pages/super-admin/components/ProductCategoriesMasterPanel.tsx:1-284 — CSV ボタンなし
- frontend/src/pages/product-categories/ProductCategoriesPage.tsx:1-378 — CSV ボタンなし
- frontend/src/pages/super-admin/UnitImportPage.tsx:1-135 — import ページパターン参照
- frontend/src/pages/units/UnitImportPage.tsx:1-142 — テナント import ページパターン参照
- frontend/src/App.tsx:101-104 — 既存 import ルート群（UnitImportPage, ConditionImportPage 等）
- frontend/src/locales/ja.json:4134-4153 — unitCsv キー群（パターン参照）

### i18n

- frontend/src/locales/ja.json:4134 — unitCsv キー群
- frontend/src/locales/en.json:4134 — unitCsv 対応英語キー

## CSV カラム設計

`tcg_product_categories` テーブルから書き込み可能カラム:

| カラム | 型 | 必須 | 備考 |
|-------|----|------|------|
| code | text | YES | ユニーク識別子 |
| display_name | text | YES | 表示名 |
| kubun_type | text | NO | NULL 可 |
| is_active | bool | NO | デフォルト true |

## 影響範囲

| 変更ファイル | 理由 |
|------------|------|
| backend/app/routers/super_admin_product_categories.py | エンドポイント追加 |
| backend/app/routers/product_categories.py | エンドポイント追加 |
| frontend/src/pages/super-admin/components/ProductCategoriesMasterPanel.tsx | CSV ボタン追加 |
| frontend/src/pages/product-categories/ProductCategoriesPage.tsx | CSV ボタン追加 |
| frontend/src/pages/super-admin/ProductCategoriesImportPage.tsx | 新規作成 |
| frontend/src/pages/product-categories/ProductCategoriesImportPage.tsx | 新規作成 |
| frontend/src/App.tsx | ルート追加 |
| frontend/src/locales/ja.json | i18n キー追加 |
| frontend/src/locales/en.json | i18n キー追加 |

## 外部事例

- 単位マスタ CSV (backend/app/routers/super_admin_units.py) — 同一プロジェクト内の直接参照実装

## 設計書参照

docs/handoff/product-categories-csv/design.md
