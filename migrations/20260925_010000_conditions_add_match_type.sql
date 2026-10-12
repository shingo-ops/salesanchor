-- conditions テーブルに match_type / effect カラムを追加
-- public.conditions はVIEW（実テーブルは public.line_conditions）
-- additive-only: カラム追加のみ

DO $$
DECLARE
  _schema text;
BEGIN
  -- public.line_conditions（実テーブル）にカラム追加
  IF EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'line_conditions'
    AND table_type = 'BASE TABLE'
  ) THEN
    IF NOT EXISTS (
      SELECT 1 FROM information_schema.columns
      WHERE table_schema = 'public' AND table_name = 'line_conditions' AND column_name = 'match_type'
    ) THEN
      ALTER TABLE public.line_conditions ADD COLUMN match_type TEXT NOT NULL DEFAULT 'KEYWORD';
    END IF;
    IF NOT EXISTS (
      SELECT 1 FROM information_schema.columns
      WHERE table_schema = 'public' AND table_name = 'line_conditions' AND column_name = 'effect'
    ) THEN
      ALTER TABLE public.line_conditions ADD COLUMN effect TEXT NOT NULL DEFAULT 'OUTPUT';
    END IF;
  -- public.conditions がテーブルの場合（VIEWリネーム前の環境対応）
  ELSIF EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'conditions'
    AND table_type = 'BASE TABLE'
  ) THEN
    IF NOT EXISTS (
      SELECT 1 FROM information_schema.columns
      WHERE table_schema = 'public' AND table_name = 'conditions' AND column_name = 'match_type'
    ) THEN
      ALTER TABLE public.conditions ADD COLUMN match_type TEXT NOT NULL DEFAULT 'KEYWORD';
    END IF;
    IF NOT EXISTS (
      SELECT 1 FROM information_schema.columns
      WHERE table_schema = 'public' AND table_name = 'conditions' AND column_name = 'effect'
    ) THEN
      ALTER TABLE public.conditions ADD COLUMN effect TEXT NOT NULL DEFAULT 'OUTPUT';
    END IF;
  END IF;

  -- VIEWを再作成（新カラムを含むように）
  IF EXISTS (
    SELECT 1 FROM information_schema.views
    WHERE table_schema = 'public' AND table_name = 'conditions'
  ) THEN
    CREATE OR REPLACE VIEW public.conditions AS TABLE public.line_conditions;
  END IF;

  -- テナントスキーマの conditions にもカラム追加
  FOR _schema IN
    SELECT nspname FROM pg_namespace WHERE nspname LIKE 'tenant_%'
  LOOP
    -- テナントスキーマでも line_conditions が実テーブルの場合
    IF EXISTS (
      SELECT 1 FROM information_schema.tables
      WHERE table_schema = _schema AND table_name = 'line_conditions'
      AND table_type = 'BASE TABLE'
    ) THEN
      IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = _schema AND table_name = 'line_conditions' AND column_name = 'match_type'
      ) THEN
        EXECUTE format('ALTER TABLE %I.line_conditions ADD COLUMN match_type TEXT NOT NULL DEFAULT ''KEYWORD''', _schema);
      END IF;
      IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = _schema AND table_name = 'line_conditions' AND column_name = 'effect'
      ) THEN
        EXECUTE format('ALTER TABLE %I.line_conditions ADD COLUMN effect TEXT NOT NULL DEFAULT ''OUTPUT''', _schema);
      END IF;
      -- テナントのVIEWも再作成
      IF EXISTS (
        SELECT 1 FROM information_schema.views
        WHERE table_schema = _schema AND table_name = 'conditions'
      ) THEN
        EXECUTE format('CREATE OR REPLACE VIEW %I.conditions AS TABLE %I.line_conditions', _schema, _schema);
      END IF;
    -- テナントスキーマで conditions がテーブルの場合
    ELSIF EXISTS (
      SELECT 1 FROM information_schema.tables
      WHERE table_schema = _schema AND table_name = 'conditions'
      AND table_type = 'BASE TABLE'
    ) THEN
      IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = _schema AND table_name = 'conditions' AND column_name = 'match_type'
      ) THEN
        EXECUTE format('ALTER TABLE %I.conditions ADD COLUMN match_type TEXT NOT NULL DEFAULT ''KEYWORD''', _schema);
      END IF;
      IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = _schema AND table_name = 'conditions' AND column_name = 'effect'
      ) THEN
        EXECUTE format('ALTER TABLE %I.conditions ADD COLUMN effect TEXT NOT NULL DEFAULT ''OUTPUT''', _schema);
      END IF;
    END IF;
  END LOOP;
END $$;
