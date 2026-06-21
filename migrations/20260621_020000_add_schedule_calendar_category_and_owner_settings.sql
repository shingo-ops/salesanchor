-- Schedule owner-based calendars
--
-- 追加内容:
--   1. calendar_events に category を追加（予定内の内部ラベル保持用）
--   2. 担当者ごとのカレンダー表示設定 calendar_owner_settings を tenant schema に追加
--
-- いずれも additive のみ。既存データは壊さず、category は既定 'meeting' を付与する。

DO $schedule_owner$
DECLARE
  schema_rec RECORD;
BEGIN
  FOR schema_rec IN
    SELECT nspname
    FROM pg_namespace
    WHERE nspname ~ '^tenant_\d+$'
    ORDER BY nspname
  LOOP
    IF NOT EXISTS (
      SELECT 1
      FROM pg_tables
      WHERE schemaname = schema_rec.nspname
        AND tablename = 'role_permissions'
    ) THEN
      CONTINUE;
    END IF;

    IF to_regclass(format('%I.calendar_events', schema_rec.nspname)) IS NULL THEN
      CONTINUE;
    END IF;

    EXECUTE format(
      'ALTER TABLE %I.calendar_events
         ADD COLUMN IF NOT EXISTS category VARCHAR(50) NOT NULL DEFAULT ''meeting''',
      schema_rec.nspname
    );

    IF NOT EXISTS (
      SELECT 1
      FROM pg_constraint c
      JOIN pg_namespace n ON n.oid = c.connamespace
      WHERE c.conname = 'calendar_events_category_check'
        AND n.nspname = schema_rec.nspname
    ) THEN
      EXECUTE format(
        'ALTER TABLE %I.calendar_events
           ADD CONSTRAINT calendar_events_category_check
           CHECK (category IN (''meeting'', ''personal'', ''procurement'', ''shipping'', ''billing'', ''release'', ''holiday''))',
        schema_rec.nspname
      );
    END IF;

    EXECUTE format(
      'CREATE TABLE IF NOT EXISTS %I.calendar_owner_settings (
         staff_id INTEGER PRIMARY KEY REFERENCES %I.staff(id) ON DELETE CASCADE,
         color VARCHAR(32) NOT NULL DEFAULT ''#1a73e8'',
         is_visible BOOLEAN NOT NULL DEFAULT FALSE,
         share_mode VARCHAR(16) NOT NULL DEFAULT ''self''
           CHECK (share_mode IN (''self'', ''view'', ''edit'')),
         updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
       )',
      schema_rec.nspname,
      schema_rec.nspname
    );

    EXECUTE format(
      'CREATE INDEX IF NOT EXISTS idx_calendar_owner_settings_staff_id
         ON %I.calendar_owner_settings (staff_id)',
      schema_rec.nspname
    );
  END LOOP;
END
$schedule_owner$;
