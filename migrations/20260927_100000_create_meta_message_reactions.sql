-- discord-reaction / Migration: meta_message_reactions テーブル作成
--
-- 背景:
--   Discord リアクション（絵文字リアクション）を受信箱で表示・操作するために
--   リアクション情報を永続化する必要がある。
--   meta_messages テーブルへのカラム追加では 1メッセージ: N リアクション の正規化が
--   できないため、専用子テーブルとして設計する（SSOT: ADR-095 準拠）。
--
-- 設計:
--   docs/handoff/discord-reaction/design.md §DB設計 に基づく。
--   1メッセージ : Nリアクション の正規化子テーブル。meta_messages.id を FK とする。
--   同一ユーザーが同じ絵文字で複数リアクションを送れないよう UNIQUE 制約を付与。
--
-- 冪等性:
--   - CREATE TABLE IF NOT EXISTS
--   - CREATE INDEX IF NOT EXISTS
--   - CREATE POLICY は pg_policies 存在確認
--   - DO block で pg_namespace 走査して全 tenant_NNN schema に適用
--
-- 参照: migrations/20260902_100000_create_lead_attachments.sql（同型の実装）
--
-- 変更履歴:
--   2026-09-27: 初版作成（discord-reaction）

DO $$
DECLARE
    schema_rec RECORD;
    created_count INTEGER := 0;
BEGIN
    FOR schema_rec IN
        SELECT nspname FROM pg_namespace
        WHERE nspname ~ '^tenant_\d+$'
        ORDER BY nspname
    LOOP
        -- meta_messages テーブルが存在するスキーマのみ対象
        IF NOT EXISTS (
            SELECT 1 FROM pg_tables
            WHERE schemaname = schema_rec.nspname AND tablename = 'meta_messages'
        ) THEN
            CONTINUE;
        END IF;

        -- テーブル作成（冪等: IF NOT EXISTS）
        EXECUTE format($q$
            CREATE TABLE IF NOT EXISTS %I.meta_message_reactions (
                id SERIAL PRIMARY KEY,
                tenant_id INTEGER NOT NULL DEFAULT current_setting('app.tenant_id', true)::INTEGER,
                meta_message_id INTEGER NOT NULL REFERENCES %I.meta_messages(id) ON DELETE CASCADE,
                emoji_name TEXT NOT NULL,
                emoji_id TEXT,
                emoji_animated BOOLEAN DEFAULT FALSE,
                reactor_discord_user_id TEXT NOT NULL,
                reactor_display_name TEXT,
                is_bot_reaction BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

                CONSTRAINT uq_reaction_per_user_emoji
                    UNIQUE (meta_message_id, emoji_name, emoji_id, reactor_discord_user_id)
            )
        $q$, schema_rec.nspname, schema_rec.nspname);

        -- インデックス（冪等）
        -- メッセージ別リアクション取得を高速化
        EXECUTE format(
            'CREATE INDEX IF NOT EXISTS idx_mmr_meta_message_id ON %I.meta_message_reactions (meta_message_id)',
            schema_rec.nspname
        );
        -- テナント別集計用
        EXECUTE format(
            'CREATE INDEX IF NOT EXISTS idx_mmr_tenant ON %I.meta_message_reactions (tenant_id)',
            schema_rec.nspname
        );

        -- RLS 有効化（冪等）
        EXECUTE format(
            'ALTER TABLE %I.meta_message_reactions ENABLE ROW LEVEL SECURITY',
            schema_rec.nspname
        );

        -- RLS ポリシー: tenant_id でテナント分離
        IF NOT EXISTS (
            SELECT 1 FROM pg_policies
            WHERE policyname = 'tenant_isolation_meta_message_reactions'
              AND schemaname = schema_rec.nspname
        ) THEN
            EXECUTE format($q$
                CREATE POLICY tenant_isolation_meta_message_reactions ON %I.meta_message_reactions
                    USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER)
            $q$, schema_rec.nspname);
        END IF;

        EXECUTE format(
            $q$COMMENT ON TABLE %I.meta_message_reactions IS
              'discord-reaction: Discord リアクション保管台帳（meta_messages の子テーブル）'$q$,
            schema_rec.nspname
        );

        created_count := created_count + 1;
        RAISE NOTICE 'migration meta_message_reactions: %: 作成完了', schema_rec.nspname;
    END LOOP;
    RAISE NOTICE 'migration meta_message_reactions: 全 % テナントに適用', created_count;
END $$;
