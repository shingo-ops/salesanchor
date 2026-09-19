-- Analysis Rule Tables for Sold-Out and Date Format Rules (C92)
--
-- 目的: 完売ルール・日付ルールの共通テーブル13表をDBに作成する。
--       analysis_*共通名でpolicy_typeにより種別を識別する（C92）。
--
-- 設計根拠: docs/handoff/tcg-import-latest-only/sold-out-rules-design.md §4.9
-- 名前衝突: analysis_runs は既存テーブル（別物）。本マイグレーションは analysis_rule_runs を作成する。
--
-- 冪等性: CREATE TABLE IF NOT EXISTS / ON CONFLICT DO NOTHING
--
-- 作成日: 2026-09-17

DO $$
DECLARE
    _schema TEXT := 'tenant_001';
BEGIN

    -- ================================================================
    -- 0. スキーマ存在ガード
    -- ================================================================
    IF NOT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = _schema) THEN
        RAISE NOTICE '20260917_000000: schema % does not exist, skipping', _schema;
        RETURN;
    END IF;
    RAISE NOTICE '20260917_000000: schema % confirmed', _schema;

    -- ====================================================
    -- 1. analysis_policies（ルール管理の入口、種別ごとに1行）
    -- ====================================================
    EXECUTE format($q$
        CREATE TABLE IF NOT EXISTS %I.analysis_policies (
            id                        UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
            policy_type               VARCHAR(30)  NOT NULL
                                                   CHECK (policy_type IN ('sold_out','date_format')),
            active_revision_id        UUID,
            draft_revision_id         UUID,
            current_suite_revision_id UUID,
            lock_version              INTEGER      NOT NULL DEFAULT 0,
            activation_state          VARCHAR(20)  NOT NULL DEFAULT 'inactive'
                                                   CHECK (activation_state IN ('inactive','draft','tested','active')),
            created_at                TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            updated_at                TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            UNIQUE (policy_type)
        )
    $q$, _schema);

    -- ====================================================
    -- 2. analysis_policy_revisions（保存のたびに不変版を作成）
    -- ====================================================
    EXECUTE format($q$
        CREATE TABLE IF NOT EXISTS %I.analysis_policy_revisions (
            id                     UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
            policy_id              UUID         NOT NULL
                                                REFERENCES %I.analysis_policies (id) ON DELETE CASCADE,
            parent_revision_id     UUID,
            instruction_version_id UUID         NOT NULL,
            profile_version_id     UUID,
            content_digest         VARCHAR(64)  NOT NULL
                                                CHECK (content_digest ~ '^[0-9a-f]{64}$'),
            created_by             VARCHAR(100) NOT NULL,
            created_at             TIMESTAMPTZ  NOT NULL DEFAULT NOW()
        )
    $q$, _schema, _schema);
    EXECUTE format($q$
        CREATE INDEX IF NOT EXISTS ix_analysis_policy_revisions_policy
            ON %I.analysis_policy_revisions (policy_id, created_at DESC)
    $q$, _schema);

    -- ====================================================
    -- 3. analysis_instruction_versions（指示文の不変版）
    -- ====================================================
    EXECUTE format($q$
        CREATE TABLE IF NOT EXISTS %I.analysis_instruction_versions (
            id         UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
            policy_id  UUID         NOT NULL
                                    REFERENCES %I.analysis_policies (id) ON DELETE CASCADE,
            body       TEXT         NOT NULL CHECK (body <> ''),
            created_by VARCHAR(100) NOT NULL,
            created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
        )
    $q$, _schema, _schema);
    EXECUTE format($q$
        CREATE INDEX IF NOT EXISTS ix_analysis_instruction_versions_policy
            ON %I.analysis_instruction_versions (policy_id, created_at DESC)
    $q$, _schema);

    -- ====================================================
    -- 4. analysis_execution_profile_versions（モデル/出力契約の不変版）
    -- ====================================================
    EXECUTE format($q$
        CREATE TABLE IF NOT EXISTS %I.analysis_execution_profile_versions (
            id                   UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
            policy_id            UUID         NOT NULL
                                              REFERENCES %I.analysis_policies (id) ON DELETE CASCADE,
            model_id             VARCHAR(100) NOT NULL,
            generation_config    JSONB        NOT NULL DEFAULT '{}'::jsonb,
            output_schema        JSONB        NOT NULL DEFAULT '{}'::jsonb,
            input_limits         JSONB        NOT NULL DEFAULT '{}'::jsonb,
            compatibility_output JSONB,
            created_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW()
        )
    $q$, _schema, _schema);
    EXECUTE format($q$
        CREATE INDEX IF NOT EXISTS ix_analysis_execution_profiles_policy
            ON %I.analysis_execution_profile_versions (policy_id, created_at DESC)
    $q$, _schema);

    -- ====================================================
    -- 5. analysis_rules（ルールの不変識別子）
    -- ====================================================
    EXECUTE format($q$
        CREATE TABLE IF NOT EXISTS %I.analysis_rules (
            id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            policy_id        UUID        NOT NULL
                                         REFERENCES %I.analysis_policies (id) ON DELETE CASCADE,
            legacy_status_id UUID,
            created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    $q$, _schema, _schema);
    EXECUTE format($q$
        CREATE INDEX IF NOT EXISTS ix_analysis_rules_policy
            ON %I.analysis_rules (policy_id)
    $q$, _schema);

    -- ====================================================
    -- 6. analysis_rule_versions（ルールの説明/文脈の不変版）
    -- ====================================================
    EXECUTE format($q$
        CREATE TABLE IF NOT EXISTS %I.analysis_rule_versions (
            id                  UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
            rule_id             UUID         NOT NULL
                                             REFERENCES %I.analysis_rules (id) ON DELETE CASCADE,
            title               TEXT         NOT NULL,
            context_instruction TEXT,
            created_by          VARCHAR(100) NOT NULL,
            created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW()
        )
    $q$, _schema, _schema);
    EXECUTE format($q$
        CREATE INDEX IF NOT EXISTS ix_analysis_rule_versions_rule
            ON %I.analysis_rule_versions (rule_id, created_at DESC)
    $q$, _schema);

    -- ====================================================
    -- 7. analysis_rule_words（1語1行、kindで種類を区別）
    -- ====================================================
    EXECUTE format($q$
        CREATE TABLE IF NOT EXISTS %I.analysis_rule_words (
            id               UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
            rule_version_id  UUID         NOT NULL
                                          REFERENCES %I.analysis_rule_versions (id) ON DELETE CASCADE,
            kind             VARCHAR(30)  NOT NULL
                                          CHECK (kind IN ('search','exclude','format_template','apply_condition')),
            text             TEXT         NOT NULL CHECK (text <> ''),
            position         INTEGER      NOT NULL CHECK (position >= 0),
            UNIQUE (rule_version_id, kind, text)
        )
    $q$, _schema, _schema);
    EXECUTE format($q$
        CREATE INDEX IF NOT EXISTS ix_analysis_rule_words_version
            ON %I.analysis_rule_words (rule_version_id)
    $q$, _schema);

    -- ====================================================
    -- 8. analysis_revision_rules（版ごとのルール採用状態）
    -- ====================================================
    EXECUTE format($q$
        CREATE TABLE IF NOT EXISTS %I.analysis_revision_rules (
            revision_id      UUID    NOT NULL
                                     REFERENCES %I.analysis_policy_revisions (id) ON DELETE CASCADE,
            rule_id          UUID    NOT NULL
                                     REFERENCES %I.analysis_rules (id) ON DELETE CASCADE,
            rule_version_id  UUID    NOT NULL
                                     REFERENCES %I.analysis_rule_versions (id),
            is_deleted       BOOLEAN NOT NULL DEFAULT FALSE,
            PRIMARY KEY (revision_id, rule_id)
        )
    $q$, _schema, _schema, _schema, _schema);

    -- ====================================================
    -- 9. analysis_test_case_versions（人間の正解の不変版）
    -- ====================================================
    EXECUTE format($q$
        CREATE TABLE IF NOT EXISTS %I.analysis_test_case_versions (
            id         UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
            case_id    UUID         NOT NULL,
            policy_id  UUID         NOT NULL
                                    REFERENCES %I.analysis_policies (id) ON DELETE CASCADE,
            raw_text   TEXT         NOT NULL CHECK (raw_text <> ''),
            posted_at  TIMESTAMPTZ,
            expected   JSONB        NOT NULL,
            created_by VARCHAR(100) NOT NULL,
            created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
        )
    $q$, _schema, _schema);
    EXECUTE format($q$
        CREATE INDEX IF NOT EXISTS ix_analysis_test_case_versions_policy
            ON %I.analysis_test_case_versions (policy_id, case_id, created_at DESC)
    $q$, _schema);

    -- ====================================================
    -- 10. analysis_test_suites（テスト合格時の版集合）
    -- ====================================================
    EXECUTE format($q$
        CREATE TABLE IF NOT EXISTS %I.analysis_test_suites (
            id         UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
            policy_id  UUID         NOT NULL
                                    REFERENCES %I.analysis_policies (id) ON DELETE CASCADE,
            created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
        )
    $q$, _schema, _schema);

    -- ====================================================
    -- 11. analysis_suite_cases（テスト集合の構成要素）
    -- ====================================================
    EXECUTE format($q$
        CREATE TABLE IF NOT EXISTS %I.analysis_suite_cases (
            suite_id        UUID NOT NULL
                                 REFERENCES %I.analysis_test_suites (id) ON DELETE CASCADE,
            case_id         UUID NOT NULL,
            case_version_id UUID NOT NULL
                                 REFERENCES %I.analysis_test_case_versions (id),
            PRIMARY KEY (suite_id, case_id)
        )
    $q$, _schema, _schema, _schema);

    -- ====================================================
    -- 12. analysis_rule_runs（テスト/通常の実行記録）
    -- ====================================================
    EXECUTE format($q$
        CREATE TABLE IF NOT EXISTS %I.analysis_rule_runs (
            id                 UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
            policy_id          UUID         NOT NULL
                                            REFERENCES %I.analysis_policies (id) ON DELETE CASCADE,
            revision_id        UUID         NOT NULL
                                            REFERENCES %I.analysis_policy_revisions (id),
            suite_revision_id  UUID
                                            REFERENCES %I.analysis_test_suites (id),
            source_message_id  UUID,
            purpose            VARCHAR(20)  NOT NULL
                                            CHECK (purpose IN ('test','production')),
            engine_version     VARCHAR(50)  NOT NULL,
            request_key        UUID         NOT NULL UNIQUE,
            started_by         VARCHAR(100) NOT NULL,
            started_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            completed_at       TIMESTAMPTZ,
            state              VARCHAR(20)  NOT NULL DEFAULT 'pending'
                                            CHECK (state IN ('pending','running','passed','failed','error')),
            CONSTRAINT analysis_rule_runs_test_suite CHECK (
                (purpose = 'test') = (suite_revision_id IS NOT NULL)),
            CONSTRAINT analysis_rule_runs_prod_source CHECK (
                (purpose = 'production') = (source_message_id IS NOT NULL))
        )
    $q$, _schema, _schema, _schema, _schema);
    EXECUTE format($q$
        CREATE INDEX IF NOT EXISTS ix_analysis_rule_runs_policy
            ON %I.analysis_rule_runs (policy_id, started_at DESC)
    $q$, _schema);
    EXECUTE format($q$
        CREATE INDEX IF NOT EXISTS ix_analysis_rule_runs_state
            ON %I.analysis_rule_runs (state)
            WHERE state IN ('pending','running')
    $q$, _schema);

    -- ====================================================
    -- 13. analysis_rule_run_results（判断結果の正規化記録）
    -- ====================================================
    EXECUTE format($q$
        CREATE TABLE IF NOT EXISTS %I.analysis_rule_run_results (
            id                 UUID  PRIMARY KEY DEFAULT gen_random_uuid(),
            run_id             UUID  NOT NULL
                                     REFERENCES %I.analysis_rule_runs (id) ON DELETE CASCADE,
            case_version_id    UUID
                                     REFERENCES %I.analysis_test_case_versions (id),
            extraction_item_id UUID,
            decision           JSONB NOT NULL,
            source_spans       JSONB,
            rule_version_refs  JSONB,
            validation_error   TEXT,
            invalidated_at     TIMESTAMPTZ,
            created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT analysis_rule_run_results_target CHECK (
                (case_version_id IS NOT NULL) OR (extraction_item_id IS NOT NULL))
        )
    $q$, _schema, _schema, _schema);
    EXECUTE format($q$
        CREATE INDEX IF NOT EXISTS ix_analysis_rule_run_results_run
            ON %I.analysis_rule_run_results (run_id)
    $q$, _schema);
    EXECUTE format($q$
        CREATE INDEX IF NOT EXISTS ix_analysis_rule_run_results_valid
            ON %I.analysis_rule_run_results (extraction_item_id)
            WHERE invalidated_at IS NULL
    $q$, _schema);

    RAISE NOTICE '20260917_000000: 13 テーブル作成完了 (schema %)', _schema;

    -- ====================================================
    -- FK後付け: analysis_policies の自己参照FK（冪等）
    -- ====================================================
    IF NOT EXISTS (SELECT 1 FROM pg_constraint c JOIN pg_namespace n ON n.oid = c.connamespace WHERE c.conname = 'fk_analysis_policies_active_rev' AND n.nspname = _schema) THEN
        EXECUTE format($q$
            ALTER TABLE %I.analysis_policies
                ADD CONSTRAINT fk_analysis_policies_active_rev
                FOREIGN KEY (active_revision_id) REFERENCES %I.analysis_policy_revisions (id)
        $q$, _schema, _schema);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint c JOIN pg_namespace n ON n.oid = c.connamespace WHERE c.conname = 'fk_analysis_policies_draft_rev' AND n.nspname = _schema) THEN
        EXECUTE format($q$
            ALTER TABLE %I.analysis_policies
                ADD CONSTRAINT fk_analysis_policies_draft_rev
                FOREIGN KEY (draft_revision_id) REFERENCES %I.analysis_policy_revisions (id)
        $q$, _schema, _schema);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint c JOIN pg_namespace n ON n.oid = c.connamespace WHERE c.conname = 'fk_analysis_policies_suite_rev' AND n.nspname = _schema) THEN
        EXECUTE format($q$
            ALTER TABLE %I.analysis_policies
                ADD CONSTRAINT fk_analysis_policies_suite_rev
                FOREIGN KEY (current_suite_revision_id) REFERENCES %I.analysis_test_suites (id)
        $q$, _schema, _schema);
    END IF;

    -- FK後付け: source_messages / extraction_items が存在する場合のみ
    IF EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = _schema AND tablename = 'source_messages') THEN
        IF NOT EXISTS (SELECT 1 FROM pg_constraint c JOIN pg_namespace n ON n.oid = c.connamespace WHERE c.conname = 'fk_analysis_rule_runs_source_msg' AND n.nspname = _schema) THEN
            EXECUTE format($q$
                ALTER TABLE %I.analysis_rule_runs
                    ADD CONSTRAINT fk_analysis_rule_runs_source_msg
                    FOREIGN KEY (source_message_id) REFERENCES %I.source_messages (id) ON DELETE CASCADE
            $q$, _schema, _schema);
        END IF;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = _schema AND tablename = 'extraction_items') THEN
        IF NOT EXISTS (SELECT 1 FROM pg_constraint c JOIN pg_namespace n ON n.oid = c.connamespace WHERE c.conname = 'fk_analysis_rule_run_results_item' AND n.nspname = _schema) THEN
            EXECUTE format($q$
                ALTER TABLE %I.analysis_rule_run_results
                    ADD CONSTRAINT fk_analysis_rule_run_results_item
                    FOREIGN KEY (extraction_item_id) REFERENCES %I.extraction_items (id) ON DELETE CASCADE
            $q$, _schema, _schema);
        END IF;
    END IF;

    RAISE NOTICE '20260917_000000: FK後付け完了 (schema %)', _schema;

    -- ====================================================
    -- 初期データ: analysis_policies に sold_out / date_format の2行
    -- ====================================================
    EXECUTE format($q$
        INSERT INTO %I.analysis_policies (policy_type, activation_state) VALUES
            ('sold_out',    'inactive'),
            ('date_format', 'inactive')
        ON CONFLICT (policy_type) DO NOTHING
    $q$, _schema);

    RAISE NOTICE '20260917_000000: 初期データ INSERT 完了（sold_out / date_format）';

    RAISE NOTICE '20260917_000000: 完了。schema % に analysis_rule 13 テーブル作成・初期データ seed 完了', _schema;
