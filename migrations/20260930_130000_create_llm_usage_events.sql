-- Migration: LLM 使用量台帳（public.llm_usage_events）新設 + 過去分バックフィル
-- 目的: Gemini を呼ぶたびに1行、量の種類ごと・使いみちごとに記録し、どこで何に
--       使ったかを1か所（SSOT）で集計できるようにする（PO「使用量は最大限細分化」指示）。
-- design: docs/handoff/llm-usage-ledger/design.md §3
-- ADR:    docs/adr/ADR-1004-llm-usage-ledger.md
-- 冪等: CREATE TABLE IF NOT EXISTS / CREATE INDEX IF NOT EXISTS。
--       バックフィルは INSERT ... SELECT ... WHERE NOT EXISTS で重複防止。
-- DROP なし: extraction_attempts.input_tokens/output_tokens/cost_usd,
--            extraction_shadow_runs の同3列は本PRでは残置する（列の削除は別途PO本人のGOが必要）。
-- extraction_shadow_run_id に FK を張らない理由: CI の migration-test-run 差分実行ベースライン
--   （.github/workflows/migration-test.yml）に public.extraction_shadow_runs が登録されておらず、
--   REFERENCES で参照すると CI のみで失敗する。試運転（extraction_shadow_runs 書き込み）自体が
--   現在停止中（#3864）のため実害はない。列とインデックスは維持する。

-- 1. public.llm_usage_events: 1行 = Gemini の応答1回
CREATE TABLE IF NOT EXISTS public.llm_usage_events (
    id                          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    occurred_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),
    purpose                     TEXT        NOT NULL,
    tenant_id                   INTEGER,
    model                       TEXT        NOT NULL,
    sdk                         TEXT        NOT NULL,
    prompt_tokens                INTEGER,
    cached_content_tokens        INTEGER,
    candidates_tokens            INTEGER,
    thoughts_tokens               INTEGER,
    tool_use_prompt_tokens        INTEGER,
    total_tokens                  INTEGER,
    cost_usd                    NUMERIC(12, 6),
    extraction_attempt_id       UUID        REFERENCES public.extraction_attempts(id) ON DELETE SET NULL,
    -- FK なし：CI の差分実行ベースラインに extraction_shadow_runs が無いため。試運転は停止中（#3864）
    extraction_shadow_run_id    UUID,
    discord_inbound_message_id  INTEGER,
    source_ref                  TEXT,
    backfilled                  BOOLEAN     NOT NULL DEFAULT false,
    CONSTRAINT llm_usage_events_purpose_check
        CHECK (purpose IN (
            'line_extraction', 'line_extraction_shadow', 'inventory_parse_fallback',
            'translation_inbound', 'translation_inbound_escalation', 'translation_outbound'
        )),
    CONSTRAINT llm_usage_events_sdk_check
        CHECK (sdk IN ('google-genai', 'google-generativeai'))
);

CREATE INDEX IF NOT EXISTS ix_llm_usage_events_occurred_at
    ON public.llm_usage_events (occurred_at);
CREATE INDEX IF NOT EXISTS ix_llm_usage_events_purpose_occurred_at
    ON public.llm_usage_events (purpose, occurred_at);
CREATE INDEX IF NOT EXISTS ix_llm_usage_events_extraction_attempt_id
    ON public.llm_usage_events (extraction_attempt_id);
CREATE INDEX IF NOT EXISTS ix_llm_usage_events_extraction_shadow_run_id
    ON public.llm_usage_events (extraction_shadow_run_id);

-- 2. 過去分バックフィル（extraction_attempts → llm_usage_events, purpose='line_extraction'）
--    条件: input_tokens IS NOT NULL OR output_tokens IS NOT NULL OR cost_usd IS NOT NULL
--    冪等: extraction_attempt_id で重複防止（WHERE NOT EXISTS）。
INSERT INTO public.llm_usage_events
    (purpose, tenant_id, model, sdk, prompt_tokens, candidates_tokens, cost_usd,
     extraction_attempt_id, occurred_at, backfilled)
SELECT
    'line_extraction',
    NULL,
    ea.requested_model,
    'google-genai',
    ea.input_tokens,
    ea.output_tokens,
    ea.cost_usd,
    ea.id,
    COALESCE(ea.response_received_at, ea.finished_at, ea.started_at),
    true
FROM public.extraction_attempts ea
WHERE (ea.input_tokens IS NOT NULL OR ea.output_tokens IS NOT NULL OR ea.cost_usd IS NOT NULL)
  AND NOT EXISTS (
      SELECT 1 FROM public.llm_usage_events e WHERE e.extraction_attempt_id = ea.id
  );
