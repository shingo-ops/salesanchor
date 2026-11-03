-- ADR-1058 段1a: AI の担当の表3つ（選択肢・今の担当・変えた記録）と、使用の記録 llm_usage_events の列 outcome・error_code を足す。
-- 追加と CHECK を広げるだけ。既存の行は変わらない。コードはこの便では変えない（設計 docs/handoff/secretary-chatgpt/design.md §4-1・§4-2-1）。
-- 流し直しても壊れない理由（run_all_migrations.sh は毎回全 migration を先頭から流す）:
--   表・索引・列は IF NOT EXISTS。名前付きの制約は表を作る文の中か、pg_constraint に名前が無い時だけ足す DO の塊で作る。
--   関数とトリガーは CREATE OR REPLACE。初めの行は ON CONFLICT DO NOTHING なので、画面で変えた担当を上書きしない。
--   llm_usage_events の purpose と sdk の CHECK は、現在の定義に目的の値が入っていれば何もしない（後の migration が値を足していても消さない）。
--
-- 戻し方（downgrade。流すのは PO。secretary_intent・codex-cli・claude-code の行が llm_usage_events に残っていると最後の ADD が止まるので、先にその行を片付ける）:
--   DROP TRIGGER IF EXISTS ai_job_assignment_history_no_change ON public.ai_job_assignment_history;
--   DROP TRIGGER IF EXISTS ai_job_assignment_history_no_truncate ON public.ai_job_assignment_history;
--   DROP FUNCTION IF EXISTS public.ai_job_assignment_history_guard();
--   DROP TABLE IF EXISTS public.ai_job_assignment_history;
--   DROP TABLE IF EXISTS public.ai_job_assignments;
--   DROP TABLE IF EXISTS public.ai_job_choices;
--   ALTER TABLE public.llm_usage_events DROP CONSTRAINT IF EXISTS llm_usage_events_outcome_error_code_check;
--   ALTER TABLE public.llm_usage_events DROP COLUMN IF EXISTS error_code;
--   ALTER TABLE public.llm_usage_events DROP COLUMN IF EXISTS outcome;
--   ALTER TABLE public.llm_usage_events DROP CONSTRAINT IF EXISTS llm_usage_events_purpose_check;
--   ALTER TABLE public.llm_usage_events ADD CONSTRAINT llm_usage_events_purpose_check
--     CHECK (purpose IN ('line_extraction', 'line_extraction_shadow', 'inventory_parse_fallback', 'translation_inbound', 'translation_inbound_escalation', 'translation_outbound'));
--   ALTER TABLE public.llm_usage_events DROP CONSTRAINT IF EXISTS llm_usage_events_sdk_check;
--   ALTER TABLE public.llm_usage_events ADD CONSTRAINT llm_usage_events_sdk_check
--     CHECK (sdk IN ('google-genai', 'google-generativeai'));

-- 1-1 選択肢（仕事ごとに選べる AI とモデルの組）
CREATE TABLE IF NOT EXISTS public.ai_job_choices (
    id SERIAL PRIMARY KEY,
    job_key TEXT NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ai_job_choices_job_key_check CHECK (job_key IN ('line_extraction', 'translation_inbound', 'translation_inbound_escalation', 'translation_outbound', 'secretary_intent')),
    CONSTRAINT ai_job_choices_provider_check CHECK (provider IN ('gemini', 'codex', 'claude')),
    CONSTRAINT ai_job_choices_job_provider_model_key UNIQUE (job_key, provider, model),
    CONSTRAINT ai_job_choices_id_job_key_key UNIQUE (id, job_key)
);

-- 1-2 今の担当（仕事ごとに1行。選べるのは同じ仕事の選択肢だけ）
CREATE TABLE IF NOT EXISTS public.ai_job_assignments (
    job_key TEXT PRIMARY KEY,
    choice_id INTEGER NOT NULL,
    updated_by INTEGER NULL REFERENCES public.users(id) ON DELETE SET NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ai_job_assignments_job_key_check CHECK (job_key IN ('line_extraction', 'translation_inbound', 'translation_inbound_escalation', 'translation_outbound', 'secretary_intent')),
    CONSTRAINT ai_job_assignments_choice_fkey FOREIGN KEY (choice_id, job_key) REFERENCES public.ai_job_choices (id, job_key)
);

