-- Analysis Rule Tables: public スキーマへの新設（SSOT化）
--
-- 目的: 完売ルール・日付ルールの共通テーブル13表を public スキーマに作成する。
--       テナントスキーマにある同テーブルと並行して存在し、
--       バックエンドの参照先を public に切り替えることでSSOT化を実現する。
--
-- 設計根拠: docs/handoff/soldout-rule-public-migration/design.md
-- 参照元DDL: migrations/20260917_000000_create_analysis_rule_tables.sql
--
-- 変更点:
--   1. スキーマプレフィックスを public. に変更
--   2. DO $$ ... $$ ブロックなし・直接DDL文（20260919パターン踏襲）
--   3. cross-schema FK（source_messages / extraction_items / extraction_jobs）は省略
--   4. public 内のFK関係は維持
--   5. tenant_id カラムなし（productsパターン踏襲）
--   6. INDEX名は ix_ プレフィックスでそのまま（IF NOT EXISTS 付き）
--
-- 冪等性: CREATE TABLE IF NOT EXISTS / CREATE INDEX IF NOT EXISTS のみ
-- データINSERT: なし（テーブルの有無のみ）
--
-- 作成日: 2026-09-20

-- ====================================================
-- 1. analysis_policies（ルール管理の入口、種別ごとに1行）
-- ====================================================
CREATE TABLE IF NOT EXISTS public.analysis_policies (
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
);

