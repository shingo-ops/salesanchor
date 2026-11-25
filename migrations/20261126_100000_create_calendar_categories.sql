-- schedule-settings 便2a: 予定の種類を DB の表 1 つへ（設計 design-bin2a.md §3-1・§3-2）
-- 各会社の部屋に calendar_categories（種類の表）を作り、今の 7 種を入れ、calendar_events.category の
-- 固定の CHECK を外部キーに置き換える。何度流しても同じ。全部屋を 1 つの DO に入れ、確かめが失敗すれば全体が戻る。
-- 欄が有る部屋は ALTER しない（ロックを取らない・ADR-1037）。外部キーは NOT VALID で足して VALIDATE する。
DO $cal_categories$
DECLARE
  schema_rec RECORD;
  tbl regclass;
  left_checks integer;
BEGIN
  FOR schema_rec IN SELECT nspname FROM pg_namespace WHERE nspname ~ '^tenant_\d+$' LOOP
    IF to_regclass(format('%I.calendar_events', schema_rec.nspname)) IS NULL THEN
      CONTINUE;
    END IF;
    tbl := format('%I.calendar_events', schema_rec.nspname)::regclass;

    -- 1. category 列が無い部屋だけ足す
    IF NOT EXISTS (
      SELECT 1 FROM pg_attribute
      WHERE attrelid = tbl AND attname = 'category' AND NOT attisdropped
    ) THEN
      EXECUTE format(
        'ALTER TABLE %s ADD COLUMN category character varying(50) NOT NULL DEFAULT ''meeting''',
        tbl
      );
    END IF;

    -- 2. 種類の表 → 7 行 → 更新時刻の関数とトリガ
    EXECUTE format($f$
      CREATE TABLE IF NOT EXISTS %1$I.calendar_categories (
        key character varying(50) NOT NULL,
        name character varying(50),
        color_key text,
        default_share character varying(10) DEFAULT 'all' NOT NULL,
        sort_order integer NOT NULL,
        is_active boolean DEFAULT true NOT NULL,
        created_at timestamp with time zone DEFAULT now() NOT NULL,
        updated_at timestamp with time zone DEFAULT now() NOT NULL,
        CONSTRAINT calendar_categories_pkey PRIMARY KEY (key),
        CONSTRAINT calendar_categories_key_format_check CHECK (key ~ '^[a-z][a-z0-9_]{0,49}$'),
        CONSTRAINT calendar_categories_default_share_check CHECK (default_share IN ('self', 'all')),
        CONSTRAINT calendar_categories_color_key_check CHECK (color_key IN ('radicchio', 'cherry_blossom', 'flamingo', 'tomato', 'tangerine', 'pumpkin', 'mango', 'banana', 'citron', 'avocado', 'pistachio', 'basil', 'sage', 'eucalyptus', 'peacock', 'cobalt', 'lavender', 'blueberry', 'wisteria', 'amethyst', 'grape', 'cocoa', 'graphite', 'birch')),
        CONSTRAINT calendar_categories_name_check CHECK (name IS NOT NULL OR key IN ('meeting', 'personal', 'procurement', 'shipping', 'billing', 'release', 'holiday'))
      )
    $f$, schema_rec.nspname);

    EXECUTE format($f$
      INSERT INTO %1$I.calendar_categories (key, default_share, sort_order) VALUES
        ('meeting', 'all', 1),
        ('personal', 'self', 2),
        ('procurement', 'all', 3),
        ('shipping', 'all', 4),
        ('billing', 'all', 5),
        ('release', 'all', 6),
        ('holiday', 'all', 7)
      ON CONFLICT (key) DO NOTHING
    $f$, schema_rec.nspname);

    EXECUTE format($f$
      CREATE OR REPLACE FUNCTION %1$I.set_updated_at_calendar_categories()
       RETURNS trigger
       LANGUAGE plpgsql
      AS $function$
      BEGIN
        NEW.updated_at = NOW();
        RETURN NEW;
      END;
      $function$
    $f$, schema_rec.nspname);

    IF NOT EXISTS (
      SELECT 1 FROM pg_trigger
      WHERE tgname = 'trg_calendar_categories_updated_at'
        AND tgrelid = format('%I.calendar_categories', schema_rec.nspname)::regclass
    ) THEN
      EXECUTE format(
        'CREATE TRIGGER trg_calendar_categories_updated_at BEFORE UPDATE ON %1$I.calendar_categories FOR EACH ROW EXECUTE FUNCTION %1$I.set_updated_at_calendar_categories()',
        schema_rec.nspname
      );
    END IF;

    -- 3. 予定の外部キー（NOT VALID → VALIDATE）
    IF NOT EXISTS (
      SELECT 1 FROM pg_constraint WHERE conrelid = tbl AND conname = 'calendar_events_category_fkey'
    ) THEN
      EXECUTE format(
        'ALTER TABLE %s ADD CONSTRAINT calendar_events_category_fkey FOREIGN KEY (category) REFERENCES %I.calendar_categories(key) ON UPDATE RESTRICT ON DELETE RESTRICT NOT VALID',
        tbl, schema_rec.nspname
      );
      EXECUTE format('ALTER TABLE %s VALIDATE CONSTRAINT calendar_events_category_fkey', tbl);
    END IF;

    -- 4. 固定の CHECK を外す
    EXECUTE format('ALTER TABLE %s DROP CONSTRAINT IF EXISTS calendar_events_category_check', tbl);

    -- 5. 確かめ: category を使う CHECK（contype = 'c'）が 1 件でも残れば全体を戻す
    SELECT count(*) INTO left_checks
    FROM pg_constraint
    WHERE conrelid = tbl
      AND contype = 'c'
      AND pg_get_constraintdef(oid) ~ '\mcategory\M';
    IF left_checks > 0 THEN
      RAISE EXCEPTION '% の calendar_events に category を使う CHECK が % 件残っている', schema_rec.nspname, left_checks;
    END IF;
  END LOOP;
END
$cal_categories$;
