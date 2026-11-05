-- discord-server-management 第2段 2a-1: アプリの役割と Discord のロールをつなぐ列と、消した番号を覚える表 2 つを作る（作るだけ・冪等）
--
-- 設計: docs/handoff/discord-server-management/design.md S2-3 D2-1・D2-3・S2-5
-- 中身（各テナントのスキーマ）:
--   roles.discord_role_id     アプリの役割につながる Discord のロールの番号（NULL 可。NULL でない値はテナント内で一意）
--   discord_retired_roles     消したアプリの役割の Discord のロールの番号（点検がこの番号のロールを登録した人から外すため）
--   discord_retired_members   消した・番号を変えたスタッフの元の Discord の番号（kick=true は自社サーバーから外す）
-- ADR-155: 構造変更のみ。値は入れない。行を入れる処理は 2a-2・2b で足す。
-- GRANT は ALTER DEFAULT PRIVILEGES（20260605_040000）で自動付与される。
-- 新しい会社のスキーマは backend/app/services/tenant.py の _TENANT_TABLES_SQL で同じ形に作る。
-- ロック待ち: run_all_migrations.sh の run_sql が PGOPTIONS で lock_timeout を付ける（既定 1s・ADR-1037）。
--
-- ロールバック（この順・各テナント）:
--   DROP TABLE IF EXISTS <tenant>.discord_retired_members;
--   DROP TABLE IF EXISTS <tenant>.discord_retired_roles;
--   DROP INDEX IF EXISTS <tenant>.uq_roles_discord_role_id;
--   ALTER TABLE <tenant>.roles DROP COLUMN IF EXISTS discord_role_id;

DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN
        SELECT nspname FROM pg_namespace
        WHERE nspname ~ '^tenant_[0-9]+$'
        ORDER BY nspname
    LOOP
        -- roles テーブルが存在するスキーマのみ対象（20261005_150000 と同じ）
        IF NOT EXISTS (
            SELECT 1 FROM pg_tables
            WHERE schemaname = r.nspname AND tablename = 'roles'
        ) THEN
            CONTINUE;
        END IF;

        EXECUTE format(
            'ALTER TABLE %I.roles ADD COLUMN IF NOT EXISTS discord_role_id TEXT',
            r.nspname
        );
        EXECUTE format(
            'CREATE UNIQUE INDEX IF NOT EXISTS uq_roles_discord_role_id ON %I.roles (discord_role_id) WHERE discord_role_id IS NOT NULL',
            r.nspname
        );
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS %I.discord_retired_roles (
                discord_role_id TEXT PRIMARY KEY,
                retired_at      TIMESTAMPTZ NOT NULL DEFAULT now()
            )',
            r.nspname
        );
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS %I.discord_retired_members (
                discord_user_id TEXT PRIMARY KEY,
                kick            BOOLEAN NOT NULL,
                retired_at      TIMESTAMPTZ NOT NULL DEFAULT now()
            )',
            r.nspname
        );
        EXECUTE format('COMMENT ON COLUMN %I.roles.discord_role_id IS %L', r.nspname,
            'つながる Discord のロールの番号（自社サーバー。NULL はまだつないでいない）');
        EXECUTE format('COMMENT ON TABLE %I.discord_retired_roles IS %L', r.nspname,
            '消したアプリの役割の Discord のロールの番号。点検が登録した人から外す');
        EXECUTE format('COMMENT ON TABLE %I.discord_retired_members IS %L', r.nspname,
            '消した・番号を変えたスタッフの元の Discord の番号。点検がロールを外し、kick=true なら自社サーバーから外す');
        EXECUTE format('COMMENT ON COLUMN %I.discord_retired_members.kick IS %L', r.nspname,
            'true = スタッフを消した（自社サーバーから外す）。false = 番号を変えた（ロールだけ外す）');
        EXECUTE format('COMMENT ON COLUMN %I.discord_retired_roles.discord_role_id IS %L', r.nspname,
            '消したアプリの役割につながっていた Discord のロールの番号');
        EXECUTE format('COMMENT ON COLUMN %I.discord_retired_roles.retired_at IS %L', r.nspname,
            'この番号を覚えた日時');
        EXECUTE format('COMMENT ON COLUMN %I.discord_retired_members.discord_user_id IS %L', r.nspname,
            '消した・番号を変えたスタッフの元の Discord の番号');
        EXECUTE format('COMMENT ON COLUMN %I.discord_retired_members.retired_at IS %L', r.nspname,
            'この番号を覚えた日時');
        RAISE NOTICE 'discord role link tables created/verified for schema: %', r.nspname;
    END LOOP;
END $$;
