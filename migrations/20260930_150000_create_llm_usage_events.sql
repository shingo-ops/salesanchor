-- Migration: LLM 使用量台帳（public.llm_usage_events）新設（A1: 表のみ）
-- 目的: Gemini を呼ぶたびに1行、量の種類ごと・使いみちごとに記録し、どこで何に
--       使ったかを1か所（SSOT）で集計できるようにする（PO「使用量は最大限細分化」指示）。
-- design: docs/handoff/llm-usage-ledger/design.md §3・§9（2段階の出し方）
-- ADR:    docs/adr/ADR-1004-llm-usage-ledger.md
-- 冪等: CREATE TABLE IF NOT EXISTS / CREATE INDEX IF NOT EXISTS。
-- DROP なし: extraction_attempts.input_tokens/output_tokens/cost_usd,
--            extraction_shadow_runs の同3列は本PRでは残置する（列の削除は別途PO本人のGOが必要）。
-- extraction_shadow_run_id に FK を張らない理由: CI の migration-test-run 差分実行ベースライン
--   （.github/workflows/migration-test.yml）に public.extraction_shadow_runs が登録されておらず、
--   REFERENCES で参照すると CI のみで失敗する。試運転（extraction_shadow_runs 書き込み）自体が
--   現在停止中（#3864）のため実害はない。列とインデックスは維持する。
--
-- 2段階の出し方（design.md §9）: 本ファイルは A1（表のみ、先行デプロイ）。
--   過去分バックフィル（INSERT ... SELECT FROM public.extraction_attempts）は
--   migrations/20260930_160000_backfill_llm_usage_events.sql（A2）に分離した。
--   理由: .github/workflows/deploy.yml はバックエンドのコード切替・celery再起動
--   （~:323, ~:337-342）を「Run database migrations」（~:448-462）より先に実行する。
--   CREATE と アプリコードの usage 書き込みロジックと バックフィル SELECT を
--   同一 migration・同一デプロイで出すと、コード切替後～migration 実行までの間、
--   本番の抽出処理が「テーブルが無い」または「列が無い」エラーで失敗する窓ができる。
--   A1（表のみ、コード変更なし）を先にマージ・本番反映してから、A2（バックフィル＋
--   アプリの書き込みコード）を出すことでこの窓を無くす。

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
