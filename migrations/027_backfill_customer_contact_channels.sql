-- Phase 1-B-1 / Migration 027: customers.primary_contact_channel から contact_channels を backfill
--
-- 背景:
--   migration 026 で customer_contact_channels テーブルを作成した。
--   既存の customers.primary_contact_channel 値を新テーブルに移す。
--   値が null でなく contact_channels に同一 channel がまだ無い顧客のみ処理。
--
-- 冪等性:
--   WHERE NOT EXISTS で既に行がある場合はスキップ。再実行 no-op。
--
-- 変更履歴:
--   2026-04-23: 初版作成

-- NEUTRALIZED (ADR-1007 / ADR-155, 2026-11-15): 連絡手段の写し（customers.primary_contact_channel と customer_discord から customer_contact_channels への INSERT 2つ）を外した。
-- 2026-04-23 の一度きりの役目は終わっている。毎回の本番反映で、消した連絡手段の行が戻っていた。
-- 決定: PO 2026-11-15。分け方: docs/handoff/migration-runner-redesign/p11-classification.md §3 #1
-- 元の内容は git history で参照可能。
DO $$ BEGIN RAISE NOTICE 'ADR-1007 neutralized: contact channel backfill removed (027)'; END $$;
