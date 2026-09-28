-- Migration: Delete skip_condition rules that Gemini already judges (完売・サーチ済み系 6件)
-- 根拠: docs/handoff/gemini-extract-role-split/design.md §10〜§12（PR-A側）
-- PO承認: 2026-09-28 チャット「完売・サーチ済みの6件（ID 21〜26）は削除して良い」
-- 冪等: id ではなく category + pattern で指定する（環境によって id が異なるため）
-- 参照整合性: supplier_knowledge_links.knowledge_rule_id は ON DELETE CASCADE
--   （migrations/20260924_050000_create_supplier_knowledge_links.sql）のため、
--   この DELETE で紐付けレコードも連動して削除される。
DELETE FROM public.knowledge_rules
WHERE category = 'skip_condition'
  AND pattern IN ('[サーチ済み]', '[サーチ済]', 'サーチ済', '完売しました', '売り切れ', '売切');
