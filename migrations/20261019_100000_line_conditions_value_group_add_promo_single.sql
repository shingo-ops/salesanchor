-- 状態の価値の群に 'promo_pack'・'single' を許す（構造のみ。値は入れない＝ADR-1007。ADR-1031）
-- public.conditions は view（実テーブルは public.line_conditions）。CHECK の作り直しだけで、view の再作成は要らない。
-- additive-only: 許す値を広げるだけ。既存の行は変わらない（既存の値 box/case/pack と NULL はそのまま通る）。
-- 空 DB（CI test-run）では line_conditions が無いので何もしない（20261017_120000_line_conditions_value_rank.sql と同じ考え方）。
--
-- 戻し方（downgrade。流すのは PO。promo_pack・single の行が残っていると失敗するので、先に行を消すか value_group を NULL にする）:
--   ALTER TABLE public.line_conditions DROP CONSTRAINT IF EXISTS line_conditions_value_group_check;
--   ALTER TABLE public.line_conditions ADD CONSTRAINT line_conditions_value_group_check
--     CHECK (value_group IS NULL OR value_group IN ('box', 'case', 'pack'));

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'line_conditions'
    AND table_type = 'BASE TABLE'
  ) AND EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'line_conditions' AND column_name = 'value_group'
  ) THEN
    ALTER TABLE public.line_conditions DROP CONSTRAINT IF EXISTS line_conditions_value_group_check;
    ALTER TABLE public.line_conditions
      ADD CONSTRAINT line_conditions_value_group_check
      CHECK (value_group IS NULL OR value_group IN ('box', 'case', 'pack', 'promo_pack', 'single'));

    COMMENT ON COLUMN public.line_conditions.value_group
      IS '状態の価値の群（box/case/pack/promo_pack/single）。NULL=価値順の対象外。promo_pack・single は v102 のシングル系・プロモパック系だけが読む（ADR-1031）';
  END IF;
END $$;
