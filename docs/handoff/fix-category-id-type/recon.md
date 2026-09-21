# recon: product_category_id type mismatch (UUID → int)

## 調査日
2026-09-21

## 現状把握

### バグ箇所

| ファイル | 行 | 変更前 | 変更後 |
|---|---|---|---|
| `backend/app/routers/tcg_product_import.py:276` | 276 | `product_category_id: UUID \| None` | `product_category_id: int \| None` |
| `frontend/src/features/tcg-product-import/TcgProductDetailDrawer.tsx:135` | 135 | `product_category_id: draft.product_category_id \|\| null` | `product_category_id: draft.product_category_id ? Number(draft.product_category_id) : null` |

### 根拠（事実）

- `backend/app/routers/tcg_product_import.py:276`: Pydantic スキーマ `ProductDetailUpdate` の `product_category_id` フィールドが `UUID | None` 型として定義されていた。
- `backend/app/services/tcg_product_detail_svc.py:18-22`: サービス側は `PUBLIC_INTEGER_LOOKUPS` dict で `product_category_id` を `public.tcg_product_categories` (INTEGER PK) として扱っており、UPDATE SQL（line 176）も `CAST` なしで整数として渡している。
- `backend/app/services/tcg_product_detail_svc.py:176`: `product_category_id=:product_category_id` — CAST なし、整数前提の SQL。
- `frontend/src/features/tcg-product-import/TcgProductDetailDrawer.tsx:134`: `product_kind_id` と `work_id` は `Number()` 変換されているが、`product_category_id` は文字列のまま送信されていた（line 135）。

### 変更しないもの

- `manufacturer_id: UUID | None` は UUID のまま正しい（`TCG_SCHEMA.tcg_manufacturers` が UUID PK）。
- `from uuid import UUID` インポートは `manufacturer_id` 用に存続。
- `backend/tests/conftest.py:839`: SQLite インメモリテストの DDL に `product_category_id UUID` があるが、これはテスト用 SQLite であり Pydantic スキーマとは独立したスコープ。本 PR の対象外。

### 既存 ADR 参照

- ADR-155 Phase 3B: `product_category_id` は `public.tcg_product_categories`（INTEGER PK）へ移行済み。
- ADR-156 Phase 3A: `product_kind_id` は `public.product_kinds`（INTEGER PK）。
- `backend/app/services/tcg_product_detail_svc.py:18-19`: コメントで ADR-155 Phase 3B を明記済み。
- `backend/app/services/tcg_product_import_svc.py:168`: コメントで UUID→INTEGER 変換済みを明記済み。
