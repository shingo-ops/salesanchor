-- schedule-settings 便3a: 人の色を 24 色の鍵へ・使っていない 3 列を外す（設計 design-bin3a.md §3-1）
-- 各会社の部屋の calendar_owner_settings に color_key（text・NULL か 24 鍵）を足し、古い color（自由な色の値）が
-- あれば 24 色に合うものだけ鍵へ写し、color・is_visible・share_mode を外す。何度流しても同じ。
-- 全部屋を 1 つの DO に入れ、最後の確かめが失敗すれば全体が戻る。calendar_owner_settings が無い部屋は飛ばす。
-- CASCADE は使わない: 3 列に依存するものがあれば、この移行は失敗して止まる。
-- ロックは短い（ADR-1037）。本番は 5 社とも 0 行。
-- 戻し方（値は戻らない。本番は 0 行）:
--   ALTER TABLE <部屋>.calendar_owner_settings
--     ADD COLUMN color varchar(32) DEFAULT '#1a73e8' NOT NULL,
--     ADD COLUMN is_visible boolean DEFAULT false NOT NULL,
--     ADD COLUMN share_mode varchar(16) DEFAULT 'self' NOT NULL;
--   ALTER TABLE <部屋>.calendar_owner_settings
--     ADD CONSTRAINT calendar_owner_settings_share_mode_check CHECK (share_mode IN ('self', 'view', 'edit'));
--   ALTER TABLE <部屋>.calendar_owner_settings DROP COLUMN color_key;
DO $owner_color_key$
DECLARE
  schema_rec RECORD;
BEGIN
  FOR schema_rec IN SELECT nspname FROM pg_namespace WHERE nspname ~ '^tenant_\d+$' LOOP
    IF to_regclass(format('%I.calendar_owner_settings', schema_rec.nspname)) IS NULL THEN
      CONTINUE;
    END IF;

    -- 1. color_key 列
    EXECUTE format(
      'ALTER TABLE %I.calendar_owner_settings ADD COLUMN IF NOT EXISTS color_key text',
      schema_rec.nspname
    );

    -- 2. CHECK（名前で確かめる）。NULL は IN を通るので「標準の色」になる
    IF NOT EXISTS (
      SELECT 1 FROM pg_constraint
      WHERE conrelid = format('%I.calendar_owner_settings', schema_rec.nspname)::regclass
        AND conname = 'calendar_owner_settings_color_key_check'
    ) THEN
      EXECUTE format($f$
        ALTER TABLE %I.calendar_owner_settings
          ADD CONSTRAINT calendar_owner_settings_color_key_check
          CHECK (color_key IN ('radicchio', 'cherry_blossom', 'flamingo', 'tomato', 'tangerine', 'pumpkin', 'mango', 'banana', 'citron', 'avocado', 'pistachio', 'basil', 'sage', 'eucalyptus', 'peacock', 'cobalt', 'lavender', 'blueberry', 'wisteria', 'amethyst', 'grape', 'cocoa', 'graphite', 'birch'))
      $f$, schema_rec.nspname);
    END IF;

    -- 3. 古い color 列が残っているときだけ、24 色に合うものを鍵へ写す（合わないものは NULL のまま）
    IF EXISTS (
      SELECT 1 FROM information_schema.columns
      WHERE table_schema = schema_rec.nspname
        AND table_name = 'calendar_owner_settings'
        AND column_name = 'color'
    ) THEN
      EXECUTE format($f$
        UPDATE %I.calendar_owner_settings SET color_key = CASE lower(btrim(color))
          WHEN '#ad1457' THEN 'radicchio'
          WHEN '#d81b60' THEN 'cherry_blossom'
          WHEN '#e67c73' THEN 'flamingo'
          WHEN '#d50000' THEN 'tomato'
          WHEN '#f4511e' THEN 'tangerine'
          WHEN '#ef6c00' THEN 'pumpkin'
          WHEN '#f09300' THEN 'mango'
          WHEN '#f6bf26' THEN 'banana'
          WHEN '#e4c441' THEN 'citron'
          WHEN '#c0ca33' THEN 'avocado'
          WHEN '#7cb342' THEN 'pistachio'
          WHEN '#0b8043' THEN 'basil'
          WHEN '#33b679' THEN 'sage'
          WHEN '#009688' THEN 'eucalyptus'
          WHEN '#039be5' THEN 'peacock'
          WHEN '#4285f4' THEN 'cobalt'
          WHEN '#7986cb' THEN 'lavender'
          WHEN '#3f51b5' THEN 'blueberry'
          WHEN '#b39ddb' THEN 'wisteria'
          WHEN '#9e69af' THEN 'amethyst'
          WHEN '#8e24aa' THEN 'grape'
          WHEN '#795548' THEN 'cocoa'
          WHEN '#616161' THEN 'graphite'
          WHEN '#a79b8e' THEN 'birch'
        END
        WHERE color_key IS NULL
      $f$, schema_rec.nspname);
    END IF;

    -- 4. 使っていない 3 列を外す（CASCADE なし。share_mode の CHECK は列と一緒に消える）
    EXECUTE format(
      'ALTER TABLE %I.calendar_owner_settings DROP COLUMN IF EXISTS color, DROP COLUMN IF EXISTS is_visible, DROP COLUMN IF EXISTS share_mode',
      schema_rec.nspname
    );

    -- 5. 最後の確かめ
    IF EXISTS (
      SELECT 1 FROM information_schema.columns
      WHERE table_schema = schema_rec.nspname
        AND table_name = 'calendar_owner_settings'
        AND column_name IN ('color', 'is_visible', 'share_mode')
    ) THEN
      RAISE EXCEPTION '% の calendar_owner_settings に古い列が残っている', schema_rec.nspname;
    END IF;
    IF NOT EXISTS (
      SELECT 1 FROM information_schema.columns
      WHERE table_schema = schema_rec.nspname
        AND table_name = 'calendar_owner_settings'
        AND column_name = 'color_key'
    ) THEN
      RAISE EXCEPTION '% の calendar_owner_settings に color_key が無い', schema_rec.nspname;
    END IF;
  END LOOP;
END
$owner_color_key$;
