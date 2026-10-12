-- Phase 1 再設計 / Migration 024: staff / bots 用 CRUD 権限を追加
--
-- 内容:
--   public.permissions に staff.*（4件）と bots.*（4件）の CRUD 粒度権限を追加。
--   既存 permissions（CRUD粒度 73件 + menu.* 19件）と共存する。
--
-- 冪等性:
--   INSERT ... ON CONFLICT (key) DO NOTHING で再実行しても副作用なし。
--
-- 実行方法:
--   docker exec -i astro-webapp-postgres-1 psql -U jarvis -d jarvis_db \
--     -v ON_ERROR_STOP=1 < migrations/024_add_staff_bots_permissions.sql
--
-- 変更履歴:
--   2026-04-23: 初版作成

--
-- NEUTRALIZED (ADR-1007 / ADR-155, 2026-10-07):
-- 商品マスタ・権限などの値はアプリ画面/CSVで管理する。migrationは構造変更のみ。
-- staff.* / bots.* 8 キーの INSERT を外した（本番には既にある）。
-- 元の内容は git history で参照可能。
--

DO $$ BEGIN RAISE NOTICE 'migration 024 neutralized (ADR-1007 / ADR-155): permission keys already exist; not added by migration'; END $$;
