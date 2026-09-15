-- CARD-LINE-INTERRUPTED-RECOVERY-01: fixed interrupted jobs, never enqueue here.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
DO $body$
DECLARE
    table_count integer;
    job_count integer;
    expected_count integer := 0;
    changed_count integer;
    target record;
    job record;
BEGIN
    SELECT count(*) INTO table_count
    FROM unnest(ARRAY['source_messages', 'extraction_jobs', 'extraction_items']) AS t(name)
    WHERE to_regclass(format('tenant_004.%I', t.name)) IS NOT NULL;
    IF table_count = 0 THEN
        RETURN;
    ELSIF table_count <> 3 THEN
        RAISE EXCEPTION 'LINE recovery: incomplete TCG structure';
    END IF;
    LOCK TABLE tenant_004.source_messages, tenant_004.extraction_jobs,
        tenant_004.extraction_items IN SHARE ROW EXCLUSIVE MODE;
    SELECT count(*) INTO job_count FROM tenant_004.extraction_jobs
    WHERE id IN ('6da3ca68-651e-4ff6-8316-1c9135508ad2', 'bfa07018-9b34-42b6-990a-017e3c1cf140');
    IF job_count = 0 THEN
        RETURN;
    ELSIF job_count <> 2 THEN
        RAISE EXCEPTION 'LINE recovery: one target job missing';
    END IF;
    FOR target IN SELECT * FROM (VALUES
        ('6da3ca68-651e-4ff6-8316-1c9135508ad2'::uuid, 'b1b58ee9-0d6a-4ed1-8034-f1d62a72b4b2'::uuid,
         false, '3a4633b1-82a6-4ce5-8694-053cd637c5f6'::uuid),
        ('bfa07018-9b34-42b6-990a-017e3c1cf140'::uuid, 'afbc08d1-cf3b-43be-87e5-4b7200144b6c'::uuid,
         true, NULL::uuid)
    ) AS v(job_id, source_id, active, successor)
    LOOP
        SELECT j.*, s.is_active, s.superseded_by,
               (SELECT count(*) FROM tenant_004.extraction_items i WHERE i.extraction_job_id=j.id) AS items
        INTO job FROM tenant_004.extraction_jobs j
        JOIN tenant_004.source_messages s ON s.id=j.source_message_id
        WHERE j.id=target.job_id;
        IF job.source_message_id IS DISTINCT FROM target.source_id
           OR job.created_at IS DISTINCT FROM '2026-09-10T02:49:21.105805Z'::timestamptz THEN
            RAISE EXCEPTION 'LINE recovery: job identity mismatch';
        END IF;
        IF job.status <> 'running' THEN
            CONTINUE;
        END IF;
        IF job.is_active IS DISTINCT FROM target.active
           OR job.superseded_by IS DISTINCT FROM target.successor
           OR job.extracted_at IS NOT NULL OR job.prompt_version IS NOT NULL
           OR job.error_message IS NOT NULL OR job.items <> 0
           OR job.created_at > CURRENT_TIMESTAMP - interval '10 minutes' THEN
            RAISE EXCEPTION 'LINE recovery: running job precondition mismatch';
        END IF;
        expected_count := expected_count + 1;
    END LOOP;
    UPDATE tenant_004.extraction_jobs
    SET status='error', error_message='LINE-RECOVERY-20260910: interrupted job; PO-approved recovery'
    WHERE id IN ('6da3ca68-651e-4ff6-8316-1c9135508ad2', 'bfa07018-9b34-42b6-990a-017e3c1cf140')
      AND status='running';
    GET DIAGNOSTICS changed_count = ROW_COUNT;
    IF changed_count <> expected_count THEN
        RAISE EXCEPTION 'LINE recovery: changed row count mismatch';
    END IF;
END;
$body$;
COMMIT;
