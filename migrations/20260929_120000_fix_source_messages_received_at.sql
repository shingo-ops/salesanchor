-- 受信時刻（received_at）を採用本文の投稿時刻（line_posted_at）にそろえ、
-- （is_current の決め直しは 2026-10-13 に外した。下の NEUTRALIZED を参照）
-- 詳細: docs/handoff/fix-received-at-latest/design.md
-- 冪等: 2回目以降は更新0行

-- NEUTRALIZED (ADR-1007 / ADR-155, 2026-11-15): received_at を line_posted_at にそろえる UPDATE を外した。
-- 2026-09-29 の一度きりの直しは終わっている。今はアプリの取り込みが received_at を入れる（backend/app/services/tcg_line_import_svc.py の source_messages への INSERT）。
-- 決定: PO 2026-11-15。分け方: docs/handoff/migration-runner-redesign/p11-classification.md §3 #43
-- 元の内容は git history で参照可能。
DO $$ BEGIN RAISE NOTICE 'ADR-1007 neutralized: received_at realign removed (20260929_120000)'; END $$;

-- NEUTRALIZED (ADR-158 / ADR-155, 2026-10-13): is_current の決め直し（組ごとに1行）を外した。2026-09-29 の一度きりの役目は終わり、今の正本は backend/app/services/tcg_analyzer_svc.py の _merge_supplier_products（同じ投稿の組の行をすべて TRUE）。デプロイのたびに流れて古い決め方に戻していた（#4169 の後 2026-10-12 19:51Z に20組が戻った）。