END $$;

DO $$
DECLARE
    _schema TEXT := 'tenant_004';
BEGIN

    -- ================================================================
    -- 0. スキーマ存在ガード
    -- ================================================================
    IF NOT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = _schema) THEN
        RAISE NOTICE '20260917_000000: schema % does not exist, skipping', _schema;
        RETURN;
    END IF;
    RAISE NOTICE '20260917_000000: schema % confirmed', _schema;

    -- ====================================================
    -- 1. analysis_policies（ルール管理の入口、種別ごとに1行）
    -- ====================================================
    EXECUTE format($q$
        CREATE TABLE IF NOT EXISTS %I.analysis_policies (
            id                        UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
            policy_type               VARCHAR(30)  NOT NULL
                                                   CHECK (policy_type IN ('sold_out','date_format')),
            active_revision_id        UUID,
            draft_revision_id         UUID,
            current_suite_revision_id UUID,
            lock_version              INTEGER      NOT NULL DEFAULT 0,
            activation_state          VARCHAR(20)  NOT NULL DEFAULT 'inactive'
                                                   CHECK (activation_state IN ('inactive','draft','tested','active')),
            created_at                TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            updated_at                TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            UNIQUE (policy_type)
        )
    $q$, _schema);

    -- ====================================================
    -- 2. analysis_policy_revisions（保存のたびに不変版を作成）
    -- ====================================================
    EXECUTE format($q$
        CREATE TABLE IF NOT EXISTS %I.analysis_policy_revisions (
            id                     UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
            policy_id              UUID         NOT NULL
                                                REFERENCES %I.analysis_policies (id) ON DELETE CASCADE,
            parent_revision_id     UUID,
            instruction_version_id UUID         NOT NULL,
            profile_version_id     UUID,
            content_digest         VARCHAR(64)  NOT NULL
                                                CHECK (content_digest ~ '^[0-9a-f]{64}$'),
            created_by             VARCHAR(100) NOT NULL,
            created_at             TIMESTAMPTZ  NOT NULL DEFAULT NOW()
        )
    $q$, _schema, _schema);
    EXECUTE format($q$
        CREATE INDEX IF NOT EXISTS ix_analysis_policy_revisions_policy
            ON %I.analysis_policy_revisions (policy_id, created_at DESC)
    $q$, _schema);

    -- ====================================================
    -- 3. analysis_instruction_versions（指示文の不変版）
    -- ====================================================
    EXECUTE format($q$
        CREATE TABLE IF NOT EXISTS %I.analysis_instruction_versions (
            id         UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
            policy_id  UUID         NOT NULL
                                    REFERENCES %I.analysis_policies (id) ON DELETE CASCADE,
            body       TEXT         NOT NULL CHECK (body <> ''),
            created_by VARCHAR(100) NOT NULL,
            created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
        )
    $q$, _schema, _schema);
    EXECUTE format($q$
        CREATE INDEX IF NOT EXISTS ix_analysis_instruction_versions_policy
            ON %I.analysis_instruction_versions (policy_id, created_at DESC)
    $q$, _schema);

    -- ====================================================
    -- 4. analysis_execution_profile_versions（モデル/出力契約の不変版）
    -- ====================================================
    EXECUTE format($q$
        CREATE TABLE IF NOT EXISTS %I.analysis_execution_profile_versions (
            id                   UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
            policy_id            UUID         NOT NULL
                                              REFERENCES %I.analysis_policies (id) ON DELETE CASCADE,
            model_id             VARCHAR(100) NOT NULL,
            generation_config    JSONB        NOT NULL DEFAULT '{}'::jsonb,
            output_schema        JSONB        NOT NULL DEFAULT '{}'::jsonb,
            input_limits         JSONB        NOT NULL DEFAULT '{}'::jsonb,
            compatibility_output JSONB,
            created_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW()
        )
    $q$, _schema, _schema);
    EXECUTE format($q$
        CREATE INDEX IF NOT EXISTS ix_analysis_execution_profiles_policy
            ON %I.analysis_execution_profile_versions (policy_id, created_at DESC)
    $q$, _schema);

    -- ====================================================
    -- 5. analysis_rules（ルールの不変識別子）
    -- ====================================================
    EXECUTE format($q$
        CREATE TABLE IF NOT EXISTS %I.analysis_rules (
            id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            policy_id        UUID        NOT NULL
                                         REFERENCES %I.analysis_policies (id) ON DELETE CASCADE,
            legacy_status_id UUID,
            created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    $q$, _schema, _schema);
    EXECUTE format($q$
        CREATE INDEX IF NOT EXISTS ix_analysis_rules_policy
            ON %I.analysis_rules (policy_id)
    $q$, _schema);

    -- ====================================================
    -- 6. analysis_rule_versions（ルールの説明/文脈の不変版）
    -- ====================================================
    EXECUTE format($q$
        CREATE TABLE IF NOT EXISTS %I.analysis_rule_versions (
            id                  UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
            rule_id             UUID         NOT NULL
                                             REFERENCES %I.analysis_rules (id) ON DELETE CASCADE,
            title               TEXT         NOT NULL,
            context_instruction TEXT,
            created_by          VARCHAR(100) NOT NULL,
            created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW()
        )
    $q$, _schema, _schema);
    EXECUTE format($q$
        CREATE INDEX IF NOT EXISTS ix_analysis_rule_versions_rule
            ON %I.analysis_rule_versions (rule_id, created_at DESC)
    $q$, _schema);

    -- ====================================================
    -- 7. analysis_rule_words（1語1行、kindで種類を区別）
    -- ====================================================
    EXECUTE format($q$
        CREATE TABLE IF NOT EXISTS %I.analysis_rule_words (
            id               UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
            rule_version_id  UUID         NOT NULL
                                          REFERENCES %I.analysis_rule_versions (id) ON DELETE CASCADE,
            kind             VARCHAR(30)  NOT NULL
                                          CHECK (kind IN ('search','exclude','format_template','apply_condition')),
            text             TEXT         NOT NULL CHECK (text <> ''),
            position         INTEGER      NOT NULL CHECK (position >= 0),
            UNIQUE (rule_version_id, kind, text)
        )
    $q$, _schema, _schema);
    EXECUTE format($q$
        CREATE INDEX IF NOT EXISTS ix_analysis_rule_words_version
            ON %I.analysis_rule_words (rule_version_id)
    $q$, _schema);

    -- ====================================================
    -- 8. analysis_revision_rules（版ごとのルール採用状態）
    -- ====================================================
    EXECUTE format($q$
        CREATE TABLE IF NOT EXISTS %I.analysis_revision_rules (
            revision_id      UUID    NOT NULL
                                     REFERENCES %I.analysis_policy_revisions (id) ON DELETE CASCADE,
            rule_id          UUID    NOT NULL
                                     REFERENCES %I.analysis_rules (id) ON DELETE CASCADE,
            rule_version_id  UUID    NOT NULL
                                     REFERENCES %I.analysis_rule_versions (id),
            is_deleted       BOOLEAN NOT NULL DEFAULT FALSE,
            PRIMARY KEY (revision_id, rule_id)
        )
    $q$, _schema, _schema, _schema, _schema);

    -- ====================================================
    -- 9. analysis_test_case_versions（人間の正解の不変版）
    -- ====================================================
    EXECUTE format($q$
        CREATE TABLE IF NOT EXISTS %I.analysis_test_case_versions (
            id         UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
            case_id    UUID         NOT NULL,
            policy_id  UUID         NOT NULL
                                    REFERENCES %I.analysis_policies (id) ON DELETE CASCADE,
            raw_text   TEXT         NOT NULL CHECK (raw_text <> ''),
            posted_at  TIMESTAMPTZ,
            expected   JSONB        NOT NULL,
            created_by VARCHAR(100) NOT NULL,
            created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
        )
    $q$, _schema, _schema);
    EXECUTE format($q$
        CREATE INDEX IF NOT EXISTS ix_analysis_test_case_versions_policy
            ON %I.analysis_test_case_versions (policy_id, case_id, created_at DESC)
    $q$, _schema);

    -- ====================================================
    -- 10. analysis_test_suites（テスト合格時の版集合）
    -- ====================================================
    EXECUTE format($q$
        CREATE TABLE IF NOT EXISTS %I.analysis_test_suites (
            id         UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
            policy_id  UUID         NOT NULL
                                    REFERENCES %I.analysis_policies (id) ON DELETE CASCADE,
            created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
        )
    $q$, _schema, _schema);

    -- ====================================================
    -- 11. analysis_suite_cases（テスト集合の構成要素）
    -- ====================================================
    EXECUTE format($q$
        CREATE TABLE IF NOT EXISTS %I.analysis_suite_cases (
            suite_id        UUID NOT NULL
                                 REFERENCES %I.analysis_test_suites (id) ON DELETE CASCADE,
            case_id         UUID NOT NULL,
            case_version_id UUID NOT NULL
                                 REFERENCES %I.analysis_test_case_versions (id),
            PRIMARY KEY (suite_id, case_id)
        )
    $q$, _schema, _schema, _schema);

    -- ====================================================
    -- 12. analysis_rule_runs（テスト/通常の実行記録）
    -- ====================================================
    EXECUTE format($q$
        CREATE TABLE IF NOT EXISTS %I.analysis_rule_runs (
            id                 UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
            policy_id          UUID         NOT NULL
                                            REFERENCES %I.analysis_policies (id) ON DELETE CASCADE,
            revision_id        UUID         NOT NULL
                                            REFERENCES %I.analysis_policy_revisions (id),
            suite_revision_id  UUID
                                            REFERENCES %I.analysis_test_suites (id),
            source_message_id  UUID,
            purpose            VARCHAR(20)  NOT NULL
                                            CHECK (purpose IN ('test','production')),
            engine_version     VARCHAR(50)  NOT NULL,
            request_key        UUID         NOT NULL UNIQUE,
            started_by         VARCHAR(100) NOT NULL,
            started_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            completed_at       TIMESTAMPTZ,
            state              VARCHAR(20)  NOT NULL DEFAULT 'pending'
                                            CHECK (state IN ('pending','running','passed','failed','error')),
            CONSTRAINT analysis_rule_runs_test_suite CHECK (
                (purpose = 'test') = (suite_revision_id IS NOT NULL)),
            CONSTRAINT analysis_rule_runs_prod_source CHECK (
                (purpose = 'production') = (source_message_id IS NOT NULL))
        )
    $q$, _schema, _schema, _schema, _schema);
    EXECUTE format($q$
        CREATE INDEX IF NOT EXISTS ix_analysis_rule_runs_policy
            ON %I.analysis_rule_runs (policy_id, started_at DESC)
    $q$, _schema);
    EXECUTE format($q$
        CREATE INDEX IF NOT EXISTS ix_analysis_rule_runs_state
            ON %I.analysis_rule_runs (state)
            WHERE state IN ('pending','running')
    $q$, _schema);

    -- ====================================================
    -- 13. analysis_rule_run_results（判断結果の正規化記録）
    -- ====================================================
    EXECUTE format($q$
        CREATE TABLE IF NOT EXISTS %I.analysis_rule_run_results (
            id                 UUID  PRIMARY KEY DEFAULT gen_random_uuid(),
            run_id             UUID  NOT NULL
                                     REFERENCES %I.analysis_rule_runs (id) ON DELETE CASCADE,
            case_version_id    UUID
                                     REFERENCES %I.analysis_test_case_versions (id),
            extraction_item_id UUID,
            decision           JSONB NOT NULL,
            source_spans       JSONB,
            rule_version_refs  JSONB,
            validation_error   TEXT,
            invalidated_at     TIMESTAMPTZ,
            created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT analysis_rule_run_results_target CHECK (
                (case_version_id IS NOT NULL) OR (extraction_item_id IS NOT NULL))
        )
    $q$, _schema, _schema, _schema);
    EXECUTE format($q$
        CREATE INDEX IF NOT EXISTS ix_analysis_rule_run_results_run
            ON %I.analysis_rule_run_results (run_id)
    $q$, _schema);
    EXECUTE format($q$
        CREATE INDEX IF NOT EXISTS ix_analysis_rule_run_results_valid
            ON %I.analysis_rule_run_results (extraction_item_id)
            WHERE invalidated_at IS NULL
    $q$, _schema);

    RAISE NOTICE '20260917_000000: 13 テーブル作成完了 (schema %)', _schema;

    -- ====================================================
    -- FK後付け: analysis_policies の自己参照FK（冪等）
    -- ====================================================
    IF NOT EXISTS (SELECT 1 FROM pg_constraint c JOIN pg_namespace n ON n.oid = c.connamespace WHERE c.conname = 'fk_analysis_policies_active_rev' AND n.nspname = _schema) THEN
        EXECUTE format($q$
            ALTER TABLE %I.analysis_policies
                ADD CONSTRAINT fk_analysis_policies_active_rev
                FOREIGN KEY (active_revision_id) REFERENCES %I.analysis_policy_revisions (id)
        $q$, _schema, _schema);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint c JOIN pg_namespace n ON n.oid = c.connamespace WHERE c.conname = 'fk_analysis_policies_draft_rev' AND n.nspname = _schema) THEN
        EXECUTE format($q$
            ALTER TABLE %I.analysis_policies
                ADD CONSTRAINT fk_analysis_policies_draft_rev
                FOREIGN KEY (draft_revision_id) REFERENCES %I.analysis_policy_revisions (id)
        $q$, _schema, _schema);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint c JOIN pg_namespace n ON n.oid = c.connamespace WHERE c.conname = 'fk_analysis_policies_suite_rev' AND n.nspname = _schema) THEN
        EXECUTE format($q$
            ALTER TABLE %I.analysis_policies
                ADD CONSTRAINT fk_analysis_policies_suite_rev
                FOREIGN KEY (current_suite_revision_id) REFERENCES %I.analysis_test_suites (id)
        $q$, _schema, _schema);
    END IF;

    -- FK後付け: source_messages / extraction_items が存在する場合のみ
    IF EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = _schema AND tablename = 'source_messages') THEN
        IF NOT EXISTS (SELECT 1 FROM pg_constraint c JOIN pg_namespace n ON n.oid = c.connamespace WHERE c.conname = 'fk_analysis_rule_runs_source_msg' AND n.nspname = _schema) THEN
            EXECUTE format($q$
                ALTER TABLE %I.analysis_rule_runs
                    ADD CONSTRAINT fk_analysis_rule_runs_source_msg
                    FOREIGN KEY (source_message_id) REFERENCES %I.source_messages (id) ON DELETE CASCADE
            $q$, _schema, _schema);
        END IF;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = _schema AND tablename = 'extraction_items') THEN
        IF NOT EXISTS (SELECT 1 FROM pg_constraint c JOIN pg_namespace n ON n.oid = c.connamespace WHERE c.conname = 'fk_analysis_rule_run_results_item' AND n.nspname = _schema) THEN
            EXECUTE format($q$
                ALTER TABLE %I.analysis_rule_run_results
                    ADD CONSTRAINT fk_analysis_rule_run_results_item
                    FOREIGN KEY (extraction_item_id) REFERENCES %I.extraction_items (id) ON DELETE CASCADE
            $q$, _schema, _schema);
        END IF;
    END IF;

    RAISE NOTICE '20260917_000000: FK後付け完了 (schema %)', _schema;

    RAISE NOTICE '20260917_000000: 完了。schema % に analysis_rule 13 テーブル作成完了（seed なし）', _schema;
END $$;
