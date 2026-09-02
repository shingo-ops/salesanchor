# PARITY-03 解析レビュー API — design.md

作成日: 2026-09-02  
ブランチ: release/parity03-analysis-review-be  
参照: docs/handoff/parity03-analysis-review-be/recon.md  
対象ADR: ADR-154（GAS→Python マイグレーション方針）

---

## 目的

GAS ベースの解析レビュー画面（`getAnalysisReviewPage` / `previewAnalysisReviewStatusTabs`）を  
Python/FastAPI バックエンドに移植し、フロントエンド React から fetch() で呼び出せる REST API を提供する。

**本 PR 範囲**: BE のみ（API 2本 + テスト）。FE 移植は別 PR。

---

## エンドポイント設計

### A-1: GET /api/v1/tcg/analysis-results

| 項目 | 値 |
|---|---|
| 認証 | `require_super_admin` |
| クエリパラメータ | `query`, `provider`, `status_tab`, `offset`, `limit`, `review_only`, `unregistered_only`, `unresolved_unit_only` |
| レスポンス | `AnalysisResultsResponse` (items + total + providers + status_tab_counts) |
| ページング単位 | アイテム単位（GAS の groupBySource=false 相当） |

### A-2: GET /api/v1/tcg/analysis-results/status-counts

| 項目 | 値 |
|---|---|
| 認証 | `require_super_admin` |
| クエリパラメータ | `query`, `provider` |
| レスポンス | `StatusCountsResponse` (status_tab_counts のみ) |

---

## 受け入れ基準と検証方法

| 基準 | 検証方法 | 守り手: |
|---|---|---|
| 認証なしで 401/403 | `test_tcg_analysis_review.py::test_list_analysis_results_requires_auth` | CI |
| status-counts も 401/403 | `test_tcg_analysis_review.py::test_status_counts_requires_auth` | CI |
| レスポンス形状が Pydantic スキーマと一致 | `test_tcg_analysis_review.py::test_list_analysis_results_response_shape` | CI |
| status_tab_counts の 6キーが全て存在 | 同上 | CI |
| 不正 status_tab は ALL にフォールバック | `test_tcg_analysis_review.py::test_status_tab_invalid_falls_back_to_all` | CI |
| DB アクセスは tenant_004 スキーマのみ | `_BASE_FROM` 定数が `tenant_004.` で固定 | コードレビュー |
| 書き込みなし（SELECT のみ） | サービス層に `db.commit()` / `db.execute` INSERT/UPDATE/DELETE が存在しない | コードレビュー |

---

## データフロー

```
FE (fetch) 
  → GET /api/v1/tcg/analysis-results
  → router (tcg_analysis_review.py)
  → require_super_admin dependency
  → fetch_analysis_results() (tcg_analysis_review_svc.py)
    → _build_where() でフィルタ条件生成
    → COUNT クエリ (total)
    → DISTINCT providers クエリ
    → paginated items クエリ
    → fetch_status_counts() (内部呼び出し)
  → AnalysisResultsResponse (Pydantic)
  → JSON レスポンス
```

---

## 外部・過去事例の参照と我々への応用

GAS `google.script.run.*` → REST API 移植パターン:  
既存 PARITY-01 (`backend/app/services/tcg_parallel_report_svc.py`) と同一方針。`require_super_admin` + `AsyncSession` 依存注入。ADR-154 方針に従い読み取り専用 API を先行移植し、フロントエンドから fetch() で直接呼び出す構成とする。

---

## 弊害・リスク

| リスク | 対策 |
|---|---|
| 実 DB (tenant_004) が CI に存在しない | テストはサービス層をモック。実 DB テストは `TEST_PG_URL` skipif パターンで対応（今回は追加しない・実 DB 結合テストは別タスク） |
| JOIN 6 テーブルの性能 | `received_at DESC` + `line_start ASC` ソートは本番データ 195 件規模のため問題なし。インデックス追加は将来タスク |
| tenant_004 外スキーマへの誤アクセス | `TCG_SCHEMA = "tenant_004"` 定数で固定、コードレビューで確認 |

---

## 移行 migration

**なし**。本 PR は読み取り専用 API のためテーブル・カラム追加は行わない。  
`deploy.yml` 変更不要。`migration-guard.yml` のブロックなし。
