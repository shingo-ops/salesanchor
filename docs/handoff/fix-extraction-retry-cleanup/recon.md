# recon: fix-extraction-retry-cleanup

**対象 ADR**: ADR-154
**design**: docs/handoff/fix-extraction-retry-cleanup/design.md

## 問題

本番 DB 調査で extraction_items が stale データとして残存する事例を 4 件確認。
原因: リトライ時に前回の extraction_items が削除されず、INSERT が重複する。

## 調査箇所

- `backend/app/tasks/tcg_extraction.py:409` — `_run_recorded_extraction()` の items INSERT 直前
- `backend/app/services/tcg_diagnostics_svc.py:209` — `retry_extraction()` の status reset 直前

## FK 制約確認

`analysis_results.extraction_item_id → extraction_items.id ON DELETE CASCADE`
→ extraction_items 削除時に analysis_results も自動削除される（整合性保証）。
