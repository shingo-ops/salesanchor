-- Migration: Delete ALL skip_condition rules (全13件を廃止)
-- 根拠: docs/handoff/gemini-extract-role-split/design.md §10〜§12（PR-A側）
-- PO決定 2026-09-28 チャット:
--   「完売・サーチ済みの6件は削除して良い」＋「残りの読み飛ばしルール7件→廃止」
--   （本番実測時点で skip_condition は exact 3件 + substring 10件 = 13件、全件対象）
-- 冪等: id ではなく category で指定する（環境によって id が異なるため）。
-- 参照整合性: supplier_knowledge_links.knowledge_rule_id は ON DELETE CASCADE
--   （migrations/20260924_050000_create_supplier_knowledge_links.sql）のため、
--   この DELETE で紐付けレコードも連動して削除される。
DELETE FROM public.knowledge_rules
WHERE category = 'skip_condition';
