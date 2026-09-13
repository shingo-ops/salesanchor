# PARITY-03 仕入元品質サマリー API — design.md

作成日: 2026-09-03
ブランチ: release/parity03-supplier-quality-be
参照: docs/handoff/parity03-supplier-quality-be/recon.md
対象ADR: ADR-154（GAS→Python マイグレーション方針）

---

## 目的

GAS の `api_getSupplierQualitySummaries` / `api_getSupplierSource` を
Python/FastAPI に移植し、FE の SupplierQualityPage / SupplierDetailPage から
fetch() で呼び出せる REST API を提供する。

**本 PR 範囲**: BE のみ（API 2本 + テスト + A-2 削除）。

---

## エンドポイント設計

### S-1: GET /api/v1/tcg/supplier-quality-summaries

| 項目 | 値 |
|---|---|
| 認証 | `require_super_admin` |
| クエリパラメータ | なし（全件返却・paginate なし） |
| レスポンス | `SupplierQualitySummariesResponse` (ok + summaries[]) |
| 集計起点 | `source_messages`（GAS Sources シート相当） |

**source 起点の理由**: items=0 の仕入元（SP0057/Hiroshi 等）が items 起点では欠落する。
GAS `SupplierQualityAPI.gs:114-131` と同じく source_messages を先に走査して
全仕入元を初期化し、analysis_results で加算する。

### S-2: GET /api/v1/tcg/suppliers/{supplier_id}/source

| 項目 | 値 |
|---|---|
| 認証 | `require_super_admin` |
| パスパラメータ | `supplier_id`: tcg_suppliers.code（例: SP0057） |
| レスポンス | `SupplierSourceResponse` (ok, found, rawText 等) |

---

## 受け入れ基準と検証方法

| 基準 | 検証方法 | 守り手 |
|---|---|---|
| 認証なしで 401/403 (S-1) | `test_tcg_supplier_quality.py::test_supplier_quality_summaries_requires_auth` | CI |
| 認証なしで 401/403 (S-2) | `test_tcg_supplier_quality.py::test_supplier_source_requires_auth` | CI |
| レスポンス形状が Pydantic スキーマと一致 | `test_tcg_supplier_quality.py::test_supplier_quality_summaries_response_shape` | CI |
| SP0057（items=0）がサマリーに含まれる | `test_tcg_supplier_quality.py::test_zero_items_supplier_included` | CI |
| A-2 status-counts が 404 | 削除後の自動テスト（test_tcg_analysis_review.py から除去済み） | CI |
| conditionFallbackCount が null 固定 | Pydantic `int \| None` 定義 + テスト | CI |

---

## 外部・過去事例の参照と我々への応用

PARITY-03 第1段階（PR #3225）で確立した `require_super_admin` + `AsyncSession` 依存注入パターンを踏襲。
source 起点集計は GAS `SupplierQualityAPI.gs:81-163` の設計をそのまま SQL で表現。
items=0 仕入元欠落問題（SP0057/Hiroshi）は LEFT JOIN で解決（GAS の `bySource` 初期化ステップに対応）。

---

## 弊害・リスク

| リスク | 対策 |
|---|---|
| A-2 削除で既存 FE（TcgAnalysisReviewPage）が壊れる | FE PR で TcgAnalysisReviewPage 自体を削除するため無問題 |
| source_messages.supplier_channel_id が NULL の場合 | `JOIN supplier_channels` は INNER JOIN のため NULL 行は除外される。インジェスト時に必ず設定される設計 |
| strip_raw_text=false 時に大量 raw_text が返る | SupplierDetailPage 側で strip_raw_text=true を必ず指定 |

---

## 移行 migration

**なし**。本 PR は読み取り専用 API のためテーブル・カラム追加は行わない。
