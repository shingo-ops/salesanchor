-- schedule-settings 便3b: ひとりひとりの初期値（開いたときの形・週の始まり・予定の長さ・Meet・誰の予定を出すか）
-- 各会社の部屋の calendar_owner_settings に 6 列を足す。既存の行は既定値（今の動きと同じ）になる。
-- 全部屋を 1 つの DO に入れ、最後の確かめが失敗すれば全体が戻る。calendar_owner_settings か teams が無い部屋は飛ばす。
-- 何度流しても同じ（列は ADD COLUMN IF NOT EXISTS・CHECK と FK は名前で確かめてから足す）。
-- ロックは短い（ADR-1037）。本番は 5 社とも 0 行。
-- 戻し方（値は戻る先が無い。color_key には触れない）:
--   ALTER TABLE <部屋>.calendar_owner_settings
--     DROP COLUMN IF EXISTS default_view,
--     DROP COLUMN IF EXISTS week_start,
--     DROP COLUMN IF EXISTS event_minutes,
--     DROP COLUMN IF EXISTS auto_meet,
--     DROP COLUMN IF EXISTS open_owners,
--     DROP COLUMN IF EXISTS open_team_id;
--   （CHECK 4 つと FK は列と一緒に消える）
DO $owner_prefs$
DECLARE
  schema_rec RECORD;
BEGIN
  FOR schema_rec IN SELECT nspname FROM pg_namespace WHERE nspname ~ '^tenant_\d+$' LOOP
    IF to_regclass(format('%I.calendar_owner_settings', schema_rec.nspname)) IS NULL
       OR to_regclass(format('%I.teams', schema_rec.nspname)) IS NULL THEN
      CONTINUE;
    END IF;

    -- 1. 6 列
    EXECUTE format($f$
      ALTER TABLE %I.calendar_owner_settings
        ADD COLUMN IF NOT EXISTS default_view text NOT NULL DEFAULT 'week',
        ADD COLUMN IF NOT EXISTS week_start smallint NOT NULL DEFAULT 0,
        ADD COLUMN IF NOT EXISTS event_minutes smallint NOT NULL DEFAULT 60,
        ADD COLUMN IF NOT EXISTS auto_meet boolean NOT NULL DEFAULT false,
        ADD COLUMN IF NOT EXISTS open_owners text NOT NULL DEFAULT 'self',
        ADD COLUMN IF NOT EXISTS open_team_id integer
    $f$, schema_rec.nspname);

    -- 2. CHECK（名前で確かめる）
    IF NOT EXISTS (
      SELECT 1 FROM pg_constraint
      WHERE conrelid = format('%I.calendar_owner_settings', schema_rec.nspname)::regclass
        AND conname = 'calendar_owner_settings_default_view_check'
    ) THEN
      EXECUTE format($f$
        ALTER TABLE %I.calendar_owner_settings
          ADD CONSTRAINT calendar_owner_settings_default_view_check
          CHECK (default_view IN ('day', 'threeDay', 'week', 'month', 'list'))
      $f$, schema_rec.nspname);
    END IF;

    IF NOT EXISTS (
      SELECT 1 FROM pg_constraint
      WHERE conrelid = format('%I.calendar_owner_settings', schema_rec.nspname)::regclass
        AND conname = 'calendar_owner_settings_week_start_check'
    ) THEN
      EXECUTE format($f$
        ALTER TABLE %I.calendar_owner_settings
          ADD CONSTRAINT calendar_owner_settings_week_start_check
          CHECK (week_start IN (0, 1))
      $f$, schema_rec.nspname);
    END IF;

    IF NOT EXISTS (
      SELECT 1 FROM pg_constraint
      WHERE conrelid = format('%I.calendar_owner_settings', schema_rec.nspname)::regclass
        AND conname = 'calendar_owner_settings_event_minutes_check'
    ) THEN
      EXECUTE format($f$
        ALTER TABLE %I.calendar_owner_settings
          ADD CONSTRAINT calendar_owner_settings_event_minutes_check
          CHECK (event_minutes IN (15, 30, 45, 60, 90, 120))
      $f$, schema_rec.nspname);
    END IF;

    IF NOT EXISTS (
      SELECT 1 FROM pg_constraint
      WHERE conrelid = format('%I.calendar_owner_settings', schema_rec.nspname)::regclass
        AND conname = 'calendar_owner_settings_open_owners_check'
    ) THEN
      EXECUTE format($f$
        ALTER TABLE %I.calendar_owner_settings
          ADD CONSTRAINT calendar_owner_settings_open_owners_check
          CHECK (open_owners IN ('self', 'all', 'team'))
      $f$, schema_rec.nspname);
    END IF;

    -- 3. FK（チームを消したら open_team_id は NULL に戻る）
    IF NOT EXISTS (
      SELECT 1 FROM pg_constraint
      WHERE conrelid = format('%I.calendar_owner_settings', schema_rec.nspname)::regclass
        AND conname = 'fk_calendar_owner_settings_open_team'
    ) THEN
      EXECUTE format($f$
        ALTER TABLE %I.calendar_owner_settings
          ADD CONSTRAINT fk_calendar_owner_settings_open_team
          FOREIGN KEY (open_team_id) REFERENCES %I.teams(id) ON DELETE SET NULL
      $f$, schema_rec.nspname, schema_rec.nspname);
    END IF;

    -- 4. 最後の確かめ（6 列の型・CHECK 4 つ・FK）
    IF (
      SELECT count(*) FROM information_schema.columns
      WHERE table_schema = schema_rec.nspname
        AND table_name = 'calendar_owner_settings'
        AND (
          (column_name = 'default_view' AND data_type = 'text')
          OR (column_name = 'week_start' AND data_type = 'smallint')
          OR (column_name = 'event_minutes' AND data_type = 'smallint')
          OR (column_name = 'auto_meet' AND data_type = 'boolean')
          OR (column_name = 'open_owners' AND data_type = 'text')
          OR (column_name = 'open_team_id' AND data_type = 'integer')
        )
    ) <> 6 THEN
      RAISE EXCEPTION '% の calendar_owner_settings に初期値の 6 列が揃っていない', schema_rec.nspname;
    END IF;
    IF (
      SELECT count(*) FROM pg_constraint
      WHERE conrelid = format('%I.calendar_owner_settings', schema_rec.nspname)::regclass
        AND conname IN (
          'calendar_owner_settings_default_view_check',
          'calendar_owner_settings_week_start_check',
          'calendar_owner_settings_event_minutes_check',
          'calendar_owner_settings_open_owners_check',
          'fk_calendar_owner_settings_open_team'
        )
    ) <> 5 THEN
      RAISE EXCEPTION '% の calendar_owner_settings に初期値の CHECK・FK が揃っていない', schema_rec.nspname;
    END IF;
  END LOOP;
END
$owner_prefs$;
