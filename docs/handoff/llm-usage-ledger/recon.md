# recon: LLM 使用量台帳（llm_usage_events）

- 対象: docs/handoff/llm-usage-ledger/design.md（Opus 設計、PO 方針承認済み 2026-09-30）
- 基準コミット: origin/main 4de895d48583e170bf6ef4ecb38166da7ee3f309 以降
- 目的: PO「使用量は最大限細分化してくれるとどこで多く消費しているとか適切かどうかも判断しやすい」→ Gemini 呼び出し4経路すべてを1か所（SSOT）で記録する

## 1. Gemini 呼び出し経路（本番）

| purpose | 呼び出し元 | usage を読む箇所 | SDK |
|---|---|---|---|
| line_extraction | `backend/app/services/gemini_extraction_svc.py:364` `call_gemini_extraction()` | `:443-449`（改修後）usage_metadata から `llm_budget.usage_counts_from()` で読む | google-genai |
| line_extraction_shadow | `backend/app/services/gemini_extraction_svc.py:465` `call_gemini_raw_copy()` | 同ファイル `:524-534`（改修後） | google-genai |
| inventory_parse_fallback | `backend/app/services/inventory_parser_llm.py:222` `parse_with_gemini()` | `:319-322`（改修後） | google-generativeai |
| translation_inbound / _escalation / translation_outbound | `backend/app/services/message_translator.py:398` `_call_gemini()` | `:431-434`（改修後） | google-generativeai |

5つ目の `tcg_work_comparison_svc.call_work_model` はテストからしか呼ばれない本番未結線経路のため対象外（design.md §4）。

## 2. 書き込み先（記録先の分散、改修前）

- `extraction_attempts`（`backend/app/services/tcg_extraction_record_svc.py` `AttemptRecorder.complete()` L172-191 / `fail()` L193-243）: input_tokens/output_tokens/cost_usd を UPDATE で書いていた
- `extraction_shadow_runs`（`backend/app/services/extraction_shadow_svc.py` `insert_shadow_run()` L99-148）: 同3列、全件 NULL（`_calc_shadow_cost` は呼ばれていたが実質未使用値だった旨は design.md 前提調査で確認済み）
- `tenant_llm_budgets`（`backend/app/services/llm_budget.py` `record_cost()`）: テナント別の月合計金額のみ。本PRでは変更しない（budget 上限判定用に継続）
- 翻訳・在庫解析フォールバックには1回ごとの記録が無かった（`discord_inbound_messages.llm_cost_usd` 列はあるが書き込みコードなし、grep 0件）

## 3. AttemptRecorder の INSERT/UPDATE 順序（FK 有効性の根拠）

`before_send()`（`tcg_extraction_record_svc.py:68-104`）が `extraction_attempts` に self.id で INSERT + commit する。`gemini_extraction_svc.call_gemini_extraction()` は `recorder.before_send(payload)`（:420 付近）を呼んでから `client.models.generate_content(...)` を呼ぶ（:427-432）ので、Gemini 応答を受け取る時点（`on_response`/`complete`/`fail`）では `extraction_attempts` 行が必ず存在する。→ `llm_usage_events.extraction_attempt_id` の FK は `complete()`/`fail()` 時点で有効。

`extraction_shadow_svc.insert_shadow_run()`（`extraction_shadow_svc.py:99-148`、改修後は tokens/cost 列を書かない）は1回の INSERT で `run_id`（`gen_random_uuid()` 相当、Python 側で `uuid.uuid4()`）を確定して返す。呼び出し元 `run_shadow_for_job()`（:310-393）は `run_id = insert_shadow_run(...)` の直後に `record_usage_event_sync(..., extraction_shadow_run_id=run_id)` を呼べる。

## 4. 単価・SDK usage フィールド（design.md §3-3 の根拠）

- Google 公式料金表（`llm_budget.py` `LLM_PRICING` 定数、2026-09-11 追記コメント）: `gemini-3.1-flash-lite` の出力単価コメントに "Output price (including thinking tokens)" と明記。thoughts が課金対象に含まれる。
- SDK の usage_metadata フィールド: `prompt_token_count` / `cached_content_token_count` / `candidates_token_count` / `thoughts_token_count` / `tool_use_prompt_token_count` / `total_token_count`。`total = prompt + candidates + tool_use_prompt + thoughts`（`candidates_token_count` 自体は thoughts を含まない）。閉じた PR #3883 (`origin/release/gemini-thinking-tokens-cost`) の `billable_output_tokens()` 実装・テストがこの前提を裏付ける（`candidates + thoughts` を課金対象出力とする）。

## 5. migration-guard / PUBLIC_TABLES

`.github/workflows/migration-guard.yml:224` の `PUBLIC_TABLES` に `extraction_attempts` `extraction_shadow_runs` `discord_inbound_messages` は既に含まれている。`llm_usage_events` を追加した（本 PR）。

## 6. discord_inbound_messages.id 型

`migrations/059_create_discord_inbound_messages.sql:40` — `id SERIAL PRIMARY KEY`（= INTEGER）。`llm_usage_events.discord_inbound_message_id` は INTEGER、FK は張らない（design.md §3-1: テーブルは運用停止中で型差異の危険を避ける）。

## 7. ADR 番号

`docs/adr/` の最新10xx系は `ADR-1002-unify-product-id-and-fix-migration-compat.md`。`ADR-1004` / `ADR-1004` はどちらも未使用（`ls docs/adr | grep -E "1003|1004"` 0件）。設計案は当初 `ADR-1004` を仮番号としていたが、次の空き番号は `ADR-1004` のため本 PR では `ADR-1004` を採番した（design.md 内の `ADR-1004` 表記は `ADR-1004` に修正済み）。

## 8. deprecated 列チェック（CI）

`.github/scripts/check_deprecated_columns.sh` は `trust_level` / `products.unit_price` / `customers.transaction_count` の3項目に固定されたシェル関数（`check <label> <pattern> [exempt]`）であり、汎用の「列名リストファイル」ではない。extraction_attempts / extraction_shadow_runs の token/cost 列を追加する体裁の汎用リストが存在しないため、本 PR では追加しない（カードの「単純リストでなければ skip して報告」に該当）。

## 9. cost-summary エンドポイント

`backend/app/routers/tcg_analysis_dashboard.py:450-540`（改修前の行番号）`GET /tcg/analysis-dashboard/cost-summary`。`daily`/`by_supplier`/`total` の3クエリが `extraction_attempts.input_tokens`（無ければ `input_bytes/3` 推定）を読んでいた。フロントエンド呼び出し元は grep 0件（未結線）。本 PR で `public.llm_usage_events` を `extraction_attempt_id` で LEFT JOIN する方式に置換し、`input_bytes/3` 推定を廃止した。
