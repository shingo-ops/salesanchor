# design: 解析段の失敗を DB に残し、1回だけ自動でやり直す

- 日付: 2026-10-17 / 設計: Opus（PO「別の問題を解消する」）
- recon: docs/handoff/analysis-failed-record/recon.md
- 関連 ADR: ADR-1003（GO委任）。docs/handoff/extraction-job-recovery/design.md（「表・列は増やさない」を守る）。ADR-027 該当なし（UI 変更なし）
- 対象 ADR: 該当 ADR なし（recon に検索結果を記載）

## 変更
1. `backend/app/tasks/tcg_extraction.py`
   - `_record_analysis_failed`: 解析の except 2か所（v102・v6）で rollback の後に `UPDATE public.extraction_jobs SET error_message='ANALYSIS_FAILED' WHERE id=:ej AND status='done'` を commit。書き込み自体の失敗は logger.error のみ。status と extraction_attempts は変えない。例外の中身は書かない（S3）。
   - `reanalyze_v102_job`: 解析成功後、同じ commit で `error_message` が ANALYSIS_FAILED / ANALYSIS_FAILED_RETRIED の行だけ NULL に戻す。
2. `backend/app/tasks/tcg_extraction_recovery.py`
   - `retry_analysis_failed_jobs`: status='done' AND error_message='ANALYSIS_FAILED' AND prompt_version LIKE 'v102:%' AND extracted_at が5分より前、1回20件まで。1件ずつ 'ANALYSIS_FAILED_RETRIED' に更新（1件更新できたときだけ）→ `v102_reanalyze_after_correction_task.delay`。10分ごとの `_run_recovery` から呼ぶ。件数を logger.info。
3. 無限ループ防止: 積む前に RETRIED へ書き換える。やり直しも失敗すれば RETRIED のまま残り、再び拾わない。成功で NULL。
4. 触らない: migration・列追加・extraction_attempts・画面。

## 検証
| 基準 | 検証方法 |
|---|---|
| T1 解析が例外 → status 'done' のまま error_message='ANALYSIS_FAILED'、自動配信は呼ばれない、例外の中身は書かない、書込失敗でも例外を出さない | backend/tests/test_analysis_failed_record.py::TestT1AnalysisFailureRecorded |
| T2 救済: 条件の SELECT・RETRIED 書換→delay 1回・2回目は積まれない・更新0件は積まない | 同 TestT2RecoveryRetry（v6・新しすぎ・NULL・RETRIED を拾わない条件は SELECT の WHERE を検証） |
| T3 reanalyze 成功で ANALYSIS_FAILED/RETRIED だけ NULL。失敗時・v6 は触らない | 同 TestT3ReanalyzeClearsMark |
| 既存テストが緑 | test_tcg_extraction_recovery.py, test_line_analysis_v102_svc.py ほか |
| K4 本番反映後、救済タスクがエラーなく回り、error_message 別件数が反映前後で同じ | 本番ログ・read-only 件数（反映後に実施。未実施） |

## 外部事例
Dead-letter / retry-once の定石に沿う（失敗を印で残し、有限回の再試行後は人に渡す）。本件は既存列の再利用のみで外部依存なし。

## 戻し方
PR を revert。DB に残った error_message は無害（status は不変）。
