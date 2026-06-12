-- SA-04: company_discord に guild_id を追加
--
-- 背景:
--   SA-04 recon で判明した不足点:
--   company_discord テーブルに guild_id 列がなく、会社レベルの
--   Discord リンク生成時に guild_id の取得経路が不完全だった。
--
--   contact_channel_links.py:82-87 で Discord URL を生成する際、
--   company_discord.guild_id から取得できるようにする。
--
-- 設計:
--   - 全テナントスキーマに ADD COLUMN IF NOT EXISTS（冪等）
--   - NULL 許可・DEFAULT なし（既存行への影響なし）
--   - 値は UI から入力（Discord サーバー ID = guild_id）
--
-- 作成日: 2026-06-12

DO $$
DECLARE
    schema_rec RECORD;
    applied_count INTEGER := 0;
BEGIN
    FOR schema_rec IN
        SELECT nspname FROM pg_namespace
        WHERE nspname ~ '^tenant_[0-9]+$'
        ORDER BY nspname
    LOOP
        -- company_discord が存在するテナントのみ処理
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = schema_rec.nspname
              AND table_name = 'company_discord'
        ) THEN
            RAISE NOTICE 'migration 20260612_110000: % — company_discord が未存在、スキップ', schema_rec.nspname;
            CONTINUE;
        END IF;

        EXECUTE format(
            'ALTER TABLE %I.company_discord ADD COLUMN IF NOT EXISTS guild_id VARCHAR(50)',
            schema_rec.nspname
        );

        applied_count := applied_count + 1;
        RAISE NOTICE 'migration 20260612_110000: %.company_discord に guild_id を追加', schema_rec.nspname;
    END LOOP;

    RAISE NOTICE 'migration 20260612_110000: 完了。適用 % スキーマ', applied_count;
END $$;

-- =====================================================================
-- Rollback 手順（緊急時のみ手動実行）:
--
-- DO $$
-- DECLARE r RECORD;
-- BEGIN
--     FOR r IN SELECT nspname FROM pg_namespace WHERE nspname ~ '^tenant_[0-9]+$'
--     LOOP
--         EXECUTE format(
--             'ALTER TABLE %I.company_discord DROP COLUMN IF EXISTS guild_id',
--             r.nspname
--         );
--     END LOOP;
-- END $$;
-- =====================================================================
