-- ADR-1041 便1 設定 v102_kubun_allowed_units の verify（読み取り）。MATCH|1 が出ること（値が設計の JSON と一字一句一致）。戻した後は EMPTY|1。
SELECT 'MATCH|' || count(*) FROM public.tcg_distribution_settings
 WHERE key = 'v102_kubun_allowed_units'
   AND value = '{"箱系": ["Box", "Case", "Pack", "MasterCarton"], "プロモパック系": ["Booklet", "Pack"], "ブックレット系": ["Booklet"]}';
SELECT 'EMPTY|' || count(*) FROM public.tcg_distribution_settings WHERE key = 'v102_kubun_allowed_units' AND value = '{}';
SELECT 'VERIFY_DONE';
