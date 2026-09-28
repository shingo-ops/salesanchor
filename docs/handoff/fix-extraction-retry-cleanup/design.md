# design: fix-extraction-retry-cleanup

**対象 ADR**: ADR-154
**recon**: docs/handoff/fix-extraction-retry-cleanup/recon.md

## 設計方針

リトライ時の冪等性を 2 箇所で保証する。

- 修正A: `retry_extraction()` — status reset 前に `DELETE FROM extraction_items WHERE extraction_job_id = ANY(:ids)`
- 修正B: `_run_recorded_extraction()` — INSERT 前に `DELETE FROM extraction_items WHERE extraction_job_id = :ej_id`

FK CASCADE により `analysis_results` も連動削除される（DB 層保証）。

## 触るファイル

- `backend/app/tasks/tcg_extraction.py`（INSERT前にDELETE追加）
- `backend/app/services/tcg_diagnostics_svc.py`（status reset前にDELETE追加）

## 削除するファイル

- なし

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| リトライ後 extraction_items が重複しないこと | 本番リトライ後のカウント確認 |
| analysis_results も連動削除されること | FK CASCADE 制約（DB 層） |
| 正常な初回抽出に影響がないこと | DELETE 対象 0 件で空振り |

## 外部・過去事例の参照と我々への応用

- 冪等 INSERT パターン（DELETE-then-INSERT）: SQL アンチパターン対策として一般的な手法。我々のケースでは INSERT 前 DELETE により extraction_items の重複を根絶する。
- PostgreSQL FK CASCADE（"ON DELETE CASCADE"）: 公式ドキュメントに記載の参照整合性機能。analysis_results → extraction_items の FK CASCADE により、削除時の整合性を DB 層で保証する。

## 維持の仕組み

守り手: `backend/app/tasks/tcg_extraction.py` / `backend/app/services/tcg_diagnostics_svc.py`
- DELETE-then-INSERT パターンがコード上で明示されるため、将来の変更時にも意図が伝わる
- FK CASCADE 制約が DB 層で analysis_results との整合性を永続的に保証する
