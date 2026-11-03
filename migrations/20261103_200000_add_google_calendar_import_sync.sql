-- ADR-1059 便2: Google の予定の取り込み（足すだけ・冪等）
ALTER TABLE public.google_webhook_subscriptions ADD COLUMN IF NOT EXISTS sync_token TEXT;
ALTER TABLE public.google_webhook_subscriptions ADD COLUMN IF NOT EXISTS channel_token_hash VARCHAR(64);

DO $gcal_import_uniq$
DECLARE
  schema_rec RECORD;
  dup_count INTEGER;
BEGIN
  FOR schema_rec IN SELECT nspname FROM pg_namespace WHERE nspname ~ '^tenant_\d+$' LOOP
    IF to_regclass(format('%I.calendar_events', schema_rec.nspname)) IS NULL THEN
      CONTINUE;
    END IF;
    EXECUTE format(
      'SELECT COUNT(*) FROM (SELECT google_event_id FROM %I.calendar_events'
      ' WHERE google_event_id IS NOT NULL GROUP BY google_event_id HAVING COUNT(*) > 1) d',
      schema_rec.nspname) INTO dup_count;
    IF dup_count > 0 THEN
      RAISE EXCEPTION '%.calendar_events に google_event_id の重複が % 件あります（ADR-1059 便2）',
        schema_rec.nspname, dup_count;
    END IF;
    EXECUTE format(
      'CREATE UNIQUE INDEX IF NOT EXISTS uq_calendar_events_google_event_id'
      ' ON %I.calendar_events (google_event_id) WHERE google_event_id IS NOT NULL',
      schema_rec.nspname);
  END LOOP;
END
$gcal_import_uniq$;
