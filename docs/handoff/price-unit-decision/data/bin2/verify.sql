-- 価格で単位を決める 便2 設定の verify（読み取り）。unit_buyback_pack_max|0.2 の 1 行が出ること。
SELECT key || '|' || value || '|' || note FROM public.tcg_distribution_settings WHERE key = 'unit_buyback_pack_max';
SELECT CASE WHEN count(*) = 1 THEN 'VERIFY_OK 1x0.2' ELSE (1 / (count(*) - count(*)))::text END
  FROM public.tcg_distribution_settings WHERE key = 'unit_buyback_pack_max' AND value = '0.2';
SELECT 'VERIFY_DONE';
