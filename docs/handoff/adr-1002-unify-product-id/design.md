# ADR-1002 Unify Product ID: Design

**日付**: 2026-09-23
**ブランチ**: release/unify-product-id
**参照 recon**: docs/handoff/adr-1002-unify-product-id/recon.md

---

## 対象ADR

ADR-1002-unify-product-id-and-fix-migration-compat.md — フェーズC（商品識別子一本化）

---

## あるべき姿（KGI）

| 基準 | 検証方法 |
|------|---------|
| API `GET /tcg/products/list` が `id: int` を返す | CI: `test_tcg_product_list_pg.py` PASS |
| CSV roundtrip の1列目が `product_id` | CI: `test_tcg_product_roundtrip_pg.py` PASS |
| `TcgProductDetailDrawer` が `productId: number` で開く | CI: frontend lint PASS |
| `validate_product_id()` が products[].id で参照する | CI: `test_tcg_work_reference.py` PASS（12/12） |
| `products.product_code` カラムは残存 | migration なし・DROP なし |

---

## 設計方針

### 1. 識別子の統一

`products.id`（INTEGER SERIAL PK）を唯一の商品識別子とする。
`product_code`（"PM0001"）はDB内の表示/補助フィールドとして残置。

### 2. API レスポンス変更

`ProductListItem.code: str` → `id: int`。フロントエンドは `row.id`（number）で状態管理・ドロワー開閉を行う。

### 3. CSV roundtrip

`COLUMNS[0]` を `"product_code"` から `"product_id"` に変更。値は `str(product["id"])`。
後方互換のため `is_update()` は `"product_id"` OR `"product_code"` ヘッダーを検出する（stale CSV rejection のみ）。

### 4. ルックアップマップ

`tcg_analyzer_svc.py`、`tcg_parallel_report_svc.py`、`tcg_work_comparison_svc.py` の全ルックアップマップを `str(p.id)` キーに統一。SQL は `SELECT id FROM public.products` のみ（`product_code` 不要）。

### 5. Gemini プロンプト

`validate_product_code()` の代わりに `validate_product_id()` を使用。プロンプト文言を「商品IDは参照products内のidをそのまま選ぶ」に変更。

### 6. 検索クエリ

`p.product_code ILIKE :q` → `p.id::text ILIKE :q`（全サービス・ルーター）。

---

## 影響範囲

- **呼び出し元**: `TcgProductMasterPage.tsx`、`ProductMasterPanel.tsx`（`selectedProduct: number | null`）
- **API**: `GET /tcg/products/list` レスポンス shape 変更（`code: str` → `id: int`）
- **CSV**: `product_id` 列が入ったラウンドトリップ CSV が既存ファイルと非互換（設計上想定済み）
- **触らない範囲**: `tcg_product_master_svc._next_pm_code()`（採番ロジック）、`migrations/`、`products.product_code` カラム定義

---

## 戻し方

git revert HEAD で1コミット分を元に戻せる。DBスキーマ変更なし・migration なし。

---

## 外部事例

- Django REST Framework では PK ベースの URL が標準（`/api/products/{id}/`）
- GitHub API は数値 ID（`node_id` ではなく `id`）をプライマリ識別子として使用

---

## 維持の仕組み

- 守り手: `backend/tests/test_tcg_product_list_pg.py`（`item.id` が int であることを検証）、`backend/tests/test_tcg_work_reference.py`（`validate_product_id` の正常・異常系）、`backend/tests/test_tcg_product_detail_pg.py`（`/{product_id}` ルート）
- CI で全テストが PASS しない限りマージ不可
