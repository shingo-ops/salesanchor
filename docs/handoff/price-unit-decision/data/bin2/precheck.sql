-- 価格で単位を決める 便2 設定 unit_buyback_pack_max 追加の precheck（読み取り）。ADR-1036。key がまだ無く、unit_buyback_box_min が 0.5 なら CHECK_OK。違えば止める。
\set ON_ERROR_STOP on
SELECT 'TABLE|' || COALESCE(to_regclass('public.tcg_distribution_settings')::text, 'NULL');
SELECT 'CURRENT|' || key || '|' || value || '|' || note FROM public.tcg_distribution_settings WHERE key IN ('unit_buyback_pack_max', 'unit_buyback_box_min') ORDER BY key;
SELECT CASE WHEN count(*) = 0 THEN 'CHECK_OK pack_max_absent' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.tcg_distribution_settings WHERE key = 'unit_buyback_pack_max';
SELECT CASE WHEN count(*) = 1 THEN 'CHECK_OK box_min_0.5' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.tcg_distribution_settings WHERE key = 'unit_buyback_box_min' AND value = '0.5';
SELECT 'PRECHECK_DONE';
