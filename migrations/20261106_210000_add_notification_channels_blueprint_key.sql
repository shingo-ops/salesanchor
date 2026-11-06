-- discord-server-management 第2段 2c: 知らせの送り先に「設計図の部屋の key」の列を足す（作るだけ・冪等）
--
-- 設計: docs/handoff/discord-server-management/design.md S2-3 D2-4・D2-11・S2-5
-- 中身（各テナントのスキーマ・notification_channels がある所だけ）:
--   notification_channels.blueprint_key   設計図の知らせの部屋の key（例 assign_notice）。NULL は手で作った行
--   uq_notification_channels_blueprint_key   NULL でない値は 1 つだけ（1 部屋 1 行・二重作成の防止）
-- ADR-155: 構造変更のみ。値は入れない。行を入れるのは自社サーバーの反映（backend/app/routers/discord_own_server.py）。
-- 新しい会社のスキーマ（backend/app/services/tenant.py）には今も notification_channels が無い（今からある抜け・この移行の対象外）。
-- ロック待ち: run_all_migrations.sh の run_sql が PGOPTIONS で lock_timeout を付ける（既定 1s・ADR-1037）。
--
-- ロールバック（この順・各テナント）:
--   DROP INDEX IF EXISTS <tenant>.uq_notification_channels_blueprint_key;
--   ALTER TABLE <tenant>.notification_channels DROP COLUMN IF EXISTS blueprint_key;

DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN
        SELECT nspname FROM pg_namespace
        WHERE nspname ~ '^tenant_[0-9]+$'
        ORDER BY nspname
    LOOP
        -- notification_channels テーブルが存在するスキーマのみ対象
        IF NOT EXISTS (
            SELECT 1 FROM pg_tables
            WHERE schemaname = r.nspname AND tablename = 'notification_channels'
        ) THEN
            CONTINUE;
        END IF;

        EXECUTE format(
            'ALTER TABLE %I.notification_channels ADD COLUMN IF NOT EXISTS blueprint_key TEXT',
            r.nspname
        );
        EXECUTE format(
            'CREATE UNIQUE INDEX IF NOT EXISTS uq_notification_channels_blueprint_key ON %I.notification_channels (blueprint_key) WHERE blueprint_key IS NOT NULL',
            r.nspname
        );
        EXECUTE format('COMMENT ON COLUMN %I.notification_channels.blueprint_key IS %L', r.nspname,
            '設計図の知らせの部屋の key（自社サーバーの反映が作った行だけ。NULL は手で作った行）');
    END LOOP;
END $$;
