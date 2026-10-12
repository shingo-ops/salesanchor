# ADR-1002 Unify Product ID: Recon

**日付**: 2026-09-23
**ブランチ**: release/unify-product-id
**ベース**: origin/main (722d536f2)
**前提**: ADR-1001 Phase 2a〜2c 完了済み・ADR-1002 Phase A/B/C 完了済み

---

## 対象ADR

- `docs/adr/ADR-1002-unify-product-id-and-fix-migration-compat.md` — フェーズC：商品識別子を `products.id` に一本化

---

## 1. product_code 識別子使用箇所（全量 grep 結果）

### 1-1. バックエンド ルーター（識別子として使用）

| ファイル | 行 | 内容 | 変更要否 |
|---------|---|------|---------|
| `backend/app/routers/tcg_product_import.py` | 45,52,60 | `ProductListItem.code: str`、`SELECT p.product_code`、`ORDER BY p.product_code DESC` | **要** → `id: int`、`SELECT p.id`、`ORDER BY p.id DESC` |
| `backend/app/routers/tcg_product_master.py` | 248,252 | `/tcg/products/{product_code}/search-keywords` | **要** → `{product_id}` |
| `backend/app/routers/inventory_offers.py` | 229,406 | `p.product_code ILIKE :q` | **要** → `p.id::text ILIKE :q` |
| `backend/app/routers/super_admin_aliases.py` | 61 | `product_code ILIKE :q` | **要** → `id::text ILIKE :q` |

### 1-2. バックエンド サービス（識別子として使用）

| ファイル | 行 | 内容 | 変更要否 |
|---------|---|------|---------|
| `backend/app/services/tcg_product_import_svc.py` | 複数 | `SELECT mark, product_code FROM public.products`、`SELECT k.keyword, p.product_code` | **要** → `id::text` |
| `backend/app/services/tcg_product_detail_svc.py` | 複数 | ルーティングキー `product_code` | **要** → `product_id` (int) |
| `backend/app/services/tcg_product_master_svc.py` | POST書き戻しゲート | `SELECT product_code FROM public.products WHERE id` | **要** → `SELECT id FROM public.products WHERE id` |
| `backend/app/services/tcg_product_roundtrip_svc.py` | COLUMNS[0], snapshots, values | `"product_code"` 列名 | **要** → `"product_id"` |
| `backend/app/services/tcg_analysis_review_svc.py` | 69,214 | `p.product_code AS product_code`、`ILIKE :query` | **要** → `p.id::text` |
| `backend/app/services/tcg_unit_recovery_svc.py` | 複数 | `tp.product_code AS product_code` | **要** → `tp.id::text` |
| `backend/app/services/tcg_result_order.py` | ORDER BY句 | `p.product_code ASC NULLS LAST` | **要**: 除去（`p.id` のみ） |
| `backend/app/services/tcg_work_reference.py` | validate_product_code | `p["code"]` 参照 | **要** → `validate_product_id()` 追加、`p["id"]` 参照 |
| `backend/app/services/tcg_analyzer_svc.py` | load_lookup_maps等 | `SELECT product_code AS code` | **要** → `SELECT id`、キー `str(r[0])` |
| `backend/app/services/tcg_parallel_report_svc.py` | _load_lookup_maps_async | 同上 | **要** |
| `backend/app/services/tcg_work_comparison_svc.py` | 複数 | 同上 | **要** |
| `backend/app/services/gemini_extraction_svc.py` | extract_message | `validate_product_code()` | **要** → `validate_product_id()` |
| `backend/app/tasks/tcg_mirror.py` | 両クエリ | `p.product_code AS product_id` | **要** → `p.id::text AS product_id` |

### 1-3. フロントエンド（識別子として使用）

| ファイル | 行 | 内容 | 変更要否 |
|---------|---|------|---------|
| `frontend/src/features/tcg-product-import/TcgProductDetailDrawer.tsx` | prop | `productCode: string \| null` | **要** → `productId: number \| null` |
| `frontend/src/features/tcg-product-import/TcgProductImportPreview.tsx` | PreviewRow | `product_code?: string` | **要** → `product_id?: string` |
| `frontend/src/pages/super-admin/TcgProductMasterPage.tsx` | ProductRow, state | `code: string`、`selectedProduct: string \| null` | **要** → `id: number`、`number \| null` |
| `frontend/src/pages/super-admin/components/ProductMasterPanel.tsx` | 同上 | 同上 | **要** |

### 1-4. i18n

| ファイル | キー | 変更要否 |
|---------|-----|---------|
| `frontend/src/locales/ja.json` | `productCsv.search`、`updateHint` 等 | **要** → "商品ID" |
| `frontend/src/locales/en.json` | 同上 | **要** → "Product ID" |

### 1-5. 変更不要箇所

- `backend/app/services/tcg_product_master_svc.py` の `_next_pm_code()` — `product_code` カラムへの INSERT は継続
- `backend/app/schemas/product.py`、`backend/app/routers/products.py` — CRM製品テーブルの display field 参照（識別子でない）
- `backend/app/services/inventory_search.py` — 同上
- `migrations/` 内の歴史的参照 — 変更不要

---

## 2. DB 状態

- `public.products.product_code` カラム: **残置**（表示・レガシー用・DROP なし）
- `extraction_items.resolved_product_code` カラム名: **残置**（値のみ `products.id` 文字列に変更）
- `tcg_product_import_rows.product_code` DB カラム名: **残置**（値が product ID 文字列になる）
