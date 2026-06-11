-- SA-02 Stage 1 / Migration 20260611_100000: channel_masters テーブル作成
--
-- 背景:
--   SA-02 設計doc §3 v1スコープ item4 「チャネルマスタ」。
--   「電話」「対面」等の手動チャネルをテナント単位で追加可能にし、
--   チャネル単位で connection_type（auto / manual）を管理する。
--   入力ボックス表示の判定（1チャネル＝1入口排他）をこのテーブルで行う。
--
-- 設計:
--   - テナントスキーマ内テーブル（マルチテナント標準パターン）
--   - connection_type: 'auto'（連携済・自動取込のみ）/ 'manual'（手動入力専用）
--   - UNIQUE(platform): 1テナント内でチャネル名は一意
--   - RLS: tenant_id 直接列で隔離（conversation_logs と同パターン）
--
-- デフォルトシード:
--   messenger / instagram / discord → auto
--   phone（電話） / in_person（対面）→ manual
--
-- 冪等性:
--   CREATE TABLE IF NOT EXISTS / ON CONFLICT DO NOTHING / RLS 存在チェック
--
-- 作成日: 2026-06-11

DO $$
DECLARE
    schema_rec    RECORD;
    tenant_id_val INTEGER;
    applied_count INTEGER := 0;
BEGIN
    FOR schema_rec IN
        SELECT nspname FROM pg_namespace
        WHERE nspname ~ '^tenant_\d+$'
        ORDER BY nspname
    LOOP
        -- schema名から tenant_id を算出: 'tenant_001' → 1
        tenant_id_val := SUBSTRING(schema_rec.nspname FROM 8)::INTEGER;

        -- channel_masters テーブル作成（IF NOT EXISTS で冪等）
        EXECUTE format($q$
            CREATE TABLE IF NOT EXISTS %I.channel_masters (
                id              SERIAL PRIMARY KEY,
                tenant_id       INTEGER NOT NULL,
                platform        VARCHAR(30) NOT NULL,
                display_name    VARCHAR(100) NOT NULL,
                connection_type VARCHAR(10) NOT NULL
                    CHECK (connection_type IN ('auto', 'manual')),
                is_active       BOOLEAN NOT NULL DEFAULT TRUE,
                created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE (platform)
            )
        $q$, schema_rec.nspname);

        -- RLS 有効化（冪等）
        EXECUTE format(
            'ALTER TABLE %I.channel_masters ENABLE ROW LEVEL SECURITY',
            schema_rec.nspname
        );

        -- RLS ポリシー（tenant_id 直接列で隔離）
        IF NOT EXISTS (
            SELECT 1 FROM pg_policies
            WHERE policyname = 'channel_masters_tenant_isolation'
              AND schemaname = schema_rec.nspname
        ) THEN
            EXECUTE format($q$
                CREATE POLICY channel_masters_tenant_isolation ON %I.channel_masters
                    USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER)
            $q$, schema_rec.nspname);
        END IF;

        -- デフォルトチャネルシード（ON CONFLICT DO NOTHING で冪等）
        EXECUTE format($q$
            INSERT INTO %I.channel_masters (tenant_id, platform, display_name, connection_type)
            VALUES
                ($1, 'messenger',  'Messenger', 'auto'),
                ($1, 'instagram',  'Instagram', 'auto'),
                ($1, 'discord',    'Discord',   'auto'),
                ($1, 'phone',      '電話',       'manual'),
                ($1, 'in_person',  '対面',       'manual')
            ON CONFLICT (platform) DO NOTHING
        $q$, schema_rec.nspname) USING tenant_id_val;

        applied_count := applied_count + 1;
        RAISE NOTICE 'migration 20260611_100000: %.channel_masters を作成', schema_rec.nspname;
    END LOOP;

    RAISE NOTICE 'migration 20260611_100000: 完了。適用 % スキーマ', applied_count;
END $$;

-- =====================================================================
-- Rollback 手順（緊急時のみ手動実行）:
--
-- DO $$
-- DECLARE r RECORD;
-- BEGIN
--     FOR r IN SELECT nspname FROM pg_namespace WHERE nspname ~ '^tenant_\d+$'
--     LOOP
--         EXECUTE format('DROP TABLE IF EXISTS %I.channel_masters CASCADE', r.nspname);
--     END LOOP;
-- END $$;
-- =====================================================================
