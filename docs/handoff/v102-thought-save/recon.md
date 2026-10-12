# recon: v102 の Gemini の思考要約を保存する

- 基準: origin/main `2fc17c538773cff2723d13df84f910a09505b5b3`（2026-10-12）。調査は Sonnet（読み取りのみ）＋ Opus の確認。
- PO の指示（原文 2026-10-12）:「思考要約は、本番では保存されていません。プログラムが受け取った後に捨てています（line_analysis_v102_svc.py →捨てない仕組みにしてくれ」

## 1. ADR の検索
- 生の応答・保存期間・JSONB の大きさを定める ADR の段落は、grep の範囲では見つからなかった。
- ADR-1004 は思考を「トークン数」で記録する決定だけ（llm_usage_events.thoughts_tokens）。
- ADR-1007（`docs/adr/ADR-1007-migration-structure-only-run-once.md`）は「migration は構造だけ」。
- ADR-135・ADR-136：migrations を含む PR は PO の「GO #番号」が要る。

## 2. 今の流れ（思考は捨てられている）
- `backend/app/services/gemini_raw_copy_v8.py:166-179` `_split_parts` は `part.thought` の part の text を `list[str]` に集める。`:231`・`:235` で `thought_summaries` を返す。
- `backend/app/services/line_analysis_v102_svc.py` の `run_v102_extraction` は、`response_text` だけを `recorder.on_response(response_text)` に渡す。thought_summaries を参照する行は、このファイルに無い（Opus が grep で確認：このファイルで "thought" が出るのは :425・:433 の設定だけ）。
- thought_summaries を読み書きするのは、`backend/app/services/gemini_raw_copy_v8.py` と `backend/app/tools/prompt_ab.py:210, :552`（試験の道具。JSONL のファイルに書く）だけ。

## 3. 保存先
- `public.extraction_attempts`（Gemini の呼び出し1回＝1行）。作成は `migrations/20260921_110000_pipeline_tables_public.sql:112-156`、その後の追加は `migrations/20260927_130000_add_extraction_token_cost_columns.sql` の3列だけ。本番は25列。
- `backend/app/services/tcg_extraction_record_svc.py:132-160` の `on_response` が、response_text・response_bytes・response_sha256 を UPDATE して commit する。`MAX_BYTES` は 8,388,608（:18）。
- 制約の complete_check は、思考の列には関わらない。

## 4. 大きさ（本番・読み取り）
- v102 の line_extraction の thoughts_tokens（173件）：最小 486・中央 3,662・95% 8,215・最大 12,139。
- extraction_attempts は 2,800 行、総サイズ 411MB（うち TOAST 407MB。内訳は未確認）。

## 5. 読む側
- `backend/app/routers/tcg_diagnostics.py:123-129` の `GET /tcg/diagnostics/extraction-jobs/{job_id}/attempts/{attempt_id}` は全列を返す（super admin のみ・no-store）。列を足すと、そのまま応答に出る。
- frontend で extraction_attempts を読む箇所は無い。

## 6. 未確認
- extraction_attempts の削除・保存期間の処理の有無。
- 思考のテキストのバイト数（トークン数からの換算は未測定）。
