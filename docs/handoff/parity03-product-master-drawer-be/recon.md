# PARITY-03 商品マスタ登録 API — recon.md

作成日: 2026-09-03
ブランチ: release/parity03-product-master-drawer-be

---

## 既存 ADR 検索結果

`git grep -i "parity" docs/adr/` → ADR-154-tcg-parity02-gas-python-migration  
ADR-154 方針（GAS→Python 段階移植）の延長として実施。  
Migration additive-only 原則: ADR-045 参照。  
PARITY-03 商品マスタ登録固有の ADR は未起案。登録・検索の軽量 API のため起案不要と判断。

---

## GAS ソース対応表

| GAS 実装 | BE 移植先 |
|---|---|
| `getRegistrationFormData()` | `GET /api/v1/tcg/products/registration-form` (B-1) |
| `searchProducts()` | `GET /api/v1/tcg/products/search` (B-4) |
| `checkDuplicateCandidates()` | `POST /api/v1/tcg/products/check-duplicates` (B-2) |
| `createProductMaster()` | `POST /api/v1/tcg/products` (B-3) |
| `addSearchKeyword()` | `POST /api/v1/tcg/products/{code}/search-keywords` (B-5) |
| `refreshShadowReviewV2()` | `POST /api/v1/tcg/extraction-jobs/{id}/reanalyze` (R-1) |

---

## 変更ファイル一覧（file:line）

| ファイル | 変更種別 | 主要行 |
|---|---|---|
| `backend/app/services/tcg_product_master_svc.py` | 新規作成 | 全行 |
| `backend/app/routers/tcg_product_master.py` | 新規作成 | `backend/app/routers/tcg_product_master.py:1` |
| `backend/tests/test_tcg_product_master.py` | 新規作成 | `backend/tests/test_tcg_product_master.py:1` |
| `backend/app/main.py` | 修正 | router 登録追加 |

---

## mark / english_title フィールド確認

#3246 (migration) が `tenant_004.tcg_products` に `mark VARCHAR` / `english_title VARCHAR` を追加する前提。  
本 PR はその列に INSERT する Python コード。適用順: #3246 → #3239（本PR）。

| 確認項目 | 結果 |
|---|---|
| `mark` / `english_title` の列追加 | #3246 migration で実施（`migrations/20260903_180000_tcg_products_mark_en_t004.sql`） |
| B-1 レスポンスに `mark` / `english_title` | `backend/app/routers/tcg_product_master.py:43` (`RegistrationFormItem`) |
| B-3 リクエストに `mark` / `english_title` | `backend/app/routers/tcg_product_master.py:88` (`CreateProductRequest`) |

---

## 触らない範囲

- `backend/app/routers/tcg_analysis_review.py` — 分析レビュー API は別ルーター
- `frontend/` — FE は #3244 で別 PR
- `migrations/` — 列追加は #3246 が担当