-- 1-3 変えた記録（足すだけ）
CREATE TABLE IF NOT EXISTS public.ai_job_assignment_history (
    id SERIAL PRIMARY KEY,
    job_key TEXT NOT NULL,
    old_choice_id INTEGER NOT NULL REFERENCES public.ai_job_choices(id),
    new_choice_id INTEGER NOT NULL REFERENCES public.ai_job_choices(id),
    changed_by INTEGER NULL REFERENCES public.users(id) ON DELETE SET NULL,
    changed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ai_job_assignment_history_job_key_check CHECK (job_key IN ('line_extraction', 'translation_inbound', 'translation_inbound_escalation', 'translation_outbound', 'secretary_intent'))
);
CREATE INDEX IF NOT EXISTS ix_ai_job_assignment_history_job_key_changed_at
    ON public.ai_job_assignment_history (job_key, changed_at);

-- 1-4 履歴の書き換え・消しを止める（users を消した時の changed_by の SET NULL だけ通す）
CREATE OR REPLACE FUNCTION public.ai_job_assignment_history_guard() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'UPDATE'
       AND NEW.changed_by IS NULL
       AND OLD.changed_by IS NOT NULL
       AND NEW.id IS NOT DISTINCT FROM OLD.id
       AND NEW.job_key IS NOT DISTINCT FROM OLD.job_key
       AND NEW.old_choice_id IS NOT DISTINCT FROM OLD.old_choice_id
       AND NEW.new_choice_id IS NOT DISTINCT FROM OLD.new_choice_id
       AND NEW.changed_at IS NOT DISTINCT FROM OLD.changed_at THEN
        RETURN NEW;
    END IF;
    RAISE EXCEPTION 'ai_job_assignment_history is append-only';
END;
$$;

CREATE OR REPLACE TRIGGER ai_job_assignment_history_no_change
    BEFORE UPDATE OR DELETE ON public.ai_job_assignment_history
    FOR EACH ROW EXECUTE FUNCTION public.ai_job_assignment_history_guard();

CREATE OR REPLACE TRIGGER ai_job_assignment_history_no_truncate
    BEFORE TRUNCATE ON public.ai_job_assignment_history
    FOR EACH STATEMENT EXECUTE FUNCTION public.ai_job_assignment_history_guard();

-- 1-5 初めの行（流し直しで上書きしない。codex の行は段3で足す）
INSERT INTO public.ai_job_choices (job_key, provider, model) VALUES
    ('line_extraction', 'gemini', 'gemini-3.1-flash-lite'),
    ('translation_inbound', 'gemini', 'gemini-2.5-flash'),
    ('translation_inbound', 'gemini', 'gemini-2.5-pro'),
    ('translation_inbound', 'gemini', 'gemini-2.5-flash-lite'),
    ('translation_inbound', 'gemini', 'gemini-3.1-flash-lite'),
    ('translation_inbound', 'gemini', 'gemini-3.5-flash-lite'),
    ('translation_inbound_escalation', 'gemini', 'gemini-2.5-flash'),
    ('translation_inbound_escalation', 'gemini', 'gemini-2.5-pro'),
    ('translation_inbound_escalation', 'gemini', 'gemini-2.5-flash-lite'),
    ('translation_inbound_escalation', 'gemini', 'gemini-3.1-flash-lite'),
    ('translation_inbound_escalation', 'gemini', 'gemini-3.5-flash-lite'),
    ('translation_outbound', 'gemini', 'gemini-2.5-flash'),
    ('translation_outbound', 'gemini', 'gemini-2.5-pro'),
    ('translation_outbound', 'gemini', 'gemini-2.5-flash-lite'),
    ('translation_outbound', 'gemini', 'gemini-3.1-flash-lite'),
    ('translation_outbound', 'gemini', 'gemini-3.5-flash-lite'),
    ('secretary_intent', 'claude', 'sonnet')
ON CONFLICT DO NOTHING;