-- ====================================================
-- 2. analysis_policy_revisions（保存のたびに不変版を作成）
-- ====================================================
CREATE TABLE IF NOT EXISTS public.analysis_policy_revisions (
    id                     UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    policy_id              UUID         NOT NULL
                                        REFERENCES public.analysis_policies (id) ON DELETE CASCADE,
    parent_revision_id     UUID,
    instruction_version_id UUID         NOT NULL,
    profile_version_id     UUID,
    content_digest         VARCHAR(64)  NOT NULL
                                        CHECK (content_digest ~ '^[0-9a-f]{64}$'),
    created_by             VARCHAR(100) NOT NULL,
    created_at             TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_analysis_policy_revisions_policy
    ON public.analysis_policy_revisions (policy_id, created_at DESC);

-- ====================================================
-- 3. analysis_instruction_versions（指示文の不変版）
-- ====================================================
CREATE TABLE IF NOT EXISTS public.analysis_instruction_versions (
    id         UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    policy_id  UUID         NOT NULL
                            REFERENCES public.analysis_policies (id) ON DELETE CASCADE,
    body       TEXT         NOT NULL CHECK (body <> ''),
    created_by VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_analysis_instruction_versions_policy
    ON public.analysis_instruction_versions (policy_id, created_at DESC);

-- ====================================================
-- 4. analysis_execution_profile_versions（モデル/出力契約の不変版）
-- ====================================================
CREATE TABLE IF NOT EXISTS public.analysis_execution_profile_versions (
    id                   UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    policy_id            UUID         NOT NULL
                                      REFERENCES public.analysis_policies (id) ON DELETE CASCADE,
    model_id             VARCHAR(100) NOT NULL,
    generation_config    JSONB        NOT NULL DEFAULT '{}'::jsonb,
    output_schema        JSONB        NOT NULL DEFAULT '{}'::jsonb,
    input_limits         JSONB        NOT NULL DEFAULT '{}'::jsonb,
    compatibility_output JSONB,
    created_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_analysis_execution_profiles_policy
    ON public.analysis_execution_profile_versions (policy_id, created_at DESC);

-- ====================================================
-- 5. analysis_rules（ルールの不変識別子）
-- ====================================================
CREATE TABLE IF NOT EXISTS public.analysis_rules (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    policy_id        UUID        NOT NULL
                                 REFERENCES public.analysis_policies (id) ON DELETE CASCADE,
    legacy_status_id UUID,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_analysis_rules_policy
    ON public.analysis_rules (policy_id);

-- ====================================================
-- 6. analysis_rule_versions（ルールの説明/文脈の不変版）
-- ====================================================
CREATE TABLE IF NOT EXISTS public.analysis_rule_versions (
    id                  UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_id             UUID         NOT NULL
                                     REFERENCES public.analysis_rules (id) ON DELETE CASCADE,
    title               TEXT         NOT NULL,
    context_instruction TEXT,
    created_by          VARCHAR(100) NOT NULL,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_analysis_rule_versions_rule
    ON public.analysis_rule_versions (rule_id, created_at DESC);

-- ====================================================
-- 7. analysis_rule_words（1語1行、kindで種類を区別）
-- ====================================================
CREATE TABLE IF NOT EXISTS public.analysis_rule_words (
    id               UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_version_id  UUID         NOT NULL
                                  REFERENCES public.analysis_rule_versions (id) ON DELETE CASCADE,
    kind             VARCHAR(30)  NOT NULL
                                  CHECK (kind IN ('search','exclude','format_template','apply_condition')),
    text             TEXT         NOT NULL CHECK (text <> ''),
    position         INTEGER      NOT NULL CHECK (position >= 0),
    UNIQUE (rule_version_id, kind, text)
);
CREATE INDEX IF NOT EXISTS ix_analysis_rule_words_version
    ON public.analysis_rule_words (rule_version_id);

-- ====================================================
-- 8. analysis_revision_rules（版ごとのルール採用状態）
-- ====================================================
CREATE TABLE IF NOT EXISTS public.analysis_revision_rules (
    revision_id      UUID    NOT NULL
                             REFERENCES public.analysis_policy_revisions (id) ON DELETE CASCADE,
    rule_id          UUID    NOT NULL
                             REFERENCES public.analysis_rules (id) ON DELETE CASCADE,
    rule_version_id  UUID    NOT NULL
                             REFERENCES public.analysis_rule_versions (id),
    is_deleted       BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (revision_id, rule_id)
);

-- ====================================================
-- 9. analysis_test_case_versions（人間の正解の不変版）
-- ====================================================
CREATE TABLE IF NOT EXISTS public.analysis_test_case_versions (
    id         UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id    UUID         NOT NULL,
    policy_id  UUID         NOT NULL
                            REFERENCES public.analysis_policies (id) ON DELETE CASCADE,
    raw_text   TEXT         NOT NULL CHECK (raw_text <> ''),
    posted_at  TIMESTAMPTZ,
    expected   JSONB        NOT NULL,
    created_by VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_analysis_test_case_versions_policy
    ON public.analysis_test_case_versions (policy_id, case_id, created_at DESC);

-- ====================================================
-- 10. analysis_test_suites（テスト合格時の版集合）
-- ====================================================
CREATE TABLE IF NOT EXISTS public.analysis_test_suites (
    id         UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    policy_id  UUID         NOT NULL
                            REFERENCES public.analysis_policies (id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- ====================================================
-- 11. analysis_suite_cases（テスト集合の構成要素）
-- ====================================================
CREATE TABLE IF NOT EXISTS public.analysis_suite_cases (
    suite_id        UUID NOT NULL
                         REFERENCES public.analysis_test_suites (id) ON DELETE CASCADE,
    case_id         UUID NOT NULL,
    case_version_id UUID NOT NULL
                         REFERENCES public.analysis_test_case_versions (id),
    PRIMARY KEY (suite_id, case_id)
);

-- ====================================================
-- 12. analysis_rule_runs（テスト/通常の実行記録）
-- NOTE: source_message_id は cross-schema FK を持たない（テナントスキーマのテーブルへのFK回避）
-- ====================================================
CREATE TABLE IF NOT EXISTS public.analysis_rule_runs (
    id                 UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    policy_id          UUID         NOT NULL
                                    REFERENCES public.analysis_policies (id) ON DELETE CASCADE,
    revision_id        UUID         NOT NULL
                                    REFERENCES public.analysis_policy_revisions (id),
    suite_revision_id  UUID
                                    REFERENCES public.analysis_test_suites (id),
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
);
CREATE INDEX IF NOT EXISTS ix_analysis_rule_runs_policy
    ON public.analysis_rule_runs (policy_id, started_at DESC);
CREATE INDEX IF NOT EXISTS ix_analysis_rule_runs_state
    ON public.analysis_rule_runs (state)
    WHERE state IN ('pending','running');

-- ====================================================
-- 13. analysis_rule_run_results（判断結果の正規化記録）
-- NOTE: extraction_item_id は cross-schema FK を持たない（テナントスキーマのテーブルへのFK回避）
-- ====================================================
CREATE TABLE IF NOT EXISTS public.analysis_rule_run_results (
    id                 UUID  PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id             UUID  NOT NULL
                             REFERENCES public.analysis_rule_runs (id) ON DELETE CASCADE,
    case_version_id    UUID
                             REFERENCES public.analysis_test_case_versions (id),
    extraction_item_id UUID,
    decision           JSONB NOT NULL,
    source_spans       JSONB,
    rule_version_refs  JSONB,
    validation_error   TEXT,
    invalidated_at     TIMESTAMPTZ,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT analysis_rule_run_results_target CHECK (
        (case_version_id IS NOT NULL) OR (extraction_item_id IS NOT NULL))
);
CREATE INDEX IF NOT EXISTS ix_analysis_rule_run_results_run
    ON public.analysis_rule_run_results (run_id);
CREATE INDEX IF NOT EXISTS ix_analysis_rule_run_results_valid
    ON public.analysis_rule_run_results (extraction_item_id)
    WHERE invalidated_at IS NULL;

-- ====================================================
-- FK後付け: analysis_policies の自己参照FK（冪等）
-- ====================================================
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint c
        JOIN pg_namespace n ON n.oid = c.connamespace
        WHERE c.conname = 'fk_public_analysis_policies_active_rev'
          AND n.nspname = 'public'
    ) THEN
        ALTER TABLE public.analysis_policies
            ADD CONSTRAINT fk_public_analysis_policies_active_rev
            FOREIGN KEY (active_revision_id) REFERENCES public.analysis_policy_revisions (id);
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint c
        JOIN pg_namespace n ON n.oid = c.connamespace
        WHERE c.conname = 'fk_public_analysis_policies_draft_rev'
          AND n.nspname = 'public'
    ) THEN
        ALTER TABLE public.analysis_policies
            ADD CONSTRAINT fk_public_analysis_policies_draft_rev
            FOREIGN KEY (draft_revision_id) REFERENCES public.analysis_policy_revisions (id);
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint c
        JOIN pg_namespace n ON n.oid = c.connamespace
        WHERE c.conname = 'fk_public_analysis_policies_suite_rev'
          AND n.nspname = 'public'
    ) THEN
        ALTER TABLE public.analysis_policies
            ADD CONSTRAINT fk_public_analysis_policies_suite_rev
            FOREIGN KEY (current_suite_revision_id) REFERENCES public.analysis_test_suites (id);
    END IF;
END $$;
