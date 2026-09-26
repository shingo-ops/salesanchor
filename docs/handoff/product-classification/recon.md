# recon: 商品分類マスタ新設（小分類・細分類）

## 現状

### products テーブルの既存カラム（大分類・中分類）

`migrations/062_create_inventory_movements_and_budget.sql:1` で `public.products` が定義されている。
主要カラム:

- `product_kind` (`VARCHAR(50)`) — 大分類（商材区分）  
  `migrations/20260603_000000_add_products_product_kind.sql:5` で追加。値例: `'TCG'`
- `tcg_type_id` or `tcg_type` — 中分類（ブランド/種別）  
  `migrations/085_create_tcg_type_master.sql` で `tcg_type_master` テーブルが作成され、FK 張り替えは ADR-083 に従う

**小分類（商品系統）・細分類（商品形態）に相当するカラム・テーブルは存在しない（2026-09-20 時点）。**

確認コマンド: `grep -r "product_line\|product_format" migrations/` → 該当なし（本 migration 実行前）

---

## 既存マスタパターン

`migrations/085_create_tcg_type_master.sql` の構造（参照パターン）:

```sql
-- migrations/085_create_tcg_type_master.sql:14-26
CREATE TABLE IF NOT EXISTS public.tcg_type_master (
    id          SERIAL PRIMARY KEY,
    code        VARCHAR(50)  NOT NULL UNIQUE,
    name_ja     VARCHAR(100) NOT NULL,
    name_en     VARCHAR(100),
    sort_order  INTEGER      NOT NULL DEFAULT 100,
    is_active   BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
```

本 migration は同パターンを採用する（`code` + `name` + `display_order` + `is_active`）。

updated_at トリガは `migrations/062_create_inventory_movements_and_budget.sql` のパターンに従い  
テーブルごとに `public.set_updated_at_<tablename>()` 関数を定義する（`public.set_updated_at()` 汎用関数は存在しない）。

---

## 関連 ADR

| ADR | 内容 |
|-----|------|
| ADR-155 (`docs/adr/ADR-155-product-master-ssot-csv-app.md`) | migration での値 INSERT 禁止。seed は別途アプリ UI / CSV import で行う |
| ADR-025 (`docs/adr/ADR-025_meta_integration_operational_hardening.md`) | 本番フェーズ移行後の手動 DB INSERT 禁止 |
| ADR-090 (`docs/adr/ADR-090-products-central-unification.md`) | public.products 中央一本化。新カラム追加は products 本体に行う |
| ADR-083 | tcg_type_master（中分類）設計。同パターンを小分類・細分類に適用 |

既存 ADR に product_lines / product_formats 言及なし（`git grep -i "product_line\|product_format" docs/adr/` → 該当なし）。

---

## 影響範囲

- 新テーブル作成（`public.product_lines`, `public.product_formats`）: 既存機能への影響なし
- `public.products` への NULLable カラム追加（`product_line_id`, `product_format_id`）:  
  既存行は NULL のまま。既存 SELECT / INSERT / UPDATE への影響なし（NOT NULL 制約なし）
- FK は `ON DELETE SET NULL`: 分類マスタ削除時も既存商品データは保全される

---

## タイムスタンプ重複確認

既存: `migrations/20260920_060000_note_master_tenant_id.sql`（run_all_migrations.sh 未登録）  
本 migration: `migrations/20260920_130000_create_product_classification.sql`（重複なし）
