-- 受信時刻（received_at）を採用本文の投稿時刻（line_posted_at）にそろえ、
-- （is_current の決め直しは 2026-10-13 に外した。下の NEUTRALIZED を参照）
-- 詳細: docs/handoff/fix-received-at-latest/design.md
-- 冪等: 2回目以降は更新0行

UPDATE public.source_messages
   SET received_at = line_posted_at
 WHERE line_posted_at IS NOT NULL
   AND received_at IS DISTINCT FROM line_posted_at;

-- NEUTRALIZED (ADR-158 / ADR-155, 2026-10-13): is_current の決め直し（組ごとに1行）を外した。2026-09-29 の一度きりの役目は終わり、今の正本は backend/app/services/tcg_analyzer_svc.py の _merge_supplier_products（同じ投稿の組の行をすべて TRUE）。デプロイのたびに流れて古い決め方に戻していた（#4169 の後 2026-10-12 19:51Z に20組が戻った）。
