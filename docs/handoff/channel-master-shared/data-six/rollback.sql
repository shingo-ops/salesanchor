-- 共用6行の投入 rollback（PR-B を戻した後だけ流す）。設計 design.md §6「戻し方」。
-- app.is_operator を置かないと FORCE RLS で1件も消えない。
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL app.is_operator = 'true';
DELETE FROM public.channel_masters WHERE tenant_id IS NULL;
SELECT 1 / (CASE WHEN (SELECT count(*) FROM public.channel_masters WHERE tenant_id IS NULL)=0 THEN 1 ELSE 0 END) AS shared_removed;
COMMIT;
