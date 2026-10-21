-- 便2: tcg_status_master id25（DATE_AHEAD）の範囲日付対応。設計 docs/handoff/v102-shipdate-range/design.md §5。
-- commit（PO の GO 後だけ）。1 行でなければゼロ除算で失敗し、COMMIT に届かない。
BEGIN;
UPDATE public.tcg_status_master SET search_pattern = '(?:\d{1,2}/\d{1,2}[～〜~\-－](?=\d{1,2}/))?(?P<m>\d{1,2})/(?:\d{1,2}[～〜~\-－])?(?P<d>\d{1,2})[^0-9]{0,4}(?:入荷|発送|発売)', note = 'v102-shipdate-range:1', updated_at = NOW()
WHERE id = 25 AND search_pattern = '(?P<m>\d{1,2})/(?P<d>\d{1,2})[^0-9]{0,4}(?:入荷|発送|発売)';
SELECT 1 / (CASE WHEN COUNT(*) = 1 THEN 1 ELSE 0 END) AS updated_must_be_one FROM public.tcg_status_master WHERE id = 25 AND search_pattern = '(?:\d{1,2}/\d{1,2}[～〜~\-－](?=\d{1,2}/))?(?P<m>\d{1,2})/(?:\d{1,2}[～〜~\-－])?(?P<d>\d{1,2})[^0-9]{0,4}(?:入荷|発送|発売)' AND note = 'v102-shipdate-range:1';
COMMIT;
