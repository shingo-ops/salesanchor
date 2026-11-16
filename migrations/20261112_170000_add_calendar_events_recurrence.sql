-- ADR-1075 便15A: 予定の繰り返し（design.md §12.4・§12.8）
-- 各会社の部屋の calendar_events に欄 4 つ・CHECK 4 つ・部分 UNIQUE 1 つを足す。何度流しても同じになる。
-- 欄はどれも NULL 可か一定の初期値なので表を書き直さない（ADR-1037 のロック待ちの決まりの中）。
DO $cal_recurrence$
DECLARE
  schema_rec RECORD;
  tbl regclass;
  chk RECORD;
BEGIN
  FOR schema_rec IN SELECT nspname FROM pg_namespace WHERE nspname ~ '^tenant_\d+$' LOOP
    IF to_regclass(format('%I.calendar_events', schema_rec.nspname)) IS NULL THEN
      CONTINUE;
    END IF;
    tbl := format('%I.calendar_events', schema_rec.nspname)::regclass;

    EXECUTE format('ALTER TABLE %s ADD COLUMN IF NOT EXISTS recurrence_rule TEXT', tbl);
    EXECUTE format(
      'ALTER TABLE %s ADD COLUMN IF NOT EXISTS recurring_event_id INTEGER REFERENCES %s(id) ON DELETE CASCADE',
      tbl, tbl
    );
    EXECUTE format('ALTER TABLE %s ADD COLUMN IF NOT EXISTS original_start_datetime TIMESTAMPTZ', tbl);
    EXECUTE format('ALTER TABLE %s ADD COLUMN IF NOT EXISTS is_cancelled BOOLEAN NOT NULL DEFAULT false', tbl);

    FOR chk IN
      SELECT * FROM (VALUES
        ('calendar_events_recurrence_role_check',
         'NOT (recurrence_rule IS NOT NULL AND recurring_event_id IS NOT NULL)'),
        ('calendar_events_exception_pair_check',
         '(recurring_event_id IS NULL) = (original_start_datetime IS NULL)'),
        ('calendar_events_cancelled_exception_check',
         'NOT is_cancelled OR recurring_event_id IS NOT NULL'),
        ('calendar_events_recurrence_rule_format_check',
         'recurrence_rule ~ ''^FREQ=(DAILY|WEEKLY|MONTHLY|YEARLY)(;[A-Z]+=[A-Z0-9,+-]+)*$''')
      ) AS v(name, expr)
    LOOP
      IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conrelid = tbl AND conname = chk.name
      ) THEN
        EXECUTE format('ALTER TABLE %s ADD CONSTRAINT %I CHECK (%s) NOT VALID', tbl, chk.name, chk.expr);
        EXECUTE format('ALTER TABLE %s VALIDATE CONSTRAINT %I', tbl, chk.name);
      END IF;
    END LOOP;

    EXECUTE format(
      'CREATE UNIQUE INDEX IF NOT EXISTS calendar_events_exception_unique_idx ON %s'
      ' (recurring_event_id, original_start_datetime) WHERE recurring_event_id IS NOT NULL',
      tbl
    );
  END LOOP;
END
$cal_recurrence$;
