-- 便PO: 予約の手がかりの規則（候補6行）。設計 docs/handoff/v102-preorder-context/card-PO.md 1-4。
-- precheck（読み取りだけ）。新しい effect の行が既にあれば、ゼロ除算で失敗して止まる。
SELECT 1 / (CASE WHEN COUNT(*) = 0 THEN 1 ELSE 0 END) AS context_rows_must_be_zero
FROM public.tcg_status_master WHERE effect IN ('HEADING', 'DATE_AHEAD', 'RELEASE_AHEAD');
SELECT 1 / (CASE WHEN COUNT(*) = 0 THEN 1 ELSE 0 END) AS marker_rows_must_be_zero
FROM public.tcg_status_master WHERE note LIKE 'v102-preorder-context:%';
SELECT 1 / (CASE WHEN COUNT(*) >= 1 THEN 1 ELSE 0 END) AS default_row_must_exist
FROM public.tcg_status_master WHERE tenant_id IS NULL AND enabled AND match_type = 'DEFAULT' AND canonical = 'In Stock';
SELECT COUNT(*) AS rows_now, MAX(status_id) AS max_status_id FROM public.tcg_status_master WHERE status_id SIMILAR TO 'ST[0-9]+';
SELECT status_id, canonical, effect, match_type, priority, enabled FROM public.tcg_status_master WHERE tenant_id IS NULL ORDER BY effect, priority;
