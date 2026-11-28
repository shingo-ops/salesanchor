-- schedule-settings 便2b: 予定の共有に「チーム」を足す（設計 design-bin2b.md §3-1・§3-2）
-- 各会社の部屋に calendar_event_teams（予定とチームの対応）・calendar_category_teams（種類の初期のチーム）を作り、
-- calendar_events.calendar_type と calendar_categories.default_share の CHECK に 'team' を足す。何度流しても同じ。
-- 全部屋を 1 つの DO に入れ、最後の確かめが失敗すれば全体が戻る。calendar_events・teams・calendar_categories が無い部屋は飛ばす。
-- CHECK は 仮の名前 _v2 で NOT VALID → VALIDATE → 古いもの（名前が違う古い部屋の名前なし CHECK も）を定義で探して全部消す → 名前を戻す。
-- ロックは短い（ADR-1037）。2 つの新しい表には RLS を付けない（親の calendar_events・calendar_categories に無いため）。
DO $cal_team_share$
DECLARE
  schema_rec RECORD;
  spec RECORD;
  old_con RECORD;
  tbl regclass;
  v2_name text;
  cnt integer;
  cur_name text;
  cur_def text;
BEGIN
  FOR schema_rec IN SELECT nspname FROM pg_namespace WHERE nspname ~ '^tenant_\d+$' LOOP
    IF to_regclass(format('%I.calendar_events', schema_rec.nspname)) IS NULL THEN
      CONTINUE;
    END IF;
    IF to_regclass(format('%I.teams', schema_rec.nspname)) IS NULL THEN
      CONTINUE;
    END IF;
    IF to_regclass(format('%I.calendar_categories', schema_rec.nspname)) IS NULL THEN
      CONTINUE;
    END IF;

    -- 1. 2 つの対応表
    EXECUTE format($f$
      CREATE TABLE IF NOT EXISTS %1$I.calendar_event_teams (
        event_id integer NOT NULL REFERENCES %1$I.calendar_events(id) ON DELETE CASCADE,
        team_id integer NOT NULL REFERENCES %1$I.teams(id) ON DELETE CASCADE,
        PRIMARY KEY (event_id, team_id)
      )
    $f$, schema_rec.nspname);
    EXECUTE format(
      'CREATE INDEX IF NOT EXISTS idx_calendar_event_teams_team ON %1$I.calendar_event_teams (team_id)',
      schema_rec.nspname
    );
    EXECUTE format($f$
      CREATE TABLE IF NOT EXISTS %1$I.calendar_category_teams (
        category_key character varying(50) NOT NULL REFERENCES %1$I.calendar_categories(key) ON UPDATE RESTRICT ON DELETE CASCADE,
        team_id integer NOT NULL REFERENCES %1$I.teams(id) ON DELETE CASCADE,
        PRIMARY KEY (category_key, team_id)
      )
    $f$, schema_rec.nspname);

    -- 2. CHECK の入れ替え（予定・種類で同じ手順）
    FOR spec IN
      SELECT * FROM (VALUES
        ('calendar_events', 'calendar_events_calendar_type_check', 'calendar_type',
         'CHECK (calendar_type IN (''shared'', ''personal'', ''team''))'),
        ('calendar_categories', 'calendar_categories_default_share_check', 'default_share',
         'CHECK (default_share IN (''self'', ''all'', ''team''))')
      ) AS v(tname, cname, col, def)
    LOOP
      tbl := format('%I.%I', schema_rec.nspname, spec.tname)::regclass;
      v2_name := spec.cname || '_v2';

      -- 2-1. 既に「team を含む CHECK が正しい名前で 1 つ」なら何もしない
      SELECT count(*) INTO cnt
      FROM pg_constraint
      WHERE conrelid = tbl AND contype = 'c'
        AND pg_get_constraintdef(oid) ~ ('\m' || spec.col || '\M');
      IF cnt = 1 THEN
        SELECT conname, pg_get_constraintdef(oid) INTO cur_name, cur_def
        FROM pg_constraint
        WHERE conrelid = tbl AND contype = 'c'
          AND pg_get_constraintdef(oid) ~ ('\m' || spec.col || '\M');
        IF cur_name = spec.cname AND cur_def ~ '\mteam\M' THEN
          CONTINUE;
        END IF;
      END IF;

      -- 2-2. 仮の名前で足して検証（前の回で残っていれば足さない）
      IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conrelid = tbl AND conname = v2_name
      ) THEN
        EXECUTE format('ALTER TABLE %s ADD CONSTRAINT %I %s NOT VALID', tbl, v2_name, spec.def);
      END IF;
      EXECUTE format('ALTER TABLE %s VALIDATE CONSTRAINT %I', tbl, v2_name);

      -- 2-3. 古い CHECK を定義で探して全部消す（名前なしの古い部屋にも効く）
      FOR old_con IN
        SELECT conname FROM pg_constraint
        WHERE conrelid = tbl AND contype = 'c'
          AND pg_get_constraintdef(oid) ~ ('\m' || spec.col || '\M')
          AND conname <> v2_name
      LOOP
        EXECUTE format('ALTER TABLE %s DROP CONSTRAINT %I', tbl, old_con.conname);
      END LOOP;

      -- 2-4. 名前を戻す
      EXECUTE format('ALTER TABLE %s RENAME CONSTRAINT %I TO %I', tbl, v2_name, spec.cname);
    END LOOP;

    -- 3. 最後の確かめ: 各 CHECK がちょうど 1 つ・名前が正しい・team を含む。2 つの表がある
    FOR spec IN
      SELECT * FROM (VALUES
        ('calendar_events', 'calendar_events_calendar_type_check', 'calendar_type'),
        ('calendar_categories', 'calendar_categories_default_share_check', 'default_share')
      ) AS v(tname, cname, col)
    LOOP
      tbl := format('%I.%I', schema_rec.nspname, spec.tname)::regclass;
      SELECT count(*) INTO cnt
      FROM pg_constraint
      WHERE conrelid = tbl AND contype = 'c'
        AND pg_get_constraintdef(oid) ~ ('\m' || spec.col || '\M');
      IF cnt <> 1 THEN
        RAISE EXCEPTION '% の % に % を使う CHECK が % 件ある（1 件のはず）', schema_rec.nspname, spec.tname, spec.col, cnt;
      END IF;
      IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = tbl AND contype = 'c' AND conname = spec.cname
          AND pg_get_constraintdef(oid) ~ '\mteam\M'
      ) THEN
        RAISE EXCEPTION '% の % に team を含む CHECK % が無い', schema_rec.nspname, spec.tname, spec.cname;
      END IF;
    END LOOP;
    IF to_regclass(format('%I.calendar_event_teams', schema_rec.nspname)) IS NULL
       OR to_regclass(format('%I.calendar_category_teams', schema_rec.nspname)) IS NULL THEN
      RAISE EXCEPTION '% に対応表が作られていない', schema_rec.nspname;
    END IF;
  END LOOP;
END
$cal_team_share$;
