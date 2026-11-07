-- ADR-1041 見出し 設定 v102_condition_heading の verify（読み取り）。MATCH|1 が出ること（値が設計の JSON と一字一句一致）。戻した後は EMPTY|1。
SELECT 'MATCH|' || count(*) FROM public.tcg_distribution_settings
 WHERE key = 'v102_condition_heading'
   AND value = '{"max_lines": 3, "sentence_end": ["。", "ます", "ません", "ございます", "おります", "です", "下さい", "ください"], "trailing_chars": "!！。"}';
SELECT 'EMPTY|' || count(*) FROM public.tcg_distribution_settings WHERE key = 'v102_condition_heading' AND value = '{}';
SELECT 'VERIFY_DONE';
