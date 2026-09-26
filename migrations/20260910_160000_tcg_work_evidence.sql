-- CARD-LINE-WORK-MATCHING-V3-01: additive evidence; no backfill or reanalysis.
DO $body$
DECLARE
    target RECORD;
BEGIN
    FOR target IN SELECT nspname FROM pg_namespace
                  WHERE nspname LIKE 'tenant_%' ORDER BY nspname
    LOOP
        IF to_regclass(format('%I.extraction_items', target.nspname)) IS NOT NULL
           AND to_regclass(format('%I.extraction_jobs', target.nspname)) IS NOT NULL THEN
            EXECUTE format('ALTER TABLE %I.extraction_items
                ADD COLUMN IF NOT EXISTS raw_work_name TEXT,
                ADD COLUMN IF NOT EXISTS raw_work_source_line_span TEXT', target.nspname);
        END IF;
    END LOOP;
END;
$body$;
