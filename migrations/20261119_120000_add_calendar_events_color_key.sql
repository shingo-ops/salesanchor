-- ADR-1081 便1: 予定ごとの色（design.md §4-2）
-- 各会社の部屋の calendar_events に color_key（NULL＝デフォルト）と値の決まり 1 つを足す。何度流しても同じになる。
-- 欄は NULL 可なので表を書き直さない（ADR-1037 のロック待ちの決まりの中）。
DO $cal_color_key$
DECLARE
  schema_rec RECORD;
  tbl regclass;
BEGIN
  FOR schema_rec IN SELECT nspname FROM pg_namespace WHERE nspname ~ '^tenant_\d+$' LOOP
    IF to_regclass(format('%I.calendar_events', schema_rec.nspname)) IS NULL THEN
      CONTINUE;
    END IF;
    tbl := format('%I.calendar_events', schema_rec.nspname)::regclass;
    EXECUTE format('ALTER TABLE %s ADD COLUMN IF NOT EXISTS color_key TEXT', tbl);
    IF NOT EXISTS (
      SELECT 1 FROM pg_constraint WHERE conrelid = tbl AND conname = 'calendar_events_color_key_check'
    ) THEN
      EXECUTE format(
        'ALTER TABLE %s ADD CONSTRAINT calendar_events_color_key_check CHECK (color_key IN (%s)) NOT VALID',
        tbl,
        '''radicchio'',''cherry_blossom'',''flamingo'',''tomato'',''tangerine'',''pumpkin'',''mango'',''banana'',''citron'',''avocado'',''pistachio'',''basil'',''sage'',''eucalyptus'',''peacock'',''cobalt'',''lavender'',''blueberry'',''wisteria'',''amethyst'',''grape'',''cocoa'',''graphite'',''birch'''
      );
      EXECUTE format('ALTER TABLE %s VALIDATE CONSTRAINT calendar_events_color_key_check', tbl);
    END IF;
  END LOOP;
END
$cal_color_key$;
