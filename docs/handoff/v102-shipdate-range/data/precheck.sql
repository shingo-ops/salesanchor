-- 便2: tcg_status_master id25（DATE_AHEAD）の範囲日付対応。設計 docs/handoff/v102-shipdate-range/design.md §5。
-- precheck（読み取りだけ）。id25 が「前」の文字列と一致しなければゼロ除算で止まる。DATE_AHEAD の有効行は 3 行。
SELECT 1 / (CASE WHEN COUNT(*) = 1 THEN 1 ELSE 0 END) AS id25_must_match_before FROM public.tcg_status_master WHERE id = 25 AND search_pattern = '(?P<m>\d{1,2})/(?P<d>\d{1,2})[^0-9]{0,4}(?:入荷|発送|発売)' AND effect = 'DATE_AHEAD' AND enabled;
SELECT 1 / (CASE WHEN COUNT(*) = 3 THEN 1 ELSE 0 END) AS date_ahead_enabled_must_be_three FROM public.tcg_status_master WHERE effect = 'DATE_AHEAD' AND enabled;
SELECT id, effect, enabled, priority, note, updated_at, search_pattern FROM public.tcg_status_master WHERE effect = 'DATE_AHEAD' ORDER BY priority;
