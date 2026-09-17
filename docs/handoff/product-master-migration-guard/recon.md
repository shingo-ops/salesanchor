# recon: 商品マスタ migration guard

## 現状（2026-09-16 実測）

### 重複の事実

- 商品マスタ画面（`/super-admin/tcg-product-master`）で「ムニキス」を検索すると 3 件表示される（PO スクリーンショットで確認）。
- 3 件の内訳:
  1. 「ムニキスゼロ / Nihil Zero」（検索キーワード: 1）
  2. 「拡張パック ムニキスゼロ」（検索キーワード: 0）
  3. 「ムニキスゼロ / Nihil Zero」（検索キーワード: 0）

### 重複の原因（migration 経由のデータ投入）

以下のマイグレーションが `public.products` に商品データを直接投入していた:

| ファイル | 行った操作 |
|---------|-----------|
| `migrations/20260604_010000_seed_product_marks.sql` | 既存商品 125 件に mark を UPDATE |
| `migrations/20260615_235900_seed_pokemon_mega_products.sql` | MEGA 商品 25 件を INSERT |
| `migrations/20260903_180000_tcg_products_mark_en_t004.sql` | GAS 商品マスタ 268 件を投入 |
| `migrations/20260905_010000_tcg_pokemon_master_batch1_t004.sql` | ポケモン商品 25 件を追加投入 |

### 型番（mark）の誤り

- PM0198（MEGAドリームex）: mark=M3 → 正しくは M2a
  - 根拠: [遊々亭 [M2a] MEGAドリームex](https://yuyu-tei.jp/sell/poc/s/m02a)、[公式 URL /ex/m2a/](https://www.pokemon-card.com/ex/m2a/index.html)
- PM0202（ムニキスゼロ）: mark=M3 → 正しい（重複ではなくPM0198側が誤り）

### 検索 API の実装

- `.github/workflows/migration-guard.yml`:391 行、チェック 1〜6 実装済み
- `backend/app/routers/tcg_product_import.py`:87-143 行 — 一覧 API は `public.products` を直接 SELECT
- `backend/app/services/tcg_product_master_svc.py`:109-157 行 — 検索 API も `public.products` を ILIKE で検索

### 保護対象テーブル（file:line で確認済み）

| テーブル | 作成元 |
|---------|--------|
| `public.products` | `migrations/062_create_inventory_movements_and_budget.sql:30-52` |
| `tenant_004.tcg_products` | `migrations/20260831_110000_create_tcg_tables_t004.sql` |
| `tenant_004.product_search_keywords` | 同上 |
| `tenant_004.product_exclude_keywords` | 同上 |