INSERT INTO public.ai_job_assignments (job_key, choice_id, updated_by) VALUES
    ('line_extraction',
     (SELECT id FROM public.ai_job_choices WHERE job_key = 'line_extraction' AND provider = 'gemini' AND model = 'gemini-3.1-flash-lite'),
     NULL),
    ('translation_inbound',
     (SELECT id FROM public.ai_job_choices WHERE job_key = 'translation_inbound' AND provider = 'gemini' AND model = 'gemini-3.5-flash-lite'),
     NULL),
    ('translation_inbound_escalation',
     (SELECT id FROM public.ai_job_choices WHERE job_key = 'translation_inbound_escalation' AND provider = 'gemini' AND model = 'gemini-3.5-flash-lite'),
     NULL),
    ('translation_outbound',
     (SELECT id FROM public.ai_job_choices WHERE job_key = 'translation_outbound' AND provider = 'gemini' AND model = 'gemini-3.5-flash-lite'),
     NULL),
    ('secretary_intent',
     (SELECT id FROM public.ai_job_choices WHERE job_key = 'secretary_intent' AND provider = 'claude' AND model = 'sonnet'),
     NULL)
ON CONFLICT (job_key) DO NOTHING;

-- 1-6 使用の記録の列（既存の行は outcome='ok'・error_code NULL になり、2列の決まりを満たす）
ALTER TABLE public.llm_usage_events
    ADD COLUMN IF NOT EXISTS outcome TEXT NOT NULL DEFAULT 'ok'
    CONSTRAINT llm_usage_events_outcome_check CHECK (outcome IN ('ok', 'failed'));

ALTER TABLE public.llm_usage_events
    ADD COLUMN IF NOT EXISTS error_code TEXT NULL
    CONSTRAINT llm_usage_events_error_code_check CHECK (error_code IS NULL OR error_code IN ('auth_failed', 'timeout', 'rate_limited', 'http_error', 'unreadable', 'tool_used', 'not_ready', 'busy', 'other'));

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'public.llm_usage_events'::regclass
          AND conname = 'llm_usage_events_outcome_error_code_check'
    ) THEN
        ALTER TABLE public.llm_usage_events
            ADD CONSTRAINT llm_usage_events_outcome_error_code_check
            CHECK ((outcome = 'ok' AND error_code IS NULL) OR (outcome = 'failed' AND error_code IS NOT NULL));
    END IF;
END $$;

-- 1-7 今ある CHECK を広げる（目的の値が定義に入っていれば何もしない。DROP と ADD は1つの DO の中）
DO $$
DECLARE
    purpose_def TEXT;
    sdk_def TEXT;
BEGIN
    SELECT pg_get_constraintdef(con.oid) INTO purpose_def
    FROM pg_constraint con
    WHERE con.conrelid = 'public.llm_usage_events'::regclass
      AND con.conname = 'llm_usage_events_purpose_check';

    IF purpose_def IS NULL OR purpose_def NOT LIKE '%secretary_intent%' THEN
        ALTER TABLE public.llm_usage_events DROP CONSTRAINT IF EXISTS llm_usage_events_purpose_check;
        ALTER TABLE public.llm_usage_events
            ADD CONSTRAINT llm_usage_events_purpose_check
            CHECK (purpose IN ('line_extraction', 'line_extraction_shadow', 'inventory_parse_fallback', 'translation_inbound', 'translation_inbound_escalation', 'translation_outbound', 'secretary_intent'));
    END IF;

    SELECT pg_get_constraintdef(con.oid) INTO sdk_def
    FROM pg_constraint con
    WHERE con.conrelid = 'public.llm_usage_events'::regclass
      AND con.conname = 'llm_usage_events_sdk_check';

    IF sdk_def IS NULL OR sdk_def NOT LIKE '%codex-cli%' OR sdk_def NOT LIKE '%claude-code%' THEN
        ALTER TABLE public.llm_usage_events DROP CONSTRAINT IF EXISTS llm_usage_events_sdk_check;
        ALTER TABLE public.llm_usage_events
            ADD CONSTRAINT llm_usage_events_sdk_check
            CHECK (sdk IN ('google-genai', 'google-generativeai', 'codex-cli', 'claude-code'));
    END IF;
END $$;

-- 1-8 権限（salesanchor_app がある時だけ）
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'salesanchor_app') THEN
        GRANT SELECT, INSERT, UPDATE, DELETE ON public.ai_job_choices, public.ai_job_assignments, public.ai_job_assignment_history TO salesanchor_app;
        GRANT USAGE, SELECT ON SEQUENCE public.ai_job_choices_id_seq, public.ai_job_assignment_history_id_seq TO salesanchor_app;
    END IF;
END $$;
