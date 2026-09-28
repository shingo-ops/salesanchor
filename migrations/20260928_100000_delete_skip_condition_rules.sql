-- Migration: Delete ALL skip_condition rules (全13件を廃止)
-- 根拠: docs/handoff/gemini-extract-role-split/design.md（PR #3825 で追加）
-- 理由（PO決定 2026-09-28）:
--   skip_condition は Gemini への指示文に入り、Gemini に商品ブロックを捨てる判断をさせていた。
--   PO 方針（2026-09-28）: Gemini は原文の書き写しのみ・判断はシステム。完売・サーチ済み等は
--   システム側の解析ルール（conditions CN0007/CN0010、tcg_status_master ST0011〜ST0013）で
--   扱うため、skip_condition は全件廃止。
--   （本番実測時点で skip_condition は exact 3件 + substring 10件 = 13件、全件対象）
-- 冪等: id ではなく category で指定する（環境によって id が異なるため）。
-- 参照整合性: supplier_knowledge_links.knowledge_rule_id は ON DELETE CASCADE
--   （migrations/20260924_050000_create_supplier_knowledge_links.sql）のため、
--   この DELETE で紐付けレコードも連動して削除される。
DELETE FROM public.knowledge_rules
WHERE category = 'skip_condition';
