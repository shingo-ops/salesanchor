# PARITY-03 解析レビュー API — recon.md

作成日: 2026-09-02  
ブランチ: release/parity03-analysis-review-be

---

## 既存 ADR 検索結果

`git grep -i "parity" docs/adr/` → 該当 ADR なし  
`docs/adr/FEATURE-INDEX.md` → TCG 関連: ADR-045 (migration), ADR-025 (DB INSERT 禁止) のみ  
PARITY-03 固有の ADR は未起案。読み取り専用 API のため起案不要と判断。

---

## DB スキーマ確認（VPS PostgreSQL 実機）

接続: `jarvis_db`、スキーマ: `tenant_004`

### 使用テーブル

| テーブル | 主キー型 | 備考 |
|---|---|---|
| `tenant_004.analysis_results` | UUID (id) | `product_id` = UUID (FK to tcg_products.id), `pid_resolved` bool, `pid_basis` text, `unit_canonical` text, `unit_resolved` bool, `condition_canonical` text, `note_ja` text, `status` text, `exclusion` text |
| `tenant_004.extraction_items` | UUID (id) | `raw_product_name`, `raw_quantity`, `raw_price`, `raw_unit`, `raw_state`, `raw_memo`, `line_start`, `line_end`, `extraction_job_id` UUID |
| `tenant_004.extraction_jobs` | UUID (id) | `source_message_id` UUID |
| `tenant_004.source_messages` | UUID (id) | `supplier_channel_id` UUID, `raw_text` text, `received_at` timestamptz |
| `tenant_004.supplier_channels` | UUID (id) | `supplier_id` UUID |
| `tenant_004.tcg_suppliers` | UUID (id) | `name` text |
| `tenant_004.tcg_products` | UUID (id) | `code` text |

### JOIN チェーン（実機確認済み）

```sql
FROM tenant_004.analysis_results ar
JOIN tenant_004.extraction_items ei ON ei.id = ar.extraction_item_id
JOIN tenant_004.extraction_jobs ej ON ej.id = ei.extraction_job_id
JOIN tenant_004.source_messages sm ON sm.id = ej.source_message_id
JOIN tenant_004.supplier_channels sc ON sc.id = sm.supplier_channel_id
LEFT JOIN tenant_004.tcg_suppliers ts ON ts.id = sc.supplier_id
LEFT JOIN tenant_004.tcg_products p ON p.id = ar.product_id
```

エラー経緯:
- `suppliers.id` (INTEGER) vs `supplier_channels.supplier_id` (UUID) は型不一致 → `tcg_suppliers` を使用
- `tcg_products.code` は text だが結合は `tcg_products.id = analysis_results.product_id` (UUID = UUID)

---

## GAS ソース対応表

| GAS 関数 | 移植先 |
|---|---|
| `getAnalysisReviewPage(params)` | `fetch_analysis_results()` @ `backend/app/services/tcg_analysis_review_svc.py` |
| `previewAnalysisReviewStatusTabs(params)` | `fetch_status_counts()` @ 同上 |

GAS ソース場所: `sqr07_work/analysis-review-ui/src/` (salesanchor リポジトリ外)

---

## 変更ファイル一覧（file:line）

| ファイル | 変更種別 | 主要行 |
|---|---|---|
| `backend/app/services/tcg_analysis_review_svc.py` | 新規作成 | 全行 |
| `backend/app/routers/tcg_analysis_review.py` | 新規作成 | 全行 |
| `backend/app/main.py` | 修正 | L93 (import 追加), L554-558 (include_router 追加) |
| `backend/tests/test_tcg_analysis_review.py` | 新規作成 | 全行 |

### main.py 変更前後

**L93 付近（import）**  
変更前: `tcg_parallel_report,  # MIG-04 ...`  
変更後: `tcg_analysis_review, ...` (1行追加)

**L554 付近（include_router）**  
追加:
```python
app.include_router(
    tcg_analysis_review.router, prefix="/api/v1", tags=["super-admin"],
)
```

---

## 触らない範囲

- `backend/app/routers/super_admin_tcg.py` — 既存 TCG マスタ CRUD（無関係）
- `backend/app/tasks/tcg_mirror.py` — GAS Mirror タスク（無関係）
- `backend/tcg_migration/` — migration スクリプト群（読み取り専用 API のため migration なし）
- `.github/workflows/deploy.yml` — migration なしのため変更不要

---

## 既存 ADR との整合

- ADR-045: migration additive-only → 本 PR は migration を含まない（テーブル追加なし）
- ADR-072: `db.commit()` 後 `reset_tenant_context()` → 本 API は読み取り専用のため不要
- ADR-025: 本番 DB への手動 INSERT 禁止 → 本 API は SELECT のみ
