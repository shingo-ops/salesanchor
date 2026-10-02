-- 目的: Discord 在庫取り込み機能（2026-10-02 PR #3932 でアプリケーションコード削除済み）の
--   残置テーブル3件（discord_inbound_messages / discord_webhook_idempotency / parse_logs）と
--   それらに依存するビュー（v_supplier_parse_stats）を削除する。
--
-- 設計: docs/handoff/drop-discord-inventory-tables/design.md
-- PO 決定: 2026-10-02（しんごさん）
--
-- 不可逆。適用には PO 本人の GO #番号 が必要（ADR-136、ADR-1003 の例外）。
--
-- 事前確認済み事実:
--   - FK: pg_constraint の confrelid 走査で、この3テーブルを参照する外部キーは0件。
--   - 依存オブジェクト: public.v_supplier_parse_stats ビューのみ（parse_logs 上に定義）。
--     本マイグレーションで先に DROP VIEW する。
--   - アプリケーションコード: backend/app/services/inventory_drift_detector.py が
--     v_supplier_parse_stats を参照していたが、呼び出し元が存在しない（dead code）ことを
--     repo 全体 grep で確認済みのため、本PRで同ファイルも削除する（git rm、本SQLとは別ファイル）。
--
-- バックアップ（PO 保管・ローカル、本リポジトリにはコミットしない）:
--   ~/salesanchor-db-backups/discord_inbound_messages_backup_20261002.csv （129件）
--   ~/salesanchor-db-backups/discord_webhook_idempotency_backup_20261002.csv （111件）
--   ~/salesanchor-db-backups/parse_logs_backup_20261002.csv （0件）
--   ~/salesanchor-db-backups/discord_inventory_tables_schema_20261002.sql
--     （pg_dump --schema-only、3テーブル + ビュー）
--
-- 冪等: IF EXISTS を使用。CASCADE は使わない（想定外の連鎖削除を防ぐ）。

DROP VIEW IF EXISTS public.v_supplier_parse_stats;
DROP TABLE IF EXISTS public.parse_logs;
DROP TABLE IF EXISTS public.discord_webhook_idempotency;
DROP TABLE IF EXISTS public.discord_inbound_messages;
