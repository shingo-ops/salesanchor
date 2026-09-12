# recon — tcg-is-active-filter (IMP-35)

## 調査対象

IMP-32 で特定した二重計上リスク: `source_messages` を参照する 3 サービスの SQL が
`is_active = TRUE` フィルタを欠いており、再アップロード後に旧データが集計に混入する。

## 根本原因の確認（IMP-32 特定済み）

### supersede の仕組み（ADR-154 / `backend/app/services/tcg_line_import_svc.py`）

再アップロード時:

1. 旧 `source_messages` の `is_active = FALSE`、`superseded_by = new_id` をセット
2. 新 `source_messages` を INSERT
3. 新 `extraction_jobs` / `extraction_items` / `analysis_results` は新 SM から派生

旧 `extraction_jobs`・`items`・`analysis_results` は **削除されない**。
`source_messages.is_active = FALSE` が唯一の除外手段。

### 修正前に is_active フィルタが欠落していた箇所

| # | ファイル | 行 | 問題 |
|---|---|---|---|
| 1 | `backend/app/services/tcg_supplier_quality_svc.py:41-49` | 41 | `FROM source_messages sm` に WHERE なし（GROUP BY 前） |
| 2 | `backend/app/services/tcg_supplier_quality_svc.py:77-85` | 83 | `WHERE ts.code = :supplier_id` のみ（is_active 条件なし） |
| 3 | `backend/app/services/tcg_distribution_svc.py:226-231` | 228 | `JOIN source_messages sm ON sm.id = ej.source_message_id` のみ |
| 4 | `backend/app/services/tcg_analysis_review_svc.py:31-39` | 35 | `_BASE_FROM` f-string の JOIN 条件に is_active なし |

### DDL 確認

`migrations/20260831_110000_create_tcg_analysis_tables_t004.sql:220`:

- `source_messages.is_active BOOLEAN NOT NULL DEFAULT TRUE`
- `source_messages.superseded_by UUID REFERENCES %I.source_messages(id)`（FK あり、DEFERRABLE なし）
- `source_messages.raw_sha256` には **UNIQUE 制約なし**（重複アップロードは is_active で区別）
- `import_jobs.raw_sha256` には UNIQUE 制約あり（同内容の再 import job 生成を防ぐ）

### 既存 ADR

- `docs/adr/ADR-154-tcg-parity02-gas-python-migration.md` — TCG LINE インポートパイプライン設計。
  is_active フィルタの記述なし（IMP-32 で新規発見）。

## 影響範囲

| ファイル | 変更行数 | 呼び出し元 |
|---|---|---|
| `backend/app/services/tcg_supplier_quality_svc.py` | +3 | `backend/app/routers/tcg_supplier_quality.py` のみ |
| `backend/app/services/tcg_distribution_svc.py` | +1 | `backend/app/routers/tcg_distribution.py` のみ |
| `backend/app/services/tcg_analysis_review_svc.py` | +1 | `backend/app/routers/tcg_analysis_review.py` のみ |
| `backend/tests/test_tcg_is_active_filter.py` | 新規 97 行 | CI テスト |

DB 書き込みなし（全サービスは読み取り専用）。
