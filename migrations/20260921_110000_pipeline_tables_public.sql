-- Migration: 20260921_010000_pipeline_tables_public.sql
-- Purpose: Create pipeline tables in public schema (tenant_004 → public Step 1)
-- Pattern: DDL-only — no INSERT / UPDATE / DELETE
-- Ref: SSOT migration pattern from 20260919_020000_master_ssot_public_tables.sql

-- ============================================================
-- Category C: source / channel tables (no upstream FK deps)
-- ============================================================

-- C-1: supplier_channels
CREATE TABLE IF NOT EXISTS public.supplier_channels (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    channel     VARCHAR(50) NOT NULL,
    external_id TEXT,
    is_active   BOOLEAN     NOT NULL,
    supplier_id INTEGER     NOT NULL REFERENCES public.suppliers(id)
);

-- C-2: source_messages (FK → supplier_channels)
CREATE TABLE IF NOT EXISTS public.source_messages (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    supplier_channel_id UUID        REFERENCES public.supplier_channels(id) ON DELETE SET NULL,
    raw_text            TEXT        NOT NULL,
    raw_sha256          VARCHAR(64) NOT NULL,
    received_at         TIMESTAMPTZ,
    superseded_by       UUID        REFERENCES public.source_messages(id),
    is_active           BOOLEAN     NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    line_posted_at      TIMESTAMPTZ
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_pub_source_messages_line_identity
    ON public.source_messages (supplier_channel_id, line_posted_at, raw_sha256)
    WHERE line_posted_at IS NOT NULL;

-- ============================================================
-- Category B: import tables
-- ============================================================

-- B-1: import_jobs (no FK deps on other migrating tables)
CREATE TABLE IF NOT EXISTS public.import_jobs (
    id                 UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    filename           TEXT        NOT NULL,
    raw_sha256         VARCHAR(64) NOT NULL,
    message_count      INTEGER     NOT NULL DEFAULT 0,
    provider_count     INTEGER     NOT NULL DEFAULT 0,
    unresolved_count   INTEGER     NOT NULL DEFAULT 0,
    uploaded_by        TEXT,
    status             VARCHAR(30) NOT NULL DEFAULT 'ok',
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    pending_messages   JSONB,
    window_start       TIMESTAMPTZ,
    window_end         TIMESTAMPTZ,
    unresolved_names   JSONB,
    review_status      TEXT        NOT NULL DEFAULT 'ok',
    messages_linked_at TIMESTAMPTZ
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_pub_import_jobs_raw_sha256
    ON public.import_jobs (raw_sha256);
CREATE INDEX IF NOT EXISTS ix_pub_import_jobs_review_status
    ON public.import_jobs (review_status) WHERE review_status = 'pending_review';

-- B-2: import_job_messages (FK → import_jobs, source_messages)
CREATE TABLE IF NOT EXISTS public.import_job_messages (
    import_job_id     UUID        NOT NULL REFERENCES public.import_jobs(id),
    source_message_id UUID        NOT NULL REFERENCES public.source_messages(id),
    relation_kind     TEXT        NOT NULL,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (import_job_id, source_message_id),
    CONSTRAINT pub_import_job_messages_relation_kind_check
        CHECK (relation_kind IN ('created', 'reused'))
);
CREATE INDEX IF NOT EXISTS ix_pub_import_job_messages_source
    ON public.import_job_messages (source_message_id, import_job_id);

-- ============================================================
-- Category A: extraction tables
-- ============================================================

-- A-1: extraction_jobs (FK → source_messages)
CREATE TABLE IF NOT EXISTS public.extraction_jobs (
    id                      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    source_message_id       UUID        NOT NULL REFERENCES public.source_messages(id) ON DELETE CASCADE,
    status                  VARCHAR(30) NOT NULL,
    extracted_at            TIMESTAMPTZ,
    error_message           TEXT,
    prompt_version          VARCHAR(50),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    work_reference_snapshot JSONB,
    work_reference_sha256   TEXT
);

-- A-2: extraction_items (FK → extraction_jobs)
CREATE TABLE IF NOT EXISTS public.extraction_items (
    id                        UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    extraction_job_id         UUID        NOT NULL REFERENCES public.extraction_jobs(id) ON DELETE CASCADE,
    line_start                INTEGER,
    line_end                  INTEGER,
    raw_product_name          TEXT,
    raw_quantity              TEXT,
    raw_price                 TEXT,
    raw_unit                  TEXT,
    raw_state                 TEXT,
    raw_memo                  TEXT,
    created_at                TIMESTAMPTZ NOT NULL DEFAULT now(),
    raw_work_name             TEXT,
    raw_work_source_line_span TEXT,
    resolved_work_id          INTEGER,
    resolved_product_code     TEXT
);

-- A-3: extraction_attempts (FK → extraction_jobs)
CREATE TABLE IF NOT EXISTS public.extraction_attempts (
    id                   UUID        PRIMARY KEY,
    extraction_job_id    UUID        NOT NULL REFERENCES public.extraction_jobs(id) ON DELETE CASCADE,
    source_message_id    UUID        NOT NULL,
    parent_attempt_id    UUID        UNIQUE,
    started_at           TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    response_received_at TIMESTAMPTZ,
    finished_at          TIMESTAMPTZ,
    phase                TEXT        NOT NULL DEFAULT 'started',
    input_payload        JSONB,
    input_sha256         TEXT        NOT NULL,
    input_bytes          BIGINT      NOT NULL,
    requested_model      TEXT        NOT NULL,
    prompt_version       TEXT        NOT NULL,
    code_version         TEXT,
    response_text        TEXT,
    response_sha256      TEXT,
    response_bytes       BIGINT,
    parsed_items         JSONB,
    parsed_bytes         BIGINT,
    item_count           INTEGER,
    validation_result    JSONB       NOT NULL DEFAULT '{}',
    error_code           TEXT,
    CONSTRAINT pub_extraction_attempts_phase_check
        CHECK (phase IN ('started', 'received', 'completed', 'failed')),
    CONSTRAINT pub_extraction_attempts_finish_check
        CHECK ((phase IN ('completed', 'failed')) = (finished_at IS NOT NULL)),
    CONSTRAINT pub_extraction_attempts_input_size
        CHECK (input_bytes >= 0),
    CONSTRAINT pub_extraction_attempts_response_size
        CHECK (response_bytes >= 0),
    CONSTRAINT pub_extraction_attempts_parsed_size
        CHECK (parsed_bytes >= 0),
    CONSTRAINT pub_extraction_attempts_complete_check
        CHECK (
            phase != 'completed' OR (
                input_payload IS NOT NULL AND
                response_text IS NOT NULL AND
                response_received_at IS NOT NULL AND
                parsed_items IS NOT NULL AND
                item_count IS NOT NULL AND
                error_code IS NULL
            )
        )
);
CREATE INDEX IF NOT EXISTS ix_pub_extraction_attempts_job_started
    ON public.extraction_attempts (extraction_job_id, started_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS ix_pub_extraction_attempts_phase
    ON public.extraction_attempts (phase);

-- ============================================================
-- Category D: analysis tables (pipeline results)
-- ============================================================

-- D-1: analysis_runs (FK → extraction_jobs)
CREATE TABLE IF NOT EXISTS public.analysis_runs (
    id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    extraction_job_id UUID        NOT NULL REFERENCES public.extraction_jobs(id) ON DELETE CASCADE,
    run_type          VARCHAR(50) NOT NULL,
    triggered_by      VARCHAR(100),
    engine_version    VARCHAR(50) NOT NULL,
    started_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at      TIMESTAMPTZ,
    total             INTEGER,
    pid_resolved      INTEGER,
    unit_resolved     INTEGER,
    needs_review      INTEGER,
    multi_count       INTEGER,
    none_count        INTEGER
);

-- D-2: analysis_results (FK → extraction_items, public.conditions, public.units, public.products)
-- VIEW guard: 20260922_080000 が本番で先行デプロイ済みの場合 public.units/conditions は VIEW になっている。
-- PostgreSQL では VIEW を REFERENCES 先にした CREATE TABLE は不可のため、VIEW の場合は FK なしで作成する。
-- FK は将来 public.units/conditions が実テーブルに昇格したタイミングで別 migration で追加する。
DO $analysis_results_ddl$
DECLARE
    _units_is_table      BOOLEAN;
    _conditions_is_table BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND c.relname = 'units' AND c.relkind = 'r'
    ) INTO _units_is_table;

    SELECT EXISTS (
        SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND c.relname = 'conditions' AND c.relkind = 'r'
    ) INTO _conditions_is_table;

    -- テーブルが既に存在する場合は CREATE TABLE IF NOT EXISTS が no-op になるため不要
    IF EXISTS (
        SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND c.relname = 'analysis_results' AND c.relkind = 'r'
    ) THEN
        RAISE NOTICE 'D-2: public.analysis_results already exists — skip CREATE TABLE';
        RETURN;
    END IF;

    IF _units_is_table AND _conditions_is_table THEN
        -- 通常パス: units/conditions が実テーブルの場合は FK 付きで作成
        EXECUTE $sql$
            CREATE TABLE IF NOT EXISTS public.analysis_results (
                id                  UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
                extraction_item_id  UUID         NOT NULL REFERENCES public.extraction_items(id) ON DELETE CASCADE,
                pid_resolved        BOOLEAN      NOT NULL,
                pid_basis           VARCHAR(100),
                unit_canonical      VARCHAR(50),
                unit_resolved       BOOLEAN      NOT NULL,
                condition_canonical VARCHAR(100),
                condition_basis     VARCHAR(100),
                quantity_normalized NUMERIC(14,2),
                price_normalized    NUMERIC(14,2),
                note_ja             TEXT,
                status              VARCHAR(50),
                exclusion           TEXT,
                needs_review        BOOLEAN      NOT NULL,
                review_reasons      TEXT,
                engine_version      VARCHAR(50)  NOT NULL,
                computed_at         TIMESTAMPTZ  NOT NULL DEFAULT now(),
                updated_at          TIMESTAMPTZ  NOT NULL DEFAULT now(),
                unit_inferred       TEXT         NOT NULL DEFAULT '',
                unit_basis          TEXT         NOT NULL DEFAULT '',
                unit_confidence     TEXT         NOT NULL DEFAULT '',
                unit_infer_reason   TEXT         NOT NULL DEFAULT '',
                product_id          INTEGER      REFERENCES public.products(id),
                unit_id             INTEGER      REFERENCES public.units(id),
                condition_id        INTEGER      NOT NULL REFERENCES public.conditions(id),
                UNIQUE (extraction_item_id)
            )
        $sql$;
        RAISE NOTICE 'D-2: public.analysis_results created with FK constraints';
    ELSE
        -- VIEW guard パス: units または conditions が VIEW の場合は FK なしで作成
        EXECUTE $sql$
            CREATE TABLE IF NOT EXISTS public.analysis_results (
                id                  UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
                extraction_item_id  UUID         NOT NULL REFERENCES public.extraction_items(id) ON DELETE CASCADE,
                pid_resolved        BOOLEAN      NOT NULL,
                pid_basis           VARCHAR(100),
                unit_canonical      VARCHAR(50),
                unit_resolved       BOOLEAN      NOT NULL,
                condition_canonical VARCHAR(100),
                condition_basis     VARCHAR(100),
                quantity_normalized NUMERIC(14,2),
                price_normalized    NUMERIC(14,2),
                note_ja             TEXT,
                status              VARCHAR(50),
                exclusion           TEXT,
                needs_review        BOOLEAN      NOT NULL,
                review_reasons      TEXT,
                engine_version      VARCHAR(50)  NOT NULL,
                computed_at         TIMESTAMPTZ  NOT NULL DEFAULT now(),
                updated_at          TIMESTAMPTZ  NOT NULL DEFAULT now(),
                unit_inferred       TEXT         NOT NULL DEFAULT '',
                unit_basis          TEXT         NOT NULL DEFAULT '',
                unit_confidence     TEXT         NOT NULL DEFAULT '',
                unit_infer_reason   TEXT         NOT NULL DEFAULT '',
                product_id          INTEGER      REFERENCES public.products(id),
                unit_id             INTEGER,
                condition_id        INTEGER      NOT NULL,
                UNIQUE (extraction_item_id)
            )
        $sql$;
        RAISE NOTICE 'D-2: public.analysis_results created WITHOUT unit_id/condition_id FK (units_is_table=%, conditions_is_table=%)',
            _units_is_table, _conditions_is_table;
    END IF;
END $analysis_results_ddl$;

-- D-3: analysis_run_snapshots (FK → analysis_runs)
-- Note: unit_id/condition_id are UUID here (legacy snapshot format, differs from analysis_results integer)
CREATE TABLE IF NOT EXISTS public.analysis_run_snapshots (
    id                  UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id              UUID         NOT NULL REFERENCES public.analysis_runs(id) ON DELETE CASCADE,
    analysis_result_id  UUID         NOT NULL,
    extraction_item_id  UUID         NOT NULL,
    pid_resolved        BOOLEAN      NOT NULL,
    pid_basis           VARCHAR(100),
    unit_id             UUID,
    unit_canonical      VARCHAR(50),
    unit_resolved       BOOLEAN      NOT NULL,
    condition_id        UUID,
    condition_canonical VARCHAR(100),
    condition_basis     VARCHAR(100),
    quantity_normalized NUMERIC(14,2),
    price_normalized    NUMERIC(14,2),
    note_ja             TEXT,
    status              VARCHAR(50),
    exclusion           TEXT,
    needs_review        BOOLEAN      NOT NULL,
    review_reasons      TEXT,
    engine_version      VARCHAR(50)  NOT NULL,
    computed_at         TIMESTAMPTZ  NOT NULL,
    updated_at          TIMESTAMPTZ  NOT NULL,
    snapshotted_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    product_id          INTEGER
);
CREATE INDEX IF NOT EXISTS ix_pub_analysis_run_snapshots_run_id
    ON public.analysis_run_snapshots (run_id);

-- ============================================================
-- Category E: correction / normalization
-- ============================================================

-- E-1: item_corrections (no FK constraints by design)
CREATE TABLE IF NOT EXISTS public.item_corrections (
    id                 BIGSERIAL    PRIMARY KEY,
    extraction_item_id UUID         NOT NULL,
    source_message_id  UUID         NOT NULL,
    field_name         TEXT         NOT NULL,
    system_value       TEXT         NOT NULL DEFAULT '',
    human_value        TEXT         NOT NULL,
    corrected_by       TEXT         NOT NULL,
    corrected_at       TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_pub_item_corrections_extraction_item_id
    ON public.item_corrections (extraction_item_id);
CREATE INDEX IF NOT EXISTS idx_pub_item_corrections_corrected_at
    ON public.item_corrections (corrected_at DESC);

-- E-2: tcg_normalization_rules
CREATE TABLE IF NOT EXISTS public.tcg_normalization_rules (
    normalization_rule_id TEXT        PRIMARY KEY,
    field                 TEXT        NOT NULL,
    rule_type             TEXT        NOT NULL,
    from_val              TEXT        NOT NULL DEFAULT '',
    to_val                TEXT        NOT NULL DEFAULT '',
    enabled               BOOLEAN     NOT NULL DEFAULT true,
    priority              INTEGER     NOT NULL,
    note                  TEXT        NOT NULL DEFAULT '',
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- Category F: distribution / product import / audit
-- ============================================================

-- F-1: tcg_distribution_settings
CREATE TABLE IF NOT EXISTS public.tcg_distribution_settings (
    key        TEXT        PRIMARY KEY,
    value      TEXT        NOT NULL,
    note       TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- F-2: tcg_distribution_targets
CREATE TABLE IF NOT EXISTS public.tcg_distribution_targets (
    id                     UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    name                   TEXT        NOT NULL,
    spreadsheet_id         TEXT        NOT NULL,
    sheet_name             TEXT        NOT NULL,
    is_active              BOOLEAN     NOT NULL DEFAULT true,
    sa_key_secret_name     TEXT        NOT NULL DEFAULT 'TCG_SHEETS_SA_KEY_FILE',
    last_distributed_at    TIMESTAMPTZ,
    last_distributed_count INTEGER,
    last_result            TEXT,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- F-3: tcg_product_import_jobs
CREATE TABLE IF NOT EXISTS public.tcg_product_import_jobs (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    filename     TEXT        NOT NULL,
    raw_sha256   VARCHAR(64) NOT NULL,
    total_rows   INTEGER     NOT NULL DEFAULT 0,
    created_rows INTEGER     NOT NULL DEFAULT 0,
    skipped_rows INTEGER     NOT NULL DEFAULT 0,
    executed_by  TEXT,
    status       VARCHAR(30) NOT NULL DEFAULT 'ok',
    started_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ
);

-- F-4: tcg_product_import_rows (FK → tcg_product_import_jobs)
CREATE TABLE IF NOT EXISTS public.tcg_product_import_rows (
    id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id         UUID        NOT NULL REFERENCES public.tcg_product_import_jobs(id),
    row_no         INTEGER     NOT NULL,
    japanese_title TEXT        NOT NULL,
    mark           TEXT,
    result         VARCHAR(20) NOT NULL,
    product_code   VARCHAR(20),
    messages       TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- F-5: audit_log
CREATE TABLE IF NOT EXISTS public.audit_log (
    id          BIGSERIAL    PRIMARY KEY,
    table_name  VARCHAR(100) NOT NULL,
    record_id   UUID,
    action      VARCHAR(20)  NOT NULL,
    changed_by  VARCHAR(100),
    changed_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    old_values  TEXT,
    new_values  TEXT
);
CREATE INDEX IF NOT EXISTS ix_pub_audit_log_changed_at
    ON public.audit_log (changed_at);
CREATE INDEX IF NOT EXISTS ix_pub_audit_log_table_record
    ON public.audit_log (table_name, record_id);
