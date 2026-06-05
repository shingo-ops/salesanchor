-- SA-18: salesanchor_app（最小権限ロール）作成＋public スキーマ付与
-- パスワードは deploy bootstrap ステップで ALTER ROLE ... PASSWORD で注入（SQL に書かない）
-- 冪等（何度でも安全に実行可能）

DO $$ BEGIN
  CREATE ROLE salesanchor_app
    LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE;
EXCEPTION WHEN duplicate_object THEN
  RAISE NOTICE 'salesanchor_app already exists, skipping CREATE';
END $$;

GRANT CONNECT ON DATABASE jarvis_db TO salesanchor_app;

-- public スキーマ: 既存テーブル + 将来テーブル
GRANT USAGE ON SCHEMA public TO salesanchor_app;
GRANT SELECT, INSERT, UPDATE, DELETE
  ON ALL TABLES IN SCHEMA public TO salesanchor_app;
GRANT USAGE, SELECT
  ON ALL SEQUENCES IN SCHEMA public TO salesanchor_app;
-- 将来 jarvis が作るテーブルも自動付与（テーブル所有者 = jarvis）
ALTER DEFAULT PRIVILEGES FOR ROLE jarvis IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO salesanchor_app;
ALTER DEFAULT PRIVILEGES FOR ROLE jarvis IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO salesanchor_app;
