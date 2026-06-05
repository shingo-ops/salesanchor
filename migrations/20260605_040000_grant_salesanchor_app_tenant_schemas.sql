-- SA-18: 既存 tenant_NNN スキーマ全件に salesanchor_app を付与
-- 冪等（GRANT は重複を無視する）

DO $$
DECLARE r RECORD;
BEGIN
  FOR r IN
    SELECT nspname FROM pg_namespace
    WHERE nspname ~ '^tenant_[0-9]+$'
    ORDER BY nspname
  LOOP
    EXECUTE format(
      'GRANT USAGE ON SCHEMA %I TO salesanchor_app', r.nspname);
    EXECUTE format(
      'GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA %I TO salesanchor_app',
      r.nspname);
    EXECUTE format(
      'GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA %I TO salesanchor_app',
      r.nspname);
    -- 将来テーブルも自動付与（テーブル所有者 = jarvis）
    EXECUTE format(
      'ALTER DEFAULT PRIVILEGES FOR ROLE jarvis IN SCHEMA %I GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO salesanchor_app',
      r.nspname);
    EXECUTE format(
      'ALTER DEFAULT PRIVILEGES FOR ROLE jarvis IN SCHEMA %I GRANT USAGE, SELECT ON SEQUENCES TO salesanchor_app',
      r.nspname);
    RAISE NOTICE 'Granted salesanchor_app on schema: %', r.nspname;
  END LOOP;
END $$;
