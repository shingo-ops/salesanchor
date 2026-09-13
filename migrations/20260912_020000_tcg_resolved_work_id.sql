-- Work-ID decision is separate from verbatim fields; no backfill.
DO $body$
DECLARE target RECORD;
BEGIN
  FOR target IN SELECT nspname FROM pg_namespace WHERE nspname LIKE 'tenant_%' ORDER BY nspname LOOP
    IF to_regclass(format('%I.extraction_items', target.nspname)) IS NOT NULL
       AND to_regclass(format('%I.extraction_jobs', target.nspname)) IS NOT NULL THEN
      EXECUTE format('ALTER TABLE %I.extraction_items ADD COLUMN IF NOT EXISTS resolved_work_id UUID', target.nspname);
      EXECUTE format('ALTER TABLE %I.extraction_jobs ADD COLUMN IF NOT EXISTS work_reference_snapshot JSONB, ADD COLUMN IF NOT EXISTS work_reference_sha256 TEXT', target.nspname);
    END IF;
  END LOOP;
END;
$body$;
