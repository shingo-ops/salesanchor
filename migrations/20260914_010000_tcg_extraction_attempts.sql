-- CARD09: additive private extraction attempts; no model calls or backfill.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
DO $body$
DECLARE
    target RECORD;
    present_count INTEGER;
    expected RECORD;
    actual_type TEXT;
BEGIN
    FOR target IN SELECT nspname FROM pg_namespace WHERE nspname LIKE 'tenant_%' ORDER BY nspname LOOP
        SELECT count(*) INTO present_count FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
          WHERE n.nspname=target.nspname AND c.relkind='r'
            AND c.relname IN ('source_messages','extraction_jobs','extraction_items');
        IF present_count=0 THEN CONTINUE; END IF;
        IF present_count<>3 THEN RAISE EXCEPTION 'Partial extraction schema: %',target.nspname; END IF;
        IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='jarvis') THEN
            RAISE EXCEPTION 'Extraction owner role is missing';
        END IF;
        EXECUTE format($ddl$
            CREATE TABLE IF NOT EXISTS %I.extraction_attempts (
                id UUID PRIMARY KEY,
                extraction_job_id UUID NOT NULL,
                source_message_id UUID NOT NULL,
                parent_attempt_id UUID UNIQUE,
                started_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
                response_received_at TIMESTAMPTZ,
                finished_at TIMESTAMPTZ,
                phase TEXT NOT NULL DEFAULT 'started',
                input_payload JSONB,
                input_sha256 TEXT NOT NULL,
                input_bytes BIGINT NOT NULL,
                requested_model TEXT NOT NULL,
                prompt_version TEXT NOT NULL,
                code_version TEXT,
                response_text TEXT,
                response_sha256 TEXT,
                response_bytes BIGINT,
                parsed_items JSONB,
                parsed_bytes BIGINT,
                item_count INTEGER,
                validation_result JSONB NOT NULL DEFAULT '{}'::jsonb,
                error_code TEXT,
                CONSTRAINT extraction_attempts_job_fk FOREIGN KEY(extraction_job_id)
                    REFERENCES %I.extraction_jobs(id) ON DELETE CASCADE,
                CONSTRAINT extraction_attempts_phase_check CHECK(phase IN ('started','received','completed','failed')),
                CONSTRAINT extraction_attempts_finish_check CHECK(
                    (phase IN ('completed','failed')) = (finished_at IS NOT NULL)),
                CONSTRAINT extraction_attempts_complete_check CHECK(phase<>'completed' OR
                    (input_payload IS NOT NULL AND response_text IS NOT NULL AND response_received_at IS NOT NULL
                     AND parsed_items IS NOT NULL AND item_count IS NOT NULL AND error_code IS NULL)),
                CONSTRAINT extraction_attempts_input_size CHECK(input_bytes>=0),
                CONSTRAINT extraction_attempts_response_size CHECK(response_bytes>=0),
                CONSTRAINT extraction_attempts_parsed_size CHECK(parsed_bytes>=0)
            )
        $ddl$, target.nspname,target.nspname);
        -- Reject an incompatible pre-existing table rather than silently accepting it.
        FOR expected IN SELECT * FROM (VALUES
            ('id','uuid'),('extraction_job_id','uuid'),('source_message_id','uuid'),('parent_attempt_id','uuid'),
            ('started_at','timestamp with time zone'),('response_received_at','timestamp with time zone'),
            ('finished_at','timestamp with time zone'),('phase','text'),('input_payload','jsonb'),
            ('input_sha256','text'),('input_bytes','bigint'),('requested_model','text'),('prompt_version','text'),
            ('code_version','text'),('response_text','text'),('response_sha256','text'),('response_bytes','bigint'),
            ('parsed_items','jsonb'),('parsed_bytes','bigint'),('item_count','integer'),
            ('validation_result','jsonb'),('error_code','text')
        ) AS cols(name,kind) LOOP
            SELECT data_type INTO actual_type FROM information_schema.columns
                WHERE table_schema=target.nspname AND table_name='extraction_attempts' AND column_name=expected.name;
            IF actual_type IS DISTINCT FROM expected.kind THEN
                RAISE EXCEPTION 'Incompatible extraction attempts column: %.%',target.nspname,expected.name;
            END IF;
        END LOOP;
        IF NOT EXISTS (SELECT 1 FROM pg_constraint
            WHERE conrelid=to_regclass(format('%I.extraction_attempts',target.nspname))
              AND conname='extraction_attempts_job_fk' AND contype='f' AND confdeltype='c'
              AND confrelid=to_regclass(format('%I.extraction_jobs',target.nspname))) THEN
            RAISE EXCEPTION 'Incompatible extraction attempts foreign key: %',target.nspname;
        END IF;
        EXECUTE format('CREATE INDEX IF NOT EXISTS ix_extraction_attempts_job_started ON %I.extraction_attempts (extraction_job_id,started_at DESC,id DESC)',target.nspname);
        EXECUTE format('CREATE INDEX IF NOT EXISTS ix_extraction_attempts_phase ON %I.extraction_attempts (phase)',target.nspname);
        IF EXISTS (
            SELECT 1 FROM information_schema.columns WHERE table_schema=target.nspname
              AND table_name='extraction_attempts'
              AND column_name IN ('id','extraction_job_id','source_message_id','started_at','phase',
                  'input_sha256','input_bytes','requested_model','prompt_version','validation_result')
              AND is_nullable<>'NO'
        ) OR (SELECT count(*) FROM pg_constraint
            WHERE conrelid=to_regclass(format('%I.extraction_attempts',target.nspname))
              AND conname IN ('extraction_attempts_pkey','extraction_attempts_parent_attempt_id_key',
                  'extraction_attempts_phase_check','extraction_attempts_finish_check',
                  'extraction_attempts_complete_check','extraction_attempts_input_size',
                  'extraction_attempts_response_size','extraction_attempts_parsed_size')
              AND convalidated)<>8 THEN
            RAISE EXCEPTION 'Incompatible extraction attempts constraints: %',target.nspname;
        END IF;
        IF NOT EXISTS (SELECT 1 FROM pg_index i JOIN pg_class idx ON idx.oid=i.indexrelid
            WHERE i.indrelid=to_regclass(format('%I.extraction_attempts',target.nspname))
              AND idx.relname='ix_extraction_attempts_job_started' AND i.indisvalid AND i.indnatts=3
              AND i.indkey::text='2 5 1')
            OR NOT EXISTS (SELECT 1 FROM pg_index i JOIN pg_class idx ON idx.oid=i.indexrelid
            WHERE i.indrelid=to_regclass(format('%I.extraction_attempts',target.nspname))
              AND idx.relname='ix_extraction_attempts_phase' AND i.indisvalid AND i.indnatts=1
              AND i.indkey::text='8') THEN
            RAISE EXCEPTION 'Incompatible extraction attempts indexes: %',target.nspname;
        END IF;
        EXECUTE format('ALTER TABLE %I.extraction_attempts OWNER TO jarvis',target.nspname);
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='salesanchor_app') THEN
            EXECUTE format('GRANT SELECT,INSERT,UPDATE ON %I.extraction_attempts TO salesanchor_app',target.nspname);
        END IF;
    END LOOP;
END;
$body$;
COMMIT;
