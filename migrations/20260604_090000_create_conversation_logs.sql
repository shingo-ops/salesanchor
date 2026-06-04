-- SA-02 / Migration 20260604_090000: conversation_logs テーブル作成
--
-- 背景:
--   Sales Anchor Foundation PR#4。会話ログを全チャネル横断で格納する
--   中央テーブルを作成する（Meta/Discord/メール等）。
--
-- 設計:
--   - contact_id=NULL（名無しコンタクト）の行もテナント隔離できるよう、
--     RLS は contact→company チェーンではなく tenant_id 直接列で行う（ADR SA-02）。
--   - channel_type: 'meta_messenger' / 'instagram' / 'discord' / 'email' 等
--   - direction: 'inbound' / 'outbound'
--   - external_message_id: チャネル固有のメッセージ ID（UNIQUE で重複受信防止）
--   - analysis: AI 解析結果 JSONB（感情スコア・要約等）
--
-- 冪等性:
--   - CREATE TABLE IF NOT EXISTS
--   - RLS は pg_policies 存在チェックで冪等
--   - 全テナントスキーマ（^tenant_\d+$）をループして適用
--
-- 作成日: 2026-06-04

DO $$
DECLARE
    schema_rec RECORD;
    applied_count INTEGER := 0;
BEGIN
    FOR schema_rec IN
        SELECT nspname FROM pg_namespace
        WHERE nspname ~ '^tenant_\d+$'
        ORDER BY nspname
    LOOP
        -- conversation_logs テーブル作成（IF NOT EXISTS で冪等）
        EXECUTE format($q$
            CREATE TABLE IF NOT EXISTS %I.conversation_logs (
                id                  SERIAL PRIMARY KEY,
                tenant_id           INTEGER NOT NULL,
                lead_id             INTEGER,
                contact_id          INTEGER,
                company_id          INTEGER,
                deal_id             INTEGER,
                channel_type        VARCHAR(30) NOT NULL,
                channel_identity    VARCHAR(255),
                direction           VARCHAR(10) NOT NULL
                    CHECK (direction IN ('inbound', 'outbound')),
                sender              VARCHAR(100),
                content_text        TEXT,
                original_language   VARCHAR(10),
                external_message_id VARCHAR(255) UNIQUE,
                raw_payload         JSONB,
                status              VARCHAR(20) DEFAULT 'sent',
                translated_text     TEXT,
                analysis            JSONB,
                occurred_at         TIMESTAMPTZ NOT NULL,
                created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        $q$, schema_rec.nspname);

        -- インデックス（冪等）
        EXECUTE format(
            'CREATE INDEX IF NOT EXISTS idx_conv_logs_tenant_id ON %I.conversation_logs (tenant_id)',
            schema_rec.nspname
        );
        EXECUTE format(
            'CREATE INDEX IF NOT EXISTS idx_conv_logs_company_id ON %I.conversation_logs (company_id)',
            schema_rec.nspname
        );
        EXECUTE format(
            'CREATE INDEX IF NOT EXISTS idx_conv_logs_contact_id ON %I.conversation_logs (contact_id)',
            schema_rec.nspname
        );
        EXECUTE format(
            'CREATE INDEX IF NOT EXISTS idx_conv_logs_occurred_at ON %I.conversation_logs (occurred_at DESC)',
            schema_rec.nspname
        );

        -- RLS 有効化（冪等: 既に有効でも no-op）
        EXECUTE format(
            'ALTER TABLE %I.conversation_logs ENABLE ROW LEVEL SECURITY',
            schema_rec.nspname
        );

        -- RLS ポリシー（tenant_id 直接列で隔離。contact_id=NULL 行も保護するため）
        IF NOT EXISTS (
            SELECT 1 FROM pg_policies
            WHERE policyname = 'conversation_logs_tenant_isolation'
              AND schemaname = schema_rec.nspname
        ) THEN
            EXECUTE format($q$
                CREATE POLICY conversation_logs_tenant_isolation ON %I.conversation_logs
                    USING (tenant_id = public.current_tenant_id())
            $q$, schema_rec.nspname);
        END IF;

        applied_count := applied_count + 1;
        RAISE NOTICE 'migration 20260604_090000: %.conversation_logs を作成', schema_rec.nspname;
    END LOOP;

    RAISE NOTICE 'migration 20260604_090000: 完了。適用 % スキーマ', applied_count;
END $$;

-- =====================================================================
-- Rollback 手順（緊急時のみ手動実行）:
--
-- DO $$
-- DECLARE r RECORD;
-- BEGIN
--     FOR r IN SELECT nspname FROM pg_namespace WHERE nspname ~ '^tenant_\d+$'
--     LOOP
--         EXECUTE format('DROP TABLE IF EXISTS %I.conversation_logs CASCADE', r.nspname);
--     END LOOP;
-- END $$;
-- =====================================================================
