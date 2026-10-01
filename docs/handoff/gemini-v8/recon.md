# Recon: gemini-v8（PR-1 比較試験の道具）

- この文書は何か（1行）: Gemini の書き写し v8 を試す道具を作る前に、今のコードがどうなっているかを事実だけ記録したもの。
- 親（設計）: docs/handoff/gemini-v8/design.md
- 起点: origin/main = 70cd49e28911705b24ab61cf7275dfabcad12e24（worktree 作成時の HEAD）
- 出典: 実装カード（card-gemini-v8-pr1.md）と設計書の recon 事実（2026-10-01）を、worktree 上で行番号を再確認して転記した。評価・提案は書かない。

## 関連ADR（すべて実在を ls で確認）
- docs/adr/ADR-1003-go-delegation-to-opus.md — GO の発行と委任
- docs/adr/ADR-1004-llm-usage-ledger.md — LLM 使用量台帳 llm_usage_events（費用の記録先）
- docs/adr/ADR-085-supplier-prompts.md — 仕入先別 Gemini プロンプト管理
- docs/adr/ADR-100-sa-ingestion-analysis-pipeline.md — 取り込み・解析パイプライン

## 既存コード（変更しない。すべて origin/main の行）
- backend/app/services/gemini_extraction_svc.py:43 `_EMOJI_RE`（絵文字の範囲）
- backend/app/services/gemini_extraction_svc.py:68 `strip_emoji`
- backend/app/services/gemini_extraction_svc.py:141 `_load_db_raw_copy_prompt`
- backend/app/services/gemini_extraction_svc.py:230 `annotate_lines`（[L0001] 形式の ID を付ける）
- backend/app/services/gemini_extraction_svc.py:236 `format_prompt_input`
- backend/app/services/gemini_extraction_svc.py:248 `_get_genai_client`
- backend/app/services/gemini_extraction_svc.py:283 `_GEMINI_MODEL = "gemini-3.1-flash-lite"`
- backend/app/services/gemini_extraction_svc.py:286 `_build_supplier_context_note`（label_map と _PATTERN_MAP は関数内のローカル変数。import できない）
- backend/app/services/gemini_extraction_svc.py:365 `call_gemini_extraction`（v6、temperature 0 は :417）
- backend/app/services/gemini_extraction_svc.py:466 `call_gemini_raw_copy`（v7。block_delimiter だけに絞る :490、ship_format を末尾に足す :498、temperature 0 は :507）
- backend/app/services/gemini_extraction_svc.py:696 `parse_raw_copy_response`
- backend/app/services/extraction_shadow_svc.py:345 `run_shadow_for_job`
- backend/app/services/llm_budget.py:159 `USAGE_PURPOSES`（line_extraction_shadow を含む。新しい purpose は migration の CHECK 制約が要る）
- backend/app/services/llm_budget.py:190 `usage_counts_from`
- backend/app/services/llm_budget.py:281 `record_usage_event_sync`（commit しない。呼び出し側が commit する）
- backend/app/tasks/tcg_extraction.py:70 `TCG_SCHEMA = "public"`
- backend/app/tasks/tcg_extraction.py:91 `_get_sync_session`
- backend/app/tasks/tcg_extraction.py:299 `load_extraction_context`
- backend/app/tools/shadow_backfill.py:60 `_LEDGER_TOTALS_SQL`、:133 `_stop_reason`（費用上限・失敗1回で止まる型。prompt_ab はこの型に合わせる）
- backend/tests/test_tcg_gemini_extraction.py（既存の試験。変更せずに通ること）
- backend/tests/test_extraction_shadow_svc.py（同上）
- backend/tests/test_tcg_work_matching_integration.py:316 共有の `pg` fixture（GITHUB_ACTIONS=true と RLS_ADMIN_DATABASE_URL が必要。CI 専用）

## Dockerfile の事実
- docker-compose.yml:64 と :198 は `build: ./backend`
- backend/Dockerfile:24 `COPY . .`（WORKDIR は :4 の /app）
- backend/.dockerignore は tests/ と *.md などを除外し、app/prompts も *.txt も除外していない。よって backend/app/prompts/raw_copy_v8.txt はイメージに入る。

## SDK の事実（ローカル実測）
- google-genai 2.20.0: GenerateContentConfig に response_json_schema と thinking_config があり、ThinkingConfig に include_thoughts と thinking_level がある。ThinkingLevel は MINIMAL / LOW / MEDIUM / HIGH。
- 本番コンテナの版は未確認（カード「マージ後に試験を流す」1 で確認する）。

## 新規作成予定のファイル（現時点で存在しない）
- 新規作成予定：backend/app/services/gemini_raw_copy_v8.py
- 新規作成予定：backend/app/prompts/raw_copy_v8.txt
- 新規作成予定：backend/app/tools/prompt_ab.py
- 新規作成予定：backend/tests/test_gemini_raw_copy_v8.py
- 新規作成予定：backend/tests/test_prompt_ab.py

## 守り手
- 守り手: .github/workflows/process-artifacts-gate.yml
- 守るもの: v6 と本番 v7 の関数が変わっていないこと（PR 本文の git diff 空の証明と、既存試験が無変更で通ること）
