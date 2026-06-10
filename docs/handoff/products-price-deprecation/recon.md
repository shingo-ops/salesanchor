# Recon: products.unit_price 廃止 (C-4) — ProductEditPage 価格欄削除の影響調査

> **作成日**: 2026-06-09  
> **担当**: architect（読み取り専用。アプリコード変更0件）  
> **背景**: `products.unit_price / unit_price_usd / unit_price_eur` は DEPRECATED C-4（migration `20260604_070000_deprecate_columns.sql`）。  
> ProductEditPage から価格欄3つを外す前に事実を確認する。

---

## 1. 廃止の根拠（事実確認済み）

`migrations/20260604_070000_deprecate_columns.sql:43`

```sql
COMMENT ON COLUMN public.products.unit_price IS
    'DEPRECATED C-4: 新規コードで参照禁止。正式単価はpublic.inventory.unit_priceを使用。';
COMMENT ON COLUMN public.products.unit_price_usd IS
    'DEPRECATED C-4: 新規コードで参照禁止。';
COMMENT ON COLUMN public.products.unit_price_eur IS
    'DEPRECATED C-4: 新規コードで参照禁止。';
```

列は **DROP されていない**（additive-only migration ポリシー）。カラムは存在するが新規コードで参照禁止。

---

## 2. 3欄が駆動しているもの（file:line）

### 2-A. `products.unit_price`（JPY）

| 場所 | 役割 | file:line |
|------|------|-----------|
| backend products ルーター SELECT | GET /products・GET /products/:id の応答に含める | `backend/app/routers/products.py:91` |
| backend products ルーター INSERT/PATCH | 保存先（products テーブルに書き込む） | `backend/app/routers/products.py:350` |
| **inventory_search サービス** | 商品マスタ検索クエリが `public.products.unit_price` を SELECT | `backend/app/services/inventory_search.py:337` |
| **quoteDraft.ts** | 在庫画面から見積作成へ渡す `SelectedProduct.unit_price` の実体 | `frontend/src/pages/quote-create/quoteDraft.ts:96` |
| **QuoteCreatePage** | 見積明細の初期単価（オペレーターが上書き可能） | `frontend/src/pages/quote-create/QuoteCreatePage.tsx:87` |
| **InvoiceCreatePage** | 請求明細の初期単価 | `frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:132` |
| dashboard ルーター | 在庫評価額の集計（`quantity × unit_price`） | `backend/app/routers/dashboard.py:185` |

> **重要**: `products.unit_price` は「商品マスタの参考単価」として在庫検索 → 見積作成フローに流れている。

### 2-B. `products.unit_price_usd` / `products.unit_price_eur`（外貨）

| 場所 | 役割 | file:line |
|------|------|-----------|
| backend products ルーター SELECT/INSERT/PATCH | GET/POST/PATCH 応答・保存 | `backend/app/routers/products.py:94` |
| ProductsPage（既存ファイル、表示のみ） | フォームにのみ表示 | `frontend/src/pages/products/ProductsPage.tsx:272` |

外貨2欄は **見積・請求・在庫検索のいずれにも流れていない**。

---

## 3. 後継の入力手段の有無

### 3-A. `public.inventory_offers.unit_price`（B在庫オファー価格）

- backend `backend/app/services/inventory_search.py:472`: 在庫オファーを `unit_price` 昇順で返す
- 編集UI: **スーパー管理者専用** `frontend/src/pages/super-admin/InventoryOffersPage.tsx:540`
- **一般スタッフには編集手段なし**

### 3-B. `own_inventory.unit_price`（A在庫・テナント自社在庫）

- backend PATCH API: `backend/app/routers/own_inventory.py:56` — `unit_price` は更新対象フィールドに含まれている
- 表示UI: `frontend/src/pages/inventory/OwnInventoryPage.tsx:151` — **読み取り表示のみ**
- 編集UI: **存在しない** — フォームは数量入力（引当/解除/発送）のみ `frontend/src/pages/inventory/OwnInventoryPage.tsx:233`
- 結論: **`own_inventory.unit_price` を更新するフロントエンドUIは現時点で不在**

---

## 4. 3欄を外したときの影響

### 4-A. `unit_price`（JPY）を外した場合

| 影響 | 詳細 |
|------|------|
| **見積・請求の初期単価が0になる** | `backend/app/services/inventory_search.py:337` の `p.unit_price` が null になり、`frontend/src/pages/quote-create/quoteDraft.ts:96` の `?? 0` で 0 がセットされる |
| **既存商品の価格が更新不能になる** | ProductsPage/ProductEditPage から外すと更新手段ゼロ |
| **dashboard 集計がゼロ化する** | `backend/app/routers/dashboard.py:185` の在庫評価額が `quantity × 0` になる |

### 4-B. `unit_price_usd` / `unit_price_eur` を外した場合

| 影響 | 詳細 |
|------|------|
| 外貨単価が更新不能になる | 見積・請求・在庫検索には流れていないため業務フローへの影響は限定的 |
| backend 保存先は残る | null を受け入れるため API エラーは起きない |

---

## 5. 結論（Path A の大きさ判定）

### `unit_price`（JPY）: **(b) 大きめ**

在庫側に価格入力手段が **現時点で存在しない**。

- `own_inventory.unit_price` の PATCH API は存在するが、フロントエンド編集UIが不在（`frontend/src/pages/inventory/OwnInventoryPage.tsx:233`）
- `inventory_offers.unit_price` の編集はスーパー管理者専用
- ProductEditPage から `unit_price` を外すと、**商品の参考単価を更新する方法がなくなる**

**正しい Path A = `own_inventory.unit_price` の編集UI を整備してから外す、が必要**。

### `unit_price_usd` / `unit_price_eur`（外貨2欄）: **(a) クリーン**

見積・請求・在庫検索のいずれにも流れていない。

---

## 6. 不明点

| 項目 | 状況 |
|------|------|
| `backend/app/services/inventory_search.py:337` の `p.unit_price` を `own_inventory.unit_price` に切り替える計画があるか | ADR・ticket 記載なし。不明 |
| `own_inventory.unit_price` 編集UIのロードマップ | 記載なし。不明 |

---

## 7. 推奨アクション（recon の判断のみ・実装指示ではない）

1. **`unit_price_usd` / `unit_price_eur` の2欄**: 外すことは可能（業務影響最小）
2. **`unit_price`（JPY）の1欄**: 在庫側の編集UI整備前に外すのはリスクが高い
3. **現PR #1828 の暫定処置**: Path B（`check_deprecated_columns.sh` の除外リストに ProductEditPage を追加し理由を明記）が最小コストで誠実
