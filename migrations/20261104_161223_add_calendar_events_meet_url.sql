-- Google Meet: 各社スキーマの calendar_events に meet_url 列を足す（足すだけ・冪等）
-- Meet の URL の置き場所はこの列 1 か所だけ（ADR-1060）
DO $cal_meet_url$
DECLARE
  schema_rec RECORD;
BEGIN
  FOR schema_rec IN SELECT nspname FROM pg_namespace WHERE nspname ~ '^tenant_\d+$' LOOP
    IF to_regclass(format('%I.calendar_events', schema_rec.nspname)) IS NULL THEN
      CONTINUE;
    END IF;
    EXECUTE format(
      'ALTER TABLE %I.calendar_events ADD COLUMN IF NOT EXISTS meet_url TEXT',
      schema_rec.nspname);
  END LOOP;
END
$cal_meet_url$;
