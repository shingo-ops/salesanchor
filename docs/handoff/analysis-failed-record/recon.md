# recon: 解析段の失敗（ANALYSIS_FAILED）の記録とやり直し

- 日付: 2026-10-17 / 基準: origin/main 15114e878
- 詳細な調査記録（原本）: ~/CC報告ファイル-keep/accuracy-20261014/g28-bulk-price/post/side4/p2_analysis_failed/recon.md, recon2.md
- 着手前の既存 ADR 検索: `docs/adr/` に 'ANALYSIS_FAILED' を含む ADR は無し。解析失敗の記録方針を定めた ADR も無し（ADR-100:95 は通知が弱いと述べるのみ）。

## 事実（file:line は変更前の origin/main）
- `/Users/tanizawashingo/salesanchor/backend/app/tasks/tcg_extraction.py:451-454`（v102）と `:600-603`（v6）の except は、rollback・logger.error・analysis_stats だけで DB に何も残さない。この時点で job.status は 'done' のまま。
- 抽出済みの job は `extraction_jobs.status` 'done'。停滞救済 `/Users/tanizawashingo/salesanchor/backend/app/tasks/tcg_extraction_recovery.py:76,125` は running/pending だけが対象で、done は拾わない。
- `extraction_jobs.error_message` は TEXT。status に CHECK 制約なし（`/Users/tanizawashingo/salesanchor/migrations/20260921_110000_pipeline_tables_public.sql:80-90`）。
- 直近7日の新規 job は全て v102（recon2 §6）。
- `reanalyze_v102_job`（`tcg_extraction.py:706-724`）は Gemini を呼ばず run_v102_analysis だけをやり直す。

## 実装前の点検（error_message を done の job で読む箇所）
- `backend/app/routers/tcg_analysis_dashboard.py:1080,1128`: /tcg/extraction-errors。failed の attempt を持つ job だけが対象で、表示は `error_code or job.error_message`。解析失敗の job は attempt が completed のみなので対象に出ない。
- `backend/app/tasks/tcg_extraction.py:576`（v6 の PARTIAL_PARSE_ERRORS を done の job に書く既存の動き）。done の job に error_message が入るのは既存の仕様。
- フロントで job の error_message を読むのは ExtractionErrorLogPanel（上記 API の応答）のみ。集計（tcg_import_progress, tcg_analysis_dashboard_svc）は status を読み error_message を見ない。
- 以上から、画面・集計にエラーとして新たに出る箇所は無し。
