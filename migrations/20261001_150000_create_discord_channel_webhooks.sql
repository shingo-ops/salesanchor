-- ADR-159 便B / Migration: discord_channel_webhooks テーブル作成
--
-- 背景:
--   Discord 返信を担当者の名前・アイコンで送るため、チャンネルごとに webhook を
--   1 本作成して保管する（webhook 実行は username / avatar_url をメッセージ毎に上書きできる）。
--   webhook token は秘密情報のため services/encryption.py（Fernet）で暗号化して保存する。
--   書き込みはアプリコード（discord_webhook_sender.py）のみ。手動 INSERT 禁止（ADR-025）。
--
-- 設計:
--   docs/handoff/discord-staff-webhook-send/design.md / docs/adr/ADR-159-staff-identity-on-discord.md
--   token カラムは encryption.encrypt() が str を返すため TEXT（migrations/076 と同じ規約）。
--
-- 冪等性:
--   - CREATE TABLE IF NOT EXISTS / CREATE POLICY は pg_policies 存在確認
--   - DO block で pg_namespace を走査して全 tenant_NNN schema に適用
--
-- 参照: migrations/20260927_100000_create_meta_message_reactions.sql（同型の実装）
--
-- 変更履歴:
--   2026-10-01: 初版作成（ADR-159 便B）

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
        EXECUTE format($q$
            CREATE TABLE IF NOT EXISTS %I.discord_channel_webhooks (
                id SERIAL PRIMARY KEY,
                tenant_id INTEGER NOT NULL DEFAULT current_setting('app.tenant_id', true)::INTEGER,
                channel_id TEXT NOT NULL,
                webhook_id TEXT NOT NULL,
                webhook_token_encrypted TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

                CONSTRAINT uq_discord_channel_webhooks_channel UNIQUE (channel_id)
            )
        $q$, schema_rec.nspname);

        EXECUTE format(
            'CREATE INDEX IF NOT EXISTS idx_dcw_tenant ON %I.discord_channel_webhooks (tenant_id)',
            schema_rec.nspname
        );

        EXECUTE format(
            'ALTER TABLE %I.discord_channel_webhooks ENABLE ROW LEVEL SECURITY',
            schema_rec.nspname
        );

        IF NOT EXISTS (
            SELECT 1 FROM pg_policies
            WHERE policyname = 'tenant_isolation_discord_channel_webhooks'
              AND schemaname = schema_rec.nspname
        ) THEN
            EXECUTE format($q$
                CREATE POLICY tenant_isolation_discord_channel_webhooks ON %I.discord_channel_webhooks
                    USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER)
            $q$, schema_rec.nspname);
        END IF;

        EXECUTE format(
            $q$COMMENT ON TABLE %I.discord_channel_webhooks IS
              'ADR-159: Discord チャンネル別 webhook（担当者名義送信用）。token は Fernet 暗号化済み'$q$,
            schema_rec.nspname
        );

        created_count := created_count + 1;
        RAISE NOTICE 'migration discord_channel_webhooks: %: 作成完了', schema_rec.nspname;
    END LOOP;
    RAISE NOTICE 'migration discord_channel_webhooks: 全 % テナントに適用', created_count;
END $$;
