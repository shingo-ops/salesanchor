-- SA-04: contact_contact_channels に重複 ID 防止 UNIQUE 制約を追加
--
-- 背景:
--   SA-04 KPI K5「重複 ID 登録の阻止 100%」を達成するため、
--   (contact_id, channel, COALESCE(purpose,'')) の組み合わせに
--   UNIQUE 制約を追加する。
--
--   事前確認（2026-06-12 recon）: 本番 DB に重複行ゼロ確認済み。
--   冪等: CREATE UNIQUE INDEX IF NOT EXISTS で再実行 no-op。
--
-- guild_id 追加 catch-up:
--   20260604_100000_add_guild_id_to_contact_channels.sql が setup_tenant.py に
--   未登録のため、同 migration と同等の ADD COLUMN IF NOT EXISTS を含む。
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
        -- contact_contact_channels が存在するテナントのみ処理
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = schema_rec.nspname
              AND table_name = 'contact_contact_channels'
        ) THEN
            RAISE NOTICE 'migration 20260612_100000: % — contact_contact_channels が未存在、スキップ', schema_rec.nspname;
            CONTINUE;
        END IF;

        -- guild_id 列が未追加のテナントにも catch-up
        EXECUTE format(
            'ALTER TABLE %I.contact_contact_channels ADD COLUMN IF NOT EXISTS guild_id VARCHAR(50)',
            schema_rec.nspname
        );

        -- UNIQUE(contact_id, channel, COALESCE(purpose,''))
        -- purpose は NULL 許容なので、COALESCE で空文字に統一して制約を一意に保つ
        EXECUTE format(
            'CREATE UNIQUE INDEX IF NOT EXISTS idx_ccc_unique_channel_purpose '
            'ON %I.contact_contact_channels (contact_id, channel, COALESCE(purpose, ''''))',
            schema_rec.nspname
        );

        applied_count := applied_count + 1;
        RAISE NOTICE 'migration 20260612_100000: %.contact_contact_channels に UNIQUE 制約を追加', schema_rec.nspname;
    END LOOP;

    RAISE NOTICE 'migration 20260612_100000: 完了。適用 % スキーマ', applied_count;
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
--             'DROP INDEX IF EXISTS %I.idx_ccc_unique_channel_purpose',
--             r.nspname
--         );
--     END LOOP;
-- END $$;
-- =====================================================================
