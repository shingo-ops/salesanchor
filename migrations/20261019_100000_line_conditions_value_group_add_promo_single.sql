-- 状態の価値の群に 'promo_pack'・'single' を許す（構造のみ。値は入れない＝ADR-1007。ADR-1031）
-- public.conditions は view（実テーブルは public.line_conditions）。CHECK の作り直しだけで、view の再作成は要らない。
-- additive-only: 許す値を広げるだけ。既存の行は変わらない（既存の値 box/case/pack と NULL はそのまま通る）。
-- 空 DB（CI test-run）では line_conditions が無いので何もしない（20261017_120000_line_conditions_value_rank.sql と同じ考え方）。
-- 再実行ガード: run_all_migrations.sh は毎回全 migration を流すため、後の migration が広げた制約を狭め直さないよう
-- 現在の制約定義を見て、すでに目的の値を含むなら何もしない（deploy 39356908634・39359118758 失敗の復旧）。
--
-- 戻し方（downgrade。流すのは PO。promo_pack・single の行が残っていると失敗するので、先に行を消すか value_group を NULL にする）:
--   ALTER TABLE public.line_conditions DROP CONSTRAINT IF EXISTS line_conditions_value_group_check;
--   ALTER TABLE public.line_conditions ADD CONSTRAINT line_conditions_value_group_check
--     CHECK (value_group IS NULL OR value_group IN ('box', 'case', 'pack'));
-- guard（流し直し対策）: deploy は全 migration を毎回先頭から流し直す。後の migration で広げた値（例: booklet）の行が既にあると、
-- 無条件の DROP→ADD で古い CHECK を付け直した時点で violated by some row になり deploy が落ちる。そのため既に 'promo_pack' を許す定義なら流さない。

DO $$
DECLARE
  existing_def TEXT;
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'line_conditions'
    AND table_type = 'BASE TABLE'
  ) AND EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'line_conditions' AND column_name = 'value_group'
  ) AND NOT EXISTS (
    -- 既に 'promo_pack' を許す形に広がっていれば何もしない（冪等性。20260613_040000_funnel_goals_kpi_extend.sql と同じ考え方）
    SELECT 1
    FROM pg_constraint c
    JOIN pg_class t ON t.oid = c.conrelid
    JOIN pg_namespace n ON n.oid = t.relnamespace
    WHERE n.nspname = 'public'
      AND t.relname = 'line_conditions'
      AND c.conname = 'line_conditions_value_group_check'
      AND pg_get_constraintdef(c.oid) LIKE '%promo_pack%'
  ) THEN
    SELECT pg_get_constraintdef(con.oid) INTO existing_def
    FROM pg_constraint con
    WHERE con.conrelid = 'public.line_conditions'::regclass
      AND con.conname = 'line_conditions_value_group_check';

    IF existing_def IS NOT NULL AND existing_def LIKE '%''promo_pack''%' AND existing_def LIKE '%''single''%' THEN
      RAISE NOTICE 'migration 20261019_100000: line_conditions_value_group_check は既に promo_pack・single を含む、skip';
    ELSE
      ALTER TABLE public.line_conditions DROP CONSTRAINT IF EXISTS line_conditions_value_group_check;
      ALTER TABLE public.line_conditions
        ADD CONSTRAINT line_conditions_value_group_check
        CHECK (value_group IS NULL OR value_group IN ('box', 'case', 'pack', 'promo_pack', 'single'));

      COMMENT ON COLUMN public.line_conditions.value_group
        IS '状態の価値の群（box/case/pack/promo_pack/single）。NULL=価値順の対象外。promo_pack・single は v102 のシングル系・プロモパック系だけが読む（ADR-1031）';
    END IF;
  END IF;
END $$;
