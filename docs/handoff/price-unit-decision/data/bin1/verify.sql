-- 価格で単位を決める 便1 設定の verify（読み取り）。unit_buyback_max_age_days|30 の 1 行が出ること。
SELECT key || '|' || value || '|' || note FROM public.tcg_distribution_settings WHERE key = 'unit_buyback_max_age_days';
SELECT 'VERIFY_DONE';
