-- ============================================================================
-- Migration 20260604_180000: 分析エージェント(A) 顧客優先度付けテーブル群
--
-- ADR-107 (ADR-SA-14) 実装:
--   - {tenant_NNN}.message_labels       per-messageラベル（5種・確信度・両方向）
--   - {tenant_NNN}.customer_scores      顧客スコア（連続数値・3段階・根拠JSONB）
--   - {tenant_NNN}.tenant_calibrations  テナント固有重み較正履歴
--
-- 信頼保護の不変条件 (§13):
--   - スコアは助言。自動で客を切る/隠す処理はこのスキーマに含まない
--   - RLS で tenant_id 分離。他テナントのデータが混ざらない
--   - 地域/国籍カラムなし（行動のみで判定）
--
-- 冪等性:
--   - CREATE TABLE / INDEX IF NOT EXISTS
--   - CREATE POLICY ... IF NOT EXISTS パターン（pg_policies 確認）
-- ============================================================================

DO $$
DECLARE
    schema_record RECORD;
BEGIN
    FOR schema_record IN
        SELECT nspname AS schema_name
        FROM pg_namespace
        WHERE nspname LIKE 'tenant_%'
        ORDER BY nspname
    LOOP
        RAISE NOTICE 'Processing schema: %', schema_record.schema_name;

        -- ① per-message ラベルテーブル
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS %I.message_labels (
                id              SERIAL PRIMARY KEY,
                tenant_id       INTEGER      NOT NULL,
                message_id      INTEGER      NOT NULL,
                lead_id         INTEGER,
                label           VARCHAR(30)  NOT NULL
                    CHECK (label IN (
                        ''price_focus'',''substance_talk'',
                        ''self_disclosure'',''early_purchase_signal'',''other''
                    )),
                confidence      NUMERIC(4,3) NOT NULL
                    CHECK (confidence >= 0 AND confidence <= 1),
                direction       VARCHAR(10)  NOT NULL
                    CHECK (direction IN (''inbound'',''outbound'')),
                source          VARCHAR(20)  NOT NULL DEFAULT ''rule''
                    CHECK (source IN (''rule'',''llm'',''human'')),
                override_by     INTEGER,
                override_at     TIMESTAMPTZ,
                created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
            )',
            schema_record.schema_name
        );

        EXECUTE format(
            'COMMENT ON TABLE %I.message_labels IS
             ''ADR-107 §B①: per-message 最小ラベリング。地域/国籍カラムなし（行動のみ）。''',
            schema_record.schema_name
        );

        -- ② 顧客スコアテーブル（1リード1行・UNIQUE制約）
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS %I.customer_scores (
                id              SERIAL PRIMARY KEY,
                tenant_id       INTEGER      NOT NULL,
                lead_id         INTEGER      NOT NULL,
                score           NUMERIC(5,3) NOT NULL
                    CHECK (score >= 0 AND score <= 1),
                confidence      NUMERIC(4,3) NOT NULL
                    CHECK (confidence >= 0 AND confidence <= 1),
                tier            VARCHAR(10)  NOT NULL
                    CHECK (tier IN (''要観察'',''有望'',''最有望'')),
                signal_summary  JSONB        NOT NULL DEFAULT ''{}''::jsonb,
                sample_size     INTEGER      NOT NULL DEFAULT 0,
                is_cold_start   BOOLEAN      NOT NULL DEFAULT TRUE,
                override_score  NUMERIC(5,3)
                    CHECK (override_score IS NULL
                           OR (override_score >= 0 AND override_score <= 1)),
                override_note   TEXT,
                override_by     INTEGER,
                override_at     TIMESTAMPTZ,
                calibration_id  INTEGER,
                scored_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
                created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
            )',
            schema_record.schema_name
        );

        EXECUTE format(
            'COMMENT ON TABLE %I.customer_scores IS
             ''ADR-107 §C: スコアは値+確信度+根拠の3点セット必須。
               裸の断定禁止。社内ロールのみアクセス（顧客非公開）。''',
            schema_record.schema_name
        );

        -- ③ テナント較正テーブル（较正履歴・月次バッチで追記）
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS %I.tenant_calibrations (
                id               SERIAL PRIMARY KEY,
                tenant_id        INTEGER      NOT NULL,
                label_weights    JSONB        NOT NULL DEFAULT ''{}''::jsonb,
                win_sample_size  INTEGER      NOT NULL DEFAULT 0,
                loss_sample_size INTEGER      NOT NULL DEFAULT 0,
                is_cold_start    BOOLEAN      NOT NULL DEFAULT TRUE,
                calibrated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
                created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
            )',
            schema_record.schema_name
        );

        EXECUTE format(
            'COMMENT ON TABLE %I.tenant_calibrations IS
             ''ADR-107 §B②: テナント固有重み。他テナントとは完全分離。
               月次バッチまたは成約/失注累計10件追加で再較正。''',
            schema_record.schema_name
        );

        -- インデックス
        EXECUTE format(
            'CREATE INDEX IF NOT EXISTS idx_message_labels_lead_id
             ON %I.message_labels (lead_id)',
            schema_record.schema_name
        );
        EXECUTE format(
            'CREATE INDEX IF NOT EXISTS idx_message_labels_message_id
             ON %I.message_labels (message_id)',
            schema_record.schema_name
        );
        EXECUTE format(
            'CREATE UNIQUE INDEX IF NOT EXISTS uq_customer_scores_lead_id
             ON %I.customer_scores (lead_id)',
            schema_record.schema_name
        );
        EXECUTE format(
            'CREATE INDEX IF NOT EXISTS idx_customer_scores_tier
             ON %I.customer_scores (tier)',
            schema_record.schema_name
        );
        EXECUTE format(
            'CREATE INDEX IF NOT EXISTS idx_tenant_calibrations_latest
             ON %I.tenant_calibrations (tenant_id, calibrated_at DESC)',
            schema_record.schema_name
        );

        -- RLS 有効化
        EXECUTE format(
            'ALTER TABLE %I.message_labels ENABLE ROW LEVEL SECURITY',
            schema_record.schema_name
        );
        EXECUTE format(
            'ALTER TABLE %I.customer_scores ENABLE ROW LEVEL SECURITY',
            schema_record.schema_name
        );
        EXECUTE format(
            'ALTER TABLE %I.tenant_calibrations ENABLE ROW LEVEL SECURITY',
            schema_record.schema_name
        );

        -- RLS ポリシー（冪等: pg_policies で存在確認）
        IF NOT EXISTS (
            SELECT 1 FROM pg_policies
            WHERE policyname = 'message_labels_tenant_isolation'
              AND schemaname = schema_record.schema_name
        ) THEN
            EXECUTE format(
                'CREATE POLICY message_labels_tenant_isolation
                 ON %I.message_labels
                 USING (tenant_id = current_setting(''app.tenant_id'', true)::INTEGER)',
                schema_record.schema_name
            );
        END IF;

        IF NOT EXISTS (
            SELECT 1 FROM pg_policies
            WHERE policyname = 'customer_scores_tenant_isolation'
              AND schemaname = schema_record.schema_name
        ) THEN
            EXECUTE format(
                'CREATE POLICY customer_scores_tenant_isolation
                 ON %I.customer_scores
                 USING (tenant_id = current_setting(''app.tenant_id'', true)::INTEGER)',
                schema_record.schema_name
            );
        END IF;

        IF NOT EXISTS (
            SELECT 1 FROM pg_policies
            WHERE policyname = 'tenant_calibrations_tenant_isolation'
              AND schemaname = schema_record.schema_name
        ) THEN
            EXECUTE format(
                'CREATE POLICY tenant_calibrations_tenant_isolation
                 ON %I.tenant_calibrations
                 USING (tenant_id = current_setting(''app.tenant_id'', true)::INTEGER)',
                schema_record.schema_name
            );
        END IF;

    END LOOP;
END $$;

-- パーミッションキー追加（社内ロールのみアクセス：ADR-107 守るべき原則）
INSERT INTO public.permissions (key, resource, action, description, category)
VALUES
    ('analytics.customer_priority.view',
     'analytics', 'customer_priority_view',
     '顧客優先度スコアの閲覧（社内専用・顧客非公開）', '分析'),
    ('analytics.customer_priority.override',
     'analytics', 'customer_priority_override',
     '顧客優先度スコアの人手上書き（tenant_admin/tenant_staff のみ）', '分析')
ON CONFLICT (key) DO NOTHING;
