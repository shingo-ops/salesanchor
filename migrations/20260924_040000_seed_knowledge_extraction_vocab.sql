-- Migration: Seed knowledge extraction vocab (block_delimiter / status_keyword)
-- 冪等: WHERE NOT EXISTS で既存レコードと衝突しない
-- 注: skip_condition の INSERT は PR #3823（2026-09-28 PO決定。設計根拠は PR #3825）で削除済み。詳細は本ファイル下部のコメント参照。

-- NEUTRALIZED (ADR-1007 / ADR-155, 2026-10-07): block_delimiter 17 語の seed を外した。

-- スキップ条件（skip_condition）の INSERT は削除済み。
-- 理由（PO決定 2026-09-28）: skip_condition は Gemini への指示文に入り、Gemini に商品ブロックを
-- 捨てる判断をさせていた。PO 方針（2026-09-28）: Gemini は原文の書き写しのみ・判断はシステム。
-- 完売・サーチ済み等はシステム側の解析ルール（conditions CN0007/CN0010、tcg_status_master
-- ST0011〜ST0013）で扱うため、skip_condition は全件廃止。
-- 削除は migrations/20260928_100000_delete_skip_condition_rules.sql（PR #3823）で実施。
-- この INSERT ブロックを残したままだと、run_all_migrations.sh の全件再実行のたびに
-- WHERE NOT EXISTS で再挿入 → 上記 delete migration が再度削除、を繰り返すため、
-- 再挿入源を止める目的でここを削除した（block_delimiter / status_keyword は変更なし）。

-- NEUTRALIZED (ADR-1007 / ADR-155, 2026-10-07):
-- status_keyword 4 語の seed を外した。knowledge_rules は画面／CSV で管理する。
-- 元の内容は git history で参照可能。
DO $$ BEGIN RAISE NOTICE 'ADR-1007 neutralized: knowledge vocab seed removed'; END $$;
