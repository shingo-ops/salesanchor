-- conditions テーブルに match_type / effect カラムを追加
-- ADR: ルールテーブル統一（conditions → tcg_status_master パターン）
-- additive-only: カラム追加のみ

DO $$
DECLARE
  _schema text;
BEGIN
  -- public スキーマの conditions テーブルにカラム追加
  IF EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'conditions'
  ) THEN
    -- match_type カラム追加
    IF NOT EXISTS (
      SELECT 1 FROM information_schema.columns
      WHERE table_schema = 'public' AND table_name = 'conditions' AND column_name = 'match_type'
    ) THEN
      ALTER TABLE public.conditions ADD COLUMN match_type TEXT NOT NULL DEFAULT 'KEYWORD';
    END IF;

    -- effect カラム追加
    IF NOT EXISTS (
      SELECT 1 FROM information_schema.columns
      WHERE table_schema = 'public' AND table_name = 'conditions' AND column_name = 'effect'
    ) THEN
      ALTER TABLE public.conditions ADD COLUMN effect TEXT NOT NULL DEFAULT 'OUTPUT';
    END IF;
  END IF;

  -- テナントスキーマの conditions テーブルにもカラム追加（存在する場合）
  FOR _schema IN
    SELECT nspname FROM pg_namespace WHERE nspname LIKE 'tenant_%'
  LOOP
    IF EXISTS (
      SELECT 1 FROM information_schema.tables
      WHERE table_schema = _schema AND table_name = 'conditions'
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
