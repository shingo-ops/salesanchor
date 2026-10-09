# Recon: prompt-ab-recompute（保存済みの応答から後処理だけをやり直す道具）

- この文書は何か（1行）: 道具を作る前に、触る場所の今の姿を事実だけ記録したもの。
- 親（設計）: docs/handoff/prompt-ab-recompute/design.md
- 起点: origin/main = 5bc79ef9710133af21bef437423ab0d02ecfda60（worktree 作成時の HEAD）。行番号はこの時点。評価・提案は書かない。
- 設計仕様書（あるべき姿）: 該当なし（比較試験の道具の追加。本番の経路・マスタ・表に触れない）。

## 既存ADRの検索
- 実行: git grep -n -i -E "prompt_ab|recompute" -- docs/adr → 0件（該当なし）。
- 関係する ADR（ls で実在を確認）
  - docs/adr/ADR-100-sa-ingestion-analysis-pipeline.md
  - docs/adr/ADR-1004-llm-usage-ledger.md
- 前の版: docs/handoff/gemini-v102/design.md（v102 の後処理 F1〜F6）。

## 事実
- file:line 一覧（origin/main 5bc79ef97 時点）
  - backend/app/tools/prompt_ab.py:160 fetch_job_ids
  - backend/app/tools/prompt_ab.py:217 _load_v10_masters
  - backend/app/tools/prompt_ab.py:253 _v102_row_fields
  - backend/app/tools/prompt_ab.py:266 _append_jsonl
  - backend/app/tools/prompt_ab.py:523 record_usage_event_sync（run_ab の中。Gemini 呼び出しの後）
  - backend/app/tasks/tcg_extraction.py:312 load_extraction_context
- backend/app/tools/prompt_ab.py は 633 行（wc -l）。CLAUDE.md の目安は 800 行まで。
- v102 の後処理の呼び出しは backend/app/tools/prompt_ab.py の _v102_row_fields（parse_v101_response → extract_v101_items(reassign=True, v102_fixes=True)）。失敗しても止めず v102_items_error を残す。
- マスタの読み込みは backend/app/tools/prompt_ab.py の _load_v10_masters（1回の実行で1回）。
- run_id → job_id は fetch_job_ids、原文と仕入元の文脈は load_extraction_context（backend/app/tasks/tcg_extraction.py）。いずれも読み取りのみ。
- 費用の台帳への書き込みは run_ab の中の record_usage_event_sync だけ（Gemini の呼び出しの後）。
- JSONL の追記は _append_jsonl。
