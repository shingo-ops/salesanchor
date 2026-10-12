-- 便PO: 予約の手がかりの規則（候補6行）。設計 docs/handoff/v102-preorder-context/card-PO.md 1-4。
-- verify（読み取りだけ）。6 行・すべて有効・中央のマスタ（tenant_id が空）であること。
SELECT 1 / (CASE WHEN COUNT(*) = 6 THEN 1 ELSE 0 END) AS inserted_must_be_six
FROM public.tcg_status_master WHERE note LIKE 'v102-preorder-context:%' AND tenant_id IS NULL;
SELECT 1 / (CASE WHEN COUNT(*) = 6 THEN 1 ELSE 0 END) AS enabled_must_be_six
FROM public.tcg_status_master WHERE note LIKE 'v102-preorder-context:%' AND enabled;
SELECT status_id, canonical, effect, match_type, priority, enabled, search_pattern, exclude_pattern
FROM public.tcg_status_master WHERE note LIKE 'v102-preorder-context:%' ORDER BY status_id;
