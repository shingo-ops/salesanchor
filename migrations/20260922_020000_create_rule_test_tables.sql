-- Rule Test System: テストケース管理 + テスト実行記録
-- tcg_status_master (SSOT) のルール検証用

CREATE TABLE IF NOT EXISTS public.rule_test_cases (
    id              SERIAL PRIMARY KEY,
    input_text      TEXT NOT NULL,
    expected_canonical TEXT NOT NULL,  -- e.g. "Sold out", "Pre-order", "In Stock"
    expected_effect TEXT,              -- 'excluded' or NULL
    note            TEXT NOT NULL DEFAULT '',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.rule_test_runs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    state           TEXT NOT NULL DEFAULT 'pending',  -- pending, running, passed, failed, error
    started_by      TEXT NOT NULL DEFAULT '',
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at    TIMESTAMPTZ,
    error_message   TEXT,
    total_cases     INTEGER NOT NULL DEFAULT 0,
    passed_cases    INTEGER NOT NULL DEFAULT 0,
    failed_cases    INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS public.rule_test_run_results (
    id              SERIAL PRIMARY KEY,
    run_id          UUID NOT NULL REFERENCES public.rule_test_runs(id) ON DELETE CASCADE,
    case_id         INTEGER NOT NULL REFERENCES public.rule_test_cases(id) ON DELETE CASCADE,
    input_text      TEXT NOT NULL,
    expected_canonical TEXT NOT NULL,
    expected_effect TEXT,
    actual_canonical TEXT,
    actual_effect   TEXT,
    is_match        BOOLEAN NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_rule_test_run_results_run_id ON public.rule_test_run_results(run_id);
CREATE INDEX IF NOT EXISTS idx_rule_test_runs_state ON public.rule_test_runs(state);
