-- Migration: create_tcg_analysis_history_t004
-- HIST-01: analysis_runs / analysis_run_snapshots — 再解析履歴テーブル（tenant_004 専用・additive only）
--
-- 設計判断:
--   - 新規テーブル2本のみ。ALTER / DROP なし。
--   - analysis_run_snapshots.analysis_result_id は UUID 参照（非FK）—
--     スナップショットは歴史記録であり、元行削除後も保持する設計
--   - 冪等: CREATE TABLE IF NOT EXISTS / CREATE INDEX IF NOT EXISTS
--
-- 作成日: 2026-09-03

DO $$
DECLARE
    _schema TEXT := 'tenant_004';
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = _schema) THEN
        RAISE NOTICE 'migration 20260903_190000: schema % does not exist, skipping', _schema;
        RETURN;
    END IF;

    RAISE NOTICE 'migration 20260903_190000: creating analysis history tables in schema %', _schema;

    -- ----------------------------------------------------------------
    -- 1. analysis_runs: 再解析ラン単位のメタデータ
    -- ----------------------------------------------------------------
    EXECUTE format($q$
        CREATE TABLE IF NOT EXISTS %I.analysis_runs (
            id                UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
            extraction_job_id UUID         NOT NULL
                                               REFERENCES %I.extraction_jobs (id) ON DELETE CASCADE,
            run_type          VARCHAR(50)  NOT NULL,
            triggered_by      VARCHAR(100),
            engine_version    VARCHAR(50)  NOT NULL,
            started_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            completed_at      TIMESTAMPTZ,
            total             INTEGER,
            pid_resolved      INTEGER,
            unit_resolved     INTEGER,
            needs_review      INTEGER,
            multi_count       INTEGER,
            none_count        INTEGER
        )
    $q$, _schema, _schema);

    EXECUTE format($q$
        CREATE INDEX IF NOT EXISTS ix_analysis_runs_extraction_job_id
            ON %I.analysis_runs (extraction_job_id)
    $q$, _schema);

    -- ----------------------------------------------------------------
    -- 2. analysis_run_snapshots: 再解析前の analysis_results スナップショット
    --    analysis_result_id は UUID 参照のみ（非FK）
    -- ----------------------------------------------------------------
    EXECUTE format($q$
        CREATE TABLE IF NOT EXISTS %I.analysis_run_snapshots (
            id                    UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
            run_id                UUID          NOT NULL
                                                    REFERENCES %I.analysis_runs (id) ON DELETE CASCADE,
            analysis_result_id    UUID          NOT NULL,
            extraction_item_id    UUID          NOT NULL,
            product_id            UUID,
            pid_resolved          BOOLEAN       NOT NULL,
            pid_basis             VARCHAR(100),
            unit_id               UUID,
            unit_canonical        VARCHAR(50),
            unit_resolved         BOOLEAN       NOT NULL,
            condition_id          UUID,
            condition_canonical   VARCHAR(100),
            condition_basis       VARCHAR(100),
            quantity_normalized   NUMERIC(14,2),
            price_normalized      NUMERIC(14,2),
            note_ja               TEXT,
            status                VARCHAR(50),
            exclusion             TEXT,
            needs_review          BOOLEAN       NOT NULL,
            review_reasons        TEXT,
            engine_version        VARCHAR(50)   NOT NULL,
            computed_at           TIMESTAMPTZ   NOT NULL,
            updated_at            TIMESTAMPTZ   NOT NULL,
            snapshotted_at        TIMESTAMPTZ   NOT NULL DEFAULT NOW()
        )
    $q$, _schema, _schema);

    EXECUTE format($q$
        CREATE INDEX IF NOT EXISTS ix_analysis_run_snapshots_run_id
            ON %I.analysis_run_snapshots (run_id)
    $q$, _schema);

    RAISE NOTICE 'migration 20260903_190000: 完了。analysis_runs / analysis_run_snapshots を schema % に作成', _schema;
END $$;
