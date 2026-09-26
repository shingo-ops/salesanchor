-- PMG import progress: additive only; no legacy backfill.
-- Apply to every provisioned TCG schema. Re-run after provisioning a new TCG schema.
DO $$
DECLARE s RECORD;
BEGIN
    FOR s IN SELECT nspname FROM pg_namespace
             WHERE nspname ~ '^tenant_[0-9]{3}$' ORDER BY nspname
    LOOP
        IF to_regclass(format('%I.import_jobs', s.nspname)) IS NULL
           OR to_regclass(format('%I.source_messages', s.nspname)) IS NULL THEN
            CONTINUE;
        END IF;
        EXECUTE format('ALTER TABLE %I.import_jobs ADD COLUMN IF NOT EXISTS messages_linked_at TIMESTAMPTZ', s.nspname);
        EXECUTE format('ALTER TABLE %I.source_messages ADD COLUMN IF NOT EXISTS line_posted_at TIMESTAMPTZ', s.nspname);
        EXECUTE format($q$
            CREATE UNIQUE INDEX IF NOT EXISTS uq_source_messages_line_identity
            ON %I.source_messages (supplier_channel_id, line_posted_at, raw_sha256)
            WHERE line_posted_at IS NOT NULL
        $q$, s.nspname);
        EXECUTE format($q$
            CREATE TABLE IF NOT EXISTS %I.import_job_messages (
                import_job_id UUID NOT NULL REFERENCES %I.import_jobs(id),
                source_message_id UUID NOT NULL REFERENCES %I.source_messages(id),
                relation_kind TEXT NOT NULL CHECK (relation_kind IN ('created', 'reused')),
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                PRIMARY KEY (import_job_id, source_message_id)
            )
        $q$, s.nspname, s.nspname, s.nspname);
        EXECUTE format($q$
            CREATE INDEX IF NOT EXISTS ix_import_job_messages_source
            ON %I.import_job_messages(source_message_id, import_job_id)
        $q$, s.nspname);
    END LOOP;
END $$;
