-- ADR-1041 便1 設定 v102_kubun_allowed_units 投入の precheck（読み取り）。CAN_PROCEED|1 が出ること（key が無い、または値が {} のときだけ進める）。
SELECT 'TABLE|' || COALESCE(to_regclass('public.tcg_distribution_settings')::text, 'NULL');
SELECT 'CAN_PROCEED|' || CASE WHEN count(*) = 0 THEN 1
                              WHEN count(*) FILTER (WHERE value = '{}') = count(*) THEN 1 ELSE 0 END
  FROM public.tcg_distribution_settings WHERE key = 'v102_kubun_allowed_units';
SELECT 'PRECHECK_DONE';
