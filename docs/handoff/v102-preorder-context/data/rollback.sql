-- 便PO: 予約の手がかりの規則（候補6行）。設計 docs/handoff/v102-preorder-context/card-PO.md 1-4。
-- rollback（行は消さず enabled を false にする）。
BEGIN;
UPDATE public.tcg_status_master SET enabled = FALSE, updated_at = NOW()
WHERE note LIKE 'v102-preorder-context:%' AND tenant_id IS NULL;
SELECT 1 / (CASE WHEN COUNT(*) = 6 THEN 1 ELSE 0 END) AS disabled_must_be_six
FROM public.tcg_status_master WHERE note LIKE 'v102-preorder-context:%' AND tenant_id IS NULL AND NOT enabled;
COMMIT;
