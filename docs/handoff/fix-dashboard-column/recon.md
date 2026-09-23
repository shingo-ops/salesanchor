# recon: fix-dashboard-column

## 対象ファイル
- backend/app/services/tcg_analysis_dashboard_svc.py:113 — `extraction_attempts ORDER BY created_at DESC`
- backend/app/services/tcg_analysis_dashboard_svc.py:122 — `analysis_results ORDER BY created_at DESC`

## DB実測（本番 tenant_004）

### extraction_attempts カラム一覧
id, extraction_job_id, source_message_id, parent_attempt_id, started_at, response_received_at, finished_at, phase, input_payload, input_sha256, input_bytes, requested_model, prompt_version, code_version, response_text, response_sha256, response_bytes, parsed_items, parsed_bytes, item_count, validation_result, error_code
→ `created_at` は存在しない。`started_at` が正しい。

### analysis_results カラム一覧
id, extraction_item_id, pid_resolved, pid_basis, unit_canonical, unit_resolved, condition_canonical, condition_basis, quantity_normalized, price_normalized, note_ja, status, exclusion, needs_review, review_reasons, engine_version, computed_at, updated_at, unit_inferred, unit_basis, unit_confidence, unit_infer_reason, product_id, unit_id, condition_id
→ `created_at` は存在しない。`computed_at` が正しい。

### extraction_jobs カラム一覧
id, source_message_id, status, extracted_at, error_message, prompt_version, created_at, work_reference_snapshot, work_reference_sha256
→ `created_at` は存在する（変更不要）。

## 関連ADR
- ADR調査: `git grep -i "dashboard" docs/adr/` → 解析ダッシュボード専用ADRなし
- 本修正はSQL文字列内のカラム名誤りの修正のみ。ADR適用範囲外。
