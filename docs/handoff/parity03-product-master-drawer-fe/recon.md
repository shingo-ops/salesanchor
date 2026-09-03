# PARITY-03 ProductMasterDrawer FE — recon.md

作成日: 2026-09-03  
ブランチ: release/parity03-product-master-drawer-fe

---

## 既存 ADR 検索結果

`git grep -i "parity\|product.master" docs/adr/` → ADR-154-tcg-parity02-gas-python-migration  
PARITY-03 固有 ADR は未起案。ADR-154 方針（GAS→Python 段階移植）の延長として実施。  
ADR-067 (CSS デザイントークン): component-scoped vars 使用。

---

## GAS ソース対応表

| GAS 実装 | FE 移植先 |
|---|---|
| `google.script.run.getProductRegistrationForm(...)` | `api.get('/tcg/products/registration-form?...')` (B-1) |
| `google.script.run.checkProductDuplicates(...)` | `api.post('/tcg/products/check-duplicates', ...)` (B-2) |
| `google.script.run.registerProductMaster(...)` | `api.post('/tcg/products', ...)` (B-3) |
| `google.script.run.searchProducts(query)` | `api.get('/tcg/products/search?query=...')` (B-4) |
| `google.script.run.addSearchKeyword(...)` | `api.post('/tcg/products/:id/search-keywords', ...)` (B-5) |

---

## 変更ファイル一覧（file:line）

| ファイル | 変更種別 | 主要行 |
|---|---|---|
| `frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx` | 新規作成 | 1-407 |
| `frontend/src/features/tcg-analysis-review/SupplierDetailView.tsx` | 修正 | 10,38,91-95,109 |
| `frontend/src/features/tcg-analysis-review/supplier-detail-view.css` | 修正 | 107-313 |

---

## 触らないファイル

- `analysis-review.css` — PR #3232 で削除済み
- `AnalysisReviewWorkspace.tsx` — PR #3232 で削除済み

---

## 依存 PR

| PR | 内容 |
|---|---|
| #3239 | BE Phase 3 API 実装 |
| #3243 | item_corrections テーブル追加 |
| mark/english_title PR | nullable カラム migration |
