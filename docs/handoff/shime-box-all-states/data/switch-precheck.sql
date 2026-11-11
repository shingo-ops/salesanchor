-- ADR-1073 便4 設定 v102_shime_box_all_states 投入の precheck（読み取り）。CAN_PROCEED|1 が出ること（key がまだ無いときだけ進める）。
-- BOX|5 は箱の仲間（value_group = 'box' で有効・value_rank あり）が便3 と同じ 5 つであること。
SELECT 'TABLE|' || COALESCE(to_regclass('public.tcg_distribution_settings')::text, 'NULL');
SELECT 'CAN_PROCEED|' || CASE WHEN count(*) = 0 THEN 1 ELSE 0 END
  FROM public.tcg_distribution_settings WHERE key = 'v102_shime_box_all_states';
SELECT 'BOX|' || count(*) FROM public.conditions WHERE is_active = TRUE AND value_group = 'box' AND value_rank IS NOT NULL;
SELECT 'PRECHECK_DONE';
