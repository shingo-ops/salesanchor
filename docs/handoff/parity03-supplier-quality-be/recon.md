# PARITY-03 仕入元品質サマリー API — recon.md

作成日: 2026-09-03
ブランチ: release/parity03-supplier-quality-be

---

## 既存 ADR 検索結果

`git grep -i "parity" docs/adr/` → ADR-154-tcg-parity02-gas-python-migration
ADR-154 方針（GAS→Python 段階移植）の延長として実施。

---

## GAS ソース対応表

| GAS 実装 | BE 移植先 |
|---|---|
| `api_getSupplierQualitySummaries()` (SupplierQualityAPI.gs:81) | `GET /api/v1/tcg/supplier-quality-summaries` |
| `api_getSupplierSource(supplierId)` (SupplierQualityAPI.gs:45) | `GET /api/v1/tcg/suppliers/{supplier_id}/source` |
| `previewAnalysisReviewStatusTabs` | **削除**（SupplierDetail は StatusTab を使わない） |

---

## 変更ファイル一覧（file:line）

| ファイル | 変更種別 | 主要行 |
|---|---|---|
| `backend/app/services/tcg_supplier_quality_svc.py` | 新規作成 | 全行 |
| `backend/app/routers/tcg_supplier_quality.py` | 新規作成 | 全行 |
| `backend/tests/test_tcg_supplier_quality.py` | 新規作成 | 全行 |
| `backend/app/main.py` | 修正 | import 追加, include_router 追加 |
| `backend/app/routers/tcg_analysis_review.py` | 修正 | A-2 エンドポイント削除, status_tab_counts 削除 |
| `backend/app/services/tcg_analysis_review_svc.py` | 修正 | fetch_status_counts 削除, strip_raw_text 追加 |
| `backend/tests/test_tcg_analysis_review.py` | 修正 | A-2 テスト削除 |

---

## 触らない範囲

- `backend/app/routers/tcg_analysis_review.py` の A-1 エンドポイント（保持）
- `backend/app/services/tcg_analysis_review_svc.py` の `fetch_analysis_results()` ロジック本体（strip_raw_text 追加以外）
- `migrations/` 一切（DB変更なし）

---

## 既存 ADR との整合

- ADR-154: GAS 解析レビュー UI → React 段階移植（第2段階: 仕入元サマリー）
- ADR-072: write endpoint なし（読み取り専用）のため reset_tenant_context 不要
