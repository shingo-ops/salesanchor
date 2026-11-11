-- ADR-1073 便4 設定 v102_shime_box_all_states の verify（読み取り）。MATCH|1・ROWS|1 が出ること（値が設計 §3-2 の JSON と一字一句一致）。戻した後は MATCH|0・ROWS|0。
SELECT 'MATCH|' || count(*) FROM public.tcg_distribution_settings
 WHERE key = 'v102_shime_box_all_states'
   AND value = '{"keep_words": ["まだあります"]}';
SELECT 'ROWS|' || count(*) FROM public.tcg_distribution_settings WHERE key = 'v102_shime_box_all_states';
SELECT 'VERIFY_DONE';
