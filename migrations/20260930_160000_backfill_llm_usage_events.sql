-- Migration: LLM 使用量台帳（public.llm_usage_events）過去分バックフィル（A2）
-- 前提: migrations/20260930_150000_create_llm_usage_events.sql（A1）が本番に適用済みであること。
--       A1・A2 の分離理由は design.md §9「出し方（2段階）」を参照。
--       （.github/workflows/deploy.yml がバックエンドのコード切替・celery再起動を
--        「Run database migrations」より先に実行するため、表の作成とアプリの書き込み
--        コード・バックフィルは別デプロイに分けている。）
-- 冪等: extraction_attempt_id で重複防止の INSERT ... SELECT ... WHERE NOT EXISTS。

-- 過去分バックフィル（extraction_attempts → llm_usage_events, purpose='line_extraction'）
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
