-- 価格で単位を決める 便1 設定 unit_buyback_max_age_days 7→30 の precheck（読み取り）。ADR-1036。今は 7 で、行が 1 行だけなら CHECK_OK。違えば止める。
\set ON_ERROR_STOP on
SELECT 'TABLE|' || COALESCE(to_regclass('public.tcg_distribution_settings')::text, 'NULL');
SELECT 'CURRENT|' || key || '|' || value || '|' || note FROM public.tcg_distribution_settings WHERE key = 'unit_buyback_max_age_days';
SELECT CASE WHEN count(*) = 1 THEN 'CHECK_OK 7x1' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.tcg_distribution_settings WHERE key = 'unit_buyback_max_age_days' AND value = '7';
SELECT CASE WHEN count(*) = 1 THEN 'ROWS_OK 1' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.tcg_distribution_settings WHERE key = 'unit_buyback_max_age_days';
SELECT 'PRECHECK_DONE';
