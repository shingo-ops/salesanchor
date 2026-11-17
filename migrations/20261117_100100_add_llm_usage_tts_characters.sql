-- ADR-1080: 使用量の台帳に読み上げの字数の列を足し、使いみち secretary_tts と sdk google-tts-rest を許す（冪等）
ALTER TABLE public.llm_usage_events ADD COLUMN IF NOT EXISTS billed_characters INTEGER;

COMMENT ON COLUMN public.llm_usage_events.billed_characters IS '料金に数える字数。読み上げ（secretary_tts）の行だけ。ほかは NULL';

-- 使いみちの値の決まり: 定義に secretary_tts が無いときだけ作り直す（後の移行が足した値を消さないため）
DO $$
DECLARE
    purpose_def TEXT;
BEGIN
    SELECT pg_get_constraintdef(con.oid) INTO purpose_def
    FROM pg_constraint con
    WHERE con.conrelid = 'public.llm_usage_events'::regclass
      AND con.conname = 'llm_usage_events_purpose_check';

    IF purpose_def IS NULL OR purpose_def NOT LIKE '%secretary_tts%' THEN
        ALTER TABLE public.llm_usage_events DROP CONSTRAINT IF EXISTS llm_usage_events_purpose_check;
        ALTER TABLE public.llm_usage_events
            ADD CONSTRAINT llm_usage_events_purpose_check
            CHECK (purpose IN ('line_extraction', 'line_extraction_shadow', 'inventory_parse_fallback', 'translation_inbound', 'translation_inbound_escalation', 'translation_outbound', 'secretary_intent', 'secretary_regression', 'secretary_tts'));
    END IF;
END $$;

-- sdk の値の決まり: 定義に google-tts-rest が無いときだけ作り直す
DO $$
DECLARE
    sdk_def TEXT;
BEGIN
    SELECT pg_get_constraintdef(con.oid) INTO sdk_def
    FROM pg_constraint con
    WHERE con.conrelid = 'public.llm_usage_events'::regclass
      AND con.conname = 'llm_usage_events_sdk_check';

    IF sdk_def IS NULL OR sdk_def NOT LIKE '%google-tts-rest%' THEN
        ALTER TABLE public.llm_usage_events DROP CONSTRAINT IF EXISTS llm_usage_events_sdk_check;
        ALTER TABLE public.llm_usage_events
            ADD CONSTRAINT llm_usage_events_sdk_check
            CHECK (sdk IN ('google-genai', 'google-generativeai', 'codex-cli', 'claude-code', 'google-tts-rest'));
    END IF;
END $$;
