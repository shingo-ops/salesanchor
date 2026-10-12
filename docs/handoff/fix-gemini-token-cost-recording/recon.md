# recon: Gemini トークン・費用の記録修正

計測時 origin/main SHA: `4c056c5f9c80b481643e0150f29fd3c95ea86e1e`

## §A 事実（設計担当が確かめたもの）

- 本番の celery-worker に入っている google-genai 2.8.0 の
  `types.GenerateContentResponseUsageMetadata.model_fields` の中身：
  cache_tokens_details、cached_content_token_count、**candidates_token_count**、
  candidates_tokens_details、**prompt_token_count**、prompt_tokens_details、
  **thoughts_token_count**、tool_use_prompt_token_count、
  tool_use_prompt_tokens_details、total_token_count、traffic_type。
  - `response_token_count` はない。
  - 設計担当が 2026-09-30 に本番のコンテナで `python -c` を実行して確かめた。

- 出力トークンの読み方が間違っている箇所（origin/main）：
  - `backend/app/services/gemini_extraction_svc.py:450`（`call_gemini_extraction` 内）
    ```
    input_tokens = int(getattr(usage, "prompt_token_count", 0) or 0)
    output_tokens = int(getattr(usage, "response_token_count", 0) or 0)
    ```
  - `backend/app/services/gemini_extraction_svc.py:529`（`call_gemini_raw_copy` 内）
    ```
    input_tokens = int(getattr(usage, "prompt_token_count", 0) or 0)
    output_tokens = int(getattr(usage, "response_token_count", 0) or 0)
    ```
  - `backend/app/services/inventory_parser_llm.py:317-318`
    ```
    input_tokens = int(getattr(usage, "prompt_token_count", 0) or 0)
    output_tokens = int(getattr(usage, "response_token_count", 0) or 0)
    ```
  - `backend/app/services/message_translator.py:425-426` は正しい：
    ```
    input_tokens = int(getattr(usage, "prompt_token_count", 0) or 0)
    output_tokens = int(getattr(usage, "candidates_token_count", 0) or 0)
    ```

- 本番DB：2026-09-29 以降の extraction_attempts 171件のうち、
  input_tokens が入っているのは 97件、**output_tokens が入っているのは 0件**、
  cost_usd が入っているのは 97件。

- 試運転の記録：
  - `backend/app/services/extraction_shadow_svc.py:97-136` の `insert_shadow_run` は、
    `input_tokens`・`output_tokens`・`cost_usd` を引数に取らず、INSERT 文
    （100-113行目）にもこれらの列が含まれていない。
  - `run_shadow_for_job`（288-366行目）は `call_gemini_raw_copy` の戻り値
    （`raw_copy = call_gemini_raw_copy(...)`, 297行目）のうち `response_text`
    （303行目）しか使っていない。`raw_copy["input_tokens"]` / `raw_copy["output_tokens"]`
    は捨てられている。
  - `insert_shadow_run` の INSERT 文（103-114行目）は `finished_at` に `now()` を
    渡しているのみで、`started_at` を渡していない（テーブル側の
    `DEFAULT now()` が使われる）。同一トランザクション内で
    `call_gemini_raw_copy` 実行後に INSERT するため、started_at（テーブル既定値）
    と finished_at が同じ `now()` 評価タイミングに実質一致する。
  - `migrations/20260928_110000_create_extraction_shadow_tables.sql:23-30` に
    `input_tokens INTEGER`・`output_tokens INTEGER`・`cost_usd NUMERIC(10,6)`・
    `started_at TIMESTAMPTZ NOT NULL DEFAULT now()`・`finished_at TIMESTAMPTZ`
    の列が既に存在する（マイグレーション追加不要）。
  - 本番の extraction_shadow_runs 23件すべてで input_tokens/output_tokens/cost_usd
    が NULL、started_at と finished_at が同じ値（設計担当の実測、本カードの
    §A に記載）。

- 費用計算：`backend/app/services/llm_budget.py:130-144` の
  `calculate_cost(input_tokens, output_tokens, model=DEFAULT_MODEL)` が
  `LLM_PRICING` に無いモデルで `ValueError(f"unknown LLM model for pricing: {model!r}")`
  を投げる（140-141行目）。
  `backend/app/services/tcg_extraction_record_svc.py:172-179`（`complete`）で
  この関数を使い、`ValueError` を捕捉して `cost = None` にしている：
  ```python
  cost: float | None = None
  if self._requested_model and (self._input_tokens > 0 or self._output_tokens > 0):
      try:
          cost = float(calculate_cost(self._input_tokens, self._output_tokens, model=self._requested_model))
      except ValueError:
          cost = None
  ```
  同ファイル 189-200行目付近の `fail()` でも同じパターン（入力分のみ、出力0扱い）。

## テスト側の現状

- `backend/tests/test_inventory_parser_llm.py:58-60`（`_make_fake_response`）で
  `usage.response_token_count = candidates_tokens` としてモックしている。
  実際の SDK 属性名と食い違っているため、修正後はこのモックも直す必要がある。
- `backend/tests/test_tcg_gemini_extraction.py` には `call_gemini_extraction` /
  `call_gemini_raw_copy` の usage_metadata 読み取り自体を検証するテストがない
  （`usage_metadata = None` に設定して迂回しているケースのみ）。
- `backend/tests/test_extraction_shadow_svc.py` の `_patch_common`（24-31行目）は
  `call_gemini_raw_copy` の戻り値を
  `{"response_text": ..., "input_tokens": 1, "output_tokens": 1}` にモックしているが、
  `insert_shadow_run` 呼び出しに tokens/cost/started_at が渡ることを検証する
  アサーションは無い。
