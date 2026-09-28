-- Migration: Delete ALL skip_condition rules (全13件を廃止)
-- 根拠: docs/handoff/gemini-extract-role-split/design.md §10〜§12（PR-A側）
-- PO承認（範囲拡大）: 2026-09-28 チャット
--   当初は完売・サーチ済み系6件（ID 21〜26）のみの承認だったが、
--   その後「skip_condition カテゴリ全体を廃止してよい」と PO が範囲を拡大承認。
--   本番実測時点（2026-09-28）で skip_condition は exact 3件 + substring 10件 = 13件。
-- 冪等: id ではなく category で指定する（環境によって id が異なるため）。
-- 参照整合性: supplier_knowledge_links.knowledge_rule_id は ON DELETE CASCADE
--   （migrations/20260924_050000_create_supplier_knowledge_links.sql）のため、
--   この DELETE で紐付けレコードも連動して削除される。
DELETE FROM public.knowledge_rules
WHERE category = 'skip_condition';
