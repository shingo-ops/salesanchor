-- 状態マスタに「状態の価値順」の列を足す（構造のみ。値は入れない＝ADR-1007。ADR-1023）
-- public.conditions は view（実テーブルは public.line_conditions）。
-- additive-only: 列の追加・CHECK 制約・コメント・view の再作成のみ。値の INSERT/UPDATE/DELETE は含めない。
-- 空 DB（CI test-run）では line_conditions が無いので何もしない（書き方は 20260925_010000_conditions_add_match_type.sql と同じ考え方）。

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'line_conditions'
    AND table_type = 'BASE TABLE'
  ) THEN
    ALTER TABLE public.line_conditions ADD COLUMN IF NOT EXISTS value_group TEXT;
    ALTER TABLE public.line_conditions ADD COLUMN IF NOT EXISTS value_rank INTEGER;

    IF NOT EXISTS (
      SELECT 1 FROM pg_constraint
      WHERE conname = 'line_conditions_value_group_check'
        AND conrelid = 'public.line_conditions'::regclass
    ) THEN
      ALTER TABLE public.line_conditions
        ADD CONSTRAINT line_conditions_value_group_check
        CHECK (value_group IS NULL OR value_group IN ('box', 'case', 'pack'));
    END IF;

    IF NOT EXISTS (
      SELECT 1 FROM pg_constraint
      WHERE conname = 'line_conditions_value_rank_check'
        AND conrelid = 'public.line_conditions'::regclass
    ) THEN
      ALTER TABLE public.line_conditions
        ADD CONSTRAINT line_conditions_value_rank_check
        CHECK (value_rank IS NULL OR value_rank >= 1);
    END IF;

    COMMENT ON COLUMN public.line_conditions.value_group
      IS '状態の価値の群（box/case/pack）。NULL=価値順の対象外';
    COMMENT ON COLUMN public.line_conditions.value_rank
      IS '群の中の価値の順位。1=価値が高い。複数の状態語が当たったら数字が大きい（価値が低い）状態を採る。ADR-1023';
  END IF;

  -- view を再作成（新しい列を含むように）
  IF EXISTS (
    SELECT 1 FROM information_schema.views
    WHERE table_schema = 'public' AND table_name = 'conditions'
  ) THEN
    CREATE OR REPLACE VIEW public.conditions AS TABLE public.line_conditions;
  END IF;
END $$;
